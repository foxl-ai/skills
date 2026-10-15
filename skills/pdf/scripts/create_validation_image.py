#!/usr/bin/env python3
"""Draw a page's label/entry bounding boxes onto its rendered image.

Usage:
    python create_validation_image.py <page_number> <fields.json> \
        <in_image.png> <out_image.png>

For the given (1-based) page it overlays each field's:
  * entry_bounding_box  in RED
  * label_bounding_box  in BLUE

Coordinates in fields.json are interpreted from that page's "pages" entry:
  * pdf_width / pdf_height  -> PDF points (top-origin); scaled to the image by
                               (image_size / pdf_size)
  * image_width / image_height -> pixels of the declared render; scaled to the
                               actual input image (which may be downscaled)
Both systems are top-origin, matching Pillow's coordinate space, so no y-flip
is needed. Uses Pillow's ImageDraw.
"""
import json
import sys

from PIL import Image, ImageDraw

_ENTRY_COLOR = (220, 30, 30)   # red
_LABEL_COLOR = (30, 60, 220)   # blue
_WIDTH = 2


def _page_entry(fields_doc, page_number):
    for page in fields_doc.get("pages", []):
        if page.get("page_number") == page_number:
            return page
    return None


def _scale_factors(page_entry, img_w, img_h):
    """Return (sx, sy) mapping fields.json coords to actual image pixels."""
    if page_entry is not None:
        if page_entry.get("image_width") and page_entry.get("image_height"):
            return (img_w / float(page_entry["image_width"]),
                    img_h / float(page_entry["image_height"]))
        if page_entry.get("pdf_width") and page_entry.get("pdf_height"):
            return (img_w / float(page_entry["pdf_width"]),
                    img_h / float(page_entry["pdf_height"]))
    # No page metadata: assume coords already match the image.
    return (1.0, 1.0)


def _scaled_box(box, sx, sy):
    x0, top, x1, bottom = (float(v) for v in box)
    return [min(x0, x1) * sx, min(top, bottom) * sy,
            max(x0, x1) * sx, max(top, bottom) * sy]


def draw(page_number, fields_doc, in_image, out_image):
    image = Image.open(in_image).convert("RGB")
    draw_ctx = ImageDraw.Draw(image)
    page_entry = _page_entry(fields_doc, page_number)
    sx, sy = _scale_factors(page_entry, image.width, image.height)

    drawn = 0
    for field in fields_doc.get("form_fields", []):
        if field.get("page_number") != page_number:
            continue
        label_box = field.get("label_bounding_box")
        entry_box = field.get("entry_bounding_box")
        if label_box:
            draw_ctx.rectangle(_scaled_box(label_box, sx, sy),
                               outline=_LABEL_COLOR, width=_WIDTH)
            drawn += 1
        if entry_box:
            draw_ctx.rectangle(_scaled_box(entry_box, sx, sy),
                               outline=_ENTRY_COLOR, width=_WIDTH)
            drawn += 1

    image.save(out_image, "PNG")
    return drawn


def main(argv):
    if len(argv) != 5:
        print("Usage: python create_validation_image.py <page_number> "
              "<fields.json> <in_image.png> <out_image.png>", file=sys.stderr)
        return 2
    try:
        page_number = int(argv[1])
    except ValueError:
        print(f"ERROR: page_number must be an integer, got {argv[1]!r}",
              file=sys.stderr)
        return 2
    with open(argv[2], encoding="utf-8") as handle:
        fields_doc = json.load(handle)
    drawn = draw(page_number, fields_doc, argv[3], argv[4])
    print(f"Drew {drawn} box(es) for page {page_number}; wrote {argv[4]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
