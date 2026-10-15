#!/usr/bin/env python3
"""Start, list, inspect, message and stop background Codex CLI runs.

`codex exec` has no background mode of its own, and a process started from
an agent's shell tool dies when that tool times out or kills its process
group. This script detaches each run into its own session (setsid on
macOS/Linux, a detached process group on Windows) under a small supervisor
that records the exit code, so a run survives the chat turn that started it.

A "run" is one Codex conversation (thread). `send` resumes the same thread,
so the run id stays the same across follow-ups.

Standard library only. Python 3.8+.

  codex_runs.py start  --cwd DIR [--name N] [--worktree | --no-worktree]
                       [--sandbox full|workspace-write|read-only] [--model M] -- PROMPT
  codex_runs.py list   [--all] [--json]
  codex_runs.py status ID|NAME [--json]
  codex_runs.py send   ID|NAME MESSAGE
  codex_runs.py wait   ID|NAME [--timeout SECONDS]
  codex_runs.py stop   ID|NAME

Environment: CODEX_BIN (default `codex`), CODEX_RUNS_DIR (default
~/.local/state/codex-runs).

Behaviour measured on Codex CLI 0.149-0.162:
- `codex exec --json` writes JSONL events: thread.started {thread_id},
  turn.started, item.started / item.completed {item: {type: agent_message |
  reasoning | command_execution | file_change | error, ...}},
  turn.completed {usage}, turn.failed {error: {message}}.
- `-o FILE` writes the final agent message to FILE.
- With stdin not a terminal it reads stdin to EOF ("Reading additional input
  from stdin..."), so runs get /dev/null or they never start.
- `codex exec resume <thread_id> PROMPT` continues the thread. It has no -C,
  so it runs from the run's folder.
- The default `exec` sandbox is read-only; workspace-write cannot reach the
  network (no git push, no package installs).
"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

CODEX = os.environ.get("CODEX_BIN", "codex")
ROOT = os.environ.get("CODEX_RUNS_DIR") or os.path.join(
    os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state"),
    "codex-runs")
SANDBOX = {
    "full": ["--dangerously-bypass-approvals-and-sandbox"],
    "workspace-write": ["-c", 'sandbox_mode="workspace-write"'],
    "read-only": ["-c", 'sandbox_mode="read-only"'],
}


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def run_dir(rid):
    return os.path.join(ROOT, rid)


def load(rid):
    try:
        with open(os.path.join(run_dir(rid), "run.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save(meta):
    path = os.path.join(run_dir(meta["id"]), "run.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def all_runs():
    if not os.path.isdir(ROOT):
        return []
    out = []
    for rid in os.listdir(ROOT):
        m = load(rid)
        if m:
            out.append(m)
    return sorted(out, key=lambda m: m.get("started", 0), reverse=True)


def find(ref):
    runs = all_runs()
    hits = [m for m in runs if m["id"] == ref] or \
           [m for m in runs if m["id"].startswith(ref)] or \
           [m for m in runs if ref.lower() in (m.get("name") or "").lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        die(f"No Codex run matches '{ref}'. Run `list --all`.")
    die("'%s' matches several runs: %s. Use the id." %
        (ref, ", ".join(f"{m['id']} ({m.get('name', '')})" for m in hits[:8])))


def alive(pid):
    if not pid:
        return False
    if os.name == "nt":
        r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True)
        return str(pid) in r.stdout
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def events(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return []
    out = []
    for l in lines:
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out


def turn_files(meta, n):
    d = run_dir(meta["id"])
    return (os.path.join(d, f"events-{n}.jsonl"), os.path.join(d, f"last-{n}.txt"),
            os.path.join(d, f"stderr-{n}.log"), os.path.join(d, f"exit-{n}.json"))


def one_line(text, n=160):
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def ago(ts):
    sec = max(0, int(time.time() - (ts or time.time())))
    for unit, n in (("d", 86400), ("h", 3600), ("m", 60)):
        if sec >= n:
            return f"{sec // n}{unit} ago"
    return f"{sec}s ago"


def state_of(meta):
    """working | done | failed | stopped, read from the newest turn."""
    n = meta["turns"]
    ev_path, _, err_path, exit_path = turn_files(meta, n)
    try:
        with open(exit_path, encoding="utf-8") as f:
            ex = json.load(f)
    except (OSError, ValueError):
        ex = None
    evs = events(ev_path)
    failed = next((e for e in reversed(evs) if e.get("type") in ("turn.failed", "error")), None)
    completed = any(e.get("type") == "turn.completed" for e in evs)
    if ex is None:
        if alive(meta.get("pid")):
            return "working", None
        return ("done" if completed else "stopped"), None
    if ex.get("signal") or meta.get("stopped_turn") == n:
        return "stopped", None
    if ex.get("code") == 0 and completed:
        return "done", None
    msg = ""
    if failed:
        msg = (failed.get("error") or {}).get("message") or failed.get("message") or ""
    if not msg:
        try:
            with open(err_path, encoding="utf-8", errors="replace") as f:
                msg = f.read()[-600:]
        except OSError:
            pass
    return "failed", one_line(msg, 300)


def last_message(meta):
    ev_path, last_path, _, _ = turn_files(meta, meta["turns"])
    try:
        with open(last_path, encoding="utf-8") as f:
            text = f.read().strip()
        if text:
            return text
    except OSError:
        pass
    for e in reversed(events(ev_path)):
        it = e.get("item") or {}
        if it.get("type") == "agent_message" and it.get("text"):
            return it["text"].strip()
    return ""


def headline(text):
    marks = [l.strip() for l in text.splitlines()
             if re.match(r"\s*(result|needs input|failed):", l, re.I)]
    return marks[-1] if marks else one_line(text.splitlines()[-1] if text else "")


def activity(meta, n=8):
    ev_path = turn_files(meta, meta["turns"])[0]
    acts, usage = [], None
    for e in events(ev_path):
        if e.get("type") == "turn.completed":
            usage = e.get("usage")
        it = e.get("item") or {}
        if e.get("type") != "item.completed":
            continue
        t = it.get("type")
        if t == "command_execution":
            acts.append(f"ran: {one_line(it.get('command', ''), 100)} (exit {it.get('exit_code')})")
        elif t == "file_change":
            files = ", ".join(c.get("path", "") for c in it.get("changes") or [])
            acts.append(f"edited: {one_line(files, 120)}")
        elif t == "agent_message":
            acts.append(f"said: {one_line(it.get('text', ''), 120)}")
        elif t == "error":
            acts.append(f"error: {one_line(it.get('message', ''), 120)}")
    return acts[-n:], usage


def git_summary(cwd):
    if not cwd or not os.path.isdir(cwd) or not shutil.which("git"):
        return None
    r = subprocess.run(["git", "-C", cwd, "status", "--porcelain=v1", "-b"],
                       capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        return None
    lines = r.stdout.splitlines()
    info = {"branch": lines[0][3:] if lines else "", "changed_files": len(lines) - 1}
    r = subprocess.run(["git", "-C", cwd, "log", "-3", "--format=%h %s"],
                       capture_output=True, text=True, timeout=20)
    if r.returncode == 0:
        info["recent_commits"] = r.stdout.strip().splitlines()
    return info


def spawn(meta, argv):
    """Start the supervisor for one turn, fully detached from this process."""
    sup = [sys.executable, os.path.abspath(__file__), "_supervise", meta["id"],
           str(meta["turns"]), "--"] + argv
    kw = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
              stderr=subprocess.DEVNULL, cwd=meta["cwd"], close_fds=True)
    if os.name == "nt":
        kw["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True  # setsid: survives the caller's process group
    p = subprocess.Popen(sup, **kw)
    meta["pid"] = p.pid
    save(meta)


def supervise(rid, turn, argv):
    meta = load(rid)
    ev_path, last_path, err_path, exit_path = turn_files(meta, int(turn))
    with open(ev_path, "w") as out, open(err_path, "w") as err:
        try:
            p = subprocess.Popen(argv,
                                 stdin=subprocess.DEVNULL, stdout=out, stderr=err, cwd=meta["cwd"])
        except FileNotFoundError:
            err.write(f"{argv[0]} not found on PATH\n")
            code, sig = 127, None
        else:
            code = p.wait()
            sig = -code if code < 0 else None
    with open(exit_path, "w") as f:
        json.dump({"code": code, "signal": sig, "ended": time.time()}, f)
    meta = load(rid)
    if meta and not meta.get("thread_id"):
        for e in events(ev_path):
            if e.get("type") == "thread.started":
                meta["thread_id"] = e.get("thread_id")
                save(meta)
                break


def codex_ok():
    if not shutil.which(CODEX):
        die(f"`{CODEX}` was not found on PATH. Install the Codex CLI "
            "(`npm install -g @openai/codex` or `brew install --cask codex`) or set CODEX_BIN.", 127)


def cmd_start(a):
    codex_ok()
    prompt = " ".join(a.prompt).strip()
    if not prompt:
        die("Give the task after `--`.")
    cwd = os.path.abspath(os.path.expanduser(a.cwd))
    if not os.path.isdir(cwd):
        die(f"No such directory: {cwd}")
    rid = time.strftime("%m%d%H%M%S") + "-" + os.urandom(2).hex()
    os.makedirs(run_dir(rid))
    top = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True) if shutil.which("git") else None
    in_git = bool(top and top.returncode == 0)
    work, branch = cwd, None
    if a.worktree or (in_git and not a.no_worktree):
        if not in_git:
            die(f"{cwd} is not a git repository, so it cannot get a worktree. "
                "Pass --no-worktree to work in the folder itself.")
        slug = re.sub(r"[^a-z0-9._-]+", "-", (a.name or "task").lower()).strip("-")[:40] or "task"
        branch = f"codex/{slug}-{rid}"
        work = os.path.join(ROOT, "worktrees", f"{slug}-{rid}")
        r = subprocess.run(["git", "-C", top.stdout.strip(), "worktree", "add", "-b", branch, work],
                           capture_output=True, text=True)
        if r.returncode != 0:
            die(f"git worktree add failed: {r.stderr.strip()}")
    meta = {"id": rid, "name": a.name or "", "cwd": work, "origin": cwd, "branch": branch,
            "sandbox": a.sandbox, "model": a.model, "started": time.time(), "turns": 1,
            "prompts": [prompt], "thread_id": None}
    save(meta)
    last = turn_files(meta, 1)[1]
    argv = [CODEX, "exec", "--json", "--skip-git-repo-check", "-o", last] + SANDBOX[a.sandbox]
    if a.model:
        argv += ["-m", a.model]
    spawn(meta, argv + ["--", prompt])
    time.sleep(4)
    state, err = state_of(load(rid))
    print(json.dumps({"id": rid, "name": meta["name"], "cwd": work, "branch": branch,
                      "sandbox": a.sandbox, "state": state, "error": err}, indent=1))
    if state == "failed":
        sys.exit(1)


def row(m):
    state, err = state_of(m)
    text = last_message(m)
    return {"id": m["id"], "name": m.get("name") or "", "state": state, "turns": m["turns"],
            "started": ago(m.get("started")), "cwd": m["cwd"], "branch": m.get("branch"),
            "headline": err or (headline(text) if state != "working" else ""),
            "thread_id": m.get("thread_id")}


def cmd_list(a):
    rows = [row(m) for m in all_runs()]
    if not a.all:
        day = time.time() - 86400
        rows = [r for r, m in zip(rows, all_runs()) if r["state"] == "working" or m["started"] > day]
    if a.json:
        print(json.dumps(rows, indent=1, ensure_ascii=False))
        return
    if not rows:
        print("No Codex runs" + ("" if a.all else " in the last day (try --all)") + ".")
        return
    for r in rows:
        print(f"{r['id']}  {r['state']:<8} {r['name'] or '-'}  [{r['started']}, {r['turns']} turn(s)]")
        if r["headline"]:
            print(f"          {r['headline']}")
        print(f"          {r['cwd']}")


def cmd_status(a):
    m = find(a.ref)
    r = row(m)
    acts, usage = activity(m)
    r.update({"last_prompt": one_line(m["prompts"][-1], 300), "recent": acts, "usage": usage,
              "last_message": last_message(m)[-2000:], "git": git_summary(m["cwd"])})
    if a.json:
        print(json.dumps(r, indent=1, ensure_ascii=False))
        return
    print(f"{r['id']}  {r['name']}  state={r['state']}  turns={r['turns']}  started {r['started']}")
    print(f"cwd: {r['cwd']}" + (f"  (branch {r['branch']})" if r["branch"] else ""))
    print(f"asked: {r['last_prompt']}")
    if r["headline"]:
        print(f"headline: {r['headline']}")
    if acts:
        print("recent activity:")
        for x in acts:
            print(f"  {x}")
    g = r["git"]
    if g:
        print(f"git: {g['branch']}  ({g['changed_files']} uncommitted files)")
        for c in g.get("recent_commits", []):
            print(f"  {c}")
    if r["last_message"]:
        print("last message:")
        print(r["last_message"][-1500:])


def cmd_send(a):
    codex_ok()
    m = find(a.ref)
    state, _ = state_of(m)
    if state == "working":
        die(f"{m['id']} is still working. Wait for it (`wait {m['id']}`) or `stop` it first.", 4)
    if not m.get("thread_id"):
        die(f"{m['id']} never started a Codex thread, so there is nothing to continue. Start a new run.")
    m["turns"] += 1
    m["prompts"].append(a.message)
    m.pop("stopped_turn", None)
    save(m)
    last = turn_files(m, m["turns"])[1]
    argv = [CODEX, "exec", "resume", "--json", "--skip-git-repo-check", "-o", last] + SANDBOX[m["sandbox"]]
    if m.get("model"):
        argv += ["-m", m["model"]]
    spawn(m, argv + [m["thread_id"], a.message])
    print(json.dumps({"id": m["id"], "turn": m["turns"], "state": "working"}, indent=1))


def cmd_wait(a):
    m = find(a.ref)
    deadline = time.time() + a.timeout
    while state_of(m)[0] == "working" and time.time() < deadline:
        time.sleep(3)
        m = load(m["id"])
    r = row(m)
    print(json.dumps({"id": r["id"], "state": r["state"], "headline": r["headline"],
                      "still_working": r["state"] == "working"}, indent=1, ensure_ascii=False))


def cmd_stop(a):
    m = find(a.ref)
    if state_of(m)[0] != "working":
        print(f"{m['id']} is not running.")
        return
    m["stopped_turn"] = m["turns"]
    save(m)
    pid = m["pid"]
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True)
    else:
        try:
            os.killpg(pid, signal.SIGTERM)  # the supervisor leads its own session
        except ProcessLookupError:
            pass
    print(f"stopped {m['id']}")


def main():
    if len(sys.argv) > 4 and sys.argv[1] == "_supervise" and sys.argv[4] == "--":
        return supervise(sys.argv[2], sys.argv[3], sys.argv[5:])
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("start")
    st.add_argument("--cwd", required=True)
    st.add_argument("--name")
    st.add_argument("--worktree", action="store_true")
    st.add_argument("--no-worktree", action="store_true")
    st.add_argument("--sandbox", choices=sorted(SANDBOX), default="full")
    st.add_argument("--model")
    st.add_argument("prompt", nargs=argparse.REMAINDER)
    ls = sub.add_parser("list")
    ls.add_argument("--all", action="store_true")
    ls.add_argument("--json", action="store_true")
    ss = sub.add_parser("status")
    ss.add_argument("ref")
    ss.add_argument("--json", action="store_true")
    sd = sub.add_parser("send")
    sd.add_argument("ref")
    sd.add_argument("message")
    wt = sub.add_parser("wait")
    wt.add_argument("ref")
    wt.add_argument("--timeout", type=int, default=150)
    sp = sub.add_parser("stop")
    sp.add_argument("ref")
    a = p.parse_args()
    if a.cmd == "start" and a.prompt[:1] == ["--"]:
        a.prompt = a.prompt[1:]
    {"start": cmd_start, "list": cmd_list, "status": cmd_status, "send": cmd_send,
     "wait": cmd_wait, "stop": cmd_stop}[a.cmd](a)


if __name__ == "__main__":
    main()
