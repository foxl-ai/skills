---
name: sonos
description: "Control Sonos speakers on the local network with the sonos CLI (sonoscli): discover rooms, play/pause/skip, volume, mute, group rooms, favorites, queue, play Spotify or a URL. Use when the user asks to control Sonos."
enabled: false
tags: music, sonos, speakers, home, media
platforms: [darwin, linux, win32]
requires: [sonos]
---

# Sonos (sonoscli)

Unofficial CLI for Sonos over the LAN (UPnP on TCP 1400). The computer must be on the
same network as the speakers. Source: https://github.com/steipete/sonoscli

## Setup (once, by the user)

```bash
brew install steipete/tap/sonoscli     # installs the `sonos` binary
# or: go install github.com/steipete/sonoscli/cmd/sonos@latest
# Windows: zip from github.com/steipete/sonoscli/releases
sonos config set defaultRoom "Kitchen" # optional: lets you omit --name
```

## Commands

Target a room with `--name "<room>"` (prefix matches work) or `--ip <speaker-ip>`.
Add `--format json` when you need to parse output.

```bash
sonos discover                          # list rooms
sonos status --name "Kitchen"           # now playing, volume
sonos play --name "Kitchen"             # also: pause, stop, next, prev
sonos volume get --name "Kitchen"
sonos volume set --name "Kitchen" 25
sonos mute toggle --name "Kitchen"
```

Groups (commands go to the group coordinator automatically):

```bash
sonos group status
sonos group join --name "Bedroom" --to "Living Room"
sonos group unjoin --name "Bedroom"
sonos group party --to "Living Room"    # every room joins this one
sonos group solo --name "Office"        # take one room out of its group
sonos group volume set --name "Living Room" 25
```

Favorites, queue, URLs:

```bash
sonos favorites list --name "Kitchen"
sonos favorites open --name "Kitchen" "BBC Radio 6 Music"   # or --index 1
sonos queue list --name "Kitchen"
sonos queue play --name "Kitchen" 3     # play item 3
sonos queue clear --name "Kitchen"
sonos play-uri --name "Kitchen" "https://example.com/stream.mp3"
sonos play-url --name "Kitchen" "<YouTube or page URL>"     # needs yt-dlp + ffmpeg
```

Spotify (must already be linked in the Sonos app):

```bash
sonos open --name "Kitchen" "https://open.spotify.com/track/<id>"   # or spotify:track:<id>
sonos play spotify --name "Kitchen" "artist or song"                 # search + play
sonos smapi search --service "Spotify" --category tracks "query"
```

`play spotify` / `smapi search` use Sonos's own service link. If they ask for a link,
the user runs `sonos auth smapi begin --service "Spotify"` once, opens the printed URL,
then `sonos auth smapi complete --service "Spotify" --code <code> --wait 5m`.

## Troubleshooting

- `discover` empty: same Wi-Fi/subnet, no client isolation; try `--ip`, or `--timeout 30s`.
- macOS 15+: allow Foxl under System Settings > Privacy & Security > Local Network.
- `sonos --help` lists every command for the installed version.
