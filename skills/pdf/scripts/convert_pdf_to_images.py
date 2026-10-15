#!/usr/bin/env python3
"""Rasterize every page of a PDF to a PNG, capped at 1000px on the long side.

Usage:
    python convert_pdf_to_images.py <input.pdf> <output_dir>

Writes <output_dir>/page_1.png, page_2.png, ... (1-based). Rendering uses
pypdfium2 (PDFium; no poppler needed). Each page is rendered at a comfortable
resolution and then downscaled with Pillow (LANCZOS) so its largest dimension
is <= 1000px; pages already smaller are left as-is (never upscaled).
"""
import os
import sys

import pypdfium2 as pdfium
from PIL import Image

_RENDER_SCALE = 2.0   # ~144 DPI base render before any downscale
_MAX_DIM = 1000       # cap on the longer image dimension, in pixels


def convert(pdf_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    written = []
    pdf = pdfium.PdfDocument(pdf_path)
    try:
        for index in range(len(pdf)):
            page = pdf[index]
            bitmap = page.render(scale=_RENDER_SCALE)
            image = bitmap.to_pil().convert("RGB")
            longest = max(image.width, image.height)
            if longest > _MAX_DIM:
                ratio = _MAX_DIM / float(longest)
                new_size = (max(1, round(image.width * ratio)),
                            max(1, round(image.height * ratio)))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            out_path = os.path.join(output_dir, f"page_{index + 1}.png")
            image.save(out_path, "PNG")
            written.append((out_path, image.width, image.height))
    finally:
        pdf.close()
    return written


def main(argv):
    if len(argv) != 3:
        print("Usage: python convert_pdf_to_images.py <input.pdf> <output_dir>",
              file=sys.stderr)
        return 2
    written = convert(argv[1], argv[2])
    for path, width, height in written:
        print(f"{path}  {width}x{height}")
    print(f"Wrote {len(written)} image(s) to {argv[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
