# Capability-based private reply compatibility

## Why not an exact build list

The configured CLI only supplies version/session reads. It does not send the
reply. Requiring its patch/build number to appear in an allowlist blocks a normal
update even when the live supervisor, worker and queue protocol are unchanged.
Conversely, trusting every version advertising `proto: 1` is too weak: ping alone
does not promise safe next-turn handling or no PTY fallback.

The adapter now requires both live negotiation and a reviewed structural contract.
No build numbers authorize a reply. Numeric version syntax remains strict so
suffixed, truncated or ambiguous output cannot be mistaken for an identity.
Worker/supervisor version equality is still required by the next-turn contract.

## Official route checked first

On the review date the configured wrapper's `--help` and `agents --help` exposed
JSON listing, attach, logs, stop and background creation, but no documented
noninteractive same-session reply command. The official agent-view page describes
Space-peek replies; ordinary dispatch creates new work. Native internal reply
clients can retry and start a supervisor, which would violate this helper's
single-attempt/no-start contract. None are invoked by this change.

Do not guess a new send command, run resume, or automate UI keystrokes. If an
official reply API appears later, review its exact identity, restart and retry
semantics before choosing it. The supported human fallback is still the agents UI.

## Gates, in order

1. Use the configured `CLAUDE_BIN`, unchanged, for CLI reads. Parse one complete
   native or four-component wrapper version; do not truncate extra suffixes.
2. Validate canonical config/socket paths, private directories and local key
   ownership. Connect only to the normal existing endpoint. Missing endpoint is
   `ENODAEMON`, not a reason to initialize state or start a daemon.
3. Pin socket inode/ctime and kernel peer UID/PID. Require explicit integer
   protocol 1 and integer `carriedPromptsFormat: 1`; booleans, floats, omissions,
   malformed frames and duplicate JSON keys do not negotiate a capability.
4. Resolve the supervisor executable through the kernel, never through argv or
   a guessed installation directory. Inspect its image read-only, bounded to
   512 MiB and three 24 KiB fragments. Require exactly one reply handler,
   handoff method and next-turn receiver with a reviewed fingerprint tuple.
5. Correlate the exact canonical CLI short ID and UUID with one supervisor job,
   daemon backend, available state and live same-user worker/REPL. Require exact
   worker/supervisor version equality and the same attested executable image.
6. Pin process start identities and executable device/inode/size/mtime/ctime.
   Before the only mutating write, repeat negotiation, target correlation and
   process checks. Do not silently re-attest a replacement process or image.
7. Keep the existing durable unknown reservation, locks, stable request keys,
   strict ACK classification, zero reply retries and retired watcher behavior.
   Repeat keys return the old receipt even if a newer build would now be refused.

`doctor` performs only these reads, never writes receipts or authenticates a
mutating probe. `auth_file_valid` is not `auth_verified`. A targeted doctor also
checks exact worker identity; an untargeted doctor cannot establish that.

## Structural attestation is deliberately conservative

The standard-library lexer normalizes horizontal whitespace and consistent
minifier-local identifier renaming. It preserves runtime dependency names,
properties (including shorthand and method names), numeric/string literals,
branch structure, operators, template expressions and line breaks. A small
conservative delimiter context distinguishes clear statement bodies from object
or destructuring keys; uncertain names are retained. Only the reviewed flat build
metadata object used as `.VERSION` is replaced with a version placeholder.
Comments, nested template expressions, unknown syntax, unbalanced or
absent/duplicate/truncated fragments and changed fingerprints are refused.
Fingerprints are never auto-learned.

The initial candidate's normalizer could conflate changed runtime names,
shorthand keys and hexadecimal/exponent literals. Review on 2026-10-29 tightened
those cases, added negative regressions and a final process-start recheck before
the mutating write. The revised tuple was recomputed only after each inspected
image matched the previous reviewed tuple, then compared across all four
previously inspected images. No new binary was trusted merely to make it pass.

Only hashes are published. The local image is never executed, imported, copied,
logged or written to disk by the attestor. Tests use independently written small
syntax fixtures, not vendor source or excerpts. The fixture attestor is confined
to the tests and cannot be enabled with a production environment variable.

The three normalized fingerprints were identical for the inspected standalone
2.1.300/2.1.312 and wrapper 2.1.311.1423/2.1.312.1459 macOS artifacts. Build number
changes and minifier renaming alone therefore do not require a helper update.
The prior standalone support remains; there is no wrapper bypass or automatic
selection of another installation.

## Residual limits and review triggers

This remains an unsupported private adapter. Structural equivalence is not a
vendor signature or a proof of every dependency's behavior. The fingerprints
cover the queue entry points, not all code in the executable. A same-user
malicious replacement with copied markers is outside the local trust model, as
are other clients deliberately racing the helper. Socket/path/UID checks are
not relaxed to make an unknown installation work.

Embedded-source layout changes, a new minifier transformation, platform-specific
handler differences or an interpreter-based installation can fail closed even
when the vendor UI still works. The current image check expects native executable
processes; an npm/Node process cannot be attested merely because Node is trusted.
macOS and Linux kernel image lookup are implemented, but this review's live
verification is macOS only. Other POSIX platforms and Windows cannot send here;
ordinary CLI commands on Windows retain their previous behavior.

The wire reply still addresses a short ID. The helper verifies its full UUID,
worker, REPL, process starts and image immediately beforehand, but the private
protocol has no atomic full-UUID compare-and-send field. No stronger guarantee is
claimed. Similarly, an ACK establishes queue acceptance only, not consumption,
and multiple messages may be combined into a turn. Receipts provide local
at-most-one attempt while that state/config/key is retained, not exactly-once
delivery across clients or state deletion.

If `ECONTRACT` appears, inspect the changed handler and dependencies read-only,
review queue/auth/refusal behavior, and add a new fingerprint only after a
separate code review and offline negatives. Do not copy proprietary source or
real session data into tests/review artifacts. If the existing process/image
cannot be established, stop and use the human route. Never restart a shared
supervisor or manufacture proof from a matching version number.

## Validation status (2026-10-29)

The tightened adapter passed a live read-only probe on wrapper 2.1.312.1459
with supervisor 2.1.312, protocol 1 and queue format 1. The original smoke
session had already exited (no live PID/status), so its targeted probe correctly
refused `ETARGET`; it was not resumed or replaced.

During the user-requested remaining validation, one separate no-tool diagnostic
session was created in plan mode using the configured wrapper. Its targeted
doctor passed, one harmless follow-up was accepted/queued, and its transcript
returned the exact response marker under the unchanged short ID/full UUID.
Repeating the identical request key returned `duplicate_suppressed: true` and
the same original receipt without another send. Initial and follow-up responses
used no tools. The normal receipt state was retained. No work session, auth,
registry, daemon, permission default or installation was changed by this canary.
This establishes this idle macOS 312 case, not all future versions or busy
states. Earlier 309 and standalone 300 live evidence remains historical.

Public semantics: https://code.claude.com/docs/en/agent-view.md
