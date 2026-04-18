---
name: browser-tool
description: Browser automation via agent-browser CLI. Navigate, snapshot, click, fill, screenshot, extract content. Use for JS-heavy sites, SPAs, login-required pages, and any task requiring real browser interaction.
trigger: manual
enabled: true
provides_tools: [browser, browser_extension]
tool_module: registry
tool_exports: [getSkillTool_browser, getSkillTool_browser_extension]
tags: automation, browser, web
---

# Browser Automation with agent-browser

The CLI uses Chrome/Chromium via CDP directly. Install via `npm i -g agent-browser` or `brew install agent-browser`.

## Provided Tools
- `browser` - agent-browser CLI. Supports snapshot refs (@e1, @e2) for fast element selection. Use for JS-heavy sites, SPAs, login-required pages.
- `browser_extension` - Chrome extension-based browser control (uses real browser with logins). Preferred for authenticated access.

## When to use browser (instead of web_fetch)
- JS-heavy sites (SPAs, React/Next.js/Astro apps that render client-side)
- Pages behind login or authentication
- Sites that need JavaScript to load content (pricing tables, dynamic data)
- When web_fetch returns mostly empty HTML with `<script>` tags

## When to use web_fetch (instead of browser)
- Static pages, REST APIs, documentation with server-rendered content
- RSS feeds, JSON endpoints
- Simple HTML pages that don't need JavaScript

## Core Workflow

Every browser automation follows this pattern:

1. **Navigate**: `agent-browser open <url>`
2. **Snapshot**: `agent-browser snapshot -i` (get element refs like `@e1`, `@e2`)
3. **Interact**: Use refs to click, fill, select
4. **Re-snapshot**: After navigation or DOM changes, get fresh refs

```bash
agent-browser open https://example.com/form
agent-browser snapshot -i
# Output: @e1 [input type="email"], @e2 [input type="password"], @e3 [button] "Submit"

agent-browser fill @e1 "user@example.com"
agent-browser fill @e2 "password123"
agent-browser click @e3
agent-browser wait --load networkidle
agent-browser snapshot -i  # Check result
```

## Command Chaining

Commands can be chained with `&&` in a single shell invocation. The browser persists between commands via a background daemon.

```bash
agent-browser open https://example.com && agent-browser wait --load networkidle && agent-browser snapshot -i
```

**When to chain:** Use `&&` when you don't need to read the output of an intermediate command. Run commands separately when you need to parse the output first (e.g., snapshot to discover refs, then interact).

## Essential Commands

```bash
# Navigation
agent-browser open <url>              # Navigate
agent-browser close                   # Close browser
agent-browser close --all             # Close all active sessions

# Snapshot
agent-browser snapshot -i             # Interactive elements with refs (recommended)
agent-browser snapshot -s "#selector" # Scope to CSS selector

# Interaction (use @refs from snapshot)
agent-browser click @e1               # Click element
agent-browser fill @e2 "text"         # Clear and type text
agent-browser type @e2 "text"         # Type without clearing
agent-browser select @e1 "option"     # Select dropdown option
agent-browser check @e1               # Check checkbox
agent-browser press Enter             # Press key
agent-browser scroll down 500         # Scroll page

# Get information
agent-browser get text @e1            # Get element text
agent-browser get url                 # Get current URL
agent-browser get title               # Get page title

# Wait
agent-browser wait @e1                # Wait for element
agent-browser wait --load networkidle # Wait for network idle
agent-browser wait --url "**/page"    # Wait for URL pattern
agent-browser wait 2000               # Wait milliseconds
agent-browser wait --text "Welcome"   # Wait for text to appear

# Capture
agent-browser screenshot              # Screenshot to temp dir
agent-browser screenshot --full       # Full page screenshot
agent-browser screenshot --annotate   # Annotated with numbered element labels
agent-browser pdf output.pdf          # Save as PDF

# Downloads
agent-browser download @e1 ./file.pdf # Click to trigger download

# Network
agent-browser network requests        # Inspect tracked requests
agent-browser network requests --type xhr,fetch  # Filter by type

# Viewport
agent-browser set viewport 1920 1080  # Set viewport size
agent-browser set device "iPhone 14"  # Emulate device
```

## Handling Authentication

**Option 1: Import auth from user's browser (fastest)**
```bash
agent-browser --auto-connect state save ./auth.json
agent-browser --state ./auth.json open https://app.example.com/dashboard
```

**Option 2: Persistent profile (recurring tasks)**
```bash
agent-browser --profile ~/.myapp open https://app.example.com/login
# ... login flow ... all future runs are authenticated
```

**Option 3: Session name (auto-save/restore)**
```bash
agent-browser --session-name myapp open https://app.example.com/login
# ... login flow ...
agent-browser close  # State auto-saved
# Next time: state auto-restored
agent-browser --session-name myapp open https://app.example.com/dashboard
```

**Option 4: Auth vault (encrypted credentials)**
```bash
echo "$PASSWORD" | agent-browser auth save myapp --url https://app.example.com/login --username user --password-stdin
agent-browser auth login myapp
```

## Common Patterns

### Form Submission
```bash
agent-browser open https://example.com/signup
agent-browser snapshot -i
agent-browser fill @e1 "Jane Doe"
agent-browser fill @e2 "jane@example.com"
agent-browser select @e3 "California"
agent-browser click @e5
agent-browser wait --load networkidle
```

### Working with Iframes
Iframe content is automatically inlined in snapshots. Refs inside iframes carry frame context, so interact directly.

### Data Extraction
```bash
agent-browser open https://example.com/products
agent-browser snapshot -i
agent-browser get text @e5
agent-browser get text body > page.txt
```

### Parallel Sessions
```bash
agent-browser --session site1 open https://site-a.com
agent-browser --session site2 open https://site-b.com
agent-browser session list
```

### Visual Debugging
```bash
agent-browser --headed open https://example.com
agent-browser highlight @e1
agent-browser inspect  # Open Chrome DevTools
```

## Ref Lifecycle (Important)

Refs (`@e1`, `@e2`, etc.) are invalidated when the page changes. Always re-snapshot after:
- Clicking links or buttons that navigate
- Form submissions
- Dynamic content loading (dropdowns, modals)

## Diffing (Verifying Changes)
```bash
agent-browser snapshot -i          # Take baseline
agent-browser click @e2            # Perform action
agent-browser diff snapshot        # See what changed
```

## Session Cleanup

Always close sessions when done to avoid leaked Chrome processes:
```bash
agent-browser close                # Close default session
agent-browser close --all          # Close all sessions
```

## Security

- `--content-boundaries` wraps output in markers for LLM safety
- `AGENT_BROWSER_ALLOWED_DOMAINS` restricts navigation
- `AGENT_BROWSER_MAX_OUTPUT` prevents context flooding
- `AGENT_BROWSER_ACTION_POLICY` gates destructive actions

## References
- [references/commands.md](references/commands.md) -- Full command reference
- [references/snapshot-refs.md](references/snapshot-refs.md) -- Ref lifecycle
- [references/session-management.md](references/session-management.md) -- Parallel sessions
- [references/authentication.md](references/authentication.md) -- Login flows
- [references/video-recording.md](references/video-recording.md) -- Recording
- [references/profiling.md](references/profiling.md) -- DevTools profiling
- [references/proxy-support.md](references/proxy-support.md) -- Proxy config

## Templates
- [templates/form-automation.sh](templates/form-automation.sh) -- Form filling
- [templates/authenticated-session.sh](templates/authenticated-session.sh) -- Login + reuse state
- [templates/capture-workflow.sh](templates/capture-workflow.sh) -- Content extraction
