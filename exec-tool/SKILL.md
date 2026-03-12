---
name: exec-tool
description: Execute shell commands and manage background processes (npm, python, curl, etc.)
trigger: manual
enabled: true
provides_tools: [exec, process]
tool_module: exec
tool_exports: [execTools]
tags: shell, automation, system
---

# Shell Execution Tool Skill

Provides shell command execution and process management tools.

## Provided Tools
- `exec` - Execute shell commands (npm, git, python, curl, etc.)
  - Supports background execution for long-running processes
  - Configurable timeout and working directory
- `process` - Manage running exec sessions (list, poll, log, kill)

## When to use
- User needs to run CLI commands
- User wants to start/stop development servers
- User needs to install packages or run builds
- User wants to manage background processes

## Security Notes
- Commands run with the server process permissions
- Use with caution for destructive operations
