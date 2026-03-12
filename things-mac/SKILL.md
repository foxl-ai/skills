---
name: things-mac
description: Manage Things 3 via things CLI on macOS
trigger: manual
platforms: [darwin]
requires: [things]
---

# Things 3 CLI

Read and manage Things 3 tasks from the terminal.

## Setup

```bash
GOBIN=/opt/homebrew/bin go install github.com/ossianhempel/things3-cli/cmd/things@latest
```

Grant Full Disk Access to Terminal for DB reads.

## Read-only (DB)

```bash
things inbox --limit 50
things today
things upcoming
things search "query"
things projects
things areas
things tags
```

## Add Tasks

```bash
things add "Buy milk"
things add "Buy milk" --notes "2% + bananas"
things add "Book flights" --list "Travel"
things add "Pack charger" --list "Travel" --heading "Before"
things add "Call dentist" --tags "health,phone"
things add "Trip prep" --checklist-item "Passport" --checklist-item "Tickets"
```

With due date:
```bash
things add "Title" --notes "..." --when today --deadline 2026-01-02
```

## Update Tasks (needs auth token)

Get ID first:
```bash
things search "milk" --limit 5
```

Set `THINGS_AUTH_TOKEN` or use `--auth-token`:
```bash
things update --id <UUID> --auth-token <TOKEN> "New title"
things update --id <UUID> --auth-token <TOKEN> --notes "New notes"
things update --id <UUID> --auth-token <TOKEN> --completed
things update --id <UUID> --auth-token <TOKEN> --canceled
```

## Preview Mode

```bash
things --dry-run add "Title"
things --dry-run update --id <UUID> --completed
```
