---
name: pdf
description: Work with PDF files or produce a .pdf - read and pull out text, harvest tables, merge or combine documents, split them apart, rotate pages, stamp watermarks, build brand-new PDFs, fill PDF forms, password-encrypt or decrypt files, extract embedded images, and OCR scanned pages into searchable text.
enabled: true
license: MIT-0
---

# PDF processing guide

## Overview

This guide walks through the core PDF operations using a small set of Python
libraries and command-line tools. Two companion documents go deeper:

- `reference.md` - advanced capabilities, JavaScript libraries, extra worked
  examples, and troubleshooting.
- `forms.md` - the step-by-step procedure for filling PDF forms. Open it and
  follow it whenever the task is to fill in a form.

## Quick start

Open a file, count its pages, and pull the text out of every page with pypdf:

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("document.pdf")
print(f"Pages: {len(reader.pages)}")

text = ""
for page in reader.pages:
    text += page.extract_text()
print(text)
```

## Python libraries

### pypdf - basic operations

pypdf handles the page-level plumbing: reading, writing, combining, splitting,
rotating, and reading document metadata. The pieces you reach for most are
`PdfReader`, `PdfWriter`, `writer.add_page(page)`, `writer.write(fileobj)`,
`page.rotate(90)` (rotation is clockwise, in degrees), and `reader.metadata`
(with `.title`, `.author`, `.subject`, `.creator`, plus `.producer` and
`.creation_date`).

Merge several files into one:

```python
from pypdf import PdfReader, PdfWriter

inputs = ["part1.pdf", "part2.pdf", "part3.pdf"]
writer = PdfWriter()
for path in inputs:
    reader = PdfReader(path)
    for page in reader.pages:
        writer.add_page(page)
with open("merged.pdf", "wb") as out:
    writer.write(out)
```

Split a document into one file per page:

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("document.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{i + 1}.pdf", "wb") as out:
        writer.write(out)
```

Read the document metadata:

```python
from pypdf import PdfReader

reader = PdfReader("document.pdf")
meta = reader.metadata
print("Title:  ", meta.title)
print("Author: ", meta.author)
print("Subject:", meta.subject)
print("Creator:", meta.creator)
```

Rotate every page a quarter turn:

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("document.pdf")
writer = PdfWriter()
for page in reader.pages:
    page.rotate(90)  # 90 degrees clockwise
    writer.add_page(page)
with open("rotated.pdf", "wb") as out:
    writer.write(out)
```

### pdfplumber - text and table extraction

pdfplumber is the tool of choice when layout matters or when the page contains
tables. Open a file as a context manager, walk `pdf.pages`, and call
`page.extract_text()` or `page.extract_tables()` (which returns a list of
tables, each a list of rows).

Extract text while keeping the visual layout:

```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        print(page.extract_text())
```

Extract tables:

```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page_index, page in enumerate(pdf.pages):
        for table_index, table in enumerate(page.extract_tables()):
            print(f"--- page {page_index + 1}, table {table_index + 1} ---")
            for row in table:
                print(row)
```

Collect every table into a single spreadsheet. This treats the first row of
each table as the header. (pandas is a separate install and is not part of the
skill's virtual environment.)

```python
import pandas as pd
import pdfplumber

frames = []
with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        for table in page.extract_tables():
            if not table or len(table) < 2:
                continue
            frames.append(pd.DataFrame(table[1:], columns=table[0]))

combined = pd.concat(frames, ignore_index=True)
combined.to_excel("tables.xlsx", index=False)
```

### reportlab - create PDFs

reportlab builds PDFs from scratch. The low-level `canvas` API draws directly
onto the page; the high-level Platypus API flows content into a document.

Note that `letter` is `(612.0, 792.0)` points and `A4` is
`(595.28, 841.89)` points.

Draw with the canvas API:

```python
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

c = canvas.Canvas("basic.pdf", pagesize=letter)
width, height = letter
c.drawString(72, height - 72, "Quarterly report")
c.line(72, height - 84, width - 72, height - 84)
c.save()
```

Build a multi-page document with Platypus:

```python
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

doc = SimpleDocTemplate("report.pdf")
styles = getSampleStyleSheet()
story = [
    Paragraph("Annual summary", styles["Title"]),
    Spacer(1, 18),
    Paragraph("Overview of the year in review.", styles["Normal"]),
    PageBreak(),
    Paragraph("Appendix", styles["Heading1"]),
    Paragraph("Supporting detail follows.", styles["Normal"]),
]
doc.build(story)
```

Subscripts and superscripts:

Do not place Unicode subscript or superscript characters directly into
reportlab output. The built-in fonts have no glyphs for them, so they render as
solid black boxes. Inside a `Paragraph`, use reportlab's XML markup instead -
`<sub>` for subscripts and `<super>` for superscripts. For text drawn with the
canvas API (which does not accept that markup), adjust the font size and the
draw position by hand.

```python
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

doc = SimpleDocTemplate("science.pdf")
styles = getSampleStyleSheet()
story = [
    Paragraph("Water is written H<sub>2</sub>O.", styles["Normal"]),
    Paragraph("The area scales as r<super>2</super>.", styles["Normal"]),
]
doc.build(story)
```

## Command-line tools

### pdftotext (poppler-utils)

```bash
# Plain extraction to a text file
pdftotext input.pdf output.txt

# Preserve the visual layout
pdftotext -layout input.pdf output.txt

# Limit to a page range (first through last, inclusive)
pdftotext -f 1 -l 5 input.pdf output.txt
```

### qpdf

```bash
# Merge two files (page-selection blocks end with a bare --)
qpdf --empty --pages file1.pdf file2.pdf -- merged.pdf

# Keep only pages 1-5 of one file ("." means the primary input)
qpdf input.pdf --pages . 1-5 -- out.pdf

# Rotate page 1 by 90 degrees (+/- means relative; :range is optional)
qpdf input.pdf output.pdf --rotate=+90:1

# Strip a known password
qpdf --password=secret --decrypt encrypted.pdf decrypted.pdf
```

The rotation angle is `0`, `90`, `180`, or `270`; a leading `+` or `-` makes it
relative to the page's current rotation, and an omitted `:page-range` applies
to all pages.

### pdftk (if available)

```bash
# Merge
pdftk file1.pdf file2.pdf cat output merged.pdf

# Split into one file per page (also writes doc_data.txt; files are pg_%04d.pdf)
pdftk input.pdf burst

# Rotate page 1 a quarter turn clockwise
pdftk input.pdf rotate 1east output rotated.pdf
```

pdftk's rotation keywords are `north` (0), `east` (90), `south` (180), `west`
(270), `left` (-90), `right` (+90), and `down` (+180); `end` refers to the last
page.

## Common tasks

### OCR scanned PDFs

A scanned PDF is a picture of text, so it has to be rendered to images and read
with `pytesseract` (which needs the tesseract binary installed on the system).
Render the pages with pypdfium2 - the rasterizer this skill uses everywhere -
rather than pdf2image or poppler. See `reference.md` for more on pypdfium2.

```python
import pypdfium2 as pdfium
import pytesseract

pdf = pdfium.PdfDocument("scanned.pdf")
text = ""
for i in range(len(pdf)):
    page = pdf[i]
    image = page.render(scale=2.0).to_pil()
    text += f"\n--- page {i + 1} ---\n"
    text += pytesseract.image_to_string(image)
pdf.close()
print(text)
```

### Add a watermark

Load a one-page watermark and stamp it onto every page of the document:

```python
from pypdf import PdfReader, PdfWriter

watermark = PdfReader("watermark.pdf").pages[0]
reader = PdfReader("document.pdf")
writer = PdfWriter()
for page in reader.pages:
    page.merge_page(watermark)
    writer.add_page(page)
with open("watermarked.pdf", "wb") as out:
    writer.write(out)
```

### Extract images

`pdfimages` (poppler) writes each embedded image to a numbered file. The `-j`
flag emits JPEGs, producing `pictures-000.jpg`, `pictures-001.jpg`, and so on:

```bash
pdfimages -j input.pdf pictures
```

### Password protection

pypdf can encrypt on the way out. Copy the pages into a writer, encrypt with a
user password (needed to open the file) and an owner password (needed to change
permissions), then write. The signature is
`encrypt(user_password, owner_password=None, use_128bit=True, permissions_flag=..., *, algorithm=None)`,
and `algorithm="AES-256"` is supported for stronger encryption.

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("document.pdf")
writer = PdfWriter()
for page in reader.pages:
    writer.add_page(page)
writer.encrypt("userpassword", "ownerpassword")
with open("encrypted.pdf", "wb") as out:
    writer.write(out)
```

## Quick reference

| Task | Best tool | Command / Code |
|---|---|---|
| Merge PDFs | pypdf | `writer.add_page(page)` |
| Split PDFs | pypdf | one page per file |
| Extract text | pdfplumber | `page.extract_text()` |
| Extract tables | pdfplumber | `page.extract_tables()` |
| Create PDFs | reportlab | Canvas or Platypus |
| Command-line merge | qpdf | `qpdf --empty --pages ...` |
| OCR scanned PDFs | pytesseract | convert to image first |
| Fill PDF forms | pdf-lib or pypdf (see forms.md) | see forms.md |

## Next steps

- For advanced pypdfium2 usage, the JavaScript libraries (pdf-lib, pdfjs), and
  troubleshooting, see `reference.md`.
- For filling forms - both the fillable AcroForm kind and the flat, overlay
  kind - see `forms.md`.
