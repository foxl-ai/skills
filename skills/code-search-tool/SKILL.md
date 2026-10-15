---
name: code-search-tool
description: "Search file contents with the built-in code_search tool (ripgrep, or grep when rg is missing) to find definitions, usages, strings and patterns across a codebase or folder."
enabled: true
requires: [rg, grep]
requiresAny: true
provides_tools: [code_search]
tags: development, search, code
---

# code_search

| Parameter | Meaning |
|---|---|
| `pattern` | Regular expression (ripgrep syntax when rg is installed, grep syntax otherwise). |
| `path` | Directory to search: absolute, `~/...`, or relative to the workspace folder (the default). |
| `filePattern` | File glob, for example `*.ts` or `*.py`. |
| `ignoreCase` | Case-insensitive match. Default false. |
| `context` | Lines of context around each match. Default 2. |
| `maxResults` | Match cap. Default 50. `truncated: true` in the result means there were more. |

## Tips

- Point `path` at a repository or subfolder; searching the home folder is slow and noisy.
- Find a definition with an anchored pattern, for example `function parseConfig|const parseConfig =` or `^class Foo`.
- Escape regex characters you mean literally (`\.`, `\(`).
- Use `context: 0` and a narrow `filePattern` when you only need file and line numbers.
- When results are truncated, narrow `path` or `filePattern` before raising `maxResults`.
- Then read the hit with `file_read` (it takes an offset and limit) instead of re-searching.
- To list files by name rather than content, use `exec` with `rg --files -g '<glob>'` or `find`.
