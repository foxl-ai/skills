---
name: research-assistant
description: "Multi-source research with cited findings: search, read primary sources, cross-check claims and write a sourced summary. Use when the user asks to research, investigate, compare options, fact-check or write a briefing on a topic, not for a single quick lookup."
enabled: true
tags: research, search, analysis, citations, fact-check
---

# Research Assistant

## Tools

- Web search: available only when the current model's provider offers it (Settings > Web Access). If there is none, say so once and work from URLs: official docs, the vendor's site, Wikipedia, arXiv, GitHub, or a search page in `browser`.
- `web_fetch` for static pages, APIs, RSS and docs; `browser` (open, then snapshot) for JavaScript-heavy pages; `browser_extension` only for pages behind the user's own login.
- Local material: `file_read`, `code_search`, `notes_search`, `memory_recall`.

## Method

1. Restate the question and what a good answer contains (scope, time range, region). Ask only if it is truly ambiguous.
2. Collect 3-8 sources, primary first: official documentation, original papers, filings, datasets, the vendor's own announcement. Treat blogs, forums and AI-written summaries as leads, not evidence.
3. Read the relevant part of each source rather than the snippet. Note the publication date: prefer current sources and flag anything older than the topic's pace (for fast-moving tech, older than about a year).
4. Cross-check every key claim against a second independent source. Record disagreements instead of picking one silently.
5. Stop when new sources stop changing the answer; do not fetch dozens of pages.

## Output

- Answer first: 2-4 sentences.
- Key findings as bullets, each with an inline citation `[1]`.
- Caveats: conflicts between sources, gaps, and what could not be verified.
- Sources: numbered list with title, publisher, date and URL.
- Only cite URLs you actually opened; never invent a citation. Separate facts from your own inference.
- For a long report, offer to save it as a Markdown file with `file_write`.
