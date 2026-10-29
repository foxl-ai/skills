"""Read-only structural attestation for the private queue-v1 adapter.

This is independent helper code, not vendor implementation. Only fingerprints
of reviewed control-flow tokens are distributed. Nothing is imported/executed
from a Claude image. A new version number is not a capability; an unchanged
reviewed handler structure AND live protocol negotiation are required.
"""
import ctypes
import ctypes.util
import hashlib
import json
import mmap
import os
from pathlib import Path
import re
import stat
import sys

# Limits keep an absent or ambiguous embedded-source layout a bounded refusal.
MAX_IMAGE = 512 * 1024 * 1024
MAX_FRAGMENT = 24000
IDENT = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
KEYWORDS = frozenset("async await break case catch class const continue debugger default delete do else export extends false finally for function if import in instanceof let new null of return super switch this throw true try typeof undefined var void while with yield".split())
# Runtime names are semantic dependencies, not minifier-local aliases. Retaining
# them also conservatively refuses a build that shadows one of these names.
RUNTIME_NAMES = frozenset((
    "AbortController AbortSignal AggregateError Array ArrayBuffer Atomics BigInt BigInt64Array BigUint64Array "
    "Boolean Buffer Bun DataView Date Deno Error EvalError FinalizationRegistry Float32Array Float64Array "
    "Function Infinity Int8Array Int16Array Int32Array Intl JSON Map Math NaN Number Object Promise Proxy "
    "RangeError ReferenceError Reflect RegExp Set SharedArrayBuffer String Symbol SyntaxError TextDecoder "
    "TextEncoder TypeError URIError Uint8Array Uint8ClampedArray Uint16Array Uint32Array URL URLSearchParams "
    "WeakMap WeakRef WeakSet WebAssembly arguments console process global globalThis module require exports "
    "setTimeout setInterval setImmediate clearTimeout clearInterval clearImmediate queueMicrotask fetch "
    "parseInt parseFloat isNaN isFinite decodeURI decodeURIComponent encodeURI encodeURIComponent escape "
    "unescape eval structuredClone"
).split())
NUMBER = re.compile(r"(?:0[xX][0-9a-fA-F]+n?|0[bB][01]+n?|0[oO][0-7]+n?|[0-9]+n|(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)")
OPERATORS = tuple(sorted(("===", "!==", "=>", "==", "!=", "<=", ">=", "&&", "||", "??", "?.",
                          "++", "--", "+=", "-=", "*=", "%=", "**", "<<", ">>", ">>>", "...",
                          "&&=", "||=", "??=", "**=", "<<=", ">>=", ">>>="), key=len, reverse=True))


class ContractError(Exception):
    pass


def tokens(source):
    """Small conservative lexer for the three bounded function fragments.

    No evaluation, no arbitrary JavaScript parsing. Unsupported lexical forms
    fail closed. Template expressions are tokenized recursively but cannot
    contain nested braces/templates; identifiers keep the same alias mapping.
    """
    out, i = [], 0
    while i < len(source):
        c = source[i]
        if c.isspace():
            # Newlines can change JavaScript via automatic semicolon insertion.
            # Do not normalize them into spaces and approve changed control flow.
            if c in "\r\n\u2028\u2029":
                out.append(("newline", c))
            i += 1
            continue
        if source.startswith("//", i) or source.startswith("/*", i):
            raise ContractError("comments require structural re-review")
        if c in "\"'`":
            start, quote = i, c
            i += 1
            while i < len(source):
                if source[i] == "\\":
                    i += 2
                elif source[i] == quote:
                    i += 1
                    break
                else:
                    i += 1
            else:
                raise ContractError("unterminated literal")
            value = source[start:i]
            if quote == "`":
                pieces = re.split(r"(\$\{[^}]*\})", value)
                for part in pieces:
                    if part.startswith("${"):
                        if any(char in part[2:-1] for char in "{}`"):
                            raise ContractError("unsupported template expression")
                        out.append(("punct", "${"))
                        out.extend(tokens(part[2:-1]))
                        out.append(("punct", "}"))
                    elif part:
                        out.append(("literal", part))
            else:
                out.append(("literal", value))
            continue
        match = IDENT.match(source, i)
        if match:
            value = match.group()
            out.append(("id", value))
            i = match.end()
        elif c.isdigit() or (c == "." and source[i + 1:i + 2].isdigit()):
            match = NUMBER.match(source, i)
            if match is None or (match.end() < len(source) and
                                 (source[match.end()].isalnum() or source[match.end()] in "_$")):
                raise ContractError("unsupported numeric literal")
            out.append(("number", match.group()))
            i = match.end()
        elif c == "/":
            # These adapter fragments do not need regex/division. Refuse rather
            # than accidentally treating braces inside a regex as source code.
            raise ContractError("unsupported slash token")
        elif c in "{}()[];:,.?!~+-*=<>%&|^":
            operator = next((op for op in OPERATORS if source.startswith(op, i)), c)
            out.append(("punct", operator))
            i += len(operator)
        else:
            raise ContractError("unsupported token")
    return out


def fragment(image, marker, kind):
    """Select exactly one executable-source-shaped fragment, never a string pool."""
    matches = []
    for hit in re.finditer(marker, image):
        start = hit.start()
        part = image[start:start + MAX_FRAGMENT]
        # The markers end at the method/function's opening brace.
        opening = hit.end() - start - 1
        depth, i, quote = 0, opening, None
        while i < len(part):
            c = part[i]
            if quote is not None:
                if c == 92:  # escape
                    i += 2
                    continue
                if c == quote:
                    quote = None
            elif c in (34, 39, 96):
                quote = c
            elif c == 123:
                depth += 1
            elif c == 125:
                depth -= 1
                if depth == 0:
                    matches.append(part[:i + 1].decode("utf-8"))
                    break
            i += 1
        else:
            raise ContractError(kind + " fragment exceeds limit or is incomplete")
    if len(matches) != 1:
        raise ContractError(kind + " fragment is absent or ambiguous")
    return matches[0]


def canonical(source):
    seq = tokens(source)
    # A build's metadata literal is not queue behavior. Only replace the known
    # flat metadata object used as .VERSION, not arbitrary objects or constants.
    clean, i = [], 0
    while i < len(seq):
        if seq[i] == ("punct", "{") and seq[i + 1:i + 3] == [("id", "ISSUES_EXPLAINER"), ("punct", ":")]:
            end = i + 1
            while end < len(seq) and seq[end] != ("punct", "}"):
                end += 1
            part = seq[i + 1:end]
            expected_keys = {"ISSUES_EXPLAINER", "PACKAGE_URL", "README_URL", "VERSION", "FEEDBACK_CHANNEL", "BUILD_TIME", "GIT_SHA", "HOOKS_WORKER_URL", "DD_SOURCEMAP_GROUP"}
            fields = [part[j:j + 3] for j in range(0, len(part), 4)]
            keys = [field[0][1] for field in fields if len(field) == 3]
            valid = (end < len(seq) and len(part) % 4 == 3 and set(keys) == expected_keys and
                     len(keys) == len(expected_keys) and all(len(f) == 3 and f[0][0] == "id" and
                     f[1] == ("punct", ":") and f[2][0] == "literal" for f in fields) and
                     all(part[j] == ("punct", ",") for j in range(3, len(part), 4)) and
                     seq[end + 1:end + 3] == [("punct", "."), ("id", "VERSION")])
            if not valid:
                raise ContractError("build metadata shape changed")
            clean.append(("metadata", "build-version"))
            i = end + 3
        else:
            clean.append(seq[i])
            i += 1
    aliases, normalized = {}, []
    significant = [i for i, token in enumerate(clean) if token[0] != "newline"]
    before = {position: significant[n - 1] if n else None for n, position in enumerate(significant)}
    after = {position: significant[n + 1] if n + 1 < len(significant) else None
             for n, position in enumerate(significant)}
    contexts, stack = {}, []
    for i in significant:
        kind, value = clean[i]
        contexts[i] = stack[-1] if stack else None
        if kind != "punct":
            continue
        if value in ("(", "[", "{", "${"):
            previous = clean[before[i]][1] if before[i] is not None else None
            # Only unmistakable statement bodies are classified as blocks.
            # Everything else is object/pattern-like, retaining observable keys.
            block = previous in (")", "=>", "else", "try", "finally", "do")
            if value == "{" and previous == ":":
                j = before.get(before[i])
                k = before.get(j)
                block = k is not None and clean[k] == ("id", "case")
            stack.append(("{" if value == "${" else value, value == "{" and not block))
        elif value in (")", "]", "}"):
            wanted = {")": "(", "]": "[", "}": "{"}[value]
            if not stack or stack[-1][0] != wanted:
                raise ContractError("unbalanced structural fragment")
            stack.pop()
    if stack:
        raise ContractError("unbalanced structural fragment")
    for i, (kind, value) in enumerate(clean):
        prev_index, next_index = before.get(i), after.get(i)
        previous = clean[prev_index][1] if prev_index is not None else None
        following = clean[next_index][1] if next_index is not None else None
        if kind == "id" and value not in KEYWORDS and value not in RUNTIME_NAMES:
            # Object/pattern shorthand names are observable; declaration names
            # inside known statement bodies and parameters are minifier-local.
            shorthand = (contexts.get(i) == ("{", True) and previous in ("{", ",") and
                         following in (",", "}", "="))
            method_name = False
            if following == "(":
                depth, j = 0, next_index
                while j < len(clean):
                    if clean[j] == ("punct", "("):
                        depth += 1
                    elif clean[j] == ("punct", ")"):
                        depth -= 1
                        if depth == 0:
                            next_token = after.get(j)
                            method_name = (next_token is not None and clean[next_token] == ("punct", "{") and
                                           previous != "function")
                            break
                    j += 1
            if previous not in (".", "?.") and following != ":" and not shorthand and not method_name:
                value = aliases.setdefault(value, "v" + str(len(aliases)))
        normalized.append((kind, value))
    return json.dumps(normalized, separators=(",", ":"), ensure_ascii=True).encode("ascii")


MARKERS = {
    "supervisor_reply": rb'case\s*[\"\']reply[\"\']\s*:\s*\{',
    "worker_handoff": rb'async\s+reply\s*\([^\n]{1,120}?\)\s*\{',
    "worker_receive": rb'function\s+[A-Za-z_$][\w$]*\([A-Za-z_$][\w$]*\)\{(?=if\([A-Za-z_$][\w$]*\.nextTurn===!0\))',
}


def fingerprints(image):
    return {name: hashlib.sha256(canonical(fragment(image, marker, name))).hexdigest()
            for name, marker in MARKERS.items()}


def process_image(pid):
    """Kernel-derived executable path, not ps argv (which a process can rename)."""
    if type(pid) is not int or pid <= 0:
        raise ContractError("invalid process identity")
    try:
        if sys.platform == "darwin":
            library = ctypes.CDLL(ctypes.util.find_library("proc"), use_errno=True)
            call = library.proc_pidpath
            call.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
            call.restype = ctypes.c_int
            buf = ctypes.create_string_buffer(4096)
            count = call(pid, buf, len(buf))
            if count <= 0 or count >= len(buf):
                raise ContractError("kernel executable identity unavailable")
            path = os.fsdecode(buf.value)
        elif sys.platform.startswith("linux"):
            path = os.readlink("/proc/%d/exe" % pid)
        else:
            raise ContractError("kernel executable identity unsupported")
        if not os.path.isabs(path) or path.endswith(" (deleted)"):
            raise ContractError("process executable unavailable")
        return Path(os.path.realpath(path))
    except (OSError, AttributeError, TypeError, ValueError):
        raise ContractError("kernel executable identity unavailable") from None


def file_identity(path):
    # Import lazily to avoid the bridge/attestor dependency cycle.
    from cc_native_reply import safe_ancestors
    safe_ancestors(path.parent)
    st = os.lstat(path)
    if (not stat.S_ISREG(st.st_mode) or st.st_uid not in (0, os.getuid()) or
            st.st_mode & 0o022 or not st.st_mode & 0o111 or not 0 < st.st_size <= MAX_IMAGE):
        raise ContractError("process executable has unsafe ownership, mode or size")
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def attest_image(path):
    """Attest the installed image against reviewed structural fingerprints.

    Artifact stat identity is pinned before/after the read. Hashes are not a
    signature: same-user hostile replacement is outside this local trust model.
    No path or source bytes are returned in the public diagnostic report.
    """
    before = file_identity(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        if (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns) != before:
            raise ContractError("executable changed while opening")
        with mmap.mmap(fd, 0, access=mmap.ACCESS_READ) as image:
            found = fingerprints(image)
        if file_identity(path) != before:
            raise ContractError("executable changed while inspecting")
    finally:
        os.close(fd)
    spec = json.loads((Path(__file__).resolve().parents[1] /
                       "reference/native-reply-contract.json").read_text(encoding="utf-8"))
    for contract in spec["structural_contracts"]:
        if found == contract["sha256"]:
            return before, contract["id"]
    raise ContractError("reply/handoff/receive structure differs from reviewed queue-v1 contracts")


class ProcessAttestation:
    def __init__(self):
        self.peer = None
        self.image = None
        self.identity = None
        self.contract_id = None
        self.target = None

    def supervisor(self, peer_pid):
        from cc_native_reply import validate_process_pair
        stamp = validate_process_pair(peer_pid, peer_pid)
        image = process_image(peer_pid)
        if self.peer is not None:
            if (peer_pid, stamp) != self.peer or image != self.image or file_identity(image) != self.identity:
                raise ContractError("supervisor process or executable changed")
            return self.contract_id
        identity, contract = attest_image(image)
        self.peer = (peer_pid, stamp)
        self.image, self.identity, self.contract_id = image, identity, contract
        return contract

    def worker(self, worker_pid, repl_pid):
        # Matching version text is insufficient: require the exact live image
        # already attested for the supervisor, plus the bridge's UID/start pair.
        if self.peer is None:
            raise ContractError("supervisor was not attested")
        for pid in {worker_pid, repl_pid}:
            path = process_image(pid)
            if path != self.image or file_identity(path) != self.identity:
                raise ContractError("worker/REPL executable differs from the supervisor")
        current = (worker_pid, repl_pid)
        if self.target is not None and current != self.target:
            raise ContractError("worker process identity changed")
        self.target = current
        return self.contract_id
