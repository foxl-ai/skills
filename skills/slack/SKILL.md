---
name: slack
description: Control Slack - send messages, react, manage pins
trigger: manual
requires: [slack-bot-token]
---

# Slack Actions

Send messages, react, manage pins, and fetch member info via Slack API.

## Actions

### React to a Message

```json
{
  "action": "react",
  "channelId": "C123",
  "messageId": "1712023032.1234",
  "emoji": "✅"
}
```

### List Reactions

```json
{
  "action": "reactions",
  "channelId": "C123",
  "messageId": "1712023032.1234"
}
```

### Send a Message

```json
{
  "action": "sendMessage",
  "to": "channel:C123",
  "content": "Hello from Pilot"
}
```

### Edit a Message

```json
{
  "action": "editMessage",
  "channelId": "C123",
  "messageId": "1712023032.1234",
  "content": "Updated text"
}
```

### Delete a Message

```json
{
  "action": "deleteMessage",
  "channelId": "C123",
  "messageId": "1712023032.1234"
}
```

### Read Recent Messages

```json
{
  "action": "readMessages",
  "channelId": "C123",
  "limit": 20
}
```

### Pin/Unpin Messages

```json
{
  "action": "pinMessage",
  "channelId": "C123",
  "messageId": "1712023032.1234"
}
```

```json
{
  "action": "unpinMessage",
  "channelId": "C123",
  "messageId": "1712023032.1234"
}
```

### List Pinned Items

```json
{
  "action": "listPins",
  "channelId": "C123"
}
```

### Member Info

```json
{
  "action": "memberInfo",
  "userId": "U123"
}
```

## Ideas

- React with ✅ to mark completed tasks
- Pin key decisions or weekly status updates
