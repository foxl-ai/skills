---
name: gemini
description: Gemini CLI for one-shot Q&A and generation
trigger: manual
requires: [gemini]
---

# Gemini CLI

Use Gemini in one-shot mode.

## Setup

```bash
brew install gemini-cli
gemini  # First run: follow login flow
```

## Quick Start

```bash
gemini "Answer this question..."
gemini --model gemini-2.0-flash "Prompt..."
gemini --output-format json "Return JSON"
```

## Extensions

```bash
gemini --list-extensions
gemini extensions <command>
```

## Notes

- Use positional prompt for one-shot mode
- Avoid interactive mode for automation
- Avoid `--yolo` for safety
