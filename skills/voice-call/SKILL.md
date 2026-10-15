---
name: voice-call
description: "Place an outbound phone call that speaks a message, using the Twilio REST API with curl; check or hang up a call. One-way announcements only. Use when the user explicitly asks to phone someone with a spoken message."
enabled: false
tags: phone, call, twilio, voice, automation
platforms: [darwin, linux, win32]
requires: [TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER]
---

# Voice Call (Twilio)

Calls go through Twilio's Call resource:
https://www.twilio.com/docs/voice/api/call-resource

Set on the Integrations page (or in the environment):
- `TWILIO_ACCOUNT_SID` - `AC...` from the Twilio Console
- `TWILIO_AUTH_TOKEN` - the account auth token
- `TWILIO_FROM_NUMBER` - a Twilio number or verified caller ID, E.164 (`+15551234567`)

Trial accounts can only call verified numbers.

## Rules

- A call rings a real phone and costs money. Before placing one, show the user the
  number and the exact message and wait for an explicit yes. Never retry a call on
  your own.
- Numbers must be E.164 (`+` and country code, no spaces).

## Place a call

```bash
curl -sS -X POST "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/Calls.json" \
  -u "$TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN" \
  --data-urlencode "To=+15555550123" \
  --data-urlencode "From=$TWILIO_FROM_NUMBER" \
  --data-urlencode "Twiml=<Response><Say>Hello, this is a reminder that your appointment is at 3 PM.</Say></Response>"
```

The JSON reply has `sid` (`CA...`) and `status`. Escape `&`, `<`, `>` in the message as
XML (`&amp;`, `&lt;`, `&gt;`); the whole `Twiml` value is limited to 4000 characters.
Add `<Pause length="1"/>` before `<Say>` so the greeting is not cut off, and repeat the
`<Say>` if it matters that it is heard.

## Check or end a call

```bash
curl -sS -u "$TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN" \
  "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/Calls/<CallSid>.json"

curl -sS -X POST -u "$TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN" \
  "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/Calls/<CallSid>.json" \
  --data-urlencode "Status=completed"
```

`status`: `queued`, `ringing`, `in-progress`, `completed`, `busy`, `failed`,
`no-answer`, `canceled`. A non-2xx reply carries `code` and `message`; report them.

## Limits

This skill cannot hold a two-way conversation: that needs a public webhook server
for Twilio to call back, which Foxl does not provide.
