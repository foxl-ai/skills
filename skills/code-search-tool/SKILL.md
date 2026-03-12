---
name: code-search-tool
description: Search code files using grep or ripgrep for patterns, symbols, and functions
trigger: manual
enabled: true
requires:
  anyBins: [rg, grep]
provides_tools: code_search
tool_module: registry
tool_exports: [getSkillTool_code_search]
tags: development, search, code
---

# Code Search Tool Skill

Provides the `code_search` tool for searching code files.

## Requirements
- Either `rg` (ripgrep) or `grep` must be available on PATH

## Provided Tool
- `code_search` - Search code with grep/ripgrep for patterns, symbols, functions

## When to use
- User asks to find code patterns or symbols
- User needs to locate function definitions
- User wants to search across a codebase
