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
  cc_sessions.py send   ID|NAME MESSAGE [--force | --no-queue]
                        [--expire-after MINUTES]
  cc_sessions.py queue  ID|NAME [--clear] [--json]
  cc_sessions.py wait   ID|NAME [--timeout SECONDS]
  cc_sessions.py stop   ID|NAME

Environment: CLAUDE_BIN (default `claude`), CLAUDE_CONFIG_DIR (default
~/.claude), CC_SESSIONS_STATE (where queued messages are kept; default
$XDG_STATE_HOME/claude-code-sessions, else ~/.local/state/claude-code-sessions).

Queued follow-ups. `send` to a session that is mid-turn does not interrupt
it and does not refuse: it appends the message to a small per-session queue
file and returns at once. A detached watcher process (its own session, so it
outlives the caller) waits until the turn ends, delivers the next message the
same way an idle `send` does, waits for that turn to end, and repeats, so
messages arrive in order, one per turn. "Mid-turn" is the live process's
`status` of `busy` in `claude agents --json`, read twice 5 s apart; `state`
"working" alone also covers a session idle between steps it drives itself
(a wait on CI), which counts as a turn boundary. The watcher exits
when the queue is empty. Each message is attempted once; a failure is
recorded, never retried. If the watcher dies (reboot, killed), its messages
are not resent later: a pending message whose watcher has been gone for more
than 10 minutes is marked `expired`, and one caught mid-delivery is marked
`unknown`. A pending message also expires after --expire-after minutes
(default 720). `queue` lists and cancels them; `status` shows them.

Claude Code has no supported command-line way to queue into a running
session. The input box queue belongs to the interactive screen (`claude
attach`, agent view peek reply). Cross-session messaging (a session's inbox
socket) is documented, but it arrives as a message from another session,
not from the user, mid-turn, and a session in bypass mode holds it for the
user's approval. So the helper waits for the turn boundary instead.

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
import contextlib
import fcntl
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
STATE = os.environ.get("CC_SESSIONS_STATE") or os.path.join(
    os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state"),
    "claude-code-sessions")
WATCHER_GONE = 600      # s without a watcher heartbeat before its messages expire
TURN_GRACE = 120        # s to wait for a delivered message's turn to show up
KEEP_FINISHED = 20      # finished queue entries kept per session for `queue`
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


def mid_turn(s):
    """True while a turn is running. A live process reports `status` busy,
    waiting or idle; `state` "working" also covers a session sitting idle
    between steps it drives itself (a wait on CI, a /loop), which is a turn
    boundary like any other."""
    if not s.get("pid"):
        return False
    if s.get("status"):
        return s["status"] == "busy"
    return state_of(s)[0] == "working"


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
        "queued": len([i for i in load_queue(s["id"])["items"] if i["status"] == "pending"])
        if os.path.exists(qpath(s["id"])) else 0,
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
        if r["queued"]:
            print(f"          {r['queued']} queued message(s) waiting for this turn to end")
        print(f"          {r['cwd']}")


def cmd_status(a):
    s = find(a.ref)
    key = queue_key_for(s["id"])
    ensure_watcher(key)
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
        "queue": queue_view(key) if os.path.exists(qpath(key)) else None,
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
    if row["queue"] and row["queue"]["items"]:
        print_queue(row["queue"])
    if last_text:
        print("last message:")
        print(last_text[-1500:])


class DeliveryError(Exception):
    pass


def deliver(s, message):
    """Pause the session if it has a process, then continue it with MESSAGE.

    Returns the id to follow and whether the new turn was seen starting."""
    if s.get("pid"):
        code, out, err = run([CLAUDE, "stop", s["id"]])
        if code != 0:
            raise DeliveryError(f"Could not pause {s['id']} to deliver the message: {err or out}")
    tl = os.path.join(job_dir(s["id"]), "timeline.jsonl")
    before = len(read_jsonl(tl))
    # No other flags: the session keeps its own saved options, and any flag here
    # would make the CLI start a copy instead of continuing this session.
    code, out, err = run([CLAUDE, "--bg", "--resume", s["sessionId"], message],
                         cwd=s.get("cwd") or None, timeout=90)
    text = (out + "\n" + err).strip()
    m = re.search(r"backgrounded\s*\S\s*([0-9a-f]{8})", text)
    if code != 0 or not m:
        raise DeliveryError(f"Claude Code did not accept the message (exit {code}):\n{text}")
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
    return {"id": new, "continued": new == s["id"], "turn_started": started,
            "timeline_before": before,
            "note": "" if new == s["id"] else
            f"The CLI started a copy of {s['id']} as {new}; follow {new} from now on."}


# Queued follow-ups. One JSON file per session under STATE:
# {"id", "target", "watcher_pid", "watcher_seen", "last_delivery", "items"}.
# `target` is the id messages go to; it moves when the CLI starts a copy.
# Item status: pending -> delivering -> delivered | failed, or expired,
# cancelled, unknown (the watcher died mid-delivery, so it may have landed).

def qpath(key, ext=".json"):
    return os.path.join(STATE, key + ext)


@contextlib.contextmanager
def queue_lock(key):
    os.makedirs(STATE, mode=0o700, exist_ok=True)
    fd = os.open(qpath(key, ".lock"), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def load_queue(key):
    q = read_json(qpath(key)) or {}
    q.setdefault("id", key)
    q.setdefault("items", [])
    return q


def save_queue(q):
    live = [i for i in q["items"] if i["status"] in ("pending", "delivering")]
    done = [i for i in q["items"] if i not in live][-KEEP_FINISHED:]
    q["items"] = sorted(done + live, key=lambda i: i["n"])
    tmp = qpath(q["id"], ".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    os.replace(tmp, qpath(q["id"]))


def live_items(q):
    return [i for i in q["items"] if i["status"] in ("pending", "delivering")]


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def pid_alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def queue_key_for(sid):
    """The queue that delivers to SID: its own, or one whose messages moved to
    SID when the CLI started a copy."""
    if os.path.exists(qpath(sid)):
        return sid
    paths = sorted(glob.glob(os.path.join(STATE, "*.json")), key=os.path.getmtime, reverse=True)
    for path in paths:
        q = read_json(path) or {}
        if q.get("target") == sid and q.get("id"):
            return q["id"]
    return sid


def reconcile(key):
    """Settle a queue whose watcher is gone. Returns True when a watcher must
    be started for messages that are still current."""
    if not os.path.exists(qpath(key)):
        return False
    with queue_lock(key):
        q = load_queue(key)
        live = live_items(q)
        if not live or pid_alive(q.get("watcher_pid")):
            return False
        seen = q.get("watcher_seen") or max(i["queued_ts"] for i in live)
        gone = time.time() - seen > WATCHER_GONE
        for i in live:
            if i["status"] == "delivering":
                i.update(status="unknown", finished=now_iso(),
                         error="The watcher stopped during delivery, so it may or may not "
                               "have arrived. Check `status` before sending it again.")
            elif gone:
                i.update(status="expired", finished=now_iso(),
                         error="The delivery watcher stopped (computer restarted or the "
                               "process was killed) and the message is too old to send now.")
        save_queue(q)
        return any(i["status"] == "pending" for i in q["items"])


def spawn_watcher(key):
    os.makedirs(STATE, mode=0o700, exist_ok=True)
    with open(qpath(key, ".log"), "a", encoding="utf-8") as log:
        p = subprocess.Popen([sys.executable, os.path.abspath(__file__), "_watch", key],
                             stdin=subprocess.DEVNULL, stdout=log, stderr=log, cwd=STATE,
                             start_new_session=True, close_fds=True)
    for _ in range(20):  # until it has registered, so `queue` right after is accurate
        if (read_json(qpath(key)) or {}).get("watcher_pid") == p.pid or p.poll() is not None:
            break
        time.sleep(0.1)


def ensure_watcher(key):
    if reconcile(key):
        spawn_watcher(key)


def enqueue(key, sid, message, expire_after):
    with queue_lock(key):
        q = load_queue(key)
        q.setdefault("target", sid)
        n = max([i["n"] for i in q["items"]] or [0]) + 1
        q["items"].append({"n": n, "message": message, "status": "pending",
                           "queued": now_iso(), "queued_ts": time.time(),
                           "expires_ts": time.time() + expire_after * 60})
        save_queue(q)
        position = len(live_items(q))
        alive = pid_alive(q.get("watcher_pid"))
    if not alive:
        spawn_watcher(key)
    return n, position


def lookup(sid):
    """The session record for SID, or None if it is gone. Asks the live list
    first (one CLI call), the full list only when the process is gone. A CLI
    failure exits via die(), which the watcher catches and retries."""
    for include_done in (False, True):
        for s in sessions(include_done=include_done):
            if s["id"] == sid:
                return s
    return None


def watch(key):
    """Detached delivery loop for one session's queue (`_watch KEY`)."""
    os.makedirs(STATE, mode=0o700, exist_ok=True)
    lock_fd = os.open(qpath(key, ".watcher"), os.O_CREAT | os.O_RDWR, 0o600)
    for _ in range(10):
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            time.sleep(0.3)
    else:
        return  # another watcher owns this queue

    def log(msg):
        print(f"{now_iso()} [{key}] {msg}", flush=True)

    with queue_lock(key):
        q = load_queue(key)
        q["watcher_pid"], q["watcher_seen"] = os.getpid(), time.time()
        save_queue(q)
    log("watcher started")
    cli_errors, last_check, quiet = 0, 0.0, 0
    while True:
        with queue_lock(key):
            q = load_queue(key)
            q["watcher_seen"] = time.time()
            for i in q["items"]:
                if i["status"] == "pending" and time.time() > i.get("expires_ts", 1e18):
                    i.update(status="expired", finished=now_iso(),
                             error="The session stayed busy past --expire-after.")
            pending = [i for i in q["items"] if i["status"] == "pending"]
            if not pending:
                q["watcher_pid"] = None
                save_queue(q)
                # Let go while the queue lock is still held: a concurrent `send`
                # either queued before this check (and we saw it), or sees no
                # watcher afterwards and starts one that can take the lock.
                os.close(lock_fd)
                log("queue empty, watcher exiting")
                return
            save_queue(q)
            item, target = pending[0], q.get("target") or key
            last = q.get("last_delivery") or {}
        # Cheap check first: state.json. Ask the CLI when that says the turn
        # is over, else every 15 s: "working" there also covers a process that
        # sits idle between its own steps, or one that died mid-turn.
        st = read_json(os.path.join(job_dir(target), "state.json")) or {}
        if st.get("state") == "working" and time.time() - last_check < 15:
            time.sleep(5)
            continue
        last_check = time.time()
        why = f"Session {target} no longer exists."
        try:
            s = lookup(target)
            cli_errors = 0
        except SystemExit:
            cli_errors += 1
            if cli_errors < 20:
                time.sleep(15)
                continue
            s, why = None, "`claude agents` kept failing; see the watcher log."
        if s is None:
            with queue_lock(key):
                q = load_queue(key)
                for i in q["items"]:
                    if i["status"] == "pending":
                        i.update(status="failed", finished=now_iso(), error=why)
                save_queue(q)
            log(why)
            continue
        state, _ = state_of(s)
        # The previous queued message's turn must have shown up before the
        # next one goes, so two messages never land in one turn.
        seen_turn = True
        if last.get("target") == target:
            grown = len(read_jsonl(os.path.join(job_dir(target), "timeline.jsonl"))) \
                > last.get("timeline_before", 0)
            seen_turn = grown or time.time() - last.get("at_ts", 0) > TURN_GRACE
        # Two quiet readings in a row, so a brief idle moment between a turn's
        # steps is not taken for its end.
        quiet = 0 if mid_turn(s) or not seen_turn else quiet + 1
        if quiet < 2:
            if quiet:
                last_check = 0.0  # take the second reading on the next pass
            time.sleep(5)
            continue
        quiet = 0
        with queue_lock(key):
            q = load_queue(key)
            cur = next((i for i in q["items"] if i["n"] == item["n"]), None)
            if cur is None or cur["status"] != "pending":
                continue  # cancelled meanwhile
            cur.update(status="delivering", started=now_iso(), session_state=state)
            save_queue(q)
        log(f"delivering #{item['n']} to {target} (state {state})")
        r, err = None, None
        try:
            r = deliver(s, item["message"])
        except DeliveryError as e:
            err = str(e)
        except SystemExit:
            err = "The Claude Code CLI did not answer; see the watcher log."
        with queue_lock(key):
            q = load_queue(key)
            cur = next(i for i in q["items"] if i["n"] == item["n"])
            if r:
                cur.update(status="delivered", finished=now_iso(), delivered_to=r["id"],
                           turn_started=r["turn_started"], note=r["note"])
                q["target"] = r["id"]
                q["last_delivery"] = {"target": r["id"], "at_ts": time.time(),
                                      "timeline_before": r["timeline_before"]}
            else:
                cur.update(status="failed", finished=now_iso(), error=err)
            save_queue(q)
        log(f"#{item['n']} " + (f"delivered to {r['id']}" if r else f"failed: {err}"))


def queue_view(key, recent=5):
    q = load_queue(key)
    live = live_items(q)
    rows = []
    for i in [i for i in q["items"] if i not in live][-recent:] + live:
        row = {k: i[k] for k in ("n", "status", "queued", "finished", "delivered_to",
                                  "error", "note") if i.get(k)}
        row["message"] = one_line(i["message"], 120)
        rows.append(row)
    return {"id": key, "target": q.get("target") or key,
            "watcher_running": pid_alive(q.get("watcher_pid")),
            "pending": sum(1 for i in live if i["status"] == "pending"), "items": rows}


def cmd_send(a):
    s = find(a.ref)
    key = queue_key_for(s["id"])
    ensure_watcher(key)
    busy = mid_turn(s)
    earlier = live_items(load_queue(key))
    if not a.force and (busy or earlier):
        if a.no_queue:
            die(f"{s['id']} is still working. Wait for it (`wait {s['id']}`), send without "
                "--no-queue to queue the message, or pass --force to interrupt the "
                "current turn.", 4)
        n, pos = enqueue(key, s["id"], a.message, a.expire_after)
        why = "is mid-turn" if busy else "has earlier queued messages"
        print(json.dumps({"id": s["id"], "queued": True, "position": pos, "item": n,
                          "note": f"{s['id']} {why}. The message goes in when the current "
                                  "turn ends, without interrupting it. "
                                  f"`queue {s['id']}` shows it; `queue {s['id']} --clear` "
                                  "cancels."}, indent=1))
        return
    try:
        r = deliver(s, a.message)
    except DeliveryError as e:
        die(str(e))
    r.pop("timeline_before")
    r["queued"] = False
    print(json.dumps(r, indent=1))


def cmd_queue(a):
    s = find(a.ref)
    key = queue_key_for(s["id"])
    ensure_watcher(key)
    if a.clear:
        if not os.path.exists(qpath(key)):
            print(json.dumps({"id": key, "cancelled": 0, "note": ""}, indent=1))
            return
        with queue_lock(key):
            q = load_queue(key)
            n = 0
            for i in q["items"]:
                if i["status"] == "pending":
                    i.update(status="cancelled", finished=now_iso())
                    n += 1
            save_queue(q)
            busy = [i["n"] for i in live_items(q)]
        print(json.dumps({"id": key, "cancelled": n,
                          "note": f"#{busy[0]} is being delivered right now and cannot be "
                                  "cancelled." if busy else ""}, indent=1))
        return
    v = queue_view(key)
    if a.json:
        print(json.dumps(v, indent=1, ensure_ascii=False))
        return
    if not v["items"]:
        print(f"No queued messages for {key}.")
        return
    print_queue(v)


def print_queue(v):
    print(f"queue: {v['pending']} pending, watcher "
          f"{'running' if v['watcher_running'] else 'not running'}"
          + (f", delivering to {v['target']}" if v["target"] != v["id"] else ""))
    for i in v["items"]:
        to = f" -> {i['delivered_to']}" if i.get("delivered_to") else ""
        print(f"  #{i['n']} {i['status']:<10} {i.get('finished') or i.get('queued')}{to}  {i['message']}")
        if i.get("error") or i.get("note"):
            print(f"      {i.get('error') or i.get('note')}")


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
    if sys.argv[1:2] == ["_watch"] and len(sys.argv) == 3:
        watch(sys.argv[2])  # the detached delivery process spawned by `send`
        return
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
    how = sd.add_mutually_exclusive_group()
    how.add_argument("--force", action="store_true",
                     help="interrupt the current turn and deliver now")
    how.add_argument("--no-queue", action="store_true",
                     help="refuse (exit 4) instead of queueing while the session works")
    sd.add_argument("--expire-after", type=int, default=720, metavar="MINUTES",
                    help="drop a queued message not delivered within this time (default 720)")
    qu = sub.add_parser("queue", help="show or cancel queued follow-up messages")
    qu.add_argument("ref")
    qu.add_argument("--clear", action="store_true", help="cancel every pending message")
    qu.add_argument("--json", action="store_true")
    wt = sub.add_parser("wait")
    wt.add_argument("ref")
    wt.add_argument("--timeout", type=int, default=150)
    sp = sub.add_parser("stop")
    sp.add_argument("ref")
    a = p.parse_args()
    if a.cmd == "start" and a.prompt[:1] == ["--"]:
        a.prompt = a.prompt[1:]
    {"start": cmd_start, "list": cmd_list, "status": cmd_status, "send": cmd_send,
     "queue": cmd_queue, "wait": cmd_wait, "stop": cmd_stop}[a.cmd](a)


if __name__ == "__main__":
    main()
