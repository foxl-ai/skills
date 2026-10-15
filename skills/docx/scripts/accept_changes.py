"""Accept (or reject) every tracked change in a DOCX, in place to a new file.

Uses officecli, which applies revision markup directly - no Word, no LibreOffice:

    officecli set <file> /revision --prop revision.action=accept

officecli holds edited documents in a resident process, so this flushes the input
first, works on a copy at the destination, then closes (flushes) the result so any
other reader - python-docx, Word, a validator - sees the applied file on disk.

Usage:
    python accept_changes.py <input.docx> <output.docx> [--reject]
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

INSTALL_HINT = (
    "officecli is required. Install it with:\n"
    "  curl -fsSL https://d.officecli.ai/install.sh | bash\n"
    "  (Windows PowerShell: irm https://d.officecli.ai/install.ps1 | iex)"
)


def _officecli(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["officecli", *args], capture_output=True, text=True,
                          timeout=timeout, check=False)


def accept_changes(input_file: str, output_file: str, action: str = "accept") -> str:
    src, dst = Path(input_file), Path(output_file)
    if not src.exists():
        return f"Error: input not found: {input_file}"
    if src.suffix.lower() != ".docx":
        return f"Error: not a .docx file: {input_file}"
    if action not in ("accept", "reject"):
        return f"Error: action must be 'accept' or 'reject'"
    if shutil.which("officecli") is None:
        return f"Error: {INSTALL_HINT}"

    _officecli("save", str(src.resolve()), timeout=60)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    target = str(dst.resolve())

    try:
        proc = _officecli("set", target, "/revision", "--prop", f"revision.action={action}")
    except subprocess.TimeoutExpired:
        return "Error: officecli timed out applying tracked changes"
    if proc.returncode != 0:
        return f"Error: officecli failed: {(proc.stderr or proc.stdout).strip() or 'unknown error'}"

    _officecli("close", target, timeout=60)
    return f"{action.capitalize()}ed all tracked changes: {input_file} -> {output_file}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Accept or reject tracked changes in a DOCX")
    ap.add_argument("input_file")
    ap.add_argument("output_file")
    ap.add_argument("--reject", action="store_true")
    args = ap.parse_args()
    msg = accept_changes(args.input_file, args.output_file, "reject" if args.reject else "accept")
    print(msg)
    sys.exit(1 if msg.startswith("Error") else 0)
