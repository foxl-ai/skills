#!/usr/bin/env python3
"""Start, inspect, message and stop Claude Code background sessions.

start/spawn creates a NEW native session through the configured CLI wrapper.
send uses a version-gated private supervisor bridge to queue into an EXISTING
session. It never stops, resumes, forks or starts a daemon. queue shows receipts,
not a helper delivery queue. doctor performs only read-only bridge checks.

Standard library, Python 3.8+. CLAUDE_BIN defaults to claude. CLAUDE_CONFIG_DIR
defaults to ~/.claude. CC_SESSIONS_STATE defaults to
$XDG_STATE_HOME/claude-code-sessions or ~/.local/state/claude-code-sessions.
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

from cc_native_reply import BridgeError, NativeReply, MANUAL, MAX_REPLY, SHORT_ID, SESSION_ID
from cc_outbox import Outbox, atomic_save

CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
CONFIG = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
STATE = os.environ.get("CC_SESSIONS_STATE") or os.path.join(
    os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state"),
    "claude-code-sessions")
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
        die("The configured executable was not found. Install Claude Code or set CLAUDE_BIN.", 127)
    except subprocess.TimeoutExpired:
        die("The configured CLI did not answer within %ss. No automatic retry." % timeout)
    out = ANSI.sub("", p.stdout)
    err = "\n".join(line for line in ANSI.sub("", p.stderr).splitlines()
                    if not line.startswith("claude: "))
    return p.returncode, out, err


def need_bg_support():
    _, out, _ = run([CLAUDE, "--help"])
    if "--bg" not in out:
        die("This Claude Code has no background sessions (`--bg`). Run `claude update`.", 2)


def cli_version():
    code, out, _ = run([CLAUDE, "--version"], timeout=15)
    # Explicitly reviewed wrapper build identifiers, not assumed public semver support.
    hits = re.findall(r"\b\d+\.\d+\.\d+(?:\.\d+)?\b", out)
    if code or len(hits) != 1:
        raise BridgeError("EVERSION", "Cannot identify the configured CLI build safely.")
    return hits[0]


def sessions(include_done=True):
    args = [CLAUDE, "agents", "--json"] + (["--all"] if include_done else [])
    code, out, _ = run(args, timeout=15)
    if code:
        die("`claude agents --json` failed. No session mutation was attempted.")
    try:
        start = out.find("[")
        items = json.loads(out[start:]) if start >= 0 else None
        if not isinstance(items, list) or any(not isinstance(s, dict) for s in items):
            raise ValueError()
        ids = [s.get("id") for s in items]
        if any(not isinstance(sid, str) or not SHORT_ID.fullmatch(sid) for sid in ids) or len(ids) != len(set(ids)):
            raise ValueError()
    except (ValueError, TypeError):
        die("Could not parse unique canonical IDs from `claude agents --json`.")
    records = {s["id"]: s for s in items}
    if include_done:
        for s in sessions(include_done=False):
            previous = records.get(s["id"], {})
            if previous.get("sessionId", s.get("sessionId")) != s.get("sessionId"):
                die("The canonical session identity changed between CLI reads. No mutation attempted.")
            records[s["id"]] = {**previous, **s}
    return list(records.values())


def find(ref):
    if not ref.strip():
        die("Use an exact session ID or a unique name.")
    items = sessions()
    exact = [s for s in items if s["id"] == ref or s.get("sessionId") == ref]
    pref = [s for s in items if s["id"].startswith(ref)]
    named = [s for s in items if ref.lower() in (s.get("name") or "").lower()]
    hits = exact or pref or named
    if len(hits) == 1:
        return hits[0]
    if not hits:
        die(f"No Claude Code session matches '{ref}'. Run `list --all`.")
    names = ", ".join(f"{s['id']} ({s.get('name', '')})" for s in hits[:8])
    die(f"'{ref}' matches several sessions: {names}. Use the exact id.")


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
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def transcript(s):
    sid = s.get("sessionId")
    if not isinstance(sid, str) or not SESSION_ID.fullmatch(sid):
        return None
    hits = glob.glob(os.path.join(CONFIG, "projects", "*", sid + ".jsonl"))
    return max(hits, key=os.path.getmtime) if hits else None


def state_of(s):
    st = read_json(os.path.join(job_dir(s["id"]), "state.json")) or {}
    state = st.get("state") or s.get("state") or "unknown"
    if state == "working" and not s.get("pid"):
        state = "stopped"
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
    return text if len(text) <= n else text[:n - 1] + "…"


def summary(s):
    state, st = state_of(s)
    out = st.get("output") or {}
    detail = st.get("detail") or ""
    headline = out.get("result") or out.get("needsInput") or out.get("failed") or detail
    last = (read_jsonl(os.path.join(job_dir(s["id"]), "timeline.jsonl"), tail=1) or [{}])[-1]
    marks = [line.strip() for line in (last.get("text") or "").splitlines()
             if re.match(r"\s*(result|needs input|failed):", line, re.I)]
    if marks and last.get("state") == state:
        headline = marks[-1].split(":", 1)[1].strip() or headline
    if headline in ("done", state):
        headline = ""
    return {
        "id": s["id"], "name": s.get("name") or "", "state": state,
        "running": bool(s.get("pid")), "cwd": s.get("cwd") or "",
        "started": ago(s.get("startedAt")), "headline": one_line(headline),
        "sessionId": s.get("sessionId"), "native_queue_depth": None,
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
    for entry in entries:
        if entry.get("type") == "system" and entry.get("subtype") == "away_summary":
            recap = entry.get("content") or recap
        msg = entry.get("message")
        if entry.get("type") != "assistant" or not isinstance(msg, dict):
            continue
        for block in msg.get("content") or []:
            if block.get("type") == "text" and block.get("text", "").strip():
                last_text = block["text"].strip()
            elif block.get("type") == "tool_use":
                inp = block.get("input") or {}
                what = (inp.get("description") or inp.get("command") or inp.get("file_path")
                        or inp.get("pattern") or inp.get("prompt") or "")
                tools.append(f"{block.get('name')}: {one_line(str(what), 100)}")
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
        die(f"Claude Code has not been opened in {cwd} on this computer yet. Ask the user "
            "to open Claude Code there and accept the trust prompt. Do not bypass it.", 3)
    match = re.search(r"backgrounded\s*\S\s*([0-9a-f]{8})", text)
    if code != 0 or not match:
        die(f"Claude Code did not confirm a new session (exit {code}). Check `list --all` before retrying.")
    print(json.dumps({
        "id": match.group(1), "name": a.name or "", "cwd": cwd, "created_new": True,
        "worktree": os.path.join(top[1].strip(), ".claude", "worktrees", worktree) if worktree else None,
        "branch": f"worktree-{worktree}" if worktree else None, "mode": a.mode,
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
        detail = one_line(t.get("detail") or "", 140)
        if detail and (not steps or steps[-1]["detail"] != detail):
            steps.append({"at": t.get("at", ""), "state": t.get("state"), "detail": detail})
    last_text, tools, recap = recent_activity(transcript(s))
    row.update({
        "recap": one_line(recap, 600), "last_message": last_text[-2000:],
        "recent_tools": tools, "timeline": steps[-6:], "tokens": st.get("tokens"),
        "git": git_summary(s.get("cwd")), "queue": Outbox(STATE, CONFIG).view(s),
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
    print_queue(row["queue"])
    if last_text:
        print("last message:")
        print(last_text[-1500:])


def cmd_doctor(a):
    bridge = NativeReply(CONFIG, cli_version())
    report = bridge.probe()
    if a.ref:
        s = find(a.ref)
        box = Outbox(STATE, CONFIG)
        box.assert_current(box.legacy(), s["id"])
        report["target"] = bridge.prepare(s)
    report["manual"] = MANUAL
    print(json.dumps(report, indent=1))


def receipt_output(receipt, duplicate=False):
    result = {key: value for key, value in receipt.items() if key not in ("config_sha256", "message_sha256")}
    result["duplicate_suppressed"] = duplicate
    result["same_session"] = True
    print(json.dumps(result, indent=1))
    return 0 if receipt["status"] == "accepted" else 5 if receipt["status"] == "unknown" else 4


def cmd_send(a):
    if a.force or a.no_queue or a.expire_after is not None:
        raise BridgeError("ELEGACYOPTION", "Interrupt/expiry/helper-queue options were retired. Native send never stops a turn.")
    if not a.message.strip() or "\0" in a.message or len(a.message.encode("utf-8")) > MAX_REPLY:
        raise BridgeError("EMESSAGE", "Reply text must be nonempty without NUL and at most 64 KiB.")
    s = find(a.ref)
    box = Outbox(STATE, CONFIG)
    with box.mutation_guard() as legacy:
        box.assert_current(legacy, s["id"])
        path, receipt = box.request(s, a.message, a.request_id)
        previous = box.existing(path, receipt)
        if previous is not None:
            return receipt_output(previous, duplicate=True)
        bridge = NativeReply(CONFIG, cli_version())
        bridge.prepare(s)
        atomic_save(path, receipt)  # Crash-safe reservation BEFORE any reply bytes are sent.
        try:
            response = bridge.reply(s, a.message)
            receipt.update(response, status="accepted", note=(
                "Accepted into the same native session's safe-boundary queue. "
                "Consumption is not observed; multiple messages may share a turn."))
        except BridgeError as exc:
            receipt.update(status="unknown" if exc.uncertain else "rejected", error_code=exc.code,
                           note=str(exc) + " " + MANUAL,
                           accepted=None if exc.uncertain else False, queued=None if exc.uncertain else False)
        receipt["finished"] = time.time()
        try:
            atomic_save(path, receipt)
        except OSError:
            # Reservation remains unknown. Reporting acceptance without a durable receipt invites retry copies.
            raise BridgeError("ERECEIPT", "Could not persist the acknowledgement. Treat outcome as unknown; do not resend.", True)
        return receipt_output(receipt)


def cmd_queue(a):
    s = find(a.ref)
    box = Outbox(STATE, CONFIG)
    if a.clear:
        with box.mutation_guard() as legacy:
            cancelled = box.cancel_legacy(legacy, s["id"])
        print(json.dumps({"id": s["id"], "legacy_cancelled": cancelled, "native_cancelled": False,
                          "note": "Only legacy pending messages were cancelled. Native accepted messages cannot be recalled here."}, indent=1))
        return
    view = box.view(s)
    if a.json:
        print(json.dumps(view, indent=1))
    else:
        print_queue(view)


def print_queue(view):
    print("send receipts (not native queue depth; consumption is not observed):")
    for item in view["items"][-10:]:
        print(f"  {item['request_id']}  {item['status']}  observed={item.get('observed', False)}")
    if view["legacy"]:
        print(f"legacy history: {len(view['legacy'])} entries, automatic delivery disabled")
    if not view["items"] and not view["legacy"]:
        print("  none")


def cmd_wait(a):
    s = find(a.ref)
    deadline = time.time() + a.timeout
    time.sleep(3)
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
    box = Outbox(STATE, CONFIG)
    with box.mutation_guard() as legacy:
        box.assert_current(legacy, s["id"])
        cancelled = box.cancel_legacy(legacy, s["id"])
        code, out, err = run([CLAUDE, "stop", s["id"]])
    print(json.dumps({"id": s["id"], "stopped": code == 0, "legacy_cancelled": cancelled,
                      "automatic_replay": False,
                      "note": "No resume will be attempted. Native queued messages are owned by Claude, not this helper."}, indent=1))
    return code


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["_watch"]:
        die("Legacy queue watcher retired. No messages were replayed. Use explicit native send or agents UI.", 4)
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("start", aliases=["spawn"], help="create a NEW session")
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
    sd = sub.add_parser("send", help="queue into an EXISTING session; never spawn")
    sd.add_argument("ref")
    sd.add_argument("message")
    sd.add_argument("--request-id", help="stable caller key; reuse on retries (default dedupes identical text per session)")
    sd.add_argument("--force", action="store_true", help=argparse.SUPPRESS)
    sd.add_argument("--no-queue", action="store_true", help=argparse.SUPPRESS)
    sd.add_argument("--expire-after", type=int, help=argparse.SUPPRESS)
    doc = sub.add_parser("doctor", help="read-only native bridge probe; no daemon starts")
    doc.add_argument("ref", nargs="?")
    doc.add_argument("--json", action="store_true")
    qu = sub.add_parser("queue", help="show receipts and retired legacy history")
    qu.add_argument("ref")
    qu.add_argument("--clear", action="store_true", help="cancel legacy pending messages only")
    qu.add_argument("--json", action="store_true")
    wt = sub.add_parser("wait")
    wt.add_argument("ref")
    wt.add_argument("--timeout", type=int, default=150)
    sp = sub.add_parser("stop")
    sp.add_argument("ref")
    a = p.parse_args(argv)
    if a.cmd in ("start", "spawn") and a.prompt[:1] == ["--"]:
        a.prompt = a.prompt[1:]
    try:
        result = {"start": cmd_start, "spawn": cmd_start, "list": cmd_list, "status": cmd_status,
                  "send": cmd_send, "doctor": cmd_doctor, "queue": cmd_queue,
                  "wait": cmd_wait, "stop": cmd_stop}[a.cmd](a)
        return result or 0
    except BridgeError as exc:
        print(json.dumps({"status": "unknown" if exc.uncertain else "refused", "error_code": exc.code,
                          "accepted": None if exc.uncertain else False, "observed": False,
                          "note": str(exc), "manual": MANUAL}, indent=1))
        return 5 if exc.uncertain else 4
    except OSError:
        # No raw frames, file contents, credentials, or prompt text in errors.
        print(json.dumps({"status": "refused", "error_code": "ELOCAL", "observed": False,
                          "note": "Local state access failed. Inspect receipts before any new request.",
                          "manual": MANUAL}, indent=1))
        return 4


if __name__ == "__main__":
    sys.exit(main())
