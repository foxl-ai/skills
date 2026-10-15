#!/usr/bin/env python3
"""Start, list, inspect, message and stop Claude Code background sessions.

A thin layer over the Claude Code CLI's own background sessions
(`claude --bg`, `claude agents --json`, `claude stop`), which outlive the
shell that started them. This script adds what a chat client needs on top:
plain-text status instead of the raw terminal stream that `claude logs`
prints, follow-up messages, and waiting for a turn to finish.

Standard library only. Python 3.8+.

  cc_sessions.py start  --cwd DIR [--name N] [--worktree N | --no-worktree]
                        [--mode bypass|auto|acceptEdits|plan] [--model M]
                        [--effort E] -- PROMPT
  cc_sessions.py list   [--all] [--json]
  cc_sessions.py status ID|NAME [--json]
  cc_sessions.py send   ID|NAME MESSAGE
  cc_sessions.py wait   ID|NAME [--timeout SECONDS]
  cc_sessions.py stop   ID|NAME

Environment: CLAUDE_BIN (default `claude`), CLAUDE_CONFIG_DIR (default
~/.claude).

Behaviour measured on Claude Code 2.1.284-2.1.300:
- `claude --bg` prints `backgrounded · <8-hex id> · <name>` and returns.
- It refuses a directory whose trust prompt was never accepted
  ("Workspace not trusted. Run `claude` in <dir> once ...").
- `claude logs` is the raw TUI stream (ANSI), so status reads
  <config>/jobs/<id>/state.json + timeline.jsonl and the transcript
  <config>/projects/*/<sessionId>.jsonl instead.
- A follow-up to a live session: `claude stop <id>`, then
  `claude --bg --resume <full session uuid> "message"` with NO other flags
  continues the same id. Any extra flag, or a short id, starts a copy under a
  new id (the CLI says so); `send` reports the id to follow either way.
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
CONFIG = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
MODES = {
    "bypass": ["--dangerously-skip-permissions"],
    "auto": ["--permission-mode", "auto"],
    "acceptEdits": ["--permission-mode", "acceptEdits"],
    "plan": ["--permission-mode", "plan"],
}


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def run(args, cwd=None, timeout=60):
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        die(f"`{args[0]}` was not found on PATH. Install Claude Code "
            "(https://docs.anthropic.com/en/docs/claude-code) or set CLAUDE_BIN.", 127)
    except subprocess.TimeoutExpired:
        die(f"`{' '.join(args[:3])}` did not answer within {timeout}s.")
    # Some installs print wrapper diagnostics on stderr; keep only CLI text.
    out = ANSI.sub("", p.stdout)
    err = "\n".join(l for l in ANSI.sub("", p.stderr).splitlines()
                    if not l.startswith("claude: "))
    return p.returncode, out, err


def need_bg_support():
    _, out, _ = run([CLAUDE, "--help"])
    if "--bg" not in out:
        die("This Claude Code has no background sessions (`--bg`). "
            "Run `claude update` (2.1.284 or newer is needed).", 2)


def sessions(include_done=True):
    args = [CLAUDE, "agents", "--json"] + (["--all"] if include_done else [])
    code, out, err = run(args)
    if code != 0:
        die(f"`claude agents --json` failed: {err.strip() or out.strip()}")
    start = out.find("[")
    try:
        items = json.loads(out[start:]) if start >= 0 else []
    except ValueError:
        die("Could not parse `claude agents --json` output.")
    live = {s["id"]: s for s in items}
    if include_done:
        # --all omits pid; merge the live view so we know what is running.
        for s in sessions(include_done=False):
            live[s["id"]] = {**live.get(s["id"], {}), **s}
    return list(live.values())


def find(ref):
    items = sessions()
    exact = [s for s in items if s["id"] == ref or s.get("sessionId") == ref]
    if exact:
        return exact[0]
    pref = [s for s in items if s["id"].startswith(ref)]
    named = [s for s in items if ref.lower() in (s.get("name") or "").lower()]
    hits = pref or named
    if len(hits) == 1:
        return hits[0]
    if not hits:
        die(f"No Claude Code session matches '{ref}'. Run `list --all`.")
    names = ", ".join(f"{s['id']} ({s.get('name', '')})" for s in hits[:8])
    die(f"'{ref}' matches several sessions: {names}. Use the id.")


def job_dir(sid):
    return os.path.join(CONFIG, "jobs", sid)


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def read_jsonl(path, tail=None):
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []
    if tail:
        lines = lines[-tail:]
    out = []
    for l in lines:
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out


def transcript(s):
    sid = s.get("sessionId")
    if not sid:
        return None
    hits = glob.glob(os.path.join(CONFIG, "projects", "*", sid + ".jsonl"))
    return max(hits, key=os.path.getmtime) if hits else None


def state_of(s):
    st = read_json(os.path.join(job_dir(s["id"]), "state.json")) or {}
    state = st.get("state") or s.get("state") or "unknown"
    if state == "working" and not s.get("pid"):
        state = "stopped"  # the process is gone mid-turn
    return state, st


def ago(ms):
    if not ms:
        return ""
    sec = max(0, int(time.time() - ms / 1000))
    for unit, n in (("d", 86400), ("h", 3600), ("m", 60)):
        if sec >= n:
            return f"{sec // n}{unit} ago"
    return f"{sec}s ago"


def one_line(text, n=160):
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def summary(s):
    state, st = state_of(s)
    out = st.get("output") or {}
    detail = st.get("detail") or ""
    # The session's own last line: its `result:` / `needs input:` / `failed:`
    # headline when it wrote one, else what it is doing now.
    headline = out.get("result") or out.get("needsInput") or out.get("failed") or detail
    # A resumed session's last timeline entry carries every turn's text; its
    # LAST headline line is the current one.
    last = (read_jsonl(os.path.join(job_dir(s["id"]), "timeline.jsonl"), tail=1) or [{}])[-1]
    marks = [l.strip() for l in (last.get("text") or "").splitlines()
             if re.match(r"\s*(result|needs input|failed):", l, re.I)]
    if marks and last.get("state") == state:
        headline = marks[-1].split(":", 1)[1].strip() or headline
    if headline in ("done", state):
        headline = ""
    return {
        "id": s["id"], "name": s.get("name") or "", "state": state,
        "running": bool(s.get("pid")), "cwd": s.get("cwd") or "",
        "started": ago(s.get("startedAt")), "headline": one_line(headline),
        "sessionId": s.get("sessionId"),
    }


def git_summary(cwd):
    if not cwd or not os.path.isdir(cwd) or not shutil.which("git"):
        return None
    code, out, _ = run(["git", "-C", cwd, "status", "--porcelain=v1", "-b"], timeout=20)
    if code != 0:
        return None
    lines = out.splitlines()
    head = lines[0][3:] if lines else ""
    info = {"branch": head, "changed_files": len(lines) - 1}
    code, out, _ = run(["git", "-C", cwd, "log", "-3", "--format=%h %s"], timeout=20)
    if code == 0:
        info["recent_commits"] = out.strip().splitlines()
    if shutil.which("gh"):
        code, out, _ = run(["gh", "pr", "view", "--json", "url,state,title"], cwd=cwd, timeout=20)
        if code == 0:
            try:
                info["pr"] = json.loads(out)
            except ValueError:
                pass
    return info


def recent_activity(path, n=6):
    """Last assistant text and the last few tool calls from the transcript."""
    entries = read_jsonl(path, tail=400) if path else []
    last_text, tools, recap = "", [], ""
    for e in entries:
        if e.get("type") == "system" and e.get("subtype") == "away_summary":
            recap = e.get("content") or recap
        msg = e.get("message")
        if e.get("type") != "assistant" or not isinstance(msg, dict):
            continue
        for b in msg.get("content") or []:
            if b.get("type") == "text" and b.get("text", "").strip():
                last_text = b["text"].strip()
            elif b.get("type") == "tool_use":
                inp = b.get("input") or {}
                what = (inp.get("description") or inp.get("command") or inp.get("file_path")
                        or inp.get("pattern") or inp.get("prompt") or "")
                tools.append(f"{b.get('name')}: {one_line(str(what), 100)}")
    return last_text, tools[-n:], recap


def cmd_start(a):
    need_bg_support()
    prompt = " ".join(a.prompt).strip()
    if not prompt:
        die("Give the task after `--`.")
    cwd = os.path.abspath(os.path.expanduser(a.cwd))
    if not os.path.isdir(cwd):
        die(f"No such directory: {cwd}")
    args = [CLAUDE, "--bg"] + MODES[a.mode]
    if a.name:
        args += ["-n", a.name]
    if a.model:
        args += ["--model", a.model]
    if a.effort:
        args += ["--effort", a.effort]
    top = run(["git", "-C", cwd, "rev-parse", "--show-toplevel"], timeout=20) \
        if shutil.which("git") else (1, "", "")
    in_git = top[0] == 0
    worktree = None
    if not a.no_worktree:
        if in_git:
            worktree = a.worktree or re.sub(r"[^a-z0-9._-]+", "-", (a.name or "task").lower()).strip("-")[:48]
            worktree = f"{worktree}-{time.strftime('%m%d-%H%M%S')}"
            args += ["-w", worktree]
        elif a.worktree:
            die(f"{cwd} is not a git repository, so it cannot get a worktree. "
                "Pass --no-worktree to work in the folder itself.")
    args.append(prompt)
    code, out, err = run(args, cwd=cwd, timeout=90)
    text = (out + "\n" + err).strip()
    if "not trusted" in text:
        die(f"Claude Code has not been opened in {cwd} on this computer yet, so it "
            "will not start a background session there. Ask the user to run `claude` "
            "in that folder once at the computer and accept the trust prompt "
            "(or choose a folder they already use with Claude Code).", 3)
    m = re.search(r"backgrounded\s*\S\s*([0-9a-f]{8})", text)
    if code != 0 or not m:
        die(f"Claude Code did not start the session (exit {code}):\n{text}")
    sid = m.group(1)
    print(json.dumps({
        "id": sid, "name": a.name or "", "cwd": cwd,
        "worktree": os.path.join(top[1].strip(), ".claude", "worktrees", worktree) if worktree else None,
        "branch": f"worktree-{worktree}" if worktree else None,
        "mode": a.mode,
    }, indent=1))


def cmd_list(a):
    rows = [summary(s) for s in sessions(include_done=True)]
    if not a.all:
        rows = [r for r in rows if r["running"] or r["state"] in ("working", "blocked")]
    rows.sort(key=lambda r: (r["state"] != "blocked", r["state"] != "working", r["id"]))
    if a.json:
        print(json.dumps(rows, indent=1, ensure_ascii=False))
        return
    if not rows:
        print("No Claude Code background sessions" + ("" if a.all else " running (try --all)") + ".")
        return
    for r in rows:
        print(f"{r['id']}  {r['state']:<8} {r['name'] or '-'}  [{r['started']}]")
        if r["headline"]:
            print(f"          {r['headline']}")
        print(f"          {r['cwd']}")


def cmd_status(a):
    s = find(a.ref)
    row = summary(s)
    _, st = state_of(s)
    timeline = read_jsonl(os.path.join(job_dir(s["id"]), "timeline.jsonl"), tail=200)
    steps = []
    for t in timeline:
        d = one_line(t.get("detail") or "", 140)
        if d and (not steps or steps[-1]["detail"] != d):
            steps.append({"at": t.get("at", ""), "state": t.get("state"), "detail": d})
    last_text, tools, recap = recent_activity(transcript(s))
    row.update({
        "recap": one_line(recap, 600),
        "last_message": last_text[-2000:],
        "recent_tools": tools,
        "timeline": steps[-6:],
        "tokens": st.get("tokens"),
        "git": git_summary(s.get("cwd")),
    })
    if a.json:
        print(json.dumps(row, indent=1, ensure_ascii=False))
        return
    print(f"{row['id']}  {row['name']}  state={row['state']}  running={row['running']}  started {row['started']}")
    print(f"cwd: {row['cwd']}")
    if row["headline"]:
        print(f"headline: {row['headline']}")
    if row["recap"]:
        print(f"recap: {row['recap']}")
    if steps:
        print("progress:")
        for t in steps[-6:]:
            print(f"  {t['at'][11:19]} {t['state']:<8} {t['detail']}")
    if tools:
        print("recent tool calls:")
        for t in tools:
            print(f"  {t}")
    g = row["git"]
    if g:
        print(f"git: {g['branch']}  ({g['changed_files']} uncommitted files)")
        for c in g.get("recent_commits", []):
            print(f"  {c}")
        if g.get("pr"):
            print(f"pr: {g['pr'].get('state')} {g['pr'].get('url')}")
    if last_text:
        print("last message:")
        print(last_text[-1500:])


def cmd_send(a):
    s = find(a.ref)
    state, _ = state_of(s)
    if state == "working" and not a.force:
        die(f"{s['id']} is still working. Wait for it (`wait {s['id']}`), or pass "
            "--force to interrupt the current turn and send this instead.", 4)
    if s.get("pid"):
        code, out, err = run([CLAUDE, "stop", s["id"]])
        if code != 0:
            die(f"Could not pause {s['id']} to deliver the message: {err or out}")
    tl = os.path.join(job_dir(s["id"]), "timeline.jsonl")
    before = len(read_jsonl(tl))
    # No other flags: the session keeps its own saved options, and any flag here
    # would make the CLI start a copy instead of continuing this session.
    code, out, err = run([CLAUDE, "--bg", "--resume", s["sessionId"], a.message],
                         cwd=s.get("cwd") or None, timeout=90)
    text = (out + "\n" + err).strip()
    m = re.search(r"backgrounded\s*\S\s*([0-9a-f]{8})", text)
    if code != 0 or not m:
        die(f"Claude Code did not accept the message (exit {code}):\n{text}")
    new = m.group(1)
    # Return only once the new turn shows up, so an immediate `wait` cannot
    # mistake the previous turn's "done" for this one.
    tl = os.path.join(job_dir(new), "timeline.jsonl")
    if new != s["id"]:
        before = 0
    started = False
    for _ in range(30):
        entries = read_jsonl(tl)
        if len(entries) > before and any(e.get("state") == "working" for e in entries[before:]):
            started = True
            break
        time.sleep(2)
    print(json.dumps({"id": new, "continued": new == s["id"], "turn_started": started,
                      "note": "" if new == s["id"] else
                      f"The CLI started a copy of {s['id']} as {new}; follow {new} from now on."},
                     indent=1))


def cmd_wait(a):
    s = find(a.ref)
    deadline = time.time() + a.timeout
    time.sleep(3)  # a just-sent message may not have flipped the state yet
    while True:
        state, _ = state_of(s)
        if state != "working" or time.time() >= deadline:
            break
        time.sleep(5)
        s = find(s["id"])
    r = summary(s)
    print(json.dumps({"id": r["id"], "state": r["state"], "headline": r["headline"],
                      "still_working": r["state"] == "working"}, indent=1, ensure_ascii=False))


def cmd_stop(a):
    s = find(a.ref)
    code, out, err = run([CLAUDE, "stop", s["id"]])
    print((out or err).strip() or f"stopped {s['id']}")
    sys.exit(code)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("start")
    st.add_argument("--cwd", required=True)
    st.add_argument("--name")
    st.add_argument("--worktree")
    st.add_argument("--no-worktree", action="store_true")
    st.add_argument("--mode", choices=sorted(MODES), default="bypass")
    st.add_argument("--model")
    st.add_argument("--effort")
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
    sd.add_argument("--force", action="store_true")
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
