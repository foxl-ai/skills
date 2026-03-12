---
name: spotify
description: Control Spotify playback and search via terminal
trigger: manual
enabled: true
requires:
  anyBins: ["spogo", "spotify_player"]
---

# Spotify Skill

Control Spotify playback from terminal.

## Requirements
- Spotify Premium account
- Either `spogo` or `spotify_player` installed

## When to use
- User wants to play music
- User wants to search for songs
- User wants to control playback

## How to execute

### Using spogo (Preferred)

Setup - import cookies:
```bash
spogo auth import --browser chrome
```

Search:
```bash
spogo search track "song name"
spogo search artist "artist name"
spogo search album "album name"
```

Playback:
```bash
spogo play
spogo pause
spogo next
spogo prev
```

Devices:
```bash
spogo device list
spogo device set "<name|id>"
```

Status:
```bash
spogo status
```

### Using spotify_player (Fallback)

Search:
```bash
spotify_player search "query"
```

Playback:
```bash
spotify_player playback play
spotify_player playback pause
spotify_player playback next
spotify_player playback previous
```

Connect device:
```bash
spotify_player connect
```

Like current track:
```bash
spotify_player like
```

## Notes
- Config folder: `~/.config/spotify-player`
- TUI shortcuts available via `?` in the app
