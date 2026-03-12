---
name: whisper
description: Local speech-to-text with OpenAI Whisper CLI
trigger: manual
requires: [whisper]
---

# Whisper (Local STT)

Transcribe audio locally using OpenAI Whisper.

## Setup

```bash
brew install openai-whisper
```

Models download to `~/.cache/whisper` on first run.

## Transcribe

```bash
whisper /path/audio.mp3 --model medium --output_format txt --output_dir .
whisper /path/audio.m4a --model large --output_format srt
```

## Translate to English

```bash
whisper /path/audio.m4a --task translate --output_format srt
```

## Models

- `tiny`, `base`, `small` - Fast, lower accuracy
- `medium` - Good balance
- `large`, `turbo` - Best accuracy, slower

## Output Formats

- `txt` - Plain text
- `srt` - Subtitles with timestamps
- `vtt` - WebVTT format
- `json` - Detailed JSON with word-level timestamps
