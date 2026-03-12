---
name: nano-pdf
description: Edit PDFs with natural-language instructions
trigger: manual
requires: [nano-pdf]
---

# nano-pdf

Edit PDFs using natural-language instructions.

## Setup

```bash
uv pip install nano-pdf
```

## Usage

```bash
nano-pdf edit deck.pdf 1 "Change the title to 'Q3 Results' and fix the typo"
nano-pdf edit report.pdf 3 "Update the date to January 2026"
```

## Notes

- Page numbers may be 0-based or 1-based depending on version
- Always verify output PDF before sending
- Works best for text-based edits
