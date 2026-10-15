---
name: coding-agent
description: Run OpenCode, Pi or another terminal coding agent on this computer. For Claude Code or Codex, use the claude-code or codex-cli skill instead, which track sessions and report status.
enabled: false
requires: [claude, codex, opencode, pi]
requiresAny: true
---

# Coding Agent

Run terminal coding agents on this computer for programmatic code generation.

**Claude Code and Codex have dedicated skills** that start background sessions,
report status and relay follow-ups: read the `claude-code` or `codex-cli` skill
for those. Use this one for other agents.

## Choosing the tool

- **One-shot, non-interactive** (`opencode run`, `pi -p`): the `exec` tool.
  Pass a `timeout` (seconds) that fits the task; the default is 180.
- **Longer work in the background**: `exec` with `background: true`, then the
  `process` tool (`action: list | poll | log | kill`) to follow it. A background
  run is killed when its timeout expires (one hour by default), so for anything
  longer detach it yourself (`nohup ... > log 2>&1 &`) or use a dedicated skill.
- **Interactive TUI** that needs a real terminal: the `terminal` tool
  (`action: spawn`, then `write` / `read`; end `input` with a newline to press
  Enter).

## OpenCode

```bash
opencode run 'Your task'          # in the project folder (exec workdir)
```

## Pi Coding Agent

```bash
# Install: npm install -g @mariozechner/pi-coding-agent
pi -p 'Summarize src/'            # one-shot
pi 'Your task'                    # interactive: use the terminal tool
```

## Parallel work with git worktrees

Give each agent its own worktree so they never edit the same checkout:

```bash
git worktree add -b fix/issue-78 ../issue-78 main
git worktree add -b fix/issue-99 ../issue-99 main
# run one agent per folder (exec workdir: ../issue-78, ../issue-99)
git worktree remove ../issue-78   # after the branch is merged or pushed
```

## Rules

1. Run agents in the project folder the user named; ask when it is unclear.
2. Be patient: do not kill a slow run, check its log first.
3. Summarize results for the user; do not paste raw logs.
