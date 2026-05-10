# Foxl Skills

Skills are folders of instructions, scripts, and resources that Foxl loads
dynamically to improve performance on specialized tasks. Each skill teaches
the agent how to complete specific tasks in a repeatable way.

## Structure

Each skill is a folder containing:

- `SKILL.md` - Skill definition with YAML frontmatter and instructions
- `scripts/` - Optional executable scripts the skill can invoke
- `references/` - Optional reference documentation
- `templates/` - Optional templates

## Skill Format

```markdown
---
name: my-skill
description: What this skill does and when to trigger it
trigger: auto | manual
tags: tag1, tag2
requires: [curl, python3]
enabled: true
---

# My Skill

Instructions for the agent to follow when this skill is active.
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique identifier (lowercase, hyphens) |
| `description` | Yes | What the skill does and trigger conditions |
| `trigger` | No | `auto` (keyword-activated) or `manual` (explicit invocation) |
| `tags` | No | Comma-separated tags for categorization |
| `requires` | No | System dependencies needed (CLI bins or env vars) |
| `enabled` | No | If `false`, skill ships disabled until the user opts in |

## Included Skills (35)

### Featured

`notion` `obsidian` `github` `gws` `weather`

### Productivity

`outlook` `outlook-web` `quip` `pdf` `pptx` `xlsx` `docx` `research-assistant`

### Communication

`himalaya`

### Dev Tools

`exec-tool` `git-tool` `code-search-tool` `web-fetch-tool` `browser-tool`
`skill-creator` `codex-cli` `claude-code` `coding-agent` `gemini` `gemini-cli`
`electron`

### Media & Content

`spotify` `spotify-player` `sonos` `video-frames` `sherpa-onnx-tts`

### Automation

`voice-call` `tmux` `autoresearch` `healthcheck`

## Installation

Foxl automatically loads skills from the `data/skills/` directory. To get the
latest skills:

```bash
cd /path/to/foxl/data
git clone https://github.com/foxl-ai/skills.git skills
```

To update:

```bash
cd /path/to/foxl/data/skills
git pull
```

Foxl also syncs this repo automatically on startup — the app calls
`POST /api/skills/sync` into a shallow clone under `data/skills/.git-repo/`
and merges new/updated skills into the local skills directory. Skills a user
has deleted locally stay deleted; skills the user has edited locally are
preserved (not overwritten by the pull).

## Creating Custom Skills

1. Create a new folder: `my-skill/`
2. Add `SKILL.md` with frontmatter and instructions
3. Optionally add `scripts/` for executable tools
4. Restart the agent to load the new skill

## License

MIT No Attribution (MIT-0). See [LICENSE](LICENSE).
