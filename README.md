# Foxl Skills

Skills are folders of instructions, scripts, and resources that Foxl loads dynamically to improve performance on specialized tasks. Each skill teaches the agent how to complete specific tasks in a repeatable way.

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
always: false
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
| `requires` | No | System dependencies needed |
| `always` | No | If `true`, skill is always loaded into agent context |

## Included Skills (69)

### Productivity
`apple-notes` `apple-notes-native` `apple-reminders` `bear-notes` `notion` `obsidian` `outlook-web` `quip` `things-mac` `trello`

### Communication
`discord` `himalaya` `imsg` `slack`

### Development
`browser-tool` `code-review` `code-search-tool` `coding-agent` `drawio` `exec-tool` `gemini` `git-tool` `github` `electron` `kiro-send-tool`

### Media
`apple-photos` `camsnap` `gifgrep` `openai-image-gen` `peekaboo` `songsee` `video-frames` `voice-call` `whisper` `whisper-api`

### Documents
`docx` `pdf` `pptx` `xlsx` `nano-pdf`

### Research & Analysis
`autoresearch` `blogwatcher` `research-assistant` `summarize` `web-fetch-tool`

### Smart Home & Local
`food-order` `goplaces` `local-places` `openhue` `sonos` `spotify` `spotify-player` `weather`

### System & Utilities
`blucli` `eightctl` `healthcheck` `mcporter` `mole` `nano-banana-pro` `oracle` `sag` `session-logs` `sherpa-onnx-tts` `tmux` `wacli`

### Agents
`morning-briefing` `bird` `gog`

## Installation

Foxl automatically loads skills from the `data/skills/` directory. To get the latest skills:

```bash
cd /path/to/foxl/data
git clone https://github.com/foxl-ai/skills.git skills
```

To update:

```bash
cd /path/to/foxl/data/skills
git pull
```

## Creating Custom Skills

1. Create a new folder: `my-skill/`
2. Add `SKILL.md` with frontmatter and instructions
3. Optionally add `scripts/` for executable tools
4. Restart the agent to load the new skill

## License

MIT No Attribution (MIT-0). See [LICENSE](LICENSE).
