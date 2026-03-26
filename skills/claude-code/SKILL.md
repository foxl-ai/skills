---
name: "claude-code"
description: "Use Claude Code CLI with your Claude Pro/Max subscription"
enabled: true
trigger: manual
---

# Claude Code CLI

Use your Claude Pro or Max subscription directly in Foxl through the Claude Code CLI. No API key needed — authenticate once with SSO and Foxl auto-detects your credentials.

## Setup

```bash
# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Authenticate (opens browser for SSO login)
claude auth login

# Verify
claude --version
```

## How It Works

Foxl spawns the `claude` CLI as a subprocess with streaming JSON output. Your subscription handles all authentication and billing — Foxl consumes zero relay credits.

The CLI is invoked with:
```
claude -p "prompt" --output-format stream-json --verbose --bare --include-partial-messages --dangerously-skip-permissions -m sonnet
```

## Available Models

| Model ID | Description |
|----------|-------------|
| `claude-code/opus` | Opus 4.6 — most capable, complex reasoning |
| `claude-code/sonnet` | Sonnet 4.6 — balanced speed and quality |
| `claude-code/haiku` | Haiku 4.5 — fastest, simple tasks |

## Credential Detection

Foxl checks these locations (in order):

1. **macOS Keychain**: service "Claude Code-credentials"
2. **Credential file**: `~/.claude/.credentials.json` (`claudeAiOauth` field)
3. **Windows Credential Manager**: "Claude Code-credentials"

## Features

- Token-level streaming (via `stream_event` / `content_block_delta`)
- Thinking/reasoning separation (displayed as collapsible reasoning in UI)
- Auto-detect credentials on startup
- No API key management needed

## Troubleshooting

### "Claude Code not configured"
Run `claude auth login` to authenticate. Make sure `claude` is in your PATH.

### Slow first response
The first call may be slower as the CLI initializes. Subsequent calls are faster.

### Token expired
Run `claude auth login` again. The CLI handles token refresh automatically in most cases.
