#!/usr/bin/env python3
"""Test double for the agy 1.5.x headless CLI. Never contacts a model or the network.

Mirrors behaviour observed with the real agy 1.5.12 (see ../reference/agy-behavior.md):
- `--print=TEXT --output-format stream-json` prints NDJSON: init {cwd}, step_update..., result.
- `--conversation=ID` continues ID if it exists; an unknown ID prints
  `warning: conversation "ID" not found` to stderr and silently starts a NEW conversation.
- SIGINT ends the turn: result status ERROR, error/finished_reason "interrupted", exit 1.

Directives inside the prompt drive test scenarios: SLEEP=<seconds>, WRITE=<file>, DENY, FAIL,
TIMEOUT, IGNORE_SIGINT. FAKE_AGY_STORE is the conversation store (<store>/conversations/<id>.db).
FAKE_AGY_REPORT_CWD overrides the cwd reported in init. FAKE_AGY_HELP=legacy hides --conversation.
"""
import json
import os
import re
import signal
import sys
import time
import uuid

HELP = """Usage of agy:
  -c                              Short alias for --continue
  --continue                      Continue the most recent conversation
  --conversation                  Resume a previous conversation by ID
  --dangerously-skip-permissions  Auto-approve all tool permission requests without prompting
  --effort                        Reasoning effort for the current CLI session (low|medium|high|xhigh|max)
  --log-file                      Override CLI log file path
  --mode                          Set the agent execution mode for this session (accept-edits, auto, plan)
  --model                         Model for the current CLI session
  --output-format                 Output format for print mode (text, json, stream-json) (default text)
  -p                              Short alias for --print
  --print                         Run a single prompt non-interactively and print the response
  --print-timeout                 Optional time limit for print mode; 0 waits until the turn completes (default 0s)
  --sandbox                       Run in a sandbox with terminal restrictions enabled
"""


def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main():
    args = sys.argv[1:]
    if args == ["--version"]:
        print("1.5.12")
        return 0
    if args == ["--help"]:
        text = HELP
        if os.environ.get("FAKE_AGY_HELP") == "legacy":
            text = "\n".join(l for l in HELP.splitlines() if "--conversation" not in l)
        print(text)
        return 0
    opts = {}
    for a in args:
        if a.startswith("--") and "=" in a:
            k, v = a[2:].split("=", 1)
            opts[k] = v
        elif a.startswith("--"):
            opts[a[2:]] = True
    prompt = opts.get("print", "")
    store = os.path.join(os.environ["FAKE_AGY_STORE"], "conversations")
    os.makedirs(store, exist_ok=True)
    log = opts.get("log-file")
    if log:
        with open(log, "a") as f:
            f.write(json.dumps({"argv": args, "cwd": os.getcwd(), "pid": os.getpid()}) + "\n")

    cid = opts.get("conversation")
    if cid and not os.path.exists(os.path.join(store, cid + ".db")):
        sys.stderr.write('warning: conversation "%s" not found\n' % cid)
        sys.stderr.flush()
        cid = None
    cid = cid or str(uuid.uuid4())
    db_path = os.path.join(store, cid + ".db")
    db = {"turns": 0, "cwds": [], "prompts": []}
    if os.path.exists(db_path):
        with open(db_path) as f:
            db = json.load(f)

    def interrupted(*_):
        if log:
            open(log + ".sigint", "a").write("SIGINT\n")
        emit({"event": "result", "result": {"conversation_id": cid, "status": "ERROR", "response": "",
                                            "error": "interrupted", "num_turns": db["turns"] + 1,
                                            "finished_reason": "interrupted"}})
        sys.stderr.write("error: interrupted\n")
        sys.exit(1)

    if "IGNORE_SIGINT" in prompt:
        signal.signal(signal.SIGINT, lambda *_: open(log + ".sigint", "a").write("ignored\n") if log else None)
    else:
        signal.signal(signal.SIGINT, interrupted)

    emit({"event": "init", "conversation_id": cid,
          "init": {"cwd": os.environ.get("FAKE_AGY_REPORT_CWD") or os.getcwd(), "tools": ["run_command"],
                   "permission_mode": "request-review"}})
    time.sleep(0.4)  # a guard may abort here, before the turn is recorded
    db["turns"] += 1
    db["cwds"].append(os.getcwd())
    db["prompts"].append(prompt)
    with open(db_path, "w") as f:
        json.dump(db, f)
    emit({"event": "step_update", "step_update": {"conversation_id": cid, "step_index": 0, "state": "DONE",
                                                  "step_type": "user_input"}})
    m = re.search(r"WRITE=(\S+)", prompt)
    if m:
        with open(os.path.join(os.getcwd(), m.group(1)), "w") as f:
            f.write("written by fake agy\n")
        emit({"event": "step_update", "step_update": {
            "conversation_id": cid, "step_index": 1, "state": "DONE", "step_type": "tool",
            "tool_name": "write_file", "tool_info": {"name": "write_file", "parameters": {"Path": m.group(1)}}}})
    m = re.search(r"SLEEP=([\d.]+)", prompt)
    if m:
        end = time.time() + float(m.group(1))
        while time.time() < end:
            time.sleep(0.05)
    if "FAIL" in prompt:
        emit({"event": "result", "result": {"conversation_id": cid, "status": "ERROR", "response": "",
                                            "error": "boom", "num_turns": db["turns"], "finished_reason": "error"}})
        sys.stderr.write("error: boom\n")
        return 1
    if "TIMEOUT" in prompt:
        emit({"event": "result", "result": {"conversation_id": cid, "status": "ERROR", "response": "partial",
                                            "num_turns": db["turns"], "finished_reason": "print_timeout"}})
        sys.stderr.write("[agy] print timeout after 1s\n")
        return 3
    text = "result: pong turn %d" % db["turns"]
    emit({"event": "step_update", "step_update": {"conversation_id": cid, "step_index": 2, "state": "DONE",
                                                  "step_type": "agent_response", "text_delta": text}})
    res = {"conversation_id": cid, "status": "SUCCESS", "response": text + "\n", "num_turns": db["turns"]}
    if "DENY" in prompt:
        res["response"] = ""
        res["denied_actions"] = [{"action": "write_file", "display_name": "Edit"}]
        sys.stderr.write('jetski: no output produced — a tool required the "write_file" permission that '
                         'headless mode cannot prompt for, so it was auto-denied.\n')
    emit({"event": "result", "result": res})
    return 0


if __name__ == "__main__":
    sys.exit(main())
