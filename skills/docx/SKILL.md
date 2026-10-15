---
name: docx
description: "Create, read, edit, review and render Word documents (.docx). Use when a Word or .docx file is the input or the requested output: reports, memos, letters or templates delivered as Word; extracting or reorganizing content; headings, tables of contents, page numbers, letterheads; inserting images; find-and-replace; tracked changes (redlines) and comments. Not for PDFs, spreadsheets, slides or Google Docs."
enabled: true
license: MIT-0
---

# Creating, Editing, and Analyzing Word Documents

## Overview

A `.docx` file is not a single blob - it is a ZIP archive, and everything inside
it is a collection of XML parts (the text, the styles, the relationships, the
media). That shape is what makes the workflows below possible: you can read and
render the archive with `officecli`, build a fresh one from JavaScript, or open
one up, edit the raw XML, and zip it back together.

## Quick Reference

| Task | How to do it |
| --- | --- |
| Read/analyze content | `officecli view` - see Reading Content below |
| SEE the rendered document | `officecli view <file> screenshot` / `html` - see Rendering below |
| Create a new document | docx-js, the `docx` npm package - see Creating New Documents with docx-js below |
| Modify an existing document | unpack, edit the XML, repack - see Editing Existing Documents below |

### OfficeCLI (the primary read/render tool)

`officecli` is a single self-contained binary that reads and renders .docx
directly. It does NOT need LibreOffice, Word, or any Office install. Verify
it is present before relying on it:

```bash
officecli --version
```

If it is missing, install it (then open a new shell if the binary is still not
found). Source and releases: https://github.com/iOfficeAI/OfficeCLI

```bash
# macOS / Linux
curl -fsSL https://d.officecli.ai/install.sh | bash
# Windows (PowerShell)
irm https://d.officecli.ai/install.ps1 | iex
```

The installer picks the right binary for macOS, Linux or Windows (x64/arm64).
On first install it also copies officecli's own SKILL.md into the config folders
of any other coding agents it detects in the home directory.

The examples write into `out/`; create it first (`mkdir out`). Do not hardcode
`/tmp`, which does not exist on Windows.

Only `.docx` is supported. Legacy binary `.doc` is NOT (see Legacy .doc below).

### Reading Content

```bash
# Plain text (paginate with --start/--end, cap with --max-lines)
officecli view document.docx text
officecli view document.docx text --start 1 --end 50

# Heading hierarchy / document structure
officecli view document.docx outline

# Text WITH formatting annotations (font, size, bold, style; equations as LaTeX)
officecli view document.docx annotated

# Machine-readable tree, one node and its children
officecli get document.docx /body --depth 1 --json

# Find things: CSS-like selectors
officecli query document.docx 'run:contains("TODO")'

# Document problems (overflow, missing alt text, ...)
officecli view document.docx issues --json

# Raw XML access (when you need to hand-edit - see Editing Existing Documents)
python scripts/office/unpack.py document.docx unpacked/
```

### Rendering (this is how you SEE the document)

`officecli` renders the real document layout, so you can look at your own
output and fix what is visibly wrong. Prefer this over converting to PDF.

```bash
# PNG you can open and inspect. -o is REQUIRED for a predictable path;
# without it officecli writes a random temp file and prints the path.
officecli view document.docx screenshot -o out/page1.png

# Specific pages (docx uses --page; comma list or range)
officecli view document.docx screenshot --page 1,3,5 -o out/pages.png
officecli view document.docx screenshot --page 2-5 -o out/pages.png

# Contact sheet: every page tiled into ONE image
officecli view document.docx screenshot --grid -o out/contact.png
officecli view document.docx screenshot --grid 4 -o out/contact.png

# Bigger raster (default 1600x1200)
officecli view document.docx screenshot --screenshot-width 1920 -o out/page.png

# Static HTML snapshot (assets inlined, single file)
officecli view document.docx html -o out/document.html

# Live preview that auto-refreshes on every officecli edit
officecli watch document.docx        # http://localhost:26315
officecli unwatch document.docx
```

**`screenshot` writes ONE PNG, never a numbered series.** A `--page` range is
composed into that single image, and `--grid` tiles it. There is no
`page-01.png, page-02.png` output mode - if you want one file per page, run
the command once per page with a different `-o`.

PNG capture needs a headless browser on the machine (Playwright / Chrome /
Edge / Firefox, auto-detected). The renderer itself is built in; only the
capture step needs the browser. `--render native` (real Word rasterization)
is Windows-only and errors elsewhere with `native_unavailable`.

### Verify Before You Call It Done

After writing a .docx, look at it before declaring success:

1. `officecli validate document.docx` - schema check (structure only)
2. `officecli view document.docx issues --json` - content/format problems
3. `officecli view document.docx screenshot --grid -o out/check.png` - then
   READ the image and list what is wrong
4. Fix, re-render, re-read. Do not declare success on the first pass.

**Flush before a non-officecli program reads the file.** officecli keeps a
resident process, so python-docx / a validator / an upload may otherwise read
a stale file on disk:

```bash
officecli save document.docx    # flush, keep resident warm
officecli close document.docx   # flush + release
```

### Tracked Changes with officecli

`officecli` reads and applies revisions directly - no LibreOffice, no macro.

```bash
# Read revisions (query selectors are UNPREFIXED - no leading slash)
officecli query document.docx revision
officecli query document.docx 'revision[revision.author=Alice]'
officecli query document.docx 'revision[revision.type=ins]'

# Accept / reject EVERYTHING (set paths DO take the leading slash)
officecli set document.docx /revision --prop revision.action=accept
officecli set document.docx /revision --prop revision.action=reject

# Accept / reject a subset
officecli set document.docx '/revision[@author=Alice]' --prop revision.action=accept
officecli set document.docx '/revision[@type=del]' --prop revision.action=reject

# Turn the tracking MODE on (distinct from the revision data)
officecli set document.docx /settings --prop trackRevisions=true
```

Covers ins, del, format, moveFrom, moveTo, paraMarkIns, rPrChange, pPrChange,
sectPrChange, and the table-property changes. Use `revision.*` keys - the
legacy `trackChange.*` keys were removed with no alias. `revision.action`
cannot be combined with a creation key in one call.

`officecli set` edits IN PLACE. To keep the original and write a clean copy,
use the wrapper (it copies first, applies, then flushes the resident):

```bash
python scripts/accept_changes.py input.docx output.docx
python scripts/accept_changes.py input.docx output.docx --reject
```

### Legacy .doc, and real PDF output

Neither is available through `officecli`, and neither is faked here:

- **`.doc` / `.rtf` (pre-2007 binary or RTF)**: `officecli` supports exactly
  `.docx`, `.xlsx`, `.pptx`. Reading `.doc` needs a format-handler plugin that
  is not published. Ask the user to re-save as `.docx`, or convert it with
  whatever converter the machine actually has (`soffice --headless
  --convert-to docx file.doc` if LibreOffice happens to be installed, or
  `pandoc`). Do NOT assume LibreOffice exists - probe first:
  `command -v soffice` on macOS/Linux,
  `Get-Command soffice -ErrorAction SilentlyContinue` in PowerShell.
- **PDF export**: `officecli view <file> pdf` requires an `exporter` plugin
  that is NOT shipped with the binary and has no published installer, so treat
  PDF as unavailable. If the deliverable must be a PDF, say so and ask how the
  user wants it produced. For *looking at* the document, use `screenshot` /
  `html` above - going through PDF buys nothing.

---

## Creating New Documents with docx-js

To build a `.docx` from scratch, generate it with JavaScript using the `docx`
npm package (docx-js, examples checked against 9.11), then validate the result
before handing it over.

Install it locally in the working directory. `require('docx')` does not find a
global (`npm install -g`) install.

```bash
npm install docx
```

### Setup

Everything comes from `require('docx')`, and the buffer is written with `fs`. A
document is a `Document` with one or more sections, and `Packer.toBuffer(doc)`
returns a `Promise` that resolves to a `Buffer` you write to disk.

```js
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun,
  Table, TableRow, TableCell,
  ImageRun, Header, Footer,
  AlignmentType, PageOrientation, LevelFormat,
  ExternalHyperlink, InternalHyperlink, Bookmark, FootnoteReferenceRun,
  PositionalTab, PositionalTabAlignment, PositionalTabRelativeTo, PositionalTabLeader,
  TabStopType, TabStopPosition,
  Column, SectionType, TableOfContents,
  HeadingLevel, BorderStyle, WidthType, ShadingType, VerticalAlign,
  PageNumber, PageBreak,
} = require('docx');

const doc = new Document({
  sections: [
    {
      children: [
        // document content goes here
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync('report.docx', buffer);
});
```

### Validation

Once the file is generated, validate it. If it fails, unpack it, fix the XML,
and repack (the Editing Existing Documents workflow below).

```bash
python scripts/office/validate.py report.docx
```

`validate.py` accepts either an unpacked directory or a packed
`.docx` / `.pptx` / `.xlsx`, and runs up to two layers:

- **Layer 1 - well-formedness.** Every `.xml` and `.rels` part must parse as
  valid XML (via lxml). This catches unbalanced tags, stray entities, and bad
  namespaces.
- **Layer 2 - schema/structure.** For a packed file, and only when `officecli`
  is on PATH, it shells out to `officecli validate`. On a directory the layer is
  reported as skipped (pack first); with no `officecli` it is also skipped.

The command exits 0 only if every layer that actually ran passed - a failing
`officecli validate` makes it exit 1, so a broken repack cannot slip through
green. Add `-v` / `--verbose` to print one `ok` line per part that parsed. A
path that is neither a directory nor an OOXML file is an error (exit 1).

### Page Size

Critical: docx-js defaults to **A4**, not US Letter. Always set the page size
explicitly. Sizes live at `sections[i].properties.page.size.{width,height}` and
margins at `sections[i].properties.page.margin.{top,right,bottom,left}`. All
values are in DXA (twentieths of a point), where 1440 DXA = 1 inch.

| Page | Width (DXA) | Height (DXA) | Content width (1-in margins) |
| --- | --- | --- | --- |
| US Letter | 12,240 (8.5 in) | 15,840 (11 in) | 9,360 |
| A4 (the default) | 11,906 | 16,838 | 9,026 |

```js
// US Letter, portrait, 1-inch margins on every side
{
  properties: {
    page: {
      size: {
        width: 12240,   // 8.5 in x 1440 DXA/in
        height: 15840,  // 11 in x 1440 DXA/in
      },
      margin: {
        top: 1440,      // 1 in
        right: 1440,    // 1 in
        bottom: 1440,   // 1 in
        left: 1440,     // 1 in
      },
    },
  },
  children: [
    // ...
  ],
}
```

For landscape, docx-js swaps width and height itself when it writes the XML, so
you still pass PORTRAIT numbers - short edge as `width`, long edge as `height` -
and add an `orientation` inside `size`:

```js
// Landscape US Letter
size: {
  width: 12240,   // short edge stays in `width`
  height: 15840,  // long edge stays in `height`
  orientation: PageOrientation.LANDSCAPE,
}
// After the swap, content width is measured across the LONG edge:
//   15840 - leftMargin - rightMargin  (e.g. 15840 - 1440 - 1440 = 12960)
```

### Styles and Overriding Built-in Headings

Use Arial as the default font - it is available everywhere - and keep title and
heading colors black for legibility. The default run formatting lives at
`styles.default.document.run`, and `size` is in half-points (so 24 = 12 pt).

To restyle the built-in headings, add entries to `styles.paragraphStyles`. The
`id` must be the exact built-in ID (`"Heading1"`, `"Heading2"`, ...) - anything
else creates a brand-new style instead of overriding the built-in one. Include
`outlineLevel`, or the heading will not appear in a table of contents.

```js
const doc = new Document({
  styles: {
    default: {
      document: {
        run: { font: "Arial", size: 24 },   // 24 half-points = 12 pt body text
      },
    },
    paragraphStyles: [
      {
        id: "Heading1",                      // exact built-in id
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 32, bold: true, font: "Arial" },   // 16 pt
        paragraph: {
          spacing: { before: 240, after: 240 },
          outlineLevel: 0,                   // required for TOC pickup
        },
      },
      {
        id: "Heading2",
        name: "Heading 2",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 28, bold: true, font: "Arial" },    // 14 pt
        paragraph: {
          spacing: { before: 180, after: 180 },
          outlineLevel: 1,
        },
      },
    ],
  },
  sections: [
    {
      children: [
        new Paragraph({
          heading: HeadingLevel.HEADING_1,
          children: [new TextRun("Quarterly Summary")],
        }),
      ],
    },
  ],
});
```

### Lists - No Literal Bullet Characters

Do not type bullet glyphs into a run. Both of these are wrong - the literal
glyph and its JS escape alike:

```js
// WRONG - a hand-typed bullet in the text
new Paragraph({ children: [new TextRun("• First item")] });
// Also WRONG: new TextRun("• First item")
```

Instead, declare the list formats in `Document({ numbering: { config: [...] } })`
and reference them from paragraphs:

```js
const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [
          {
            level: 0,
            format: LevelFormat.BULLET,
            text: "•",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } },
          },
        ],
      },
      {
        reference: "steps",
        levels: [
          {
            level: 0,
            format: LevelFormat.DECIMAL,
            text: "%1.",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } },
          },
        ],
      },
    ],
  },
  sections: [
    {
      children: [
        new Paragraph({
          numbering: { reference: "bullets", level: 0 },
          children: [new TextRun("A bulleted point")],
        }),
        new Paragraph({
          numbering: { reference: "steps", level: 0 },
          children: [new TextRun("A numbered step")],
        }),
      ],
    },
  ],
});
// Counting is per reference: reuse "steps" and it keeps going (1, 2, 3, then
// 4, 5, 6); switch to a different reference and the count restarts at 1.
```

### Tables

Critical: a table needs BOTH a `columnWidths` array on the `Table` AND a `width`
on every `TableCell`. Miss either one and some platforms render the table wrong.
The width rules, all of which matter:

- Always set the table `width`, and always with `WidthType.DXA`. Never
  `WidthType.PERCENTAGE` - it breaks in Google Docs.
- `columnWidths` must sum exactly to the table `width`.
- Each cell `width` must equal that column's entry in `columnWidths`.
- Cell `margins` are internal padding: they shrink the content area, they do NOT
  add to the cell width.
- A full-width table equals the content width = page width minus the left and
  right margins. On US Letter with 1-inch margins that is 12240 - 2880 = 9360.

Shading uses `ShadingType.CLEAR` (never SOLID, which produces black cell
backgrounds).

```js
// A reusable border spec, applied to all four edges of each cell
const cellBorder = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };

const table = new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [4680, 4680],                 // sums to 9360
  rows: [
    new TableRow({
      children: [
        new TableCell({
          width: { size: 4680, type: WidthType.DXA },   // == columnWidths[0]
          borders: { top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder },
          shading: { fill: "D5E8F0", type: ShadingType.CLEAR },  // CLEAR, not SOLID
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({ children: [new TextRun("Region")] })],
        }),
        new TableCell({
          width: { size: 4680, type: WidthType.DXA },   // == columnWidths[1]
          borders: { top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({ children: [new TextRun("Revenue")] })],
        }),
      ],
    }),
  ],
});
```

An uneven split works the same way, as long as the numbers still add up:

```js
// Full-width on US Letter: content width = 12240 - 2880 = 9360 DXA
const wideTable = new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [7000, 2360],                 // uneven, still sums to 9360
  rows: [ /* ... */ ],
});
```

### Images

Place an `ImageRun` inside a `Paragraph`'s children. The `type` field is
REQUIRED (allowed: `png`, `jpg`, `jpeg`, `gif`, `bmp`, `svg`), `data` is the raw
bytes, `transformation` sizes the image in pixels, and `altText` needs all three
of `title`, `description`, and `name`.

```js
new Paragraph({
  children: [
    new ImageRun({
      type: "png",                             // required
      data: fs.readFileSync("logo.png"),
      transformation: { width: 200, height: 150 },   // pixels
      altText: {
        title: "Company logo",
        description: "The Foxl wordmark in blue",
        name: "logo",
      },
    }),
  ],
});
```

### Page Breaks

A `PageBreak` must live INSIDE a `Paragraph`'s children - a standalone one
produces invalid XML. The alternative is `pageBreakBefore` on the paragraph that
should start the new page.

```js
// A break inside a paragraph
new Paragraph({ children: [new PageBreak()] });

// Or: force this paragraph to open a new page
new Paragraph({
  pageBreakBefore: true,
  children: [new TextRun("This section starts on a fresh page.")],
});
```

### Hyperlinks

An external link is an `ExternalHyperlink`; its text runs use `style:
"Hyperlink"`.

```js
new Paragraph({
  children: [
    new ExternalHyperlink({
      children: [new TextRun({ text: "Visit Foxl", style: "Hyperlink" })],
      link: "https://foxl.ai",
    }),
  ],
});
```

An internal link is a bookmark at the destination plus an `InternalHyperlink`
whose `anchor` equals the bookmark `id`.

```js
// 1. Mark the destination with a Bookmark (here, inside a heading)
new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [
    new Bookmark({
      id: "methods",
      children: [new TextRun("Methods")],
    }),
  ],
});

// 2. Link to it from somewhere else
new Paragraph({
  children: [
    new InternalHyperlink({
      children: [new TextRun({ text: "See the Methods section", style: "Hyperlink" })],
      anchor: "methods",                       // must match the Bookmark id
    }),
  ],
});
```

### Footnotes

Declare the notes on the `Document` as an object keyed by number, then reference
each one inline with a `FootnoteReferenceRun` placed right after the text it
annotates.

```js
const doc = new Document({
  footnotes: {
    1: { children: [new Paragraph("Figures are unaudited.")] },
    2: { children: [new Paragraph("Excludes one-time charges.")] },
  },
  sections: [
    {
      children: [
        new Paragraph({
          children: [
            new TextRun("Revenue rose sharply"),
            new FootnoteReferenceRun(1),
            new TextRun(" in every region"),
            new FootnoteReferenceRun(2),
            new TextRun("."),
          ],
        }),
      ],
    },
  ],
});
```

### Tab Stops

To put right-aligned text on the same line as left text (a date opposite a name,
say), begin the second `TextRun` with a tab and give the paragraph a
right-aligned tab stop at the far margin:

```js
new Paragraph({
  tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
  children: [
    new TextRun("Project Kickoff"),
    new TextRun({ text: "\tJanuary 5, 2026" }),   // leading tab jumps to the stop
  ],
});
```

For a TOC-style dotted leader ending in a page number at the right margin, use a
`PositionalTab` inside a run's children:

```js
new Paragraph({
  children: [
    new TextRun("Chapter 1"),
    new TextRun({
      children: [
        new PositionalTab({
          alignment: PositionalTabAlignment.RIGHT,
          relativeTo: PositionalTabRelativeTo.MARGIN,
          leader: PositionalTabLeader.DOT,
        }),
        "12",
      ],
    }),
  ],
});
```

Tab stops, not tables, are the right tool for two-column header and footer lines
(see Headers and Footers).

### Multi-Column Layouts

Columns are a section property (`properties.column`), and content flows across
the columns automatically.

```js
// Two equal columns with a vertical rule between them
{
  properties: {
    column: {
      count: 2,
      space: 720,          // gap in DXA (720 = 0.5 in)
      equalWidth: true,
      separate: true,      // draw a rule between columns
    },
  },
  children: [ /* content flows across both columns */ ],
}

// Custom column widths
{
  properties: {
    column: {
      equalWidth: false,   // required when giving explicit widths
      children: [
        new Column({ width: 5400, space: 720 }),
        new Column({ width: 3240 }),
      ],
    },
  },
  children: [ /* ... */ ],
}
```

To force content onto the next column, start a new section with `type:
SectionType.NEXT_COLUMN`.

### Table of Contents

Build a TOC with `TableOfContents`. The heading paragraphs it collects must use
`HeadingLevel` only - a custom paragraph style on them and the TOC skips them.

```js
new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-3" });
```

### Headers and Footers

Headers and footers are section keys. Put a page number together from a literal
label run and a `PageNumber` run.

```js
{
  properties: {
    page: {
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },   // 1 in each
    },
  },
  headers: {
    default: new Header({
      children: [new Paragraph({ children: [new TextRun("Quarterly Report")] })],
    }),
  },
  footers: {
    default: new Footer({
      children: [
        new Paragraph({
          children: [
            new TextRun("Page "),
            new TextRun({ children: [PageNumber.CURRENT] }),
          ],
        }),
      ],
    }),
  },
  children: [ /* ... */ ],
}
```

### docx-js Rules Checklist

- Set the page size explicitly. The default is A4; US documents want US Letter,
  12240 x 15840 DXA.
- Landscape: give PORTRAIT dimensions (short edge as `width`, long edge as
  `height`) plus `orientation: PageOrientation.LANDSCAPE`; docx-js swaps them
  internally.
- Never use `\n` for a line break inside text - make separate `Paragraph`s.
- Never type unicode bullet characters - use `LevelFormat.BULLET` in a
  `numbering` config.
- A `PageBreak` must sit inside a `Paragraph` (standalone is invalid XML).
- `ImageRun` needs a `type` (png/jpg/etc.).
- A table `width` is always set and always `WidthType.DXA`; never
  `WidthType.PERCENTAGE` (Google Docs breaks on it).
- Use dual widths - a `columnWidths` array AND a per-cell `width` - and keep them
  in agreement.
- The table width must equal the exact sum of `columnWidths`.
- Always give cells margins; `{ top: 80, bottom: 80, left: 120, right: 120 }`
  reads well.
- Table shading uses `ShadingType.CLEAR`, never SOLID.
- Never build divider lines or rules out of tables - cells have a minimum height
  and show up as empty boxes (headers and footers included). Put a bottom border
  on a Paragraph instead: `border: { bottom: { style: BorderStyle.SINGLE, size:
  6, color: "2E75B6", space: 1 } }`. For two-column footers, use tab stops (see
  Tab Stops), not tables.
- A TOC needs `HeadingLevel` only on heading paragraphs - no custom styles.
- Override built-in styles by their exact ID: "Heading1", "Heading2", etc.
- Include `outlineLevel` (0 for H1, 1 for H2, ...) - the TOC depends on it.

---

## Editing Existing Documents

To change an existing `.docx`, do three things in order: unpack it, edit the
XML, then pack it back up.

### Step 1 - Unpack

```bash
python scripts/office/unpack.py document.docx unpacked/
```

Full usage is `unpack.py [--no-merge-runs] [--no-simplify-redlines] office_file
output_dir`. It accepts `.docx`, `.pptx`, and `.xlsx` (anything else, or a
missing file, is an error and exits 1) and creates `output_dir` if needed. What
it does:

- extracts the ZIP;
- pretty-prints every `.xml` and `.rels` part so the markup is readable and
  diffable (a part that fails to parse is left as-is, with a WARN on stderr);
- the pretty-printer never rewrites the text inside `<w:t>` or any other leaf
  element, and it leaves `xml:space="preserve"` content alone, so the words
  survive an unpack/pack round-trip unchanged;
- for DOCX only, and only on `word/document.xml`, it then tidies the body by
  default:
  - **merge runs** removes `<w:proofErr>` markers, drops the `w:rsid*`
    attributes from `<w:r>`, merges neighbouring `<w:r>` siblings whose `<w:rPr>`
    is identical (inside `<w:ins>` and `<w:del>` too), and joins the adjacent
    `<w:t>` text, adding `xml:space="preserve"` when the joined text starts or
    ends with a space;
  - **simplify redlines** fuses directly adjacent `<w:ins>`+`<w:ins>` (or
    `<w:del>`+`<w:del>`) siblings that share a `w:author` (date ignored), within
    one paragraph or table cell.

Pass `--no-merge-runs` to skip the run merging, or `--no-simplify-redlines` to
skip the tracked-change fusing. Curly quotes and apostrophes already in the
document come out as literal UTF-8 characters in the XML (verified by
round-trip) - unpack does NOT turn them into entities.

### Step 2 - Edit the XML

Edit the parts under `unpacked/word/`; the main body is `word/document.xml`. The
markup patterns you will need (tracked changes, comments, images) are in the XML
Reference section below.

**Use "Foxl" as the author** for tracked changes and comments, unless the user explicitly requests use of a different name.

Make string replacements with your file-edit tool directly rather than writing a
Python script to do them: the edit shows exactly which text is being replaced.

New text you add must use typographic (smart) quotes and apostrophes, not
straight ones. You can write them as numeric character entities:

| Entity | Character |
| --- | --- |
| `&#x2018;` | ' - left single quote |
| `&#x2019;` | ' - right single quote / apostrophe |
| `&#x201C;` | " - left double quote |
| `&#x201D;` | " - right double quote |

```xml
<w:r>
  <w:t>The committee&#x2019;s ruling was described as &#x201C;final and unappealable&#x201D; that morning.</w:t>
</w:r>
```

Literal UTF-8 curly characters are equally valid XML. Because `unpack.py` leaves
the curly quotes that were already in the document as literal characters, an
edit match string has to use the literal character, not the entity, to line
up with what is on disk.

**Adding comments:** `comment.py` writes one comment into all four Word comment
parts (`comments.xml`, `commentsExtended.xml`, `commentsIds.xml`,
`commentsExtensible.xml`), creating them plus their relationships and content
types if missing. Pass plain text; the script escapes it. `comment_id` and
`--parent` are integers (`--parent N` exits 1 if comment N does not exist). It
prints the anchor markup to paste into `document.xml`.
```bash
python scripts/comment.py unpacked/ 0 "Comment text with & and ’ written literally"
python scripts/comment.py unpacked/ 1 "Good catch - agreed" --parent 0  # reply to comment 0
python scripts/comment.py unpacked/ 0 "Text" --author "Custom Author"  # default author is Foxl
```

After that, add the range markers and the reference run to `document.xml` - see
the Comments part of the XML Reference below.

### Step 3 - Pack

```bash
python scripts/office/pack.py unpacked/ output.docx
python scripts/office/validate.py output.docx        # then check the result
```

Full usage is `pack.py [--no-repair] input_directory output_file`. The output
suffix must be `.docx` / `.pptx` / `.xlsx`, the input must be a directory, and it
creates the output's parent directory. It writes a plain deflated ZIP of every
file in the directory - which is all an OOXML container is. It does NOT validate,
and it does NOT minify or condense the XML, so run `validate.py` on the output
afterwards (see Validation) and/or the officecli verification loop.

Before zipping, it applies two safe repairs (skip them all with `--no-repair`):

- any hex id attribute - `paraId`, `textId`, or `durableId` (w14/w15/w16) - whose
  value is above 0x7FFFFFFF, or is not valid hex, is replaced with a fresh random
  8-hex-digit id at or below 0x7FFFFFFF;
- any `<w:t>` whose text begins or ends with whitespace gets
  `xml:space="preserve"`.

It prints how many id/space fixes it made. It does NOT repair malformed XML
(those parts are skipped by the repair pass - `validate.py` catches them),
invalid element nesting, missing relationships, or schema violations.

### Common Pitfalls

- When you add a tracked change, replace the WHOLE `<w:r>...</w:r>` with a
  `<w:del>` and `<w:ins>` pair as SIBLINGS. Never put tracked-change tags inside
  a run.
- Carry the formatting across: copy the original run's `<w:rPr>` into each run
  inside the `<w:del>` and `<w:ins>`, so bold, size, and the rest survive the
  edit.

---

## XML Reference

### Schema Compliance

Word enforces the child order inside `<w:pPr>`. Keep them in this sequence:
`<w:pStyle>`, then `<w:numPr>`, then `<w:spacing>`, then `<w:ind>`, then
`<w:jc>`, and `<w:rPr>` last. Any `<w:t>` with leading or trailing spaces needs
`xml:space="preserve"`, or Word trims the space. RSID stamps are 8 hex digits
(for example `00F3A21C`).

### Tracked Changes

An insertion is a `<w:ins>` wrapping normal runs (`<w:r><w:t>...</w:t></w:r>`); a
deletion is a `<w:del>` wrapping runs whose text element is `<w:delText>`. Each
revision element carries `w:id`, `w:author`, and `w:date` (ISO 8601 UTC, e.g.
`YYYY-MM-DDTHH:MM:SSZ`), and each one gets its own `w:id`.

**Insertion:**

```xml
<w:ins w:id="1" w:author="Foxl" w:date="2025-01-01T00:00:00Z">
  <w:r><w:t>a newly added sentence</w:t></w:r>
</w:ins>
```

**Deletion:**

```xml
<w:del w:id="2" w:author="Foxl" w:date="2025-01-01T00:00:00Z">
  <w:r><w:delText>the text being removed</w:delText></w:r>
</w:del>
```

Inside a `<w:del>`, the text element changes: `<w:delText>` replaces `<w:t>`, and
`<w:delInstrText>` replaces `<w:instrText>`.

**Minimal edit** - mark only the characters that change, and leave everything
else in ordinary runs before and after the del/ins pair. Here the due day is
changed from Friday to Monday:

```xml
<!-- Change the due day from Friday to Monday -->
<w:r><w:t xml:space="preserve">The report is due </w:t></w:r>
<w:del w:id="1" w:author="Foxl" w:date="...">
  <w:r><w:delText>Friday</w:delText></w:r>
</w:del>
<w:ins w:id="2" w:author="Foxl" w:date="...">
  <w:r><w:t>Monday</w:t></w:r>
</w:ins>
<w:r><w:t>.</w:t></w:r>
```

**Deleting an entire paragraph or list item** - besides wrapping its runs in a
`<w:del>`, mark the paragraph mark itself deleted with a self-closing `<w:del/>`
inside `<w:pPr><w:rPr>`, so the paragraph merges into the next one:

```xml
<w:p>
  <w:pPr>
    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>  <!-- keep only for a list item -->
    <w:rPr>
      <w:del w:id="1" w:author="Foxl" w:date="2025-01-01T00:00:00Z"/>
    </w:rPr>
  </w:pPr>
  <w:del w:id="2" w:author="Foxl" w:date="2025-01-01T00:00:00Z">
    <w:r><w:delText>This entire paragraph is being removed.</w:delText></w:r>
  </w:del>
</w:p>
```

Without the `<w:del/>` inside `<w:pPr><w:rPr>`, accepting the change leaves an
empty paragraph (or empty bullet) behind. Keep the `<w:numPr>` in `<w:pPr>` only
when the paragraph is a list item.

**Rejecting someone else's insertion** - nest your `<w:del>` INSIDE their
`<w:ins>`; their insertion stays, wrapping your deletion (whose run uses
`<w:delText>`):

```xml
<w:ins w:id="5" w:author="Morgan" w:date="2025-01-01T00:00:00Z">
  <w:del w:author="Foxl" w:id="10">
    <w:r><w:delText>text Morgan had inserted</w:delText></w:r>
  </w:del>
</w:ins>
```

**Restoring someone else's deletion** - leave their `<w:del>` untouched and add
your own `<w:ins>` right after it (as a sibling) with the same text in an
ordinary `<w:t>` run:

```xml
<w:del w:id="5" w:author="Morgan" w:date="2025-01-01T00:00:00Z">
  <w:r><w:delText>text Morgan had deleted</w:delText></w:r>
</w:del>
<w:ins w:author="Foxl" w:id="10">
  <w:r><w:t>text Morgan had deleted</w:t></w:r>
</w:ins>
```

### Comments

After `comment.py` writes the comment parts (Step 2), anchor the comment in
`document.xml`. Critical: `<w:commentRangeStart>` and `<w:commentRangeEnd>` are
SIBLINGS of `<w:r>` - direct children of `<w:p>` - and NEVER go inside a `<w:r>`.
The reference run goes after the range end, and this exact markup is safe to use
as-is: `<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference
w:id="0"/></w:r>`. A comment range may enclose tracked-change elements (a
`<w:del>`, for example) as well as plain runs.

For a reply, create it with `--parent` and nest the reply's range markers inside
the parent's range. The nested order is: start(parent), start(reply), the
commented runs, end(reply), end(parent), then the reference run for the parent
followed by the reference run for the reply.

```xml
<!-- Part 1: the markers are direct children of <w:p>, never inside a <w:r>.
     The comment range here wraps a Foxl deletion plus a plain run. -->
<w:commentRangeStart w:id="0"/>
<w:del w:id="1" w:author="Foxl" w:date="2025-01-01T00:00:00Z">
  <w:r><w:delText>an obsolete clause</w:delText></w:r>
</w:del>
<w:r><w:t>the sentence that remains</w:t></w:r>
<w:commentRangeEnd w:id="0"/>
<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="0"/></w:r>

<!-- Part 2: comment 0 with reply 1 nested inside its range -->
<w:commentRangeStart w:id="0"/>
  <w:commentRangeStart w:id="1"/>
  <w:r><w:t>the text under discussion</w:t></w:r>
  <w:commentRangeEnd w:id="1"/>
<w:commentRangeEnd w:id="0"/>
<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="0"/></w:r>
<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="1"/></w:r>
```

### Images in Raw XML

Adding an image to unpacked XML is four steps:

1. Put the image file in `word/media/`.
2. Add a `<Relationship>` to `word/_rels/document.xml.rels` - a so-far-unused
   `Id`, the image relationship `Type`, and a `Target` pointing at the media
   file:

   ```xml
   <Relationship Id="rId5"
     Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
     Target="media/diagram.png"/>
   ```

3. Register the extension in `[Content_Types].xml` (one `<Default>` per
   extension, if it is not already present):

   ```xml
   <Default Extension="png" ContentType="image/png"/>
   ```

4. Reference it in `document.xml` inside a run. `r:embed` must equal the
   relationship `Id`, `wp:extent` is in EMU (914400 EMU = 1 inch), and the
   picture `graphicData` uses the picture URI. This is the FULL, schema-valid
   form - `wp:inline` also needs a `<wp:docPr>` after `wp:extent`, and `pic:pic`
   needs `<pic:nvPicPr>` before and `<pic:spPr>` after `pic:blipFill` (run
   `validate.py` if you abbreviate any of it):

   ```xml
   <w:r>
     <w:drawing>
       <wp:inline>
         <wp:extent cx="914400" cy="914400"/>   <!-- EMU; 914400 = 1 inch, so 1 in square -->
         <wp:docPr id="1" name="Diagram"/>
         <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
           <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
             <pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
               <pic:nvPicPr>
                 <pic:cNvPr id="1" name="Diagram"/>
                 <pic:cNvPicPr/>
               </pic:nvPicPr>
               <pic:blipFill>
                 <a:blip r:embed="rId5"/>       <!-- must equal the Relationship Id -->
               </pic:blipFill>
               <pic:spPr/>
             </pic:pic>
           </a:graphicData>
         </a:graphic>
       </wp:inline>
     </w:drawing>
   </w:r>
   ```

---

## Dependencies

- **officecli** (primary): reading, rendering, tracked changes, validation; install above.
- **a headless browser** (Playwright / Chrome / Edge / Firefox): only for
  `view ... screenshot`; auto-detected.
- **docx** (npm, local install): creating new documents with docx-js.
- **python**: `scripts/office/{unpack,pack,validate}.py` for raw-XML editing.

Not required: LibreOffice, Word, Poppler/`pdftoppm`, pandoc. If a task genuinely
needs a legacy `.doc` conversion or a real PDF, see "Legacy .doc, and real PDF
output" above - check what the machine has instead of assuming.

The Python scripts need Python 3.10+ and `lxml` (`pip install lxml`);
`accept_changes.py` and `validate.py`'s schema layer additionally call
`officecli`.
