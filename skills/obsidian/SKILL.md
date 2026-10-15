---
name: obsidian
description: "Find, read, create, append to and reorganize notes in a local Obsidian vault (plain Markdown files), directly on disk or with the official obsidian CLI. Use when the user mentions Obsidian, their vault, a daily note or [[wikilinks]]."
enabled: true
tags: obsidian, notes, markdown, vault, pkm
---

# Obsidian

A vault is a folder of Markdown files. Most work needs no CLI: find the vault, then use `file_read`, `file_edit`, `file_write` and `code_search` on the `.md` files. Obsidian picks up changes on disk by itself.

## Find the vault

The list of vaults (each has a `path`) is in `obsidian.json`:

- macOS: `~/Library/Application Support/obsidian/obsidian.json`
- Linux: `~/.config/obsidian/obsidian.json` (Flatpak: `~/.var/app/md.obsidian.Obsidian/config/obsidian/obsidian.json`)
- Windows: `%APPDATA%\obsidian\obsidian.json`

If there are several, ask which one; `"open": true` marks the last opened.

## Vault conventions

- Notes `*.md`; canvases `*.canvas` (JSON); attachments in the folder set in `.obsidian/app.json` (`attachmentFolderPath`).
- Links are `[[Note name]]` or `[[Note name|alias]]`; embeds `![[file.png]]`. Frontmatter is YAML between `---` lines.
- Daily notes: folder and date format are in `.obsidian/daily-notes.json` (defaults: vault root, `YYYY-MM-DD`).
- Never edit `.obsidian/` or other dot-folders unless asked, and do not create notes there.

## Renaming or moving a note

Moving a file on disk does NOT update links pointing to it. Either grep the vault for `[[Old name` and fix each link, or use the CLI below, which renames through the app and updates links when the user has "Automatically update internal links" on.

## Official CLI (optional)

Obsidian 1.12.7+ ships `obsidian` (https://obsidian.md/help/cli). The user enables it in Obsidian Settings > General > Command line interface. It talks to the running app and launches it if needed. Check with `obsidian vaults`.

```bash
obsidian vault="My Vault" search query="meeting notes" limit=20 format=json
obsidian search:context query="budget" path=Projects
obsidian read file="Recipe"                    # file= resolves like a wikilink
obsidian read path="Templates/Recipe.md"       # path= is exact, from the vault root
obsidian create path="Inbox/Idea.md" content="# Idea\nBody"
obsidian append file="Project X" content="- [ ] Follow up"
obsidian daily:append content="- Met with Sam"
obsidian move file="Idea" to="Projects/Idea.md"
obsidian rename file="Idea" name="Better idea"
obsidian delete file="Old note"                # moves to trash; add permanent only if asked
```

Without `vault=` it uses the active vault. In `content=`, write `\n` for a newline and `\t` for a tab. Confirm before delete, overwrite or bulk moves.

The older community `obsidian-cli` (Yakitrak) is unrelated to the official CLI; do not suggest installing it.
