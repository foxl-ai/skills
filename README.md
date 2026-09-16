<p align="center">
  <a href="https://foxl.ai"><img src="assets/readme/foxl.svg" width="64" height="64" alt="Foxl" /></a>
</p>

<h1 align="center">Foxl Skills</h1>

<p align="center">
  <strong>Useful knowledge. Ready for the next task.</strong><br />
  Instructions, scripts, and references that help Foxl do specialized work.<br />
  Read them. Understand them. Choose what your agent uses.
</p>

<p align="center">
  <a href="#get-started"><strong>Get started</strong></a> &nbsp;·&nbsp;
  <a href="#explore-the-library">Explore the library</a> &nbsp;·&nbsp;
  <a href="#create-a-skill">Create a skill</a> &nbsp;·&nbsp;
  <a href="#contribute">Contribute</a> &nbsp;·&nbsp;
  <a href="#licenses-and-attribution">Licenses</a>
</p>

A skill gives an agent a repeatable way to approach a particular kind of work: preparing a document, researching a question, working with a repository, or using a connected service.

Each skill lives in an ordinary folder, starting with a readable `SKILL.md`. Supporting scripts and reference material stay beside the instructions. This repository is the skill library; [Foxl Desktop](https://github.com/foxl-ai/foxl) provides the agent and its runtime.

## Get started

In Foxl Desktop:

1. **Open Skills** and choose **Sync** to check this library for updates.
2. **Review the proposed changes** before applying the sync.
3. **Choose a skill** and check its instructions, requirements, and enabled state.
4. **Try it in chat** with a small, concrete task.

> “Use the research assistant to turn these sources into a short briefing, with references.”

Some skills ship disabled and need to be enabled before use. Others need a local command, an account connection, or an API key. Each skill's frontmatter and instructions describe those requirements.

To inspect or contribute to the library without changing your installed skills:

```sh
git clone https://github.com/foxl-ai/skills.git
cd skills
```

The skill folders are under **`skills/` inside this checkout**. Use the app's Skills controls to manage your installed library; cloning this repository alone does not connect external services or install their tools.

## The ideas behind the library

**Make knowledge readable.** Instructions are plain Markdown. You can inspect a workflow before giving it a place in your agent's context.

**Be specific about the task.** A useful skill says when it applies, what inputs it needs, how to proceed, and how to judge the result.

**Put detail where it is needed.** Keep the main instructions focused. Longer references, reusable templates, and deterministic scripts belong in supporting files.

**Keep choice with the user.** Enabled state, tool requirements, and account connections are part of using a skill. Instructions should make those dependencies clear and respect the permissions of the host application.

## Explore the library

| Work | Skills |
| :--- | :--- |
| **Documents** | [Word](skills/docx/) · [PDF](skills/pdf/) · [PowerPoint](skills/pptx/) · [Excel](skills/xlsx/) |
| **Research and knowledge** | [Research assistant](skills/research-assistant/) · [Notion](skills/notion/) · [Obsidian](skills/obsidian/) · [Weather](skills/weather/) |
| **Email and workspace** | [Google Workspace](skills/gws/) · [Outlook](skills/outlook/) · [Outlook web fallback](skills/outlook-web/) · [Himalaya](skills/himalaya/) · [Quip](skills/quip/) |
| **Development** | [GitHub](skills/github/) · [Git](skills/git-tool/) · [Code search](skills/code-search-tool/) · [Shell execution](skills/exec-tool/) · [Web fetch](skills/web-fetch-tool/) · [Browser](skills/browser-tool/) · [Electron](skills/electron/) |
| **Coding agents** | [Coding agent](skills/coding-agent/) · [Claude Code](skills/claude-code/) · [Codex CLI](skills/codex-cli/) · [Gemini](skills/gemini/) · [Gemini CLI](skills/gemini-cli/) · [Skill creator](skills/skill-creator/) |
| **Media and audio** | [Spotify](skills/spotify/) · [Spotify player](skills/spotify-player/) · [Sonos](skills/sonos/) · [Video frames](skills/video-frames/) · [Local text-to-speech](skills/sherpa-onnx-tts/) |
| **Automation and experiments** | [Voice calls](skills/voice-call/) · [tmux](skills/tmux/) · [Autoresearch](skills/autoresearch/) · [Healthcheck](skills/healthcheck/) |

The library includes both everyday workflows and specialized experiments. A folder's presence does not mean its dependencies are installed or that it is enabled by default. The document skills also have [separate license terms](#licenses-and-attribution).

## Inside a skill

```text
skills/
  my-skill/
    SKILL.md          Instructions and metadata
    scripts/         Optional executable helpers
    references/      Optional detailed guidance
    templates/       Optional starting files
```

A minimal `SKILL.md`:

```markdown
---
name: meeting-brief
description: Turn meeting notes into a brief with decisions, owners, and next steps.
enabled: true
tags: [meetings, writing]
---

# Meeting brief

Use this skill when the user asks to summarize meeting notes.

1. Read the supplied notes and identify the meeting's purpose.
2. Separate decisions from open questions.
3. List next steps with owners and dates only when the notes provide them.
4. Return a concise brief and flag missing information.
```

### Common metadata

| Field | Purpose |
| :--- | :--- |
| `name` | Identifies the skill. Use a stable, descriptive name for new skills. |
| `description` | Explains what the skill does and when it should apply. |
| `enabled` | Controls whether it is enabled; `false` allows a skill to ship inactive. |
| `tags` | Describes its subject or category. |
| `requires` | Declares required commands, environment variables, or integrations. Existing skills show the supported forms. |

Some built-in skills also declare Foxl runtime tools. Those declarations depend on the host application's implementation; they do not make the checkout a standalone tool server.

## Create a skill

In Foxl's Skills page, choose **New**, then **Custom SKILL.md** to add your own instructions.

For a contribution to this library:

1. Add a folder under `skills/` with a clear name and a `SKILL.md`.
2. State the task, inputs, prerequisites, and expected result.
3. Add scripts or references only when they make the workflow more reliable.
4. Try a representative task and check the actual result.
5. Include appropriate license and attribution information for material you add.

The [skill creator](skills/skill-creator/) includes guidance and tools for evaluating and improving a skill.

## Contribute

Useful contributions include clearer instructions, corrected commands, better examples, and new workflows with a well-defined purpose.

Open a pull request explaining the task the skill helps with, what changed, and how you exercised it. Include required tools and setup steps. Keep credentials, personal documents, and private service data out of examples.

[Report a problem or propose a skill](https://github.com/foxl-ai/skills/issues) · [Foxl documentation](https://docs.foxl.ai/docs)

For a security issue, contact [security@foxl.ai](mailto:security@foxl.ai) privately.

## Licenses and attribution

The repository's default license is [MIT No Attribution (MIT-0)](LICENSE). **Individual skill licenses also apply.**

| Material | License information |
| :--- | :--- |
| Repository material without a separate license | [MIT-0](LICENSE) |
| Skill creator | [Apache-2.0](skills/skill-creator/LICENSE.txt) |
| Word, PDF, PowerPoint, and Excel skills | Separate Anthropic terms: [Word](skills/docx/LICENSE.txt), [PDF](skills/pdf/LICENSE.txt), [PowerPoint](skills/pptx/LICENSE.txt), [Excel](skills/xlsx/LICENSE.txt) |
| Other bundled components | [Third-party notices](THIRD_PARTY_NOTICES.md) |

Read the applicable skill's license before reusing or redistributing its contents.

<p align="center"><sub>Part of <a href="https://foxl.ai">Foxl</a> · Your day. A little lighter.</sub></p>
