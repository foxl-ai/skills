---
name: outlook-web
description: "Legacy browser-extension Outlook skill (superseded by 'outlook'). Only used as fallback when the Graph API integration is unavailable."
platforms: [darwin, linux, win32]
enabled: true
tags: outlook, email, calendar, browser-fallback, legacy
---

# Outlook Web (Legacy Browser Fallback)

**Superseded.** The native `outlook` skill (Microsoft Graph API) is the
recommended path - set it up under Settings → Integrations → Connect Microsoft
365.

This skill remains in the catalog as a browser-extension-based fallback for
environments where direct Graph API access is not possible (e.g., users who
cannot install a custom Azure AD app for their tenant). It interacts with
outlook.office.com via Foxl's Chrome browser extension.

Enable manually by setting `enabled: true` if needed. When both this skill
and `outlook` are active, prefer `outlook` - this skill has read-only coverage
and no write operations (compose/send/reply/reactions) for safety.

## Prerequisites (when enabled)

- Chrome browser extension (Foxl) installed and connected
- User logged into outlook.office.com in Chrome
- Outlook tab open (or opened via `browser_extension new_tab`)

## Architecture

All operations read the Outlook Web App DOM via `browser_extension` tree
snapshots. This file is kept intentionally terse since the path is deprecated.
