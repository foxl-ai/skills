---
name: imsg
description: iMessage/SMS CLI for listing chats, history, and sending
trigger: manual
platforms: [darwin]
requires: [imsg]
---

# imsg

Read and send Messages.app iMessage/SMS on macOS.

## Setup

```bash
brew install steipete/tap/imsg
```

Requirements:
- Messages.app signed in
- Full Disk Access for terminal
- Automation permission to control Messages.app

## List Chats

```bash
imsg chats --limit 10 --json
```

## Fetch Chat History

```bash
imsg history --chat-id 1 --limit 20 --attachments --json
```

## Watch a Chat

```bash
imsg watch --chat-id 1 --attachments
```

## Send a Message

```bash
imsg send --to "+14155551212" --text "hi"
imsg send --to "+14155551212" --text "hi" --file /path/pic.jpg
```

## Options

- `--service imessage|sms|auto` - Control delivery method

## Safety

- Confirm recipient + message before sending
- Use `imsg chats --limit 10 --json` to discover chat IDs
