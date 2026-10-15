---
name: gemini
description: "Ask Google's Gemini CLI a one-shot question from the shell (gemini -p) for a second opinion, a long-context read of big files or folders, or a quick generation, billed to the user's own Gemini key or Google account. Use only when the user asks for Gemini or a second model."
enabled: false
requires: [gemini]
tags: ai, gemini, google, cli
---

# Gemini CLI, one-shot

Run with `exec`. `-p` is headless mode; without it the CLI starts an interactive session and hangs.

```bash
gemini -p "Explain this error: ..." --approval-mode plan --skip-trust -o json
cat big.log | gemini -p "Summarize the failures" --approval-mode plan --skip-trust
gemini -p "Review the code in this folder for bugs" --approval-mode plan --skip-trust \
  --include-directories ./src -m gemini-3.1-pro-preview
```

- `--approval-mode plan` keeps the CLI read-only (no file edits or shell commands). Do not use `-y` / `--yolo` from here; if the user wants Gemini to change files, run it in the `terminal` tool where they can see and approve it.
- `--skip-trust` trusts the working folder for this run; without it a folder the user never trusted makes headless mode exit 55.
- `-o json` returns `{"response": ..., "stats": ..., "error": ...}`; read `response`. `-o stream-json` emits JSONL events.
- `-m` picks the model. Omit it to use the CLI's default. Current ids per https://ai.google.dev/gemini-api/docs/models: `gemini-3.8-flash` (fast), `gemini-3.5-flash-lite` (cheapest), `gemini-3.1-pro-preview` (strongest reasoning). An older CLI may not know the newest ids: upgrade it rather than guessing.
- Give it a long `timeout` (for example 300) for big inputs.

Exit codes: 0 ok, 1 API or general error, 41 no auth configured, 42 bad input, 53 turn limit, 55 untrusted folder. Errors are on stderr.

## Setup (the user does this)

```bash
npm install -g @google/gemini-cli     # or: brew install gemini-cli (may lag behind npm)
```

Auth, one of (https://geminicli.com/docs/get-started/authentication/):

- API key from https://aistudio.google.com/apikey in `GEMINI_API_KEY`. Best for use from Foxl.
- Sign in with Google: run `gemini` once in a terminal and choose it. Headless runs reuse the cached login.
- Vertex AI: `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` plus gcloud credentials or `GOOGLE_API_KEY`.

Free-tier keys have low daily quotas; a 429 means wait or use a paid key.
