---
name: himalaya
description: "Read, search, send, reply to and file email over IMAP/SMTP (any provider) with the himalaya v2 CLI. Use when the user wants to work with an email account that is not connected as Microsoft 365 or Google, or asks for himalaya by name."
enabled: false
tags: email, imap, smtp, mail, cli
requires: [himalaya]
---

# himalaya (v2)

Docs: https://github.com/pimalaya/himalaya (v2 changed most commands; `MIGRATION.md` there lists them). Check `himalaya --version` says 2.x; v1 syntax (`--folder`, `message write`, `template send`) does not work on v2.

## Setup (user does this in their own terminal)

- Install: `brew install himalaya`, `cargo install himalaya`, or a release binary from GitHub.
- Run `himalaya` with no command: an interactive wizard discovers the account from the email address and writes `~/.config/himalaya/config.toml`. The agent cannot drive this wizard (no TTY in `exec`).
- Or write the file by hand, keeping the password in a password manager:

```toml
[accounts.personal]
default = true
email = "you@example.com"
display-name = "Your Name"
imap.server = "imap.example.com"            # bare host = imaps:// on 993
imap.sasl.plain.username = "you@example.com"
imap.sasl.plain.password.command = "security find-generic-password -s himalaya -w"
smtp.server = "smtp.example.com"            # bare host = smtps:// on 465; "smtp://host:587" for STARTTLS
smtp.sasl.plain.username = "you@example.com"
smtp.sasl.plain.password.command = "security find-generic-password -s himalaya -w"
message.send.save-copy = "sent"
```

(`security` is macOS; on Linux use `secret-tool lookup ...` or `pass show ...`.) Gmail and Outlook.com need an app password or OAuth; prefer the gws or outlook skills for those. Verify with `himalaya account check`.

## Commands

Add `--json` for machine-readable output and `-a NAME` for a non-default account. `-m` takes a mailbox name or role (`inbox`, `sent`, `drafts`, `trash`); default is the inbox.

```bash
himalaya account list
himalaya mailbox list
himalaya envelope list -s 20                         # newest first; -p 2 for the next page
himalaya envelope list -m sent -r
himalaya envelope search from alice and after 2026-10-01
himalaya envelope search subject invoice and not flag seen order by date desc
himalaya message read 42                             # headers + decoded text parts
himalaya message read 42 --raw                       # full RFC 5322 source
himalaya attachment list 42
himalaya attachment download 42 -d ~/Downloads
```

Search clauses: `date`, `after <yyyy-mm-dd>`, `from`, `to`, `subject`, `body`, `flag <seen|answered|flagged|draft>`, combined with `and`, `or`, `not`, parentheses, and `order by <date|from|to|subject> [asc|desc]`.

Writing (show the full message and get confirmation first). Without `--send`, compose/reply/forward only print the message, which is a safe preview:

```bash
himalaya message compose -t bob@example.com -s "Hello" --body "Hi Bob"           # preview
himalaya message compose -t bob@example.com -s "Hello" --body "Hi Bob" --send    # send
himalaya message reply 42 --body "Thanks, see you then." --send
himalaya message forward 42 -t carol@example.com --body "FYI" --send
himalaya message compose -t bob@example.com -s "Draft" --body "..." --save drafts
```

Filing:

```bash
himalaya message move 42 43 --to Archive          # -f SOURCE, default inbox
himalaya message copy 42 --to Important
himalaya message delete 42                        # moves to trash first
himalaya flag add 42 -f seen
himalaya flag remove 42 -f flagged
```
