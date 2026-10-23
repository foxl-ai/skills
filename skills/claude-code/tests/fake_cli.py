#!/usr/bin/env python3
"""Fake configured CLI for offline integration tests. Never runs Claude."""
import json
import os
from pathlib import Path
import sys

root = Path(os.environ["FAKE_CC_ROOT"])
args = sys.argv[1:]
with (root / "calls.jsonl").open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(args) + "\n")
if args == ["--version"]:
    print((root / "version.txt").read_text())
elif args == ["--help"]:
    print("Usage: fake-claude --bg TASK")
elif args[:2] == ["agents", "--json"]:
    print((root / "sessions.json").read_text())
elif args[:1] == ["stop"]:
    print("stopped " + args[1])
elif args[:1] == ["--bg"] and "--resume" not in args:
    print("backgrounded · fedcba98 · isolated fake task")
else:
    print("Forbidden or unknown CLI operation", file=sys.stderr)
    sys.exit(97)
