---
name: bear-notes
description: Create, search, and manage Bear notes via grizzly CLI
trigger: manual
platforms: [darwin]
requires: [grizzly]
---

# Bear Notes (grizzly)

Manage Bear notes from the terminal using `grizzly`.

## Setup

```bash
go install github.com/tylerwince/grizzly/cmd/grizzly@latest
```

For operations requiring a token (add-text, tags):
1. Open Bear → Help → API Token → Copy Token
2. Save: `echo "YOUR_TOKEN" > ~/.config/grizzly/token`

## Create a Note

```bash
echo "Note content here" | grizzly create --title "My Note" --tag work
grizzly create --title "Quick Note" --tag inbox < /dev/null
```

## Open/Read a Note

```bash
grizzly open-note --id "NOTE_ID" --enable-callback --json
```

## Append Text

```bash
echo "Additional content" | grizzly add-text --id "NOTE_ID" --mode append --token-file ~/.config/grizzly/token
```

## List Tags

```bash
grizzly tags --enable-callback --json --token-file ~/.config/grizzly/token
```

## Search Notes

```bash
grizzly open-tag --name "work" --enable-callback --json
```

## Options

- `--dry-run` - Preview URL without executing
- `--print-url` - Show the x-callback-url
- `--enable-callback` - Wait for Bear's response
- `--json` - Output as JSON
- `--token-file PATH` - Path to Bear API token

## Configuration

Create `~/.config/grizzly/config.toml`:

```toml
token_file = "~/.config/grizzly/token"
callback_url = "http://127.0.0.1:42123/success"
timeout = "5s"
```
