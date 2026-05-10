---
name: healthcheck
description: Host security hardening and risk-tolerance configuration
enabled: false
trigger: manual
---

# Host Healthcheck

Assess and harden the host running Pilot.

## Workflow

### 1. Establish Context (read-only)

Determine:
1. OS and version
2. Privilege level (root/admin vs user)
3. Access path (local, SSH, RDP)
4. Network exposure (public IP, tunnel)
5. Backup status
6. Disk encryption status
7. Auto security updates status

### 2. Run Security Audits

```bash
pilot security audit
pilot security audit --deep
pilot security audit --json
```

### 3. Check Version Status

```bash
pilot update status
```

### 4. Determine Risk Tolerance

Profiles:
1. **Home/Workstation Balanced** - Firewall on, remote access restricted to LAN
2. **VPS Hardened** - Deny-by-default, key-only SSH, no root login
3. **Developer Convenience** - More local services, explicit warnings
4. **Custom** - User-defined constraints

### 5. Produce Remediation Plan

Include:
- Target profile
- Current posture summary
- Gaps vs target
- Step-by-step remediation
- Rollback strategy
- Risks and lockout scenarios

### 6. Execute with Confirmations

For each step:
- Show exact command
- Explain impact and rollback
- Confirm access remains available
- Stop on unexpected output

## Required Confirmations

Always require approval for:
- Firewall rule changes
- Opening/closing ports
- SSH/RDP configuration
- Installing/removing packages
- Enabling/disabling services
- User/group modifications
- Scheduling tasks
- Update policy changes

## Periodic Checks

Schedule via cron:
- `pilot security audit`
- `pilot update status`
