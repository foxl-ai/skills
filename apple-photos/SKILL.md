---
name: apple-photos
description: Apple Photos.app integration for macOS. List albums, browse photos, search by date/person/content, export photos.
---

# Apple Photos

Access Photos.app via SQLite queries and AppleScript. Run scripts from: `cd ~/Library/Application\ Support/pilot/skills/apple-photos`

## Requirements
- Full Disk Access for terminal (System Settings > Privacy > Full Disk Access)

## Commands

| Command | Usage |
|---------|-------|
| Library stats | `scripts/photos-count.sh` |
| List albums | `scripts/photos-list-albums.sh` |
| Recent photos | `scripts/photos-recent.sh [count]` |
| List people | `scripts/photos-list-people.sh [limit]` |
| Search by person | `scripts/photos-search-person.sh <name> [limit]` |
| Search by content | `scripts/photos-search-content.sh <query> [limit]` |
| Search by date | `scripts/photos-search-date.sh <start> [end] [limit]` |
| Photo info | `scripts/photos-info.sh <uuid>` |
| Export photo | `scripts/photos-export.sh <uuid> [output_path]` |

## Default Limits

| Script | Default | Notes |
|--------|---------|-------|
| photos-recent.sh | 10 | Pass count as arg |
| photos-list-people.sh | 20 | Pass limit as arg |
| photos-search-person.sh | 10 | Pass limit as 2nd arg |
| photos-search-date.sh | 10 | Pass limit as 3rd arg |
| photos-search-content.sh | 10 | Pass limit as 2nd arg |

## Output

- Recent/search: `Filename | Date | Type | UUID`
- People: `ID | Name | Photo Count`
- Default export: `/tmp/photo_export.jpg`

## Workflow: View a Photo

1. Get UUID: `scripts/photos-recent.sh 1`
2. Export: `scripts/photos-export.sh "UUID"`
3. View exported file with `view_image` tool at `/tmp/photo_export.jpg`

## Workflow: Search and View

1. Search: `scripts/photos-search-content.sh "cat"` or `scripts/photos-search-person.sh "name"`
2. Pick UUID from results
3. Export: `scripts/photos-export.sh "UUID"`
4. View with `view_image`

## Token Optimization

- Always use the smallest limit needed. Start with 3~5, increase only if needed.
- When viewing photos, export and view one at a time rather than batch exporting.
- Use `view_image` with `maxWidth: 256` for thumbnails, `512` only when detail is needed.
- Avoid running `photos-list-albums.sh` unless specifically asked (AppleScript output can be large).
- For people search, get the person list first with a small limit, then search with specific name.
- iCloud optimized mode: originals may not be local. Export script has fallback to derivatives.

## Notes

- Date format: `YYYY-MM-DD` or `YYYY-MM-DD HH:MM`
- Content search uses ML, slower (~5-10s) than date/person (~100ms)
- HEIC auto-converts to JPEG on export
- Name search is case-insensitive, partial match
- All scripts must be run with `exec` tool from the skill base directory
