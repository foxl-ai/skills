"""Minimal, unsupported Claude supervisor reply bridge. Standard library only.

Live negotiation (integer protocol 1, carriedPromptsFormat 1) plus exact target,
socket, peer and auth checks decide whether a reply is sent. CLI, supervisor and
worker version or image differences are reported, never refused by themselves.
Never starts a daemon, retries a reply, edits Claude's files, or invokes a native
binary behind a wrapper. See reference/native-reply-contract.json.
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

from cc_contract import ContractChanged, ContractError, ProcessAttestation, UnsafeImage

PROTOCOL = 1
QUEUE_FORMAT = 1
# Version text is informational only. Compatibility is negotiated live, never
# inferred from (or refused because of) patch/build numbers or suffixes.
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)?\Z")
VERSION_TOKEN = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+_-]{0,79}\Z")
# Job/session states that mean the target cannot take a reply. Other (including
# future) state names are left to the supervisor, which refuses pre-accept.
UNAVAILABLE = frozenset(("stopped", "failed", "exited", "killed", "crashed", "dead", "removed", "offline"))
NEXT_TURN = "next-turn-queue"
AGENTS_UI = "agents-ui-reply"
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
        if not (sys.platform == "darwin" or sys.platform.startswith("linux")):
            reject("EPLATFORM", "Verified process/socket identity is supported only on macOS and Linux.")
        # The configured CLI only supplies session reads; its version is a label.
        self.cli_version = (cli_version if isinstance(cli_version, str) and VERSION_TOKEN.fullmatch(cli_version)
                            else None)
        self.config = Path(os.path.abspath(os.path.expanduser(config)))
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
        self._worker_version = None
        self._process_pair = None
        self._attestation = ProcessAttestation()
        self._supervisor = None
        self._target = None
        self._route = None

    def _attest(self, worker=None, repl=None):
        """Gather image/structure evidence. Differences are informational."""
        try:
            self._supervisor = self._attestation.supervisor(self.peer[1])
            if worker is not None:
                return self._attestation.worker(worker, repl)
        except ContractChanged:
            reject("ECHANGED", "The supervisor or worker process/executable changed during this request. No reply was sent.")
        except UnsafeImage:
            reject("EPATH", "The live Claude executable is owned or writable by another user.")
        except (ContractError, OSError, ValueError, KeyError, TypeError, RecursionError):
            # Internal evidence errors only. Unreviewed/unreadable/deleted images do not land here.
            reject("ECONTRACT", "The live process identity could not be pinned for this request.")
        return None

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
                if mutating:
                    # Recheck the pinned process/image evidence right before the
                    # first reply byte, not just at an earlier doctor probe.
                    self._attest(self._worker_pid, self._prepared[2])
                    if validate_process_pair(self._worker_pid, self._prepared[2]) != self._process_pair:
                        reject("ECHANGED", "The worker/REPL changed before the reply write. No reply was sent.")
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
        except (FileNotFoundError, ConnectionRefusedError):
            raise BridgeError("ENODAEMON", "No reachable supervisor at the normal configured endpoint. Nothing was started.",
                              uncertain=attempted) from None
        except (OSError, ValueError, UnicodeError, ConnectionError, RecursionError):
            # Never echo server errors, auth, raw frames, prompts, or exception buffers.
            raise BridgeError("ETRANSPORT", "The local supervisor exchange failed or timed out.",
                              uncertain=attempted) from None

    def probe(self):
        reply = self._rpc({"proto": PROTOCOL, "op": "ping"})
        if reply.get("ok") is not True or reply.get("op") != "ping":
            reject("EPROTO", "The supervisor did not acknowledge the read-only ping operation.")
        if type(reply.get("proto")) is not int or reply["proto"] != PROTOCOL:
            reject("EPROTO", "The supervisor must explicitly negotiate integer protocol 1.")
        if type(reply.get("carriedPromptsFormat")) is not int or reply["carriedPromptsFormat"] != QUEUE_FORMAT:
            reject("EPROTO", "The supervisor must advertise integer carriedPromptsFormat=1; nextTurn alone is insufficient.")
        version = reply.get("version")
        # Any single version token is fine (future builds, suffixes); it is only
        # compared for skew reporting and mid-request change detection.
        if not isinstance(version, str) or not VERSION_TOKEN.fullmatch(version):
            reject("EPROTO", "The supervisor supplied a missing or malformed version identity.")
        if self.daemon_version is not None and self.daemon_version != version:
            reject("ECHANGED", "The supervisor version changed during this request.")
        self.daemon_version = version
        self._attest()
        try:
            self._auth()
        except BridgeError:
            raise
        except (OSError, UnicodeError):
            reject("EAUTHFILE", "The normal local supervisor control key is unavailable.")
        image = self._supervisor["image"]
        reviewed = image == "reviewed"
        cli_skew = None if self.cli_version is None else self.cli_version.split(".")[:3] != version.split(".")[:3]
        warnings = []
        if not reviewed:
            warnings.append(("Supervisor %s is an unreviewed build" if image == "unreviewed" else
                             "Supervisor %s executable could not be inspected (an update may have removed it)")
                            % version + "; proceeding on negotiated protocol 1 and carriedPromptsFormat 1.")
        if self.cli_version is None:
            warnings.append("The configured CLI version could not be read; it is informational only.")
        elif cli_skew:
            warnings.append("CLI %s and supervisor %s are different builds; informational only."
                            % (self.cli_version, version))
        return {"cli_version": self.cli_version, "daemon_version": version,
                "protocol": PROTOCOL, "queue_format": QUEUE_FORMAT,
                "compatibility": "negotiated-and-structurally-attested" if reviewed else "negotiated-unreviewed-build",
                "reviewed_build": reviewed, "supervisor_image": image,
                "contract": self._supervisor["contract"], "private_bridge": True, "peer_verified": True,
                "process_image_verified": reviewed, "auth_file_valid": True, "auth_verified": False,
                "cli_daemon_skew": cli_skew, "warnings": warnings,
                "note": "Read-only probe. Version differences are informational; authentication is verified only by an actual reply."}

    def _job(self, session):
        response = self._rpc({"proto": PROTOCOL, "op": "list"})
        jobs = response.get("jobs")
        if response.get("ok") is not True or response.get("op") != "list" or not isinstance(jobs, list):
            reject("ETARGET", "Cannot validate the target against the running supervisor.")
        matches = [job for job in jobs if isinstance(job, dict) and job.get("short") == session["id"]]
        if len(matches) != 1:
            reject("ETARGET", "The target is missing or ambiguous in the supervisor.")
        job = matches[0]
        state = job.get("state")
        if (job.get("sessionId") != session["sessionId"] or job.get("backend") != "daemon" or
                job.get("dying") or job.get("outcome") or job.get("legacy") or
                not isinstance(state, str) or state in UNAVAILABLE):
            reject("ETARGET", "The target identity changed, is unavailable, or is not a native daemon session.")
        # No worker/supervisor version comparison here: skew selects a route, it never refuses.
        return job

    @staticmethod
    def _awaiting_input(session, job):
        """Pending question/permission/dialog, or a status this helper cannot classify."""
        return (session.get("status") not in ("busy", "idle") or
                "blocked" in (session.get("state"), job.get("state"), job.get("tempo")))

    def prepare(self, session):
        sid, uuid = session.get("id"), session.get("sessionId")
        state, status = session.get("state"), session.get("status")
        if (not isinstance(sid, str) or not SHORT_ID.fullmatch(sid) or
                not isinstance(uuid, str) or not SESSION_ID.fullmatch(uuid) or
                type(session.get("pid")) is not int or session["pid"] <= 0 or
                not isinstance(state, str) or state in UNAVAILABLE or
                not isinstance(status, str) or status in UNAVAILABLE):
            reject("ETARGET", "The target is not an available canonical local Claude session.")
        probe = self.probe()
        job = self._job(session)
        self._worker_pid = job.get("pid")
        self._process_pair = validate_process_pair(self._worker_pid, session["pid"])
        image = self._attest(self._worker_pid, session["pid"])
        self._worker_version = job.get("cliVersion")
        # The supervisor itself refuses nextTurn (ESKEW) unless the worker reports
        # exactly its version, so a skewed worker gets the agents-UI request.
        skew = self._worker_version != self.daemon_version
        self._route = AGENTS_UI if skew else NEXT_TURN
        self._prepared = (sid, uuid, session["pid"])
        worker_version = (self._worker_version if isinstance(self._worker_version, str) and
                          VERSION_TOKEN.fullmatch(self._worker_version) else None)
        warnings = list(probe["warnings"])
        if skew:
            warnings.append("Worker %s and supervisor %s are different builds (normal after an update); the reply is "
                            "sent the way the agents UI sends it." % (worker_version or "(unknown)", self.daemon_version))
        if image["image"] == "unavailable":
            warnings.append("The worker executable could not be inspected (an update may have removed it); informational only.")
        elif image["image"] == "different-image":
            warnings.append("The worker runs a different executable than the supervisor (%s structure); informational only."
                            % image["structure"])
        ready = not (skew and self._awaiting_input(session, job))
        self._target = {"id": sid, "sessionId": uuid, "worker_version": worker_version,
                        "daemon_version": self.daemon_version, "protocol": PROTOCOL,
                        "skew": skew, "route": self._route,
                        "worker_image": image["image"], "worker_structure": image["structure"],
                        "reviewed_build": self._supervisor["image"] == "reviewed",
                        "send_ready": ready, "warnings": warnings}
        if not ready:
            self._target["send_refusal"] = "EBLOCKED"
            warnings.append(BLOCKED)
        return dict(self._target, warnings=list(warnings))

    def check_text(self, text):
        """The agents-UI request is handled like typed input. Refuse what would not
        stay an ordinary prompt; the next-turn route skips slash commands natively."""
        if self._route != AGENTS_UI:
            return
        if not self._target["send_ready"]:
            reject("EBLOCKED", BLOCKED)
        if text.lstrip()[:1] in ("/", "!"):
            reject("ECOMMAND", "On a different-build worker, text starting with / or ! would run as a command. "
                               "Rephrase it, or use the agents UI.")
        if any((ord(c) < 32 and c not in "\n\t") or 127 <= ord(c) < 160 for c in text):
            reject("EMESSAGE", "On a different-build worker, terminal control characters are not allowed in reply text.")

    def reply(self, session, text):
        if self._prepared != (session.get("id"), session.get("sessionId"), session.get("pid")):
            reject("ETARGET", "Reply target has not passed the read-only identity checks.")
        if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > MAX_REPLY or "\0" in text:
            reject("EMESSAGE", "Reply text must be nonempty UTF-8 without NUL and at most 64 KiB.")
        self.check_text(text)
        if validate_process_pair(self._worker_pid, session["pid"]) != self._process_pair:
            reject("ECHANGED", "The native worker/REPL changed after preparation. No reply was sent.")
        # Repeat only read-only negotiation/identity immediately before mutation.
        # There is deliberately no retry of reply, even after an unknown ACK.
        self.probe()
        job = self._job(session)
        if job.get("pid") != self._worker_pid:
            reject("ECHANGED", "The native target worker changed after preparation.")
        if job.get("cliVersion") != self._worker_version:
            reject("ECHANGED", "The native target worker build changed after preparation. No reply was sent.")
        if self._route == AGENTS_UI and self._awaiting_input(session, job):
            reject("EBLOCKED", BLOCKED)
        try:
            token = self._auth()
        except BridgeError:
            raise
        except (OSError, UnicodeError):
            reject("EAUTHFILE", "The normal local supervisor control key is unavailable.")
        if validate_process_pair(self._worker_pid, session["pid"]) != self._process_pair:
            reject("ECHANGED", "The native worker/REPL changed after preparation. No reply was sent.")
        request = {"proto": PROTOCOL, "op": "reply", "short": session["id"], "text": text, "auth": token}
        if self._route == NEXT_TURN:
            # Native safe-boundary queue semantics, including while idle.
            request["nextTurn"] = True
        try:
            response = self._rpc(request, mutating=True)
        finally:
            # This client object is single-attempt too, including after a dropped ACK.
            self._prepared = None
        if response == {"ok": True, "op": "reply"}:
            return {"accepted": True, "queued": True, "observed": False,
                    "id": session["id"], "sessionId": session["sessionId"],
                    "protocol": PROTOCOL, "daemon_version": self.daemon_version,
                    "worker_version": self._target["worker_version"], "skew": self._target["skew"],
                    "route": self._route, "reviewed_build": self._target["reviewed_build"]}
        code = response.get("code")
        # Only reviewed pre-enqueue refusals can establish that nothing was accepted.
        if response.get("ok") is False and isinstance(code, str) and code in {
                "EAUTH", "EPROTO", "ESTARTING", "ERESPAWNING", "ESKEW", "ENOJOB", "ENOREPLY"}:
            raise BridgeError(code, "The supervisor refused the reply (%s). No retry was made." % code)
        raise BridgeError("EACK", "The reply acknowledgement was not recognized. Do not resend.", uncertain=True)


BLOCKED = ("The session is waiting on a question, permission or dialog. On a different-build worker an ordinary "
           "reply could answer it, so answer it in the agents UI (or send again once it is busy or idle).")
