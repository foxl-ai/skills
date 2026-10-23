---
name: claude-code
description: "Hand new coding tasks to Claude Code, inspect background sessions, send follow-ups to the same existing session, and stop sessions. Use for 'have Claude do X', 'how are my Claude sessions doing', 'tell that session to also...', or 'stop it', including from the phone. Distinguish new-task spawn from existing-session send."
enabled: false
requires: [claude, python3]
tags: coding, agents, claude-code, background, remote
---

# Claude Code sessions

Use one helper, where `<skill-dir>` is this skill's directory:

```bash
python3 <skill-dir>/scripts/cc_sessions.py <command> ...
```

Python 3.8+. All CLI calls use `CLAUDE_BIN` (default `claude`), including the
normal Toolbox wrapper and its authentication/settings. Never bypass that wrapper.
New sessions use supported `--bg` (Claude Code 2.1.284+), with the project's
existing trust confirmation. Do not bypass trust or permission prompts.

## Commands

| Command | Meaning |
|---|---|
| `spawn --cwd DIR [--name N] -- TASK` | Create a **new** background session. `start` is an alias. Default: an isolated worktree/branch in git projects. |
| `send ID\|NAME MESSAGE [--request-id KEY]` | Queue a follow-up into the **same existing native session**, working or idle. Never stop, resume, fork or create a replacement. |
| `doctor [ID\|NAME] --json` | Read-only bridge/version/ownership probe. With a target, validate its exact identity and worker build too. Never starts a daemon. |
| `list [--all] [--json]` | Show sessions, blocked first. Include finished sessions with `--all`. |
| `status ID\|NAME [--json]` | Read progress, recent tools, last message, branch/commits/PR and send receipts. |
| `queue ID\|NAME [--json]` | Read send receipts and retired legacy queue history. Not the native queue depth. |
| `queue ID\|NAME --clear` | Cancel **legacy pending** messages only. Cannot recall native accepted replies. |
| `wait ID\|NAME [--timeout S]` | Wait for current work (default 150 seconds). Not proof a particular reply was consumed. |
| `stop ID\|NAME` | Stop through the normal CLI, cancel legacy pending work first, never resume automatically. |

Prefer the exact 8-character native ID. A unique name or full session UUID may
resolve to it, but ambiguous names are refused. Legacy copy IDs are never
silently redirected. Inspect history, confirm the current ID, then use that ID.

Spawn options: `--mode bypass|auto|acceptEdits|plan`, `--model`, `--effort`,
`--worktree NAME`, `--no-worktree`. Existing defaults are unchanged.

## New task versus follow-up

For a **new task**, confirm the folder rather than guessing between repos. Write
a complete brief with goal, scope, tests and authorized result handling. Respect
user-specific commit/push/PR permissions and prohibitions. Finish the brief with:
`When you finish, end with "result:", "needs input:", or "failed:" and a short outcome.`
Use `spawn`, then report its ID and branch. Do not wait unless asked.

For **"tell that session to also..."** or an answer to an existing session, use
`send`, even while it is busy. Do not turn it into a new task. Use a stable request
ID for the user's action and reuse it on transport retries. Without a key, the
helper deduplicates identical text for that canonical session. To intentionally
repeat identical text later, use a new key only for a genuinely new user request.
Never change keys to evade an `unknown` outcome.

Native `send` is an **unsupported private POSIX bridge**, not an official CLI command.
On Windows use the agents UI for replies. Spawn, list, status and stop remain
normal CLI operations there; no POSIX process probes or receipt writes run.
The exact reviewed Toolbox CLI builds are `2.1.308.1355` and `2.1.309.1365`.
Reviewed supervisors are `2.1.308` and `2.1.309`, protocol 1. The target worker
must match its supervisor. CLI/supervisor upgrade skew is allowed only inside
that reviewed set. Other builds, absent daemons, unsafe paths, auth failures and
unavailable/stopped targets fail closed. Do not restart the daemon or downgrade
security to make a send work. Run `doctor` to diagnose.

## What to report

`accepted: true, queued: true` means the supervisor acknowledged the native
safe-boundary queue request for the same ID. Say **"queued in the existing
session"**, not "Claude has read it". Native scheduling may combine messages in
one turn. There is no guaranteed queue position, one-turn-per-message rule, or
consumption acknowledgement. `observed: false` explicitly means unverified.
The bridge queues ordinary prompt text. It does not answer permission dialogs,
select a structured question's choice, or execute `/model`, `/stop` and other
slash commands. Use the agents peek panel or attach for those interactions.

`rejected`/`refused` (exit 4) means it was not accepted. `unknown` (exit 5) means
it may have arrived. The helper saves an unknown receipt **before sending**,
never automatically resends, and retains receipt keys without pruning. A
repeated request returns the existing receipt, not another reply. This is local
at-most-one-attempt protection, not daemon exactly-once delivery. Changing
`CC_SESSIONS_STATE`, deleting receipts, a new key or another client defeats that
protection. For unknown outcomes, inspect the session before any manual action.

When unavailable, give this manual route: open `claude agents`, select the exact
session, press **Space** to peek, and reply there. Ordinary agents dispatch creates
new work. Never substitute `--resume`, `--bg --resume`, `stop` plus restart,
`--force`, an extra session, direct edits to Claude's registry/queue, or an auth
bypass. A stopped session needs an explicit user decision, not automatic revival.

For status reports, names are only handles. Read `status` for each relevant
working/blocked or newly finished session, then describe its actual content,
branch/PR and unverified tests. Blocked can mean awaiting review, not a question.
Report results from transcripts separately from send acknowledgement receipts.

## Legacy migration and safety

The old helper watcher and stop/resume delivery path are retired. `_watch` now
refuses. Reading `list`, `status` or `queue` never starts or repairs a watcher.
Legacy pending entries remain disabled history and are never replayed. `stop`
and explicit `queue --clear` cancel them across recorded copy lineage.

Before replacing an old installation, explicitly retire any already-running old
watcher processes. New send/stop refuse when a legacy watcher PID or lock is live,
but cannot disable old code running elsewhere. Do not run old and new helpers
concurrently. Receipt state defaults to `~/.local/state/claude-code-sessions/`
(or `$XDG_STATE_HOME/claude-code-sessions`); `CC_SESSIONS_STATE` overrides it.
Native registry, roster and queue files are never modified by this helper.

The default spawn mode remains `bypass` (`--dangerously-skip-permissions`), which
runs unattended with the user's file and network permissions. Explain that once,
and use a stricter mode when requested. Worktrees isolate edits, not permissions.
Only start requested work in confirmed folders. Keep secrets out of briefs and
reply text. Delete a session/worktree only with explicit authorization.
