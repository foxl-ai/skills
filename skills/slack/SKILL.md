---
name: slack
description: "Slack messaging, search, reactions, and file uploads via the user's OAuth token. Triggers on: 'slack', 'send slack', 'search slack', 'slack thread', 'slack channel', 'dm on slack'."
enabled: true
trigger: manual
tags: slack, messaging, search, reactions
requires: [integration:slack]
provides_tools: slack
tool_module: registry
---

# Slack (User Token)

Read and write Slack in the signed-in user's context. Matches Amazon Quick's
slack-mcp tool surface (16 actions). Requires the user to connect their Slack
account from **Settings → Integrations**.

## Capabilities

Dispatched via a single `slack` tool that takes an `action` parameter.

### Read (9 actions)
- `whoami` - Current authenticated user info (user, team, url)
- `search_messages` - Search across accessible messages (KQL-style query)
- `get_recent_messages` - Recent @mentions + DMs directed at you
- `channels_list` - Channels/groups/IMs the user belongs to
- `conversations_history` - Full message history for a channel
- `conversations_replies` - Replies in a message thread
- `check_replies_batch` - For a batch of (channel, ts), did the user reply?
- `users_lookup` - Find users by display name / alias / email
- `attachment_get_data` - Download a file attachment (base64)

### Write (5 actions)
- `conversations_add_message` - Post a message to a channel or DM
- `conversations_open` - Open a DM with one or more users
- `reactions_add` - Add an emoji reaction
- `reactions_remove` - Remove an emoji reaction
- `file_upload` - Upload a file to a channel/DM/thread (external-upload flow)

### Other (2 actions)
- `users_profile_get` - Get a user's full profile by user ID
- `conversations_members` - List member user IDs in a channel

## When to use

- User asks about Slack messages, threads, channels, DMs
- User wants to send a Slack message, reaction, or file
- User asks "who on Slack..." or "search Slack for..."
- User wants to check if someone replied to a thread

## Setup

1. Open Settings → Integrations in Foxl
2. Click "Connect Slack"
3. Authorize foxl's Slack app on your workspace (user-token scopes)
4. Return to Foxl - the tool is now available

## Notes

- All actions operate as the signed-in user (not as a bot) - `whoami` returns
  your identity, `search_messages` searches what you can see, DMs post from you
- The `channel` parameter accepts channel IDs (`C01234`, `D01234`)
- `file_upload` uses Slack's newer external-upload flow (getUploadURLExternal +
  completeUploadExternal) - works for all file sizes

## Replaces

This skill replaces the previous bot-token Slack skill. The old version used a
workspace bot token (`xoxb-`); the new one uses a user token (`xoxp-`) for
proper per-user context matching Quick's spec.
