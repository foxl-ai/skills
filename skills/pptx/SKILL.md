---
name: pptx
description: "Create, read, edit, and combine PowerPoint .pptx files. Use for ANY task where a .pptx is an input, an output, or both: building slide decks, pitch decks, or presentations; reading, parsing, or extracting text from a deck (even when the text is reused elsewhere, such as an email or a summary); editing, modifying, or updating an existing presentation; combining or splitting slide files; and working with templates, layouts, speaker notes, or comments. Triggers on 'deck', 'slides', 'presentation', or any reference to a .pptx filename, no matter what happens to the content downstream. Fire whenever a .pptx must be opened, created, or touched."
enabled: true
license: MIT-0
---

# PPTX presentation skill

## Quick reference

| Task | Guide |
| --- | --- |
| Read/analyze content | `officecli view deck.pptx outline` / `text` |
| SEE the slides | `officecli view deck.pptx screenshot --grid` - see Rendering |
| Edit an existing deck, or build one from a template | read editing.md |
| Create a deck from scratch | read pptxgenjs.md |

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

## Reading content

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
python scripts/office/unpack.py presentation.pptx unpacked/   # then read unpacked/ppt/slides/*.xml
```

Quote bracketed paths in bash/zsh (`'/slide[1]'`) - the shell glob-expands
brackets otherwise. `shape[1]` is usually the title placeholder; content shapes
start at `shape[2]`.

## Editing workflow

For the full procedure - the scripts, the slide operations, and the pitfalls
that actually bite - read editing.md. In short:

1. Analyze the template with `python scripts/thumbnail.py template.pptx`, which
   builds a labeled grid you can use to map each layout back to its `slideN.xml`.
2. Unpack the deck, rearrange its slides, edit the text on each one, clean up the
   parts nothing references anymore, and pack it back into a `.pptx`.

## Creating from scratch

When there is no template or reference presentation to start from, build the deck
programmatically with the `pptxgenjs` library. The full API, examples, and gotchas
are in pptxgenjs.md.

## Design ideas

Plain bullet lists on a white background are the default that makes a deck
forgettable. Decide on a visual direction first, then apply one of the ideas below
to every slide.

Before you start:
- Choose a bold palette that fits the subject. A quick test: if the same colors
  would look at home in a completely unrelated deck, they are too generic - push
  for choices the content itself suggests.
- Let one color dominate. Give a single color 60-70% of the visual weight, add one
  or two supporting tones, and reserve one sharp accent. Never weight the colors
  equally.
- Play dark against light. Put dark backgrounds behind the title and the closing
  slide and keep the content slides light (the "sandwich"), or commit to dark
  everywhere for a premium feel.
- Pick one visual motif and repeat it on every slide - rounded image frames, icons
  set in colored circles, or a thick border on a single edge.

Palettes (hex values, no leading `#`; pick one that matches the topic instead of
defaulting to blue):

| Theme | Primary | Secondary | Accent |
| --- | --- | --- | --- |
| Midnight Executive | 1E2761 (navy) | CADCFC (ice blue) | FFFFFF (white) |
| Forest & Moss | 2C5F2D (forest) | 97BC62 (moss) | F5F5F5 (cream) |
| Coral Energy | F96167 (coral) | F9E795 (gold) | 2F3C7E (navy) |
| Warm Terracotta | B85042 (terracotta) | E7E8D1 (sand) | A7BEAE (sage) |
| Ocean Gradient | 065A82 (deep blue) | 1C7293 (teal) | 21295C (midnight) |
| Charcoal Minimal | 36454F (charcoal) | F2F2F2 (off-white) | 212121 (black) |
| Teal Trust | 028090 (teal) | 00A896 (seafoam) | 02C39A (mint) |
| Berry & Cream | 6D2E46 (berry) | A26769 (dusty rose) | ECE2D0 (cream) |
| Sage Calm | 84B59F (sage) | 69A297 (eucalyptus) | 50808E (slate) |
| Cherry Bold | 990011 (cherry) | FCF6F5 (off-white) | 2F3C7E (navy) |

Every slide needs a visual element - an image, a chart, an icon, or a shape. A
slide that is nothing but text is forgettable.

Layout options:
- Two columns: text on the left, an illustration on the right.
- Icon-and-text rows: an icon inside a colored circle, a bold header, and a short
  description below.
- A 2x2 or 2x3 grid: an image on one side, content blocks on the other.
- Half-bleed image: a full-height image on the left or right, with the content
  overlaid.

Data display:
- Large stat callouts: big numbers at 60-72pt with a small label underneath.
- Comparison columns: before/after, pros/cons, or side-by-side.
- Timeline or process flow: numbered steps joined by arrows.

Visual polish:
- Set icons in small colored circles beside section headers.
- Use italic accent text for a key stat or a tagline.

Typography - pick an interesting header/body pairing rather than defaulting to
Arial:

| Header | Body |
| --- | --- |
| Georgia | Calibri |
| Arial Black | Arial |
| Calibri | Calibri Light |
| Cambria | Calibri |
| Trebuchet MS | Calibri |
| Impact | Arial |
| Palatino | Garamond |
| Consolas | Calibri |

Sizes:

| Element | Size |
| --- | --- |
| Slide title | 36-44pt bold |
| Section header | 20-24pt bold |
| Body text | 14-16pt |
| Captions | 10-12pt, muted |

Spacing: keep margins of at least 0.5", leave 0.3-0.5" between content blocks, and
give the layout room to breathe.

Common mistakes to avoid:
- Do not reuse one layout on every slide - alternate columns, cards, and callouts.
- Do not center body text; left-align paragraphs and lists, and center only titles.
- Keep a clear size contrast - titles at 36pt or more against 14-16pt body text.
- Do not default to blue.
- Do not mix spacing at random; settle on 0.3" or 0.5" and stay consistent.
- Do not polish one slide and leave the rest plain.
- No text-only slides.
- Do not forget text-box padding: when you line rules or shapes up with the edge of
  the text, set `margin: 0` on the text box, or offset the shape to match.
- No low-contrast icons or text.
- NEVER put an accent line under a title - it is a hallmark of AI-generated slides;
  use whitespace or a background color instead.

## QA (required)

Assume the deck has problems and go hunting for them. The first render is almost
never right, so treat QA as a bug hunt rather than a confirmation pass - if you
come away with zero issues, you did not look hard enough.

### Content QA

Pull the text back out and read it with `python -m markitdown output.pptx`, then
check for content that went missing, typos, and slides in the wrong order.

When you started from a template, grep for placeholder text that survived:

```bash
python -m markitdown output.pptx | grep -iE "xxxx|lorem|ipsum|this.*(page|slide).*layout"
```

Fix every match before you declare success.

### Visual QA

Bring in a subagent for the visual pass even on a two- or three-slide deck; fresh
eyes catch what the author's eyes glide past. Render the slides to images (see
[Rendering](#rendering-this-is-how-you-see-the-slides)), then use this prompt:

```
You are reviewing rendered slides for defects. Assume issues exist and find them.
For each image, look for:
- Overlapping elements: text running through a shape, a line crossing words, or
  anything stacked on top of something else.
- Text overflow: content cut off at a slide edge or spilling past its box boundary.
- A decorative line placed for a one-line title that has since wrapped to two lines.
- Source citations or footers colliding with the content above them.
- Elements crowded together (gaps under 0.3") or cards that nearly touch.
- Uneven gaps between items.
- Too little edge margin (under 0.5").
- Columns that do not line up consistently.
- Low-contrast text, such as light gray on cream.
- Low-contrast icons, such as a dark glyph on a dark background with no contrasting
  circle behind it.
- Text boxes so narrow that lines wrap far more than they should.
- Leftover placeholder content.
List the issues for each slide, including minor ones, and report every issue you
find.

1. /tmp/slide-1.png (Expected: [brief description])
2. /tmp/slide-2.png (Expected: [brief description])
```

### Verification loop

1. Generate slides → render to PNG (`officecli view ... screenshot`) → inspect
2. List every issue you found. If the list is empty, look again, harder and more
   skeptically.
3. Fix the issues.
4. **Re-verify affected slides** - one fix often creates another problem.
   Re-render just the slide you touched:
   `officecli view output.pptx screenshot --start N --end N -o /tmp/slide-N.png`
5. Repeat the cycle until a full pass turns up nothing new.

Run `officecli view output.pptx issues --json` alongside the visual pass - it
catches text overflow, missing alt text and low contrast mechanically. It does
NOT replace looking at the slides.

Do not declare the deck finished until you have completed at least one full
fix-and-verify cycle.

**Re-render, do not trust a cached image.** A stale PNG at the same path reads
as a passing check. Write to a fresh `-o` path (or delete the old file first)
whenever you re-verify.

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
