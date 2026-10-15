---
name: spotify-player
description: "Control Spotify with the spotify_player CLI (official Spotify login): search, start a track/album/playlist, pause, skip, volume, like, devices. Use when the user wants Spotify playback and spotify_player is installed."
enabled: false
tags: music, spotify, playback, media
platforms: [darwin, linux, win32]
requires: [spotify_player]
---

# Spotify (spotify_player)

`spotify_player` is a Spotify client with a scriptable CLI. Needs Spotify Premium.
Source: https://github.com/aome510/spotify-player

## Setup (once, by the user)

```bash
brew install spotify_player      # or: cargo install spotify_player --locked
spotify_player authenticate      # opens a browser login; run it in a real terminal
```

Login is interactive, so ask the user to run `authenticate` themselves (or use the
`terminal` tool). Config lives in `~/.config/spotify-player/app.toml`. The default
shared client ID can hit `429`; the README explains setting your own `client_id`.

## Commands

The CLI talks to a running instance on port 8080 (`client_port`) and starts one if
none is running, so the first call can be slow.

```bash
spotify_player get key playback          # current playback as JSON
spotify_player get key devices           # also: queue, user-playlists, user-liked-tracks
spotify_player search "query"            # JSON with tracks, albums, artists, playlists
spotify_player playback start track --id <track_id>
spotify_player playback start context playlist --id <id>   # or album, artist; add --shuffle
spotify_player playback start liked --random
spotify_player playback pause           # also: play, play-pause, next, previous
spotify_player playback volume 40        # add --offset to change by a relative amount
spotify_player playback seek 30000       # offset in ms, negative goes back
spotify_player playback shuffle         # toggle; `repeat` cycles the mode
spotify_player connect --name "<device name>"
spotify_player like                      # like current track; --unlike to undo
spotify_player playlist list
```

Play by name: `spotify_player search "<query>"`, take `.tracks[0].id` from the JSON,
then `playback start track --id <id>`. `--name` works in place of `--id` for most items.

## Notes

- Run `spotify_player -h` or `spotify_player <command> -h` for the installed version's flags.
- Do not start the TUI from `exec` (it needs a terminal); use the CLI subcommands.
