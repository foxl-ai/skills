---
name: outlook-web
description: Read and manage Outlook email, calendar, and to-do via browser_extension on outlook.office.com. Use when user asks about email inbox, calendar schedule, meetings, tasks, or today's agenda in Outlook. Triggers on: "메일", "이메일", "캘린더", "일정", "미팅", "회의", "오늘 일정", "내일 일정", "이번 주 일정", "스케줄", "outlook", "inbox", "calendar", "schedule", "meeting", "what's on my calendar", "today's schedule", "agenda". Also triggers when user asks things like "오늘 뭐 있어?", "일정 뭐 있어?", "미팅 있어?" in the context of checking their work schedule.
trigger: manual
platforms: [darwin, linux, win32]
enabled: true
# requires: [browser_extension]  # removed: browser_extension is a built-in tool, not a binary
tags: outlook, email, calendar, meetings, tasks
---

# Outlook Web (browser_extension)

Read and manage Outlook email, calendar, and tasks through the Chrome browser extension on outlook.office.com.

## Prerequisites

- Chrome browser extension (Pilot) installed and connected
- User already logged into outlook.office.com in Chrome
- Outlook tab open (or will be opened via `new_tab` / `navigate`)

## Architecture

All operations use `browser_extension` to interact with the Outlook Web App DOM.
The Outlook tab must be active (navigated to) before `get_tree` works.

**Account**: sanghwa@amazon.com

## Finding the Outlook Tab

First, find the Outlook tab among open Chrome tabs:

```
browser_extension action=get_tabs
```

Look for a tab with URL containing `outlook.office.com`. Note its `tabId`.

If no Outlook tab exists, open one:

```
browser_extension action=new_tab url=https://outlook.office.com/mail/
```

**IMPORTANT**: If `get_tree` returns "Could not establish connection", the tab is likely suspended. Re-navigate:

```
browser_extension action=navigate tabId=<TAB_ID> url=https://outlook.office.com/mail/
```

Then wait 2 seconds before calling `get_tree`.

## Navigation Between Views

Outlook Web has a left sidebar with buttons for switching views:

| View | How to switch |
|---|---|
| Mail | Click the "Mail" button in `navigation "left-rail-appbar"` |
| Calendar | Click the "Calendar" button |
| People | Click the "People" button |
| To Do | Click the "To Do" button |

After clicking, wait briefly then call `get_tree` to read the new view.

---

## MAIL OPERATIONS

### Read Inbox (Message List)

1. Navigate to Mail view (click "Mail" button or go to `https://outlook.office.com/mail/`)
2. `get_tree` with `filter=visible, depth=6`
3. The message list is in `complementary "Message list"` > `listbox "Message list..."`
4. Each email is an `option` element with text like:
   - `"Unread Collapsed Important Has attachments Flagged Pinned Replied Sender Subject DateTime Preview..."`
5. Parse the option text to extract: read status, sender, subject, date, preview

**Key patterns in option text:**
- `Unread` prefix = unread message
- `Collapsed` = conversation collapsed
- `Important` = high importance
- `Has attachments` = has attachments
- `Flagged` = flagged
- `Pinned` = pinned to top
- `Replied` / `Forwarded` = replied or forwarded

**Focused vs Other tab:**
- `tab "Focused"` and `tab "Other"` are in a `tablist`
- Click the tab to switch
- Other tab shows count like `"Other Emails (30)"`

### Read a Specific Email

1. Click the `option` element (refId) of the desired email
2. The reading pane (`main "Reading Pane"`) will populate
3. `get_tree` again with depth=8 to read the email body
4. Email content appears in the reading pane region

### Search Emails

1. Look for a search box (usually at top of mail view)
2. Or navigate directly: `https://outlook.office.com/search/`
3. Type search query and read results

### Scroll for More Emails

```
browser_extension action=scroll tabId=<TAB_ID> direction=down amount=500
```

Focus the message list area first by clicking on it, then scroll.

---

## CALENDAR OPERATIONS

### View Weekly Calendar

1. Click "Calendar" button in left sidebar
2. `get_tree` with `filter=visible, depth=6`
3. Calendar view shows as `main "calendar view, current time: ..."`
4. Each event is a `button` with rich text like:
   - `"Event Title, 10:00 AM to 11:00 AM, Tuesday, March 03, 2026, By Organizer, Busy"`
5. Parse button text to extract: title, time, date, organizer, status

**Event metadata in button text:**
- `By <Name>` = organizer
- `Busy` / `Tentative` / `Free` = availability
- `Private` = private event
- `Recurring event` / `Repeating event` = recurring
- Zoom/Teams URL may appear in nested generic elements

### Navigate Calendar Dates

- **Today**: Click `button "Go to today March 04, 2026"`
- **Previous week**: Click `button "Go to previous week..."`
- **Next week**: Click `button "Go to next week..."`
- **Specific date**: Use the mini calendar grid, click `button "15, March, 2026"` etc.

### View a Specific Day

Click a date in the mini calendar on the left sidebar. The weekly view will shift to include that date, or switch to day view.

### Get Event Details

Click on an event button to open its detail popup. Then `get_tree` to read the full details including:
- Full title
- Time
- Location
- Organizer
- Attendees
- Description/body
- Meeting link (Zoom/Teams)

### Create a New Event

1. In calendar view, look for "New event" button
2. Or navigate: `https://outlook.office.com/calendar/view/week` and find the new event button
3. Fill in the form fields: title, date/time, location, attendees, body

---

## TO DO OPERATIONS

1. Click "To Do" button in left sidebar
2. Read task lists and tasks from the tree
3. Tasks can be created, completed, etc. through the UI

---

## RESPONSE FORMAT GUIDELINES

### When reporting emails:
- Summarize in a clear list: sender, subject, time, read/unread status
- Group by date (Today, Yesterday, etc.) as Outlook does
- Note pinned items separately
- Mention unread count

### When reporting calendar:
- List events chronologically for the day/week
- Include: time, title, organizer, location/meeting link
- Note conflicts (overlapping times)
- Mark tentative vs busy vs free

### When reporting a specific email:
- Show: From, To, CC, Date, Subject
- Summarize body content
- Note attachments

---

## COMMON PATTERNS

### Check today's schedule
```
1. get_tabs → find Outlook tab
2. navigate to calendar view (click Calendar button)
3. get_tree → parse events for today's column
4. Summarize chronologically
```

### Check unread emails
```
1. get_tabs → find Outlook tab
2. navigate to mail view (click Mail button)
3. get_tree → parse message list
4. Filter for options starting with "Unread"
5. Summarize
```

### Read a specific email thread
```
1. Find the email in message list
2. Click its option element
3. get_tree with depth=8 to read reading pane
4. Extract and summarize content
```

---

## TROUBLESHOOTING

| Issue | Solution |
|---|---|
| "Could not establish connection" | Tab is suspended. Use `navigate` to reload it. |
| Empty message list | Outlook may still be loading. Wait 2~3 seconds, retry `get_tree`. |
| Tree too large / truncated | Use `filter=visible` and limit `depth` to 5~6. Increase only when reading specific content. |
| Tab not found | Open a new tab: `new_tab url=https://outlook.office.com/mail/` |
| Reading pane empty | Click an email first, then re-read the tree. |

## LIMITATIONS

- Cannot compose/send emails (no write operations via browser automation for safety)
- Cannot download attachments directly
- Calendar event creation requires careful form filling
- Some dynamic content may need scrolling to load
- Private/encrypted emails may not show full content
