---
name: whisper-api
description: Transcribe audio via OpenAI Whisper API (cloud)
trigger: manual
requires: [curl, OPENAI_API_KEY]
---

# OpenAI Whisper API

Transcribe audio via OpenAI's cloud API.

## Quick Start

```bash
curl https://api.openai.com/v1/audio/transcriptions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -F file="@/path/to/audio.m4a" \
  -F model="whisper-1"
```

## With Options

```bash
curl https://api.openai.com/v1/audio/transcriptions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -F file="@/path/to/audio.m4a" \
  -F model="whisper-1" \
  -F language="en" \
  -F response_format="json" \
  -F prompt="Speaker names: Peter, Daniel"
```

## Response Formats

- `json` - JSON with text
- `text` - Plain text
- `srt` - Subtitles
- `verbose_json` - Detailed with timestamps
- `vtt` - WebVTT format

## Notes

- Model: `whisper-1`
- Supported formats: mp3, mp4, mpeg, mpga, m4a, wav, webm
- Max file size: 25 MB
