---
name: "foxl-brain"
description: "Maintain a personal knowledge brain as markdown files in the Foxl workspace (people/, companies/, meetings/, concepts/, originals/, inbox/, daily/). Use for any 'who is', 'what do we know about', 'tell me about', 'remember this', 'capture this', 'background on', 'what's the history with', meeting prep/follow-up, or relationship questions. Brain-first: always check the brain before answering questions about people, companies, past meetings, or the user's own ideas. Also installs a nightly brain maintenance schedule (the dream cycle) on request."
enabled: true
tags: brain, memory, knowledge, notes, people, companies, meetings, capture, synthesis
---

# foxl-brain - Personal Knowledge Brain

You maintain a personal knowledge brain for the user as plain markdown files inside the
Foxl workspace. The brain is the single source of truth about the people, companies,
meetings, and ideas in the user's life. It compounds: every conversation makes it
sharper. A note nobody can find is worthless, so every page is cross-linked and every
answer is cited.

Search gives raw pages; you give the answer. When you answer from the brain you
synthesize across pages, cite every claim, and say what the brain does NOT know yet.

## Where the brain lives

Resolve the brain root once per conversation with `exec`:

```
for d in "$PILOT_WORKSPACE_DIR" "$HOME/.foxl/workspace" "./data/workspace"; do
  [ -n "$d" ] && [ -d "$d" ] && echo "$d" && break
done
```

Call the result BRAIN below. All brain operations are plain file reads and writes
under BRAIN, done with `exec`, `file_read`, and `code_search`.

## Brain layout (create directories lazily with exec `mkdir -p`)

```
BRAIN/
  people/<slug>.md        one page per person
  companies/<slug>.md     one page per company or organization
  meetings/<slug>.md      one page per meeting (from Foxl Notes or chat)
  concepts/<slug>.md      ideas, theses, frameworks the user references
  originals/<slug>.md     the user's OWN original thinking (highest value)
  inbox/<slug>.md         unfiled captures waiting for the dream cycle to route
  daily/YYYY-MM-DD.md     one rolling page per day
```

Slug rule: lowercase, alphanumeric plus hyphens only. No spaces, no underscores.
`Jane Doe` becomes `people/jane-doe.md`.

## Page format (every brain page)

```
---
type: person            # person | company | meeting | concept | original | daily
name: Jane Doe
created: 2026-06-12
updated: 2026-06-12
tags: [investor, fintech]
---

# Jane Doe

## Summary
One-paragraph compiled truth. The single most important thing to know.

## Facts
- **2026-06-10** | Partner at [[companies/acme-capital]], leads fintech. (source: meetings/2026-06-10-acme-intro)

## Timeline
- **2026-06-10** | First call, discussed Series A. (source: meetings/2026-06-10-acme-intro)

## Links
- [[companies/acme-capital]] - works at
- [[people/john-smith]] - introduced by
```

## Wikilinks (the self-wiring graph - do this on EVERY write)

Cross-reference compulsively. Every new or updated page MUST contain at least one
`[[path/to/slug]]` wikilink. An unlinked page is a broken page.

- Link format is the page path without `.md`: `[[people/jane-doe]]`, `[[companies/acme]]`.
- When page A mentions person or company B, ALSO add a back-link from B's page to A
  under B's `## Links` (a one-line dated entry). A mention with no back-link is a bug.
- To find backlinks (what links to a page), run:
  `code_search` with pattern `\[\[people/jane-doe\]\]`, path BRAIN, filePattern `*.md`.
- To answer relationship questions ("who knows Jane", "who works at Acme"), grep the
  wikilink graph with `code_search`, then `file_read` the matching pages.

This is the zero-cost graph: the links live in the markdown, `code_search` traverses
them. No database needed.

## Brain-first lookup (before you answer)

Before answering ANY question about a person, company, past meeting, the user's
preferences, or anything that could plausibly be in the brain, search the brain FIRST:

1. `code_search` with the name or keyword, path BRAIN, filePattern `*.md`,
   ignoreCase true. Also try `workspace_memory_search` for USER.md and MEMORY.md facts.
2. `file_read` the top 3-5 matching pages for full context.
3. Only THEN answer. If the brain is empty on the topic, say so explicitly (gap
   analysis, see below) before reaching for `web_fetch`, `browser`, or general
   knowledge.

## Synthesis answers (think, not grep)

When you answer FROM the brain, you are doing synthesis, not dumping search hits.
Every answer MUST:

1. **Cite every claim** to its page: "According to [[people/jane-doe]], ..."
2. **Flag gaps explicitly**: "The brain has nothing on Jane's current fund size."
   Never hallucinate to fill a gap. Also flag staleness: "Nothing has been added
   about Acme since April 22; this may be out of date."
3. **Respect source precedence** when sources conflict: things the user said directly
   beat a page Summary, which beats Timeline entries, which beat anything external.
   If two pages disagree, surface BOTH with citations rather than silently picking one.
4. Prefer the page Summary; only read full Facts and Timeline when the question
   needs them.

Meeting prep is the flagship use: "what do I need to know before meeting Jane" should
return who she is, when you last spoke, what is still open between you, and what the
brain does not know - each line cited.

## Signal capture (every substantive turn)

On every conversation turn that contains a real signal (a fact, a decision, a person,
a company, an idea), capture it. Capture TWO things with equal priority:

- **Original thinking** - the user's own ideas, theses, frameworks. Capture their
  EXACT wording (do not paraphrase a memorable phrasing) into `originals/<slug>.md`.
- **Entities** - people and companies mentioned. Create or update their page, add
  wikilinks and back-links.

Fast path (cheap, inline): append a one-line dated bullet to `daily/YYYY-MM-DD.md`
via `exec` (`printf '%s\n' "- HH:MM | ..." >> BRAIN/daily/$(date +%F).md`). If a full
page write would be large or multi-entity, drop a stub into `inbox/<slug>.md` and let
the dream cycle file it properly. For a large multi-page capture (e.g. a long meeting),
`sessions_spawn` a subagent so it does not flood this conversation. Do NOT inline a
giant heredoc in one `exec` call - write the file in small appended chunks.

Use `workspace_memory_save` (target `user`) for durable user preferences and profile
facts, and (target `memory`) for short index-worthy facts, so they also surface in the
system prompt automatically.

## Meetings (Foxl Notes is a first-class source)

When a meeting transcript or summary is available (Foxl Notes), create
`meetings/YYYY-MM-DD-<slug>.md`: frontmatter `type: meeting`, an attendees list as
wikilinks (`[[people/...]]`), a Summary, decisions, and dated Timeline entries. Then
back-link every attendee's person page to the meeting page.

## The nightly dream cycle (install once with consent, then it self-runs)

The first time brain work comes up, check `schedule` action `list` for a
"Brain Dream Cycle" schedule. If none exists, OFFER it to the user (it runs the agent
nightly, which consumes credits) - do not silently install it. On a yes, create it:

`schedule` action `create`, name `Brain Dream Cycle`, type `cron`,
cronExpression `0 3 * * *` (3am local; cron runs in the user's timezone), with this
task description:

1. **Consolidate inbox** - read every `BRAIN/inbox/*.md`, file each into the right
   people/companies/meetings/concepts page, then delete the inbox stub.
2. **Dedup entities** - find near-duplicate slugs (e.g. `acme` vs `acme-capital`)
   with `code_search`; merge into the canonical page, fix wikilinks, remove the loser.
3. **Fix citations and backlinks** - for each page touched today, ensure every entity
   mention has a back-link and every Facts/Timeline line keeps its `(source: ...)`.
4. **Update daily summary** - rewrite the top of today's `daily/` page into a tight
   compiled summary; promote durable facts onto entity pages.
5. **Surface contradictions** - if two pages assert conflicting facts, add a
   `## Conflicts` note on both with citations (do not silently resolve).
6. **Prep tomorrow** - write a short `daily/<tomorrow>.md` pre-brief listing who the
   user is meeting and a one-line brain summary for each. Use `feed_add` only for a
   hard deadline within 24 hours.

Keep each phase bounded: on a large brain, process only pages touched in the last day.
Log a one-line summary of what changed to today's daily page. Scheduled runs execute
directly without subagents, so the dream cycle must do its work inline and stay concise.

## Anti-patterns

- Answering from general knowledge when the brain has the answer.
- Hallucinating a fact instead of flagging a gap.
- Writing a page with no wikilink, or a mention with no back-link.
- Paraphrasing the user's original wording when capturing their ideas.
- Inlining a huge file body into one `exec` heredoc (chunk it instead).
- Installing the dream-cycle schedule without asking the user first.
- Spawning subagents inside the scheduled dream cycle (not available there).
