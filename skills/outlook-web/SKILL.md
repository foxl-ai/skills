---
name: outlook-web
description: "Read Outlook mail and calendar in the user's own Chrome through the Foxl browser extension (Outlook on the web). Use ONLY when the outlook tool is not available, e.g. Microsoft 365 is not connected or the user's organization blocks the connection. Read-only."
enabled: true
tags: outlook, email, calendar, browser
---

# Outlook on the web (browser fallback)

If the `outlook` tool exists, use it instead. Otherwise suggest connecting Microsoft 365 in Settings > Connect > Integrations, and fall back to this skill if the user cannot or does not want to.

## Requirements

- Foxl Chrome extension installed and connected (`browser_extension` action `status`).
- The user is signed in to Outlook in Chrome. Work or school: `https://outlook.office.com/mail/`; personal: `https://outlook.live.com/mail/`.

## How

1. `browser_extension` `new_tab` (or `navigate`) to the mail URL above, or `.../calendar/view/day` (`/week`) for the calendar.
2. `snapshot` to read the page; it returns interactive elements with `[ref_N]` ids. Use `click` on a ref to open a message, then `snapshot` again to read it. `scroll` for more of the list.
3. To search, `click` the search box, `type` the query, `press_key` `Enter`, then `snapshot`.
4. If the page shows a sign-in screen, stop and ask the user to sign in in that tab.

## Limits

- Read-only by policy: do not compose, send, reply, delete, move or RSVP through the page. For writes, the user needs the Microsoft 365 connection (`outlook` tool).
- Summarize what you read; do not paste whole mail bodies back unless asked.
