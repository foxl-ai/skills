---
name: kiro-send-tool
description: Interact with Kiro IDE (Electron app) using agent-browser via Chrome DevTools Protocol. Use the electron skill to connect to Kiro's Electron process and automate it.
trigger: manual
enabled: true
tags: ide, kiro, code, electron
---

# Kiro IDE Automation

Kiro is an Electron app. To interact with it programmatically, use the `electron` skill with `agent-browser`.

## Connect to already-running Kiro

```bash
# Auto-discover any running Chromium-based app (checks DevToolsActivePort)
agent-browser --auto-connect snapshot -i

# Or find the port manually
# macOS: Kiro stores its debug port in the user data dir
lsof -i -P | grep -i kiro | grep LISTEN

# Then connect explicitly
agent-browser connect <port>
```

## Launch Kiro with debugging enabled (if not running)

```bash
# macOS
open -a "Kiro" --args --remote-debugging-port=9333

# Wait for startup, then connect
sleep 3
agent-browser connect 9333
```

## Interact

```bash
agent-browser snapshot -i          # Discover UI elements
agent-browser click @e5            # Click a button
agent-browser fill @e3 "prompt"    # Type into an input
agent-browser screenshot kiro.png  # Capture current state
agent-browser get text @e1         # Read text from an element
```

## Related Skills
- `electron` — Full guide for automating any Electron app via agent-browser CDP
- `browser-tool` — Browser automation for web pages
