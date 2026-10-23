# Native reply regression tests

Run from the repository root:

```bash
python3 -m unittest discover -s skills/claude-code/tests -v
python3 -m py_compile skills/claude-code/scripts/cc_sessions.py skills/claude-code/scripts/cc_native_reply.py skills/claude-code/scripts/cc_outbox.py
```

The suite uses a temporary fake configured CLI plus a real temporary Unix socket,
strict local permissions and kernel peer checks. It never uses a model, the real
Claude CLI, a user's credential, session, or native registry. Fixture subprocesses
receive isolated CLI/config/state paths. No global cwd mutation is used.

The three realistic prompts in `../evals/evals.json` have deterministic command
routing expectations. `EvalTests` executes those routes against fixtures. This
validates helper behavior, not whether a language model chooses the correct tool.

`test_native_compatibility.py` adds exact native `2.1.300 (Claude Code)` version
output, strict build suffix rejection, reviewed CLI/supervisor combinations,
matching-worker enforcement, isolated subprocess busy/idle sends with a real
fixture parent/child pair, receipt dedupe, unknown-outcome suppression, fresh
config refusal, config-derived socket hashing, auth failures, and the explicit
`2.1.293` refusal for its missing queue-format capability. These are still fake
CLI/supervisor tests, not real Claude/model tests. See
`../reference/standalone-compatibility.md` for the static review and separate
operator-owned standalone canary procedure.

## Contract and operational limits

`../reference/native-reply-contract.json` records only independently described
wire shapes and exact reviewed versions. It contains no vendor implementation,
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

Unsupported builds/skew must produce a refusal with Space-peek agents UI guidance.
Fake tests and a read-only `doctor` are not evidence of live message consumption.
