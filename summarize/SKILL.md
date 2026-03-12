---
name: summarize
description: Summarize URLs, articles, YouTube videos, and local files
trigger: manual
enabled: true
requires:
  bins: ["summarize"]
---

# Summarize Skill

Summarize or extract text from URLs, podcasts, and local files.

## When to use
- User asks "what's this link about?"
- User asks to summarize a URL or article
- User asks to transcribe a YouTube video
- User shares a PDF or document to summarize

## How to execute

### Quick start

```bash
summarize "https://example.com" --model google/gemini-3-flash-preview
summarize "/path/to/file.pdf" --model google/gemini-3-flash-preview
summarize "https://youtu.be/dQw4w9WgXcQ" --youtube auto
```

### YouTube transcript

Extract transcript only:
```bash
summarize "https://youtu.be/VIDEO_ID" --youtube auto --extract-only
```

### Model + API Keys

Set the API key for your chosen provider:
- OpenAI: `OPENAI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- Google: `GEMINI_API_KEY`

### Useful flags

- `--length short|medium|long|xl|xxl|<chars>` - Control output length
- `--max-output-tokens <count>` - Limit tokens
- `--extract-only` - Just extract, don't summarize
- `--json` - Machine readable output

## Notes
- Default model is `google/gemini-3-flash-preview`
- For blocked sites, set `FIRECRAWL_API_KEY`
- For YouTube fallback, set `APIFY_API_TOKEN`
