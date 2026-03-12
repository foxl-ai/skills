---
name: "git-tool"
description: "Git version control operations - status, diff, log, branch, checkout, commit, push, pull, add, stash"
enabled: true
trigger: manual
tags: development, vcs, git
requires: [git]
provides_tools: git
tool_module: registry
tool_exports: [getSkillTool_git]
---

# Git Tool Skill

Provides the `git` tool for version control operations.

## Requirements
- `git` binary must be installed and available on PATH

## Provided Tool
- `git` - Execute git commands (status, diff, log, branch, checkout, commit, push, pull, add, stash)

## When to use
- User asks about code changes, diffs, or history
- User wants to commit, push, or manage branches
- User needs to check repository status