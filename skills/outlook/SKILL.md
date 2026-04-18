---
name: outlook
description: "Outlook email, calendar, and Microsoft To-Do via Microsoft Graph API. Triggers on: 'outlook', 'inbox', 'calendar', 'schedule', 'meeting', 'agenda', 'm365', 'microsoft 365', 'to-do', 'tasks'."
enabled: true
trigger: manual
tags: outlook, email, calendar, meetings, tasks, microsoft, graph
requires: [integration:microsoft]
provides_tools: outlook
tool_module: registry
---

# Outlook (Microsoft Graph)

Read and write Outlook email, calendar events, and Microsoft To-Do tasks using
the Microsoft Graph API. Requires the user to connect their Microsoft 365
account from **Settings → Integrations** (one-time OAuth consent).

## Capabilities

Dispatched via a single `outlook` tool that takes an `action` parameter. See the
tool description for the full action list.

### Email (13 actions)
- `email_inbox` - First N messages in Inbox (default 10)
- `email_read` - Full message by `messageId`, or thread by `conversationId`
- `email_send` - Compose + send (HTML body, CC/BCC, attachments)
- `email_reply` - Reply (or reply-all) to an existing message
- `email_forward` - Forward with optional comment + attachments
- `email_search` - KQL search across mailbox or specific folder
- `email_folders` - List mail folders or list messages in a folder
- `email_draft` - CRUD drafts (`operation`: list/read/create/update/delete)
- `email_attachments` - List or download attachments on a message
- `email_contacts` - List/search Outlook contacts
- `email_move` - Move a message to another folder
- `email_categories` - List the mailbox's master category list
- `email_update` - Flag for follow-up, set categories, importance, read state

### Calendar (6 actions)
- `calendar_view` - Events in a date range (default: today)
- `calendar_meeting` - CRUD + RSVP (`operation`: create/read/update/delete/rsvp)
- `calendar_availability` - getSchedule for one or more users
- `calendar_room_booking` - List rooms / buildings / rooms-in-building
- `calendar_search` - Search events by title/body keyword
- `calendar_shared_list` - Calendars the user has access to

### To-Do (3 actions)
- `todo_lists` - Manage task lists (list/create/update/delete)
- `todo_tasks` - Manage tasks within a list (list/get/create/update/delete/complete)
- `todo_checklist` - Manage subtasks within a task (list/create/update/delete/toggle)

## When to use

- User asks about email (inbox, unread, search, send, reply, forward)
- User asks about calendar / schedule / meetings / availability / agenda
- User asks about Microsoft To-Do tasks or checklists
- User mentions "Outlook", "Office 365", or "M365"

## Setup

1. Open Settings → Integrations in Foxl
2. Click "Connect Microsoft 365"
3. Sign in with your work/school or personal Microsoft account
4. Accept the permission scopes (Mail, Calendar, Tasks, Profile)
5. Return to Foxl - the tool is now available

## Notes

- HTML email bodies are supported; plain text auto-detected based on leading `<`
- Times default to the system timezone; pass `timeZone` to override
- Attachments use base64-encoded inline upload (works for files up to ~3MB);
  larger files require the upload session flow (not yet implemented)
- Rate limits: Graph enforces per-app and per-user throttling; the tool surfaces
  429 errors verbatim
