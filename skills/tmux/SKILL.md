---
name: tmux
description: Remote-control tmux sessions for interactive CLIs
trigger: manual
platforms: [darwin, linux]
requires: [tmux]
---

# tmux Skill

Use tmux for interactive TTY sessions. Prefer exec background mode for non-interactive tasks.

## Quickstart

```bash
SOCKET_DIR="${TMPDIR:-/tmp}/pilot-tmux-sockets"
mkdir -p "$SOCKET_DIR"
SOCKET="$SOCKET_DIR/pilot.sock"
SESSION=pilot-python

tmux -S "$SOCKET" new -d -s "$SESSION" -n shell
tmux -S "$SOCKET" send-keys -t "$SESSION":0.0 -- 'python3 -q' Enter
tmux -S "$SOCKET" capture-pane -p -J -t "$SESSION":0.0 -S -200
```

## Targeting

- Format: `session:window.pane` (defaults to `:0.0`)
- List sessions: `tmux -S "$SOCKET" list-sessions`
- List panes: `tmux -S "$SOCKET" list-panes -a`

## Sending Input

```bash
# Literal text
tmux -S "$SOCKET" send-keys -t target -l -- "$cmd"

# Control keys
tmux -S "$SOCKET" send-keys -t target C-c

# For TUI apps (Claude Code/Codex), send text and Enter separately
tmux -S "$SOCKET" send-keys -t target -l -- "$cmd" && sleep 0.1 && tmux -S "$SOCKET" send-keys -t target Enter
```

## Watching Output

```bash
# Capture recent history
tmux -S "$SOCKET" capture-pane -p -J -t target -S -200

# Attach (detach with Ctrl+b d)
tmux -S "$SOCKET" attach -t "$SESSION"
```

## Orchestrating Coding Agents

```bash
SOCKET="${TMPDIR:-/tmp}/codex-army.sock"

# Create multiple sessions
for i in 1 2 3; do
  tmux -S "$SOCKET" new-session -d -s "agent-$i"
done

# Launch agents
tmux -S "$SOCKET" send-keys -t agent-1 "cd /tmp/project1 && codex --yolo 'Fix bug X'" Enter
tmux -S "$SOCKET" send-keys -t agent-2 "cd /tmp/project2 && codex --yolo 'Fix bug Y'" Enter

# Poll for completion
for sess in agent-1 agent-2; do
  if tmux -S "$SOCKET" capture-pane -p -t "$sess" -S -3 | grep -q "❯"; then
    echo "$sess: DONE"
  fi
done
```

## Cleanup

```bash
tmux -S "$SOCKET" kill-session -t "$SESSION"
tmux -S "$SOCKET" kill-server  # Kill all
```
