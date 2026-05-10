---
name: spotify-player
description: Terminal Spotify playback and search via spogo or spotify_player
enabled: false
trigger: manual
requires: [spogo, spotify_player]
requiresAny: true
---

# Spotify Player

Control Spotify from the terminal.

## Setup (spogo - preferred)

```bash
brew install steipete/tap/spogo
spogo auth import --browser chrome
```

## spogo Commands

```bash
spogo search track "query"
spogo play
spogo pause
spogo next
spogo prev
spogo status
spogo device list
spogo device set "<name|id>"
```

## spotify_player Commands (fallback)

```bash
spotify_player search "query"
spotify_player playback play
spotify_player playback pause
spotify_player playback next
spotify_player playback previous
spotify_player connect
spotify_player like
```

## Notes

- Requires Spotify Premium
- Config: `~/.config/spotify-player/app.toml`
- TUI shortcuts available via `?`
