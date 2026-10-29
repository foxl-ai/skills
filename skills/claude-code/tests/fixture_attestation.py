"""Test-only image fingerprint substitution, not a production override.

Transport tests run a supervisor inside Python, not Claude. Keep real kernel
image/UID/start/file checks and substitute only the expected Python fingerprint.
This module is never imported by the production helper.
"""
import os
from pathlib import Path
import sys

import cc_contract


def attest_python(path):
    root = Path(os.environ["FAKE_CC_ROOT"]).resolve(strict=True)
    if not root.name.startswith("cc-tests-") or not (root / "fake-claude").is_file():
        raise cc_contract.ContractError("fixture root required")
    expected = cc_contract.process_image(os.getpid())
    if path != expected or path != Path(sys.executable).resolve():
        raise cc_contract.ContractError("only this test interpreter image is allowed")
    return cc_contract.file_identity(path), "fixture-python-only"
