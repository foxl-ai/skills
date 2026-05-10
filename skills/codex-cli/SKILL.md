---
name: "codex-cli"
description: "Use Codex CLI with your OpenAI subscription"
enabled: false
trigger: manual
---

# Codex CLI

Use OpenAI's models directly in Foxl through the Codex CLI. Authenticate with your OpenAI account — Foxl consumes zero relay credits.

## Setup

```bash
# Install Codex CLI
npm install -g @openai/codex
# or
brew install --cask codex

# Authenticate (choose one)
# Option A: OAuth login
codex login

# Option B: API key
export OPENAI_API_KEY=your-key-here

# Verify
codex exec "hello"
```

## How It Works

Foxl spawns the `codex` CLI as a subprocess with JSON output. Your OpenAI subscription or API key handles billing — Foxl consumes zero relay credits.

The CLI is invoked with:
```
codex exec --json -m o4-mini "prompt"
```

## Available Models

| Model ID | Description |
|----------|-------------|
| `codex-cli/o3` | o3 — advanced reasoning, complex tasks |
| `codex-cli/o4-mini` | o4 Mini — fast reasoning, cost-effective |
| `codex-cli/gpt-4.1` | GPT 4.1 — 1M context, general purpose |

## Credential Detection

Foxl checks these sources (in order):

1. **Environment variable**: `OPENAI_API_KEY`
2. **Auth file**: `~/.codex/auth.json`
3. **macOS Keychain**: service "Codex Auth"

## Features

- JSONL streaming (via `exec --json`)
- Reasoning model support (o3, o4-mini)
- Tool call events in stream
- Auto-detect credentials on startup

## Troubleshooting

### "Codex CLI not configured"
Run `codex login` or set `OPENAI_API_KEY` environment variable.

### 401 Unauthorized
Your OpenAI API key may be invalid or expired. Run `codex login` again or check your key at platform.openai.com.

### Model not found
Some models require specific API tier access. Check your OpenAI account for available models.
