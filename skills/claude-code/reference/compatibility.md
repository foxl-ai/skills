# Capability-based private reply compatibility

## Version skew policy (2026-11-13)

Claude Code (especially Toolbox, channel head) updates often. A newer supervisor
routinely adopts sessions that keep running an older build, and the updater may
delete that older binary while the session is still alive. On 2026-11-13 this
helper refused every follow-up to such a session (`ESKEW`) and the owner had to
type replies into `claude agents` by hand. The policy is now permissive:

- **Informational, never a refusal by itself:** CLI vs supervisor version, worker
  vs supervisor version, an unparseable or suffixed CLI version label, a suffixed
  or future supervisor version, a worker running a different (or deleted)
  executable, a supervisor build whose reply structure is unreviewed, missing or
  oversized, and new job-state names. Results carry `cli_version`,
  `daemon_version`, `worker_version`, `skew`, `route`, `reviewed_build`,
  `supervisor_image`, `worker_image` and a short `warnings` list.
- **Route choice:** the supervisor itself refuses `nextTurn: true` unless the
  job's `cliVersion` equals its own version ("it runs a different Claude Code
  build"). So a same-build worker gets the reviewed `nextTurn: true` request
  (`next-turn-queue`). A different-build worker gets exactly the request the
  `claude agents` reply box sends, without `nextTurn` (`agents-ui-reply`), which
  the supervisor does not version-gate. Without `nextTurn` the worker treats text
  like typed input: a leading `!` runs a shell command, a leading `/` a slash
  command, a pending question may be answered, and a busy session gets a
  bracketed paste plus Enter. The helper therefore refuses, on that route only
  and before any receipt: text starting with `/` or `!` (`ECOMMAND`), terminal
  control characters other than newline/tab (`EMESSAGE`), and a target whose
  agents status is not `busy`/`idle` or whose session/job state or tempo is
  `blocked` (`EBLOCKED`).
- **Still refused (unsafe or impossible):** ping without integer protocol 1 and
  `carriedPromptsFormat: 1`, or a missing/garbage version identity (`EPROTO`);
  a wrong UUID, ambiguous, dying, exited, stopped, legacy or non-daemon target
  (`ETARGET`); unsafe or foreign socket, control-key or executable ownership
  (`EPATH`, `EAUTHFILE`, `EPEER`); a rejected key (`EAUTH`); and the supervisor
  socket/peer/version, worker PID/start/build or any pinned image changing
  mid-request (`ECHANGED`). The supervisor's own pre-accept refusals (including
  its `ESKEW` if a worker changes in a race) stay `rejected` with no retry.
- **Unchanged protections:** a fsynced `unknown` receipt before the only write,
  no automatic resend, request-key dedupe across upgrades, and no daemon start or
  restart, resume, stop, respawn, registry/queue/auth edit to get a send through.

## Why not an exact build list

The configured CLI only supplies version/session reads. It does not send the
reply. Requiring its patch/build number to appear in an allowlist blocks a normal
update even when the live supervisor, worker and queue protocol are unchanged.
Conversely, trusting every version advertising `proto: 1` is too weak: ping alone
does not promise safe next-turn handling or no PTY fallback.

Live negotiation authorizes a reply; build numbers neither authorize nor refuse
one. Version text is never truncated: one complete token is reported whole, and
ambiguous CLI output is reported as unknown. Until 2026-11-13 a reviewed
structural contract and worker/supervisor version equality were also required;
both are now reported instead (see the policy above).

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

1. Use the configured `CLAUDE_BIN`, unchanged, for CLI reads. Report one complete
   version token; ambiguous or unreadable output is reported as `null`.
2. Validate canonical config/socket paths, private directories and local key
   ownership. Connect only to the normal existing endpoint. Missing endpoint is
   `ENODAEMON`, not a reason to initialize state or start a daemon.
3. Pin socket inode/ctime and kernel peer UID/PID. Require explicit integer
   protocol 1 and integer `carriedPromptsFormat: 1`; booleans, floats, omissions,
   malformed frames and duplicate JSON keys do not negotiate a capability. The
   ping version must be one token (letters, digits, `.+_-`, at most 80 chars).
4. Resolve the supervisor executable through the kernel, never through argv or
   a guessed installation directory. Refuse only foreign ownership or group/world
   write access. Inspect its image read-only, bounded to 512 MiB and three 24 KiB
   fragments, and report `reviewed`, `unreviewed` or `unavailable`.
5. Correlate the exact canonical CLI short ID and UUID with one supervisor job,
   daemon backend, not-unavailable state and live same-user worker/REPL. Report
   worker version, `skew` and the worker image relation (`same-as-supervisor`,
   `different-image`, `unavailable`); choose the route from exact version equality.
6. Pin process start identities, worker build and executable path plus
   device/inode/size/mtime/ctime (or their absence). Before the only mutating
   write, repeat negotiation, target correlation and process checks. Any change is
   `ECHANGED`; nothing is silently re-attested.
7. Keep the existing durable unknown reservation, locks, stable request keys,
   strict ACK classification, zero reply retries and retired watcher behavior.
   Repeat keys return the old receipt even if a newer build would now be refused.

`doctor` performs only these reads, never writes receipts or authenticates a
mutating probe. `auth_file_valid` is not `auth_verified`. A targeted doctor also
checks exact worker identity and reports `route` and `send_ready`; an untargeted
doctor cannot establish that.

## Structural attestation (evidence, not a gate)

The standard-library lexer normalizes horizontal whitespace and consistent
minifier-local identifier renaming. It preserves runtime dependency names,
properties (including shorthand and method names), numeric/string literals,
branch structure, operators, template expressions and line breaks. A small
conservative delimiter context distinguishes clear statement bodies from object
or destructuring keys; uncertain names are retained. Only the reviewed flat build
metadata object used as `.VERSION` is replaced with a version placeholder.
Comments, nested template expressions, unknown syntax, unbalanced or
absent/duplicate/truncated fragments and changed fingerprints make the build
`unreviewed`. Fingerprints are never auto-learned; since 2026-11-13 an
unreviewed build is reported, not refused.

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
handler differences or an interpreter-based installation make a build
`unreviewed`; sends then rely on negotiation alone. The image check expects
native executable processes; an npm/Node process is reported as unreviewed, never
attested merely because Node is trusted.
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

If `reviewed_build: false` appears, sends continue on negotiation; review the
changed handler and dependencies read-only when convenient and add a new
fingerprint only after a separate code review and offline negatives. Do not copy
proprietary source or real session data into tests/review artifacts. `ECONTRACT`
now means only an internal failure to pin process evidence; stop and use the
human route. Never restart a shared supervisor to make a send work.

The `agents-ui-reply` route has the agents UI's semantics, not next-turn
semantics. The blocked/dialog check and the reply are separate reads, so a dialog
that opens in between could receive the text as its answer; the window is the
same as a human typing into the agents UI. The helper cannot set
`skipSlashCommands` on this route, which is why `/` and `!` text is refused there.

## Validation status (2026-11-13)

Live macOS state: Toolbox CLI 2.1.323.1727, supervisor 2.1.323 (its image
still matches `queue-v1-structural-1`; so does the installed 2.1.322.1722 image),
and an orchestrator session whose worker reports 2.1.322 and whose 2.1.322.1695
binary had been removed by the updater (kernel image lookup fails). The old
helper refused `doctor` and `send` with `ESKEW`. Read-only local inspection of the
2.1.323 image showed the supervisor refuses `nextTurn: true` for a different
build, and the agents UI reply box sends `reply` without `nextTurn`.

With this change, a targeted `doctor` on that session (read-only, no message
sent to it) passed with `skew: true`, `worker_version: 2.1.322`,
`daemon_version: 2.1.323`, `route: agents-ui-reply`, `worker_image: unavailable`
and two warnings. A separate throwaway plan-mode canary (same 2.1.323 build) was
created; one message with a fixed request key was sent through the full `send`
pipeline with the `agents-ui-reply` request forced by a test harness (the request a
skewed worker gets; the supervisor does not version-gate it, and both installed
builds share the reviewed receive structure). It was accepted, the identical key
returned `duplicate_suppressed: true` with no second send, and the transcript
showed the exact marker once with no tool use. The canary was then stopped; no
other session, the daemon, auth or registry was touched. The busy-session
(bracketed-paste) branch of that route was not live-tested here; it is the path
the agents UI uses for busy sessions.

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
