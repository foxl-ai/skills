#!/usr/bin/env python3
"""`overview`: ONE roster snapshot, bounded parallel details for the sessions that matter, compact JSON.

Candidate for the claude-code skill (foxl-ai/skills skills/claude-code/scripts/), evaluated in pilot by
scripts/trajectory-eval (scenario cc-status-fast). Read-only: it lists and reads, and never sends,
stops, spawns, starts a daemon, writes receipts or refreshes another session's git index.

Why it exists (measured on the 2026-11-02 "how are my sessions doing" turn): the documented path is
`list --all --json`, then `status ID` per relevant session. Every `status` re-reads the whole roster
(`find()` -> `sessions()` = two `claude agents --json` CLI calls), so one answer cost 22 roster reads,
and the model ran the 9 statuses as two shell loops (18.45 s of sequential tool time) before a fifth
model round. Here the roster is read once (the same two calls, merged exactly as `sessions()` does),
every state/headline comes from the helper's own `summary()`/`state_of()`, and the per-session reads
(timeline, transcript tail, git, PR) run in parallel with a deadline. A session whose details cannot
be read is reported as `unknown` with the reason, never silently dropped.

Differences from `status`, on purpose and pinned by the eval's equivalence test:
  - the transcript tail is read from the END of the file (same last 400 lines as `read_jsonl(..., tail=400)`),
    refuses a non-regular file (a FIFO hung `status` forever) and survives invalid UTF-8;
  - `last_message` is cut to its last 400 characters (status: 2000), recent tools to 3, timeline to 2;
  - git runs with GIT_OPTIONAL_LOCKS=0 so a status read never writes another worktree's index;
  - what finished in the last day is listed newest first, at most 10 (`recently_finished`), the rest counted (`omitted`):
    `list --all` named every one, and a person asking after an hour away is asking what finished;
  - blocked sessions carry `blocked_kind`: `question` only when the job recorded `needsInput`,
    otherwise `unknown` (a blocked session may be waiting for review; that is not guessed).
"""
import argparse
import calendar
import contextlib
import io
import json
import os
import queue
import re
import stat
import sys
import threading
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
os.environ.setdefault("GIT_OPTIONAL_LOCKS", "0")

import cc_sessions as cs  # noqa: E402  (the helper this candidate sits beside)

SCHEMA = "cc-overview/1"
TAIL_LINES = 400
MAX_TAIL_BYTES = 64 * 1024 * 1024


def tail_lines(path, n=TAIL_LINES, max_bytes=MAX_TAIL_BYTES):
    """The last `n` lines of a regular file, exactly as text-mode `readlines()[-n:]` gives them
    (universal newlines: \\r\\n and \\r end a line and become \\n), as bytes. Reads from the END in
    64 KB blocks, linear in what it reads. Returns (lines, truncated)."""
    st = os.stat(path)
    if not stat.S_ISREG(st.st_mode):
        raise OSError("transcript is not a regular file")
    size = st.st_size
    if size == 0 or n <= 0:
        return [], False
    chunks = []
    breaks = 0
    pos = size
    with open(path, "rb") as f:
        # Stop once there are more than n line breaks (a margin per block covers a \\r\\n split by a block edge).
        while pos > 0 and breaks <= n + len(chunks) and size - pos < max_bytes:
            step = min(64 * 1024, pos)
            pos -= step
            f.seek(pos)
            b = f.read(step)
            chunks.append(b)
            breaks += b.count(b"\n") + b.count(b"\r") - b.count(b"\r\n")
    data = b"".join(reversed(chunks)).replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    truncated = pos > 0 and data.count(b"\n") <= n
    parts = data.split(b"\n")
    if pos > 0:
        parts = parts[1:]          # the first piece may start mid-line
    ends_nl = data.endswith(b"\n")
    if ends_nl:
        parts = parts[:-1]
    if not parts:
        return [], truncated
    lines = [p + b"\n" for p in parts[:-1]] + [parts[-1] + (b"\n" if ends_nl else b"")]
    return lines[-n:], truncated


def tail_jsonl(path, n=TAIL_LINES):
    """JSON entries of the last `n` lines, skipping bad lines like `read_jsonl`; invalid UTF-8 is skipped too."""
    raw, truncated = tail_lines(path, n)
    out = []
    bad_utf8 = 0
    for line in raw:
        try:
            text = line.decode("utf-8")
        except UnicodeDecodeError:
            bad_utf8 += 1
            continue
        try:
            out.append(json.loads(text))
        except ValueError:
            pass
    return out, truncated, bad_utf8


def recent_activity_entries(entries, n=6):
    """`cs.recent_activity`'s parsing, over already-read entries (kept identical; the eval compares them)."""
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
                tools.append(f"{block.get('name')}: {cs.one_line(str(what), 100)}")
    return last_text, tools[-n:], recap


def headline_source(s, state, st):
    """Where `cs.summary()` took the headline from: timeline, output (a finished turn's result) or detail."""
    out = st.get("output") or {}
    last = (cs.read_jsonl(os.path.join(cs.job_dir(s["id"]), "timeline.jsonl"), tail=1) or [{}])[-1]
    marks = [line for line in (last.get("text") or "").splitlines()
             if re.match(r"\s*(result|needs input|failed):", line, re.I)]
    if marks and last.get("state") == state:
        return "timeline", last.get("at")
    if out.get("result") or out.get("needsInput") or out.get("failed"):
        return "output", st.get("updatedAt")
    return "detail", st.get("updatedAt")


def details(s, row, with_pr):
    """Everything `status` adds, for one session, compacted. Raises nothing: errors become fields."""
    errors = []
    _, st = cs.state_of(s)
    timeline = cs.read_jsonl(os.path.join(cs.job_dir(s["id"]), "timeline.jsonl"), tail=200)
    steps = []
    for t in timeline:
        detail = cs.one_line(t.get("detail") or "", 140)
        if detail and (not steps or steps[-1]["detail"] != detail):
            steps.append({"at": t.get("at", ""), "state": t.get("state"), "detail": detail})
    last_text, tools, recap = "", [], ""
    path = cs.transcript(s)
    if path:
        try:
            entries, truncated, bad = tail_jsonl(path)
            last_text, tools, recap = recent_activity_entries(entries)
            if truncated:
                errors.append("transcript_tail_truncated")
            if bad:
                errors.append("transcript_invalid_utf8_lines")
        except OSError:
            errors.append("transcript_unreadable")
    git = None
    if s.get("cwd"):
        try:
            git = cs.git_summary(s.get("cwd")) if with_pr else _git_without_pr(s.get("cwd"))
        except BaseException:  # noqa: BLE001 - the helper's run() calls sys.exit on a CLI timeout
            errors.append("git_failed")
    receipts = None
    try:
        view = cs.Outbox(cs.STATE, cs.CONFIG).view(s)
        items = view.get("items") or []
        receipts = {"count": len(items), "unknown": sum(1 for i in items if i.get("status") == "unknown"),
                    "legacy": len(view.get("legacy") or [])}
    except Exception:  # noqa: BLE001 - a refused receipt store is reported, not fatal
        errors.append("receipts_unavailable")
    src, src_at = headline_source(s, row["state"], st)
    out = {
        "id": row["id"], "name": cs.one_line(row["name"], 60), "state": row["state"], "running": row["running"],
        "started": row["started"], "headline": row["headline"], "headline_from": src,
        "headline_stale": row["state"] == "working" and src == "output",
        "last_steps": steps[-2:], "recent_tools": tools[-3:],
        "last_message": last_text[-400:], "recap": cs.one_line(recap, 300),
    }
    if row["state"] == "blocked":
        needs = (st.get("output") or {}).get("needsInput")
        out["blocked_kind"] = "question" if needs else "unknown"
        out["blocked_detail"] = cs.one_line(needs or st.get("detail") or "", 160)
    if receipts and (receipts["count"] or receipts["legacy"]):
        out["send_receipts"] = receipts  # acceptance receipts, not proof a reply was read
    if git:
        out["git"] = {k: git[k] for k in ("branch", "changed_files") if k in git}
        if git.get("recent_commits"):
            out["git"]["head"] = git["recent_commits"][0]
        if isinstance(git.get("pr"), dict):
            out["git"]["pr"] = {k: git["pr"].get(k) for k in ("state", "url")}
    if errors:
        out["detail_errors"] = errors
    return out


def _git_without_pr(cwd):
    if not cwd or not os.path.isdir(cwd) or not cs.shutil.which("git"):
        return None
    code, out, _ = cs.run(["git", "-C", cwd, "status", "--porcelain=v1", "-b"], timeout=20)
    if code != 0:
        return None
    lines = out.splitlines()
    info = {"branch": lines[0][3:] if lines else "", "changed_files": len(lines) - 1}
    code, out, _ = cs.run(["git", "-C", cwd, "log", "-3", "--format=%h %s"], timeout=20)
    if code == 0:
        info["recent_commits"] = out.strip().splitlines()
    return info


def finished_at(st):
    """When a done session last changed (state.json `updatedAt`, UTC ISO), as epoch seconds, or None."""
    try:
        return calendar.timegm(time.strptime(str(st.get("updatedAt"))[:19], "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, OverflowError):
        return None


def relevant(row, st, now, recent_s):
    if row["state"] in ("working", "blocked") or row["running"]:
        return "active"
    if row["state"] == "done":
        t = finished_at(st)
        if t is not None and now - t <= recent_s:
            return "recent"
    return None


def recently_finished(rows, now, recent_s, n):
    """The done sessions that finished in the last `recent_s` seconds, NEWEST first, at most `n` (the rest are counted in
    `omitted`). Newest first because the ids are random: in id order the session that finished a minute ago could be the one
    left out, and "what finished" is what a person coming back to their sessions asks about first."""
    out = [(finished_at(st), s, row) for s, row, st in rows if relevant(row, st, now, recent_s) == "recent"]
    out.sort(key=lambda x: (-x[0], x[2]["id"]))
    return [(s, row) for _, s, row in out[:max(0, n)]]


def cmd_overview(a):
    started = time.monotonic()
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            items = cs.sessions(include_done=True)
    except SystemExit as e:
        msg = cs.one_line(err.getvalue(), 200)
        print(json.dumps({"schema": SCHEMA, "error": "roster_unavailable", "detail": msg, "exit": e.code,
                          "sessions": [], "note": "No session state was read; nothing is reported as working or done."}))
        sys.exit(3)
    roster_ms = int((time.monotonic() - started) * 1000)
    rows = []
    for s in items:
        row = cs.summary(s)
        _, st = cs.state_of(s)
        rows.append((s, row, st))
    counts = {"working": 0, "blocked": 0, "done": 0, "stopped": 0, "unknown": 0, "running": 0, "done_running": 0}
    for _, row, _ in rows:
        counts[row["state"] if row["state"] in counts else "unknown"] += 1
        counts["running"] += 1 if row["running"] else 0
        counts["done_running"] += 1 if row["running"] and row["state"] == "done" else 0
    now = time.time()
    active = [(s, row) for s, row, st in rows if relevant(row, st, now, a.recent_minutes * 60) == "active"]
    recent = recently_finished(rows, now, a.recent_minutes * 60, a.max_recent)
    active.sort(key=lambda x: (x[1]["state"] != "blocked", x[1]["state"] != "working", x[1]["id"]))
    detail_targets = active[:a.max_detail]
    results = {}
    unknown = []
    q = queue.Queue()

    def work(s, row):
        try:
            q.put((row["id"], details(s, row, not a.no_pr), None))
        except BaseException as e:  # noqa: BLE001 - one session's failure must not hide the others
            q.put((row["id"], None, type(e).__name__))

    pending = list(detail_targets)
    live = {}
    deadline = time.monotonic() + a.detail_timeout
    while pending or live:
        while pending and len(live) < a.concurrency:
            s, row = pending.pop(0)
            t = threading.Thread(target=work, args=(s, row), daemon=True)
            live[row["id"]] = t
            t.start()
        try:
            sid, res, e = q.get(timeout=max(0.01, deadline - time.monotonic()))
        except queue.Empty:
            break
        live.pop(sid, None)
        if res is not None:
            results[sid] = res
        else:
            unknown.append({"id": sid, "reason": f"detail_error:{e}"})
    for sid in list(live):
        unknown.append({"id": sid, "reason": "detail_timeout"})
    for s, row in pending:
        unknown.append({"id": row["id"], "reason": "detail_timeout"})
    over = active[a.max_detail:]
    for s, row in over:
        unknown.append({"id": row["id"], "reason": "over_max_detail"})
    sessions = []
    for s, row in detail_targets:
        if row["id"] in results:
            sessions.append(results[row["id"]])
        else:
            sessions.append({"id": row["id"], "name": cs.one_line(row["name"], 60), "state": row["state"],
                             "running": row["running"], "headline": row["headline"], "details": "unknown"})
    # Over the detail cap: the roster state is still reported (only the details are left out).
    for s, row in over:
        sessions.append({"id": row["id"], "name": cs.one_line(row["name"], 60), "state": row["state"],
                         "running": row["running"], "headline": row["headline"], "details": "omitted"})
    stopped = [{"id": row["id"], "name": cs.one_line(row["name"], 60)} for _, row, _ in rows if row["state"] == "stopped"]
    finished = [{"id": row["id"], "name": cs.one_line(row["name"], 60), "headline": row["headline"], "started": row["started"]}
                for s, row in recent]
    out = {
        "schema": SCHEMA,
        "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "roster": {"reads": 2, "ms": roster_ms, "total": len(rows)},
        "counts": counts,
        "sessions": sessions,
        "recently_finished": finished,
        "stopped": stopped[:10],
        "omitted": {"done": counts["done"] - counts["done_running"] - len(finished)},
        "unknown": unknown,
        "elapsed_ms": int((time.monotonic() - started) * 1000),
    }
    if not rows:
        out["note"] = "No Claude Code background sessions."
    print(json.dumps(out, ensure_ascii=False, separators=(",", ":")) if a.json else _text(out))


def _text(o):
    lines = [f"{o['counts']['working']} working, {o['counts']['blocked']} blocked, {o['counts']['done']} done "
             f"({o['counts']['done_running']} done but still running), {o['roster']['total']} total"]
    for s in o["sessions"]:
        lines.append(f"{s['id']} {s['state']}{' (running)' if s.get('running') else ''} {s.get('name') or '-'}: {s.get('headline') or ''}")
    for u in o["unknown"]:
        lines.append(f"{u['id']} details unknown ({u['reason']})")
    for x in o.get("stopped") or []:
        lines.append(f"{x['id']} stopped (working, but no process) {x['name'] or '-'}")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(prog="cc_overview.py", description="One-snapshot, read-only session overview.")
    sub = p.add_subparsers(dest="cmd", required=True)
    ov = sub.add_parser("overview")
    ov.add_argument("--json", action="store_true")
    ov.add_argument("--max-detail", type=int, default=24)
    ov.add_argument("--max-recent", type=int, default=10)
    ov.add_argument("--recent-minutes", type=int, default=1440)
    ov.add_argument("--concurrency", type=int, default=6)
    ov.add_argument("--detail-timeout", type=float, default=20.0)
    ov.add_argument("--no-pr", action="store_true", help="skip the per-session `gh pr view` (network)")
    a = p.parse_args(argv)
    cmd_overview(a)


if __name__ == "__main__":
    main()
