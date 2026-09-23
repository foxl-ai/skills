#!/usr/bin/env python3
"""Extract the visual structure of a NON-fillable PDF form with pdfplumber.

Usage:
    python extract_form_structure.py <input.pdf> <output.json>

Writes a JSON document describing, per page:
  * labels        - every text word with coordinates (x0, top, x1, bottom)
  * lines         - horizontal rule lines (row separators)
  * checkboxes    - small near-square rectangles (candidate check boxes),
                    each with its center
  * row_boundaries- sorted 'top' positions of the horizontal lines

All coordinates are pdfplumber page coordinates: PDF points with y=0 at the
TOP of the page, increasing downward. These feed the fields.json coordinates
used by fill_pdf_form_with_annotations.py (pdf_width / pdf_height mode).
"""
import json
import sys

import pdfplumber

# Thresholds (PDF points) for classifying primitives.
_LINE_MAX_THICKNESS = 2.0    # a rule line is nearly zero height
_LINE_MIN_LENGTH = 15.0      # ignore tiny stray segments
_BOX_MIN = 4.0               # checkbox side length lower bound
_BOX_MAX = 28.0              # checkbox side length upper bound
_BOX_ASPECT = 2.0            # width/height (and inverse) must stay under this


def _round(value, ndigits=2):
    return round(float(value), ndigits)


def _labels(page):
    labels = []
    for word in page.extract_words(use_text_flow=False):
        labels.append({
            "text": word["text"],
            "x0": _round(word["x0"]),
            "top": _round(word["top"]),
            "x1": _round(word["x1"]),
            "bottom": _round(word["bottom"]),
        })
    return labels


def _horizontal_lines(page):
    lines = []
    tops = []
    # Explicit line primitives plus rects thin enough to read as rules.
    candidates = list(page.lines)
    for rect in page.rects:
        if abs(rect["bottom"] - rect["top"]) <= _LINE_MAX_THICKNESS:
            candidates.append(rect)
    for seg in candidates:
        width = abs(seg["x1"] - seg["x0"])
        thickness = abs(seg["bottom"] - seg["top"])
        if thickness <= _LINE_MAX_THICKNESS and width >= _LINE_MIN_LENGTH:
            y = _round((seg["top"] + seg["bottom"]) / 2.0)
            lines.append({
                "x0": _round(min(seg["x0"], seg["x1"])),
                "x1": _round(max(seg["x0"], seg["x1"])),
                "y": y,
            })
            tops.append(y)
    lines.sort(key=lambda l: (l["y"], l["x0"]))
    row_boundaries = sorted({t for t in tops})
    return lines, row_boundaries


def _checkboxes(page):
    boxes = []
    for rect in page.rects:
        width = abs(rect["x1"] - rect["x0"])
        height = abs(rect["bottom"] - rect["top"])
        if not (_BOX_MIN <= width <= _BOX_MAX and _BOX_MIN <= height <= _BOX_MAX):
            continue
        if height == 0:
            continue
        aspect = width / height
        if aspect > _BOX_ASPECT or aspect < 1.0 / _BOX_ASPECT:
            continue
        x0, x1 = min(rect["x0"], rect["x1"]), max(rect["x0"], rect["x1"])
        top, bottom = min(rect["top"], rect["bottom"]), max(rect["top"], rect["bottom"])
        boxes.append({
            "x0": _round(x0),
            "top": _round(top),
            "x1": _round(x1),
            "bottom": _round(bottom),
            "center_x": _round((x0 + x1) / 2.0),
            "center_y": _round((top + bottom) / 2.0),
            "width": _round(width),
            "height": _round(height),
        })
    return boxes


def extract_structure(pdf_path):
    pages_out = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            lines, row_boundaries = _horizontal_lines(page)
            pages_out.append({
                "page_number": page_num,
                "width": _round(page.width),
                "height": _round(page.height),
                "labels": _labels(page),
                "lines": lines,
                "checkboxes": _checkboxes(page),
                "row_boundaries": row_boundaries,
            })
    return {"pages": pages_out}


def main(argv):
    if len(argv) != 3:
        print("Usage: python extract_form_structure.py <input.pdf> <output.json>",
              file=sys.stderr)
        return 2
    structure = extract_structure(argv[1])
    with open(argv[2], "w", encoding="utf-8") as handle:
        json.dump(structure, handle, indent=2)
    total_labels = sum(len(p["labels"]) for p in structure["pages"])
    total_lines = sum(len(p["lines"]) for p in structure["pages"])
    total_boxes = sum(len(p["checkboxes"]) for p in structure["pages"])
    print(f"Wrote {argv[2]}: {len(structure['pages'])} page(s), "
          f"{total_labels} label(s), {total_lines} line(s), "
          f"{total_boxes} checkbox(es).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
