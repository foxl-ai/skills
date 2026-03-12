---
name: session-logs
description: Search and analyze conversation history from session logs
trigger: manual
requires: [jq, rg]
---

# Session Logs

Search your complete conversation history stored in session JSONL files.

## Location

Session logs: `~/.pilot/sessions/`

- `sessions.json` - Index mapping session keys to IDs
- `<session-id>.jsonl` - Full conversation transcript

## Structure

Each `.jsonl` file contains:
- `type`: "session" (metadata) or "message"
- `timestamp`: ISO timestamp
- `message.role`: "user", "assistant", or "toolResult"
- `message.content[]`: Text, thinking, or tool calls

## Common Queries

### List sessions by date

```bash
for f in ~/.pilot/sessions/*.jsonl; do
  date=$(head -1 "$f" | jq -r '.timestamp' | cut -dT -f1)
  size=$(ls -lh "$f" | awk '{print $5}')
  echo "$date $size $(basename $f)"
done | sort -r
```

### Extract user messages

```bash
jq -r 'select(.message.role == "user") | .message.content[]? | select(.type == "text") | .text' <session>.jsonl
```

### Search assistant responses

```bash
jq -r 'select(.message.role == "assistant") | .message.content[]? | select(.type == "text") | .text' <session>.jsonl | rg -i "keyword"
```

### Get total cost

```bash
jq -s '[.[] | .message.usage.cost.total // 0] | add' <session>.jsonl
```

### Tool usage breakdown

```bash
jq -r '.message.content[]? | select(.type == "toolCall") | .name' <session>.jsonl | sort | uniq -c | sort -rn
```

### Search all sessions

```bash
rg -l "phrase" ~/.pilot/sessions/*.jsonl
```

## Tips

- Sessions are append-only JSONL
- Use `head`/`tail` for large sessions
- Deleted sessions have `.deleted.<timestamp>` suffix
