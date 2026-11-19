# agy lifecycle behaviour this skill relies on

Observed on 2026-11-18 with agy **1.5.12** (macOS arm64, Google sign-in), in throwaway
git repositories, using only harmless prompts. Re-check after agy updates. `doctor`
checks the required flags on every spawn, but not the behaviour below.

Sources: `agy --help`, `agy help <subcommand>`, `agy changelog`, and the docs at
https://antigravity.google/docs/cli/headless/, .../cli/reference/,
.../cli/conversations/ and .../cli/commands/resume/.

## Supported and used

| Behaviour | Evidence |
|---|---|
| `agy --print=TEXT --output-format stream-json` runs one turn and exits | Docs (headless); observed |
| NDJSON: `init` {`cwd`, `tools`, `permission_mode`}, `step_update` {`conversation_id`, `step_index`, `state`, `step_type`, `tool_name`, `tool_info`, `text_delta`}, final `result` {`conversation_id`, `status`, `response`, `num_turns`, `finished_reason`, `denied_actions`} | Docs; observed |
| `--conversation <uuid>` continues that conversation in a new process (`num_turns` grows, the model remembers the earlier turn) | Docs ("resume a specific conversation using an ID"); observed |
| SIGINT ends the turn: exit 1, `status: ERROR`, `error`/`finished_reason: interrupted`; the `run_command` child (`sleep`) was cleaned up | Docs ("INTERRUPTED (e.g., SIGINT)"); observed |
| `--print-timeout` cut-off exits 3 with `finished_reason: print_timeout` | Changelog 1.5.0 (not reproduced) |
| An approval headless mode cannot ask for is auto-denied: exit 0, `status: SUCCESS`, `denied_actions: [...]`, explanation on stderr | Docs ("soft-denied"); observed with a write outside the workspace |
| `--log-file PATH` writes that turn's CLI log there | `--help`; observed |
| `--print=-text` passes text that starts with a dash safely | Observed |

## Hazards the helper guards against

| Behaviour | Guard |
|---|---|
| `--conversation` with an unknown id prints `warning: conversation "<id>" not found`, **starts a new conversation**, and exits 0 | Pre-check that `<AGY_DATA_DIR>/conversations/<id>.db` exists. The runner aborts on the warning or a different id (`EREPLACED`) and keeps the original id |
| `--conversation` from another folder resumes the conversation but reports the new folder as its `cwd` | Follow-ups always run from the recorded folder. The runner aborts if `init.cwd` differs (`ECWD`) |
| SIGTERM to agy's process group ended agy (exit 1) but **orphaned** its `sleep` child | `stop` uses SIGINT first; SIGTERM only after 15 s, with a warning |
| Exit 0 does not mean the work was done (soft denials) | State `denied` when `denied_actions` is present |

## Not supported in agy 1.5.12, therefore not offered

- Native detached or background sessions for coding tasks (`--bg`-style). `agy
  remote-control` is a boot/login daemon for the browser Remote Control view;
  starting it would register a system service, so the helper never touches it.
- A command that lists conversations or reports a conversation's live state.
- Sending a message to a running headless turn. `--input-format stream-json` and `agy
  acp` can take several prompts, but only from the single process that owns stdin. A
  separate client cannot join a running turn, so `send` refuses while a turn runs.
- Answering a permission prompt or question from outside an interactive session.
- Proof that the model acted on a message beyond the turn's own `result`.

## Trust, sign-in, configuration

Headless 1.5.12 did not show a folder-trust prompt for new folders or worktrees. It did
not add them to `trustedWorkspaces`. Without a cached sign-in, the docs say headless
exits with "authentication required" instead of hanging. A headless run updates only
agy's own state (conversation store, `cache/last_conversations.json`, logs).
`settings.json`, the trust lists and sign-in files had the same checksum before and
after the smoke tests.
