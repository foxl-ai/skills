---
name: quip
description: Manage Amazon Quip documents via REST API
enabled: true
trigger: manual
tags: quip, documents, meeting-notes
requires: [curl]
always: true
---

# Quip Skill

Manage Amazon Quip documents via REST API.

## Setup

1. Set `QUIP_API_TOKEN` environment variable with your Quip API token
2. Configure target folder IDs in your workspace settings
3. API Base URL: `https://platform.quip-amazon.com/1/`

## Title Convention

Meeting notes follow the format: `[MM/DD] Customer/Topic - Meeting Details`

Examples:
- `[02/20] Acme Corp - Architecture Review`
- `[02/20] Team Sync - Weekly Standup`

## API Endpoints

### List Folder Contents
```bash
curl -s -H "Authorization: Bearer $QUIP_API_TOKEN" \
  "https://platform.quip-amazon.com/1/folders/{folder_id}"
```

### Get Document
```bash
curl -s -H "Authorization: Bearer $QUIP_API_TOKEN" \
  "https://platform.quip-amazon.com/1/threads/{thread_id}"
```

Response includes `html` field with document content and `thread` metadata.

### Create Document
```python
import json, urllib.request, urllib.parse

data = urllib.parse.urlencode({
    'title': '[MM/DD] Customer - Topic',
    'content': '<h1>Title</h1><p>Content in HTML</p>',
    'format': 'html',
    'member_ids': 'FOLDER_ID',  # folder to place doc in
    'type': 'document'
}).encode('utf-8')

req = urllib.request.Request(
    'https://platform.quip-amazon.com/1/threads/new-document',
    data=data,
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
)
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
# result['thread']['link'] = document URL
# result['thread']['id'] = thread ID
```

### Edit Document (Append/Prepend/Replace)
```python
data = urllib.parse.urlencode({
    'content': '<p>New content</p>',
    'format': 'html',
    'location': 0,  # 0=APPEND, 1=PREPEND, 2=AFTER_SECTION, 3=BEFORE_SECTION, 4=REPLACE_SECTION, 5=DELETE_SECTION
    'section_id': 'optional_section_id'  # required for location 2-5
}).encode('utf-8')

req = urllib.request.Request(
    f'https://platform.quip-amazon.com/1/threads/edit-document',
    data=data + b'&thread_id=THREAD_ID',
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
)
```

### Search
```bash
curl -s -H "Authorization: Bearer $QUIP_API_TOKEN" \
  "https://platform.quip-amazon.com/1/threads/search?query=search+terms"
```

## HTML Format Notes

- Use `<h1>` for title, `<h2>` for sections, `<h3>` for subsections
- Use `<div data-section-style='5'><ul><li>...</li></ul></div>` for bullet lists
- Use `<hr style='width:100%'>` for section dividers
- Use `<p class='line'>` for paragraphs
- Use `<b>` for bold, `<code>` for inline code
- Tables: standard `<table>` with inline border styles
- Quip assigns section IDs automatically; use thread GET to retrieve them for editing

## Workflow

1. Check existing docs in folder to avoid duplicates
2. Create document with HTML content
3. Place in target folder via `member_ids` parameter
4. Verify creation by checking folder contents
