---
name: coding-agent
description: Run Codex CLI, Claude Code, or other coding agents via background process
enabled: false
requires: [claude, codex, opencode, pi]
requiresAny: true
---

# Coding Agent

Run coding agents (Codex, Claude Code, OpenCode, Pi) for programmatic code generation.

## PTY Mode Required

Coding agents are interactive terminal apps that need a pseudo-terminal:

```bash
# Always use pty:true when running coding agents
bash pty:true command:"codex exec 'Your prompt'"
```

## Quick Start

```bash
# Quick chat (Codex needs a git repo)
SCRATCH=$(mktemp -d) && cd $SCRATCH && git init && codex exec "Your prompt"

# In a real project
bash pty:true workdir:~/project command:"codex exec 'Add error handling'"
```

## Codex CLI

```bash
# One-shot execution
bash pty:true workdir:~/project command:"codex exec --full-auto 'Build a dark mode toggle'"

# Background for longer work
bash pty:true workdir:~/project background:true command:"codex --yolo 'Refactor auth module'"
```

Flags:
- `exec "prompt"` - One-shot execution
- `--full-auto` - Sandboxed but auto-approves
- `--yolo` - No sandbox, no approvals (fastest)

## Claude Code

```bash
bash pty:true workdir:~/project command:"claude 'Your task'"
```

## OpenCode

```bash
bash pty:true workdir:~/project command:"opencode run 'Your task'"
```

## Pi Coding Agent

```bash
# Install: npm install -g @mariozechner/pi-coding-agent
bash pty:true workdir:~/project command:"pi 'Your task'"
bash pty:true command:"pi -p 'Summarize src/'"
```

## Parallel Issue Fixing with Git Worktrees

```bash
# Create worktrees
git worktree add -b fix/issue-78 /tmp/issue-78 main
git worktree add -b fix/issue-99 /tmp/issue-99 main

# Launch agents
bash pty:true workdir:/tmp/issue-78 background:true command:"codex --yolo 'Fix issue #78'"
bash pty:true workdir:/tmp/issue-99 background:true command:"codex --yolo 'Fix issue #99'"

# Monitor
process action:list
process action:log sessionId:XXX

# Cleanup
git worktree remove /tmp/issue-78
```

## Rules

1. Always use `pty:true`
2. Be patient - don't kill slow sessions
3. Monitor with `process:log`
4. Use `--full-auto` for building, vanilla for reviewing
