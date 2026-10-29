"""Offline native-distribution contract checks. No installed Claude is executed."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from test_native_send import IsolatedCase, SID, UUID, TEXT, SCRIPTS, helper, native


class NativeCompatibilityTests(IsolatedCase):
    def configure_native(self):
        (self.root / "version.txt").write_text("2.1.300 (Claude Code)\n")
        self.server.version = "2.1.300"
        self.server.jobs[0]["cliVersion"] = "2.1.300"

    def test_exact_native_and_toolbox_version_output(self):
        for output, version in (
            ("2.1.300 (Claude Code)\n", "2.1.300"),
            ("2.1.293 (Claude Code)\n", "2.1.293"),
            ("claude 2.1.308.1355 (ASBX Claude Code)\n", "2.1.308.1355"),
            ("claude 2.1.309.1365 (ASBX Claude Code)\n", "2.1.309.1365"),
        ):
            with self.subTest(version=version):
                (self.root / "version.txt").write_text(output)
                self.assertEqual(helper.cli_version(), version)
        self.assertEqual(self.server.calls, [])
        self.assertTrue(all(args == ["--version"] for args in self.cli_calls()))

    def test_version_suffix_extra_component_and_ambiguous_output_are_not_truncated(self):
        for output in ("2.1.300-beta (Claude Code)", "2.1.300+build", "2.1.300.7.1",
                       "v2.1.300-custom", "2.1.300native", "native2.1.300", "",
                       "2.1.300 (Claude Code) 2.1.309.1365"):
            with self.subTest(output=output):
                (self.root / "version.txt").write_text(output)
                with self.assertRaises(native.BridgeError) as error:
                    helper.cli_version()
                self.assertEqual(error.exception.code, "EVERSION")
        self.assertEqual(self.server.calls, [])

    def test_structural_contract_is_documented_without_numeric_allowlists(self):
        contract = json.loads((SCRIPTS.parent / "reference/native-reply-contract.json").read_text())
        self.assertFalse(hasattr(native, "CLI_VERSIONS"))
        self.assertFalse(hasattr(native, "DAEMON_VERSIONS"))
        self.assertEqual(contract["structural_contracts"][0]["id"], "queue-v1-structural-1")
        self.assertEqual(set(contract["structural_contracts"][0]["sha256"]),
                         {"supervisor_reply", "worker_handoff", "worker_receive"})

    def test_historical_and_future_cli_supervisor_pairs_require_matching_worker(self):
        for cli in ("2.1.300", "2.1.308.1355", "2.1.310.1371", "2.1.312.1459", "9.4.2000.9100"):
            (self.root / "version.txt").write_text(cli + " (Claude Code)")
            for daemon in ("2.1.300", "2.1.309", "2.1.310", "2.1.312", "9.4.2000"):
                with self.subTest(cli=cli, daemon=daemon):
                    self.server.version = daemon
                    self.server.jobs[0]["cliVersion"] = daemon
                    code, report = self.call("doctor", SID, "--json")
                    self.assertEqual(code, 0)
                    self.assertEqual(report["cli_version"], cli)
                    self.assertEqual(report["daemon_version"], daemon)
                    self.assertEqual(report["target"]["worker_version"], daemon)
                    self.assertFalse(report["auth_verified"])
                    self.server.jobs[0]["cliVersion"] = "2.1.293"
                    self.assertEqual(self.call("doctor", SID, "--json")[1]["error_code"], "ESKEW")
        self.assertFalse(self.state.exists())
        self.assertEqual(self.reply_count(), 0)

    def test_293_precise_capability_refusal_before_auth_or_reply(self):
        (self.root / "version.txt").write_text("2.1.293 (Claude Code)")
        self.server.version = "2.1.293"
        self.server.carried_prompts_format = None
        for args in (("doctor", "--json"), ("send", SID, TEXT)):
            with self.subTest(command=args[0]), patch.object(native.NativeReply, "_auth", side_effect=AssertionError):
                code, report = self.call(*args)
                self.assertEqual(code, 4)
                self.assertEqual(report["error_code"], "EPROTO")
                self.assertIn("carriedPromptsFormat=1", report["note"])
                self.assertFalse(report["accepted"])
        self.assertTrue(all(call["op"] == "ping" for call in self.server.calls))
        self.assertTrue(all(args[:1] in (["agents"], ["--version"]) for args in self.cli_calls()))

    def test_missing_or_changed_queue_capability_is_not_inferred_from_version(self):
        self.configure_native()
        for value in (None, False, True, "1", 1.0, 0, 2):
            with self.subTest(value=value):
                self.server.carried_prompts_format = value
                code, report = self.call("send", SID, TEXT)
                self.assertEqual(code, 4)
                self.assertEqual(report["error_code"], "EPROTO")
                self.assertFalse(report["accepted"])
        self.assertEqual(self.reply_count(), 0)

    def test_adjacent_native_cli_numbers_are_not_a_compatibility_gate(self):
        for version in ("2.1.299", "2.1.301", "2.1.300.1", "2.1.308", "2.1.309", "12.8.9000"):
            with self.subTest(version=version):
                (self.root / "version.txt").write_text(version + " (Claude Code)")
                code, report = self.call("doctor", "--json")
                self.assertEqual(code, 0)
                self.assertEqual(report["cli_version"], version)
                self.assertEqual(report["compatibility"], "negotiated-and-structurally-attested")
        self.assertEqual(self.reply_count(), 0)

    def test_native_subprocess_busy_idle_dedupe_and_process_identity(self):
        self.configure_native()
        # Stay alive until teardown, even on a slow test host. Wait for startup
        # rather than racing ps against the child's interpreter initialization.
        child = subprocess.Popen(
            [sys.executable, "-c", "import sys; print('ready', flush=True); sys.stdin.read()"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            self.assertEqual(child.stdout.readline(), b"ready\n")
            self.session["pid"] = child.pid
            self.set_sessions([self.session])
            before = {p.relative_to(self.config): p.read_bytes()
                      for p in self.config.rglob("*") if p.is_file()}
            runner = Path(__file__).with_name("isolated_runner.py")
            env = {**os.environ, "HOME": str(self.root), "CLAUDE_CONFIG_DIR": str(self.config),
                   "CC_SESSIONS_STATE": str(self.state), "CLAUDE_BIN": str(self.cli),
                   "FAKE_CC_SOCKETS": str(self.root / "sockets")}
            for status, state in (("busy", "working"), ("idle", "done")):
                self.session.update(status=status, state=state)
                self.set_sessions([self.session])
                self.server.jobs[0]["state"] = state
                for duplicate in (False, True):
                    result = subprocess.run(
                        [sys.executable, str(runner), "send", SID, TEXT,
                         "--request-id", "native-" + status], env=env,
                        capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                    report = json.loads(result.stdout)
                    self.assertEqual((report["id"], report["sessionId"]), (SID, UUID))
                    self.assertEqual(report["daemon_version"], "2.1.300")
                    self.assertTrue(report["accepted"])
                    self.assertTrue(report["queued"])
                    self.assertFalse(report["observed"])
                    self.assertEqual(report["duplicate_suppressed"], duplicate)
                self.assertIsNone(child.poll())
                self.assertEqual(json.loads((self.root / "sessions.json").read_text())[0]["pid"], child.pid)
            self.assertEqual(self.reply_count(), 2)
            self.assertTrue(all(req["short"] == SID and req["nextTurn"] is True
                                for req in self.server.calls if req["op"] == "reply"))
            self.assertEqual(before, {p.relative_to(self.config): p.read_bytes()
                                     for p in self.config.rglob("*") if p.is_file()})
            self.assertTrue(all(args[:1] in (["agents"], ["--version"]) for args in self.cli_calls()))
            self.assertEqual(len(list((self.state / "native-replies-v1").glob("*.json"))), 2)
        finally:
            child.terminate()
            child.wait(timeout=5)
            child.stdin.close()
            child.stdout.close()

    def test_native_unknown_outcome_still_suppresses_resend(self):
        self.configure_native()
        self.server.mode = "drop"
        code, report = self.call("send", SID, TEXT, "--request-id", "native-unknown")
        self.assertEqual(code, 5)
        self.assertEqual(report["status"], "unknown")
        self.assertIsNone(report["accepted"])
        code, repeat = self.call("send", SID, TEXT, "--request-id", "native-unknown")
        self.assertEqual(code, 5)
        self.assertTrue(repeat["duplicate_suppressed"])
        self.assertEqual(self.reply_count(), 1)

    def test_clean_native_config_is_not_initialized_or_repaired_by_doctor(self):
        self.configure_native()
        clean = self.root / "fresh-native-config"
        clean.mkdir(mode=0o700)
        with patch.object(helper, "CONFIG", str(clean)), \
                patch.object(native.socket, "socket", side_effect=AssertionError("no endpoint")):
            code, report = self.call("doctor", "--json")
        self.assertEqual(code, 4)
        self.assertEqual(report["error_code"], "ENODAEMON")
        self.assertFalse(report["accepted"])
        self.assertEqual(list(clean.iterdir()), [])
        self.assertFalse(self.state.exists())
        self.assertEqual(self.cli_calls(), [["--version"]])
        self.assertEqual(self.server.calls, [])

    def test_native_config_socket_hash_and_key_location_are_exact(self):
        bridge = self.bridge(version="2.1.300")
        digest = hashlib.sha256(str(self.config).encode("utf-8")).hexdigest()[:8]
        self.assertEqual(bridge.socket_path, self.root / "sockets" /
                         ("cc-daemon-%s" % os.getuid()) / digest / "control.sock")
        self.assertEqual(bridge.auth_path, self.config / "daemon/control.key")
        with patch.dict(os.environ, {"TMPDIR": str(self.root / "unused-temp")}), \
                patch.object(native.socket, "socket", side_effect=AssertionError("no connection")):
            normal = native.NativeReply(str(self.config), "2.1.300")
        self.assertEqual(normal.socket_path, Path(os.path.realpath("/tmp")) /
                         ("cc-daemon-%s" % os.getuid()) / digest / "control.sock")
        other = self.bridge(config=str(self.root / "other-config"), version="2.1.300")
        self.assertNotEqual(other.socket_path, bridge.socket_path)
        self.assertEqual(self.server.calls, [])

    def test_native_auth_mismatch_missing_key_and_worker_skew_fail_closed(self):
        self.configure_native()
        self.server.jobs[0]["cliVersion"] = "2.1.309"
        code, report = self.call("send", SID, TEXT, "--request-id", "native-skew")
        self.assertEqual(code, 4)
        self.assertEqual(report["error_code"], "ESKEW")
        self.assertEqual(self.reply_count(), 0)
        self.server.jobs[0]["cliVersion"] = "2.1.300"
        self.key.unlink()
        code, report = self.call("send", SID, TEXT, "--request-id", "native-missing-auth")
        self.assertEqual(code, 4)
        self.assertEqual(report["error_code"], "EAUTHFILE")
        self.assertFalse(self.key.exists())
        self.assertEqual(self.reply_count(), 0)
        self.key.write_text("1" * 32)
        self.key.chmod(0o600)
        code, report = self.call("send", SID, TEXT, "--request-id", "native-auth-mismatch")
        self.assertEqual(code, 4)
        self.assertEqual(report["error_code"], "EAUTH")
        self.assertFalse(report["accepted"])
        self.assertNotIn("1" * 32, json.dumps(report))
        self.assertEqual(self.reply_count(), 1)


if __name__ == "__main__":
    unittest.main()
