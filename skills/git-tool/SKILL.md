---
name: git-tool
description: "Git version control through the exec tool: status, diff, log, blame, branches, commits, stash, pull and push. Use when the user asks about changes, history or branches in a git repository, or wants to commit or sync work."
enabled: true
requires: [git]
tags: development, vcs, git
---

# Git via exec

There is no separate git tool. Run `git` with `exec`, setting `workdir` to the repository.

## Read first

```bash
git status --short --branch          # what changed, which branch, ahead/behind
git diff --stat                      # unstaged changes, per file
git diff --staged                    # what the next commit contains
git log --oneline -n 20              # recent history
git log -p -n 3 -- path/to/file      # recent changes to one file
git blame -L 40,60 path/to/file      # who changed these lines
git branch -vv                       # local branches and their upstreams
```

Pipe long output through `head`, or pass a path, instead of dumping a whole diff.

## Change

```bash
git switch -c feature/x              # new branch
git add path/to/file                 # stage specific files, not blindly everything
git commit -m "Short summary"        # message in the repo's existing style
git pull --rebase                    # update the current branch
git push -u origin feature/x         # first push of a branch
git stash push -m "wip"              # set work aside; git stash list, git stash apply
```

## Rules

- Inspect `status` and `diff` before committing, and show the user what will be committed.
- Commit or push only when the user asked for it. Use the user's configured identity.
- Never pass `--no-verify`. If a hook fails, report what it said.
- Ask before anything that discards or rewrites work: `reset --hard`, `clean -fd`, `checkout -- .`, `rebase`, `push --force` (prefer `--force-with-lease` when the user does want it), deleting branches.
- Git opens an editor for some commands; avoid it with `-m`, `--no-edit`, or `GIT_EDITOR=true` in `env`.
- For GitHub pull requests, issues and CI, see the github skill.
