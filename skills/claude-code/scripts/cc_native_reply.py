"""Minimal, unsupported Claude supervisor reply bridge. Standard library only.

Only independently verified wire contracts are allowed. Never starts a daemon,
retries a reply, edits Claude's files, or invokes a native binary behind a wrapper.
See reference/native-reply-contract.json for the scrubbed contract evidence.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import struct
import subprocess
import sys
import time

PROTOCOL = 1
CLI_VERSIONS = frozenset({"2.1.308.1355", "2.1.309.1365"})
DAEMON_VERSIONS = frozenset({"2.1.308", "2.1.309"})
SHORT_ID = re.compile(r"[0-9a-f]{8}\Z")
SESSION_ID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z")
MAX_REPLY = 64 * 1024
MAX_RESPONSE = 2 * 1024 * 1024
MANUAL = ("Use `claude agents` at the computer, select the exact session, press Space "
          "to peek, and reply there. Do not use ordinary dispatch, stop/resume, or "
          "a new task as a follow-up fallback.")


class BridgeError(Exception):
    def __init__(self, code, message, uncertain=False):
        super().__init__(message)
        self.code = code
        self.uncertain = uncertain


def reject(code, message):
    raise BridgeError(code, message)


def private_dir(path):
    """Validate an existing private directory; never repair someone else's state."""
    st = os.lstat(path)
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) != 0o700:
        reject("EPATH", "A private directory is missing, linked, or has unsafe ownership/permissions.")
    return st


def safe_ancestors(path):
    """No symlinks or writable ancestors, except root-owned sticky temp directories."""
    p = Path(path)
    if not p.is_absolute() or str(p) != os.path.realpath(p):
        reject("EPATH", "Paths must be absolute and canonical (no symlink components).")
    for part in (p, *p.parents):
        st = os.lstat(part)
        sticky_root = st.st_uid == 0 and bool(st.st_mode & stat.S_ISVTX)
        if (not stat.S_ISDIR(st.st_mode) or st.st_uid not in (0, os.getuid()) or
                (st.st_mode & 0o022 and not sticky_root)):
            reject("EPATH", "An ancestor directory is writable by another user or untrusted.")


def peer_identity(sock):
    """Check kernel credentials, not a PID or username supplied in JSON."""
    if sys.platform == "darwin":
        cred = sock.getsockopt(0, socket.LOCAL_PEERCRED, 80)
        if len(cred) != 76:
            reject("EPEER", "Unrecognized macOS peer credential layout.")
        version, uid = struct.unpack_from("=II", cred)
        if version != 0:
            reject("EPEER", "Unrecognized macOS peer credential version.")
        pid = struct.unpack("=i", sock.getsockopt(0, 2, 4))[0]  # LOCAL_PEERPID
    elif sys.platform.startswith("linux") and hasattr(socket, "SO_PEERCRED"):
        pid, uid, _ = struct.unpack("=3i", sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
    else:
        reject("EPLATFORM", "Verified local socket peer credentials are unavailable on this platform.")
    if uid != os.getuid() or pid <= 0:
        reject("EPEER", "The supervisor socket is not served by this user.")
    return uid, pid


def validate_process_pair(worker_pid, repl_pid):
    """The supervisor owns a worker; agents --json reports its REPL child.

    Observed on the actual 2.1.309 canary, not interchangeable PID fields.
    Require both PIDs to exist under this UID and permit only the same process
    or a direct child. Never accept arbitrary descendant or recycled PIDs.
    """
    if any(type(pid) is not int or pid <= 0 for pid in (worker_pid, repl_pid)):
        reject("ETARGET", "The worker/REPL process identity is unavailable.")
    try:
        result = subprocess.run(
            ["/bin/ps", "-p", ",".join(str(pid) for pid in sorted({worker_pid, repl_pid})),
             "-o", "pid=,ppid=,uid=,lstart="],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=2)
        rows = {}
        for line in result.stdout.splitlines():
            parts = line.split(None, 3)
            if len(parts) != 4:
                raise ValueError()
            pid, parent, uid = map(int, parts[:3])
            if pid in rows or uid != os.getuid():
                raise ValueError()
            rows[pid] = (parent, uid, parts[3])
        if result.returncode or set(rows) != {worker_pid, repl_pid}:
            raise ValueError()
        if worker_pid != repl_pid and rows[repl_pid][0] != worker_pid:
            raise ValueError()
        return tuple((pid, *rows[pid]) for pid in sorted(rows))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        reject("ETARGET", "The native worker and REPL are not a verified same-user process pair.")


def strict_json(data):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate key")
            out[key] = value
        return out
    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))


class NativeReply:
    def __init__(self, config, cli_version, timeout=3.0, temp_root=None):
        if os.name != "posix" or not hasattr(os, "getuid") or os.getuid() != os.geteuid():
            reject("EPLATFORM", "Native reply requires a non-setuid POSIX process.")
        if cli_version not in CLI_VERSIONS:
            reject("EVERSION", "This configured Claude CLI version has not been reviewed for native reply.")
        self.config = Path(os.path.abspath(os.path.expanduser(config)))
        self.cli_version = cli_version
        self.timeout = max(0.05, min(float(timeout), 10.0))
        # temp_root is dependency injection for isolated tests, never an environment override.
        root = Path(os.path.realpath(temp_root or "/tmp"))
        digest = hashlib.sha256(str(self.config).encode("utf-8")).hexdigest()[:8]
        self.socket_path = root / ("cc-daemon-%s" % os.getuid()) / digest / "control.sock"
        self.auth_path = self.config / "daemon" / "control.key"
        self.endpoint = None
        self.peer = None
        self.daemon_version = None
        self._prepared = None
        self._worker_pid = None
        self._process_pair = None

    def _validate_path(self):
        safe_ancestors(self.config)
        safe_ancestors(self.socket_path.parent)
        private_dir(self.auth_path.parent)
        private_dir(self.socket_path.parent.parent)
        private_dir(self.socket_path.parent)
        st = os.lstat(self.socket_path)
        if (not stat.S_ISSOCK(st.st_mode) or st.st_uid != os.getuid() or
                st.st_mode & 0o022 or st.st_nlink != 1):
            reject("EPATH", "The supervisor endpoint is not a safe, user-owned Unix socket.")
        identity = (st.st_dev, st.st_ino, st.st_ctime_ns)
        if self.endpoint is not None and self.endpoint != identity:
            reject("ECHANGED", "The supervisor socket changed during this request. No automatic retry.")
        self.endpoint = identity

    def _auth(self):
        private_dir(self.auth_path.parent)
        fd = os.open(self.auth_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            st = os.fstat(fd)
            if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or
                    stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1 or st.st_size > 4096):
                reject("EAUTHFILE", "The local control key has unsafe type, ownership, permissions, or size.")
            token = os.read(fd, 4097).decode("ascii").strip()
            if re.fullmatch(r"[0-9a-f]{32}", token) is None:
                reject("EAUTHFILE", "The local control key has an unreviewed format.")
            return token
        finally:
            os.close(fd)

    def _rpc(self, request, mutating=False):
        attempted = False
        deadline = time.monotonic() + self.timeout
        try:
            self._validate_path()
            wire = json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(max(0.001, deadline - time.monotonic()))
                sock.connect(str(self.socket_path))
                identity = peer_identity(sock)
                if self.peer is not None and self.peer != identity:
                    reject("ECHANGED", "The supervisor peer changed during this request.")
                self.peer = identity
                self._validate_path()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError()
                sock.settimeout(remaining)
                # sendall can partly write before failing. Reserve before the first byte.
                attempted = mutating
                sock.sendall(wire)
                data = bytearray()
                while b"\n" not in data:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError()
                    sock.settimeout(remaining)
                    part = sock.recv(min(65536, MAX_RESPONSE + 1 - len(data)))
                    if not part:
                        raise ConnectionError()
                    data.extend(part)
                    if len(data) > MAX_RESPONSE:
                        reject("ERESPONSE", "The supervisor response exceeded the local size limit.")
                line, extra = bytes(data).split(b"\n", 1)
                if extra.strip():
                    reject("ERESPONSE", "The supervisor returned more than one response.")
                response = strict_json(line)
                if not isinstance(response, dict) or type(response.get("ok")) is not bool:
                    reject("ERESPONSE", "The supervisor returned an unrecognized response shape.")
                return response
        except BridgeError as exc:
            if attempted:
                exc.uncertain = True
            raise
        except (OSError, ValueError, UnicodeError, ConnectionError, RecursionError):
            # Never echo server errors, auth, raw frames, prompts, or exception buffers.
            raise BridgeError("ETRANSPORT", "The local supervisor exchange failed or timed out.",
                              uncertain=attempted) from None

    def probe(self):
        reply = self._rpc({"proto": PROTOCOL, "op": "ping"})
        if (reply.get("ok") is not True or reply.get("op") != "ping" or
                type(reply.get("proto")) is not int or reply["proto"] != PROTOCOL or
                type(reply.get("carriedPromptsFormat")) is not int or reply["carriedPromptsFormat"] != 1):
            reject("EPROTO", "The supervisor protocol/queue format is not supported.")
        if not isinstance(reply.get("version"), str) or reply["version"] not in DAEMON_VERSIONS:
            reject("EVERSION", "The running supervisor version has not been reviewed.")
        if self.daemon_version is not None and self.daemon_version != reply["version"]:
            reject("ECHANGED", "The supervisor version changed during this request.")
        self.daemon_version = reply["version"]
        try:
            self._auth()
        except BridgeError:
            raise
        except (OSError, UnicodeError):
            reject("EAUTHFILE", "The normal local supervisor control key is unavailable.")
        return {"cli_version": self.cli_version, "daemon_version": self.daemon_version,
                "protocol": PROTOCOL, "private_bridge": True, "peer_verified": True,
                "auth_file_valid": True, "auth_verified": False,
                "note": "Read-only probe. Authentication is verified only by an actual reply."}

    def prepare(self, session):
        sid, uuid = session.get("id"), session.get("sessionId")
        if (not isinstance(sid, str) or not SHORT_ID.fullmatch(sid) or
                not isinstance(uuid, str) or not SESSION_ID.fullmatch(uuid) or
                type(session.get("pid")) is not int or session["pid"] <= 0 or
                session.get("state") not in ("working", "blocked", "done") or
                session.get("status") not in ("busy", "waiting", "idle")):
            reject("ETARGET", "The target is not an available canonical local Claude session.")
        self.probe()
        response = self._rpc({"proto": PROTOCOL, "op": "list"})
        jobs = response.get("jobs")
        if response.get("ok") is not True or response.get("op") != "list" or not isinstance(jobs, list):
            reject("ETARGET", "Cannot validate the target against the running supervisor.")
        matches = [job for job in jobs if isinstance(job, dict) and job.get("short") == sid]
        if len(matches) != 1:
            reject("ETARGET", "The target is missing or ambiguous in the supervisor.")
        job = matches[0]
        if (job.get("sessionId") != uuid or job.get("backend") != "daemon" or
                job.get("dying") or job.get("outcome") or job.get("legacy") or
                job.get("state") in ("stopped", "failed")):
            reject("ETARGET", "The target identity changed, is unavailable, or is not a native daemon session.")
        if job.get("cliVersion") != self.daemon_version:
            reject("ESKEW", "Safe-boundary reply requires the worker and supervisor to run the same reviewed build.")
        self._worker_pid = job.get("pid")
        self._process_pair = validate_process_pair(self._worker_pid, session["pid"])
        self._prepared = (sid, uuid, session["pid"])
        return {"id": sid, "sessionId": uuid, "worker_version": job["cliVersion"],
                "daemon_version": self.daemon_version, "protocol": PROTOCOL}

    def reply(self, session, text):
        if self._prepared != (session.get("id"), session.get("sessionId"), session.get("pid")):
            reject("ETARGET", "Reply target has not passed the read-only identity checks.")
        if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > MAX_REPLY or "\0" in text:
            reject("EMESSAGE", "Reply text must be nonempty UTF-8 without NUL and at most 64 KiB.")
        try:
            token = self._auth()
        except BridgeError:
            raise
        except (OSError, UnicodeError):
            reject("EAUTHFILE", "The normal local supervisor control key is unavailable.")
        if validate_process_pair(self._worker_pid, session["pid"]) != self._process_pair:
            reject("ECHANGED", "The native worker/REPL changed after preparation. No reply was sent.")
        # nextTurn uses native safe-boundary queue semantics, including while idle.
        try:
            response = self._rpc({"proto": PROTOCOL, "op": "reply", "short": session["id"],
                                  "text": text, "auth": token, "nextTurn": True}, mutating=True)
        finally:
            # This client object is single-attempt too, including after a dropped ACK.
            self._prepared = None
        if response == {"ok": True, "op": "reply"}:
            return {"accepted": True, "queued": True, "observed": False,
                    "id": session["id"], "sessionId": session["sessionId"],
                    "protocol": PROTOCOL, "daemon_version": self.daemon_version}
        code = response.get("code")
        # Only reviewed pre-enqueue refusals can establish that nothing was accepted.
        if response.get("ok") is False and isinstance(code, str) and code in {
                "EAUTH", "EPROTO", "ESTARTING", "ERESPAWNING", "ESKEW", "ENOJOB", "ENOREPLY"}:
            raise BridgeError(code, "The supervisor refused the reply (%s). No retry was made." % code)
        raise BridgeError("EACK", "The reply acknowledgement was not recognized. Do not resend.", uncertain=True)
