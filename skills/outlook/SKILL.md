---
name: outlook
description: "Outlook email, calendar and Microsoft To Do for a connected Microsoft 365 or Outlook.com account, through the outlook tool (Microsoft Graph). Use for inbox, unread mail, searching, sending or replying to email, meetings, agenda, availability, room booking and To Do tasks."
enabled: true
tags: outlook, email, calendar, meetings, tasks, microsoft, m365, graph
requires: [integration:microsoft]
provides_tools: outlook
tool_module: registry
---

# Outlook (Microsoft Graph)

This skill is only loaded once the user has connected Microsoft 365 in Foxl (Settings > Connect > Integrations > Microsoft 365). Use the `outlook` tool: pass `action` plus that action's fields; CRUD actions also take `operation`.

## Actions

Email:
- `email_inbox` (`limit`), `email_read` (`messageId`, or `conversationId` for a thread)
- `email_search` (`query`, KQL such as `from:alice subject:invoice`; optional `folder`, `limit`)
- `email_folders` (no folder = list folders; `folderId` = list its messages)
- `email_send` (`to`, `subject`, `body`, `cc`, `bcc`, `attachments`), `email_reply` (`messageId`, `body`, `replyAll`), `email_forward` (`messageId`, `to`, `comment`)
- `email_draft` (`operation`: list/read/create/update/delete, `draftId`)
- `email_attachments` (`messageId`, optional `attachmentId` to download), `email_contacts` (`query`)
- `email_move` (`messageId`, `destinationFolderId`), `email_categories`
- `email_update` (`messageId`; `flag`, `categories`, `importance`, `isRead`)

Calendar:
- `calendar_view` (`start`, `end`; default today), `calendar_search` (`query`), `calendar_shared_list`
- `calendar_meeting` (`operation`: create/read/update/delete/rsvp; `meetingId`, `subject`, `start`, `end`, `timeZone`, `attendees`, `optionalAttendees`, `location`, `isAllDay`, `rsvpResponse`)
- `calendar_availability` (`emails`, `start`, `end`, `intervalMinutes`)
- `calendar_room_booking` (`operation`: list_rooms/list_buildings/rooms_in_building, `buildingId`)

To Do:
- `todo_lists` (`operation`: list/create/update/delete)
- `todo_tasks` (`listId`; `operation`: list/get/create/update/delete/complete; `title`, `status`, `dueDateTime`)
- `todo_checklist` (`listId`, `taskId`; `operation`: list/create/update/delete/toggle)

## Rules

- Show the recipients, subject and body and get confirmation before `email_send`, `email_reply`, `email_forward`, meeting create/update/delete, RSVP or any delete.
- A `body` starting with `<` is sent as HTML, otherwise as plain text.
- Times without `timeZone` use this computer's time zone.
- `attachments` are file paths inside the Foxl workspace; copy other files there first. Each is uploaded inline, so keep the total under about 3 MB.
- Read with `email_inbox` / `email_search` first, then `email_read` only the messages needed: full bodies are large.
- A 401 or "not connected" error means the connection expired: ask the user to reconnect Microsoft 365 in Settings. A 429 is Graph throttling; wait and retry once.
