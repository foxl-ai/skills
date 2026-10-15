---
name: gws
description: "Google Workspace from the command line with the gws CLI: Gmail, Calendar, Drive, Sheets, Docs, Chat, Tasks and more. Use when the user asks about Gmail, Google Calendar, Drive files, Google Sheets or Docs, or a Google account's mail, meetings or tasks."
enabled: true
tags: google, gmail, calendar, drive, sheets, docs, workspace
requires: [gws]
---

# gws (Google Workspace CLI)

https://github.com/googleworkspace/cli (npm `@googleworkspace/cli`, Homebrew `googleworkspace-cli`; not an official Google product). Commands mirror the Google REST APIs, plus `+helper` shortcuts. Output is JSON by default.

## Setup (user runs these in their own terminal; sign-in opens a browser)

```bash
npm install -g @googleworkspace/cli     # or: brew install googleworkspace-cli
gws auth setup --login                  # needs gcloud; creates the OAuth client, then signs in
gws auth login -s gmail,calendar,drive  # later sign-ins, limited to some services
gws auth status                         # the agent can run this to check
```

Exit code 2 means not signed in: ask the user to run `gws auth login`, do not try to sign in for them.

## Rules

- Before sending, replying, forwarding, deleting or creating anything visible to others, show the draft and get confirmation. `--dry-run` shows the request without sending; `--draft` saves Gmail mail as a draft.
- Quote JSON in single quotes; Sheets ranges with `!` too: `'Sheet1!A1:D10'`.
- `--output` and `-a/--attach` refuse paths outside the current directory: set the `exec` `workdir` to the file's folder and pass a relative path.
- `--page-all` streams one JSON line per page (max `--page-limit`, default 10). `--format table|csv|yaml` for readable output.
- Unsure of a method or field: `gws <service> --help`, `gws schema <service.resource.method>`.

## Gmail

```bash
gws gmail +triage --max 20                             # unread summary; --query 'from:bob newer_than:7d'
gws gmail users messages list --params '{"userId": "me", "q": "newer_than:7d", "maxResults": 10}'
gws gmail +read --id MSG_ID --headers
gws gmail +send --to a@example.com --subject 'Hi' --body 'Text' [-a file.pdf] [--cc ...] [--html] [--draft]
gws gmail +reply --message-id MSG_ID --body 'Thanks'   # +reply-all same flags
gws gmail +forward --message-id MSG_ID --to b@example.com --body 'FYI'
```

## Calendar

```bash
gws calendar +agenda --today          # --tomorrow, --week, --days 3, --timezone Europe/Berlin
gws calendar +insert --summary 'Sync' --start 2026-10-20T10:00:00-07:00 --end 2026-10-20T10:30:00-07:00 \
  --attendee a@example.com --meet
gws calendar events list --params '{"calendarId": "primary", "timeMin": "2026-10-15T00:00:00Z", "singleEvents": true, "orderBy": "startTime", "maxResults": 10}'
```

Give times with an explicit offset or `Z`.

## Drive

```bash
gws drive files list --params '{"q": "name contains '\''report'\'' and trashed = false", "pageSize": 10, "fields": "files(id,name,mimeType,modifiedTime)"}'
gws drive +upload ./report.pdf --name 'Q3 Report' [--parent FOLDER_ID]
gws drive files get --params '{"fileId": "FILE_ID", "alt": "media"}' --output ./file.pdf
gws drive files export --params '{"fileId": "DOC_ID", "mimeType": "text/plain"}' --output ./doc.txt   # Google Docs/Sheets
```

## Sheets and Docs

```bash
gws sheets +read --spreadsheet SHEET_ID --range 'Sheet1!A1:D10'
gws sheets +append --spreadsheet SHEET_ID --json-values '[["Bob", 95]]'
gws sheets spreadsheets values update --params '{"spreadsheetId": "ID", "range": "Sheet1!A1:B2", "valueInputOption": "USER_ENTERED"}' \
  --json '{"values": [["A","B"],["1","2"]]}'
gws sheets spreadsheets create --json '{"properties": {"title": "New sheet"}}'
gws docs documents get --params '{"documentId": "DOC_ID"}'
gws docs +write --document DOC_ID --text 'Appended paragraph'
gws docs documents create --json '{"title": "New doc"}'
```

## Chat, Tasks, workflows

```bash
gws chat spaces list
gws chat +send --space spaces/AAAA --text 'Deploy complete'
gws tasks tasklists list
gws tasks tasks list --params '{"tasklist": "TASKLIST_ID"}'
gws workflow +standup-report      # today's meetings + open tasks
gws workflow +meeting-prep        # next meeting: agenda, attendees, linked docs
gws workflow +weekly-digest
gws workflow +email-to-task --message-id MSG_ID
gws workflow +file-announce --file-id FILE_ID --space spaces/AAAA
```

Also available: `slides`, `forms`, `keep`, `meet`, `people`, `classroom`, `script` (see `gws --help`).
