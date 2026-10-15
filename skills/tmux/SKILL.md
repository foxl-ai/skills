---
name: tmux
description: "Drive interactive programs (REPLs, TUIs, other coding agent CLIs) in detached tmux sessions that outlive Foxl, using send-keys and capture-pane through exec. Use when a session must survive a Foxl restart, several programs must run side by side, or the user works in tmux themselves; otherwise prefer the built-in terminal tool."
enabled: false
platforms: [darwin, linux]
requires: [tmux]
tags: shell, terminal, automation
---

# tmux via exec

First choice for one interactive program is the built-in `terminal` tool (real PTY: `spawn`, `write`, `read`). Use tmux when you need detached sessions that keep running independently, or many at once.

Install if missing (the user runs it): `brew install tmux` or the distro package (`apt install tmux`, `dnf install tmux`).

## Setup

Use a private socket so you never touch the user's own tmux server:

```bash
SOCK="${TMPDIR:-/tmp}/foxl-tmux.sock"
tmux -S "$SOCK" new-session -d -s work -x 200 -y 50
tmux -S "$SOCK" has-session -t work && echo ok
```

Shell variables do not persist between `exec` calls; repeat the `SOCK=` line (or the literal path) in each command.

## Send input

```bash
tmux -S "$SOCK" send-keys -t work -l -- 'python3 -q'   # -l: literal text
tmux -S "$SOCK" send-keys -t work Enter                # named key, separate call
tmux -S "$SOCK" send-keys -t work C-c                  # interrupt
```

Send text and `Enter` as two calls; TUIs often drop an Enter glued to pasted text.

## Read output

```bash
tmux -S "$SOCK" capture-pane -p -J -t work -S -200     # last 200 lines, wrapped lines joined
```

Poll instead of sleeping long: capture, check for the prompt or the text you expect, repeat after a short `sleep 2`. For a full log, `tmux -S "$SOCK" pipe-pane -o -t work 'cat >> /tmp/work.log'`.

## Several sessions

```bash
for n in a b c; do tmux -S "$SOCK" new-session -d -s "job-$n" -c "$HOME/projects/$n"; done
tmux -S "$SOCK" list-sessions
```

Targets are `session`, `session:window` or `session:window.pane`.

## Hand off and clean up

The user can watch with `tmux -S <socket path> attach -t work` (detach: Ctrl-b then d). When finished:

```bash
tmux -S "$SOCK" kill-session -t work
tmux -S "$SOCK" kill-server        # all sessions on this private socket only
```
