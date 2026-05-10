---
name: "gemini-cli"
description: "Use Gemini CLI with your Google AI subscription or API key"
enabled: false
---

# Gemini CLI

Use Google's Gemini models directly in Foxl through the Gemini CLI. Authenticate with your Google account or API key — Foxl consumes zero relay credits.

## Setup

```bash
# Install Gemini CLI
npm install -g @google/gemini-cli

# Authenticate (choose one)
# Option A: Google account SSO
gemini auth login

# Option B: API key (from aistudio.google.com)
export GEMINI_API_KEY=your-key-here

# Verify
gemini -p "hello" --output-format json
```

## How It Works

Foxl spawns the `gemini` CLI as a subprocess with streaming JSON output. Your Google subscription or API key handles billing — Foxl consumes zero relay credits.

The CLI is invoked with:
```
gemini -p "prompt" --output-format stream-json -y -m gemini-2.5-flash
```

The `-y` flag auto-approves tool calls (YOLO mode) for non-interactive use.

## Available Models

| Model ID | Description |
|----------|-------------|
| `gemini-cli/gemini-2.5-pro` | Gemini 2.5 Pro — 1M context, deep analysis |
| `gemini-cli/gemini-2.5-flash` | Gemini 2.5 Flash — 1M context, fast and cost-effective |

## Credential Detection

Foxl checks these sources (in order):

1. **Environment variable**: `GEMINI_API_KEY`
2. **Settings file**: `~/.gemini/settings.json` (auth method config)
3. **Google Cloud auth**: `~/.config/gcloud/application_default_credentials.json`

## Features

- Token-level streaming (via stream-json output)
- 1M token context window
- Thinking support (Gemini's reasoning mode)
- Auto-detect credentials on startup

## Troubleshooting

### "Gemini CLI not configured"
Run `gemini auth login` or set `GEMINI_API_KEY` environment variable.

### "Please set an Auth method"
Create `~/.gemini/settings.json` with your auth configuration, or set `GEMINI_API_KEY`.

### Model not available
Some models may require specific API access. Check your Google AI Studio account for available models.
