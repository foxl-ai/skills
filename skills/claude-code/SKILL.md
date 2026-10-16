---
name: claude-code
description: "Hand coding tasks to Claude Code on this computer and keep track of them. Starts Claude Code background sessions, lists what is running, reports progress and results, relays follow-up messages and answers, and stops sessions. Use when the user says things like 'have Claude Code do X', 'ask Claude to fix this', 'how are my Claude sessions doing', 'what is Claude working on', 'tell that session to also...', or 'stop it', including from the phone."
enabled: false
requires: [claude, python3]
tags: coding, agents, claude-code, background, remote
---

# Claude Code sessions

Run Claude Code as background sessions on this computer and manage them from
chat. The sessions belong to Claude Code itself (`claude --bg`), so they keep
running after this chat turn ends, and the user can still open any of them at
the computer with `claude attach <id>`.

Everything goes through one helper. `<skill-dir>` is the folder this file was
read from:

```bash
python3 <skill-dir>/scripts/cc_sessions.py <command> ...
```

Run it with the normal shell tool (`exec`). It returns within seconds, except
`wait`, which blocks up to `--timeout` seconds (default 150, under the shell
tool's default 180 s timeout). A queued `send` also returns at once; delivery
happens later in a background process.

## Requirements

- Claude Code 2.1.284 or newer, signed in (`claude --version`, `claude auth status`).
  Older builds have no `--bg`: run `claude update`.
- Python 3.8+.
- The project folder must have been opened in Claude Code once at the computer
  (Claude Code asks whether to trust a folder the first time, and background
  sessions refuse an untrusted folder). See Troubleshooting.

## Commands

| Command | What it does |
|---|---|
| `start --cwd DIR [--name N] -- TASK` | Start a session in DIR. In a git repo it gets its own worktree and branch, so parallel sessions never edit the same checkout. Prints `id`, `worktree`, `branch`. |
| `list [--all]` | Sessions that are running or waiting on the user (`--all`: finished ones too). Blocked first, then working. |
| `status ID\|NAME` | One session in detail: state, headline, recent progress steps, recent tool calls, git branch / uncommitted files / recent commits / PR, queued messages, last message. |
| `send ID\|NAME "MESSAGE"` | Follow-up or answer. If the session is between turns, it is paused and continued with the message right away. If it is mid-turn, the message is queued and goes in when the turn ends, without interrupting it; `send` returns at once with `"queued": true` and a `position`. `--force` interrupts the turn and delivers now; `--no-queue` refuses instead (exit 4). |
| `queue ID\|NAME [--clear]` | Queued messages for a session and what happened to each (`pending`, `delivered` with the id it went to, `cancelled`, `expired`, `failed`, `unknown`). `--clear` cancels every pending one. |
| `wait ID\|NAME [--timeout S]` | Block until the current turn ends, then print the state and headline. |
| `stop ID\|NAME` | Stop a session. The conversation and worktree are kept. |

`ID` is the 8-character id; any unique part of the session name also works.
Add `--json` to `list` and `status` for machine-readable output.

States: `working`, `blocked` (the session asked the user something), `done`,
`failed`, `stopped`.

Start options: `--mode bypass|auto|acceptEdits|plan` (default `bypass`, see
Safety), `--model`, `--effort`, `--worktree NAME`, `--no-worktree`.

## How to handle requests

**"Have Claude Code do X"**

1. Work out the folder. If the user did not say, and it is not obvious from the
   conversation, ask. `list --all` shows the folders recent sessions used; offer
   those. Never guess between repositories.
2. Write the task for the session as a complete brief: the goal, where to look,
   what "done" means, and what to do with the result (leave changes on the
   branch, commit, push, open a pull request - only what the user asked for).
   End the brief with this line, which is how `list` and `status` show a clean
   one-line outcome:
   `When you finish, end your final message with one line starting with "result:", or "needs input:" if you need the user, or "failed:" if it cannot be done.`
3. `start --cwd DIR --name "<3-5 word name>" -- "<brief>"`.
4. Reply with the name, id and branch, and that you will report back when asked.
   Do not `wait` unless the task is small or the user wants to wait.

**"How is it going?" / "What is running?"**

Run `list`. For a single session, or one the user names, also run `status`.
Answer in a few lines, one per session, most urgent first:

```
fix-login-redirect (a1b2c3d4): working, 12 min - running the auth tests
docs-typos (e5f6a7b8): done - fixed 14 typos, PR #212 opened
upgrade-deps (c9d0e1f2): needs your answer - "Pin React 18 or move to 19?"
```

Lead with anything `blocked` or `failed`, quote its question or error, and say
how to answer. Do not paste raw logs or tool output; summarize.

**Session names are unreliable: read inside before reporting.** The name is a
short label made when the session started, and the work often drifts away from
it (a session named after one bug can turn into a broad bug hunt that opens
many PRs; a session named "agent management" can turn into a repo cleanup).
`list` alone is therefore not enough for a status report:

1. Run `list`, then `status` for every `working` or `blocked` session and for
   anything that finished in the last few hours. Run them in parallel. Each
   `status` can take about 45 seconds, so skip old finished sessions unless
   the user asks about them.
2. Describe each session by what it is actually doing, taken from `recap`,
   `headline`, the branch and commits, the PR, and the `last message`. Use the
   name only as a handle. When the name and the content disagree, say so in one
   line.
3. `list` can be stale. A session can go from `working` to `done` between
   `list` and `status`. Trust the `status` result and mention the change.
4. `blocked` does not always mean a question. It is often "PR ready, waiting
   for your review". Read the last message and say whether it needs an answer,
   a review, or a decision.
5. Surface what the session says it did not verify (tests not run, not checked
   on screen, needs a real account or device). The headline usually hides it.

**Answers and follow-ups** ("tell it to use 19", "also add a test")

`send ID "<message>"`. There is no need to wait for a busy session first.

- `"queued": false`: the message went in. If `send` reports a different id
  ("started a copy"), use the new id from then on and tell the user.
- `"queued": true`: the session is mid-turn. Tell the user the message is
  queued (and its `position` if there are others) and goes in when the current
  turn ends, without cutting it. A later `send` lines up behind it; queued
  messages arrive in order, one per turn. Use `--force` only if the user wants
  the current turn stopped now.
- To check on a queued message, run `queue ID` (or `status ID`). A delivered
  entry names the id it went to; follow that id if it differs. To take back
  messages that have not gone in yet, `queue ID --clear`.
- A queued message is sent once, never retried. `failed` means the CLI refused
  it: say so and quote the error. `expired` means it was never sent, because
  the computer restarted or the session stayed busy for 12 hours
  (`--expire-after MINUTES` on `send` changes that). `unknown` means delivery
  was cut off midway: run `status` before sending it again.

The queue is the helper's own, not Claude Code's input box: Claude Code has no
supported command-line way to queue into a running session. The helper starts
a small background process that waits for the turn to end, then delivers the
message the same way an idle `send` does. "Turn ended" includes a session that
is waiting on its own work (for example CI) with nothing running, and one that
was stopped or is waiting on the user.

The queue works on macOS and Linux. On Windows `send` to a busy session
refuses (exit 4) instead: offer to send it once the turn ends (`wait`, then
`send`), or to interrupt with `--force` only if the user wants that.

**"Stop it" / "Cancel"**

`stop ID`. Work done so far stays in the worktree. Deleting a session and its
worktree (`claude rm ID`) loses uncommitted work: do it only when the user
explicitly asks to delete, and report what `claude rm` says it kept.

**"Where is the result?"**

`status ID` shows the worktree path, branch, commits and PR. The user can open
the session at the computer with `claude attach ID`, or review the branch.

## Safety

- `--mode bypass` (the default) runs the session with
  `--dangerously-skip-permissions`: it can run any command and edit any file
  without asking. A background session has nobody to answer permission
  prompts, so a stricter mode stalls on the first command that needs approval.
  The worktree keeps its edits off the user's checkout, but commands still run
  as the user, on this computer, with network access. Tell the user once that
  delegated sessions run unattended with full permissions, and use
  `--mode auto` or `--mode acceptEdits` if they prefer (`auto` needs a Claude
  Code plan that offers auto mode).
- Only start sessions the user asked for, in folders the user named or
  confirmed.
- Do not put secrets in the task text; the session reads them from the project
  the same way the user's own Claude Code does.

## Use Claude Code as a model in Foxl

Separately from sessions, a signed-in Claude Code can power Foxl chats directly
with your Claude subscription (no API key, no relay credits). Pick a Claude Code
model in Foxl's model picker. Foxl finds the Claude Code sign-in automatically;
if it says Claude Code is not configured, run `claude auth login`.

## Raw CLI reference

The helper wraps these; use them directly only if the helper is unavailable.

```bash
claude --bg --dangerously-skip-permissions -n "name" -w <worktree> "task"   # in the repo root
claude agents --json [--all]          # id, sessionId, name, cwd, state, status, pid
claude stop <id>
claude --bg --resume <full-session-uuid> "follow-up"   # after stop; no other flags
claude attach <id>                    # interactive, at the computer only
claude rm <id>                        # deletes the session and its worktree
```

`claude logs <id>` prints the raw terminal stream (escape codes); use
`status` for a readable view.

## Troubleshooting

- **"has not been opened in DIR on this computer yet"**: Claude Code wants a
  one-time trust confirmation for that folder. Ask the user to run `claude` in
  it once at the computer and accept, or pick a folder they already use with
  Claude Code. Do not work around the trust prompt.
- **"no background sessions (`--bg`)"**: `claude update`.
- **"`claude` was not found"**: install Claude Code, or set `CLAUDE_BIN` to its
  path (shells started by apps sometimes lack the login PATH).
- **A session shows `stopped` although nobody stopped it**: it was interrupted
  (for example the computer restarted). `send` it a message such as
  "continue" to resume it.
- **Sign-in errors in `status`**: run `claude auth login` at the computer.
- **Every `send` reports "started a copy"**: the CLI continues a session in
  place only when `--resume` gets no other flags. A `claude` that is a wrapper
  script adding its own flags makes every resume a copy. The work still
  continues (the copy has the whole conversation); follow the new id.
- **A queued message never arrived**: `queue ID` says why. The watcher's log
  and the queue files are in `$CC_SESSIONS_STATE` (default
  `~/.local/state/claude-code-sessions/`), one `<id>.json` and `<id>.log` per
  session.
