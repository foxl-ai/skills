"""Regression tests for agy_sessions.py against a fake agy. No model, network or real agy state.

Run from the repository root:
    python3 -B -m unittest discover -s skills/antigravity-cli/tests -v
"""
import importlib.util
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
HELPER = os.path.join(HERE, "..", "scripts", "agy_sessions.py")
FAKE = os.path.join(HERE, "fake_agy.py")


def load_module():
    spec = importlib.util.spec_from_file_location("agy_sessions_under_test", HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(cwd, *args):
    return subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True, check=True).stdout.strip()


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = os.path.realpath(tempfile.mkdtemp(prefix="agy-sessions-test-"))
        cls.repo = os.path.join(cls.root, "repo")
        os.makedirs(os.path.join(cls.repo, "pkg", "sub"))
        with open(os.path.join(cls.repo, "README.md"), "w") as f:
            f.write("test repo\n")
        with open(os.path.join(cls.repo, "pkg", "sub", "keep.txt"), "w") as f:
            f.write("keep\n")
        git(cls.repo, "init", "-q")
        git(cls.repo, "add", "-A")
        git(cls.repo, "commit", "-q", "-m", "init")
        os.chmod(FAKE, 0o755)

    @classmethod
    def tearDownClass(cls):
        for wt in git(cls.repo, "worktree", "list", "--porcelain").splitlines():
            if wt.startswith("worktree ") and wt[9:] != cls.repo:
                subprocess.run(["git", "-C", cls.repo, "worktree", "remove", "--force", wt[9:]],
                               capture_output=True)
        shutil.rmtree(cls.root, ignore_errors=True)

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="t-", dir=self.root)
        self.state = os.path.join(self.tmp, "state")
        self.store = os.path.join(self.tmp, "agy-data")
        os.makedirs(os.path.join(self.store, "conversations"))
        self.env = dict(os.environ, AGY_BIN=FAKE, AGY_SESSIONS_STATE=self.state, AGY_DATA_DIR=self.store,
                        FAKE_AGY_STORE=self.store, PYTHONDONTWRITEBYTECODE="1")
        for k in ("FAKE_AGY_HELP", "FAKE_AGY_REPORT_CWD", "XDG_STATE_HOME"):
            self.env.pop(k, None)
        self._procs = []

    def tearDown(self):
        for p in self._procs:
            if p.poll() is None:
                p.kill()

    def run_helper(self, *args, env=None, timeout=90):
        p = subprocess.run([sys.executable, "-B", HELPER] + list(args), capture_output=True, text=True,
                           env=env or self.env, timeout=timeout, stdin=subprocess.DEVNULL)
        try:
            body = json.loads(p.stdout)
        except ValueError:
            body = p.stdout
        return p.returncode, body

    def spawn(self, task, *extra, cwd=None):
        code, body = self.run_helper("spawn", "--cwd", cwd or self.repo, *extra, "--", task)
        self.assertEqual(code, 0, body)
        return body

    def wait_state(self, sid, states=("done",), timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            code, body = self.run_helper("status", sid, "--json")
            if body["state"] in states:
                return body
            time.sleep(0.3)
        self.fail("session %s never reached %s; last: %s" % (sid, states, body))

    def wait_recorded(self, sid, timeout=20):
        """Wait until the fake agy has recorded the turn in its conversation store."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            cid = self.session(sid).get("conversation_id")
            if cid and os.path.exists(os.path.join(self.store, "conversations", cid + ".db")):
                return cid
            time.sleep(0.1)
        self.fail("conversation never recorded")

    def session(self, sid):
        with open(os.path.join(self.state, "sessions", sid, "session.json")) as f:
            return json.load(f)

    def fake_calls(self, sid, n):
        path = os.path.join(self.state, "sessions", sid, "turns", str(n), "agy.log")
        with open(path) as f:
            return [json.loads(l) for l in f]

    def conv(self, cid):
        with open(os.path.join(self.store, "conversations", cid + ".db")) as f:
            return json.load(f)


class IsolationTests(Base):
    def test_spawn_creates_distinct_branch_and_worktree(self):
        body = self.spawn("make a file WRITE=agy-made.txt", "--name", "Isolation check")
        self.assertEqual(body["isolation"], "worktree")
        self.assertTrue(body["branch"].startswith("agy/isolation-check-"))
        self.assertNotEqual(os.path.realpath(body["cwd"]), self.repo)
        done = self.wait_state(body["id"])
        self.assertIn("result: pong", done["headline"])
        self.assertTrue(os.path.exists(os.path.join(body["worktree"], "agy-made.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.repo, "agy-made.txt")), "origin checkout was edited")
        self.assertEqual(git(body["worktree"], "rev-parse", "--abbrev-ref", "HEAD"), body["branch"])
        self.assertEqual(self.fake_calls(body["id"], 1)[0]["cwd"], body["cwd"])

    def test_concurrent_spawns_never_collide(self):
        results, errors = [], []

        def go():
            try:
                code, b = self.run_helper("spawn", "--cwd", self.repo, "--name", "same name", "--", "SLEEP=1 hi")
                (results if code == 0 else errors).append(b)
            except Exception as e:  # pragma: no cover
                errors.append(str(e))

        threads = [threading.Thread(target=go) for _ in range(4)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertFalse(errors, errors)
        self.assertEqual(len({r["id"] for r in results}), 4)
        self.assertEqual(len({r["branch"] for r in results}), 4)
        self.assertEqual(len({r["worktree"] for r in results}), 4)
        cids = {self.wait_state(r["id"])["conversation_id"] for r in results}
        self.assertEqual(len(cids), 4)
        code, body = self.run_helper("status", "same name")
        self.assertEqual((code, body["error"]), (4, "EAMBIGUOUS"))
        self.assertEqual(len(body["matches"]), 4)

    def test_subdirectory_maps_into_worktree(self):
        body = self.spawn("hi", cwd=os.path.join(self.repo, "pkg", "sub"))
        self.assertEqual(body["cwd"], os.path.join(body["worktree"], "pkg", "sub"))
        self.assertTrue(os.path.exists(os.path.join(body["cwd"], "keep.txt")))

    def test_no_worktree_is_explicit_and_edits_in_place(self):
        target = os.path.join(self.tmp, "inplace")
        shutil.copytree(self.repo, target, ignore=shutil.ignore_patterns(".git"))
        git(target, "init", "-q")
        body = self.spawn("WRITE=inplace.txt", "--no-worktree", cwd=target)
        self.assertEqual((body["isolation"], body["branch"], body["worktree"]), ("none", None, None))
        self.assertTrue(any("edits" in w for w in body["warnings"]))
        self.wait_state(body["id"])
        self.assertTrue(os.path.exists(os.path.join(target, "inplace.txt")))

    def test_non_git_folder_requires_explicit_opt_out(self):
        plain = os.path.join(self.tmp, "plain")
        os.makedirs(plain)
        code, body = self.run_helper("spawn", "--cwd", plain, "--", "hi")
        self.assertEqual((code, body["error"]), (2, "EISOLATION"))
        self.assertFalse(os.path.isdir(os.path.join(self.state, "sessions")) and
                         os.listdir(os.path.join(self.state, "sessions")), "a session was created")
        code, body = self.run_helper("spawn", "--cwd", plain, "--worktree", "--", "hi")
        self.assertEqual(code, 2)
        body = self.spawn("WRITE=x.txt", "--no-worktree", cwd=plain)
        self.assertEqual(body["isolation"], "none")
        self.assertTrue(any("no isolation" in w for w in body["warnings"]))
        self.wait_state(body["id"])

    def test_create_worktree_never_reuses_branch_or_path(self):
        mod = load_module()
        git(self.repo, "branch", "agy/existing-branch-test")
        try:
            with self.assertRaises(mod.Refusal) as cm:
                mod.create_worktree(self.repo, "agy/existing-branch-test", os.path.join(self.tmp, "wt-a"))
            self.assertEqual(cm.exception.code, "ECOLLISION")
            self.assertFalse(os.path.exists(os.path.join(self.tmp, "wt-a")))
            occupied = os.path.join(self.tmp, "occupied")
            os.makedirs(occupied)
            with open(os.path.join(occupied, "user-file"), "w") as f:
                f.write("mine")
            with self.assertRaises(mod.Refusal) as cm:
                mod.create_worktree(self.repo, "agy/brand-new-test-branch", occupied)
            self.assertEqual(cm.exception.code, "ECOLLISION")
            with open(os.path.join(occupied, "user-file")) as f:
                self.assertEqual(f.read(), "mine")
            self.assertNotIn("agy/brand-new-test-branch", git(self.repo, "branch", "--list"))
        finally:
            git(self.repo, "branch", "-D", "agy/existing-branch-test")


class FollowUpTests(Base):
    def test_send_continues_same_conversation_from_recorded_folder(self):
        body = self.spawn("first")
        first = self.wait_state(body["id"])
        cid = first["conversation_id"]
        self.assertTrue(cid)
        code, sent = self.run_helper("send", body["id"], "second", "--request-id", "k1")
        self.assertEqual(code, 0, sent)
        self.assertEqual((sent["turn"], sent["conversation_id"], sent["observed"]), (2, cid, False))
        done = self.wait_state(body["id"])
        self.assertEqual(done["conversation_id"], cid)
        self.assertIn("turn 2", done["headline"])
        call = self.fake_calls(body["id"], 2)[0]
        self.assertIn("--conversation=" + cid, call["argv"])
        self.assertEqual(call["cwd"], body["cwd"])
        self.assertEqual(self.conv(cid)["turns"], 2)
        self.assertEqual(self.conv(cid)["cwds"], [body["cwd"], body["cwd"]])

    def test_send_while_working_is_refused_as_unsupported(self):
        body = self.spawn("SLEEP=4")
        self.wait_state(body["id"], ("working",))
        code, sent = self.run_helper("send", body["id"], "steer")
        self.assertEqual((code, sent["error"]), (4, "EBUSY"))
        self.assertIn("unsupported", sent["message"])
        self.assertEqual(self.session(body["id"])["turns"], 1)

    def test_concurrent_sends_start_exactly_one_turn(self):
        body = self.spawn("first")
        self.wait_state(body["id"])
        codes = []

        def go(k):
            codes.append(self.run_helper("send", body["id"], "SLEEP=2 msg %d" % k, "--request-id", "r%d" % k))

        threads = [threading.Thread(target=go, args=(k,)) for k in range(3)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        accepted = [b for c, b in codes if c == 0]
        refused = [b for c, b in codes if c == 4]
        self.assertEqual(len(accepted), 1, codes)
        self.assertEqual(len(refused), 2, codes)
        self.assertTrue(all(b["error"] == "EBUSY" for b in refused))
        self.assertEqual(self.session(body["id"])["turns"], 2)

    def test_request_id_and_identical_text_are_not_resent(self):
        body = self.spawn("first")
        self.wait_state(body["id"])
        code, a = self.run_helper("send", body["id"], "again", "--request-id", "same")
        self.assertEqual(code, 0)
        self.wait_state(body["id"])
        code, b = self.run_helper("send", body["id"], "again", "--request-id", "same")
        self.assertEqual(code, 0)
        self.assertTrue(b["duplicate"])
        self.assertEqual(b["receipt"]["turn"], 2)
        code, c = self.run_helper("send", body["id"], "plain text")
        self.wait_state(body["id"])
        code, d = self.run_helper("send", body["id"], "plain text")
        self.assertTrue(d["duplicate"])
        self.assertEqual(self.session(body["id"])["turns"], 3)

    def test_unknown_conversation_is_aborted_not_adopted(self):
        body = self.spawn("first")
        done = self.wait_state(body["id"])
        real = done["conversation_id"]
        sdir = os.path.join(self.state, "sessions", body["id"])
        s = self.session(body["id"])
        ghost = str(uuid.uuid4())
        s["conversation_id"] = ghost  # e.g. deleted in agy, or from another machine
        with open(os.path.join(sdir, "session.json"), "w") as f:
            json.dump(s, f)
        env = dict(self.env, AGY_DATA_DIR=os.path.join(self.tmp, "no-local-store"))  # skip the pre-check
        code, sent = self.run_helper("send", body["id"], "SLEEP=3 follow", env=env)
        self.assertEqual(code, 0, sent)
        refused = self.wait_state(body["id"], ("refused",))
        self.assertEqual(refused["guard"]["code"], "EREPLACED")
        self.assertEqual(self.session(body["id"])["conversation_id"], ghost, "replacement was adopted")
        self.assertEqual(self.conv(real)["turns"], 1)
        code, again = self.run_helper("send", body["id"], "once more", env=env)
        self.assertEqual((code, again["error"]), (4, "ETARGET"))

    def test_missing_conversation_refused_before_launch(self):
        body = self.spawn("first")
        self.wait_state(body["id"])
        cid = self.session(body["id"])["conversation_id"]
        os.rename(os.path.join(self.store, "conversations", cid + ".db"),
                  os.path.join(self.store, "conversations", cid + ".moved"))
        code, sent = self.run_helper("send", body["id"], "follow")
        self.assertEqual((code, sent["error"]), (4, "ETARGET"))
        self.assertEqual(self.session(body["id"])["turns"], 1)

    def test_folder_mismatch_is_aborted(self):
        body = self.spawn("first")
        self.wait_state(body["id"])
        env = dict(self.env, FAKE_AGY_REPORT_CWD=self.tmp)
        code, sent = self.run_helper("send", body["id"], "SLEEP=3 follow", env=env)
        self.assertEqual(code, 0)
        refused = self.wait_state(body["id"], ("refused",))
        self.assertEqual(refused["guard"]["code"], "ECWD")

    def test_stopped_session_needs_explicit_allow(self):
        body = self.spawn("SLEEP=20")
        self.wait_recorded(body["id"])
        code, st = self.run_helper("stop", body["id"])
        self.assertEqual(code, 0, st)
        code, sent = self.run_helper("send", body["id"], "continue")
        self.assertEqual((code, sent["error"]), (4, "ESTOPPED"))
        code, sent = self.run_helper("send", body["id"], "continue", "--allow-stopped")
        self.assertEqual(code, 0, sent)
        self.wait_state(body["id"])


class LifecycleTests(Base):
    def test_stop_interrupts_with_sigint_and_keeps_worktree(self):
        body = self.spawn("WRITE=partial.txt SLEEP=30")
        self.wait_recorded(body["id"])
        code, st = self.run_helper("stop", body["id"])
        self.assertEqual(code, 0, st)
        self.assertEqual((st["stopped"], st["state"]), (True, "stopped"))
        self.assertEqual(st["worktree_kept"], body["worktree"])
        log = os.path.join(self.state, "sessions", body["id"], "turns", "1", "agy.log.sigint")
        with open(log) as f:
            self.assertEqual(f.read().strip(), "SIGINT")
        self.assertTrue(os.path.exists(os.path.join(body["worktree"], "partial.txt")))
        self.assertIn(body["branch"], git(self.repo, "branch", "--list", body["branch"]))
        code, again = self.run_helper("stop", body["id"])
        self.assertEqual((code, again["stopped"], again["running"]), (0, False, False))

    def test_immediate_stop_never_kills_the_runner(self):
        for _ in range(3):
            body = self.spawn("SLEEP=30")
            code, st = self.run_helper("stop", body["id"])
            self.assertEqual(code, 0, st)
            self.assertEqual(st["state"], "stopped", st)
            self.assertFalse(st["running"])

    def test_stop_escalates_when_sigint_is_ignored(self):
        body = self.spawn("IGNORE_SIGINT SLEEP=60")
        self.wait_state(body["id"], ("working",))
        code, st = self.run_helper("stop", body["id"], timeout=120)
        self.assertEqual(code, 0, st)
        self.assertEqual(st["state"], "stopped")
        self.assertIn("SIGTERM", st["warning"])

    def test_stale_pid_is_neither_running_nor_signalled(self):
        body = self.spawn("first")
        self.wait_state(body["id"])
        bystander = subprocess.Popen(["sleep", "60"])
        self._procs.append(bystander)
        tdir = os.path.join(self.state, "sessions", body["id"], "turns", "1")
        os.remove(os.path.join(tdir, "exit.json"))
        mod = load_module()
        real = mod.proc(bystander.pid)
        with open(os.path.join(tdir, "runner.json"), "w") as f:
            json.dump({"runner": {"pid": bystander.pid, "uid": os.getuid(), "lstart": real["lstart"],
                                  "marker": "agy-sessions-runner-not-this-one"},
                       "agy": {"pid": bystander.pid, "uid": os.getuid(), "lstart": "Thu Jan  1 00:00:00 1970",
                               "marker": tdir}}, f)
        code, st = self.run_helper("status", body["id"], "--json")
        self.assertEqual(st["state"], "lost")
        code, stop = self.run_helper("stop", body["id"])
        self.assertEqual((code, stop["stopped"]), (0, False))
        time.sleep(0.5)
        self.assertIsNone(bystander.poll(), "an unrelated process was signalled")
        code, doc = self.run_helper("doctor", body["id"], "--json")
        self.assertFalse(doc["session"]["runner_identity_ok"])
        self.assertFalse(doc["session"]["agy_identity_ok"])

    def test_vanished_runner_is_lost_not_done(self):
        body = self.spawn("SLEEP=30")
        self.wait_recorded(body["id"])
        tdir = os.path.join(self.state, "sessions", body["id"], "turns", "1")
        with open(os.path.join(tdir, "runner.json")) as f:
            r = json.load(f)
        os.kill(r["runner"]["pid"], signal.SIGKILL)
        os.kill(r["agy"]["pid"], signal.SIGKILL)
        st = self.wait_state(body["id"], ("lost",))
        self.assertNotIn(st["state"], ("done", "working"))
        code, sent = self.run_helper("send", body["id"], "carry on")
        self.assertEqual(code, 0, sent)
        self.assertIn("warning", sent)

    def test_failure_timeout_and_denial_states_keep_worktrees(self):
        cases = {"FAIL": "failed", "TIMEOUT": "timed-out", "DENY": "denied"}
        for directive, expected in cases.items():
            body = self.spawn("WRITE=%s.txt %s" % (directive.lower(), directive))
            st = self.wait_state(body["id"], (expected,))
            self.assertTrue(os.path.exists(os.path.join(body["worktree"], directive.lower() + ".txt")))
            if expected == "denied":
                self.assertIn("write_file", st["headline"])
                self.assertIn("auto-denied", st["stderr_tail"])
        code, rows = self.run_helper("list", "--json")
        self.assertEqual([r["state"] for r in rows][:2].count("done"), 0, "problems are listed first")

    def test_wait_reports_still_working(self):
        body = self.spawn("SLEEP=10")
        code, w = self.run_helper("wait", body["id"], "--timeout", "1")
        self.assertTrue(w["still_working"])


class SafetyTests(Base):
    def test_ambiguous_short_and_unknown_refs(self):
        a = self.spawn("x", "--name", "twin")
        b = self.spawn("y", "--name", "twin")
        self.wait_state(a["id"])
        self.wait_state(b["id"])
        code, body = self.run_helper("send", "twin", "hello")
        self.assertEqual((code, body["error"]), (4, "EAMBIGUOUS"))
        code, body = self.run_helper("status", a["id"][:4])
        self.assertEqual(body["error"], "ENOTFOUND")
        code, body = self.run_helper("status", a["id"], "--json")
        self.assertEqual(body["id"], a["id"])
        cid = self.session(b["id"])["conversation_id"]
        code, body = self.run_helper("status", cid, "--json")
        self.assertEqual(body["id"], b["id"])

    def test_unsupported_agy_is_refused_before_any_change(self):
        env = dict(self.env, FAKE_AGY_HELP="legacy")
        before = git(self.repo, "branch", "--list")
        code, body = self.run_helper("spawn", "--cwd", self.repo, "--", "hi", env=env)
        self.assertEqual((code, body["error"]), (2, "EUNSUPPORTED"))
        self.assertIn("--conversation", body["message"])
        self.assertEqual(git(self.repo, "branch", "--list"), before)
        code, doc = self.run_helper("doctor", "--json", env=env)
        self.assertEqual(code, 2)
        self.assertFalse(doc["agy"]["flags"]["--conversation"])

    def test_doctor_reports_capability_limits(self):
        code, doc = self.run_helper("doctor", "--json")
        self.assertEqual(code, 0, doc)
        caps = doc["capabilities"]
        self.assertFalse(caps["native_background_sessions"])
        self.assertFalse(caps["native_session_list"])
        self.assertFalse(caps["mid_turn_send"])
        self.assertFalse(caps["answer_permission_prompts"])
        self.assertEqual(doc["agy"]["version"], "1.5.12")

    def test_unsafe_state_folder_is_refused(self):
        os.makedirs(self.state)
        os.chmod(self.state, 0o777)
        code, body = self.run_helper("list", "--json")
        self.assertEqual((code, body["error"]), (1, "EPATH"))
        os.chmod(self.state, 0o700)
        link = os.path.join(self.tmp, "state-link")
        os.symlink(self.state, link)
        code, body = self.run_helper("list", "--json", env=dict(self.env, AGY_SESSIONS_STATE=link))
        self.assertEqual(body["error"], "EPATH")

    def test_state_files_are_private(self):
        body = self.spawn("hi")
        self.wait_state(body["id"])
        for dirpath, dirs, files in os.walk(os.path.join(self.state, "sessions")):
            for name in files:
                mode = stat.S_IMODE(os.stat(os.path.join(dirpath, name)).st_mode)
                self.assertEqual(mode & 0o077, 0, "%s is readable by others" % name)

    def test_messages_are_validated(self):
        body = self.spawn("hi")
        self.wait_state(body["id"])
        code, sent = self.run_helper("send", body["id"], "   ")
        self.assertEqual((code, sent["error"]), (2, "EMESSAGE"))


if __name__ == "__main__":
    unittest.main()
