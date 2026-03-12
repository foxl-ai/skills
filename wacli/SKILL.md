---
name: wacli
description: Send WhatsApp messages or search/sync WhatsApp history
trigger: manual
requires: [wacli]
---

# wacli

Send WhatsApp messages to others or sync/search history.

## Setup

```bash
brew install steipete/tap/wacli
```

## Auth & Sync

```bash
wacli auth              # QR login + initial sync
wacli sync --follow     # Continuous sync
wacli doctor            # Check status
```

## Find Chats & Messages

```bash
wacli chats list --limit 20 --query "name or number"
wacli messages search "query" --limit 20 --chat <jid>
wacli messages search "invoice" --after 2025-01-01 --before 2025-12-31
```

## History Backfill

```bash
wacli history backfill --chat <jid> --requests 2 --count 50
```

## Send Messages

```bash
# Text
wacli send text --to "+14155551212" --message "Hello!"

# Group
wacli send text --to "1234567890-123456789@g.us" --message "Running late"

# File
wacli send file --to "+14155551212" --file /path/agenda.pdf --caption "Agenda"
```

## JID Formats

- Direct: `<number>@s.whatsapp.net`
- Group: `<id>@g.us`

Use `wacli chats list` to find JIDs.

## Safety

- Require explicit recipient + message text
- Confirm before sending
- Store dir: `~/.wacli`
