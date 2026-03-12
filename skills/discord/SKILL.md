---
name: discord
description: Control Discord - messages, reactions, threads, polls, moderation
trigger: manual
requires: [discord-bot-token]
---

# Discord Actions

Manage messages, reactions, threads, polls, and moderation via Discord API.

## React to a Message

```json
{
  "action": "react",
  "channelId": "123",
  "messageId": "456",
  "emoji": "✅"
}
```

## Send a Message

```json
{
  "action": "sendMessage",
  "to": "channel:123",
  "content": "Hello from Pilot"
}
```

Note: `sendMessage` uses `to: "channel:<id>"` format, not `channelId`.

## Send with Media

```json
{
  "action": "sendMessage",
  "to": "channel:123",
  "content": "Check this out!",
  "mediaUrl": "file:///tmp/image.png"
}
```

## Create a Poll

```json
{
  "action": "poll",
  "to": "channel:123",
  "question": "Lunch?",
  "answers": ["Pizza", "Sushi", "Salad"],
  "allowMultiselect": false,
  "durationHours": 24
}
```

## Threads

```json
{
  "action": "threadCreate",
  "channelId": "123",
  "name": "Bug triage",
  "messageId": "456"
}
```

```json
{
  "action": "threadReply",
  "channelId": "777",
  "content": "Replying in thread"
}
```

## Pins

```json
{
  "action": "pinMessage",
  "channelId": "123",
  "messageId": "456"
}
```

## Search Messages

```json
{
  "action": "searchMessages",
  "guildId": "999",
  "content": "release notes",
  "limit": 10
}
```

## Channel Management (disabled by default)

```json
{
  "action": "channelCreate",
  "guildId": "999",
  "name": "general-chat",
  "type": 0,
  "topic": "General discussion"
}
```

## Bot Presence (disabled by default)

```json
{
  "action": "setPresence",
  "activityType": "playing",
  "activityName": "with fire",
  "status": "online"
}
```

## Action Groups

Enable/disable via config:
- `reactions`, `messages`, `threads`, `pins`, `search`
- `stickers`, `polls`, `permissions`
- `roles`, `channels`, `moderation`, `presence` (disabled by default)
