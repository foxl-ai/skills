---
name: quip
description: "Search, read, create and edit Quip documents and folders through the Quip Automation REST API with curl. Use when the user mentions Quip, a Quip doc, spreadsheet or folder, or asks to file notes into Quip."
enabled: true
tags: quip, documents, docs, notes
requires: [QUIP_API_TOKEN, curl]
---

# Quip

Quip Automation API, reference: https://quip.com/dev/automation/documentation/current

## Setup (user does this once)

1. Get a personal access token at https://quip.com/dev/token (making a new one invalidates the old one).
2. Save it as `QUIP_API_TOKEN` in Foxl (Settings > Connect > Integrations, Quip), or export it in the shell.
3. Base URL is `https://platform.quip.com`. Companies on a private Quip cloud (VPC) use their own host instead, e.g. `https://platform.acme.onquip.com` or `https://platform.quip-acme.com`; ask if the user's Quip URL is not `quip.com`.

## Rules

- Thread = a document, spreadsheet or chat. Its id is in the API responses; the short code in a doc URL (`quip.com/<code>/Title`) also works where the docs say "ID or secret path".
- Confirm before creating, editing or deleting content. Check the target folder first to avoid duplicates.
- Rate limit: 50 requests/minute and 750/hour per user. Batch metadata reads (`GET /2/threads/?ids=a,b,c`) instead of looping.
- Every `exec` is a fresh shell, so start each command with the helper below. On Windows (cmd.exe) use `%QUIP_API_TOKEN%` and double quotes.

```bash
q() { curl -s -H "Authorization: Bearer $QUIP_API_TOKEN" "$@"; }
```

## Read

```bash
q "https://platform.quip.com/1/users/current"                     # private_folder_id, shared_folder_ids, group_folder_ids
q "https://platform.quip.com/1/folders/FOLDER_ID"                 # children: thread_id / folder_id
q "https://platform.quip.com/1/threads/search?query=roadmap&count=10"
q "https://platform.quip.com/2/threads/THREAD_ID"                 # metadata
q "https://platform.quip.com/2/threads/THREAD_ID/html"            # body as HTML (paginate with cursor)
```

## Create

`content` may be HTML or Markdown (max 1 MB). `member_ids` = comma-separated folder or user ids; omitted, the doc goes to the user's Private folder.

```bash
q -X POST "https://platform.quip.com/1/threads/new-document" \
  --data-urlencode "title=Weekly sync 2026-10-15" \
  --data-urlencode "format=markdown" \
  --data-urlencode "content=# Weekly sync
- Item one
- Item two" \
  --data-urlencode "member_ids=FOLDER_ID"
```

The response is the new thread: `thread.id`, `thread.link`. `type=spreadsheet` with an HTML `<table>` creates a spreadsheet.

## Edit

```bash
q -X POST "https://platform.quip.com/1/threads/edit-document" \
  --data-urlencode "thread_id=THREAD_ID" \
  --data-urlencode "format=html" \
  --data-urlencode "content=<p>New paragraph</p>" \
  --data-urlencode "location=0"
```

`location`: 0 append (default), 1 prepend, 2 after section, 3 before section, 4 replace section, 5 delete section; 2-5 need `section_id`. Section ids are the `id` attributes on elements in the thread HTML, so read the HTML first.
