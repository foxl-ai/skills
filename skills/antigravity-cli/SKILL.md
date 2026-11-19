---
name: antigravity-cli
description: "Hand coding tasks to Google Antigravity's agy CLI as background runs, check how they are doing, continue the same agy conversation after a turn ends, and stop them. Use for 'have agy (or Antigravity) do X', 'how are my agy tasks doing', 'tell agy to also...', or 'stop it', including from the phone. agy has no native background sessions or mid-turn messages; this skill runs headless turns and refuses what agy cannot do."
enabled: false
requires: [agy, python3]
tags: coding, agents, antigravity, agy, background, remote
---

# Antigravity CLI (agy) sessions

Everything goes through one helper. `<skill-dir>` is the folder this file was read from:

```bash
python3 <skill-dir>/scripts/agy_sessions.py <command> ...
```

Python 3.8+, macOS or Linux. It returns within seconds, except `wait` (default 150 s)
and `stop` (up to about 30 s). Output is JSON unless noted.

## What agy supports, and what this skill does about it

Checked against agy 1.5.12 and its docs (`reference/agy-behavior.md`):

| Need | agy itself | This skill |
|---|---|---|
| Background session | None. Headless `agy -p` runs one turn and exits | A detached runner per turn that records events, stderr, agy's own log and the exit |
| List or status | No session list command | Its own records only. Never reads or edits agy's conversation files |
| Same-session follow-up | `--conversation <uuid>` in a new process, after the turn | `send`, only when no turn is running. The exact UUID, from the recorded folder |
| Message while it works | Not in headless mode | **Unsupported.** `send` refuses with `EBUSY`. Use `wait`, then `send` |
| Approve a permission | Headless cannot prompt; it auto-denies | **Unsupported.** State `denied`; see Permissions |
| Stop | Ctrl+C (SIGINT) interrupts the turn and its commands | `stop` sends SIGINT to the verified process |

agy silently starts a **new** conversation when `--conversation` names an id it cannot
find, and moves a conversation to the current folder when resumed elsewhere. `send`
therefore refuses when agy's local store lacks the id. Its runner also aborts a turn
the moment agy reports another conversation id or folder (state `refused`, `EREPLACED`
or `ECWD`). It never adopts the replacement, and never resends automatically.

## Commands

| Command | Meaning |
|---|---|
| `spawn --cwd DIR [--name N] -- TASK` | A **new** task and conversation. `start` is an alias. In git: own worktree and branch |
| `send REF MESSAGE [--request-id KEY]` | Next turn of the **same** conversation. Refused while working, stopped or after a guard abort |
| `list [--all] [--json]` | Problems first, then working, then the rest of the last day (`--all`: everything) |
| `status REF [--json]` | State, last request, recent tool steps, response, denied actions, git branch/commits, receipts, log paths |
| `wait REF [--timeout S]` | Block until the turn ends. `still_working: true` if it did not |
| `stop REF` | Interrupt the running turn. Keeps worktree, branch and logs |
| `doctor [REF] [--live]` | Read-only probe: agy path, version, required flags, capabilities; with REF, process identity and send readiness. `--live` runs one tiny real prompt in an empty folder |

REF is the exact session id (preferred), a unique id prefix of 6+ characters, the exact
agy conversation UUID, or an exact unique name. Ambiguous refs are refused with the
matches; then use the id.

Spawn options: `--mode auto|accept-edits|plan` (omitted: agy's own default, Auto
where available), `--model`, `--effort low|medium|high|xhigh|max`, `--sandbox`,
`--print-timeout 30m` (default: no limit), `--worktree`, `--no-worktree`. Follow-ups
reuse the session's options.

## Isolation

- In a git repository each task gets a new branch `agy/<name>-<id>` and a new worktree
  under `~/.local/state/agy-sessions/worktrees/`. It branches from the current commit
  of the folder, and a subfolder maps to the same subfolder. An existing branch or
  path is never reused or overwritten. Uncommitted changes in the folder are **not**
  copied; `spawn` warns about them. The default is to commit first, or pass `--no-worktree`.
- `--no-worktree` is the explicit opt-out: agy edits the folder itself, on its branch.
- Outside git there is no isolation. `spawn` refuses unless `--no-worktree` is given,
  then warns that agy edits the folder in place with no undo. Say so to the user first.
- Stop, failure, denial, timeout and abort never remove anything. Delete a worktree only
  when the user asks: from the original repo, `git worktree remove <worktree>`, which
  refuses with uncommitted changes. Report that instead of forcing. The branch stays until
  the user deletes it.

## How to handle requests

**"Have agy do X"**: confirm the folder unless obvious; never guess between repos.
Write a complete brief with the goal, scope, how to test, and what to do with the
result (leave it on the branch, commit, push, open a PR). Include only what the user
authorized, and respect their commit/push rules. End the brief with:
`When you finish, end with "result:", "needs input:", or "failed:" and a short outcome.`
Run `spawn`, then reply with name, id, branch and folder. Do not `wait` unless asked or tiny.

**"How is it going?"**: `list` (one line per task, problems first); `status ID` only for
the task asked about. Lead with `denied`, `failed`, `refused`, `lost` and "needs input:"
headlines, quoting the question or error.

**"Tell it to also..." / an answer**: `send ID "..." --request-id <stable key>`. If it is
working, say so and offer to send when the turn ends (`wait`, then `send`). Reuse the
key on retries; a repeat returns the existing receipt instead of sending again.
Without a key, identical text to the same session is also not resent.

**"Stop it"**: `stop ID`. Report the kept worktree/branch. A stopped session is resumed
only when the user explicitly asks: `send ID "..." --allow-stopped`.

## States and what to report

`starting`, `working` (a live process proven to be the one started), `done` (agy exit 0
and `SUCCESS`), `denied` (finished, but a tool needed approval headless mode cannot
give), `failed`, `timed-out` (`--print-timeout` hit, partial answer), `interrupted`
(ended by something other than `stop`), `stopped`, `refused` (guard abort, see above),
`lost` (no recorded exit and the process is gone or a different process now has its pid).
Never call `lost` done or running.

`send` → `accepted: true, observed: false` means a follow-up turn of the same
conversation was started. Say "sent as the next turn". Confirm from `status` that it
finished. Exit 4 = refused (not sent), 5 = unknown (it may have started; inspect
`status` before doing anything), 2 = unsupported or invalid.

## Permissions, trust and sign-in

The helper never passes `--dangerously-skip-permissions`, never edits agy settings,
trusted folders, permission rules or sign-in, and never answers prompts for the user.
Headless agy cannot ask for approval. When a turn needs one, agy denies it and the
state is `denied`, with the actions in `status`. Offer the user these choices:
continue at the computer with `cd <cwd> && agy --conversation <conversation_id>`
(only while no helper turn runs), add an allow rule in agy themselves
(`permissions.allow` in `~/.gemini/antigravity-cli/settings.json`), or choose
another `--mode`. An "authentication required" failure means: run `agy` once at the
computer and sign in. Headless agy 1.5.12 did not ask for folder trust; the helper
does not grant trust.

agy works unattended under the user's account. In Auto mode it edits the workspace and
runs sandboxed commands without asking. Say this once. Worktrees isolate edits, not
permissions. Start only tasks the user asked for, and keep secrets out of briefs.

## Files

`$AGY_SESSIONS_STATE` (default `~/.local/state/agy-sessions/`, mode 700) holds
`sessions/<id>/session.json` and `receipts/`. Each turn's `turns/<n>/` has `turn.json`,
`events.jsonl` (raw stream-json), `stderr.log`, `agy.log`, `runner.json` (pid, start time,
marker) and `exit.json`. The state folder is refused if it is a link, someone else's,
or group/world writable. Env: `AGY_BIN`, `AGY_SESSIONS_STATE`, `AGY_DATA_DIR`.
Tests: `tests/README.md`.
