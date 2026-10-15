---
name: github
description: "Work with GitHub through the gh CLI: pull requests (view, diff, review, create, checks), issues, Actions runs and failed logs, releases, search, and raw API calls. Use when the user mentions a GitHub repo, PR, issue, CI run or release."
enabled: true
requires: [gh]
tags: development, github, ci
---

# GitHub via gh

Run `gh` with `exec`. Inside a clone it picks the repo up automatically; elsewhere add `-R owner/repo`.

Setup if missing: install from https://cli.github.com (macOS: `brew install gh`), then the user runs `gh auth login` themselves in a terminal (it is interactive). Check with `gh auth status`.

## Pull requests

```bash
gh pr list --state open --limit 20
gh pr view 123 --comments
gh pr view 123 --json title,state,author,reviewDecision,mergeable,statusCheckRollup
gh pr diff 123 --name-only           # changed files; drop --name-only for the patch
gh pr checks 123                     # CI status; add --watch --fail-fast to wait
gh pr checkout 123
gh pr create --fill --draft          # or --title "..." --body-file notes.md --base main
gh pr review 123 --comment --body "..."    # --approve / --request-changes
gh pr merge 123 --squash --delete-branch
```

## Actions

```bash
gh run list --limit 10               # filter: --branch main, --workflow ci.yml, --status failure
gh run view <run-id>                 # jobs and which steps failed
gh run view <run-id> --log-failed    # logs of failed steps only (start here)
gh run watch <run-id> --exit-status
gh run rerun <run-id> --failed
gh workflow run ci.yml --ref main -f key=value
```

## Issues, releases, search

```bash
gh issue list --label bug --limit 20
gh issue view 45 --comments
gh issue create --title "..." --body "..."
gh issue comment 45 --body "..."
gh release list --limit 5
gh release view v1.2.0
gh search issues "memory leak" --repo owner/repo --state open
gh search code "parseConfig" --repo owner/repo
```

## Structured output and the API

```bash
gh issue list --json number,title,labels --jq '.[] | "\(.number) \(.title)"'
gh api repos/owner/repo/pulls/123/comments --paginate
gh api graphql -f query='query { viewer { login } }'
```

Most list and view commands take `--json <fields>`; run the command with `--json` and no fields to see the valid names.

## Rules

- Read before writing. Creating, commenting, merging, closing, re-running or dispatching changes shared state: confirm with the user first unless they asked for exactly that.
- Never print or paste tokens. Do not change repo visibility, settings or secrets unless explicitly asked.
- For long bodies use `--body-file` instead of quoting multi-line text in the command.
