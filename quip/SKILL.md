---
name: quip
description: Manage Amazon Quip documents via REST API
trigger: manual
tags: quip, documents, meeting-notes
requires: [curl]
always: true
---

# Quip Skill

Manage Amazon Quip documents via REST API.

## Configuration

- **API Base URL**: `https://platform.quip-amazon.com/1/`
- **Auth**: Bearer token via `QUIP_API_TOKEN` environment variable
- **Token**: Set via `QUIP_API_TOKEN` environment variable

## Key Folders

- **2026 Engagements - Sanghwa** (고객 미팅 노트): Folder ID `VYQ9OAhF8oz` 
- **2026 1:1 and Internal - Sanghwa** (내부/1:1 미팅 노트): Folder ID `HKX9OANlr0Y` 

## Folder Routing Rules

- **Customer-facing 미팅** (고객과 직접 미팅, discovery call, POC 논의 등) → `2026 Engagements - Sanghwa` (`VYQ9OAhF8oz`)
- **Internal/1:1 미팅** (매니저 1:1, 내부 sync, 올핸즈, 팀미팅, internal debrief 등) → `2026 1:1 and Internal - Sanghwa` (`HKX9OANlr0Y`)
- `[Internal]` 태그가 들어간 문서는 반드시 Internal 폴더에 저장

## Title Convention

Meeting notes follow the format: `[MM/DD] Customer/Topic - Meeting Details`

Customer engagement examples:
- `[02/20] Marzen Media - AgentCore Observability, MCP Architecture & Migration Planning`
- `[02/19] Orange Logic - Nova MME POC Alignment Call`

Internal/1:1 examples:
- `[02/20] Michael 1:1 Sync - Customer Prioritization & Scale Strategy`
- `[02/20] Schools PLP - 2/20 인터널 싱크 미팅 로그`
- `[02/16] GenAI/ML Team All-Hands 올핸즈 미팅 요약 / 칼파나 Kalpana`
- `[02/18] SMB 팀미팅 w/ 찬드라 랑 나머지`

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

## Common Patterns

### Meeting Notes Template
Standard sections for engagement meeting notes:
1. Header (Date, Type, Attendees)
2. Context / Background
3. Discussion Topics (numbered sections)
4. Timeline / Milestones (table format)
5. Action Items (grouped by owner: AWS / Customer / Joint)
6. Internal Notes (AWS Eyes Only)

### Workflow
1. Check existing docs in folder to avoid duplicates
2. Determine correct folder based on Folder Routing Rules
3. Create document with HTML content
4. Place in appropriate folder via `member_ids` parameter
5. Verify creation by checking folder contents
