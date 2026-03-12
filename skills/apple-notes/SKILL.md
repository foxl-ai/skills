---
name: apple-notes
description: Manage Apple Notes via memo CLI on macOS
trigger: manual
platforms: [darwin]
requires: [memo]
---

# Apple Notes (memo)

Manage Apple Notes from the terminal using `memo`.

## Setup

```bash
brew tap antoniorodr/memo && brew install antoniorodr/memo/memo
```

Grant Automation access to Notes.app when prompted.

## View Notes

- List all: `memo notes`
- Filter by folder: `memo notes -f "Folder Name"`
- Search (fuzzy): `memo notes -s "query"`

## Create Notes

- Add new note: `memo notes -a`
- Quick add with title: `memo notes -a "Note Title"`

## Edit/Delete/Move

- Edit: `memo notes -e` (interactive selection)
- Delete: `memo notes -d` (interactive selection)
- Move to folder: `memo notes -m` (interactive selection)

## Export

- Export to HTML/Markdown: `memo notes -ex`

## Limitations

- Cannot edit notes containing images or attachments
- Interactive prompts require terminal access
