# Native reply regression tests

Run from the repository root:

```bash
python3 -B -m unittest discover -s skills/claude-code/tests -v
python3 -B -c 'import ast, pathlib; [ast.parse(p.read_text()) for p in pathlib.Path("skills/claude-code/scripts").glob("*.py")]'
```

The suite uses a temporary fake configured CLI plus a real temporary Unix socket,
strict local permissions and kernel peer checks. It never uses a model, the real
Claude CLI, a user's credential, session, or native registry. Fixture subprocesses
receive isolated CLI/config/state paths. No global cwd mutation is used.

The realistic prompts in `../evals/evals.json` have deterministic command routing
expectations. `EvalTests` executes those routes against fixtures. This validates
helper behavior, not whether a language model chooses the correct tool.

`test_native_compatibility.py` retains standalone output, auth, socket hashing,
process-pair and no-daemon regressions. `test_toolbox_310.py` preserves the installed
310 regressions; assertions about numeric allowlists are now capability checks.
`test_capability_gate.py` adds future versions, CLI/supervisor skew, worker skew,
malformed negotiation, insufficient structural evidence, changed UUID/process/image,
unknown receipts across upgrades, platform negatives and conservative lexer tests.
The tiny independently written syntax fixtures are not vendor source excerpts.

Transport tests still exercise real private Unix sockets, kernel peer/image lookup,
process UID/start times and safe file checks. Since the test supervisor is Python,
`fixture_attestation.py` substitutes only its image fingerprint and refuses any
image other than that test interpreter. It is not imported by production and
cannot be enabled through a production environment variable. Subprocess tests use
`isolated_runner.py`, which first requires CLI/config/state/socket fixture roots.
Use `-B` when testing a read-only installed baseline. Host overload can exhaust the
intentionally short timeout case; do not change production timeouts to hide it.
See `../reference/compatibility.md` for supported proof limits.

## Contract and operational limits

`../reference/native-reply-contract.json` records only independently described
wire shapes, structural hashes and historical evidence. It contains no vendor implementation,
secret, native session ID, prompt history or user path.

Every follow-up uses a read-only CLI lookup plus supervisor ping/list to verify
short ID, full session UUID, daemon backend and worker version. The supervisor's
PID identifies its worker, while `agents --json` identifies the REPL child, as
observed in the live 2.1.309 canary. Both must be same-user live processes, either
the same PID or a direct parent/child pair. Their process start times and
relationship are rechecked immediately before reply. The bridge
pins the socket identity and kernel peer across checks and reply, uses normal
local auth, sets `nextTurn: true`, and sends exactly once. There is no daemon
startup, auth refresh retry, registry edit, CLI resume, fork, or queue watcher.

Receipts in `native-replies-v1/` are separate from Claude's own files. A fsynced
unknown reservation precedes the only reply attempt. ACK means accepted, not
consumed. Connection loss, timeout, unknown error/ACK or crash after reservation
remain unknown. Reusing a key returns the receipt. No receipt pruning means
idempotency lasts only as long as that state is retained. Clearing state, switching
state directories, changing request keys, or sending from other clients can
create duplicates. This is not a daemon exactly-once contract.

Legacy queues are read as disabled history, including connected copy lineage.
Stale, branching or cyclic aliases fail closed rather than redirecting. Explicit
stop/clear cancels legacy pending entries. The mutation guard refuses active old
watcher PIDs/locks, but cannot neutralize an old helper installed somewhere else
or one deliberately started after migration. Retire old watchers before install
and do not mix old/new helper binaries. No migration step deletes sessions.

## Optional operator-owned live canary

Not part of the test suite. Requires explicit permission to create a disposable
new task and to send/stop only that task. Use the normal configured CLI or wrapper,
trusted scratch folder, minimal permissions and an unmistakable test name.
A standalone canary must explicitly select its native executable and keep its
private HOME/config/state separate. Never change an installed skill, bypass a
configured wrapper or fabricate a new trust grant to run this optional test.

1. Record the pre-test native IDs and create one intentionally new session with
   `spawn`. Never select another person's existing session.
2. Run `doctor <exact-test-id> --json`. Supervisor and worker versions must match
   a reviewed contract. Do not restart a shared supervisor to force the test.
3. While the canary is busy, send a harmless uniquely tagged instruction with a
   stable request key. Repeat the exact request/key. Expect one accepted receipt,
   then `duplicate_suppressed: true`, the same short ID/UUID and no second session.
4. Inspect its transcript to establish whether/when the marker was consumed.
   Repeat with a different key while idle. Do not infer consumption from ACK.
5. Stop only the test session with explicit authorization. Never use rm or delete
   an unrelated worktree as part of the test. Capture scrubbed counts/versions,
   not credentials or other sessions' histories.

Incompatible structures/protocols or worker skew must produce a refusal with
Space-peek agents UI guidance, not a request to blindly allow a new build.
Fake tests and a read-only `doctor` are not evidence of live message consumption.
If authorization is limited to one existing smoke session, do not run the optional
create/busy/idle/stop sequence above. Use only its exact UUID and one authorized
harmless follow-up, keep the normal state directory, and re-read the same receipt
key to verify suppression. Inspect only that session's transcript for consumption.
