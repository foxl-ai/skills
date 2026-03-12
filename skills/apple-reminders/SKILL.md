---
name: apple-reminders
description: Manage Apple Reminders via remindctl CLI on macOS
trigger: manual
platforms: [darwin]
requires: [remindctl]
---

# Apple Reminders (remindctl)

Manage Apple Reminders from the terminal using `remindctl`.

## Setup

```bash
brew install steipete/tap/remindctl
```

Grant Reminders permission when prompted. Check status: `remindctl status`

## View Reminders

- Today: `remindctl today`
- Tomorrow: `remindctl tomorrow`
- Week: `remindctl week`
- Overdue: `remindctl overdue`
- Upcoming: `remindctl upcoming`
- Completed: `remindctl completed`
- All: `remindctl all`
- Specific date: `remindctl 2026-01-04`

## Manage Lists

- List all: `remindctl list`
- Show list: `remindctl list Work`
- Create: `remindctl list Projects --create`
- Rename: `remindctl list Work --rename Office`
- Delete: `remindctl list Work --delete`

## Create Reminders

- Quick add: `remindctl add "Buy milk"`
- With list + due: `remindctl add --title "Call mom" --list Personal --due tomorrow`

## Edit/Complete/Delete

- Edit: `remindctl edit 1 --title "New title" --due 2026-01-04`
- Complete: `remindctl complete 1 2 3`
- Delete: `remindctl delete 4A83 --force`

## Output Formats

- JSON: `remindctl today --json`
- Plain TSV: `remindctl today --plain`
- Counts only: `remindctl today --quiet`

## Date Formats

Accepted: `today`, `tomorrow`, `yesterday`, `YYYY-MM-DD`, `YYYY-MM-DD HH:mm`, ISO 8601
