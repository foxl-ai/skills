---
name: codex-cli
description: "Hand coding tasks to the Codex CLI on this computer and keep track of them. Starts Codex runs in the background, lists what is running, reports progress and results, sends follow-up messages into the same Codex conversation, and stops runs. Use when the user says things like 'have Codex do X', 'ask Codex to fix this', 'how are my Codex runs doing', 'what is Codex working on', 'tell Codex to also...', or 'stop it', including from the phone."
enabled: false
requires: [codex, python3]
tags: coding, agents, codex, background, remote
---

# Codex runs

Run the Codex CLI (`codex exec`) as background runs on this computer and
manage them from chat. Each run is detached from this chat's shell, so it keeps
going after the turn ends, and its full event log stays on disk.

Everything goes through one helper. `<skill-dir>` is the folder this file was
read from:

```bash
python3 <skill-dir>/scripts/codex_runs.py <command> ...
```

Run it with the normal shell tool (`exec`). It returns within seconds, except
`wait`, which blocks up to `--timeout` seconds (default 150, under the shell
tool's default 180 s timeout).

## Requirements

- Codex CLI, signed in (`codex --version`, `codex login status`). Install with
  `npm install -g @openai/codex` or `brew install --cask codex`; sign in with
  `codex login` or set `OPENAI_API_KEY`.
- Python 3.8+.
- Git, for the default per-run worktree.

## Commands

| Command | What it does |
|---|---|
| `start --cwd DIR [--name N] -- TASK` | Start a run in DIR. In a git repo it gets its own worktree on a new `codex/...` branch, so parallel runs never edit the same checkout. Prints `id`, `cwd` (the worktree), `branch`. |
| `list [--all]` | Runs that are working or started in the last day (`--all`: every run). |
| `status ID\|NAME` | One run in detail: state, the last request, recent commands and file edits, git branch / uncommitted files / commits, last message. |
| `send ID\|NAME "MESSAGE"` | Follow-up in the same Codex conversation (`codex exec resume`). Refuses while the run is working. |
| `wait ID\|NAME [--timeout S]` | Block until the current turn ends, then print the state and headline. |
| `stop ID\|NAME` | Stop the current turn. The worktree and log are kept; `send` continues later. |

`ID` is the run id printed by `start`; any unique prefix, or part of the name,
also works. Add `--json` to `list` and `status` for machine-readable output.

States: `working`, `done`, `failed` (with the error), `stopped`.

Start options: `--sandbox full|workspace-write|read-only` (default `full`, see
Safety), `--model`, `--worktree` (require one), `--no-worktree` (edit DIR in
place).

Runs are kept in `~/.local/state/codex-runs/<id>/` (`CODEX_RUNS_DIR` overrides):
`run.json`, and per turn `events-N.jsonl` (the raw `codex exec --json` stream),
`last-N.txt`, `stderr-N.log`, `exit-N.json`. Worktrees live under
`worktrees/` there.

## How to handle requests

**"Have Codex do X"**

1. Work out the folder. If the user did not say, and it is not obvious from the
   conversation, ask. `list --all` shows the folders recent runs used. Never
   guess between repositories.
2. Write the task as a complete brief: the goal, where to look, what "done"
   means, and what to do with the result (leave changes on the branch, commit,
   push, open a pull request - only what the user asked for). End it with:
   `When you finish, end your final message with one line starting with "result:", or "needs input:" if you need the user, or "failed:" if it cannot be done.`
3. `start --cwd DIR --name "<3-5 word name>" -- "<brief>"`.
4. Reply with the name, id and branch, and that you will report back when asked.
   Do not `wait` unless the task is small or the user wants to wait.

**"How is it going?" / "What is running?"**

Run `list`; for one run, also `status`. Answer in a few lines, one per run,
most urgent first:

```
fix-login-redirect (1015093012-a1b2): working, 12 min - last ran the auth tests
docs-typos (1015090144-c3d4): done - fixed 14 typos on codex/docs-typos-...
upgrade-deps (1015085530-e5f6): needs your answer - "Pin React 18 or move to 19?"
```

Lead with anything that failed or ends in "needs input:", quote its question or
error, and say how to answer. Summarize; do not paste raw event logs.

**Answers and follow-ups**: `send ID "<message>"`. If the run is still working,
say so and offer to send it when the turn ends (`wait`, then `send`).

**"Stop it"**: `stop ID`. To delete a run's worktree, only when the user asks:
`git worktree remove <cwd>` from the original repo (refuses if there are
uncommitted changes; report that rather than forcing it).

**"Where is the result?"**: `status ID` shows the worktree path, branch and
commits. The user can review the branch, or continue interactively at the
computer with `codex resume <thread_id>` (`status --json` shows `thread_id`).

## Safety

- `--sandbox full` (the default) runs Codex with
  `--dangerously-bypass-approvals-and-sandbox`: no sandbox, no approvals, network
  allowed. A background run has nobody to approve anything, and most real tasks
  need the network (installing packages, `git push`, opening a pull request).
  The worktree keeps edits off the user's checkout, but commands run as the
  user on this computer. Tell the user once that delegated runs are unattended
  with full access.
- `--sandbox workspace-write` confines edits to the folder and blocks network
  access, which suits "fix this and leave it on a branch" tasks; `read-only`
  suits questions and reviews.
- Only start runs the user asked for, in folders the user named or confirmed.
- Do not put secrets in the task text.

## Use Codex as a model in Foxl

Separately from runs, a signed-in Codex CLI can power Foxl chats with your
OpenAI account (no relay credits). Pick a Codex model in Foxl's model picker. If
Foxl says Codex is not configured, run `codex login` or set `OPENAI_API_KEY`.

## Raw CLI reference

The helper wraps these; use them directly only if the helper is unavailable.

```bash
codex exec --json -C DIR -o last.txt --dangerously-bypass-approvals-and-sandbox "task" </dev/null
codex exec resume --json <thread_id> "follow-up" </dev/null   # from DIR; resume has no -C
```

`--json` prints JSONL: `thread.started` (with `thread_id`), `item.completed`
(`agent_message`, `command_execution`, `file_change`, `error`),
`turn.completed`, `turn.failed`. Without `</dev/null` a backgrounded
`codex exec` waits for stdin forever.

## Troubleshooting

- **State `failed` with 401 / "not logged in"**: `codex login` at the computer,
  or set `OPENAI_API_KEY`.
- **"`codex` was not found"**: install it, or set `CODEX_BIN` to its path
  (shells started by apps sometimes lack the login PATH).
- **A run shows `stopped` although nobody stopped it**: it was interrupted (for
  example the computer restarted). `send` it "continue".
