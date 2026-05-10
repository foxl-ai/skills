---
name: web-fetch-tool
description: Fetch content from URLs - web pages, APIs, and online resources
enabled: true
provides_tools: web_fetch
tool_module: registry
tool_exports: [getSkillTool_web_fetch]
tags: web, http, api
---

# Web Fetch Tool Skill

Provides the `web_fetch` tool for HTTP requests.

## Provided Tool
- `web_fetch` - Fetch content from URLs with configurable options

## When to use
- User needs to fetch web page content
- User wants to call REST APIs
- User needs to download or check online resources

## Features
- Supports GET requests
- Domain filtering (whitelist/blacklist) for security
- Configurable timeout
- Content extraction from HTML
