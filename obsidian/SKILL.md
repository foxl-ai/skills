---
name: obsidian
description: Work with Obsidian vaults and notes using obsidian-cli
trigger: manual
enabled: true
requires:
  bins: ["obsidian-cli"]
---

# Obsidian Skill

Work with Obsidian vaults (plain Markdown notes).

## Vault Structure
- Notes: `*.md` (plain text Markdown)
- Config: `.obsidian/` (workspace + plugin settings)
- Canvases: `*.canvas` (JSON)
- Attachments: images/PDFs in configured folder

## When to use
- User wants to search Obsidian notes
- User wants to create/edit notes
- User wants to organize vault

## How to execute

### Find active vault

Obsidian tracks vaults in:
`~/Library/Application Support/obsidian/obsidian.json`

Get default vault path:
```bash
obsidian-cli print-default --path-only
```

### Set default vault

```bash
obsidian-cli set-default "<vault-folder-name>"
```

### Search notes

By name:
```bash
obsidian-cli search "query"
```

By content:
```bash
obsidian-cli search-content "query"
```

### Create note

```bash
obsidian-cli create "Folder/New note" --content "..." --open
```

### Move/rename (safe refactor)

```bash
obsidian-cli move "old/path/note" "new/path/note"
```

This updates `[[wikilinks]]` across the vault.

### Delete note

```bash
obsidian-cli delete "path/note"
```

## Notes
- Prefer direct `.md` file edits when appropriate
- Obsidian will pick up changes automatically
- Avoid creating notes in hidden dot-folders
