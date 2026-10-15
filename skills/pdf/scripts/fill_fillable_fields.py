#!/usr/bin/env python3
"""Fill a PDF's AcroForm fields from a JSON list of values.

Usage:
    python fill_fillable_fields.py <input.pdf> <field_values.json> <output.pdf>

field_values.json is a list of objects:
    [{"field_id": "last_name", "page": 1, "value": "Simpson",
      "description": "..."}, ...]

Each requested value is validated against the field discovered by
extract_form_field_info.get_field_info:
  * unknown field_id            -> error
  * page mismatch               -> error
  * checkbox value must equal the field's checked_value or unchecked_value
  * radio_group value must be one of the radio option values
  * choice value must be a valid option value (or its display text)
Any error prints a message and exits 1 without writing output.

Valid requests are applied with pypdf's update_page_form_field_values
(auto_regenerate=False) and NeedAppearances is set so viewers regenerate the
field appearances.
"""
import json
import sys

from pypdf import PdfReader, PdfWriter

from extract_form_field_info import get_field_info


def _load_values(path):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("field_values.json must be a JSON list of field objects")
    return data


def _validate(requests, info_by_id):
    """Return a list of human-readable error strings (empty when all valid)."""
    errors = []
    for i, req in enumerate(requests):
        if not isinstance(req, dict):
            errors.append(f"entry {i}: not an object")
            continue
        fid = req.get("field_id")
        if fid is None:
            errors.append(f"entry {i}: missing 'field_id'")
            continue
        if "value" not in req:
            errors.append(f"{fid}: missing 'value'")
            continue
        info = info_by_id.get(fid)
        if info is None:
            errors.append(f"{fid}: unknown field_id (not present in the PDF)")
            continue
        if "page" in req and req["page"] != info["page"]:
            errors.append(
                f"{fid}: page {req['page']} does not match field page "
                f"{info['page']}")
            continue

        value = req["value"]
        ftype = info["type"]
        if ftype == "checkbox":
            allowed = {info["checked_value"], info["unchecked_value"]}
            if str(value) not in {str(a) for a in allowed}:
                errors.append(
                    f"{fid}: checkbox value {value!r} must be one of "
                    f"{sorted(allowed)}")
        elif ftype == "radio_group":
            allowed = {str(o["value"]) for o in info.get("radio_options", [])}
            if str(value) not in allowed:
                errors.append(
                    f"{fid}: radio value {value!r} must be one of "
                    f"{sorted(allowed)}")
        elif ftype == "choice":
            values = {str(o["value"]) for o in info.get("choice_options", [])}
            texts = {str(o["text"]) for o in info.get("choice_options", [])}
            if str(value) not in values | texts:
                errors.append(
                    f"{fid}: choice value {value!r} must be one of "
                    f"{sorted(values)}")
        # text: any string is acceptable
    return errors


def main(argv):
    if len(argv) != 4:
        print("Usage: python fill_fillable_fields.py <input.pdf> "
              "<field_values.json> <output.pdf>", file=sys.stderr)
        return 2
    in_pdf, values_path, out_pdf = argv[1], argv[2], argv[3]

    reader = PdfReader(in_pdf)
    info = get_field_info(reader)
    info_by_id = {f["field_id"]: f for f in info}

    requests = _load_values(values_path)
    errors = _validate(requests, info_by_id)
    if errors:
        print("Validation failed; no output written:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    # Group the requested values by the page their field lives on.
    by_page = {}
    for req in requests:
        info_f = info_by_id[req["field_id"]]
        by_page.setdefault(info_f["page"], {})[req["field_id"]] = req["value"]

    writer = PdfWriter(clone_from=reader)
    writer.set_need_appearances_writer(True)
    for page_num, mapping in by_page.items():
        writer.update_page_form_field_values(
            writer.pages[page_num - 1], mapping, auto_regenerate=False)

    with open(out_pdf, "wb") as handle:
        writer.write(handle)

    filled = sum(len(m) for m in by_page.values())
    print(f"Filled {filled} field(s); wrote {out_pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
