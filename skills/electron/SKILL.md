---
name: electron
description: "Automate an Electron desktop app (Slack, VS Code, Discord, Figma, Notion, Obsidian and similar) by relaunching it with a Chrome DevTools port and driving it with the browser tool. Use when the user wants Foxl to read from, click through or test a desktop app built on Electron."
enabled: false
tags: automation, desktop, electron
---

# Electron app automation

Electron apps are Chromium, so the `browser` tool can attach to one over the Chrome DevTools Protocol (CDP) and use the same snapshot, ref and click workflow as a web page.

## 1. Relaunch the app with a debugging port (exec)

The flag only works at launch, so quit the app first (ask the user; unsaved work may be lost).

```bash
# macOS
osascript -e 'quit app "Slack"'
open -a "Slack" --args --remote-debugging-port=9222

# Linux
slack --remote-debugging-port=9222 &

# Windows (cmd)
start "" "%LOCALAPPDATA%\slack\slack.exe" --remote-debugging-port=9222
```

Use a different port per app (9222, 9223, ...). Wait a few seconds, then check it is listening: `curl -s http://127.0.0.1:9222/json/version`.

## 2. Attach with the browser tool

Use a dedicated `session` per app so the default Foxl browser session is not taken over:

```text
browser  session: slack   command: connect 9222
browser  session: slack   command: tab list          # windows and webviews, ids like t1, t2
browser  session: slack   command: tab t2            # switch target if needed
browser  session: slack   command: snapshot -i
browser  session: slack   command: click @e5
browser  session: slack   command: screenshot
```

After `connect`, later commands in that session go to the app. Re-snapshot after every navigation. Text that will not type with `fill`: try `keyboard type "text"` or `keyboard inserttext "text"`. When dark mode turns light after connecting: `set media dark`.

## 3. Clean up

Run `close` in that session, then quit and reopen the app normally. While the port is open, any local program can control the app, so do not leave it running with the flag.

## Troubleshooting

- Connection refused: the app was already running without the flag, or it is still starting. Quit fully (check the menu bar or tray) and relaunch.
- Empty or wrong snapshot: the content is in another target; use `tab list` and switch.
- Some apps ignore or strip `--remote-debugging-port`. Then CDP automation is not possible; say so instead of retrying.
