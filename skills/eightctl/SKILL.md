---
name: eightctl
description: Control Eight Sleep pods - status, temperature, alarms, schedules
trigger: manual
requires: [eightctl]
---

# eightctl

Control Eight Sleep pods.

## Setup

```bash
go install github.com/steipete/eightctl/cmd/eightctl@latest
```

Config: `~/.config/eightctl/config.yaml`
Or env: `EIGHTCTL_EMAIL`, `EIGHTCTL_PASSWORD`

## Quick Start

```bash
eightctl status
eightctl on
eightctl off
eightctl temp 20
```

## Alarms

```bash
eightctl alarm list
eightctl alarm create
eightctl alarm dismiss
```

## Schedules

```bash
eightctl schedule list
eightctl schedule create
eightctl schedule update
```

## Audio

```bash
eightctl audio state
eightctl audio play
eightctl audio pause
```

## Base

```bash
eightctl base info
eightctl base angle
```

## Notes

- API is unofficial and rate-limited
- Avoid repeated logins
- Confirm before changing temperature or alarms
