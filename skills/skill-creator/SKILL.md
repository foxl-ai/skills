---
name: skill-creator
description: "Create a new Foxl skill or improve an existing one: interview the user, write the SKILL.md in Foxl's format, validate it, test it on realistic prompts, and tighten its description so the agent picks it at the right time. Use when the user wants to turn a workflow into a skill, edit or fix a skill, or asks why a skill is not being used."
enabled: true
requires: [python3]
tags: skills, development
---

# Skill Creator

## How Foxl uses a skill

- Skills live in the skills directory named at the top of the `<available_skills>` list (normally `~/.foxl/skills/`), one folder each: `<folder>/SKILL.md` plus optional `scripts/`, `references/`, `assets/`.
- Only `name`, folder, `tags` and `description` go into every prompt. The agent reads the whole SKILL.md with `file_read` only after it picks the skill, and reads bundled files only when SKILL.md points to them by path.
- So the description decides whether the skill is ever used, and the body decides whether it works.
- A new or edited folder is picked up within about 10 seconds, no restart. Users can also edit a skill in Settings > Connect > Skills.

## Frontmatter (Foxl's parser is a simple line parser)

```yaml
---
name: my-skill
description: "What it does and when to use it, on ONE line. Use 'single quotes' inside."
enabled: true
requires: [jq, MY_API_TOKEN]
tags: research, pdf
---
```

| Field | Rule |
|---|---|
| `name` | Required. Lowercase, digits, hyphens; usually the folder name. Renaming later changes the skill's id. |
| `description` | Required. One line, double-quoted if it contains `:`. No `\"` escapes. |
| `enabled` | Only an explicit `false` hides it by default; the user's toggle overrides it. |
| `requires` | Array. SCREAMING_CASE = environment variable, `integration:<provider>` = a connected integration, anything else = a binary on PATH. A missing binary or variable does not hide the skill, so say how to install or set it in the body. |
| `requiresAny` | `true` makes `requires` "any one of". |
| `platforms` | `[darwin, linux, win32]`; omit for all. |
| `tags` | A few short words; they are in every prompt. |

`trigger` and `schedule` are ignored; recurring runs belong on the Schedules page.

## Writing the description

State WHAT the skill does and WHEN to use it, with the words a user would actually say (product names, file types, verbs). Mention the boundary when a neighbouring tool or skill is the better choice. Keep it to one or two sentences: every skill's description is paid for in every conversation.

## Writing the body

- Lead with the commands or steps that work, using the real Foxl tool names: `exec` (shell), `process` (background jobs), `terminal` (interactive PTY), `file_read`, `file_write`, `file_edit`, `code_search`, `web_fetch`, `browser`. Check a tool exists before naming it.
- Verify every CLI flag with `<cli> --help` or the official docs. Never invent flags, model ids or endpoints; put the docs URL beside anything that changes often.
- Explain why when a rule is not obvious; skip marketing, history and duplicated sections.
- Keep SKILL.md under about 300 lines. Move long reference material into `references/<topic>.md` and say exactly when to read it.
- Put deterministic or repeated work in `scripts/` and call it with `exec` (`python3 <skills dir>/<folder>/scripts/x.py`).
- Say what needs the user's confirmation (sending, deleting, spending money) and never put secrets in the file; read them from environment variables.
- Public skills: English, no personal paths or names.

## Workflow

1. Capture intent: what the skill should do, when it should trigger, the expected output, the tools or credentials it needs. If the conversation already shows the workflow, extract it from there and confirm.
2. Draft `<skills dir>/<name>/SKILL.md` with `file_write`.
3. Validate: `python3 <skills dir>/skill-creator/scripts/quick_validate.py <skills dir>/<name>` (checks the frontmatter rules above). Fix every error.
4. Test with 2-3 realistic prompts a user would type. Run each yourself following only the skill, or hand it to a fresh subagent with `sessions_spawn` (goal: the prompt plus "read and follow <path>/SKILL.md"). Compare the result with what the user expects.
5. Show the user the results, ask what is wrong, revise, and re-test. Generalise from feedback instead of patching one example.
6. Check triggering: list a few prompts that should and should not pick the skill, and make sure the description separates them.

## Optional: quantitative evals (needs the Claude Code CLI)

The bundled `scripts/` (`run_eval.py`, `run_loop.py`, `improve_description.py`, `aggregate_benchmark.py`), `agents/` (grader, comparator, analyzer instructions), `eval-viewer/` and `references/schemas.md` implement Anthropic's benchmark and description-optimisation loop. They drive `claude -p`, so they work only where the `claude` CLI is installed and signed in, and they measure Claude Code's skill triggering, not Foxl's. Read `references/schemas.md` before using them.
