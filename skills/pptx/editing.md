# Editing presentations

## Template-based workflow

1. **Analyze the existing slides.** Render a grid and read the outline so you know
   what each layout offers:

   ```bash
   officecli view template.pptx screenshot --grid -o out/template-grid.png
   officecli view template.pptx outline
   ```
   Read `out/template-grid.png` to see the layouts, and the outline to see
   slide titles and placeholder text. (`python scripts/thumbnail.py
   template.pptx` also works and additionally labels each tile with its
   `slideN.xml` filename and marks hidden slides - use it when you need to map
   a layout back to a specific XML part.)

2. **Plan the slide mapping.** For each section of your content, choose a template
   slide to carry it. Reach for varied layouts - monotony is the most common way a
   deck fails, so do not fall back to title-plus-bullets for everything. Look for
   multi-column (two- or three-column) slides, image-plus-text slides, full-bleed
   images with a text overlay, quote or callout slides, section dividers, stat or
   number callouts, and icon grids or icon-and-text rows. Match the content type to
   the layout: key points map to bullets, team information to multi-column,
   testimonials to a quote slide.

3. **Unpack the template.**

   ```bash
   python scripts/office/unpack.py template.pptx unpacked/
   ```

4. **Build the presentation structure yourself** (do not delegate this to
   subagents). Delete the slides you do not want by removing their `<p:sldId>` from
   `<p:sldIdLst>`; duplicate the slides you want to reuse with `add_slide.py`;
   reorder slides by rearranging the `<p:sldId>` elements. Finish every structural
   change before you move on to editing content.

5. **Edit the content.** Update the text in each `slide{N}.xml`. Because every slide
   is its own XML file, subagents can work on different slides in parallel at this
   stage.

6. **Clean up.**

   ```bash
   python scripts/clean.py unpacked/
   ```

7. **Pack the result.**

   ```bash
   python scripts/office/pack.py unpacked/ output.pptx
   python scripts/office/validate.py output.pptx
   ```

## Scripts

| Script | Purpose |
| --- | --- |
| `unpack.py` | Extract the PPTX and pretty-print its XML parts so they are readable and diffable. |
| `add_slide.py` | Duplicate a slide, or create a new slide from a layout. |
| `clean.py` | Remove orphaned parts that nothing references anymore. |
| `pack.py` | Repack the directory into a `.pptx`, applying safe repairs. |
| `thumbnail.py` | Build a labeled thumbnail grid of the deck. |

### unpack.py

```bash
python scripts/office/unpack.py input.pptx unpacked/
```

Extracts the archive and pretty-prints every `.xml` and `.rels` part so the markup
is easy to read and diff. Leaf text - the content of nodes like `<a:t>`, and
anything carrying `xml:space="preserve"` - is left exactly as it was, so words
round-trip unchanged. The `--no-merge-runs` and `--no-simplify-redlines` flags apply
to DOCX only and are no-ops for a PPTX. Unpacking does not "escape" smart quotes as a
separate step; curly quotes pass through untouched (the real rule is in Smart quotes,
below).

### add_slide.py

Duplicate a slide:

```bash
python scripts/add_slide.py unpacked/ slide2.xml
```

Create a slide from a layout:

```bash
python scripts/add_slide.py unpacked/ slideLayout2.xml
```

It writes `ppt/slides/slide{next}.xml`, where `next` is one greater than the highest
slide number already present. It also writes that slide's `_rels` (a clone of the
source slide's rels when you duplicate a slide, or a single slideLayout relationship
when you start from a layout), adds the matching `<Override>` to
`[Content_Types].xml`, and registers a slide relationship in
`ppt/_rels/presentation.xml.rels` under a fresh `rId`.

It does NOT edit `<p:sldIdLst>`: it prints a `<p:sldId id="..." r:id="..."/>`
element for you to paste into `<p:sldIdLst>` where the slide should appear. Ids
printed by earlier runs that were not pasted yet are skipped, so several slides can
be added before pasting.

### clean.py

```bash
python scripts/clean.py unpacked/
```

Walks the OPC relationship graph outward from the package root and
`ppt/presentation.xml`, then deletes every part the graph never reaches: slides no
longer listed in `<p:sldIdLst>`, plus the notes slides, media, embeddings, charts,
diagrams, drawings, and ink that only those orphaned slides referenced, along with any
unused theme parts and a stray `[trash]` directory. It keeps the package consistent as
it goes - removing each deleted part's `_rels`, pruning the relationships that pointed
at it, and dropping its `<Override>` from `[Content_Types].xml`. It is conservative: a
part is deleted only when nothing reachable references it, and a slide counts as
referenced for as long as `<p:sldIdLst>` still lists the `r:id` that targets it.

### pack.py

```bash
python scripts/office/pack.py unpacked/ output.pptx   # optional --no-repair
```

Zips the directory back into a deflated OPC container. Its default repairs are
Word-specific and do nothing on a deck. It does not validate: run
`python scripts/office/validate.py output.pptx` (lxml well-formedness plus
`officecli validate`) afterwards.

### thumbnail.py

```bash
python scripts/thumbnail.py input.pptx [output_prefix] [--cols N]
```

**Use for template analysis only** (choosing layouts, mapping a layout to its
`slideN.xml`). For visual QA, render full-resolution slides with
`officecli view deck.pptx screenshot --start N --end N -o out/slide-N.png` - see SKILL.md.

Writes `thumbnails.jpg` (default prefix), each tile labeled with its `slideN.xml`
filename; hidden slides (`show="0"`) get a crosshatched tile. `--cols` defaults to 3
(max 6); each sheet holds up to 12 tiles, and a larger deck is split into
`<prefix>-1.jpg`, `<prefix>-2.jpg`, ... Needs `officecli` on PATH and Pillow; it fails
loudly rather than writing a blank sheet.

## Slide operations

Slide order lives in `ppt/presentation.xml`, inside `<p:sldIdLst>`.

- **Reorder:** rearrange the `<p:sldId>` elements within `<p:sldIdLst>`.
- **Delete:** remove the slide's `<p:sldId>`, then run `clean.py` to sweep up the
  parts it referenced.
- **Add:** use `add_slide.py`. Never hand-copy slide files - the script handles the
  notes references, the `[Content_Types].xml` entry, and the relationship IDs that
  manual copying tends to miss.

## Editing content

Once the structure is settled (step 4 above is done), subagents can help here if they
are available: each slide is a separate XML file, so they can edit in parallel. When
you hand a slide to a subagent, tell it the slide file path(s), that it must use a
file-edit tool for every change, and the formatting rules and pitfalls below.

For each slide: read the slide XML, identify every piece of placeholder content (text,
images, charts, icons, captions), and replace each placeholder with the final content.

Make changes with your file-edit tool rather than `sed` or a Python script - it forces
you to be specific about what you are changing and where, which is far more reliable.

Formatting rules:
- Bold every header, subheading, and inline label by setting `b="1"` on the
  `<a:rPr>`. That covers slide titles, in-slide section headers, and inline labels at
  the start of a line (for example "Status:" or "Description:").
- Never use a unicode bullet character. Use real list formatting - `<a:buChar>` or
  `<a:buAutoNum>`.
- For bullet consistency, let bullets inherit from the layout; only specify
  `<a:buChar>` or `<a:buNone>` when you need to override.

## Common pitfalls

### Template adaptation

- When the source has fewer items than the template provides, remove the excess
  elements outright - images, shapes, text boxes - rather than just clearing their
  text. After you clear text, check for visuals that were left orphaned, and run
  visual QA to catch a mismatched count.
- When you replace text with text of a different length, shorter is usually safe, but
  longer text may overflow or wrap in ways you did not expect. Test it with visual QA,
  and consider truncating or splitting the content to fit the template's constraints.
- Template slots rarely match the number of source items. If the template lays out
  four team members but you only have three, delete the fourth member's ENTIRE group -
  the image and every text box - not just its text.

### Multi-item content

When the source has several items (a numbered list, or multiple sections), create one
`<a:p>` per item. Never concatenate them into a single string. Copy the `<a:pPr>` from
the original paragraph so the line spacing is preserved, and set `b="1"` on headers.

WRONG - several steps crammed into one paragraph and one run:

```xml
<a:p>
  <a:r>
    <a:rPr lang="en-US"/>
    <a:t>Draft the outline. Collect the assets. Assemble the deck.</a:t>
  </a:r>
</a:p>
```

CORRECT - one paragraph per item, line spacing carried over from the source, header
paragraphs bold and body paragraphs not:

```xml
<a:p>
  <a:pPr>
    <a:lnSpc><a:spcPts val="2000"/></a:lnSpc>
  </a:pPr>
  <a:r>
    <a:rPr lang="en-US" b="1"/>
    <a:t>Step 1: Draft the outline</a:t>
  </a:r>
</a:p>
<a:p>
  <a:pPr>
    <a:lnSpc><a:spcPts val="2000"/></a:lnSpc>
  </a:pPr>
  <a:r>
    <a:rPr lang="en-US"/>
    <a:t>Gather every image and data source you will need.</a:t>
  </a:r>
</a:p>
```

### Smart quotes

unpack and pack leave existing curly quotes untouched. Some edit tools normalize curly
quotes to ASCII, so when you add NEW text that contains quotes, write them as XML
numeric entities:

```xml
<a:t>The panel called it &#x201C;unmissable&#x201D; in the review.</a:t>
```

| Character | Name | Unicode | XML entity |
| --- | --- | --- | --- |
| “ | left double quote | U+201C | `&#x201C;` |
| ” | right double quote | U+201D | `&#x201D;` |
| ‘ | left single quote | U+2018 | `&#x2018;` |
| ’ | right single quote | U+2019 | `&#x2019;` |

### Other

- **Whitespace:** set `xml:space="preserve"` on any `<a:t>` that has leading or
  trailing spaces, or they will be stripped.
- **XML parsing:** if you script an XML change, use `lxml` (what the helper scripts
  use), not `xml.etree.ElementTree`, which rewrites namespace prefixes to `ns0:`.
