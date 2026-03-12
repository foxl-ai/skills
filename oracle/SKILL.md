---
name: oracle
description: Bundle prompt + files for one-shot LLM requests with repo context
trigger: manual
requires: [oracle]
---

# oracle

Bundle your prompt + selected files into one request for another model.

## Setup

```bash
npx -y @steipete/oracle --help
```

## Quick Start

### Preview (no tokens)
```bash
oracle --dry-run summary -p "<task>" --file "src/**" --file "!**/*.test.*"
oracle --dry-run full -p "<task>" --file "src/**"
```

### Token Check
```bash
oracle --dry-run summary --files-report -p "<task>" --file "src/**"
```

### Browser Run (GPT-5.2 Pro)
```bash
oracle --engine browser --model gpt-5.2-pro -p "<task>" --file "src/**"
```

### Manual Paste
```bash
oracle --render --copy -p "<task>" --file "src/**"
```

## File Patterns

```bash
--file "src/**"                    # Include directory
--file src/index.ts                # Include file
--file "src/**" --file "!**/*.test.ts"  # Exclude tests
```

Default ignored: `node_modules`, `dist`, `.git`, `build`, `tmp`

## Engines

- `browser` - GPT + Gemini via browser automation
- `api` - Direct API (requires OPENAI_API_KEY)

## Sessions

```bash
oracle status --hours 72           # List sessions
oracle session <id> --render       # Reattach to session
```

Sessions stored in `~/.oracle/sessions`

## Prompt Tips

Include:
- Project briefing (stack, build commands)
- Key directories and entrypoints
- Exact question + error text
- Constraints and desired output
