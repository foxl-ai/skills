#!/usr/bin/env python3
"""Start, inspect, follow up on and stop Google Antigravity CLI (`agy`) tasks.

agy 1.5.x has no native detached/background session and no command that lists
sessions. This helper therefore runs the documented headless mode
(`agy --print=... --output-format stream-json`) under a small detached runner
that records the event stream, stderr, a per-turn agy log and the exit status.

A "session" here is one agy conversation. A follow-up (`send`) starts a NEW agy
process with the documented `--conversation <uuid>` flag, from the session's
recorded folder, after the previous turn ended. agy cannot take a message while
a headless turn is running, so `send` refuses then (mid-turn send is
unsupported). agy silently starts a different conversation when the id is not
found, so the runner aborts a follow-up the moment agy reports another
conversation id or another folder, and never adopts the replacement.

Standard library only. Python 3.8+. macOS and Linux only.

  agy_sessions.py spawn  --cwd DIR [--name N] [--worktree | --no-worktree]
                         [--mode auto|accept-edits|plan] [--model M] [--effort E]
                         [--sandbox] [--print-timeout DUR] -- TASK      (alias: start)
  agy_sessions.py send   REF MESSAGE [--request-id KEY] [--allow-stopped]
  agy_sessions.py list   [--all] [--json]
  agy_sessions.py status REF [--json]
  agy_sessions.py wait   REF [--timeout SECONDS]
  agy_sessions.py stop   REF
  agy_sessions.py doctor [REF] [--live] [--json]

REF is the exact session id, a unique id prefix of at least 6 characters, the
exact agy conversation UUID, or an exact unique name. Ambiguous refs are refused.

Environment: AGY_BIN (default `agy` on PATH, else ~/.local/bin/agy),
AGY_SESSIONS_STATE (default $XDG_STATE_HOME/agy-sessions or
~/.local/state/agy-sessions), AGY_DATA_DIR (agy's data folder, default
~/.gemini/antigravity-cli; read only, used to pre-check that a conversation
exists before a follow-up).

Exit codes: 0 ok, 1 error, 2 unsupported or invalid request, 4 refused,
5 outcome unknown.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
import uuid

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None

HOME = os.path.expanduser("~")
STATE = os.environ.get("AGY_SESSIONS_STATE") or os.path.join(
    os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local", "state"), "agy-sessions")
AGY_DATA = os.environ.get("AGY_DATA_DIR") or os.path.join(HOME, ".gemini", "antigravity-cli")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
SID_RE = re.compile(r"^\d{10}-[0-9a-f]{6}$")
NOT_FOUND_RE = re.compile(r'conversation "([^"]*)" not found')
MARK_RE = re.compile(r"^\s*(result|needs input|failed):", re.I)
MODES = ("auto", "accept-edits", "plan")
REQUIRED_FLAGS = ("--print", "--output-format", "--conversation", "--print-timeout", "--log-file")
MAX_PROMPT = 200000
ACTIVE = ("starting", "working")
STOP_GRACE = 15

CAPABILITIES = {
    "native_background_sessions": False,
    "native_session_list": False,
    "detached_runner": True,
    "same_conversation_followup": "after the turn ends: new `agy -p --conversation <uuid>` process "
                                  "from the recorded folder, aborted if agy reports another id or folder",
    "mid_turn_send": False,
    "answer_permission_prompts": False,
    "stop": "SIGINT to the verified agy process (agy's own interrupt path); SIGTERM only as escalation",
    "platforms": ["darwin", "linux"],
}

EXIT_ERR, EXIT_UNSUPPORTED, EXIT_REFUSED, EXIT_UNKNOWN = 1, 2, 4, 5


class Refusal(Exception):
    def __init__(self, code, message, exit_code=EXIT_REFUSED, **extra):
        super().__init__(message)
        self.code, self.message, self.exit_code, self.extra = code, message, exit_code, extra


def out(obj, code=0):
    print(json.dumps(obj, indent=1, ensure_ascii=False))
    sys.exit(code)


# ---------------------------------------------------------------- files

def ensure_private_dir(path):
    """Create or accept a directory only if it is ours, real and not group/world writable."""
    try:
        os.makedirs(path, mode=0o700, exist_ok=True)
        st = os.lstat(path)
    except OSError as e:
        raise Refusal("EPATH", f"Cannot use state folder {path}: {e}", EXIT_ERR)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise Refusal("EPATH", f"{path} is a link or not a folder; refusing to use it as state.", EXIT_ERR)
    if hasattr(os, "getuid") and st.st_uid != os.getuid():
        raise Refusal("EPATH", f"{path} is owned by another user; refusing to use it.", EXIT_ERR)
    if st.st_mode & 0o022:
        raise Refusal("EPATH", f"{path} is group or world writable; fix its permissions (chmod 700).", EXIT_ERR)
    return path


def state_root():
    ensure_private_dir(STATE)
    ensure_private_dir(os.path.join(STATE, "sessions"))
    return STATE


def sess_dir(sid):
    return os.path.join(STATE, "sessions", sid)


def turn_dir(sid, n):
    return os.path.join(sess_dir(sid), "turns", str(n))


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write_json(path, obj):
    tmp = "%s.%s.tmp" % (path, os.getpid())
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_session(sid):
    return read_json(os.path.join(sess_dir(sid), "session.json"))


def save_session(s):
    write_json(os.path.join(sess_dir(s["id"]), "session.json"), s)


class Lock:
    """Exclusive per-session lock so two helper commands never start two turns."""

    def __init__(self, sid, timeout=10.0):
        self.path, self.timeout, self.fd = os.path.join(sess_dir(sid), "lock"), timeout, None

    def __enter__(self):
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        deadline = time.time() + self.timeout
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.time() > deadline:
                    os.close(self.fd)
                    raise Refusal("EBUSY", "Another helper command is changing this session. Try again.")
                time.sleep(0.05)

    def __exit__(self, *exc):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)


# ---------------------------------------------------------------- processes

def proc(pid):
    """uid, state, start time and argv of a live process, or None."""
    try:
        pid = int(pid)
        r = subprocess.run(["ps", "-ww", "-o", "uid=,stat=,lstart=,command=", "-p", str(pid)],
                           capture_output=True, text=True, timeout=10)
    except (TypeError, ValueError, OSError, subprocess.TimeoutExpired):
        return None
    line = r.stdout.strip()
    parts = line.split(None, 7)
    if r.returncode != 0 or len(parts) < 8:
        return None
    try:
        return {"uid": int(parts[0]), "stat": parts[1], "lstart": " ".join(parts[2:7]), "command": parts[7]}
    except ValueError:
        return None


def identity(pid, marker):
    p = proc(pid)
    if not p:
        return None
    return {"pid": int(pid), "uid": p["uid"], "lstart": p["lstart"], "marker": marker}


def provably_gone(rec):
    """True when the recorded process is certainly not running as ours (exited or pid reused)."""
    if not rec or not rec.get("pid"):
        return True
    try:
        os.kill(int(rec["pid"]), 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return True  # another user's process now holds the pid
    except (OSError, ValueError):
        return False
    return proc(rec["pid"]) is not None and not identity_ok(rec)


def identity_ok(rec):
    """True only if the recorded pid is still the same process we started.

    Checks same user, same start time, the unique marker in its argv and not a zombie,
    so a reused pid or an unrelated process is never treated as ours.
    """
    if not rec or not rec.get("pid") or not rec.get("lstart") or not rec.get("marker"):
        return False
    p = proc(rec["pid"])
    return bool(p and p["uid"] == os.getuid() and p["lstart"] == rec["lstart"]
                and rec["marker"] in p["command"] and "Z" not in p["stat"])


# ---------------------------------------------------------------- agy

def agy_bin():
    configured = os.environ.get("AGY_BIN")
    if configured:
        found = shutil.which(configured)
        return os.path.abspath(found) if found else None
    found = shutil.which("agy")
    if found:
        return os.path.abspath(found)
    default = os.path.join(HOME, ".local", "bin", "agy")  # documented install location
    return default if os.access(default, os.X_OK) else None


def agy_probe(path):
    info = {"agy_bin": path, "version": None, "flags": {}, "supported": False}
    if not path:
        return info
    try:
        v = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=20,
                           stdin=subprocess.DEVNULL)
        h = subprocess.run([path, "--help"], capture_output=True, text=True, timeout=20,
                           stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as e:
        info["error"] = str(e)
        return info
    hits = re.findall(r"\d+\.\d+\.\d+[\w.+-]*", v.stdout)
    info["version"] = hits[0] if len(hits) == 1 else None
    text = h.stdout + h.stderr
    info["flags"] = {f: bool(re.search(r"(^|\s)%s(\s|$)" % re.escape(f), text, re.M)) for f in REQUIRED_FLAGS}
    info["supported"] = all(info["flags"].values())
    return info


def require_agy():
    path = agy_bin()
    if not path:
        raise Refusal("ENOAGY", "agy was not found. Install the Antigravity CLI "
                      "(https://antigravity.google/docs/getting-started?tab=cli) or set AGY_BIN.", 127)
    info = agy_probe(path)
    if not info["supported"]:
        missing = [f for f, ok in info["flags"].items() if not ok]
        raise Refusal("EUNSUPPORTED", "This agy (%s) lacks the headless flags this helper needs: %s. "
                      "Update agy at the computer (`agy update`); nothing was started."
                      % (info["version"] or "unknown version", ", ".join(missing) or "help unreadable"),
                      EXIT_UNSUPPORTED, agy=info)
    return path, info


def agy_argv(s, t, td):
    argv = [s["agy_bin"], "--print=" + t["prompt"], "--output-format", "stream-json",
            "--log-file=" + os.path.join(td, "agy.log")]
    if s.get("print_timeout"):
        argv.append("--print-timeout=" + s["print_timeout"])
    if s.get("mode"):
        argv.append("--mode=" + s["mode"])
    if s.get("model"):
        argv.append("--model=" + s["model"])
    if s.get("effort"):
        argv.append("--effort=" + s["effort"])
    if s.get("sandbox"):
        argv.append("--sandbox")
    if t.get("expected_conversation_id"):
        argv.append("--conversation=" + t["expected_conversation_id"])
    return argv


def conversation_known(cid):
    """False only when agy's local conversation store exists and lacks this id."""
    store = os.path.join(AGY_DATA, "conversations")
    if not os.path.isdir(store):
        return None
    return os.path.exists(os.path.join(store, cid + ".db"))


# ---------------------------------------------------------------- runner

def runner_main(sid, n, nonce):
    """Detached supervisor for one turn. Never prints; records everything to files."""
    os.umask(0o077)
    td = turn_dir(sid, n)
    state = {"p": None, "stop": False, "guard": None, "cid": None, "escalated": False}
    lock = threading.Lock()

    def escalate(p):
        deadline = time.time() + STOP_GRACE
        while p.poll() is None and time.time() < deadline:
            time.sleep(0.2)
        if p.poll() is None:
            state["escalated"] = True
            try:
                p.terminate()
            except OSError:
                pass

    def interrupt():
        with lock:
            p = state["p"]
            state["stop"] = True
            if p is None or p.poll() is not None:
                return
            try:
                p.send_signal(signal.SIGINT)
            except OSError:
                return
        threading.Thread(target=escalate, args=(p,), daemon=True).start()

    def trip(code, detail):
        with lock:
            if state["guard"]:
                return
            state["guard"] = dict(detail, code=code, at=time.time())
        interrupt()

    # Handlers first: a stop that arrives as soon as runner.json exists must never kill the runner.
    signal.signal(signal.SIGTERM, lambda *_: interrupt())
    signal.signal(signal.SIGINT, lambda *_: interrupt())
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    s, t = load_session(sid), read_json(os.path.join(td, "turn.json"))
    me = identity(os.getpid(), nonce) or {"pid": os.getpid(), "marker": nonce}
    rinfo = {"runner": me, "agy": None, "started": time.time()}
    write_json(os.path.join(td, "runner.json"), rinfo)

    expected = t.get("expected_conversation_id")
    want_cwd = os.path.realpath(s["cwd"])

    def on_event(ev):
        if not isinstance(ev, dict):
            return
        body = ev.get(ev.get("event")) if isinstance(ev.get(ev.get("event")), dict) else {}
        cid = ev.get("conversation_id") or body.get("conversation_id")
        if ev.get("event") == "init":
            cwd = body.get("cwd")
            if cwd and os.path.realpath(cwd) != want_cwd:
                trip("ECWD", {"expected_cwd": want_cwd, "reported_cwd": cwd})
        if not cid:
            return
        if expected and cid != expected:
            trip("EREPLACED", {"expected": expected, "stray_conversation_id": cid})
        elif state["cid"] is None:
            state["cid"] = cid
            if not expected:
                record_conversation(sid, cid)
        elif cid != state["cid"]:
            trip("ECHANGED", {"first": state["cid"], "stray_conversation_id": cid})

    events = open(os.path.join(td, "events.jsonl"), "wb")
    errlog = open(os.path.join(td, "stderr.log"), "wb")
    exit_rec = {"code": None, "signal": None, "result": None}
    session = load_session(sid) or {}
    if session.get("stopped_turn") == n or state["stop"]:
        exit_rec.update(code=None, note="stopped before agy started")
    else:
        try:
            env = dict(os.environ, PWD=s["cwd"])
            p = subprocess.Popen(agy_argv(s, t, td), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, cwd=s["cwd"], env=env)
        except OSError as e:
            p = None
            exit_rec.update(code=127, error=str(e))
        if p is not None:
            with lock:
                state["p"] = p
                stop_now = state["stop"]
            rinfo["agy"] = identity(p.pid, os.path.join(td, "agy.log")) or {"pid": p.pid}
            write_json(os.path.join(td, "runner.json"), rinfo)
            if stop_now:
                interrupt()

            def pump_err():
                for raw in iter(p.stderr.readline, b""):
                    errlog.write(raw)
                    errlog.flush()
                    m = NOT_FOUND_RE.search(raw.decode("utf-8", "replace"))
                    if m and expected:
                        trip("EREPLACED", {"expected": expected, "agy_said": m.group(0)})

            te = threading.Thread(target=pump_err, daemon=True)
            te.start()
            result = None
            for raw in iter(p.stdout.readline, b""):
                events.write(raw)
                events.flush()
                try:
                    ev = json.loads(raw.decode("utf-8", "replace"))
                except ValueError:
                    continue
                on_event(ev)
                if isinstance(ev, dict) and ev.get("event") == "result":
                    result = ev.get("result") or {}
            code = p.wait()
            te.join(timeout=5)
            exit_rec.update(code=code, signal=-code if code < 0 else None, result=summarize(result))
    events.close()
    errlog.close()
    exit_rec.update(ended=time.time(), guard=state["guard"], escalated=state["escalated"],
                    stop_requested=state["stop"])
    write_json(os.path.join(td, "exit.json"), exit_rec)


def summarize(r):
    if r is None:
        return None
    keys = ("conversation_id", "status", "finished_reason", "error", "denied_actions", "num_turns",
            "duration_seconds", "structured_output")
    out_ = {k: r[k] for k in keys if k in r}
    out_["response"] = (r.get("response") or "")[-8000:]
    return out_


def record_conversation(sid, cid):
    with Lock(sid, timeout=30):
        s = load_session(sid)
        if s is not None and not s.get("conversation_id"):
            s["conversation_id"] = cid
            save_session(s)


def launch(s, n):
    """Start the detached runner for turn n and wait briefly for it to record itself."""
    nonce = "agy-sessions-runner-" + uuid.uuid4().hex
    td = turn_dir(s["id"], n)
    errf = os.fdopen(os.open(os.path.join(td, "runner.err"), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600), "ab")
    try:
        subprocess.Popen([sys.executable, "-I", os.path.abspath(__file__), "_run", s["id"], str(n), nonce],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=errf,
                         cwd=s["cwd"], start_new_session=True, close_fds=True)
    except OSError as e:
        write_json(os.path.join(td, "exit.json"), {"code": 127, "error": "runner failed: %s" % e,
                                                     "ended": time.time()})
        return False
    finally:
        errf.close()
    deadline = time.time() + 10
    while time.time() < deadline:
        r = read_json(os.path.join(td, "runner.json"))
        if r and (r.get("runner") or {}).get("marker") == nonce:
            return True
        time.sleep(0.1)
    return False


# ---------------------------------------------------------------- state

def turn_state(s, n):
    """Return (state, detail). Never claims working or done beyond what files and processes prove."""
    td = turn_dir(s["id"], n)
    ex = read_json(os.path.join(td, "exit.json"))
    if ex:
        return exit_state(s, n, ex, td)
    r = read_json(os.path.join(td, "runner.json"))
    if r and (identity_ok(r.get("agy")) or identity_ok(r.get("runner"))):
        return "working", None
    ex = read_json(os.path.join(td, "exit.json"))  # the runner may have finished between the two reads
    if ex:
        return exit_state(s, n, ex, td)
    t = read_json(os.path.join(td, "turn.json")) or {}
    if not r and time.time() - t.get("created", 0) < 20:
        return "starting", None
    return "lost", "ended without a recorded exit; its process is gone or is no longer the one started"


def exit_state(s, n, ex, td):
    if ex:
        res = ex.get("result") or {}
        if ex.get("guard"):
            return "refused", ex["guard"]
        stopped = s.get("stopped_turn") == n
        if stopped and (res.get("finished_reason") == "interrupted" or ex.get("code") != 0 or not res):
            return "stopped", None
        if ex.get("code") == 3 or res.get("finished_reason") == "print_timeout":
            return "timed-out", res.get("error")
        if ex.get("code") == 0 and res.get("status") == "SUCCESS":
            if res.get("denied_actions"):
                return "denied", res.get("denied_actions")
            return "done", None
        if res.get("finished_reason") == "interrupted":
            return "interrupted", res.get("error")
        return "failed", res.get("error") or ex.get("error") or stderr_tail(td) or "exit %s" % ex.get("code")


def session_state(s):
    return turn_state(s, s["turns"])


def stderr_tail(td, n=600):
    try:
        with open(os.path.join(td, "stderr.log"), encoding="utf-8", errors="replace") as f:
            return " ".join(f.read()[-n:].split())
    except OSError:
        return ""


def turn_events(td):
    evs = []
    try:
        with open(os.path.join(td, "events.jsonl"), encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    evs.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return evs


def response_text(td):
    ex = read_json(os.path.join(td, "exit.json")) or {}
    res = ex.get("result") or {}
    if res.get("response"):
        return res["response"].strip()
    chunks = {}
    for ev in turn_events(td):
        su = ev.get("step_update") or {}
        if su.get("step_type") == "agent_response" and su.get("text_delta"):
            chunks.setdefault(su.get("step_index"), []).append(su["text_delta"])
    if not chunks:
        return ""
    return "".join(chunks[max(chunks, key=lambda k: k or 0)]).strip()


def headline(text):
    marks = [l.strip() for l in text.splitlines() if MARK_RE.match(l)]
    if marks:
        return marks[-1]
    lines = [l for l in text.splitlines() if l.strip()]
    return one_line(lines[-1]) if lines else ""


def one_line(text, n=160):
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def activity(td, n=8):
    acts = []
    for ev in turn_events(td):
        su = ev.get("step_update") or {}
        if su.get("step_type") != "tool" or su.get("state") not in ("DONE", "ERROR"):
            continue
        info = su.get("tool_info") or {}
        params = info.get("parameters") or {}
        arg = params.get("CommandLine") or params.get("Path") or params.get("TargetFile") or ""
        line = "%s %s" % (su.get("tool_name") or info.get("name"), one_line(str(arg), 100))
        if su.get("state") == "ERROR":
            line += " -> error: " + one_line((info.get("error") or {}).get("message", ""), 120)
        acts.append(line.strip())
    return acts[-n:]


def ago(ts):
    sec = max(0, int(time.time() - (ts or time.time())))
    for unit, k in (("d", 86400), ("h", 3600), ("m", 60)):
        if sec >= k:
            return "%d%s ago" % (sec // k, unit)
    return "%ds ago" % sec


def git(args, cwd, timeout=30):
    try:
        r = subprocess.run(["git", "-C", cwd] + args, capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def git_summary(s):
    cwd = s.get("cwd")
    if not cwd or not os.path.isdir(cwd) or not shutil.which("git"):
        return None
    code, outp, _ = git(["status", "--porcelain=v1", "-b"], cwd)
    if code:
        return None
    lines = outp.splitlines()
    info = {"branch": lines[0][3:] if lines else "", "uncommitted_files": max(0, len(lines) - 1)}
    code, log, _ = git(["log", "--format=%h %s", "%s..HEAD" % s["base"]] if s.get("base")
                       else ["log", "-3", "--format=%h %s"], cwd)
    if not code:
        info["commits" if s.get("base") else "recent_commits"] = log.splitlines()[:20]
    return info


# ---------------------------------------------------------------- lookup

def all_sessions():
    root = os.path.join(STATE, "sessions")
    if not os.path.isdir(root):
        return []
    found = []
    for sid in os.listdir(root):
        if SID_RE.match(sid):
            s = load_session(sid)
            if s and s.get("id") == sid:
                found.append(s)
    return sorted(found, key=lambda s: s.get("created", 0), reverse=True)


def find(ref):
    ref = (ref or "").strip()
    if not ref:
        raise Refusal("ETARGET", "Give a session id, conversation id or name.", EXIT_UNSUPPORTED)
    sessions = all_sessions()
    exact = [s for s in sessions if s["id"] == ref]
    if exact:
        return exact[0]
    hits = {}
    for s in sessions:
        if len(ref) >= 6 and s["id"].startswith(ref):
            hits[s["id"]] = s
        if s.get("conversation_id") and (s["conversation_id"] == ref.lower()
                                         or (len(ref) >= 8 and s["conversation_id"].startswith(ref.lower()))):
            hits[s["id"]] = s
        if s.get("name") and s["name"].lower() == ref.lower():
            hits[s["id"]] = s
    if len(hits) == 1:
        return next(iter(hits.values()))
    if not hits:
        hint = " Prefixes need at least 6 characters." if len(ref) < 6 else ""
        raise Refusal("ENOTFOUND", "No agy session matches %r.%s Run `list --all`." % (ref, hint))
    raise Refusal("EAMBIGUOUS", "%r matches several sessions; use the exact id." % ref,
                  matches=[{"id": s["id"], "name": s.get("name"), "cwd": s.get("cwd")} for s in hits.values()])


# ---------------------------------------------------------------- commands

def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:40].strip("-")
    return slug or "task"


def check_prompt(text):
    text = (text or "").strip()
    if not text:
        raise Refusal("EMESSAGE", "The message is empty.", EXIT_UNSUPPORTED)
    if "\x00" in text or len(text) > MAX_PROMPT:
        raise Refusal("EMESSAGE", "The message has a NUL byte or is longer than %d characters." % MAX_PROMPT,
                      EXIT_UNSUPPORTED)
    return text


def new_session_dir():
    ensure_private_dir(os.path.join(STATE, "sessions"))
    for _ in range(20):
        sid = time.strftime("%m%d%H%M%S") + "-" + os.urandom(3).hex()
        try:
            os.mkdir(sess_dir(sid), 0o700)
            return sid
        except FileExistsError:
            time.sleep(0.01)
    raise Refusal("ECOLLISION", "Could not reserve a unique session id.", EXIT_ERR)


def create_worktree(top, branch, path):
    """git worktree add on a NEW branch at a NEW path. Never reuses or overwrites either."""
    if os.path.lexists(path):
        raise Refusal("ECOLLISION", "Worktree path %s already exists; nothing was changed." % path, EXIT_ERR)
    if git(["show-ref", "--verify", "--quiet", "refs/heads/" + branch], top)[0] == 0:
        raise Refusal("ECOLLISION", "Branch %s already exists; nothing was changed." % branch, EXIT_ERR)
    code, base, err = git(["rev-parse", "--verify", "HEAD^{commit}"], top)
    if code:
        raise Refusal("EISOLATION", "The repository has no commit to branch from. Commit first, or pass "
                      "--no-worktree to let agy edit the folder itself.", EXIT_UNSUPPORTED)
    code, _, err = git(["worktree", "add", "-b", branch, path, base], top, timeout=300)
    if code:
        raise Refusal("EISOLATION", "git worktree add failed: %s" % err, EXIT_ERR)
    return base


def cmd_spawn(a):
    state_root()
    path, info = require_agy()
    task = check_prompt(" ".join(a.task))
    origin = os.path.realpath(os.path.expanduser(a.cwd))
    if not os.path.isdir(origin):
        raise Refusal("ECWD", "No such folder: %s" % origin, EXIT_UNSUPPORTED)
    has_git = bool(shutil.which("git"))
    code, top, _ = git(["rev-parse", "--show-toplevel"], origin) if has_git else (1, "", "")
    in_git = code == 0 and bool(top)
    warnings = []
    if not in_git and not a.no_worktree:
        raise Refusal("EISOLATION", "%s is not inside a git repository, so agy cannot get its own worktree "
                      "and branch. Pass --no-worktree to let agy edit this folder in place (no isolation)."
                      % origin, EXIT_UNSUPPORTED)
    if a.worktree and a.no_worktree:
        raise Refusal("EUSAGE", "Choose either --worktree or --no-worktree.", EXIT_UNSUPPORTED)
    sid = new_session_dir()
    name = (a.name or "").strip()
    s = {"v": 1, "id": sid, "name": name, "origin": origin, "repo": top if in_git else None,
         "cwd": origin, "worktree": None, "branch": None, "base": None, "isolation": "none",
         "agy_bin": path, "agy_version": info["version"], "mode": a.mode, "model": a.model,
         "effort": a.effort, "sandbox": bool(a.sandbox), "print_timeout": a.print_timeout,
         "conversation_id": None, "created": time.time(), "turns": 1, "stopped_turn": None}
    try:
        if in_git and not a.no_worktree:
            top = os.path.realpath(top)
            prefix = os.path.relpath(origin, top)
            slug = slugify(name or task[:60])
            branch = "agy/%s-%s" % (slug, sid)
            wt_root = ensure_private_dir(os.path.join(STATE, "worktrees"))
            wt = os.path.join(wt_root, "%s-%s" % (slug, sid))
            dirty = git(["status", "--porcelain"], top)[1]
            if dirty:
                warnings.append("The folder has uncommitted changes; they are NOT in the new worktree.")
            s["base"] = create_worktree(top, branch, wt)
            run_cwd = os.path.realpath(os.path.join(wt, prefix)) if prefix != "." else os.path.realpath(wt)
            os.makedirs(run_cwd, exist_ok=True)
            s.update(worktree=os.path.realpath(wt), branch=branch, cwd=run_cwd, isolation="worktree")
        elif in_git:
            warnings.append("--no-worktree: agy edits %s directly, on its current branch." % origin)
        else:
            warnings.append("Not a git repository: agy edits %s in place with no isolation or undo." % origin)
    except Refusal:
        try:
            os.rmdir(sess_dir(sid))  # only our own empty reservation
        except OSError:
            pass
        raise
    os.makedirs(turn_dir(sid, 1), 0o700)
    write_json(os.path.join(turn_dir(sid, 1), "turn.json"),
               {"n": 1, "prompt": task, "created": time.time(), "kind": "spawn"})
    save_session(s)
    started = launch(s, 1)
    deadline = time.time() + 8
    while started and time.time() < deadline:
        cur = load_session(sid)
        st, _ = turn_state(cur, 1)
        if cur.get("conversation_id") or st not in ACTIVE:
            break
        time.sleep(0.25)
    cur = load_session(sid)
    st, detail = turn_state(cur, 1)
    res = {"ok": st not in ("failed", "refused", "lost"), "id": sid, "name": name, "state": st,
           "conversation_id": cur.get("conversation_id"), "cwd": cur["cwd"], "origin": origin,
           "isolation": cur["isolation"], "branch": cur["branch"], "worktree": cur["worktree"],
           "base": cur["base"], "agy_version": info["version"], "mode": a.mode or "agy default",
           "logs": turn_dir(sid, 1), "warnings": warnings}
    if detail:
        res["detail"] = detail
    if not started:
        res["warnings"].append("The runner did not confirm its start within 10 s; check `status`.")
    out(res, 0 if res["ok"] else EXIT_ERR)


def receipt_path(s, key):
    d = ensure_private_dir(os.path.join(sess_dir(s["id"]), "receipts"))
    return os.path.join(d, hashlib.sha256(key.encode()).hexdigest()[:40] + ".json")


def cmd_send(a):
    state_root()
    msg = check_prompt(a.message)
    s = find(a.ref)
    key = ("request-id:" + a.request_id) if a.request_id else \
        ("text:" + hashlib.sha256(msg.encode()).hexdigest())
    with Lock(s["id"]):
        s = load_session(s["id"])
        rp = receipt_path(s, key)
        old = read_json(rp)
        if old:
            code = 0 if old.get("outcome") == "accepted" else EXIT_UNKNOWN
            out({"ok": code == 0, "duplicate": True, "id": s["id"], "receipt": old,
                 "note": "Already handled; not sent again. Use a new --request-id only for a genuinely "
                         "new request."}, code)
        st, detail = session_state(s)
        if st in ACTIVE:
            raise Refusal("EBUSY", "Session %s is still working. agy headless mode cannot take a message "
                          "mid-turn (unsupported). Wait for the turn to end (`wait %s`), then send."
                          % (s["id"], s["id"]), state=st)
        if st == "stopped" and not a.allow_stopped:
            raise Refusal("ESTOPPED", "Session %s was stopped. Continue it only if the user explicitly asks; "
                          "then repeat with --allow-stopped." % s["id"], state=st)
        if st == "lost":
            r = read_json(os.path.join(turn_dir(s["id"], s["turns"]), "runner.json")) or {}
            if not (provably_gone(r.get("runner")) and provably_gone(r.get("agy"))):
                raise Refusal("EUNKNOWN", "Cannot prove the previous turn of %s has ended (its process could not "
                              "be checked). Not starting another turn on the same conversation." % s["id"],
                              EXIT_UNKNOWN, state=st)
        if st == "refused":
            raise Refusal("ETARGET", "The previous follow-up was aborted because agy reported a different "
                          "conversation or folder (%s). Not sending again; inspect `status %s`."
                          % (detail.get("code"), s["id"]), guard=detail)
        cid = s.get("conversation_id")
        if not cid or not UUID_RE.match(cid):
            raise Refusal("ETARGET", "Session %s has no recorded agy conversation id, so there is nothing to "
                          "continue. Start a new task instead." % s["id"], state=st)
        if not os.path.isdir(s["cwd"]):
            raise Refusal("ETARGET", "The session folder %s no longer exists; not recreating it." % s["cwd"])
        if conversation_known(cid) is False:
            raise Refusal("ETARGET", "agy's local store has no conversation %s, and agy would silently start "
                          "a new one. Not sending." % cid)
        if not os.path.exists(s["agy_bin"]):
            raise Refusal("ENOAGY", "The agy executable used by this session (%s) is gone." % s["agy_bin"], 127)
        n = s["turns"] + 1
        os.makedirs(turn_dir(s["id"], n), 0o700)
        write_json(os.path.join(turn_dir(s["id"], n), "turn.json"),
                   {"n": n, "prompt": msg, "created": time.time(), "kind": "send",
                    "request_id": a.request_id, "expected_conversation_id": cid})
        receipt = {"key_kind": key.split(":", 1)[0], "request_id": a.request_id,
                   "message_sha256": hashlib.sha256(msg.encode()).hexdigest(), "turn": n,
                   "conversation_id": cid, "outcome": "unknown", "at": time.time()}
        write_json(rp, receipt)  # saved before launching: a crash leaves "unknown", never a silent resend
        s["turns"] = n
        if a.allow_stopped:
            s["stopped_turn"] = None
        save_session(s)
        started = launch(s, n)
        receipt["outcome"] = "accepted" if started else "unknown"
        write_json(rp, receipt)
    res = {"ok": started, "accepted": started, "id": s["id"], "turn": n, "conversation_id": cid,
           "route": "agy --print --conversation (new process, same conversation)", "observed": False,
           "receipt": receipt, "note": "Started a follow-up turn of the same agy conversation; check "
           "`status` for whether agy really continued it."}
    if warn_lost(st):
        res["warning"] = warn_lost(st)
    out(res, 0 if started else EXIT_UNKNOWN)


def warn_lost(st):
    return "The previous turn ended without a recorded result." if st == "lost" else None


def row(s):
    st, detail = session_state(s)
    td = turn_dir(s["id"], s["turns"])
    text = response_text(td) if st not in ACTIVE else ""
    hl = headline(text)
    if st == "denied":
        hl = "permission denied in headless mode: %s" % ", ".join(
            d.get("action", "?") for d in detail or [] if isinstance(d, dict))
    elif st in ("failed", "refused", "lost", "timed-out", "interrupted") and detail:
        hl = one_line(json.dumps(detail) if isinstance(detail, dict) else str(detail), 300)
    return {"id": s["id"], "name": s.get("name") or "", "state": st, "turns": s["turns"],
            "created": ago(s.get("created")), "cwd": s["cwd"], "branch": s.get("branch"),
            "isolation": s.get("isolation"), "conversation_id": s.get("conversation_id"), "headline": hl}


def cmd_list(a):
    state_root()
    rows = []
    day = time.time() - 86400
    for s in all_sessions():
        r = row(s)
        if a.all or r["state"] in ACTIVE or s.get("created", 0) > day:
            rows.append(r)
    order = {"denied": 0, "failed": 0, "refused": 0, "lost": 1, "timed-out": 1, "working": 2, "starting": 2}
    rows.sort(key=lambda r: order.get(r["state"], 3))
    if a.json:
        out(rows)
    if not rows:
        print("No agy sessions" + ("" if a.all else " in the last day (try --all)") + ".")
        return
    for r in rows:
        print("%s  %-10s %s  [%s, %d turn(s)]" % (r["id"], r["state"], r["name"] or "-", r["created"], r["turns"]))
        if r["headline"]:
            print("            " + r["headline"])
        print("            %s%s" % (r["cwd"], "  (%s)" % r["branch"] if r["branch"] else ""))


def cmd_status(a):
    state_root()
    s = find(a.ref)
    r = row(s)
    td = turn_dir(s["id"], s["turns"])
    t = read_json(os.path.join(td, "turn.json")) or {}
    ex = read_json(os.path.join(td, "exit.json")) or {}
    receipts = []
    rd = os.path.join(sess_dir(s["id"]), "receipts")
    if os.path.isdir(rd):
        for f in sorted(os.listdir(rd)):
            rec = read_json(os.path.join(rd, f))
            if rec:
                receipts.append(rec)
    r.update({"last_prompt": one_line(t.get("prompt", ""), 300), "recent": activity(td),
              "last_response": response_text(td)[-3000:] if r["state"] not in ACTIVE else "",
              "result": ex.get("result"), "exit_code": ex.get("code"), "guard": ex.get("guard"),
              "stderr_tail": stderr_tail(td, 400), "git": git_summary(s), "worktree": s.get("worktree"),
              "origin": s.get("origin"), "base": s.get("base"), "mode": s.get("mode") or "agy default",
              "receipts": sorted(receipts, key=lambda x: x.get("at", 0))[-10:],
              "logs": {"events": os.path.join(td, "events.jsonl"), "stderr": os.path.join(td, "stderr.log"),
                       "agy_log": os.path.join(td, "agy.log")}})
    if a.json:
        out(r)
    print("%s  %s  state=%s  turns=%d  created %s" % (r["id"], r["name"], r["state"], r["turns"], r["created"]))
    print("cwd: %s%s" % (r["cwd"], "  (branch %s)" % r["branch"] if r["branch"] else "  (no isolation)"))
    print("conversation: %s" % (r["conversation_id"] or "not reported yet"))
    print("asked: %s" % r["last_prompt"])
    if r["headline"]:
        print("headline: %s" % r["headline"])
    for x in r["recent"]:
        print("  " + x)
    g = r["git"]
    if g:
        print("git: %s (%d uncommitted)" % (g["branch"], g["uncommitted_files"]))
        for c in g.get("commits", g.get("recent_commits", [])):
            print("  " + c)
    if r["last_response"]:
        print("last response:\n" + r["last_response"][-1500:])


def cmd_wait(a):
    state_root()
    s = find(a.ref)
    deadline = time.time() + a.timeout
    while session_state(load_session(s["id"]))[0] in ACTIVE and time.time() < deadline:
        time.sleep(2)
    r = row(load_session(s["id"]))
    out({"id": r["id"], "state": r["state"], "headline": r["headline"],
         "still_working": r["state"] in ACTIVE})


def cmd_stop(a):
    state_root()
    s = find(a.ref)
    with Lock(s["id"]):
        s = load_session(s["id"])
        n = s["turns"]
        st, _ = turn_state(s, n)
        if st not in ACTIVE:
            out({"ok": True, "id": s["id"], "stopped": False, "running": False, "state": st,
                 "note": "Not running; nothing was signalled.", "worktree_kept": s.get("worktree")})
        r = read_json(os.path.join(turn_dir(s["id"], n), "runner.json")) or {}
        s["stopped_turn"] = n
        save_session(s)
        signalled = None
        if identity_ok(r.get("runner")):
            os.kill(r["runner"]["pid"], signal.SIGTERM)  # runner forwards SIGINT to agy, then escalates
            signalled = "runner"
        elif identity_ok(r.get("agy")):
            os.kill(r["agy"]["pid"], signal.SIGINT)  # orphaned agy: use its own interrupt path
            signalled = "agy"
    deadline = time.time() + STOP_GRACE + 15
    while time.time() < deadline:
        st, _ = turn_state(load_session(s["id"]), n)
        if st not in ACTIVE:
            break
        time.sleep(0.3)
    escalated = False
    if signalled == "agy" and st in ACTIVE and identity_ok(r.get("agy")):
        os.kill(r["agy"]["pid"], signal.SIGTERM)
        escalated = True
        time.sleep(3)
        st, _ = turn_state(load_session(s["id"]), n)
    ex = read_json(os.path.join(turn_dir(s["id"], n), "exit.json")) or {}
    escalated = escalated or bool(ex.get("escalated"))
    res = {"ok": st not in ACTIVE, "id": s["id"], "stopped": st == "stopped", "running": st in ACTIVE,
           "state": st, "signalled": signalled, "worktree_kept": s.get("worktree"), "branch": s.get("branch")}
    if st not in ACTIVE and st != "stopped":
        res["note"] = "No longer running, but the turn ended as %r rather than by this stop." % st
    if escalated:
        res["warning"] = "agy did not exit on SIGINT and was sent SIGTERM; commands it started may still run."
    if st in ACTIVE:
        res["note"] = "Stop was requested but agy has not exited yet. Check `status` again."
    out(res, 0 if res["ok"] else EXIT_UNKNOWN)


def cmd_doctor(a):
    path = agy_bin()
    info = agy_probe(path)
    res = {"ok": bool(info["supported"]), "agy": info, "capabilities": CAPABILITIES,
           "platform": sys.platform, "state_dir": STATE, "agy_data_dir": AGY_DATA}
    try:
        state_root()
        res["state_dir_ok"] = True
    except Refusal as e:
        res["state_dir_ok"], res["state_dir_error"] = False, e.message
    if a.ref:
        s = find(a.ref)
        n = s["turns"]
        r = read_json(os.path.join(turn_dir(s["id"], n), "runner.json")) or {}
        st, detail = turn_state(s, n)
        res["session"] = {
            "id": s["id"], "state": st, "detail": detail, "turn": n, "conversation_id": s.get("conversation_id"),
            "cwd_exists": os.path.isdir(s["cwd"]),
            "conversation_in_local_store": conversation_known(s["conversation_id"]) if s.get("conversation_id") else None,
            "runner_identity_ok": identity_ok(r.get("runner")), "agy_identity_ok": identity_ok(r.get("agy")),
            "send_ready": st not in ACTIVE + ("refused",) and bool(s.get("conversation_id"))
            and (st != "stopped"),
        }
        if s.get("branch") and s.get("repo"):
            res["session"]["branch_exists"] = git(["show-ref", "--verify", "--quiet",
                                                  "refs/heads/" + s["branch"]], s["repo"])[0] == 0
    if a.live:
        if not info["supported"]:
            res["live"] = {"ok": False, "skipped": "agy lacks required flags"}
        else:
            d = os.path.join(ensure_private_dir(os.path.join(STATE, "doctor")), time.strftime("%Y%m%d-%H%M%S"))
            os.makedirs(d, 0o700, exist_ok=True)
            try:
                p = subprocess.run([path, "--print=Reply with exactly the word pong. Do not call any tools.",
                                    "--output-format", "json", "--print-timeout=90s",
                                    "--log-file=" + os.path.join(d, "agy.log")], cwd=d, capture_output=True,
                                   text=True, timeout=150, stdin=subprocess.DEVNULL)
                body = json.loads(p.stdout) if p.stdout.strip().startswith("{") else {}
                res["live"] = {"ok": p.returncode == 0 and body.get("status") == "SUCCESS", "exit": p.returncode,
                               "status": body.get("status"), "response": (body.get("response") or "")[:80],
                               "error": body.get("error") or one_line(p.stderr, 300) or None, "folder": d}
            except (OSError, subprocess.TimeoutExpired, ValueError) as e:
                res["live"] = {"ok": False, "error": str(e), "folder": d}
            res["ok"] = res["ok"] and res["live"]["ok"]
    out(res, 0 if res["ok"] else EXIT_UNSUPPORTED)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 4 and argv[0] == "_run":
        return runner_main(argv[1], int(argv[2]), argv[3])
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("spawn", "start"):
        sp = sub.add_parser(name)
        sp.add_argument("--cwd", required=True)
        sp.add_argument("--name")
        sp.add_argument("--worktree", action="store_true", help="require an isolated worktree (default in git)")
        sp.add_argument("--no-worktree", action="store_true", help="let agy edit the folder in place")
        sp.add_argument("--mode", choices=MODES, help="agy --mode; omitted = agy's own default")
        sp.add_argument("--model")
        sp.add_argument("--effort", choices=("low", "medium", "high", "xhigh", "max"))
        sp.add_argument("--sandbox", action="store_true")
        sp.add_argument("--print-timeout", help="agy --print-timeout, e.g. 30m (default: no limit)")
        sp.add_argument("task", nargs=argparse.REMAINDER)
    sd = sub.add_parser("send")
    sd.add_argument("ref")
    sd.add_argument("message")
    sd.add_argument("--request-id")
    sd.add_argument("--allow-stopped", action="store_true")
    ls = sub.add_parser("list")
    ls.add_argument("--all", action="store_true")
    ls.add_argument("--json", action="store_true")
    ss = sub.add_parser("status")
    ss.add_argument("ref")
    ss.add_argument("--json", action="store_true")
    wt = sub.add_parser("wait")
    wt.add_argument("ref")
    wt.add_argument("--timeout", type=int, default=150)
    sp = sub.add_parser("stop")
    sp.add_argument("ref")
    dr = sub.add_parser("doctor")
    dr.add_argument("ref", nargs="?")
    dr.add_argument("--live", action="store_true", help="run one tiny real agy prompt in an empty folder")
    dr.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    if getattr(a, "task", None) and a.task[:1] == ["--"]:
        a.task = a.task[1:]
    if os.name != "posix" or fcntl is None:
        out({"ok": False, "error": "EUNSUPPORTED", "message": "This helper supports macOS and Linux only. "
             "On Windows run agy -p yourself in a terminal."}, EXIT_UNSUPPORTED)
    handlers = {"spawn": cmd_spawn, "start": cmd_spawn, "send": cmd_send, "list": cmd_list,
                "status": cmd_status, "wait": cmd_wait, "stop": cmd_stop, "doctor": cmd_doctor}
    try:
        handlers[a.cmd](a)
    except Refusal as e:
        body = {"ok": False, "error": e.code, "message": e.message}
        body.update(e.extra)
        out(body, e.exit_code)


if __name__ == "__main__":
    main()
