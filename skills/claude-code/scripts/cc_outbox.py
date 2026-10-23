"""Durable local send receipts, not a delivery queue. No replay worker exists."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import time

try:
    import fcntl
except ImportError:
    fcntl = None

from cc_native_reply import BridgeError, SHORT_ID, SESSION_ID, private_dir, safe_ancestors, strict_json

MAX_FILE = 2 * 1024 * 1024


def fail(code, text):
    raise BridgeError(code, text)


def checked_read(path, private=False):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_nlink != 1 or
                st.st_mode & 0o022 or (private and stat.S_IMODE(st.st_mode) != 0o600) or st.st_size > MAX_FILE):
            fail("ESTATE", "Unsafe or oversized local receipt/history file.")
        data = b""
        while len(data) <= MAX_FILE:
            chunk = os.read(fd, min(65536, MAX_FILE + 1 - len(data)))
            if not chunk:
                break
            data += chunk
        if len(data) > MAX_FILE:
            fail("ESTATE", "Local receipt/history file grew beyond the read limit.")
        value = strict_json(data)
        if not isinstance(value, dict):
            fail("ESTATE", "Unrecognized local receipt/history file.")
        return value
    except (ValueError, UnicodeError, RecursionError):
        fail("ESTATE", "Malformed local receipt/history file. Refusing to lose idempotency history.")
    finally:
        os.close(fd)


def atomic_save(path, value):
    fd, tmp = tempfile.mkstemp(prefix=".receipt-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=1)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def alive(pid):
    if type(pid) is not int or pid <= 0:
        return False
    try:
        os.kill(pid, 0)  # Probe only, never a signal that stops a process.
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@contextlib.contextmanager
def lock(path):
    if fcntl is None:
        fail("EPLATFORM", "Native follow-up receipts require POSIX file locking.")
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or
                stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1):
            fail("ESTATE", "Unsafe local lock file.")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail("ELOCKED", "A send, stop, or legacy watcher still owns the local lock. No retry was made.")
        yield
    finally:
        os.close(fd)


class Outbox:
    def __init__(self, state, config):
        self.root = Path(os.path.abspath(os.path.expanduser(state)))
        self.directory = self.root / "native-replies-v1"
        self.config = os.path.abspath(os.path.expanduser(config))

    def setup(self):
        if fcntl is None or os.name != "posix":
            fail("EPLATFORM", "Native follow-up receipts require POSIX file locking.")
        canonical = Path(os.path.realpath(self.root))
        config = Path(os.path.realpath(self.config))
        if canonical == config or config in canonical.parents:
            fail("ESTATE", "Receipt state must be separate from Claude's native config/registry.")
        parent = self.root
        while not parent.exists():
            if parent.is_symlink():
                fail("ESTATE", "Receipt state cannot traverse a dangling symlink.")
            parent = parent.parent
        safe_ancestors(parent)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        safe_ancestors(self.root)
        private_dir(self.root)
        self.directory.mkdir(mode=0o700, exist_ok=True)
        private_dir(self.directory)

    def legacy(self):
        if not self.root.exists():
            return []
        safe_ancestors(self.root)
        private_dir(self.root)
        paths = sorted(self.root.glob("*.json"))
        if len(paths) > 4096:
            fail("ESTATE", "Too many legacy history files to inspect safely.")
        result = []
        for path in paths:
            if not SHORT_ID.fullmatch(path.stem):
                fail("ESTATE", "Unrecognized legacy history filename.")
            row = checked_read(path)
            if row.get("id") != path.stem or not isinstance(row.get("items"), list):
                fail("ESTATE", "Unrecognized legacy history identity or items.")
            if not all(isinstance(item, dict) for item in row["items"]):
                fail("ESTATE", "Unrecognized legacy history items.")
            result.append(row)
        return result

    @contextlib.contextmanager
    def mutation_guard(self):
        """Hold old watcher locks too; never kill a watcher or let it restart."""
        self.setup()
        with contextlib.ExitStack() as stack:
            stack.enter_context(lock(self.directory / "mutation.lock"))
            rows = self.legacy()
            keys = {row["id"] for row in rows}
            keys.update(p.stem for p in self.root.glob("*.watcher"))
            for key in sorted(keys):
                if not SHORT_ID.fullmatch(key):
                    fail("ESTATE", "Unrecognized legacy watcher filename.")
                stack.enter_context(lock(self.root / (key + ".watcher")))
            rows = self.legacy()
            if any(alive(row.get("watcher_pid")) for row in rows):
                fail("ELEGACY", "A legacy helper watcher may still be running. Retire it explicitly before sending or stopping.")
            yield rows

    @staticmethod
    def lineage(rows, sid):
        """Return connected history, but never redirect a mutation to an alias."""
        edges = {}
        members = {sid}
        for row in rows:
            chain = [row["id"]]
            for item in row["items"]:
                target = item.get("delivered_to")
                if target and target != chain[-1]:
                    if not isinstance(target, str) or not SHORT_ID.fullmatch(target):
                        fail("EALIAS", "Unsafe legacy copy identity.")
                    chain.append(target)
            target = row.get("target")
            if target and target != chain[-1]:
                if not isinstance(target, str) or not SHORT_ID.fullmatch(target):
                    fail("EALIAS", "Unsafe legacy target identity.")
                chain.append(target)
            for source, target in zip(chain, chain[1:]):
                edges.setdefault(source, set()).add(target)
        changed = True
        while changed:
            before = len(members)
            for source, targets in edges.items():
                if source in members or members.intersection(targets):
                    members.add(source)
                    members.update(targets)
            changed = len(members) != before
        return edges, members, [row for row in rows if row["id"] in members]

    def assert_current(self, rows, sid):
        edges, members, _ = self.lineage(rows, sid)
        if any(len(edges.get(node, set())) > 1 for node in members):
            fail("EALIAS", "Legacy copy lineage branches. Choose and verify a canonical session manually.")
        for origin in members:
            seen = set()
            node = origin
            while edges.get(node):
                if node in seen:
                    fail("EALIAS", "Legacy copy lineage contains a cycle. No message was sent.")
                seen.add(node)
                node = next(iter(edges[node]))
        if edges.get(sid):
            fail("ESTALEID", "This is a stale legacy copy ID. Inspect queue history and explicitly select the current ID.")

    def cancel_legacy(self, rows, sid):
        _, _, related = self.lineage(rows, sid)
        count = 0
        for row in related:
            changed = False
            for item in row["items"]:
                if item.get("status") in ("pending", "delivering"):
                    previous = item["status"]
                    item.update(status="cancelled" if previous == "pending" else "unknown",
                                finished=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                                note="Legacy automatic delivery retired. This message will never be replayed.")
                    count += previous == "pending"
                    changed = True
            if changed:
                row["watcher_pid"] = None
                atomic_save(self.root / (row["id"] + ".json"), row)
        return count

    def request(self, session, message, request_id=None):
        if (not isinstance(session.get("sessionId"), str) or not SESSION_ID.fullmatch(session["sessionId"]) or
                not isinstance(session.get("id"), str) or not SHORT_ID.fullmatch(session["id"])):
            fail("ETARGET", "A canonical native session identity is required.")
        digest = hashlib.sha256(message.encode("utf-8")).hexdigest()
        identity = self.config + "\0" + session["sessionId"] + "\0" + digest
        key = request_id or ("auto:" + hashlib.sha256(identity.encode()).hexdigest())
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,100}", key):
            fail("EREQUEST", "Request IDs must be 1 to 100 letters, digits, dots, colons, underscores, or hyphens.")
        filename = hashlib.sha256((self.config + "\0" + key).encode()).hexdigest() + ".json"
        return self.directory / filename, {
            "schema": 1, "request_id": key, "id": session["id"], "sessionId": session["sessionId"],
            "config_sha256": hashlib.sha256(self.config.encode()).hexdigest(),
            "message_sha256": digest, "created": time.time(),
            "status": "unknown", "accepted": None, "queued": None, "observed": False,
            "note": "Reserved before writing to the supervisor. No automatic resend is allowed.",
        }

    def existing(self, path, expected):
        if not path.exists() and not path.is_symlink():
            return None
        receipt = checked_read(path, private=True)
        if any(receipt.get(key) != expected[key] for key in (
                "schema", "request_id", "id", "sessionId", "config_sha256", "message_sha256")):
            fail("EREQUEST", "This request ID is already bound to a different target or message.")
        if receipt.get("status") not in ("accepted", "rejected", "unknown"):
            fail("ESTATE", "Unrecognized receipt status. Refusing to resend.")
        return receipt

    def receipts(self, session):
        if not self.directory.exists():
            return []
        safe_ancestors(self.directory)
        private_dir(self.directory)
        paths = list(self.directory.glob("*.json"))
        if len(paths) > 20000:
            fail("ESTATE", "Too many receipts for a bounded history read. Receipts are never auto-pruned.")
        config_hash = hashlib.sha256(self.config.encode()).hexdigest()
        rows = [checked_read(path, private=True) for path in paths]
        return sorted((row for row in rows if row.get("sessionId") == session["sessionId"] and
                       row.get("config_sha256") == config_hash), key=lambda row: row.get("created", 0))

    def view(self, session):
        if os.name != "posix" or fcntl is None:
            return {"id": session["id"], "sessionId": session.get("sessionId"),
                    "items": [], "legacy": [], "watcher_running": False,
                    "automatic_replay": False, "native_queue_depth": None,
                    "observed": False, "supported": False,
                    "note": "Native reply receipts require POSIX. Use the agents UI for follow-ups."}
        legacy = self.legacy()
        _, _, related = self.lineage(legacy, session["id"])
        history = []
        for row in related:
            for item in row["items"]:
                # Preserve historical outcomes without pretending they are native acknowledgements.
                history.append({"origin": row["id"], "target": row.get("target", row["id"]),
                                **{key: item[key] for key in ("n", "status", "delivered_to", "queued", "finished") if key in item},
                                "automatic_delivery": False})
        return {"id": session["id"], "sessionId": session["sessionId"], "items": self.receipts(session),
                "legacy": history, "legacy_watcher_pid_alive": any(alive(row.get("watcher_pid")) for row in legacy),
                "watcher_running": False, "automatic_replay": False,
                "native_queue_depth": None, "observed": False,
                "note": "Receipts show supervisor acceptance, not consumption. Legacy pending entries are disabled."}
