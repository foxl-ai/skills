---
name: healthcheck
description: "Read-only security posture check of this computer (macOS, Linux or Windows): disk encryption, firewall, OS updates, remote access, listening ports, backups, then a remediation plan applied only step by step with the user's approval. Use when the user asks if their machine is secure, to harden it, or to audit open ports."
enabled: false
tags: security, hardening, audit, firewall, macos, linux, windows
---

# Host healthcheck

## Rules

- Phase 1 is read-only. Change nothing until the user approves a specific step.
- Never run `sudo` / an elevated shell yourself: `exec` has no TTY for a password prompt. Show the command and let the user run it, or skip that check and say so.
- Before any change to SSH, RDP, firewall or network settings on a machine the user reaches remotely, confirm they keep another way in.

## 1. Context

Ask or detect: OS and version, laptop / desktop / server, local or remote (SSH, RDP), and which profile fits: Workstation (default), Server (deny-by-default, key-only SSH), Developer (more local services, each one named).

## 2. Checks (read-only, no admin needed unless marked)

macOS:
```bash
sw_vers -productVersion
fdesetup status                                              # FileVault
/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
/usr/libexec/ApplicationFirewall/socketfilterfw --getstealthmode
csrutil status; spctl --status                               # SIP, Gatekeeper
softwareupdate --list                                        # pending updates (slow, network)
tmutil destinationinfo                                       # Time Machine target
nc -z -G 2 127.0.0.1 22 && echo "SSH (Remote Login) is on"
lsof -nP -iTCP -sTCP:LISTEN                                  # own processes only; root ones need sudo
```

Linux:
```bash
cat /etc/os-release
lsblk -o NAME,TYPE,FSTYPE,MOUNTPOINTS | grep -i crypt        # LUKS
ss -tulpn                                                    # process names need root
systemctl is-active ufw firewalld nftables 2>/dev/null
systemctl is-active sshd ssh 2>/dev/null
grep -Ei '^\s*(PermitRootLogin|PasswordAuthentication)' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf 2>/dev/null
systemctl is-enabled unattended-upgrades dnf-automatic.timer 2>/dev/null
```
(admin: `sudo ufw status verbose`, `sudo nft list ruleset`, `sudo sshd -T`)

Windows (`exec` runs cmd.exe, so wrap PowerShell):
```bat
powershell -NoProfile -Command "Get-ComputerInfo -Property OsName,OsVersion"
powershell -NoProfile -Command "Get-NetFirewallProfile | Select Name,Enabled"
powershell -NoProfile -Command "Get-MpComputerStatus | Select AntivirusEnabled,RealTimeProtectionEnabled,AntivirusSignatureLastUpdated"
powershell -NoProfile -Command "Get-NetTCPConnection -State Listen | Select LocalAddress,LocalPort,OwningProcess | Sort LocalPort"
powershell -NoProfile -Command "Get-HotFix | Sort InstalledOn -Desc | Select -First 5"
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server" /v fDenyTSConnections
```
(admin: `manage-bde -status` for BitLocker)

Foxl itself: its local server should listen on `127.0.0.1` only; a Foxl or other process on `0.0.0.0` / `*` is reachable from the network and worth flagging.

## 3. Report and plan

Report a short table: check, current state, target for the chosen profile, risk (high / medium / low). Then a numbered remediation plan, highest risk first; for each step give the exact command or settings path, what it changes, how to undo it, and whether it can lock the user out.

## 4. Apply

One step at a time, only after explicit approval. Show the command, run it (or hand it to the user if it needs admin), re-run the matching check to confirm, and stop on any unexpected output. Always ask before: firewall or port changes, SSH/RDP settings, enabling or disabling services, installing or removing software, user or group changes, update policy, scheduled tasks.

For recurring checks, offer a Foxl schedule (Schedules page) that re-runs section 2 and reports only changes.
