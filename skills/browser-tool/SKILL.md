---
name: browser-tool
description: Browser automation via agent-browser CLI (Rust + Playwright). Navigate, snapshot, click, fill, screenshot, extract content. Use for JS-heavy sites, SPAs, login-required pages, and any task requiring real browser interaction.
trigger: manual
enabled: true
provides_tools: [browser, browser_extension]
tool_module: registry
tool_exports: [getSkillTool_browser, getSkillTool_browser_extension]
tags: automation, browser, web
---

# Browser Tool Skill

Provides browser automation via agent-browser CLI and Chrome Extension.

## Provided Tools
- `browser` - agent-browser CLI (Rust + Playwright). Supports snapshot refs (@e1, @e2) for fast element selection. Use for JS-heavy sites, SPAs, login-required pages.
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
1. `browser open <url>` — Navigate
2. `browser snapshot -i` — Get interactive elements with refs
3. `browser click @e1` / `browser fill @e2 "text"` — Interact using refs
4. Re-snapshot after page changes

## References
- [references/commands.md](references/commands.md) — Full command reference
- [references/snapshot-refs.md](references/snapshot-refs.md) — Ref lifecycle and troubleshooting
- [references/session-management.md](references/session-management.md) — Parallel sessions
- [references/authentication.md](references/authentication.md) — Login flows and state reuse
- [references/video-recording.md](references/video-recording.md) — Recording workflows
- [references/profiling.md](references/profiling.md) — Chrome DevTools profiling
- [references/proxy-support.md](references/proxy-support.md) — Proxy configuration

## Templates
- [templates/form-automation.sh](templates/form-automation.sh) — Form filling
- [templates/authenticated-session.sh](templates/authenticated-session.sh) — Login + reuse state
- [templates/capture-workflow.sh](templates/capture-workflow.sh) — Content extraction
