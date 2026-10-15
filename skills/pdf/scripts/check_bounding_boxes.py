#!/usr/bin/env python3
"""Validate a non-fillable-form fields.json before overlaying text.

Usage:
    python check_bounding_boxes.py <fields.json>

fields.json has "form_fields", each with "label_bounding_box",
"entry_bounding_box" ([x0, top, x1, bottom]), "page_number", "description",
and optional "entry_text.font_size".

Reports FAILURE for:
  * any two boxes on the same page that intersect, where at least one is an
    entry box (overlapping entry text would collide with a label or another
    entry)
  * any entry box whose height is smaller than its font size (text will not fit)

Prints SUCCESS when everything is valid. Output is capped at ~20 messages.
"""
import json
import sys

_MAX_MESSAGES = 20


def _height(box):
    """Box is [x0, top, x1, bottom] in top-origin coords: height = bottom-top."""
    return abs(float(box[3]) - float(box[1]))


def _intersects(a, b):
    """True if rectangles a and b overlap (edge-touching does not count)."""
    ax0, atop, ax1, abot = (float(v) for v in a)
    bx0, btop, bx1, bbot = (float(v) for v in b)
    ax0, ax1 = min(ax0, ax1), max(ax0, ax1)
    atop, abot = min(atop, abot), max(atop, abot)
    bx0, bx1 = min(bx0, bx1), max(bx0, bx1)
    btop, bbot = min(btop, bbot), max(btop, bbot)
    return ax0 < bx1 and bx0 < ax1 and atop < bbot and btop < abot


def _label(field, index):
    desc = field.get("description") or field.get("field_label")
    return f"field {index}" + (f" ({desc})" if desc else "")


def check(fields_doc):
    """Return a list of failure messages (empty means valid)."""
    failures = []
    fields = fields_doc.get("form_fields", [])

    # Group boxes by page. Each box: (kind, field_index, description, coords).
    by_page = {}
    for idx, field in enumerate(fields):
        page = field.get("page_number")
        entry = by_page.setdefault(page, [])
        if field.get("label_bounding_box"):
            entry.append(("label", idx, _label(field, idx),
                          field["label_bounding_box"]))
        if field.get("entry_bounding_box"):
            entry.append(("entry", idx, _label(field, idx),
                          field["entry_bounding_box"]))

    # Intersection check: any pair on the same page where >=1 box is an entry.
    for page, boxes in by_page.items():
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                kind_i, _fi, name_i, box_i = boxes[i]
                kind_j, _fj, name_j, box_j = boxes[j]
                if kind_i == "label" and kind_j == "label":
                    continue  # pre-printed labels are not ours to move
                if _intersects(box_i, box_j):
                    failures.append(
                        f"FAILURE: page {page}: {kind_i} box of {name_i} "
                        f"intersects {kind_j} box of {name_j}")

    # Font-fit check: entry box must be at least as tall as its font size.
    for idx, field in enumerate(fields):
        box = field.get("entry_bounding_box")
        entry_text = field.get("entry_text") or {}
        font_size = entry_text.get("font_size")
        if box and font_size:
            h = _height(box)
            if h < float(font_size):
                failures.append(
                    f"FAILURE: page {field.get('page_number')}: entry box of "
                    f"{_label(field, idx)} height {h:.1f} is smaller than "
                    f"font size {font_size}")
    return failures


def main(argv):
    if len(argv) != 2:
        print("Usage: python check_bounding_boxes.py <fields.json>",
              file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        fields_doc = json.load(handle)

    failures = check(fields_doc)
    if not failures:
        print("SUCCESS: all bounding boxes are valid.")
        return 0

    total = len(failures)
    for message in failures[:_MAX_MESSAGES]:
        print(message)
    if total > _MAX_MESSAGES:
        print(f"... and {total - _MAX_MESSAGES} more issue(s) "
              f"({total} total).")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
