"""Offline deterministic tests. Temporary CLI, config, receipts and real Unix socket.

No model, real Claude process, user session or production credential is accessed.
"""
import argparse
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import cc_native_reply as native
import cc_outbox as outbox
import cc_sessions as helper

SID = "abcdef12"
UUID = "12345678-1234-5678-9abc-123456789abc"
FAKE_KEY = "0" * 32
TEXT = "Keep working, and add a regression test. $(touch NO_SHELL)\nDo not open a second session."


class FakeSupervisor:
    def __init__(self, config, temp_root):
        digest = hashlib.sha256(str(config).encode()).hexdigest()[:8]
        self.directory = temp_root / ("cc-daemon-%s" % os.getuid()) / digest
        self.directory.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.directory.mkdir(mode=0o700)
        self.path = self.directory / "control.sock"
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(str(self.path))
        os.chmod(self.path, 0o700)
        self.sock.listen(5)
        self.sock.settimeout(0.1)
        self.calls = []
        self.error = None
        self.mode = "ok"
        self.version = "2.1.308"
        self.proto = 1
        self.jobs = [{"short": SID, "sessionId": UUID, "pid": os.getpid(), "backend": "daemon",
                      "cliVersion": self.version, "state": "working"}]
        self.closed = threading.Event()
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        while not self.closed.is_set():
            try:
                conn, _ = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                try:
                    conn.settimeout(1)
                    data = b""
                    while b"\n" not in data:
                        chunk = conn.recv(65536)
                        if not chunk:
                            break
                        data += chunk
                    if not data:
                        continue
                    req = json.loads(data.split(b"\n", 1)[0])
                    # Record no credentials or raw prompt in any test logs.
                    self.calls.append({key: value for key, value in req.items() if key not in ("auth", "text")})
                    op = req["op"]
                    if op == "ping":
                        reply = {"ok": True, "op": op, "version": self.version,
                                 "proto": self.proto, "carriedPromptsFormat": 1}
                    elif op == "list":
                        reply = {"ok": True, "op": op, "jobs": self.jobs}
                    elif op == "reply":
                        if req.get("auth") != FAKE_KEY:
                            reply = {"ok": False, "code": "EAUTH", "error": "redacted"}
                        elif self.mode == "timeout":
                            time.sleep(0.18)
                            continue
                        elif self.mode == "drop":
                            continue
                        elif self.mode == "oversize":
                            conn.sendall(b"x" * (native.MAX_RESPONSE + 1))
                            continue
                        elif self.mode == "duplicate-json":
                            conn.sendall(b'{"ok":true,"ok":false,"op":"reply"}\n')
                            continue
                        elif self.mode == "bad-json":
                            conn.sendall(b"nonsense\n")
                            continue
                        elif self.mode == "unknown-ack":
                            reply = {"ok": True, "op": op, "surprise": True}
                        elif self.mode.startswith("E"):
                            reply = {"ok": False, "code": self.mode, "error": FAKE_KEY + TEXT}
                        else:
                            reply = {"ok": True, "op": op}
                    else:
                        self.error = "Mutation other than reply was attempted: " + op
                        reply = {"ok": False, "code": "EFORBIDDEN"}
                    conn.sendall(json.dumps(reply).encode() + b"\n")
                except (BrokenPipeError, ConnectionResetError, socket.timeout):
                    pass
                except Exception as exc:
                    self.error = type(exc).__name__

    def close(self):
        self.closed.set()
        self.sock.close()
        self.thread.join(2)


class IsolatedCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cc-tests-", dir=os.path.realpath("/tmp"))
        self.root = Path(self.tmp.name)
        self.config = self.root / "config"
        self.config.mkdir(mode=0o700)
        (self.config / "daemon").mkdir(mode=0o700)
        self.key = self.config / "daemon/control.key"
        self.key.write_text(FAKE_KEY)
        self.key.chmod(0o600)
        self.state = self.root / "state"
        self.server = FakeSupervisor(self.config, self.root / "sockets")
        self.session = {"id": SID, "sessionId": UUID, "pid": os.getpid(), "kind": "background",
                        "state": "working", "status": "busy", "name": "login regression", "cwd": str(self.root)}
        self.cli = self.root / "fake-claude"
        shutil.copy(Path(__file__).with_name("fake_cli.py"), self.cli)
        self.cli.chmod(0o700)
        (self.root / "version.txt").write_text("claude 2.1.309.1365 (ASBX Claude Code)")
        self.set_sessions([self.session])
        self.env = patch.dict(os.environ, {"FAKE_CC_ROOT": str(self.root)})
        self.env.start()
        self.patches = [patch.object(helper, "CLAUDE", str(self.cli)),
                        patch.object(helper, "CONFIG", str(self.config)), patch.object(helper, "STATE", str(self.state)),
                        patch.object(helper, "NativeReply", self.bridge)]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.env.stop()
        self.server.close()
        self.assertIsNone(self.server.error)
        self.tmp.cleanup()

    def bridge(self, config=None, version="2.1.309.1365", **kwargs):
        return native.NativeReply(config or str(self.config), version, timeout=0.1,
                                  temp_root=self.root / "sockets", **kwargs)

    def set_sessions(self, rows):
        (self.root / "sessions.json").write_text(json.dumps(rows))

    def call(self, *args):
        output = io.StringIO()
        with redirect_stdout(output):
            code = helper.main(list(args))
        return code, json.loads(output.getvalue())

    def reply_count(self):
        return sum(req["op"] == "reply" for req in self.server.calls)

    def cli_calls(self):
        path = self.root / "calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def legacy(self, sid=SID, target=None, pending=True, extra=None):
        self.state.mkdir(mode=0o700, exist_ok=True)
        row = {"id": sid, "target": target or sid, "items": []}
        if target:
            row["items"].append({"n": 1, "status": "delivered", "delivered_to": target, "message": "legacy"})
        if pending:
            row["items"].append({"n": 2, "status": "pending", "message": "never replay"})
        row.update(extra or {})
        path = self.state / (sid + ".json")
        path.write_text(json.dumps(row))
        path.chmod(0o600)
        return path


class SendTests(IsolatedCase):
    def test_working_and_idle_use_same_id_without_stop_or_resume(self):
        for index, status in enumerate(("busy", "idle", "waiting")):
            self.session["status"] = status
            self.session["state"] = "done" if status == "idle" else "working"
            self.set_sessions([self.session])
            code, result = self.call("send", SID, TEXT, "--request-id", "turn-%s" % index)
            self.assertEqual(code, 0)
            self.assertEqual(result["id"], SID)
            self.assertEqual(result["sessionId"], UUID)
            self.assertTrue(result["queued"])
            self.assertTrue(result["accepted"])
            self.assertFalse(result["observed"])
        self.assertEqual(self.reply_count(), 3)
        self.assertTrue(all(req["short"] == SID and req["nextTurn"] for req in self.server.calls if req["op"] == "reply"))
        self.assertTrue(all(args[:1] in (["--version"], ["agents"]) for args in self.cli_calls()))

    def test_identical_retry_is_suppressed_even_under_name_or_uuid(self):
        self.assertEqual(self.call("send", SID, TEXT)[0], 0)
        for ref in (SID, "login", UUID):
            code, result = self.call("send", ref, TEXT)
            self.assertEqual(code, 0)
            self.assertTrue(result["duplicate_suppressed"])
        self.assertEqual(self.reply_count(), 1)
        receipts = list((self.state / "native-replies-v1").glob("*.json"))
        self.assertEqual(len(receipts), 1)
        self.assertNotIn(TEXT, receipts[0].read_text())
        self.assertNotIn(FAKE_KEY, receipts[0].read_text())
        self.assertEqual(stat.S_IMODE(receipts[0].stat().st_mode), 0o600)

    def test_explicit_id_conflict_is_refused_and_distinct_intent_is_allowed(self):
        self.call("send", SID, TEXT, "--request-id", "user-turn-1")
        code, result = self.call("send", SID, "different text", "--request-id", "user-turn-1")
        self.assertEqual(code, 4)
        self.assertEqual(result["error_code"], "EREQUEST")
        self.call("send", SID, TEXT, "--request-id", "user-turn-2")
        self.assertEqual(self.reply_count(), 2)

    def test_unknown_timeout_drop_and_unrecognized_ack_are_never_retried(self):
        for mode in ("timeout", "drop", "bad-json", "duplicate-json", "unknown-ack", "oversize", "EUNREVIEWED"):
            with self.subTest(mode=mode):
                self.server.mode = mode
                request_id = "mode-" + mode
                code, result = self.call("send", SID, TEXT, "--request-id", request_id)
                self.assertEqual(code, 5)
                self.assertEqual(result["status"], "unknown")
                self.assertIsNone(result["accepted"])
                before = self.reply_count()
                code, second = self.call("send", SID, TEXT, "--request-id", request_id)
                self.assertEqual(code, 5)
                self.assertTrue(second["duplicate_suppressed"])
                self.assertEqual(before, self.reply_count())
                self.assertNotIn(FAKE_KEY, json.dumps(result))
                self.assertNotIn(TEXT, json.dumps(result))

    def test_known_auth_and_protocol_refusals_are_rejected_not_accepted(self):
        for mode in ("EAUTH", "EPROTO", "ESTARTING", "ERESPAWNING", "ESKEW", "ENOJOB", "ENOREPLY"):
            self.server.mode = mode
            code, result = self.call("send", SID, TEXT, "--request-id", mode)
            self.assertEqual(code, 4)
            self.assertFalse(result["accepted"])
            self.assertEqual(result["status"], "rejected")
            before = self.reply_count()
            self.call("send", SID, TEXT, "--request-id", mode)
            self.assertEqual(self.reply_count(), before)
            self.assertNotIn(FAKE_KEY, json.dumps(result))

    def test_ambiguous_name_duplicate_id_and_uuid_refuse_before_rpc(self):
        other = {**self.session, "id": "01234567", "sessionId": "87654321-1234-5678-9abc-123456789abc"}
        for rows, ref in (([self.session, other], "login"), ([self.session, self.session], SID),
                          ([self.session, {**other, "sessionId": UUID}], UUID)):
            self.set_sessions(rows)
            with self.assertRaises(SystemExit):
                self.call("send", ref, TEXT)
        self.assertEqual(self.reply_count(), 0)

    def test_legacy_copy_alias_never_redirects_and_history_cannot_split_delivery(self):
        old = "00000001"
        self.legacy(old, target=SID)
        self.legacy(SID, pending=False)  # The old queue_key_for would ignore the original queue here.
        self.set_sessions([self.session, {**self.session, "id": old}])
        code, result = self.call("send", old, TEXT)
        self.assertEqual(code, 4)
        self.assertEqual(result["error_code"], "ESTALEID")
        self.assertEqual(self.reply_count(), 0)
        self.assertEqual(self.call("send", SID, TEXT)[0], 0)
        _, view = self.call("queue", SID, "--json")
        self.assertEqual(len(view["legacy"]), 2)
        self.assertEqual(len(view["items"]), 1)
        self.assertFalse(view["automatic_replay"])
        self.assertEqual(self.reply_count(), 1)

    def test_legacy_pending_history_does_not_replay_on_status_or_queue(self):
        path = self.legacy()
        before = path.read_bytes()
        self.call("queue", SID, "--json")
        with patch.object(helper, "git_summary", return_value=None):
            self.call("status", SID, "--json")
        self.assertEqual(before, path.read_bytes())
        self.assertEqual(self.reply_count(), 0)
        self.assertEqual(self.call("send", SID, TEXT)[0], 0)
        self.assertEqual(before, path.read_bytes())
        self.assertEqual(self.reply_count(), 1)

    def test_active_old_watcher_blocks_send_and_stop(self):
        self.legacy(extra={"watcher_pid": os.getpid()})
        for command in (("send", SID, TEXT), ("stop", SID)):
            code, result = self.call(*command)
            self.assertEqual(code, 4)
            self.assertEqual(result["error_code"], "ELEGACY")
        self.assertFalse(any(args[0] == "stop" for args in self.cli_calls()))
        self.assertEqual(self.reply_count(), 0)

    def test_stop_cancels_legacy_pending_and_never_resurrects(self):
        old = "00000002"
        path = self.legacy(old, target=SID)
        code, result = self.call("stop", SID)
        self.assertEqual(code, 0)
        self.assertEqual(result["legacy_cancelled"], 1)
        self.assertEqual(json.loads(path.read_text())["items"][-1]["status"], "cancelled")
        self.call("queue", SID, "--json")
        with self.assertRaises(SystemExit) as stopped:
            self.call("_watch", old)
        self.assertEqual(stopped.exception.code, 4)
        self.assertEqual(self.reply_count(), 0)
        self.assertEqual([call for call in self.cli_calls() if call[0] not in ("agents", "--version")], [["stop", SID]])

    def test_non_posix_status_and_stop_do_not_use_posix_receipt_calls(self):
        box = outbox.Outbox(str(self.state), str(self.config))
        with patch.object(outbox.os, "name", "nt"), patch.object(outbox, "checked_read", side_effect=AssertionError):
            view = box.view(self.session)
            self.assertFalse(view["supported"])
            self.assertEqual(view["items"], [])
        output = io.StringIO()
        with patch.object(helper.os, "name", "nt"), patch.object(helper, "find", return_value=self.session), \
                patch.object(helper, "run", return_value=(0, "", "")) as run, \
                patch.object(helper, "Outbox", side_effect=AssertionError), redirect_stdout(output):
            code = helper.cmd_stop(argparse.Namespace(ref=SID))
        self.assertEqual(code, 0)
        run.assert_called_once_with([helper.CLAUDE, "stop", SID])
        self.assertTrue(json.loads(output.getvalue())["stopped"])
        self.assertEqual(self.reply_count(), 0)

    def test_retired_options_refuse_without_cli_calls(self):
        for option in (("--force",), ("--no-queue",), ("--expire-after", "10")):
            code, result = self.call("send", SID, TEXT, *option)
            self.assertEqual(code, 4)
            self.assertEqual(result["error_code"], "ELEGACYOPTION")
        self.assertEqual(self.cli_calls(), [])

    def test_spawn_and_start_are_the_only_new_session_paths(self):
        subprocess.run(["git", "init", "--quiet", str(self.root / "project")], check=True)
        for name in ("start", "spawn"):
            code, result = self.call(name, "--cwd", str(self.root / "project"), "--name", "test task",
                                     "--", TEXT)
            self.assertEqual(code, 0)
            self.assertTrue(result["created_new"])
            self.assertIsNotNone(result["worktree"])
        creates = [args for args in self.cli_calls() if args[0] == "--bg"]
        self.assertEqual(len(creates), 2)
        self.assertTrue(all("-w" in args and "--dangerously-skip-permissions" in args for args in creates))
        self.assertTrue(all(args[-1] == TEXT and "--resume" not in args for args in creates))
        self.assertFalse((self.root / "NO_SHELL").exists())
        self.assertEqual(self.reply_count(), 0)

    def test_prewrite_crash_reservation_prevents_resend(self):
        box = outbox.Outbox(str(self.state), str(self.config))
        with box.mutation_guard():
            path, receipt = box.request(self.session, TEXT)
            outbox.atomic_save(path, receipt)
        code, result = self.call("send", SID, TEXT)
        self.assertEqual(code, 5)
        self.assertTrue(result["duplicate_suppressed"])
        self.assertEqual(self.reply_count(), 0)

    def test_failed_ack_receipt_write_stays_unknown(self):
        real_save = helper.atomic_save
        writes = []
        def broken(path, receipt):
            writes.append(path)
            if len(writes) == 2:
                raise OSError("fixture failure")
            return real_save(path, receipt)
        with patch.object(helper, "atomic_save", broken):
            code, result = self.call("send", SID, TEXT)
        self.assertEqual(code, 5)
        self.assertEqual(result["error_code"], "ERECEIPT")
        self.assertEqual(self.call("send", SID, TEXT)[0], 5)
        self.assertEqual(self.reply_count(), 1)

    def test_concurrent_send_guard_refuses_without_duplicate(self):
        box = outbox.Outbox(str(self.state), str(self.config))
        with box.mutation_guard():
            code, result = self.call("send", SID, TEXT)
        self.assertEqual(code, 4)
        self.assertEqual(result["error_code"], "ELOCKED")
        self.assertEqual(self.reply_count(), 0)

    def test_retired_watcher_subprocess_cannot_run_cli(self):
        env = {**os.environ, "HOME": str(self.root), "CLAUDE_CONFIG_DIR": str(self.config),
               "CC_SESSIONS_STATE": str(self.state), "CLAUDE_BIN": str(self.cli)}
        process = subprocess.run([sys.executable, str(SCRIPTS / "cc_sessions.py"), "_watch", SID],
                                 env=env, capture_output=True, text=True, timeout=5)
        self.assertEqual(process.returncode, 4)
        self.assertIn("retired", process.stderr)
        self.assertEqual(self.cli_calls(), [])

    def test_full_subprocess_send_and_retry_use_only_isolated_supervisor(self):
        runner = Path(__file__).with_name("isolated_runner.py")
        env = {**os.environ, "HOME": str(self.root), "CLAUDE_CONFIG_DIR": str(self.config),
               "CC_SESSIONS_STATE": str(self.state), "CLAUDE_BIN": str(self.cli),
               "FAKE_CC_SOCKETS": str(self.root / "sockets")}
        for duplicate in (False, True):
            process = subprocess.run([sys.executable, str(runner), "send", SID, TEXT,
                                      "--request-id", "subprocess-once"], env=env,
                                     capture_output=True, text=True, timeout=10)
            self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
            self.assertEqual(json.loads(process.stdout)["duplicate_suppressed"], duplicate)
        self.assertEqual(self.reply_count(), 1)


class TransportTests(IsolatedCase):
    def test_actual_worker_parent_and_repl_child_contract(self):
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        try:
            self.session["pid"] = child.pid
            self.set_sessions([self.session])
            # Real supervisor list reports the worker, CLI list reports its child.
            self.server.jobs[0]["pid"] = os.getpid()
            code, result = self.call("send", SID, TEXT, "--request-id", "parent-child")
            self.assertEqual(code, 0)
            self.assertTrue(result["accepted"])
            self.assertEqual(self.reply_count(), 1)
        finally:
            child.terminate()
            child.wait(timeout=5)

    def test_unrelated_or_changed_process_pair_refuses_before_reply(self):
        self.server.jobs[0]["pid"] = 1  # Not a same-user direct parent of this test.
        self.assertEqual(self.call("send", SID, TEXT)[0], 4)
        self.assertEqual(self.reply_count(), 0)
        self.server.jobs[0]["pid"] = os.getpid()
        bridge = self.bridge()
        bridge.prepare(self.session)
        with patch.object(native, "validate_process_pair", return_value=((999, 998, os.getuid(), "changed"),)):
            with self.assertRaises(native.BridgeError) as result:
                bridge.reply(self.session, TEXT)
        self.assertEqual(result.exception.code, "ECHANGED")
        self.assertFalse(result.exception.uncertain)
        self.assertEqual(self.reply_count(), 0)

    def test_no_native_files_are_changed_and_bridge_is_single_attempt(self):
        before = {p.relative_to(self.config): p.read_bytes() for p in self.config.rglob("*") if p.is_file()}
        bridge = self.bridge()
        bridge.prepare(self.session)
        bridge.reply(self.session, TEXT)
        with self.assertRaises(native.BridgeError):
            bridge.reply(self.session, TEXT)
        self.assertEqual(self.reply_count(), 1)
        self.assertEqual(before, {p.relative_to(self.config): p.read_bytes() for p in self.config.rglob("*") if p.is_file()})

    def test_unsafe_state_inside_native_config_is_never_created(self):
        state = self.config / "do-not-create"
        with patch.object(helper, "STATE", str(state)):
            code, result = self.call("send", SID, TEXT)
        self.assertEqual(result["error_code"], "ESTATE")
        self.assertFalse(state.exists())
        self.assertEqual(self.reply_count(), 0)

    def test_invalid_receipt_and_unavailable_socket_do_not_retry(self):
        self.call("send", SID, TEXT)
        receipt = next((self.state / "native-replies-v1").glob("*.json"))
        receipt.write_text("not json")
        self.assertEqual(self.call("send", SID, TEXT)[0], 4)
        self.assertEqual(self.reply_count(), 1)
        self.server.close()
        self.server.path.unlink()
        code, result = self.call("send", SID, "a separate explicit request")
        self.assertEqual(code, 4)
        self.assertEqual(self.reply_count(), 1)
        self.assertTrue(all(args[0] in ("agents", "--version") for args in self.cli_calls()))

    def test_false_auth_key_is_refused_and_never_logged(self):
        self.key.write_text("1" * 32)
        code, result = self.call("send", SID, TEXT)
        self.assertEqual(code, 4)
        self.assertEqual(result["error_code"], "EAUTH")
        self.assertNotIn("1" * 32, json.dumps(result))
        self.assertFalse(result["accepted"])

    def test_legacy_cycle_and_branch_both_refuse(self):
        old = "00000001"
        self.legacy(old, target=SID)
        current = self.legacy(SID, target=old)
        self.assertEqual(self.call("send", SID, TEXT)[1]["error_code"], "EALIAS")
        current.unlink()
        row = {"id": SID, "target": SID, "items": [
            {"n": 1, "status": "delivered", "delivered_to": old},
            {"n": 2, "status": "delivered", "delivered_to": "00000003"}]}
        self.legacy(SID, pending=False, extra=row)
        self.assertEqual(self.call("send", SID, TEXT)[1]["error_code"], "EALIAS")
        self.assertEqual(self.reply_count(), 0)

    def test_read_only_doctor_supports_observed_cli_daemon_skew(self):
        code, result = self.call("doctor", SID, "--json")
        self.assertEqual(code, 0)
        self.assertEqual(result["cli_version"], "2.1.309.1365")
        self.assertEqual(result["daemon_version"], "2.1.308")
        self.assertFalse(result["auth_verified"])
        self.assertTrue(result["peer_verified"])
        self.assertTrue(all(call["op"] in ("ping", "list") for call in self.server.calls))
        self.assertFalse(self.state.exists())

    def test_unknown_cli_daemon_and_protocol_fail_closed(self):
        (self.root / "version.txt").write_text("claude 2.1.300")
        code, result = self.call("send", SID, TEXT)
        self.assertEqual(result["error_code"], "EVERSION")
        (self.root / "version.txt").write_text("claude 2.1.309.1365")
        self.server.version = "2.1.999"
        code, result = self.call("send", SID, TEXT)
        self.assertEqual(result["error_code"], "EVERSION")
        self.server.version = "2.1.308"
        self.server.proto = 2
        code, result = self.call("send", SID, TEXT)
        self.assertEqual(result["error_code"], "EPROTO")
        self.assertEqual(self.reply_count(), 0)

    def test_unknown_old_skewed_and_stopped_workers_fail_closed(self):
        for version in ("2.1.300", "2.1.309", "unrecognized"):
            self.server.jobs[0]["cliVersion"] = version
            code, result = self.call("send", SID, TEXT)
            self.assertEqual(code, 4)
            self.assertEqual(result["error_code"], "ESKEW")
        self.server.jobs[0]["cliVersion"] = "2.1.308"
        self.session["pid"] = None
        self.session["state"] = "stopped"
        self.set_sessions([self.session])
        self.assertEqual(self.call("send", SID, TEXT)[0], 4)
        self.assertEqual(self.reply_count(), 0)

    def test_duplicate_mismatched_peer_and_exited_targets_fail_closed(self):
        original = dict(self.server.jobs[0])
        for changed in ([original, original], [{**original, "sessionId": "changed"}],
                        [{**original, "backend": "peer"}], [{**original, "dying": True}], []):
            self.server.jobs = changed
            self.assertEqual(self.call("send", SID, TEXT)[0], 4)
        self.assertEqual(self.reply_count(), 0)

    def test_auth_file_unsafe_modes_symlink_missing_and_bad_format(self):
        for mode in (0o644, 0o666):
            self.key.chmod(mode)
            self.assertEqual(self.call("send", SID, TEXT)[0], 4)
        self.key.chmod(0o600)
        self.key.write_text("bad format")
        self.assertEqual(self.call("send", SID, TEXT)[0], 4)
        self.key.unlink()
        self.assertEqual(self.call("send", SID, TEXT)[0], 4)
        other = self.root / "other-key"
        other.write_text(FAKE_KEY)
        other.chmod(0o600)
        self.key.symlink_to(other)
        self.assertEqual(self.call("send", SID, TEXT)[0], 4)
        self.assertEqual(self.reply_count(), 0)

    def test_unsafe_socket_dir_file_and_wrong_peer_are_refused(self):
        self.server.directory.chmod(0o755)
        self.assertEqual(self.call("send", SID, TEXT)[0], 4)
        self.server.directory.chmod(0o700)
        self.server.path.chmod(0o777)
        self.assertEqual(self.call("send", SID, TEXT)[0], 4)
        self.server.path.chmod(0o700)
        with patch.object(native, "peer_identity", side_effect=native.BridgeError("EPEER", "wrong peer")):
            self.assertEqual(self.call("send", SID, TEXT)[0], 4)
        self.assertEqual(self.reply_count(), 0)

    def test_changed_socket_after_probe_prevents_mutation(self):
        bridge = self.bridge()
        bridge.prepare(self.session)
        os.chmod(self.server.path, 0o600)  # ctime/identity validation notices replacement or mutation.
        with self.assertRaises(native.BridgeError) as result:
            bridge.reply(self.session, TEXT)
        self.assertFalse(result.exception.uncertain)
        self.assertEqual(self.reply_count(), 0)


class EvalTests(IsolatedCase):
    def test_three_realistic_prompts_route_deterministically(self):
        spec = json.loads((SCRIPTS.parent / "evals/evals.json").read_text())
        self.assertEqual(len(spec["evals"]), 3)
        project = self.root / "eval-project"
        subprocess.run(["git", "init", "--quiet", str(project)], check=True)
        for case in spec["evals"]:
            with self.subTest(prompt=case["id"]):
                route = [str(project) if arg == "<isolated-project>" else arg for arg in case["route"]]
                if case.get("fixture") == "unknown receipt already reserved":
                    box = outbox.Outbox(str(self.state), str(self.config))
                    with box.mutation_guard():
                        path, receipt = box.request(self.session, route[2], route[4])
                        outbox.atomic_save(path, receipt)
                before = self.reply_count()
                code, result = self.call(*route)
                for key, value in case["expect"].items():
                    if key == "exit":
                        self.assertEqual(code, value)
                    elif key == "created_new":
                        self.assertEqual(result.get(key, False), value)
                    elif key == "reply_attempts":
                        self.assertEqual(self.reply_count() - before, value)
                    else:
                        self.assertEqual(result[key], value)
                self.assertNotIn("--resume", json.dumps(self.cli_calls()))


if __name__ == "__main__":
    unittest.main()
