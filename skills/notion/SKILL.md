---
name: notion
description: Create and manage Notion pages, databases, and blocks via API
enabled: true
requires:
  env: ["NOTION_API_KEY"]
---

# Notion Skill

Use the Notion API to manage pages and databases.

## Setup

1. Create an integration at https://notion.so/my-integrations
2. Copy the API key (starts with `ntn_` or `secret_`)
3. Store it: `export NOTION_API_KEY="ntn_your_key_here"`
4. Share target pages/databases with your integration

## When to use
- User wants to create/update Notion pages
- User wants to query Notion databases
- User wants to add content to Notion

## How to execute

### Search for pages

```bash
curl -X POST "https://api.notion.com/v1/search" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"query": "page title"}'
```

### Get page content

```bash
curl "https://api.notion.com/v1/blocks/{page_id}/children" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03"
```

### Create page in database

```bash
curl -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {"database_id": "xxx"},
    "properties": {
      "Name": {"title": [{"text": {"content": "New Item"}}]},
      "Status": {"select": {"name": "Todo"}}
    }
  }'
```

### Query database

```bash
curl -X POST "https://api.notion.com/v1/data_sources/{id}/query" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"filter": {"property": "Status", "select": {"equals": "Active"}}}'
```

## Property Types

- Title: `{"title": [{"text": {"content": "..."}}]}`
- Select: `{"select": {"name": "Option"}}`
- Date: `{"date": {"start": "2024-01-15"}}`
- Checkbox: `{"checkbox": true}`
- Number: `{"number": 42}`
