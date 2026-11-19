# agy session helper tests

Run from the repository root:

```bash
python3 -B -W error::ResourceWarning -m unittest discover -s skills/antigravity-cli/tests -v
```

The suite (about a minute) uses `fake_agy.py`, a test double that mirrors the agy
1.5.12 headless behaviour recorded in `../reference/agy-behavior.md`. That includes
silently starting a new conversation for an unknown `--conversation` id. It never runs
the real agy, a model, the network or the user's agy state. Every test gets its own
`AGY_SESSIONS_STATE`, `AGY_DATA_DIR` and conversation store. A temporary git repo is
created once per class; tests remove only the worktrees they created.

Covered:

- **Isolation**: a new branch and worktree per task; the origin checkout is untouched;
  subfolders are mapped; `--no-worktree` is explicit; outside git it is required; an
  existing branch or path is never reused or overwritten.
- **Concurrency**: four simultaneous spawns get distinct ids, branches, worktrees and
  conversations. Of three simultaneous sends, exactly one starts a turn.
- **Follow-ups**: same conversation, `--conversation=<uuid>`, recorded folder. Refused
  while working (unsupported mid-turn send). Request-id and identical-text dedupe.
  `--allow-stopped` is required after `stop`.
- **Guards**: an unknown conversation is aborted and not adopted (`EREPLACED`); a missing
  conversation is refused before launch; a folder mismatch is aborted (`ECWD`).
- **Lifecycle**: stop by SIGINT keeps the worktree and branch; SIGTERM escalation when
  SIGINT is ignored; an immediate stop never kills the runner; failed, timed-out and
  denied states keep the worktree.
- **Process identity**: a recorded pid that now belongs to an unrelated process is
  reported `lost`, never `working`, and is never signalled. A vanished runner is `lost`,
  not `done`.
- **Unsupported capability**: an agy without `--conversation` is refused before any
  change. `doctor` reports no native background, no session list, no mid-turn send
  and no permission answering.
- **Safety**: ambiguous, short and unknown refs; unsafe state folder (writable by others,
  or a link); private file modes; message validation.

## Optional live smoke test (real agy)

Run it only with permission to use the user's signed-in agy. Use a throwaway git repo
and a separate state folder, so the user's session list stays clean:

```bash
export AGY_SESSIONS_STATE=$(mktemp -d)/state
H=skills/antigravity-cli/scripts/agy_sessions.py
python3 $H doctor --json
python3 $H spawn --cwd /tmp/throwaway-repo --name "smoke A" -- 'Reply with exactly: result: pong A. Do not call any tools.'
python3 $H wait <id> && python3 $H send <id> 'What letter followed pong? Reply: result: <letter>. No tools.' --request-id smoke-1
python3 $H wait <id> && python3 $H status <id> --json   # same conversation_id, num_turns 2
python3 $H send <id> 'Use run_command to run exactly: sleep 47 ; then reply result: slept.' --request-id smoke-2
python3 $H send <id> steer                              # EBUSY while working
python3 $H stop <id>                                    # stopped; `pgrep -f "sleep 47"` finds nothing
```

The run on 2026-11-18 with agy 1.5.12 passed every step, including two concurrent
spawns in one repo. Delete the throwaway repo and the state folder afterwards. Only
the agy conversations from the smoke test remain in agy's own history.
