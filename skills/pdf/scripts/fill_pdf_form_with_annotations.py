#!/usr/bin/env python3
"""Overlay text onto a NON-fillable PDF at given bounding boxes.

Usage:
    python fill_pdf_form_with_annotations.py <input.pdf> <fields.json> <output.pdf>

fields.json (see forms.md) has:
    {"pages": [{"page_number": 1, "pdf_width": 612, "pdf_height": 792}],
     "form_fields": [
        {"page_number": 1,
         "entry_bounding_box": [x0, top, x1, bottom],
         "entry_text": {"text": "Smith", "font_size": 10}},
        ...]}

Coordinate system per page auto-detected from its "pages" entry:
  * pdf_width / pdf_height     -> coordinates are PDF points (top-origin)
  * image_width / image_height -> coordinates are pixels; scaled to the real
                                  PDF page size read from the input PDF
A reportlab overlay canvas (bottom-origin) is drawn for each page and merged
onto the original page with pypdf. Text is baseline-placed just inside the
bottom edge of each entry box.
"""
import io
import json
import sys

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

_DEFAULT_FONT = "Helvetica"
_DEFAULT_FONT_SIZE = 10.0
_BASELINE_PAD = 2.0  # points above the box's bottom edge for the text baseline


def _page_meta(fields_doc):
    meta = {}
    for page in fields_doc.get("pages", []):
        num = page.get("page_number")
        if num is not None:
            meta[num] = page
    return meta


def _fields_by_page(fields_doc):
    by_page = {}
    for field in fields_doc.get("form_fields", []):
        by_page.setdefault(field.get("page_number"), []).append(field)
    return by_page


def _scale_to_pdf(page_meta, pdf_w, pdf_h):
    """Return (sx, sy) converting fields.json coords into PDF points."""
    if page_meta is not None:
        if page_meta.get("image_width") and page_meta.get("image_height"):
            return (pdf_w / float(page_meta["image_width"]),
                    pdf_h / float(page_meta["image_height"]))
        if page_meta.get("pdf_width") and page_meta.get("pdf_height"):
            # Coords already in points; correct only if declared size drifts.
            return (pdf_w / float(page_meta["pdf_width"]),
                    pdf_h / float(page_meta["pdf_height"]))
    return (1.0, 1.0)


def fill(in_pdf, fields_doc, out_pdf):
    reader = PdfReader(in_pdf)
    meta = _page_meta(fields_doc)
    by_page = _fields_by_page(fields_doc)

    packet = io.BytesIO()
    overlay = canvas.Canvas(packet)
    drawn = 0

    for index, page in enumerate(reader.pages):
        page_number = index + 1
        box = page.mediabox
        pdf_w = float(box.width)
        pdf_h = float(box.height)
        overlay.setPageSize((pdf_w, pdf_h))

        sx, sy = _scale_to_pdf(meta.get(page_number), pdf_w, pdf_h)
        for field in by_page.get(page_number, []):
            entry_box = field.get("entry_bounding_box")
            entry_text = field.get("entry_text") or {}
            text = entry_text.get("text")
            if not entry_box or text is None:
                continue
            font_size = float(entry_text.get("font_size") or _DEFAULT_FONT_SIZE)
            x0 = min(float(entry_box[0]), float(entry_box[2])) * sx
            bottom = max(float(entry_box[1]), float(entry_box[3])) * sy
            # Top-origin box bottom -> reportlab bottom-origin baseline.
            baseline_y = pdf_h - bottom + _BASELINE_PAD
            overlay.setFont(_DEFAULT_FONT, font_size)
            overlay.drawString(x0, baseline_y, str(text))
            drawn += 1
        overlay.showPage()

    overlay.save()
    packet.seek(0)

    overlay_reader = PdfReader(packet)
    writer = PdfWriter()
    for index, page in enumerate(reader.pages):
        if index < len(overlay_reader.pages):
            page.merge_page(overlay_reader.pages[index])
        writer.add_page(page)

    with open(out_pdf, "wb") as handle:
        writer.write(handle)
    return drawn


def main(argv):
    if len(argv) != 4:
        print("Usage: python fill_pdf_form_with_annotations.py <input.pdf> "
              "<fields.json> <output.pdf>", file=sys.stderr)
        return 2
    with open(argv[2], encoding="utf-8") as handle:
        fields_doc = json.load(handle)
    drawn = fill(argv[1], fields_doc, argv[3])
    print(f"Overlaid {drawn} text field(s); wrote {argv[3]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
