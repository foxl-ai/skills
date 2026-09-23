"""Repack an unpacked directory into a DOCX/PPTX/XLSX file.

Before zipping it applies two safe repairs that Word rejects a file for, then
writes a plain (deflated) ZIP - which is exactly what an OOXML container is:

  - clamp w14/w15/w16 hex ids (paraId, textId, durableId) to the 0x7FFFFFFF the
    format allows, regenerating any that overflow,
  - set xml:space="preserve" on every <w:t> whose text has leading or trailing
    whitespace, so Word keeps the spaces.

Usage:
    python office/pack.py <input_dir> <output_file> [--no-repair]
"""
import argparse
import random
import sys
import zipfile
from pathlib import Path

from lxml import etree

OOXML_SUFFIXES = {".docx", ".pptx", ".xlsx"}
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
ID_LOCALNAMES = {"paraId", "textId", "durableId"}
MAX_ID = 0x7FFFFFFF


def _new_id() -> str:
    return f"{random.randint(1, MAX_ID):08X}"


def _repair_part(part: Path) -> int:
    try:
        tree = etree.parse(str(part))
    except etree.XMLSyntaxError:
        return 0
    root = tree.getroot()
    fixed = 0
    for el in root.iter():
        for name, value in list(el.attrib.items()):
            if etree.QName(name).localname in ID_LOCALNAMES:
                try:
                    if int(value, 16) > MAX_ID:
                        el.set(name, _new_id())
                        fixed += 1
                except ValueError:
                    el.set(name, _new_id())
                    fixed += 1
        if etree.QName(el).localname == "t" and el.tag.startswith(f"{{{W}}}"):
            text = el.text or ""
            if text[:1].isspace() or text[-1:].isspace():
                if el.get(XML_SPACE) != "preserve":
                    el.set(XML_SPACE, "preserve")
                    fixed += 1
    if fixed:
        tree.write(str(part), xml_declaration=True, encoding="UTF-8", standalone=True)
    return fixed


def pack(input_dir: str, output_file: str, repair: bool = True) -> str:
    src = Path(input_dir)
    out = Path(output_file)
    if not src.is_dir():
        return f"Error: {input_dir} is not a directory"
    if out.suffix.lower() not in OOXML_SUFFIXES:
        return f"Error: {output_file} must be a .docx, .pptx or .xlsx file"

    repaired = 0
    if repair:
        for part in list(src.rglob("*.xml")) + list(src.rglob("*.rels")):
            repaired += _repair_part(part)

    out.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in src.rglob("*") if p.is_file())
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f.relative_to(src).as_posix())

    note = f" (repaired {repaired} id/space issue(s))" if repaired else ""
    return f"Packed {input_dir} into {output_file}{note}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Pack a directory into an Office file")
    ap.add_argument("input_directory")
    ap.add_argument("output_file")
    ap.add_argument("--no-repair", action="store_true", help="skip the id/whitespace repairs")
    args = ap.parse_args()
    msg = pack(args.input_directory, args.output_file, repair=not args.no_repair)
    print(msg)
    sys.exit(1 if msg.startswith("Error") else 0)
