# PDF reference

This document collects the advanced features, the detailed examples, and the
libraries that go beyond the main skill guide - including the JavaScript
options and a troubleshooting section.

## pypdfium2 (Apache / BSD license)

pypdfium2 is a Python binding for PDFium, the PDF engine that ships inside
Chromium. It renders pages and generates images quickly, and it is a good
alternative to PyMuPDF.

```python
import pypdfium2 as pdfium
```

Rendering works off a `PdfDocument`. Index pages with `pdf[0]` or iterate the
document, render each page to a bitmap, and hand the bitmap to Pillow:

```python
import pypdfium2 as pdfium

pdf = pdfium.PdfDocument("document.pdf")

# First page at high resolution -> PNG
page = pdf[0]
bitmap = page.render(scale=2.0, rotation=0)   # higher scale = more detail
image = bitmap.to_pil()
image.save("page.png", "PNG")

# Every page at a lower scale -> JPEG
for i, page in enumerate(pdf):
    img = page.render(scale=1.0).to_pil()
    img.save(f"page_{i + 1}.jpg", "JPEG", quality=90)

pdf.close()
```

Text extraction is important to get right: in pypdfium2 5.x (checked on 5.14) there is **no**
`page.get_text()` method. Read text through the text page instead - call
`page.get_textpage()`, then `get_text_range()` for the whole page (or
`get_text_bounded(...)` for a region):

```python
import pypdfium2 as pdfium

pdf = pdfium.PdfDocument("document.pdf")
for i in range(len(pdf)):
    page = pdf[i]
    textpage = page.get_textpage()
    text = textpage.get_text_range()
    print(f"page {i + 1}: {len(text)} characters")
pdf.close()
```

## JavaScript - pdf-lib (MIT license)

pdf-lib has an async API. Import the pieces you need:

```javascript
import { PDFDocument, rgb, StandardFonts } from 'pdf-lib';
```

Load an existing file, inspect it, add a page, and save:

```javascript
import { PDFDocument } from 'pdf-lib';
import fs from 'fs';

const bytes = fs.readFileSync('document.pdf');
const doc = await PDFDocument.load(bytes);

console.log('pages:', doc.getPageCount());
console.log('indices:', doc.getPageIndices());

const page = doc.addPage([600, 400]);
page.drawText('Appended page', { x: 50, y: 350, size: 24 });

const out = await doc.save();
fs.writeFileSync('extended.pdf', out);
```

Create a styled document from scratch:

```javascript
import { PDFDocument, rgb, StandardFonts } from 'pdf-lib';
import fs from 'fs';

const doc = await PDFDocument.create();
const font = await doc.embedFont(StandardFonts.Helvetica);
const bold = await doc.embedFont(StandardFonts.HelveticaBold);

const page = doc.addPage([595, 842]);   // A4 in points
const { width, height } = page.getSize();

page.drawText('Invoice', {
  x: 50, y: height - 60, size: 28, font: bold,
  color: rgb(0.1, 0.1, 0.4),
});
page.drawRectangle({
  x: 50, y: height - 90, width: width - 100, height: 2,
  color: rgb(0.1, 0.1, 0.4),
});

const rows = [['Item', 'Qty', 'Price'], ['Widget', '3', '9.00']];
rows.forEach((cells, r) => {
  cells.forEach((text, c) => {
    page.drawText(text, {
      x: 50 + c * 150, y: height - 130 - r * 20, size: 12, font,
      color: rgb(0, 0, 0),
    });
  });
});

fs.writeFileSync('invoice.pdf', await doc.save());
```

Merge whole documents, or copy a specific set of pages:

```javascript
import { PDFDocument } from 'pdf-lib';
import fs from 'fs';

const mergedPdf = await PDFDocument.create();
const first = await PDFDocument.load(fs.readFileSync('first.pdf'));
const second = await PDFDocument.load(fs.readFileSync('second.pdf'));

// All of the first document...
const firstPages = await mergedPdf.copyPages(first, first.getPageIndices());
firstPages.forEach((p) => mergedPdf.addPage(p));

// ...and only pages 1, 3, and 5 of the second.
const somePages = await mergedPdf.copyPages(second, [0, 2, 4]);
somePages.forEach((p) => mergedPdf.addPage(p));

fs.writeFileSync('merged.pdf', await mergedPdf.save());
```

pdf-lib can also drive AcroForm fields directly: `doc.getForm()` returns the
form, then `form.getTextField(name).setText(...)`,
`form.getCheckBox(name).check()`,
`form.getRadioGroup(name).getOptions()` and `.select(opt)`,
`form.getDropdown(name).getOptions()`, and `form.flatten()` to bake the filled
values into the page content.

## JavaScript - pdfjs-dist (Apache license)

pdfjs-dist is Mozilla's PDF.js. Prefer the Python tools above for agent work;
reach for it when the job is already in JavaScript. In Node, import the legacy
build (`import * as pdfjsLib from 'pdfjs-dist/legacy/build/pdf.mjs'`) and open a
file with `const pdf = await pdfjsLib.getDocument({ data: new
Uint8Array(fs.readFileSync('document.pdf')) }).promise`.

Extract the text along with each item's position. Every item exposes `str`, a
6-element `transform` matrix (x is `transform[4]`, y is `transform[5]`), and
`width` and `height` (plus `dir`, `fontName`, and `hasEOL`):

```javascript
for (let n = 1; n <= pdf.numPages; n++) {
  const page = await pdf.getPage(n);
  const tc = await page.getTextContent();

  const plain = tc.items.map((item) => item.str).join(' ');
  const positioned = tc.items.map((item) => ({
    text: item.str,
    x: item.transform[4],
    y: item.transform[5],
    width: item.width,
    height: item.height,
  }));
  console.log(`page ${n}:`, plain.length, 'chars', positioned.length, 'items');
}
```

Read the annotations, including form fields. Note that the annotation's text is
exposed through `contentsObj.str` (an object with `str` and `dir`), not a bare
`contents` string:

```javascript
for (let n = 1; n <= pdf.numPages; n++) {
  const page = await pdf.getPage(n);
  const annotations = await page.getAnnotations();
  for (const a of annotations) {
    console.log(a.subtype, a.contentsObj && a.contentsObj.str, a.rect);
  }
}
```

Each annotation also carries `fieldName`, `fieldValue`, and `fieldType` for form
widgets.

## Advanced CLI - poppler-utils

```bash
# Emit XHTML with a bounding box for every word
pdftotext -bbox-layout document.pdf output.xml

# Render pages to PNG at 300 DPI (files are output_prefix-1.png, -2.png, ...)
pdftoppm -png -r 300 document.pdf output_prefix

# Render only pages 1 to 3
pdftoppm -png -f 1 -l 3 document.pdf output_prefix

# Render to JPEG at 200 DPI with a quality setting
pdftoppm -jpeg -jpegopt quality=85 -r 200 document.pdf out
```

```bash
# Extract embedded JPEGs, tagging each file with its page number:
#   out-<page>-<index>.jpg
pdfimages -j -p document.pdf out

# List the images without extracting anything
pdfimages -list document.pdf

# Extract every image in its original format (png, tiff, jpg, jp2, jbig2, ccitt)
pdfimages -all document.pdf images/img
```

Without `-p`, the extracted files are simply named `prefix-000.jpg`,
`prefix-001.jpg`, and so on.

## Advanced CLI - qpdf

```bash
# Split into fixed groups of 3 pages. A %d in the name is replaced by a
# zero-padded page range; if you leave it out and the name ends in .pdf,
# qpdf inserts a -range before the extension.
qpdf --split-pages=3 input.pdf output_group_%02d.pdf

# Extract a complex set of pages. Range syntax: comma list; a-b is inclusive;
# end (or z) is the last page; rN is the Nth from the end; an x prefix excludes
# pages; and :odd / :even select alternates.
qpdf input.pdf --pages input.pdf 1,3-5,8,10-end -- extracted.pdf

# Merge specific ranges out of several files
qpdf --empty --pages doc1.pdf 1-3 doc2.pdf 5-7 doc3.pdf 2,4 -- combined.pdf

# Linearize for web / streaming delivery
qpdf --linearize input.pdf optimized.pdf

# Shrink the file. --compression-level (1-9) needs --recompress-flate to touch
# streams that are already compressed; --object-streams=generate packs the
# object structure; --optimize-images recompresses embedded images.
qpdf --compression-level=9 --recompress-flate --object-streams=generate \
     --optimize-images input.pdf smaller.pdf

# Report structural validity
qpdf --check input.pdf

# Encrypt with 256-bit keys and restricted permissions
#   qpdf --encrypt <user-pw> <owner-pw> <bits> [opts] -- in.pdf out.pdf
# bits is 40, 128, or 256; the permission options below apply to 128/256-bit.
qpdf --encrypt userpw ownerpw 256 --print=low --modify=none -- input.pdf locked.pdf

# Inspect an encrypted file's settings
qpdf --show-encryption locked.pdf

# Remove a known password
qpdf --password=userpw --decrypt locked.pdf unlocked.pdf
```

The 128/256-bit permission options include `--print=none|low|full`,
`--modify=none|...`, `--extract=[y|n]`, `--annotate=[y|n]`, `--assemble=[y|n]`,
and `--form=[y|n]`. To rewrite a file in place (useful for repair), use
`qpdf --replace-input <file>`, which overwrites the input with a clean copy.

## Advanced Python - pdfplumber

`page.chars` is a list of per-character dictionaries with the keys `text`, `x0`,
`x1`, `y0`, `y1`, `top`, `bottom`, `fontname`, and `size`. You can also crop to
a region and pull the text out of just that box:

```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    page = pdf.pages[0]

    for char in page.chars[:5]:
        print(char["text"], char["x0"], char["y0"])

    region = page.within_bbox((50, 100, 550, 300))  # (left, top, right, bottom)
    print(region.extract_text())
```

Table detection can be tuned with a settings dictionary, and you can render the
page to an image to debug how the strategies are landing:

```python
import pdfplumber

settings = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 3,
    "intersection_tolerance": 3,
}

with pdfplumber.open("document.pdf") as pdf:
    page = pdf.pages[0]
    tables = page.extract_tables(settings)
    for table in tables:
        for row in table:
            print(row)
    page.to_image(resolution=150).save("debug.png")
```

## Advanced Python - reportlab tables

```python
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

data = [
    ["Region", "Q1", "Q2"],
    ["North", "120", "138"],
    ["South", "98", "104"],
]

doc = SimpleDocTemplate("table_report.pdf")
styles = getSampleStyleSheet()

table = Table(data)
table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 14),
    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
    ("GRID", (0, 0), (-1, -1), 1, colors.black),
]))

elements = [Paragraph("Sales by region", styles["Title"]), table]
doc.build(elements)
```

Each style tuple is a command name, a start cell `(col, row)`, an end cell
(`(-1, -1)` reaches the last column and row), and any command-specific
arguments.

## Complex workflows

### Extract figures and images

The fastest route is `pdfimages`, which pulls the images straight out of the
file structure in their original formats:

```bash
pdfimages -all document.pdf images/img
```

When the figures are not stored as discrete image objects, render the pages at
high resolution with pypdfium2 and analyze the pixels. The masking below is
illustrative and deliberately simple:

```python
import numpy as np
import pypdfium2 as pdfium

pdf = pdfium.PdfDocument("document.pdf")
page = pdf[0]
img = page.render(scale=3.0).to_pil()          # high-res render
arr = np.array(img)

# A crude "not white" mask marks ink and figure regions.
non_white = (arr[:, :, :3] < 245).any(axis=2)
print("non-white pixels:", int(non_white.sum()))
pdf.close()
```

### Batch processing

Iterate a directory, guard each file with try/except and logging, and support a
couple of operations - accumulating everything into one merged file, or writing
a sibling `.txt` per file:

```python
import glob
import logging

from pypdf import PdfReader, PdfWriter

logging.basicConfig(level=logging.INFO)


def process(directory, operation):
    if operation == "merge":
        writer = PdfWriter()
    for path in glob.glob(directory + "/*.pdf"):
        try:
            reader = PdfReader(path)
            if operation == "merge":
                for page in reader.pages:
                    writer.add_page(page)
            elif operation == "extract_text":
                text = "".join(page.extract_text() for page in reader.pages)
                with open(path + ".txt", "w", encoding="utf-8") as out:
                    out.write(text)
        except Exception as exc:
            logging.warning("skipping %s: %s", path, exc)
    if operation == "merge":
        with open("merged.pdf", "wb") as out:
            writer.write(out)
```

### Crop pages

Set the four `mediabox` edges (in points) and write the result:

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("document.pdf")
writer = PdfWriter()
for page in reader.pages:
    page.mediabox.left = 72
    page.mediabox.bottom = 72
    page.mediabox.right = 540
    page.mediabox.top = 720
    writer.add_page(page)
with open("cropped.pdf", "wb") as out:
    writer.write(out)
```

## Performance optimization tips

- For large documents, stream page by page (pypdfium2 is well suited to this)
  rather than loading everything at once, and use `qpdf --split-pages` to break a
  file into manageable pieces.
- For text, plain `pdftotext` is fastest, and pdfplumber is the better choice
  for structured content and tables. Avoid
  `pypdf.extract_text()` on very large documents.
- For images, `pdfimages` beats rendering. Render at low resolution for previews
  and reserve high resolution for the final output.
- For forms, pdf-lib preserves the document structure well; validate the field
  names before you write.
- To keep memory in check, process in fixed page chunks.

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("large.pdf")
total = len(reader.pages)
chunk_size = 50

for i in range(0, total, chunk_size):
    writer = PdfWriter()
    for page in reader.pages[i:i + chunk_size]:
        writer.add_page(page)
    with open(f"chunk_{i // chunk_size}.pdf", "wb") as out:
        writer.write(out)
```

## Troubleshooting

### Encrypted files

```python
from pypdf import PdfReader

reader = PdfReader("locked.pdf")
if reader.is_encrypted:
    try:
        reader.decrypt("password")
    except Exception as exc:
        print("could not decrypt:", exc)
```

### Corrupted files

```bash
# Report what is wrong
qpdf --check corrupted.pdf

# Rewrite the file in place, which repairs many structural problems
qpdf --replace-input corrupted.pdf
```

### Text extraction returns nothing (scanned pages)

The pages are images: use the OCR recipe in SKILL.md (pypdfium2 render +
pytesseract).

## License information

- pypdf: BSD
- pdfplumber: MIT
- pypdfium2: Apache / BSD
- reportlab: BSD
- poppler-utils: GPL-2
- qpdf: Apache
- pdf-lib: MIT
- pdfjs-dist: Apache
