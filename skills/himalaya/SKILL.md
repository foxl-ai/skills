---
name: himalaya
description: CLI email client via IMAP/SMTP - list, read, write, reply, search
trigger: manual
requires: [himalaya]
---

# Himalaya Email CLI

Manage emails from the terminal using IMAP/SMTP.

## Setup

```bash
brew install himalaya
himalaya account configure  # Interactive wizard
```

Or create `~/.config/himalaya/config.toml`:

```toml
[accounts.personal]
email = "you@example.com"
display-name = "Your Name"
default = true

backend.type = "imap"
backend.host = "imap.example.com"
backend.port = 993
backend.encryption.type = "tls"
backend.login = "you@example.com"
backend.auth.type = "password"
backend.auth.cmd = "pass show email/imap"

message.send.backend.type = "smtp"
message.send.backend.host = "smtp.example.com"
message.send.backend.port = 587
message.send.backend.encryption.type = "start-tls"
message.send.backend.login = "you@example.com"
message.send.backend.auth.type = "password"
message.send.backend.auth.cmd = "pass show email/smtp"
```

## List Emails

```bash
himalaya envelope list                    # INBOX
himalaya envelope list --folder "Sent"    # Specific folder
himalaya envelope list --page 1 --page-size 20
```

## Search

```bash
himalaya envelope list from john@example.com subject meeting
```

## Read Email

```bash
himalaya message read 42
himalaya message export 42 --full  # Raw MIME
```

## Reply/Forward

```bash
himalaya message reply 42
himalaya message reply 42 --all
himalaya message forward 42
```

## Write New Email

```bash
himalaya message write  # Opens $EDITOR

# Or send directly
cat << 'EOF' | himalaya template send
From: you@example.com
To: recipient@example.com
Subject: Test

Hello from Himalaya!
EOF
```

## Move/Copy/Delete

```bash
himalaya message move 42 "Archive"
himalaya message copy 42 "Important"
himalaya message delete 42
```

## Flags

```bash
himalaya flag add 42 --flag seen
himalaya flag remove 42 --flag seen
```

## Attachments

```bash
himalaya attachment download 42
himalaya attachment download 42 --dir ~/Downloads
```

## Multiple Accounts

```bash
himalaya account list
himalaya --account work envelope list
```
