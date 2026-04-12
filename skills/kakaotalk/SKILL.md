---
name: kakaotalk
description: Send and read KakaoTalk messages via batiflow-mcp (macOS only)
trigger: manual
platforms: [darwin]
tags: [messaging, kakaotalk, korean, batiflow]
---

# KakaoTalk Messaging

Send and read KakaoTalk messages using batiflow-mcp. Requires macOS with KakaoTalk desktop app installed and running.

## Setup

batiflow-mcp must be available. Install globally:

```bash
npm install -g batiflow-mcp
```

Or run directly with npx (auto-installs on first use):

```bash
npx batiflow-mcp
```

## Send a Message

Use the `exec` tool to send a KakaoTalk message:

```bash
npx batiflow-mcp send "Contact Name" "Hello from Foxl"
```

- Contact name must match exactly as shown in KakaoTalk (display name)
- Supports Korean and other Unicode characters
- Group chat names work too

## Read Messages

Read recent messages from a conversation:

```bash
npx batiflow-mcp read "Contact Name" --limit 50
```

Options:
- `--limit N` - Number of messages to retrieve (default: 20)
- Returns messages with sender, timestamp, and content

## Send to Group Chat

```bash
npx batiflow-mcp send "Group Chat Name" "Meeting at 3pm today"
```

## How It Works

batiflow-mcp uses macOS accessibility APIs to interact with the KakaoTalk desktop app. It:

1. Activates the KakaoTalk window
2. Navigates to the target conversation
3. Types and sends the message (or reads messages)
4. Returns to the previous window

## Gotchas

- KakaoTalk desktop app must be running and logged in
- macOS only - uses AppleScript/accessibility APIs
- First run may prompt for accessibility permissions (System Settings > Privacy & Security > Accessibility)
- Contact names are case-sensitive and must match exactly
- Sending to new contacts (not in recent chats) may fail - start a conversation manually first
- There may be a brief visual flash as batiflow switches windows

## Example Workflows

### Morning briefing to team
```
Send a morning briefing to the "Team" KakaoTalk group with today's weather, calendar, and top 3 Slack messages.
```

### Auto-reply when busy
```
Read the last 10 KakaoTalk messages from "Boss". If any are urgent, reply with "Checking now, will respond in 5 minutes."
```

### Forward summary
```
Read the last 50 messages from "Project Chat" on KakaoTalk, summarize the key decisions, and send the summary to "Manager".
```
