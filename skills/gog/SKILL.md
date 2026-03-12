---
name: gog
description: Google Workspace CLI - Gmail, Calendar, Drive, Contacts, Sheets, Docs
trigger: manual
requires: [gog]
---

# gog (Google Workspace CLI)

Access Gmail, Calendar, Drive, Contacts, Sheets, and Docs.

## Setup

```bash
brew install steipete/tap/gogcli
gog auth credentials /path/to/client_secret.json
gog auth add you@gmail.com --services gmail,calendar,drive,contacts,docs,sheets
```

## Gmail

```bash
# Search
gog gmail search 'newer_than:7d' --max 10
gog gmail messages search "in:inbox from:example.com" --max 20

# Send
gog gmail send --to a@b.com --subject "Hi" --body "Hello"
gog gmail send --to a@b.com --subject "Hi" --body-file ./message.txt

# Reply
gog gmail send --to a@b.com --subject "Re: Hi" --body "Reply" --reply-to-message-id <msgId>

# Draft
gog gmail drafts create --to a@b.com --subject "Hi" --body-file ./message.txt
gog gmail drafts send <draftId>
```

## Calendar

```bash
# List events
gog calendar events <calendarId> --from <iso> --to <iso>

# Create event
gog calendar create <calendarId> --summary "Title" --from <iso> --to <iso>
gog calendar create <calendarId> --summary "Title" --from <iso> --to <iso> --event-color 7

# Update event
gog calendar update <calendarId> <eventId> --summary "New Title"

# Show colors
gog calendar colors
```

## Drive

```bash
gog drive search "query" --max 10
```

## Contacts

```bash
gog contacts list --max 20
```

## Sheets

```bash
gog sheets get <sheetId> "Tab!A1:D10" --json
gog sheets update <sheetId> "Tab!A1:B2" --values-json '[["A","B"],["1","2"]]'
gog sheets append <sheetId> "Tab!A:C" --values-json '[["x","y","z"]]'
gog sheets clear <sheetId> "Tab!A2:Z"
```

## Docs

```bash
gog docs export <docId> --format txt --out /tmp/doc.txt
gog docs cat <docId>
```

## Notes

- Set `GOG_ACCOUNT=you@gmail.com` to avoid repeating `--account`
- Use `--json` for scripting
