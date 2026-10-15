"""Validate an unpacked directory or a packed Office file.

Two layers, both dependency-light:

  1. XML well-formedness of every part (via lxml). This catches the mistakes that
     hand-editing introduces - unbalanced tags, stray entities, bad namespaces.
  2. Structural validation, delegated to `officecli validate` when that binary is
     on PATH. officecli checks the file against the OpenXML schema without needing
     Word or LibreOffice; when it is absent, layer 1 still runs and the command
     reports that the structural check was skipped.

Exit status is 0 only when every layer that ran passed. A schema failure from
officecli fails the command (exit 1), so a broken repack cannot slip through green.

Usage:
    python office/validate.py <path> [-v]
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

OOXML_SUFFIXES = {".docx", ".pptx", ".xlsx"}


def _wellformed(directory: Path, verbose: bool) -> list[str]:
    errors = []
    for part in list(directory.rglob("*.xml")) + list(directory.rglob("*.rels")):
        try:
            etree.parse(str(part))
            if verbose:
                print(f"ok    {part.relative_to(directory)}")
        except etree.XMLSyntaxError as exc:
            errors.append(f"{part.relative_to(directory)}: {exc}")
    return errors


def _officecli_validate(packed: Path) -> tuple[bool | None, str]:
    if shutil.which("officecli") is None:
        return None, "skipped (officecli not on PATH)"
    proc = subprocess.run(["officecli", "validate", str(packed)],
                          capture_output=True, text=True, timeout=120, check=False)
    detail = (proc.stdout + proc.stderr).strip()
    return (proc.returncode == 0), (detail or ("passed" if proc.returncode == 0 else "failed"))


def validate(path: str, verbose: bool = False) -> tuple[bool, str]:
    target = Path(path)
    if not target.exists():
        return False, f"Error: {path} does not exist"

    packed_for_officecli: Path | None = None
    tmp: tempfile.TemporaryDirectory | None = None

    if target.is_dir():
        directory = target
    elif target.suffix.lower() in OOXML_SUFFIXES:
        packed_for_officecli = target
        tmp = tempfile.TemporaryDirectory()
        directory = Path(tmp.name)
        with zipfile.ZipFile(target) as zf:
            zf.extractall(directory)
    else:
        return False, f"Error: {path} must be a directory or a .docx/.pptx/.xlsx file"

    lines = []
    errors = _wellformed(directory, verbose)
    if errors:
        lines.append("XML NOT well-formed:")
        lines.extend(f"  - {e}" for e in errors)
    else:
        lines.append("XML well-formed: all parts parse")

    schema_ok: bool | None = None
    if packed_for_officecli is not None:
        schema_ok, detail = _officecli_validate(packed_for_officecli)
        lines.append(f"officecli validate: {detail}")
    else:
        lines.append("officecli validate: skipped (pack first to run the schema check)")

    if tmp is not None:
        tmp.cleanup()
    ok = (not errors) and (schema_ok is not False)
    return ok, "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Validate an Office document")
    ap.add_argument("path", help="unpacked directory or packed .docx/.pptx/.xlsx")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    ok, report = validate(args.path, verbose=args.verbose)
    print(report)
    sys.exit(0 if ok else 1)
