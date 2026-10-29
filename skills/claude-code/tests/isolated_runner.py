"""Test-only subprocess entry point; refuses non-fixture CLI/config/state/socket roots."""
import os
from pathlib import Path
import sys

root = Path(os.environ["FAKE_CC_ROOT"]).resolve(strict=True)
for key in ("CLAUDE_BIN", "CLAUDE_CONFIG_DIR", "CC_SESSIONS_STATE", "FAKE_CC_SOCKETS"):
    path = Path(os.environ[key]).resolve()
    if root not in path.parents:
        raise SystemExit("Test runner requires isolated fixture paths")
if Path(os.environ["CLAUDE_BIN"]).name != "fake-claude":
    raise SystemExit("A real Claude executable is not allowed")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cc_native_reply
import cc_sessions
import cc_contract
from fixture_attestation import attest_python

cc_contract.attest_image = attest_python


def bridge(config, version):
    return cc_native_reply.NativeReply(config, version, timeout=1,
                                       temp_root=os.environ["FAKE_CC_SOCKETS"])


cc_sessions.NativeReply = bridge
sys.exit(cc_sessions.main())
