"""Accept all tracked changes in a DOCX file using officecli.

Requires `officecli` on PATH (a single self-contained binary):
    curl -fsSL https://d.officecli.ai/install.sh | bash
    # Windows: irm https://d.officecli.ai/install.ps1 | iex

No LibreOffice, no Word, no macro profile. officecli applies the revision
markup directly:
    officecli set <file> /revision --prop revision.action=accept
"""

import argparse
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

INSTALL_HINT = (
    "officecli not found. Install it with:\n"
    "  curl -fsSL https://d.officecli.ai/install.sh | bash\n"
    "  (Windows PowerShell: irm https://d.officecli.ai/install.ps1 | iex)\n"
    "Then verify with: officecli --version"
)


def accept_changes(
    input_file: str,
    output_file: str,
    action: str = "accept",
) -> tuple[None, str]:
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        return None, f"Error: Input file not found: {input_file}"

    if not input_path.suffix.lower() == ".docx":
        return None, f"Error: Input file is not a DOCX file: {input_file}"

    if action not in ("accept", "reject"):
        return None, f"Error: action must be 'accept' or 'reject', got: {action}"

    if shutil.which("officecli") is None:
        return None, f"Error: {INSTALL_HINT}"

    # CRITICAL: flush the INPUT first. officecli keeps edited documents in a
    # resident process, so a file just built with `officecli add/set` may not
    # be on disk yet - copying it without this produces a copy that is missing
    # the newest content (measured: a fresh paragraph vanished entirely).
    subprocess.run(
        ["officecli", "save", str(input_path.absolute())],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    # officecli edits in place, so operate on a copy at the destination.
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(input_path, output_path)
    except Exception as e:
        return None, f"Error: Failed to copy input file to output location: {e}"

    abs_output = str(output_path.absolute())

    try:
        result = subprocess.run(
            [
                "officecli",
                "set",
                abs_output,
                "/revision",
                "--prop",
                f"revision.action={action}",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, "Error: officecli timed out applying tracked changes"

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return None, f"Error: officecli failed: {detail or 'unknown error'}"

    # Flush the resident process so any non-officecli reader (python-docx, Word,
    # a validator, an upload) sees the applied result on disk.
    close_result = subprocess.run(
        ["officecli", "close", abs_output],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if close_result.returncode != 0:
        logger.warning(
            "officecli close failed (file may still be flushed by the idle "
            "timeout): %s",
            (close_result.stderr or close_result.stdout or "").strip(),
        )

    verb = "accepted" if action == "accept" else "rejected"
    return None, f"Successfully {verb} all tracked changes: {input_file} -> {output_file}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Accept (or reject) all tracked changes in a DOCX file"
    )
    parser.add_argument("input_file", help="Input DOCX file with tracked changes")
    parser.add_argument(
        "output_file", help="Output DOCX file (clean, no tracked changes)"
    )
    parser.add_argument(
        "--reject",
        action="store_true",
        help="Reject all tracked changes instead of accepting them",
    )
    args = parser.parse_args()

    _, message = accept_changes(
        args.input_file,
        args.output_file,
        action="reject" if args.reject else "accept",
    )
    print(message)

    if "Error" in message:
        raise SystemExit(1)
