"""Unpack a DOCX/PPTX/XLSX (a ZIP of XML parts) into a directory for editing.

Extracts the archive and pretty-prints every .xml/.rels part so the markup is
readable and diff-friendly. For DOCX it then tidies the body by default:

  - merge adjacent runs that share formatting (see helpers/merge_runs.py),
  - fuse adjacent tracked-change wrappers from one author (helpers/simplify_redlines.py).

Pretty-printing never rewrites the text inside <w:t> and other leaf elements, and
xml:space="preserve" content is left untouched, so the document's words survive a
round-trip through office/pack.py unchanged.

Usage:
    python office/unpack.py <office_file> <output_dir> [--no-merge-runs] [--no-simplify-redlines]
"""
import argparse
import sys
import zipfile
from pathlib import Path

from lxml import etree

from helpers.merge_runs import merge_runs
from helpers.simplify_redlines import simplify_redlines

OOXML_SUFFIXES = {".docx", ".pptx", ".xlsx"}


def _pretty(part: Path) -> None:
    try:
        parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)
        tree = etree.parse(str(part), parser)
        tree.write(str(part), pretty_print=True, xml_declaration=True,
                   encoding="UTF-8", standalone=True)
    except etree.XMLSyntaxError as exc:
        print(f"WARN: left {part.name} as-is ({exc})", file=sys.stderr)


def unpack(office_file: str, out_dir: str, merge: bool = True, simplify: bool = True) -> str:
    src = Path(office_file)
    out = Path(out_dir)
    if not src.exists():
        return f"Error: {office_file} does not exist"
    if src.suffix.lower() not in OOXML_SUFFIXES:
        return f"Error: {office_file} must be a .docx, .pptx or .xlsx file"

    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as zf:
        zf.extractall(out)

    parts = list(out.rglob("*.xml")) + list(out.rglob("*.rels"))
    for part in parts:
        _pretty(part)

    if src.suffix.lower() == ".docx":
        if merge:
            merge_runs(str(out))
        if simplify:
            simplify_redlines(str(out))

    return f"Unpacked {office_file} into {out_dir} ({len(parts)} XML parts)"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Unpack an Office file for editing")
    ap.add_argument("office_file")
    ap.add_argument("output_dir")
    ap.add_argument("--no-merge-runs", action="store_true", help="skip merging adjacent runs (DOCX)")
    ap.add_argument("--no-simplify-redlines", action="store_true", help="skip fusing tracked changes (DOCX)")
    args = ap.parse_args()
    msg = unpack(args.office_file, args.output_dir,
                 merge=not args.no_merge_runs, simplify=not args.no_simplify_redlines)
    print(msg)
    sys.exit(1 if msg.startswith("Error") else 0)
