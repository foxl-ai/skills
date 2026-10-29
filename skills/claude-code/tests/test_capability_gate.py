"""Forward-compatibility and fail-closed regressions, synthetic fixtures only."""
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from test_native_send import IsolatedCase, SID, UUID, TEXT, SCRIPTS, helper, native, outbox
import cc_contract as contract


class CapabilityGateTests(IsolatedCase):
    def versions(self, cli, daemon, worker=None):
        (self.root / "version.txt").write_text("claude %s (Claude Code)" % cli)
        self.server.version = daemon
        self.server.jobs[0]["cliVersion"] = daemon if worker is None else worker

    def test_future_versions_with_attested_contract_send_once_all_states(self):
        for cli, daemon in (("2.1.312.1459", "2.1.312"), ("2.1.999.4321", "2.1.312"),
                            ("8.7.6000", "8.7.6000"), ("2.1.300", "8.7.6000")):
            self.versions(cli, daemon)
            for state, status in (("working", "busy"), ("done", "idle"), ("blocked", "waiting")):
                with self.subTest(cli=cli, daemon=daemon, state=state):
                    self.session.update(state=state, status=status)
                    self.set_sessions([self.session])
                    key = "future-%s-%s-%s" % (cli, daemon, state)
                    before = self.reply_count()
                    code, result = self.call("send", SID, TEXT, "--request-id", key)
                    self.assertEqual(code, 0)
                    self.assertEqual(result["sessionId"], UUID)
                    self.assertTrue(result["accepted"] and result["queued"])
                    self.assertFalse(result["observed"])
                    code, duplicate = self.call("send", UUID, TEXT, "--request-id", key)
                    self.assertEqual(code, 0)
                    self.assertTrue(duplicate["duplicate_suppressed"])
                    self.assertEqual(self.reply_count(), before + 1)
        self.assertTrue(all(c[0] in ("agents", "--version") for c in self.cli_calls()))

    def test_future_version_and_good_ping_without_structural_proof_refuse(self):
        self.versions("8.7.6000.1", "8.7.6000")
        with patch.object(contract, "attest_image", side_effect=contract.ContractError("changed queue structure")), \
                patch.object(native.NativeReply, "_auth", side_effect=AssertionError):
            code, result = self.call("doctor", SID, "--json")
        self.assertEqual((code, result["error_code"]), (4, "ECONTRACT"))
        self.assertIn("changed queue structure", result["note"])
        self.assertFalse(self.state.exists())
        self.assertEqual(self.reply_count(), 0)

    def test_malformed_negotiation_fails_before_auth(self):
        original = {"ok": True, "op": "ping", "version": "2.1.999", "proto": 1, "carriedPromptsFormat": 1}
        cases = [{**original, key: value} for key, values in (
            ("ok", [False, 1, None]), ("op", [None, "list"]),
            ("proto", [True, False, None, "1", 1.0, 2]),
            ("carriedPromptsFormat", [True, None, "1", 1.0, 0, 2]),
            ("version", [None, False, "2.1.999-custom", "2.1.999 2.1.998"])) for value in values]
        for response in cases:
            with self.subTest(response=response), patch.object(native.NativeReply, "_rpc", return_value=response), \
                    patch.object(native.NativeReply, "_auth", side_effect=AssertionError), \
                    patch.object(contract, "attest_image", side_effect=AssertionError):
                with self.assertRaises(native.BridgeError) as caught:
                    self.bridge(version="2.1.999.1").probe()
                self.assertEqual(caught.exception.code, "EPROTO")
                self.assertFalse(caught.exception.uncertain)
        self.assertEqual(self.server.calls, [])

    def test_bad_json_frames_and_duplicate_fields_are_never_negotiated(self):
        for value in (b'{"ok":true,"ok":true}', b'{"proto":1,"proto":2}',
                      b'{"proto":NaN}', b'{} trailing', b'\xff'):
            with self.subTest(value=value), self.assertRaises((ValueError, UnicodeError)):
                native.strict_json(value)

    def test_worker_version_skew_is_independent_of_cli_version(self):
        for cli in ("2.1.300", "2.1.312.1459", "9.0.8888.1234"):
            self.versions(cli, "2.1.312", "2.1.311")
            code, report = self.call("doctor", SID, "--json")
            self.assertEqual((code, report["error_code"]), (4, "ESKEW"))
        self.assertEqual(self.reply_count(), 0)

    def test_matching_worker_version_but_wrong_executable_is_refused(self):
        actual = contract.process_image
        # Use a real direct child so the pair check passes; the executable
        # attestation, not a version string, must catch an image mismatch.
        import subprocess
        child = subprocess.Popen([sys.executable, "-c", "import sys; print('ready',flush=True); sys.stdin.read()"],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            self.assertEqual(child.stdout.readline(), b"ready\n")
            self.session["pid"] = child.pid
            self.set_sessions([self.session])
            def mismatch(pid):
                return self.root / "different-image" if pid == child.pid else actual(pid)
            with patch.object(contract, "process_image", side_effect=mismatch):
                code, result = self.call("send", SID, TEXT)
            self.assertEqual((code, result["error_code"]), (4, "ECONTRACT"))
            self.assertEqual(self.reply_count(), 0)
        finally:
            child.terminate()
            child.wait(timeout=5)
            child.stdin.close()
            child.stdout.close()

    def test_target_revalidation_detects_reassigned_uuid_and_worker(self):
        for delta in ({"sessionId": "87654321-1234-5678-9abc-123456789abc"}, {"pid": 1}, {"state": "stopped"}):
            original = dict(self.server.jobs[0])
            bridge = self.bridge()
            bridge.prepare(self.session)
            self.server.jobs[0].update(delta)
            with self.assertRaises(native.BridgeError) as caught:
                bridge.reply(self.session, TEXT)
            self.assertFalse(caught.exception.uncertain)
            self.server.jobs[0] = original
        self.assertEqual(self.reply_count(), 0)

    def test_changed_protocol_between_prepare_and_reply_is_refused(self):
        bridge = self.bridge()
        bridge.prepare(self.session)
        self.server.carried_prompts_format = 2
        with self.assertRaises(native.BridgeError) as caught:
            bridge.reply(self.session, TEXT)
        self.assertEqual(caught.exception.code, "EPROTO")
        self.assertFalse(caught.exception.uncertain)
        self.assertEqual(self.reply_count(), 0)

    def test_receipts_survive_upgrade_even_when_new_contract_is_unavailable(self):
        self.versions("2.1.300", "2.1.300")
        self.assertEqual(self.call("send", SID, TEXT, "--request-id", "stable-action")[0], 0)
        self.versions("8.7.6000.1", "8.7.6000")
        with patch.object(contract, "attest_image", side_effect=AssertionError("no new attempt")):
            code, result = self.call("send", SID, TEXT, "--request-id", "stable-action")
        self.assertEqual(code, 0)
        self.assertTrue(result["duplicate_suppressed"])
        box = outbox.Outbox(str(self.state), str(self.config))
        with box.mutation_guard():
            path, receipt = box.request(self.session, "reserved", "unknown-stable-action")
            outbox.atomic_save(path, receipt)
        with patch.object(contract, "attest_image", side_effect=AssertionError("no new attempt")):
            code, result = self.call("send", SID, "reserved", "--request-id", "unknown-stable-action")
        self.assertEqual(code, 5)
        self.assertTrue(result["duplicate_suppressed"])
        self.assertEqual(self.reply_count(), 1)

    def test_future_drop_and_ack_uncertainty_stays_deduplicated(self):
        self.versions("8.7.6000.1", "8.7.6000")
        for mode in ("drop", "bad-json", "unknown-ack", "EUNKNOWN", "EPEERUID", "ETOOLARGE"):
            self.server.mode = mode
            key = "future-unknown-" + mode
            code, result = self.call("send", SID, TEXT, "--request-id", key)
            self.assertEqual((code, result["status"]), (5, "unknown"))
            before = self.reply_count()
            code, repeat = self.call("send", SID, TEXT, "--request-id", key)
            self.assertEqual(code, 5)
            self.assertTrue(repeat["duplicate_suppressed"])
            self.assertEqual(self.reply_count(), before)

    def test_platform_negatives_refuse_without_probe_or_state(self):
        for platform in ("win32", "freebsd14", "sunos5"):
            with self.subTest(platform=platform), patch.object(native.sys, "platform", platform), \
                    patch.object(native.socket, "socket", side_effect=AssertionError):
                with self.assertRaises(native.BridgeError) as caught:
                    self.bridge()
                self.assertEqual(caught.exception.code, "EPLATFORM")
        with patch.object(native.os, "geteuid", return_value=os.getuid() + 1):
            with self.assertRaises(native.BridgeError) as caught:
                self.bridge()
            self.assertEqual(caught.exception.code, "EPLATFORM")
        self.assertFalse(self.state.exists())

    def test_process_start_change_at_final_write_is_refused(self):
        bridge = self.bridge()
        bridge.prepare(self.session)
        original_pair, original_attest = native.validate_process_pair, bridge._attest
        final_attestation_finished = False
        def mark_final(worker=None, repl=None):
            nonlocal final_attestation_finished
            result = original_attest(worker, repl)
            if worker is not None:
                final_attestation_finished = True
            return result
        def change_last(worker, repl):
            if final_attestation_finished:
                return ((worker, 0, os.getuid(), 'recycled-start'),)
            return original_pair(worker, repl)
        with patch.object(bridge, '_attest', side_effect=mark_final), \
                patch.object(native, 'validate_process_pair', side_effect=change_last):
            with self.assertRaises(native.BridgeError) as caught:
                bridge.reply(self.session, TEXT)
        self.assertTrue(final_attestation_finished)
        self.assertEqual(caught.exception.code, 'ECHANGED')
        self.assertFalse(caught.exception.uncertain)
        self.assertEqual(self.reply_count(), 0)

    def test_provenance_change_after_attestation_is_not_silently_reprobed(self):
        bridge = self.bridge()
        bridge.prepare(self.session)
        with patch.object(contract, "file_identity", return_value=(0, 0, 0, 0, 0)):
            with self.assertRaises(native.BridgeError) as caught:
                bridge.reply(self.session, TEXT)
        self.assertEqual(caught.exception.code, "ECONTRACT")
        self.assertFalse(caught.exception.uncertain)
        self.assertEqual(self.reply_count(), 0)


class StructuralLexerTests(unittest.TestCase):
    def test_alpha_renaming_and_horizontal_spacing_but_not_behavior(self):
        a = 'function sample(input){if(input.ready)return verify(input.auth);return false}'
        b = 'function other(thing) { if(thing.ready) return check(thing.auth);return false }'
        self.assertEqual(contract.canonical(a), contract.canonical(b))
        for left, right in (
                ('function f(x){let a=x,b=x;return b}', 'function g(y){let c=y,d=y;return d}'),
                ('function f(x){return `v=${x.ready}`}', 'function g(y){return `v=${y.ready}`}'),
                ('async reply(x,y){let a=x,b=y;return b}', 'async reply(c,d){let z=c,w=d;return w}')):
            self.assertEqual(contract.canonical(left), contract.canonical(right))
        for changed in (a.replace('ready', 'disabled'), a.replace('return false', 'return true'),
                        a.replace('verify(input.auth)', 'verify(input.text)'),
                        a.replace('return verify', 'return\nverify'), a.replace('if(', 'if(!')):
            self.assertNotEqual(contract.canonical(a), contract.canonical(changed))

    def test_operator_boundaries_properties_and_identifier_correlation_are_preserved(self):
        for left, right in (("return x++ + y", "return x+ + +y"),
                            ("return x===y", "return x== =y"),
                            ("return x?.safe", "return x?.unsafe"),
                            ("return check(x,x)", "return check(x,y)")):
            self.assertNotEqual(contract.canonical(left), contract.canonical(right))

    def test_runtime_dependencies_shorthand_and_method_names_are_not_aliases(self):
        pairs = (
            ('function f(x){return Number(x)}', 'function g(y){return String(y)}'),
            ('function f(x){return JSON.parse(x)}', 'function g(y){return eval.parse(y)}'),
            ('function f(x){return setTimeout(x,1)}', 'function g(y){return setImmediate(y,1)}'),
            ('function f(x){return {x}}', 'function g(y){return {y}}'),
            ('function f(x){return {\n x\n}}', 'function g(y){return {\n y\n}}'),
            ('function f(x){let {safe}=x;return safe}', 'function g(y){let {unsafe}=y;return unsafe}'),
            ('return {safe(x){return x}}', 'return {unsafe(y){return y}}'),
            ('return {safe(x)\n{return x}}', 'return {unsafe(y)\n{return y}}'),
            ('return {async safe(x){return x}}', 'return {async unsafe(y){return y}}'),
        )
        for left, right in pairs:
            with self.subTest(left=left):
                self.assertNotEqual(contract.canonical(left), contract.canonical(right))

    def test_numeric_literals_are_preserved_as_literals_not_identifier_aliases(self):
        for left, right in (('0x1', '0x2'), ('0b10', '0b11'), ('0o10', '0o11'),
                            ('1e3', '1e4'), ('1E+3', '1E-3'), ('1n', '1'), ('.1', '.2')):
            self.assertNotEqual(contract.canonical('return ' + left), contract.canonical('return ' + right))
        for invalid in ('0x', '1e', '1e+', '0b2', '12nonsense', '1_000'):
            with self.subTest(invalid=invalid), self.assertRaises(contract.ContractError):
                contract.canonical('return ' + invalid)

    def test_unknown_lexical_forms_do_not_silently_normalize(self):
        for value in ('return /regex/', 'return /* x */ value', 'return // x\nvalue',
                      'return `nested ${call({x:1})}`', 'return "unfinished'):
            with self.subTest(value=value), self.assertRaises(contract.ContractError):
                contract.canonical(value)

    def test_missing_duplicated_truncated_and_oversize_fragments_refuse(self):
        marker = rb'function demo\(x\)\{'
        sample = b'function demo(x){return x.ready}'
        self.assertEqual(contract.fragment(sample, marker, "fixture"), sample.decode())
        for data in (b'nothing', sample + sample, sample[:-1], b'function demo(x){' + b'x' * contract.MAX_FRAGMENT):
            with self.subTest(length=len(data)), self.assertRaises(contract.ContractError):
                contract.fragment(data, marker, "fixture")

    def test_unsafe_image_and_unrecognized_python_source_are_not_accepted(self):
        with __import__('tempfile').TemporaryDirectory(dir=os.path.realpath('/tmp')) as tmp:
            p = Path(tmp) / 'fixture-image'
            p.write_bytes(b'not a supported image')
            p.chmod(0o777)
            with self.assertRaises(contract.ContractError):
                contract.attest_image(p)
            p.chmod(0o700)
            with self.assertRaises(contract.ContractError):
                contract.attest_image(p)
        with self.assertRaises(contract.ContractError):
            contract.attest_image(contract.process_image(os.getpid()))

    def test_kernel_image_lookup_rejects_unknown_pid_and_platform(self):
        for pid in (True, 0, -1, None):
            with self.assertRaises(contract.ContractError):
                contract.process_image(pid)
        with patch.object(contract.sys, 'platform', 'unsupported'):
            with self.assertRaises(contract.ContractError):
                contract.process_image(os.getpid())
