---
name: voice-call
description: Start voice calls via Twilio, Telnyx, or Plivo
trigger: manual
requires: [voice-call-plugin]
---

# Voice Call

Initiate and manage voice calls programmatically.

## CLI

```bash
pilot voicecall call --to "+15555550123" --message "Hello from Pilot"
pilot voicecall status --call-id <id>
```

## Tool Actions

- `initiate_call` - Start a new call
  - `message`: What to say
  - `to`: Phone number (optional if default set)
  - `mode`: Call mode

- `continue_call` - Continue conversation
  - `callId`: Active call ID
  - `message`: What to say

- `speak_to_user` - Speak during call
  - `callId`: Active call ID
  - `message`: What to say

- `end_call` - End the call
  - `callId`: Active call ID

- `get_status` - Check call status
  - `callId`: Call ID

## Provider Config

### Twilio
```yaml
provider: "twilio"
twilio:
  accountSid: "AC..."
  authToken: "..."
fromNumber: "+1..."
```

### Telnyx
```yaml
provider: "telnyx"
telnyx:
  apiKey: "..."
  connectionId: "..."
fromNumber: "+1..."
```

### Plivo
```yaml
provider: "plivo"
plivo:
  authId: "..."
  authToken: "..."
fromNumber: "+1..."
```

### Mock (dev)
```yaml
provider: "mock"
```
