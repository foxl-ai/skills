---
name: gws
description: Google Workspace CLI - Gmail, Calendar, Drive, Sheets, Docs, Chat, Tasks, Meet, and more
enabled: true
requires: [gws]
---

# gws (Google Workspace CLI)

One CLI for all of Google Workspace. Built for humans and AI agents.
Dynamically built from Google Discovery Service — when Google adds an API endpoint, gws picks it up automatically.

## Setup

```bash
# Install
npm install -g @googleworkspace/cli
# or: brew install googleworkspace-cli

# Auth (one-time)
gws auth setup        # creates GCP project, enables APIs, logs you in
gws auth login        # subsequent logins (scope selection)
gws auth login -s drive,gmail,sheets,calendar,docs  # selective scopes
```

## CLI Syntax

```bash
gws <service> <resource> <method> [flags]
gws <service> +<helper> [flags]           # helper commands (prefixed with +)
```

### Global Flags

| Flag | Description |
|------|-------------|
| `--format <FORMAT>` | Output: `json` (default), `table`, `yaml`, `csv` |
| `--dry-run` | Preview request without executing |
| `--page-all` | Auto-paginate (NDJSON output) |
| `--page-limit <N>` | Max pages (default: 10) |

## Gmail

```bash
# Send email
gws gmail +send --to alice@example.com --subject "Hello" --body "Hi there"
gws gmail +send --to a@b.com --subject "Report" --body "See attached" --attach ./report.pdf

# Reply / Reply-all / Forward
gws gmail +reply --message-id MSG_ID --body "Thanks!"
gws gmail +reply-all --message-id MSG_ID --body "Noted"
gws gmail +forward --message-id MSG_ID --to bob@example.com

# Read a message
gws gmail +read --message-id MSG_ID

# Triage inbox
gws gmail +triage

# Watch for new emails (streaming)
gws gmail +watch

# Search (API method)
gws gmail users messages list --params '{"q": "newer_than:7d", "maxResults": 10}'
```

## Calendar

```bash
# Today's agenda
gws calendar +agenda --today

# This week
gws calendar +agenda --week

# Next N days
gws calendar +agenda --days 3

# Create event
gws calendar +insert --summary "Team Sync" --start "2026-03-25T10:00:00" --end "2026-03-25T11:00:00"

# List events (API method)
gws calendar events list --params '{"calendarId": "primary", "timeMin": "2026-03-22T00:00:00Z", "maxResults": 10}'
```

## Drive

```bash
# List recent files
gws drive files list --params '{"pageSize": 10}'

# Search files
gws drive files list --params '{"q": "name contains '\''report'\''", "pageSize": 10}'

# Upload a file
gws drive +upload ./report.pdf --name "Q1 Report"

# Download a file
gws drive files get --params '{"fileId": "FILE_ID", "alt": "media"}' -o ./downloaded.pdf
```

## Sheets

```bash
# Read cells
gws sheets +read --spreadsheet SPREADSHEET_ID --range 'Sheet1!A1:D10'

# Read entire sheet
gws sheets +read --spreadsheet SPREADSHEET_ID --range Sheet1

# Append rows
gws sheets +append --spreadsheet SPREADSHEET_ID --values 'Alice,100,true'
gws sheets +append --spreadsheet SPREADSHEET_ID --json-values '[["Name","Score"],["Bob",95]]'

# Update cells (API method)
gws sheets spreadsheets values update \
  --params '{"spreadsheetId": "ID", "range": "Sheet1!A1:B2", "valueInputOption": "USER_ENTERED"}' \
  --json '{"values": [["A","B"],["1","2"]]}'

# Create spreadsheet
gws sheets spreadsheets create --json '{"properties": {"title": "New Sheet"}}'
```

## Docs

```bash
# Read document
gws docs documents get --params '{"documentId": "DOC_ID"}'

# Append text
gws docs +write --document DOC_ID --text 'Hello, world!'

# Create document
gws docs documents create --json '{"title": "New Doc"}'
```

## Chat

```bash
# Send message to a space
gws chat +send --space SPACE_ID --text "Deploy complete."

# List spaces
gws chat spaces list
```

## Tasks

```bash
# List task lists
gws tasks tasklists list

# List tasks
gws tasks tasks list --params '{"tasklist": "TASKLIST_ID"}'
```

## Workflows (Helper Commands)

```bash
# Morning standup summary (today's meetings + open tasks)
gws workflow +standup-report

# Meeting prep (agenda, attendees, linked docs)
gws workflow +meeting-prep

# Weekly digest (meetings + unread email count)
gws workflow +weekly-digest

# Convert email to task
gws workflow +email-to-task --message-id MSG_ID

# Announce a Drive file in Chat
gws workflow +file-announce --file FILE_ID --space SPACE_ID
```

## Discovery / Introspection

```bash
# Browse any service
gws sheets --help
gws gmail --help

# Inspect method schema
gws schema sheets.spreadsheets.values.get
gws schema drive.files.list
```

## Notes

- All output is structured JSON by default
- Use `--dry-run` before destructive operations
- Sheets ranges with `!` must be single-quoted in bash: `'Sheet1!A1:D10'`
- `gws auth login -s drive,gmail,sheets` for selective scope login
- 100+ agent skills available: see `skills/` in the gws repo
