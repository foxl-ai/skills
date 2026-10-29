"""Toolbox 310 regressions using only the existing isolated fake CLI/socket."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from test_native_send import IsolatedCase, SID, UUID, TEXT, FAKE_KEY, SCRIPTS
import cc_native_reply as native
import cc_outbox as outbox
import cc_sessions as helper

CLI = "2.1.310.1371"
DAEMON = "2.1.310"
PREVIOUS = "2.1.309"


class Toolbox310Tests(IsolatedCase):
    def setUp(self):
        super().setUp()
        self.versions(CLI, DAEMON)

    def versions(self, cli, daemon, worker=None):
        (self.root / "version.txt").write_text(
            "claude %s (ASBX Claude Code, channel head)" % cli)
        self.server.version = daemon
        self.server.jobs[0]["cliVersion"] = worker or daemon

    def test_previously_reviewed_pairs_keep_working_under_capability_checks(self):
        expected = {
            ("2.1.308.1355", "2.1.308"), ("2.1.308.1355", PREVIOUS),
            ("2.1.309.1365", "2.1.308"), ("2.1.309.1365", PREVIOUS),
            (CLI, PREVIOUS), (CLI, DAEMON),
        }
        self.assertFalse(hasattr(native, "REVIEWED_PAIRS"))
        for cli, daemon in sorted(expected):
            with self.subTest(cli=cli, daemon=daemon):
                self.versions(cli, daemon)
                code, result = self.call("doctor", SID, "--json")
                self.assertEqual(code, 0)
                self.assertEqual(result["target"]["worker_version"], daemon)
                self.assertFalse(result["auth_verified"])
                self.assertFalse(self.state.exists())
                self.assertEqual(self.reply_count(), 0)
        self.assertTrue(all(call["op"] in ("ping", "list") for call in self.server.calls))

    def test_310_cli_matching_and_309_pair_send_once_busy_idle_blocked(self):
        for daemon in (PREVIOUS, DAEMON):
            self.versions(CLI, daemon)
            for state, status in (("working", "busy"), ("done", "idle"), ("blocked", "waiting")):
                with self.subTest(daemon=daemon, state=state):
                    self.session.update(state=state, status=status)
                    self.set_sessions([self.session])
                    key = "310-%s-%s" % (daemon, state)
                    before = self.reply_count()
                    code, result = self.call("send", SID, TEXT, "--request-id", key)
                    self.assertEqual(code, 0)
                    self.assertEqual(result["sessionId"], UUID)
                    self.assertEqual(result["daemon_version"], daemon)
                    self.assertTrue(result["accepted"] and result["queued"])
                    self.assertFalse(result["observed"])
                    code, retry = self.call("send", UUID, TEXT, "--request-id", key)
                    self.assertEqual(code, 0)
                    self.assertTrue(retry["duplicate_suppressed"])
                    self.assertEqual(self.reply_count(), before + 1)
        self.assertTrue(all(call["short"] == SID and call["nextTurn"] is True
                            for call in self.server.calls if call["op"] == "reply"))
        self.assertTrue(all(args[0] in ("agents", "--version") for args in self.cli_calls()))

    def test_cli_suffix_extra_component_and_ambiguous_versions_fail(self):
        versions = (CLI + ".1", CLI + "-dev", CLI + "+custom", CLI + "x",
                    "v" + CLI, "2.1.309.1365-rc1", CLI + " 2.1.309.1365",
                    CLI + "-dev (based on " + CLI + ")")
        for version in versions:
            with self.subTest(version=version):
                self.versions(version, DAEMON)
                code, result = self.call("send", SID, TEXT)
                self.assertEqual((code, result["error_code"]), (4, "EVERSION"))
        self.assertEqual(self.server.calls, [])

    def test_worker_skew_and_protocol_fail_before_reply(self):
        for daemon in (PREVIOUS, DAEMON):
            for worker in ("2.1.308", "2.1.311", CLI, "unknown", None,
                           PREVIOUS if daemon == DAEMON else DAEMON):
                self.versions(CLI, daemon)
                self.server.jobs[0]["cliVersion"] = worker
                code, result = self.call("send", SID, TEXT)
                self.assertEqual((code, result["error_code"]), (4, "ESKEW"))
        self.versions(CLI, DAEMON)
        for proto, queue_format in ((2, 1), (True, 1), (1, 2), (1, True)):
            self.server.proto, self.server.carried_prompts_format = proto, queue_format
            code, result = self.call("send", SID, TEXT)
            self.assertEqual((code, result["error_code"]), (4, "EPROTO"))
        self.assertEqual(self.reply_count(), 0)
        self.assertEqual(list((self.state / "native-replies-v1").glob("*.json")), [])

    def test_310_identity_duplicates_stopped_and_unavailable_targets_refuse(self):
        original = dict(self.server.jobs[0])
        for jobs in ([original, original], [{**original, "sessionId": "0" * 36}], [],
                     [{**original, "backend": "peer"}], [{**original, "legacy": True}],
                     [{**original, "dying": True}], [{**original, "outcome": "done"}],
                     [{**original, "state": "stopped"}], [{**original, "state": "failed"}],
                     [{**original, "pid": True}], [{**original, "pid": 1}]):
            self.server.jobs = jobs
            code, result = self.call("send", SID, TEXT)
            self.assertEqual((code, result["error_code"]), (4, "ETARGET"))
        self.server.jobs = [original]
        for delta in ({"state": "stopped"}, {"state": "failed"}, {"pid": None},
                      {"pid": True}, {"status": "offline"}, {"sessionId": "../unsafe"}):
            self.set_sessions([{**self.session, **delta}])
            code, result = self.call("send", SID, TEXT)
            self.assertEqual((code, result["error_code"]), (4, "ETARGET"))
        self.set_sessions([self.session])
        bridge = self.bridge(version=CLI)
        bridge.prepare(self.session)
        with patch.object(native, "validate_process_pair", return_value=((999, 1, 0, "changed"),)):
            with self.assertRaises(native.BridgeError) as caught:
                bridge.reply(self.session, TEXT)
        self.assertEqual(caught.exception.code, "ECHANGED")
        self.assertFalse(caught.exception.uncertain)
        self.assertEqual(self.reply_count(), 0)

    def test_310_known_rejections_and_unknown_outcomes_never_retry(self):
        known = ("EAUTH", "EPROTO", "ESTARTING", "ERESPAWNING", "ESKEW", "ENOJOB", "ENOREPLY")
        unknown = ("timeout", "drop", "bad-json", "duplicate-json", "unknown-ack",
                   "oversize", "EUNKNOWN", "EPEERUID", "ETOOLARGE")
        for daemon in (PREVIOUS, DAEMON):
            self.versions(CLI, daemon)
            for mode in known + unknown:
                with self.subTest(daemon=daemon, mode=mode):
                    self.server.mode = mode
                    key = "310-%s-%s" % (daemon, mode)
                    code, result = self.call("send", SID, TEXT, "--request-id", key)
                    self.assertEqual(code, 4 if mode in known else 5)
                    self.assertEqual(result["status"], "rejected" if mode in known else "unknown")
                    before = self.reply_count()
                    self.assertTrue(self.call("send", SID, TEXT, "--request-id", key)[1]["duplicate_suppressed"])
                    self.assertEqual(self.reply_count(), before)
                    self.assertNotIn(FAKE_KEY, json.dumps(result))
                    self.assertNotIn(TEXT, json.dumps(result))

    def test_310_receipt_reservation_and_key_survive_cli_upgrade(self):
        self.versions("2.1.309.1365", PREVIOUS)
        self.assertEqual(self.call("send", SID, TEXT)[0], 0)
        self.versions(CLI, DAEMON)
        code, result = self.call("send", SID, TEXT)
        self.assertEqual(code, 0)
        self.assertTrue(result["duplicate_suppressed"])
        self.assertEqual(self.reply_count(), 1)
        # An unknown reservation made before an upgrade still forbids a send.
        box = outbox.Outbox(str(self.state), str(self.config))
        with box.mutation_guard():
            path, receipt = box.request(self.session, "separate unknown", "reserved-before-310")
            outbox.atomic_save(path, receipt)
        code, result = self.call("send", SID, "separate unknown", "--request-id", "reserved-before-310")
        self.assertEqual(code, 5)
        self.assertTrue(result["duplicate_suppressed"])
        self.assertEqual(self.reply_count(), 1)
        real_save = helper.atomic_save
        writes = []
        def fail_final_save(path, receipt):
            writes.append(path)
            if len(writes) == 2:
                raise OSError("fixture ACK persistence failure")
            return real_save(path, receipt)
        with patch.object(helper, "atomic_save", fail_final_save):
            code, result = self.call("send", SID, "ACK write fails", "--request-id", "310-ack-write")
        self.assertEqual((code, result["error_code"]), (5, "ERECEIPT"))
        self.assertEqual(self.call("send", SID, "ACK write fails", "--request-id", "310-ack-write")[0], 5)
        self.assertEqual(self.reply_count(), 2)
        code, result = self.call("send", SID, "changed text", "--request-id", "310-ack-write")
        self.assertEqual((code, result["error_code"]), (4, "EREQUEST"))

    def test_310_unsafe_paths_ownership_and_peer_still_fail_closed(self):
        self.config.chmod(0o777)
        self.assertEqual(self.call("send", SID, TEXT)[1]["error_code"], "EPATH")
        self.config.chmod(0o700)
        self.server.directory.chmod(0o755)
        self.assertEqual(self.call("send", SID, TEXT)[1]["error_code"], "EPATH")
        self.server.directory.chmod(0o700)
        link = self.root / "config-link"
        link.symlink_to(self.config, target_is_directory=True)
        with patch.object(helper, "CONFIG", str(link)):
            self.assertEqual(self.call("send", SID, TEXT)[1]["error_code"], "EPATH")
        self.key.chmod(0o644)
        self.assertEqual(self.call("send", SID, TEXT)[1]["error_code"], "EAUTHFILE")
        self.key.chmod(0o600)
        key_link = self.root / "linked-key"
        os.link(self.key, key_link)
        self.assertEqual(self.call("send", SID, TEXT)[1]["error_code"], "EAUTHFILE")
        key_link.unlink()
        real_lstat = native.os.lstat
        def foreign_socket(path, *args, **kwargs):
            value = real_lstat(path, *args, **kwargs)
            if Path(path) == self.server.path:
                fields = list(value)
                fields[4] = os.getuid() + 1
                return os.stat_result(fields)
            return value
        with patch.object(native.os, "lstat", foreign_socket):
            self.assertEqual(self.call("send", SID, TEXT)[1]["error_code"], "EPATH")
        with patch.object(native, "peer_identity", side_effect=native.BridgeError("EPEER", "wrong peer")):
            self.assertEqual(self.call("send", SID, TEXT)[1]["error_code"], "EPEER")
        state_link = self.root / "state-link"
        state_link.symlink_to(self.state, target_is_directory=True)
        with patch.object(helper, "STATE", str(state_link)):
            self.assertEqual(self.call("send", SID, TEXT)[0], 4)
        self.assertEqual(self.reply_count(), 0)

    def test_310_full_subprocess_matching_and_cross_pair_preserve_native_files(self):
        before = {p.relative_to(self.config): p.read_bytes() for p in self.config.rglob("*") if p.is_file()}
        runner = Path(__file__).with_name("isolated_runner.py")
        env = {**os.environ, "HOME": str(self.root), "CLAUDE_CONFIG_DIR": str(self.config),
               "CC_SESSIONS_STATE": str(self.state), "CLAUDE_BIN": str(self.cli),
               "FAKE_CC_SOCKETS": str(self.root / "sockets")}
        for daemon in (PREVIOUS, DAEMON):
            self.versions(CLI, daemon)
            for duplicate in (False, True):
                result = subprocess.run([sys.executable, str(runner), "send", SID, TEXT,
                                         "--request-id", "310-subprocess-" + daemon],
                                        env=env, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)["duplicate_suppressed"], duplicate)
        self.assertEqual(self.reply_count(), 2)
        self.assertEqual(before, {p.relative_to(self.config): p.read_bytes() for p in self.config.rglob("*") if p.is_file()})
        self.assertTrue(all(args[0] in ("agents", "--version") for args in self.cli_calls()))
