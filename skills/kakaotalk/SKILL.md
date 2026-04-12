---
name: kakaotalk
description: Send and read KakaoTalk messages via BatiFlow CLI (macOS only)
trigger: manual
platforms: [darwin]
tags: [messaging, kakaotalk, korean, batiflow]
requires: [/Applications/BatiFlow.app/Contents/MacOS/batiflow-cli]
---

# KakaoTalk Messaging

Send and read KakaoTalk messages using the BatiFlow CLI. Requires macOS with BatiFlow app and KakaoTalk desktop app installed.

## Binary Path

The CLI is bundled inside the BatiFlow app:

```
/Applications/BatiFlow.app/Contents/MacOS/batiflow-cli
```

Use the full path in all `exec` commands. Alias as `batiflow` below for readability.

## Send a Message

```bash
/Applications/BatiFlow.app/Contents/MacOS/batiflow-cli send "Contact Name" "Hello from Foxl"
```

Options:
- `--app kakao` (default) - KakaoTalk
- `--app imessage` - iMessage
- `--app slack` - Slack
- `--dry-run` - simulate without sending

## Read Messages

```bash
/Applications/BatiFlow.app/Contents/MacOS/batiflow-cli read "Contact Name" --limit 50
```

Options:
- `--limit N` - number of messages (default: 20)
- `--json` - output as JSON

## List Chat Rooms

```bash
/Applications/BatiFlow.app/Contents/MacOS/batiflow-cli chats --limit 30
```

## List Friends

```bash
/Applications/BatiFlow.app/Contents/MacOS/batiflow-cli friends
```

## Send to iMessage or Slack

```bash
/Applications/BatiFlow.app/Contents/MacOS/batiflow-cli send "John" "Hey" --app imessage
/Applications/BatiFlow.app/Contents/MacOS/batiflow-cli send "#general" "Deploy done" --app slack
```

## Check Status

```bash
/Applications/BatiFlow.app/Contents/MacOS/batiflow-cli status
```

Verifies accessibility permissions and app availability.

## Gotchas

- KakaoTalk desktop app must be running and logged in
- macOS only - uses Accessibility API
- First run prompts for accessibility permission (System Settings > Privacy & Security > Accessibility - grant to BatiFlow)
- Contact/chat names must match exactly as displayed in KakaoTalk
- There may be a brief window flash as BatiFlow interacts with the app
- BatiFlow app must be installed from https://github.com/batiai/batiflow-releases/releases/latest

## Example Workflows

### Morning briefing to team
```
Send a morning briefing to the "Team" KakaoTalk group with today's weather and calendar.
```

### Read and summarize
```
Read the last 50 messages from "Project Chat" on KakaoTalk, summarize key decisions.
```

### Cross-platform notify
```
Send "Deploy complete" to #engineering on Slack and "Team" on KakaoTalk.
```
