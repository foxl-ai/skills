---
name: sonos
description: Control Sonos speakers - discover, play, volume, group
trigger: manual
requires: [sonos]
---

# Sonos CLI

Control Sonos speakers on the local network.

## Setup

```bash
go install github.com/steipete/sonoscli/cmd/sonos@latest
```

## Quick Start

```bash
sonos discover
sonos status --name "Kitchen"
sonos play --name "Kitchen"
sonos pause --name "Kitchen"
sonos volume set 15 --name "Kitchen"
```

## Grouping

```bash
sonos group status
sonos group join --name "Bedroom" --coordinator "Kitchen"
sonos group unjoin --name "Bedroom"
sonos group party    # Group all speakers
sonos group solo     # Ungroup all
```

## Favorites

```bash
sonos favorites list
sonos favorites open "Morning Jazz"
```

## Queue

```bash
sonos queue list
sonos queue play 3
sonos queue clear
```

## Spotify Search (via SMAPI)

```bash
sonos smapi search --service "Spotify" --category tracks "query"
```

Requires `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`.

## Notes

- If SSDP fails, specify `--ip <speaker-ip>`
