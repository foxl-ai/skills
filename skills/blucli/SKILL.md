---
name: blucli
description: BluOS CLI for Bluesound/NAD player control
trigger: manual
requires: [blu]
---

# blucli (blu)

Control Bluesound/NAD players.

## Setup

```bash
go install github.com/steipete/blucli/cmd/blu@latest
```

## Quick Start

```bash
blu devices              # List devices
blu --device <id> status # Check status
blu play
blu pause
blu stop
blu volume set 15
```

## Target Selection (priority order)

1. `--device <id|name|alias>`
2. `BLU_DEVICE` env var
3. Config default

## Grouping

```bash
blu group status
blu group add --device <id>
blu group remove --device <id>
```

## TuneIn

```bash
blu tunein search "query"
blu tunein play "query"
```

## Notes

- Use `--json` for scripts
- Confirm target device before changing playback
