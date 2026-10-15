#!/usr/bin/env python3
"""Extract structured information about a PDF's fillable AcroForm fields.

Usage:
    python extract_form_field_info.py <input.pdf> [field_info.json]

Prints (and optionally writes) a JSON list. Each element describes one field:

    {"field_id": <fully-qualified name>,
     "page": <1-based page number>,
     "rect": [left, bottom, right, top],   # PDF points, y=0 at page bottom
     "type": "text" | "checkbox" | "radio_group" | "choice"}

Type-specific keys:
    checkbox     -> "checked_value", "unchecked_value"
    radio_group  -> "radio_options": [{"value", "rect"}, ...]
    choice       -> "choice_options": [{"value", "text"}, ...]

Built on pypdf: the AcroForm is discovered by walking each page's /Annots
widget annotations up to their terminal field object (the nearest node carrying
a /T name), grouping widgets that share one field (e.g. radio buttons).
"""
import json
import sys

from pypdf import PdfReader

# PDF button field flags (/Ff), 1-based bit positions from the PDF spec.
_FLAG_RADIO = 1 << 15       # bit 16
_FLAG_PUSHBUTTON = 1 << 16  # bit 17


def _obj(x):
    """Resolve an indirect object to its concrete value."""
    if x is not None and hasattr(x, "get_object"):
        return x.get_object()
    return x


def _terminal_field(widget):
    """Nearest node (widget or ancestor) that carries a /T field name."""
    cur = _obj(widget)
    seen = set()
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if "/T" in cur:
            return cur
        cur = _obj(cur.get("/Parent"))
    return None


def _inherited(field, key):
    """Look up an attribute on the field or any ancestor (PDF inheritance)."""
    cur = _obj(field)
    seen = set()
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if key in cur:
            return cur[key]
        cur = _obj(cur.get("/Parent"))
    return None


def _full_name(field):
    """Build the fully-qualified field name by joining /T up the parent chain."""
    parts = []
    cur = _obj(field)
    seen = set()
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        t = cur.get("/T")
        if t is not None:
            parts.insert(0, str(t))
        cur = _obj(cur.get("/Parent"))
    return ".".join(parts)


def _rect(widget):
    """Return the widget's /Rect as [left, bottom, right, top] floats."""
    rect = _obj(_obj(widget).get("/Rect"))
    if not rect:
        return None
    return [float(_obj(v)) for v in rect]


def _on_state(widget):
    """Return the appearance-state name that turns a button widget 'on'."""
    ap = _obj(_obj(widget).get("/AP"))
    if not ap:
        return None
    normal = _obj(ap.get("/N"))
    if not normal or not hasattr(normal, "keys"):
        return None
    for key in normal.keys():
        if str(key) != "/Off":
            return str(key)
    return None


def _choice_options(field):
    """Return the /Opt list of a choice field as [{'value', 'text'}, ...]."""
    opt = _obj(_inherited(field, "/Opt"))
    options = []
    if not opt:
        return options
    for entry in opt:
        entry = _obj(entry)
        if isinstance(entry, str):
            options.append({"value": str(entry), "text": str(entry)})
        elif hasattr(entry, "__getitem__") and len(entry) >= 2:
            export = str(_obj(entry[0]))
            display = str(_obj(entry[1]))
            options.append({"value": export, "text": display})
        else:
            options.append({"value": str(entry), "text": str(entry)})
    return options


def get_field_info(reader):
    """Return a list of field-info dicts for every fillable field in ``reader``.

    Imported by fill_fillable_fields.py to validate requested values.
    """
    groups = {}
    order = []
    for page_num, page in enumerate(reader.pages, start=1):
        annots = _obj(page.get("/Annots"))
        if not annots:
            continue
        for annot in annots:
            widget = _obj(annot)
            if widget is None or widget.get("/Subtype") != "/Widget":
                continue
            field = _terminal_field(widget)
            if field is None:
                continue
            ft = _inherited(field, "/FT")
            if ft is None:
                continue
            key = id(field)
            if key not in groups:
                groups[key] = {
                    "field": field,
                    "ft": str(ft),
                    "page": page_num,
                    "widgets": [],
                }
                order.append(key)
            groups[key]["widgets"].append(widget)

    results = []
    for key in order:
        group = groups[key]
        ft = group["ft"]
        widgets = group["widgets"]
        info = {"field_id": _full_name(group["field"]), "page": group["page"]}

        if ft == "/Tx":
            info["rect"] = _rect(widgets[0])
            info["type"] = "text"
        elif ft == "/Btn":
            ff = _inherited(group["field"], "/Ff")
            ff = int(ff) if ff is not None else 0
            if ff & _FLAG_PUSHBUTTON:
                continue  # push buttons hold no data; skip them
            if ff & _FLAG_RADIO:
                info["type"] = "radio_group"
                options = []
                for widget in widgets:
                    on = _on_state(widget)
                    if on is not None:
                        options.append({"value": on, "rect": _rect(widget)})
                info["radio_options"] = options
            else:
                info["rect"] = _rect(widgets[0])
                info["type"] = "checkbox"
                info["checked_value"] = _on_state(widgets[0]) or "/Yes"
                info["unchecked_value"] = "/Off"
        elif ft == "/Ch":
            info["rect"] = _rect(widgets[0])
            info["type"] = "choice"
            info["choice_options"] = _choice_options(group["field"])
        else:
            continue  # e.g. /Sig signature fields are not fillable text

        results.append(info)
    return results


def main(argv):
    if len(argv) not in (2, 3):
        print("Usage: python extract_form_field_info.py <input.pdf> "
              "[field_info.json]", file=sys.stderr)
        return 2
    reader = PdfReader(argv[1])
    fields = get_field_info(reader)
    text = json.dumps(fields, indent=2)
    if len(argv) == 3:
        with open(argv[2], "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"Wrote {len(fields)} field(s) to {argv[2]}", file=sys.stderr)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
