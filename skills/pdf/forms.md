# Filling PDF forms

Filling a form is a step-ordered procedure. Work through the steps in order and
resist the urge to write filling code before the detection step has told you
which kind of form you are dealing with.

All of the helper scripts live in `scripts/` and are run from the skill
directory as `python scripts/<name>.py ...`. They take positional arguments
only - there is no `--help` and no `--flag` parsing. In particular
`check_fillable_fields.py`, `extract_form_field_info.py`, and
`check_bounding_boxes.py` treat their first argument (even the literal string
`--help`) as a file path. Passing the wrong number of arguments prints a usage
line to stderr and exits with code 2. Every page rasterization is done with
pypdfium2 (PDFium), not pdf2image or poppler.

## Step 1 - detect the form type

Run the detector first:

```bash
python scripts/check_fillable_fields.py form.pdf
```

Under the hood this calls pypdf's `PdfReader.get_fields()`; an empty or falsy
result means there is no AcroForm. Branch on the first word of the output, not
on the exit code (the exit code is 0 in both cases):

- Output that begins `FILLABLE: 'form.pdf' has N AcroForm form field(s).`
  means the PDF carries real, interactive form fields. Follow the
  **Fillable-fields workflow** below.
- Output that begins `NOT FILLABLE: 'form.pdf' has no AcroForm form fields.`
  means the page is flat and text must be painted onto it. Follow the
  **Non-fillable-fields workflow** below.

---

## Fillable-fields workflow (the PDF has AcroForm fields)

### F1 - Extract the field information

```bash
python scripts/extract_form_field_info.py form.pdf field_info.json
```

The JSON is always printed to stdout. The output-file argument is optional; when
you supply it the script also writes that file and notes
`Wrote N field(s) to field_info.json` on stderr. Pass the filename so the values
file you author next has something concrete to refer back to.

The output is a JSON list, one object per fillable field:

- `field_id` - the fully-qualified field name (parent `/T` names joined with
  dots).
- `page` - the 1-based page the field sits on.
- `type` - one of `"text"`, `"checkbox"`, `"radio_group"`, or `"choice"`.
- `rect` - the widget rectangle as `[left, bottom, right, top]`, measured in PDF
  points with **y = 0 at the bottom of the page**. It is present for text,
  checkbox, and choice fields, but not on a `radio_group` itself (each radio
  button carries its own rect instead).
- Type-specific keys:
  - checkbox: `checked_value` (set the field to this to tick the box - it is the
    widget's on-state name, for example `"/Yes"`) and `unchecked_value` (always
    `"/Off"`).
  - radio_group: `radio_options`, a list of `{ "value", "rect" }` objects, one
    per button, where `value` is that button's on-state name (for example
    `"/Yes"` or `"/No"`).
  - choice: `choice_options`, a list of `{ "value", "text" }` objects, where
    `value` is the export value and `text` is the display label.

Push buttons and signature (`/Sig`) fields are left out, since they hold no
fillable value. A representative `field_info.json` with one field of each type:

```json
[
  {
    "field_id": "applicant.last_name",
    "page": 1,
    "rect": [140.0, 712.0, 340.0, 730.0],
    "type": "text"
  },
  {
    "field_id": "applicant.subscribe",
    "page": 1,
    "rect": [140.0, 676.0, 156.0, 692.0],
    "type": "checkbox",
    "checked_value": "/Yes",
    "unchecked_value": "/Off"
  },
  {
    "field_id": "applicant.plan",
    "page": 1,
    "type": "radio_group",
    "radio_options": [
      { "value": "/basic", "rect": [140.0, 636.0, 154.0, 650.0] },
      { "value": "/pro", "rect": [200.0, 636.0, 214.0, 650.0] }
    ]
  },
  {
    "field_id": "applicant.country",
    "page": 1,
    "rect": [140.0, 594.0, 280.0, 614.0],
    "type": "choice",
    "choice_options": [
      { "value": "US", "text": "United States" },
      { "value": "CA", "text": "Canada" }
    ]
  }
]
```

### F2 - Render the pages to understand each field

```bash
python scripts/convert_pdf_to_images.py form.pdf pages/
```

This writes `pages/page_1.png`, `pages/page_2.png`, and so on (1-based). It
prints each path followed by the image's `WxH`, then a final count. Look at the
images to work out what each field is actually for. Because `rect` is in PDF
points with y = 0 at the bottom, while the image is addressed in top-origin
pixels, you have to convert bounding boxes when you want to line a field up with
a spot in the rendered picture.

### F3 - Author the values file

Write `field_values.json` as a JSON list, one object per field you want to set:

- `field_id` (required) - must match a `field_id` from step F1.
- `value` (required) - the value to enter.
- `page` (optional) - if present it must equal the field's own `page`, or
  validation fails.
- `description` (optional) - a free-text note for whoever reads the file later.

The accepted `value` depends on the field type:

- text: any string.
- checkbox: exactly the field's `checked_value` or its `unchecked_value`.
- radio_group: one of the `radio_options[].value` names.
- choice: one of the `choice_options[].value` export values, or one of the
  display `text` labels.

```json
[
  {
    "field_id": "applicant.last_name",
    "page": 1,
    "value": "Okafor",
    "description": "Applicant surname"
  },
  {
    "field_id": "applicant.subscribe",
    "value": "/Yes",
    "description": "Opt into the newsletter"
  },
  {
    "field_id": "applicant.plan",
    "value": "/pro",
    "description": "Chosen subscription tier"
  }
]
```

### F4 - Fill the form

```bash
python scripts/fill_fillable_fields.py form.pdf field_values.json filled.pdf
```

Every requested value is validated against the discovered fields before
anything is written. If any request is wrong, the script prints
`Validation failed; no output written:` followed by one `  - <message>` line per
problem to stderr, exits 1, and writes no output file. The problems it reports
include:

- an unknown `field_id` ("unknown field_id (not present in the PDF)"),
- a `page` that does not match the field's page ("page X does not match field
  page Y"),
- a checkbox, radio, or choice value outside the allowed set ("... must be one
  of [...]"),
- a missing `value` ("missing 'value'"), and a values file that is not a JSON
  list at all ("field_values.json must be a JSON list of field objects").

On success it prints `Filled N field(s); wrote filled.pdf` and exits 0.

Internally it clones the reader into a writer with `PdfWriter(clone_from=reader)`,
calls `writer.set_need_appearances_writer(True)` so viewers regenerate the field
appearances, and applies the values a page at a time with
`writer.update_page_form_field_values(page, mapping, auto_regenerate=False)`.

One thing to know: because the appearances rely on NeedAppearances, some
renderers only show the values once form rendering is switched on (pypdfium2,
for instance, needs `init_forms()`). The value is stored in the field's `/V`
either way, so the data is present even if a particular preview does not paint
it.

---

## Non-fillable-fields workflow (a flat PDF, no form fields)

Here the page has no interactive fields, so text has to be overlaid at the right
coordinates. Prefer coordinates read out of the PDF's own structure - they are
far more accurate - and fall back to eyeballing the rendered image only when
structure extraction turns up no usable text.

Throughout this workflow, coordinates use **top-origin** PDF points or pixels:
y = 0 is at the **top** of the page and increases downward. This is the opposite
of the bottom-origin `rect` you saw from `extract_form_field_info.py` in the
fillable workflow, so keep the two straight.

### N1 - Try structure extraction first

```bash
python scripts/extract_form_structure.py form.pdf form_structure.json
```

This uses pdfplumber and writes an object of the shape `{ "pages": [ ... ] }`.
Each page object contains:

- `page_number` (1-based), `width`, and `height` (the page size in PDF points),
- `labels` - every extracted word as `{ "text", "x0", "top", "x1", "bottom" }`,
- `lines` - near-horizontal rule lines as `{ "x0", "x1", "y" }`, which usually
  act as row separators,
- `checkboxes` - small near-square rectangles as
  `{ "x0", "top", "x1", "bottom", "center_x", "center_y", "width", "height" }`,
- `row_boundaries` - the sorted list of the horizontal lines' `y` positions.

All of these coordinates are pdfplumber page coordinates - PDF points with
y = 0 at the top of the page.

The classification thresholds, for reference: a rule line must be at most 2.0 pt
thick and at least 15.0 pt long; a checkbox candidate must have a side between
4.0 and 28.0 pt with a width-to-height aspect ratio within a factor of 2.0.

The script prints a one-line summary, for example
`Wrote form_structure.json: 1 page(s), 5 label(s), 1 line(s), 1 checkbox(es).`

Now decide: if the structure has meaningful labels, use **Approach A**. If the
PDF is scanned or image-based and the labels are missing or garbage (for example
the text comes out as `(cid:N)` sequences), use **Approach B**.

### N2 (Approach A) - coordinates from the structure (preferred)

Study the extracted structure and identify the label groups (adjacent words that
form a single label), the rows (labels that share a similar `top`), the field
columns (the entry area starts just after a label ends), and the checkboxes (use
their detected rectangles as-is).

Be aware of the detector's limits: only square rectangles register as
checkboxes. Circular checkboxes, complex graphics, and faint or light elements
can be missed - handle those with the Hybrid approach below.

Deriving each field's entry box:

- Text field: `x0 = label.x1 + ~5` (a small gap after the label); `x1` is the
  next label's `x0` or a row boundary; `top = label.top`; `bottom` is the row
  boundary line just below, or `label.bottom + row_height`.
- Checkbox: use the detected checkbox rectangle directly as the entry box
  `[x0, top, x1, bottom]`.

Then author `fields.json` in PDF-point mode - a page whose size is given as
`pdf_width` and `pdf_height` tells the downstream scripts to read that page's
coordinates as PDF points.

### N3 (Approach B) - visual estimation (fallback)

1. Render the pages:

   ```bash
   python scripts/convert_pdf_to_images.py form.pdf images/
   ```

2. Examine each `images/page_N.png` for the rough position of every label, entry
   line or box, and checkbox.

3. Zoom in with ImageMagick to read precise pixels:

   ```bash
   magick page_1.png -crop 400x120+90+300 +repage crop.png
   ```

   (If `magick` is not installed, `convert` takes the same arguments.) Set the
   crop origin `+<x>+<y>` to your rough estimate minus a little padding, and the
   `<W>x<H>` size to the field area plus about 50 px of padding on each side.
   Read where the entry area begins and ends and its top and bottom inside the
   crop, then map back to full-image coordinates with
   `full_x = crop_x + crop_offset_x` and `full_y = crop_y + crop_offset_y`.

4. Author `fields.json` in image mode - a page whose size is given as
   `image_width` and `image_height` tells the downstream scripts to read that
   page's coordinates as pixels.

### The `fields.json` schema

This one file is consumed by `check_bounding_boxes.py`,
`create_validation_image.py`, and `fill_pdf_form_with_annotations.py`. It is a
top-level object:

- `pages` - a list of `{ "page_number", ... }` objects. Each page carries either
  a `pdf_width` and `pdf_height` pair or an `image_width` and `image_height`
  pair, and that choice decides the coordinate system used for the page.
- `form_fields` - a list of field objects, each with:
  - `page_number` (1-based),
  - `description` and `field_label` (both free text),
  - `label_bounding_box` as `[x0, top, x1, bottom]` (top-origin, in the page's
    chosen system),
  - `entry_bounding_box` as `[x0, top, x1, bottom]` (where the text is drawn),
  - `entry_text` as `{ "text": "<string>", "font_size": <number> }` (the
    `font_size` is optional).

Two rules about coordinate systems: if a page somehow declares both an `image_*`
pair and a `pdf_*` pair, the **image** pair wins (this is true in both
`create_validation_image.py` and `fill_pdf_form_with_annotations.py`). And if the
`pages` list is missing, or a field's page has no entry there, its coordinates
are taken to be PDF points already and used 1:1.

An Approach A file (PDF-point mode, US Letter is 612 x 792) with a text field and
a checkbox-style field:

```json
{
  "pages": [
    { "page_number": 1, "pdf_width": 612, "pdf_height": 792 }
  ],
  "form_fields": [
    {
      "page_number": 1,
      "description": "Applicant full name",
      "field_label": "Full name:",
      "label_bounding_box": [72, 83, 124, 95],
      "entry_bounding_box": [130, 83, 395, 95],
      "entry_text": { "text": "Amara Okafor", "font_size": 10 }
    },
    {
      "page_number": 1,
      "description": "Agreement checkbox",
      "field_label": "Agree to terms:",
      "label_bounding_box": [72, 123, 165, 135],
      "entry_bounding_box": [180, 124, 194, 138],
      "entry_text": { "text": "X", "font_size": 11 }
    }
  ]
}
```

An Approach B file (image mode) with a single text field placed by refined pixel
coordinates:

```json
{
  "pages": [
    { "page_number": 1, "image_width": 1000, "image_height": 1294 }
  ],
  "form_fields": [
    {
      "page_number": 1,
      "description": "Applicant full name",
      "field_label": "Full name:",
      "label_bounding_box": [118, 136, 203, 155],
      "entry_bounding_box": [214, 136, 646, 155],
      "entry_text": { "text": "Amara Okafor", "font_size": 16 }
    }
  ]
}
```

### Hybrid - structure plus visual

Use Approach A for everything the detector found, then render the pages and use
the step-N3 zoom technique to place the elements it missed (circular checkboxes,
faded lines, and the like). When you mix the two, convert the visually estimated
pixel coordinates into PDF points and emit a single coordinate system for the
whole file - PDF points, with `pdf_width` and `pdf_height`:

- `pdf_x = image_x * (pdf_width / image_width)`
- `pdf_y = image_y * (pdf_height / image_height)`

### N4 (optional) - sanity-check the boxes visually

```bash
python scripts/create_validation_image.py 1 fields.json pages/page_1.png check_1.png
```

For the given 1-based page number, this draws each field's `entry_bounding_box`
in red and its `label_bounding_box` in blue (2 px lines) onto a copy of the
rendered page, so a misplaced box is obvious before you commit to filling. It
scales the `fields.json` coordinates to the actual image using that page's
`image_*` or `pdf_*` pair, and prints `Drew N box(es) for page P; wrote check_1.png`.

### N5 - validate the bounding boxes (always, before filling)

```bash
python scripts/check_bounding_boxes.py fields.json
```

Per page, this flags two problems: (1) boxes that intersect where at least one
of them is an entry box - two pre-printed label boxes overlapping each other is
ignored, since those labels are not ours to move; and (2) any entry box shorter
than its own `entry_text.font_size`, where the text would not fit.

On success it prints `SUCCESS: all bounding boxes are valid.` and exits 0. On
failure it prints one `FAILURE: ...` line per problem (capped at about 20, then
`... and N more`) and exits 1. Fix `fields.json` and rerun until it passes.

### N6 - fill by overlay

```bash
python scripts/fill_pdf_form_with_annotations.py form.pdf fields.json filled.pdf
```

The script auto-detects each page's coordinate system from its `pages` entry and
converts accordingly. It builds a reportlab overlay `canvas.Canvas` (which is
bottom-origin) for each page and merges it onto the original page with pypdf's
`page.merge_page(...)`. The default font is Helvetica and the default size is 10
when `entry_text.font_size` is absent; the text baseline is placed about 2 pt
above the bottom edge of the entry box. Fields with no `entry_bounding_box` or no
`entry_text.text` are skipped.

It prints `Overlaid N text field(s); wrote filled.pdf`. The result has no
AcroForm annotations at all - the text is painted directly into the page
content.

### N7 - verify the output

Render the filled file back to images and confirm the placement:

```bash
python scripts/convert_pdf_to_images.py filled.pdf verify/
```

If any text landed in the wrong spot: for Approach A, recheck the PDF-point
coordinates and the `pdf_width` / `pdf_height` values; for Approach B, confirm
the declared image dimensions match the render and that the pixels are accurate;
for Hybrid, recheck the image-to-PDF conversions.
