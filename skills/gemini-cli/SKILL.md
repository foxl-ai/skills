---
name: gemini-cli
description: "Set up and troubleshoot Foxl's Gemini CLI model provider, which runs chats on Google's gemini CLI with the user's own Gemini API key or Google account instead of Foxl credits. Use when the user asks how to use Gemini models through the CLI, or when Gemini CLI models are missing or failing in Foxl."
enabled: false
requires: [gemini]
tags: ai, gemini, google, provider
---

# Gemini CLI provider

Foxl runs the official `gemini` binary headless (`gemini -p ... --output-format stream-json -y -m <model>`) and streams its answer into the chat. Google bills the user's key or account; Foxl uses no credits. The CLI's own tools do not become Foxl tools.

## Setup

1. Install the CLI (the user runs this): `npm install -g @google/gemini-cli`. Homebrew's `gemini-cli` formula can lag several releases behind npm, and an old CLI may reject the newest model ids. Check with `gemini --version`.
2. Authenticate, one of (https://geminicli.com/docs/get-started/authentication/):
   - API key (recommended): create one at https://aistudio.google.com/apikey, run `gemini` once in a terminal, choose "Use Gemini API key" and paste it so the CLI stores it. A `GEMINI_API_KEY` exported only in a shell profile may not reach Foxl's background service.
   - Sign in with Google: run `gemini` in a terminal and pick it.
   - Vertex AI: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` and gcloud credentials.
3. Verify outside Foxl: `gemini -p "say pong" -o json`.
4. Pick a "(CLI)" Gemini model in Foxl's model picker. Foxl looks for the CLI again every 30 seconds, so a fresh install appears without a restart.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| No Gemini CLI models | `gemini` not on PATH for Foxl, or no auth found (`GEMINI_API_KEY`, `~/.gemini/oauth_creds.json`, `~/.gemini/settings.json`, Vertex/gcloud). Fix install or auth, wait 30 s. |
| Exit 41 | No auth method; set up step 2. |
| Exit 55 | Untrusted folder. Current Foxl trusts its own folder; on an old build update Foxl or add the folder in `~/.gemini/trustedFolders.json`. |
| 401 `API key not valid` | Wrong or old key. The CLI keeps a stored key; run `gemini`, then `/auth`, and enter the new one. |
| 429 or quota exhausted | Free-tier limit. Wait, pick a Flash-Lite model, or use a paid key. |
| Model not found | The CLI is older than the model; upgrade the CLI or choose another model. |

Models change often; the current list is at https://ai.google.dev/gemini-api/docs/models. With an API key the CLI may silently upgrade a Flash or Flash-Lite id to the newest one of that tier.
