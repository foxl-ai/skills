---
name: pptx
description: "Use this skill any time a .pptx file is involved in any way — as input, output, or both. This includes: creating slide decks, pitch decks, or presentations; reading, parsing, or extracting text from any .pptx file (even if the extracted content will be used elsewhere, like in an email or summary); editing, modifying, or updating existing presentations; combining or splitting slide files; working with templates, layouts, speaker notes, or comments. Trigger whenever the user mentions \"deck,\" \"slides,\" \"presentation,\" or references a .pptx filename, regardless of what they plan to do with the content afterward. If a .pptx file needs to be opened, created, or touched, use this skill."
enabled: true
license: Proprietary. LICENSE.txt has complete terms
---

# PPTX Skill

## Quick Reference

| Task | Guide |
|------|-------|
| Read/analyze content | `officecli view deck.pptx outline` / `text` |
| SEE the slides | `officecli view deck.pptx screenshot --grid` - see Rendering |
| Edit or create from template | Read [editing.md](editing.md) |
| Create from scratch | Read [pptxgenjs.md](pptxgenjs.md) |

---

## OfficeCLI (the primary read/render tool)

`officecli` is a single self-contained binary that reads and renders .pptx
directly. No LibreOffice, no PowerPoint, no Office install. Verify first:

```bash
officecli --version
```

If missing, install it (open a new shell if the binary still is not found):

```bash
# macOS / Linux
curl -fsSL https://d.officecli.ai/install.sh | bash
# Windows (PowerShell)
irm https://d.officecli.ai/install.ps1 | iex
```

Runs on macOS, Linux and Windows (x64 and arm64 on each, plus musl/Alpine
Linux) - the installer picks the right binary. **Write output next to the deck
or into a directory you created, not `/tmp`**: the examples below use `/tmp` for
brevity, but it does not exist on Windows - use `$env:TEMP` there, or just a
relative `out\` folder.

Supported formats are exactly `.docx`, `.xlsx`, `.pptx` - legacy `.ppt` is not.

---

## Reading Content

```bash
# Structure: slide count, titles, shape/picture counts per slide
officecli view presentation.pptx outline

# Plain text
officecli view presentation.pptx text

# Everything on one slide, as structured data
officecli get presentation.pptx '/slide[1]' --depth 1 --json

# Find shapes by property
officecli query presentation.pptx 'shape[fill=FF0000]'

# Problems (text overflow, missing alt text, low contrast)
officecli view presentation.pptx issues --json

# Visual overview - see Rendering below
officecli view presentation.pptx screenshot --grid -o /tmp/overview.png

# Raw XML
python scripts/office/unpack.py presentation.pptx unpacked/
```

Quote bracketed paths in bash/zsh (`'/slide[1]'`) - the shell glob-expands
brackets otherwise. `shape[1]` is usually the title placeholder; content shapes
start at `shape[2]`.

---

## Editing Workflow

**Read [editing.md](editing.md) for full details.**

1. Analyze template with `thumbnail.py`
2. Unpack → manipulate slides → edit content → clean → pack

---

## Creating from Scratch

**Read [pptxgenjs.md](pptxgenjs.md) for full details.**

Use when no template or reference presentation is available.

---

## Design Ideas

**Don't create boring slides.** Plain bullets on a white background won't impress anyone. Consider ideas from this list for each slide.

### Before Starting

- **Pick a bold, content-informed color palette**: The palette should feel designed for THIS topic. If swapping your colors into a completely different presentation would still "work," you haven't made specific enough choices.
- **Dominance over equality**: One color should dominate (60-70% visual weight), with 1-2 supporting tones and one sharp accent. Never give all colors equal weight.
- **Dark/light contrast**: Dark backgrounds for title + conclusion slides, light for content ("sandwich" structure). Or commit to dark throughout for a premium feel.
- **Commit to a visual motif**: Pick ONE distinctive element and repeat it — rounded image frames, icons in colored circles, thick single-side borders. Carry it across every slide.

### Color Palettes

Choose colors that match your topic — don't default to generic blue. Use these palettes as inspiration:

| Theme | Primary | Secondary | Accent |
|-------|---------|-----------|--------|
| **Midnight Executive** | `1E2761` (navy) | `CADCFC` (ice blue) | `FFFFFF` (white) |
| **Forest & Moss** | `2C5F2D` (forest) | `97BC62` (moss) | `F5F5F5` (cream) |
| **Coral Energy** | `F96167` (coral) | `F9E795` (gold) | `2F3C7E` (navy) |
| **Warm Terracotta** | `B85042` (terracotta) | `E7E8D1` (sand) | `A7BEAE` (sage) |
| **Ocean Gradient** | `065A82` (deep blue) | `1C7293` (teal) | `21295C` (midnight) |
| **Charcoal Minimal** | `36454F` (charcoal) | `F2F2F2` (off-white) | `212121` (black) |
| **Teal Trust** | `028090` (teal) | `00A896` (seafoam) | `02C39A` (mint) |
| **Berry & Cream** | `6D2E46` (berry) | `A26769` (dusty rose) | `ECE2D0` (cream) |
| **Sage Calm** | `84B59F` (sage) | `69A297` (eucalyptus) | `50808E` (slate) |
| **Cherry Bold** | `990011` (cherry) | `FCF6F5` (off-white) | `2F3C7E` (navy) |

### For Each Slide

**Every slide needs a visual element** — image, chart, icon, or shape. Text-only slides are forgettable.

**Layout options:**
- Two-column (text left, illustration on right)
- Icon + text rows (icon in colored circle, bold header, description below)
- 2x2 or 2x3 grid (image on one side, grid of content blocks on other)
- Half-bleed image (full left or right side) with content overlay

**Data display:**
- Large stat callouts (big numbers 60-72pt with small labels below)
- Comparison columns (before/after, pros/cons, side-by-side options)
- Timeline or process flow (numbered steps, arrows)

**Visual polish:**
- Icons in small colored circles next to section headers
- Italic accent text for key stats or taglines

### Typography

**Choose an interesting font pairing** — don't default to Arial. Pick a header font with personality and pair it with a clean body font.

| Header Font | Body Font |
|-------------|-----------|
| Georgia | Calibri |
| Arial Black | Arial |
| Calibri | Calibri Light |
| Cambria | Calibri |
| Trebuchet MS | Calibri |
| Impact | Arial |
| Palatino | Garamond |
| Consolas | Calibri |

| Element | Size |
|---------|------|
| Slide title | 36-44pt bold |
| Section header | 20-24pt bold |
| Body text | 14-16pt |
| Captions | 10-12pt muted |

### Spacing

- 0.5" minimum margins
- 0.3-0.5" between content blocks
- Leave breathing room—don't fill every inch

### Avoid (Common Mistakes)

- **Don't repeat the same layout** — vary columns, cards, and callouts across slides
- **Don't center body text** — left-align paragraphs and lists; center only titles
- **Don't skimp on size contrast** — titles need 36pt+ to stand out from 14-16pt body
- **Don't default to blue** — pick colors that reflect the specific topic
- **Don't mix spacing randomly** — choose 0.3" or 0.5" gaps and use consistently
- **Don't style one slide and leave the rest plain** — commit fully or keep it simple throughout
- **Don't create text-only slides** — add images, icons, charts, or visual elements; avoid plain title + bullets
- **Don't forget text box padding** — when aligning lines or shapes with text edges, set `margin: 0` on the text box or offset the shape to account for padding
- **Don't use low-contrast elements** — icons AND text need strong contrast against the background; avoid light text on light backgrounds or dark text on dark backgrounds
- **NEVER use accent lines under titles** — these are a hallmark of AI-generated slides; use whitespace or background color instead

---

## QA (Required)

**Assume there are problems. Your job is to find them.**

Your first render is almost never correct. Approach QA as a bug hunt, not a confirmation step. If you found zero issues on first inspection, you weren't looking hard enough.

### Content QA

```bash
python -m markitdown output.pptx
```

Check for missing content, typos, wrong order.

**When using templates, check for leftover placeholder text:**

```bash
python -m markitdown output.pptx | grep -iE "xxxx|lorem|ipsum|this.*(page|slide).*layout"
```

If grep returns results, fix them before declaring success.

### Visual QA

**⚠️ USE SUBAGENTS** — even for 2-3 slides. You've been staring at the code and will see what you expect, not what's there. Subagents have fresh eyes.

Render the slides to images (see [Rendering](#rendering-this-is-how-you-see-the-slides)), then use this prompt:

```
Visually inspect these slides. Assume there are issues — find them.

Look for:
- Overlapping elements (text through shapes, lines through words, stacked elements)
- Text overflow or cut off at edges/box boundaries
- Decorative lines positioned for single-line text but title wrapped to two lines
- Source citations or footers colliding with content above
- Elements too close (< 0.3" gaps) or cards/sections nearly touching
- Uneven gaps (large empty area in one place, cramped in another)
- Insufficient margin from slide edges (< 0.5")
- Columns or similar elements not aligned consistently
- Low-contrast text (e.g., light gray text on cream-colored background)
- Low-contrast icons (e.g., dark icons on dark backgrounds without a contrasting circle)
- Text boxes too narrow causing excessive wrapping
- Leftover placeholder content

For each slide, list issues or areas of concern, even if minor.

Read and analyze these images:
1. /tmp/slide-1.png (Expected: [brief description])
2. /tmp/slide-2.png (Expected: [brief description])

Report ALL issues found, including minor ones.
```

### Verification Loop

1. Generate slides → render to PNG (`officecli view ... screenshot`) → inspect
2. **List issues found** (if none found, look again more critically)
3. Fix issues
4. **Re-verify affected slides** — one fix often creates another problem.
   Re-render just the slide you touched:
   `officecli view output.pptx screenshot --start N --end N -o /tmp/slide-N.png`
5. Repeat until a full pass reveals no new issues

Run `officecli view output.pptx issues --json` alongside the visual pass - it
catches text overflow, missing alt text and low contrast mechanically. It does
NOT replace looking at the slides.

**Do not declare success until you've completed at least one fix-and-verify cycle.**

**Re-render, do not trust a cached image.** A stale PNG at the same path reads
as a passing check. Write to a fresh `-o` path (or delete the old file first)
whenever you re-verify.

---

## Rendering (this is how you SEE the slides)

`officecli` renders the real slide layout, so you can look at your own deck and
fix what is visibly wrong. This replaces the old PDF-then-rasterize two-step -
do not convert to PDF just to look at slides.

```bash
# ONE slide (default is slide 1)
officecli view output.pptx screenshot -o /tmp/slide-01.png

# A specific slide
officecli view output.pptx screenshot --start 3 --end 3 -o /tmp/slide-03.png

# Contact sheet: every slide tiled into ONE image, for a whole-deck pass
officecli view output.pptx screenshot --grid -o /tmp/overview.png
officecli view output.pptx screenshot --grid 4 -o /tmp/overview.png

# A slide range, wider raster (default 1600x1200)
officecli view output.pptx screenshot --start 1 --end 4 --grid 2 \
  --screenshot-width 1920 -o /tmp/first-four.png

# Crop to one shape
officecli view output.pptx screenshot --range '/slide[1]/shape[@id=100000]' -o /tmp/shape.png

# Vector render of a single slide (sharpest for text/equation checks).
# NOTE: svg mode ignores -o and writes to STDOUT - redirect it yourself.
officecli view output.pptx svg --start 3 --end 3 > /tmp/slide-03.svg

# Static HTML snapshot, or a live auto-refreshing preview
officecli view output.pptx html -o /tmp/deck.html
officecli watch output.pptx        # http://localhost:26315
officecli unwatch output.pptx
```

**`screenshot` writes ONE PNG, never a numbered series.** A `--start/--end`
range is stacked vertically into that single image and `--grid` tiles it - there
is no `slide-01.png, slide-02.png` output mode. For per-slide files, loop:

```bash
# macOS / Linux
for i in $(seq 1 12); do
  officecli view output.pptx screenshot --start "$i" --end "$i" -o "out/slide-$i.png"
done
```

```powershell
# Windows PowerShell - officecli ships win-x64 and win-arm64 binaries
1..12 | ForEach-Object {
  officecli view output.pptx screenshot --start $_ --end $_ -o "out\slide-$_.png"
}
```

`-o` is effectively required: with no `-o`, officecli writes a random temp file
and prints its path. PNG capture needs a headless browser on the machine
(Playwright / Chrome / Edge / Firefox, auto-detected); the renderer itself is
built in. `--render native` (real PowerPoint rasterization) is Windows-only and
errors elsewhere with `native_unavailable`.

**Flush before a non-officecli program reads the deck.** officecli keeps a
resident process, so python-pptx / an upload / a validator may otherwise read a
stale file:

```bash
officecli save output.pptx     # flush, keep resident warm
officecli close output.pptx    # flush + release
```

Also worth running on a finished deck:

```bash
officecli validate output.pptx            # OpenXML schema (structure only)
officecli view output.pptx issues --json   # overflow, missing alt text, contrast
```

---

## Dependencies

- **officecli**: reading, rendering (PNG/SVG/HTML), validation.
  `curl -fsSL https://d.officecli.ai/install.sh | bash` - verify with
  `officecli --version`. This is the primary tool.
- **a headless browser** (Playwright / Chrome / Edge / Firefox): only for
  `view ... screenshot`; auto-detected.
- `npm install -g pptxgenjs` - creating decks from scratch
- `pip install Pillow` - only if you build custom thumbnail grids yourself
  (`officecli view ... screenshot --grid` already makes contact sheets)
- `pip install "markitdown[pptx]"` - optional alternative text extraction
  (`officecli view ... text` covers this)

Not required: LibreOffice, PowerPoint, Poppler/`pdftoppm`. Legacy `.ppt` is not
supported by officecli - ask for a `.pptx`, and do not assume a converter
exists (probe first: `command -v soffice` on macOS/Linux,
`Get-Command soffice -ErrorAction SilentlyContinue` in PowerShell).
