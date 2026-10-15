---
name: spotify
description: "Control Spotify with the spogo CLI (browser-cookie login, no developer app): search, play, pause, skip, volume, queue, devices, playlists. Use when the user asks to play or control music on Spotify and spogo is installed."
enabled: false
tags: music, spotify, playback, media
platforms: [darwin, linux, win32]
requires: [spogo]
---

# Spotify (spogo)

`spogo` drives Spotify through the same endpoints as the web player, so it needs no
Spotify developer app. Playback control needs Spotify Premium and an active Spotify
device (desktop app, phone, speaker). Source: https://github.com/openclaw/spogo

## Setup (once, by the user)

```bash
brew install steipete/tap/spogo        # or: go install github.com/steipete/spogo/cmd/spogo@latest
                                       # Windows: zip from github.com/openclaw/spogo/releases
spogo auth import --browser chrome     # reads the open.spotify.com cookies; log in there first
spogo auth status
```

- Other browser profile: `--browser-profile "Profile 1"`. On macOS the import may show
  a Keychain prompt for the browser's cookie key; the user must approve it.
- If import fails (e.g. WSL): `spogo auth paste` and paste `sp_dc` (required) and `sp_t`
  from DevTools > Application > Cookies > https://open.spotify.com.

## Commands

Add `--json` (or `--plain`) when you need to parse output.

```bash
spogo status                              # what is playing, on which device
spogo search track "song name" --limit 5  # also: album, artist, playlist, show, episode
spogo play spotify:track:<id>             # id, URI or open.spotify.com URL; no arg = resume
spogo play <id> --type album              # --type is needed only for a bare id
spogo pause                               # also: next, prev
spogo volume 40                           # 0-100
spogo seek 1:30                           # ms or mm:ss
spogo shuffle on                          # on | off
spogo repeat off                          # off | track | context
spogo queue add <id|url>
spogo queue show
spogo device list
spogo device set "<name|id>"
spogo library tracks list --limit 20
spogo playlist create "Name"
spogo playlist add <playlist> <track...>
```

To play something by name: `search ... --json`, pick the best match, then `play` its URI.

## Notes

- "No active device": open Spotify on a device, then `spogo device set`, or pass
  `--device "<name>"` on the command.
- Saving to the library, following, and creating playlists use Spotify's public Web API,
  which can answer `429` with a cooldown of hours; report the retry hint, do not loop.
- `spogo auth clear` removes the stored cookies.
