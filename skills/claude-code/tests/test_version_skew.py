"""Version-skew regressions (2026-11-13). Synthetic fixtures only.

Observed live: a Toolbox 2.1.323.1727 supervisor with an orchestrator session
still running the 2.1.322.1695 build, whose binary the updater had deleted. The
helper used to refuse ESKEW. Skew is now reported, the supervisor's own
next-turn build rule is respected by sending the agents-UI request, and the
refusals that protect the owner still hold.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_native_send import IsolatedCase, SID, UUID, TEXT, helper, native, outbox
import cc_contract as contract

ORIGINAL_ATTEST = contract.attest_image


class VersionSkewTests(IsolatedCase):
    def versions(self, cli, daemon, worker=None):
        (self.root / "version.txt").write_text("claude %s (ASBX Claude Code, channel head)" % cli)
        self.server.version = daemon
        self.server.jobs[0]["cliVersion"] = daemon if worker is None else worker

    def repl_child(self):
        child = subprocess.Popen([sys.executable, "-c", "import sys; print('ready', flush=True); sys.stdin.read()"],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.addCleanup(child.stdout.close)
        self.addCleanup(child.stdin.close)
        self.addCleanup(child.wait, 5)
        self.addCleanup(child.terminate)
        self.assertEqual(child.stdout.readline(), b"ready\n")
        self.session["pid"] = child.pid
        self.set_sessions([self.session])
        return child

    def test_observed_323_supervisor_with_322_worker_whose_binary_was_deleted(self):
        self.versions("2.1.323.1727", "2.1.323", "2.1.322")
        child = self.repl_child()
        actual = contract.process_image
        def deleted(pid):
            if pid == child.pid:
                raise contract.ContractError("kernel executable identity unavailable")
            return actual(pid)
        with patch.object(contract, "process_image", side_effect=deleted):
            code, report = self.call("doctor", SID, "--json")
            self.assertEqual(code, 0, report)
            self.assertEqual((report["cli_version"], report["daemon_version"], report["worker_version"]),
                             ("2.1.323.1727", "2.1.323", "2.1.322"))
            self.assertTrue(report["skew"])
            self.assertEqual(report["route"], "agents-ui-reply")
            self.assertEqual(report["target"]["worker_image"], "unavailable")
            self.assertTrue(report["target"]["send_ready"])
            self.assertTrue(any("different builds" in w for w in report["warnings"]))
            self.assertFalse(self.state.exists())
            self.assertEqual(self.reply_count(), 0)
            for duplicate in (False, True):
                code, result = self.call("send", SID, TEXT, "--request-id", "regression-323-322")
                self.assertEqual(code, 0, result)
                self.assertEqual(result["duplicate_suppressed"], duplicate)
                self.assertEqual((result["id"], result["sessionId"]), (SID, UUID))
                self.assertTrue(result["accepted"] and result["queued"] and result["skew"])
                self.assertFalse(result["observed"])
                self.assertEqual((result["worker_version"], result["daemon_version"]), ("2.1.322", "2.1.323"))
                self.assertEqual(result["route"], "agents-ui-reply")
        self.assertEqual(self.reply_count(), 1)
        sent = self.replies()[0]
        self.assertEqual((sent["short"], sent["proto"]), (SID, 1))
        self.assertNotIn("nextTurn", sent)
        self.assertEqual(self.server.server_skew_refusals, 0)
        self.assertIsNone(child.poll())
        self.assertTrue(all(args[:1] in (["agents"], ["--version"]) for args in self.cli_calls()))

    def test_agents_ui_send_unknown_outcome_is_never_retried(self):
        self.versions("2.1.323.1727", "2.1.323", "2.1.322")
        self.server.mode = "drop"
        code, result = self.call("send", SID, TEXT, "--request-id", "skew-unknown")
        self.assertEqual((code, result["status"]), (5, "unknown"))
        self.server.mode = "ok"
        code, repeat = self.call("send", SID, TEXT, "--request-id", "skew-unknown")
        self.assertEqual(code, 5)
        self.assertTrue(repeat["duplicate_suppressed"])
        self.assertEqual(repeat["route"], "agents-ui-reply")
        self.assertEqual(self.reply_count(), 1)

    def test_future_unreviewed_330_build_with_protocol_1_proceeds(self):
        unreviewed = patch.object(contract, "attest_image",
                                  side_effect=contract.ContractError("reply/handoff/receive structure differs"))
        for worker, route in (("2.1.330", "next-turn-queue"), ("2.1.323", "agents-ui-reply")):
            with self.subTest(worker=worker), unreviewed:
                self.versions("2.1.330.1800", "2.1.330", worker)
                code, report = self.call("doctor", SID, "--json")
                self.assertEqual(code, 0, report)
                self.assertEqual(report["compatibility"], "negotiated-unreviewed-build")
                self.assertFalse(report["reviewed_build"])
                self.assertEqual((report["protocol"], report["queue_format"]), (1, 1))
                self.assertEqual(report["route"], route)
                self.assertTrue(any("unreviewed build" in w for w in report["warnings"]))
                code, result = self.call("send", SID, TEXT, "--request-id", "future-330-" + worker)
                self.assertEqual(code, 0, result)
                self.assertTrue(result["accepted"])
                self.assertFalse(result["reviewed_build"])
                self.assertEqual(result["route"], route)
                self.assertEqual(self.replies()[-1].get("nextTurn"), True if route == "next-turn-queue" else None)
        self.assertEqual(self.reply_count(), 2)

    def test_agents_ui_route_refuses_commands_controls_and_pending_dialogs_before_reserving(self):
        self.versions("2.1.323.1727", "2.1.323", "2.1.322")
        for text, code_name in (("/clear", "ECOMMAND"), ("  /model opus", "ECOMMAND"), ("!rm -rf build", "ECOMMAND"),
                                ("ok\x1b[201~\r/clear", "EMESSAGE"), ("ok\rnext", "EMESSAGE"), ("ok\x9b", "EMESSAGE")):
            with self.subTest(text=text):
                code, result = self.call("send", SID, text)
                self.assertEqual((code, result["error_code"], result["status"]), (4, code_name, "refused"))
        for session_delta, job_delta in (({"status": "waiting"}, {}), ({"state": "blocked"}, {}),
                                         ({}, {"tempo": "blocked"}), ({}, {"state": "blocked"}),
                                         ({"status": "someday-new"}, {})):
            with self.subTest(session=session_delta, job=job_delta):
                original_job = dict(self.server.jobs[0])
                self.set_sessions([{**self.session, **session_delta}])
                self.server.jobs[0].update(job_delta)
                code, report = self.call("doctor", SID, "--json")
                self.assertEqual(code, 0, report)
                self.assertFalse(report["target"]["send_ready"])
                self.assertEqual(report["target"]["send_refusal"], "EBLOCKED")
                code, result = self.call("send", SID, TEXT)
                self.assertEqual((code, result["error_code"]), (4, "EBLOCKED"))
                self.set_sessions([self.session])
                self.server.jobs[0] = original_job
        self.assertEqual(self.reply_count(), 0)
        receipts = self.state / "native-replies-v1"
        self.assertEqual(list(receipts.glob("*.json")) if receipts.exists() else [], [])

    def test_pending_dialog_becoming_visible_after_prepare_is_refused(self):
        self.versions("2.1.323.1727", "2.1.323", "2.1.322")
        bridge = self.bridge()
        bridge.prepare(self.session)
        self.server.jobs[0]["tempo"] = "blocked"
        with self.assertRaises(native.BridgeError) as caught:
            bridge.reply(self.session, TEXT)
        self.assertEqual(caught.exception.code, "EBLOCKED")
        self.assertFalse(caught.exception.uncertain)
        self.assertEqual(self.reply_count(), 0)

    def test_matching_build_keeps_next_turn_semantics_for_slash_text_and_blocked_sessions(self):
        self.versions("2.1.323.1727", "2.1.323")
        for index, (text, delta) in enumerate((("/not-a-command, just text", {}),
                                               (TEXT, {"state": "blocked", "status": "waiting"}))):
            self.set_sessions([{**self.session, **delta}])
            code, result = self.call("send", SID, text, "--request-id", "match-%d" % index)
            self.assertEqual(code, 0, result)
            self.assertFalse(result["skew"])
            self.assertEqual(result["route"], "next-turn-queue")
            self.assertIs(self.replies()[-1]["nextTurn"], True)
        self.assertEqual(self.reply_count(), 2)

    def test_worker_build_or_process_change_mid_request_is_echanged(self):
        self.versions("2.1.323.1727", "2.1.323", "2.1.322")
        for delta in ({"cliVersion": "2.1.323"}, {"cliVersion": None}, {"pid": 1}):
            with self.subTest(delta=delta):
                original = dict(self.server.jobs[0])
                bridge = self.bridge()
                bridge.prepare(self.session)
                self.server.jobs[0].update(delta)
                with self.assertRaises(native.BridgeError) as caught:
                    bridge.reply(self.session, TEXT)
                self.assertEqual(caught.exception.code, "ECHANGED")
                self.assertFalse(caught.exception.uncertain)
                self.server.jobs[0] = original
        bridge = self.bridge()
        bridge.prepare(self.session)
        self.server.version = "2.1.324"
        with self.assertRaises(native.BridgeError) as caught:
            bridge.reply(self.session, TEXT)
        self.assertEqual(caught.exception.code, "ECHANGED")
        self.assertEqual(self.reply_count(), 0)

    def test_skew_does_not_bypass_identity_protocol_path_or_auth_refusals(self):
        self.versions("2.1.323.1727", "2.1.323", "2.1.322")
        original = dict(self.server.jobs[0])
        for jobs in ([{**original, "sessionId": "87654321-1234-5678-9abc-123456789abc"}], [original, original],
                     [{**original, "dying": True}], [{**original, "backend": "peer"}],
                     [{**original, "outcome": "done"}], [{**original, "state": "stopped"}], []):
            self.server.jobs = jobs
            self.assertEqual(self.call("send", SID, TEXT)[1]["error_code"], "ETARGET")
        self.server.jobs = [original]
        for proto, queue_format in ((2, 1), (1, None), (1, 2)):
            self.server.proto, self.server.carried_prompts_format = proto, queue_format
            self.assertEqual(self.call("send", SID, TEXT)[1]["error_code"], "EPROTO")
        self.server.proto, self.server.carried_prompts_format = 1, 1
        self.server.directory.chmod(0o755)
        self.assertEqual(self.call("send", SID, TEXT)[1]["error_code"], "EPATH")
        self.server.directory.chmod(0o700)
        self.key.chmod(0o644)
        self.assertEqual(self.call("send", SID, TEXT)[1]["error_code"], "EAUTHFILE")
        self.key.chmod(0o600)
        with patch.object(contract, "file_identity", side_effect=contract.UnsafeImage("writable by another user")):
            self.assertEqual(self.call("send", SID, TEXT)[1]["error_code"], "EPATH")
        self.assertEqual(self.reply_count(), 0)
        self.key.write_text("1" * 32)
        code, result = self.call("send", SID, TEXT, "--request-id", "skew-bad-key")
        self.assertEqual((code, result["error_code"], result["status"]), (4, "EAUTH", "rejected"))
        self.assertEqual(self.reply_count(), 1)

    def test_supervisor_image_unavailable_or_new_job_state_is_reported_not_refused(self):
        self.versions("2.1.323.1727", "2.1.323")
        self.server.jobs[0]["state"] = "running"  # Observed in a live 2.1.323 list; unknown to older reviews.
        with patch.object(contract, "process_image", side_effect=contract.ContractError("deleted by an update")):
            code, report = self.call("doctor", SID, "--json")
            self.assertEqual(code, 0, report)
            self.assertEqual(report["supervisor_image"], "unavailable")
            self.assertEqual(report["compatibility"], "negotiated-unreviewed-build")
            self.assertEqual(report["target"]["worker_image"], "unavailable")
            code, result = self.call("send", SID, TEXT)
        self.assertEqual(code, 0, result)
        self.assertTrue(result["accepted"])
        self.assertEqual(self.reply_count(), 1)

    def test_server_side_skew_refusal_after_a_race_is_rejected_without_retry(self):
        self.versions("2.1.323.1727", "2.1.323")
        self.server.mode = "ESKEW"
        code, result = self.call("send", SID, TEXT, "--request-id", "race")
        self.assertEqual((code, result["status"], result["error_code"]), (4, "rejected", "ESKEW"))
        self.server.mode = "ok"
        self.assertTrue(self.call("send", SID, TEXT, "--request-id", "race")[1]["duplicate_suppressed"])
        self.assertEqual(self.reply_count(), 1)


class ImageEvidenceTests(unittest.TestCase):
    def test_oversize_unreadable_and_unknown_images_are_unreviewed_not_errors(self):
        with tempfile.TemporaryDirectory(dir=os.path.realpath("/tmp")) as tmp:
            image = Path(tmp) / "future-image"
            image.write_bytes(b"function unrelated(){return 1}")
            image.chmod(0o700)
            with patch.object(contract, "attest_image", ORIGINAL_ATTEST):
                self.assertIsNone(contract.structure(image))
                with patch.object(contract, "MAX_IMAGE", 4):
                    self.assertIsNone(contract.structure(image))
                self.assertIsNone(contract.structure(Path(tmp) / "missing"))
            self.assertEqual(contract.locate(-1), (None, None))
            image.chmod(0o722)
            with self.assertRaises(contract.UnsafeImage):
                contract.file_identity(image)


if __name__ == "__main__":
    unittest.main()
