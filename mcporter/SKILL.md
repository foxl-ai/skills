---
name: mcporter
description: List, configure, auth, and call MCP servers/tools directly
trigger: manual
requires: [mcporter]
---

# mcporter

Work with MCP servers directly from CLI.

## Setup

```bash
npm install -g mcporter
```

## List Servers/Tools

```bash
mcporter list
mcporter list <server> --schema
```

## Call Tools

```bash
# Selector syntax
mcporter call linear.list_issues team=ENG limit:5

# Function syntax
mcporter call "linear.create_issue(title: \"Bug\")"

# Full URL
mcporter call https://api.example.com/mcp.fetch url:https://example.com

# Stdio server
mcporter call --stdio "bun run ./server.ts" scrape url=https://example.com

# JSON payload
mcporter call <server.tool> --args '{"limit":5}'
```

## Auth & Config

```bash
mcporter auth <server | url> [--reset]
mcporter config list
mcporter config get <key>
mcporter config add <server>
mcporter config remove <server>
```

## Daemon

```bash
mcporter daemon start
mcporter daemon status
mcporter daemon stop
mcporter daemon restart
```

## Codegen

```bash
mcporter generate-cli --server <name>
mcporter emit-ts <server> --mode client|types
```

## Notes

- Config: `./config/mcporter.json`
- Use `--output json` for machine-readable results
