---
name: "1password"
description: "Use 1Password CLI (op) for secrets management"
enabled: false
trigger: manual
---

# 1Password CLI

Use `op` to read and inject secrets securely.

## Setup

```bash
brew install 1password-cli
```

Enable desktop app integration and unlock the app before using CLI.

## Workflow

1. Check CLI: `op --version`
2. Sign in: `op signin`
3. Verify: `op whoami`

## REQUIRED: tmux Session

The `op` CLI needs a persistent TTY. Always run in a dedicated tmux session:

```bash
SOCKET_DIR="${TMPDIR:-/tmp}/pilot-tmux-sockets"
mkdir -p "$SOCKET_DIR"
SOCKET="$SOCKET_DIR/pilot-op.sock"
SESSION="op-auth-$(date +%Y%m%d-%H%M%S)"

tmux -S "$SOCKET" new -d -s "$SESSION" -n shell
tmux -S "$SOCKET" send-keys -t "$SESSION":0.0 -- "op signin --account my.1password.com" Enter
tmux -S "$SOCKET" send-keys -t "$SESSION":0.0 -- "op whoami" Enter
tmux -S "$SOCKET" send-keys -t "$SESSION":0.0 -- "op vault list" Enter
tmux -S "$SOCKET" capture-pane -p -J -t "$SESSION":0.0 -S -200
tmux -S "$SOCKET" kill-session -t "$SESSION"
```

## Common Commands

- List vaults: `op vault list`
- List items: `op item list`
- Get item: `op item get "Item Name"`
- Read field: `op read "op://Vault/Item/Field"`

## Inject Secrets

```bash
# Run command with secrets injected
op run --env-file=.env.tpl -- ./my-script.sh

# Inject into file
op inject -i template.env -o .env
```

## Guardrails

- Never paste secrets into logs, chat, or code
- Prefer `op run` / `op inject` over writing secrets to disk
- If sign-in fails, re-run `op signin` and authorize in the app