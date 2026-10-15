#!/usr/bin/env python3
"""Report whether a PDF contains fillable AcroForm fields.

Usage:
    python check_fillable_fields.py <file.pdf>

Uses pypdf's PdfReader.get_fields(), which returns the document's interactive
form fields (or None / empty when the PDF has no AcroForm). A truthy result
means the PDF can be filled directly (see the "Fillable fields" workflow); an
empty result means text must be overlaid onto the page (see "Non-fillable
fields").
"""
import sys

from pypdf import PdfReader


def has_fillable_fields(pdf_path):
    """Return (bool, field_count). True when the PDF exposes AcroForm fields."""
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    if not fields:
        return False, 0
    return True, len(fields)


def main(argv):
    if len(argv) != 2:
        print("Usage: python check_fillable_fields.py <file.pdf>", file=sys.stderr)
        return 2
    pdf_path = argv[1]
    try:
        fillable, count = has_fillable_fields(pdf_path)
    except Exception as exc:  # noqa: BLE001 - surface any read error clearly
        print(f"ERROR: could not read '{pdf_path}': {exc}", file=sys.stderr)
        return 2

    if fillable:
        print(f"FILLABLE: '{pdf_path}' has {count} AcroForm form field(s).")
        print("Next: use extract_form_field_info.py and fill_fillable_fields.py.")
    else:
        print(f"NOT FILLABLE: '{pdf_path}' has no AcroForm form fields.")
        print("Next: use extract_form_structure.py and "
              "fill_pdf_form_with_annotations.py to overlay text.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
