---
name: openhue
description: Control Philips Hue lights and scenes via OpenHue CLI
trigger: manual
requires: [openhue]
---

# OpenHue CLI

Control Hue lights and scenes via a Hue Bridge.

## Setup

```bash
brew install openhue/cli/openhue-cli
openhue discover
openhue setup  # Press Hue Bridge button when prompted
```

## Read

```bash
openhue get light --json
openhue get room --json
openhue get scene --json
```

## Control Lights

```bash
# Turn on/off
openhue set light <id-or-name> --on
openhue set light <id-or-name> --off

# Brightness (0-100)
openhue set light <id> --on --brightness 50

# Color
openhue set light <id> --on --rgb #3399FF
```

## Scenes

```bash
openhue set scene <scene-id>
```

## Notes

- Use `--room "Room Name"` when light names are ambiguous
- Press Hue Bridge button during initial setup
