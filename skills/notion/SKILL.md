---
name: notion
description: "Search, read, create and update Notion pages and database rows through the Notion REST API with curl. Use when the user mentions Notion, a Notion page, wiki or database, or asks to file notes or tasks into Notion."
enabled: true
tags: notion, notes, wiki, database, docs
requires: [NOTION_API_KEY, curl]
---

# Notion

Notion REST API, version header `Notion-Version: 2026-03-11`
(https://developers.notion.com/reference/versioning).

## Setup (user does this once)

1. Create an internal integration at https://www.notion.so/profile/integrations and copy its secret (starts with `ntn_`).
2. Save it as `NOTION_API_KEY` in Foxl (Settings > Connect > Integrations, Notion), or export it in the shell.
3. In Notion, open each page or database to use, `...` menu > Connections > add the integration. The API only sees pages shared this way; a 404 `object_not_found` usually means "not shared".

## Rules

- IDs: take the 32-hex id from the end of a page URL, or the `id` field of a response. Do not parse other URL parts.
- Databases hold one or more data sources. Rows are queried and created through the DATA SOURCE id, not the database id.
- Writes change the user's workspace: confirm before creating, editing or trashing anything.
- Paginate with `start_cursor` / `next_cursor` while `has_more` is true; `page_size` max 100.
- Windows (`exec` runs cmd.exe): use `%NOTION_API_KEY%`, double quotes, and put JSON bodies in a file (`-d @body.json`).

## Requests

Every `exec` is a fresh `/bin/sh`, so start each command with this helper (POSIX, works in dash):

```bash
n() { curl -s -H "Authorization: Bearer $NOTION_API_KEY" -H "Notion-Version: 2026-03-11" -H "Content-Type: application/json" "$@"; }
```

Search pages (or `"value": "data_source"` for databases):

```bash
n -X POST https://api.notion.com/v1/search \
  -d '{"query": "Roadmap", "filter": {"property": "object", "value": "page"}, "page_size": 10}'
```

Read a page as Markdown (cheapest way to read content):

```bash
n "https://api.notion.com/v1/pages/PAGE_ID/markdown"
```

Page properties: `GET /v1/pages/PAGE_ID`. Raw blocks: `GET /v1/blocks/PAGE_ID/children`.

Create a child page with Markdown content:

```bash
n -X POST https://api.notion.com/v1/pages -d '{
  "parent": {"page_id": "PARENT_PAGE_ID"},
  "properties": {"title": {"title": [{"text": {"content": "Meeting notes"}}]}},
  "markdown": "## Agenda\n- Item one\n- Item two"
}'
```

Append Markdown to the end of a page:

```bash
n -X PATCH "https://api.notion.com/v1/pages/PAGE_ID/markdown" \
  -d '{"type": "insert_content", "insert_content": {"content": "## Follow-ups\n- Send recap", "position": {"type": "end"}}}'
```

Targeted edit: `{"type": "update_content", "update_content": {"content_updates": [{"old_str": "...", "new_str": "..."}]}}` on the same endpoint.

### Databases

Get the data source id, then query or add rows:

```bash
n "https://api.notion.com/v1/databases/DATABASE_ID"   # -> data_sources[].id
n "https://api.notion.com/v1/data_sources/DATA_SOURCE_ID"   # -> properties (schema)

n -X POST "https://api.notion.com/v1/data_sources/DATA_SOURCE_ID/query" \
  -d '{"filter": {"property": "Status", "status": {"equals": "In progress"}}, "page_size": 20}'

n -X POST https://api.notion.com/v1/pages -d '{
  "parent": {"type": "data_source_id", "data_source_id": "DATA_SOURCE_ID"},
  "properties": {
    "Name": {"title": [{"text": {"content": "New item"}}]},
    "Status": {"status": {"name": "Not started"}}
  }
}'
```

Read the schema first: property names and option names must match exactly, and `status` and `select` are different types.

Property values: title `{"title": [{"text": {"content": "..."}}]}`, rich text `{"rich_text": [{"text": {"content": "..."}}]}`, select `{"select": {"name": "A"}}`, multi-select `{"multi_select": [{"name": "A"}]}`, status `{"status": {"name": "Done"}}`, date `{"date": {"start": "2026-10-15"}}`, checkbox `{"checkbox": true}`, number `{"number": 42}`, url `{"url": "https://..."}`.

Update properties: `PATCH /v1/pages/PAGE_ID` with `{"properties": {...}}`. Trash: same call with `{"in_trash": true}` (the field was `archived` before 2026-03-11).
