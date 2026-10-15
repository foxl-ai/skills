"""recalc.py - recalculate an .xlsx and report any resulting Excel errors.

Recalculation is delegated to a headless engine, preferring officecli (which
needs neither Excel nor LibreOffice), then falling back to LibreOffice only when
officecli is not on PATH:

  1. officecli (preferred). `officecli view <file> issues --json` runs officecli's
     own formula evaluator across the workbook and returns structured issues. The
     formula_* subtypes are the recalculation result: formula_eval_error and
     formula_ref_missing_sheet are genuine Excel errors (e.g. #DIV/0!, #REF!),
     reported with their cell coordinates. This path works even on a freshly
     authored workbook that carries no cached formula values.

  2. LibreOffice (fallback, only if officecli is absent AND `soffice` is on PATH).
     `soffice --headless --convert-to xlsx` re-saves the workbook, which recomputes
     the formulas and persists fresh cached values, storing error results as OOXML
     t="e" cells. The recalculated copy is then handed to the openpyxl scan below.
     When neither engine is available a clear "LibreOffice not found" message is
     printed and the command still runs the openpyxl scan over the file as-is,
     rather than crashing.

After recalculation, an independent openpyxl pass opens the workbook with
data_only=True and scans every sheet's cells for the seven Excel error strings,
reporting the coordinate of each. openpyxl reads a t="e" error cell back as its
error string (e.g. "#DIV/0!"), so this pass catches errors that a real recalc
engine (LibreOffice, or a workbook last saved by Excel) has persisted as cached
values, as well as error text stored literally in a cell.

The command exits non-zero when any Excel error cell is found by either mechanism.

Usage:
    python recalc.py <file.xlsx> [timeout_seconds]
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import openpyxl

# The seven Excel error strings, exactly as Excel/openpyxl render them. Every one
# begins with "#", which makes a substring test unambiguous against ordinary text.
EXCEL_ERRORS = ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NULL!", "#NUM!")

# officecli issue subtypes that represent a genuine formula error (as opposed to a
# merely stale or unevaluated cache, which officecli resolves by evaluating).
FORMULA_ERROR_SUBTYPES = {"formula_eval_error", "formula_ref_missing_sheet"}


def _find_error_token(text) -> str | None:
    """Return the first Excel error string contained in *text*, or None."""
    if text is None:
        return None
    text = str(text)
    for token in EXCEL_ERRORS:
        if token in text:
            return token
    return None


def _recalc_officecli(path: Path, timeout: int):
    """Evaluate formulas with officecli and collect formula errors.

    Returns (findings, notes, log) where findings is a list of error records,
    notes is a list of non-error formula remarks, and log is the command line
    (with any stderr) for the report.
    """
    cmd = ["officecli", "view", str(path), "issues", "--json"]
    log = "$ " + " ".join(cmd)
    findings: list[dict] = []
    notes: list[str] = []
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return findings, [f"officecli timed out after {timeout}s"], log

    out = (proc.stdout or "").strip()
    try:
        doc = json.loads(out)
    except json.JSONDecodeError:
        detail = (proc.stderr or "").strip() or out
        return findings, [f"officecli view issues: unparseable output ({detail[:200]})"], log

    issues = ((doc.get("data") or {}).get("issues")) or []
    for issue in issues:
        subtype = issue.get("subtype", "") or ""
        if not subtype.startswith("formula_"):
            continue  # non-formula issues are out of scope for a recalc report
        loc = issue.get("path", "?")            # e.g. "Data!B2"
        sheet, sep, coord = loc.partition("!")
        if not sep:
            sheet, coord = "?", loc
        message = issue.get("message", "") or ""
        token = _find_error_token(message) or _find_error_token(issue.get("context"))
        is_error = subtype in FORMULA_ERROR_SUBTYPES or token is not None
        if is_error:
            findings.append({
                "sheet": sheet, "coord": coord,
                "token": token or subtype, "source": "officecli",
                "message": message,
            })
        else:
            notes.append(f"{loc}: {subtype} - {message}")
    return findings, notes, log


def _recalc_libreoffice(path: Path, timeout: int):
    """Recalculate via headless LibreOffice by re-saving the workbook.

    `--convert-to xlsx` reloads and rewrites the file, which recomputes the
    formulas and persists fresh cached values (error results as t="e" cells) that
    the openpyxl scan can then read. Returns the recalculated file path, or None
    if the conversion did not produce an output.

    CODE-REVIEW ONLY in this environment: `soffice` is not installed here, so this
    branch is never exercised. For a guaranteed full recompute (rather than relying
    on LibreOffice's recalc-on-load setting) the robust alternative is a headless
    macro that calls ThisComponent.calculateAll() before storing; the plain
    convert-to path is used here because it needs no macro plumbing.
    """
    out_dir = tempfile.mkdtemp(prefix="recalc_lo_")
    cmd = ["soffice", "--headless", "--calc",
           "--convert-to", "xlsx", "--outdir", out_dir, str(path)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return None
    produced = Path(out_dir) / (path.stem + ".xlsx")
    if proc.returncode == 0 and produced.exists():
        return produced
    return None


def _scan_openpyxl(path: Path):
    """Scan every cell of every sheet for the Excel error strings (cached values)."""
    findings: list[dict] = []
    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    try:
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    token = _find_error_token(cell.value)
                    if token is not None:
                        findings.append({
                            "sheet": ws.title, "coord": cell.coordinate,
                            "token": token, "source": "openpyxl",
                        })
    finally:
        wb.close()
    return findings


def recalc(path: str, timeout: int = 120):
    """Recalculate *path* and report Excel errors. Returns (ok, report)."""
    target = Path(path)
    if not target.exists():
        return False, f"Error: {path} does not exist"
    if target.suffix.lower() != ".xlsx":
        return False, f"Error: {path} must be a .xlsx file"

    lines: list[str] = []
    officecli_findings: list[dict] = []
    officecli_notes: list[str] = []
    scan_target = target        # the file the openpyxl scan reads

    if shutil.which("officecli") is not None:
        lines.append("Recalc engine: officecli")
        officecli_findings, officecli_notes, log = _recalc_officecli(target, timeout)
        lines.append(f"  {log}")
        lines.append(f"  officecli evaluated formulas: "
                     f"{len(officecli_findings)} error(s), {len(officecli_notes)} note(s)")
    elif shutil.which("soffice") is not None:
        lines.append("Recalc engine: LibreOffice (officecli not on PATH)")
        recalced = _recalc_libreoffice(target, timeout)
        if recalced is not None:
            scan_target = recalced
            lines.append(f"  soffice recalculated -> {recalced}")
        else:
            lines.append("  soffice recalc produced no output; scanning the original file")
    else:
        lines.append("Recalc engine: none")
        lines.append("  officecli not on PATH; LibreOffice not found "
                     "(install officecli or LibreOffice to recalculate).")
        lines.append("  Proceeding with an openpyxl scan of the file's existing cached values.")

    try:
        scan_findings = _scan_openpyxl(scan_target)
    except Exception as exc:  # a corrupt/locked file should report, not traceback
        return False, "\n".join(lines + [f"Error: openpyxl scan failed: {exc}"])

    lines.append(f"openpyxl scan ({scan_target.name}): "
                 f"{len(scan_findings)} cell(s) with an error string")
    for rec in scan_findings:
        lines.append(f"  {rec['sheet']}!{rec['coord']}  {rec['token']}")

    # Merge both mechanisms, de-duplicating on (sheet, coordinate).
    seen = set()
    errors: list[dict] = []
    for rec in officecli_findings + scan_findings:
        key = (rec["sheet"], rec["coord"])
        if key in seen:
            continue
        seen.add(key)
        errors.append(rec)

    lines.append("")
    if errors:
        lines.append(f"FOUND {len(errors)} Excel error cell(s):")
        for rec in sorted(errors, key=lambda r: (r["sheet"], r["coord"])):
            lines.append(f"  {rec['sheet']}!{rec['coord']}  {rec['token']}  [{rec['source']}]")
    else:
        lines.append("No Excel errors found.")

    if officecli_notes:
        lines.append("")
        lines.append("Notes (not counted as errors):")
        for note in officecli_notes:
            lines.append(f"  {note}")

    return (not errors), "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if argv else 2)

    file_arg = argv[0]
    timeout = 120
    if len(argv) >= 2:
        try:
            timeout = int(argv[1])
        except ValueError:
            print(f"Error: timeout_seconds must be an integer, got {argv[1]!r}")
            sys.exit(2)

    ok, report = recalc(file_arg, timeout=timeout)
    print(report)
    sys.exit(0 if ok else 1)
