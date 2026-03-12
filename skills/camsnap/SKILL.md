---
name: camsnap
description: Capture frames or clips from RTSP/ONVIF cameras
trigger: manual
requires: [camsnap, ffmpeg]
---

# camsnap

Grab snapshots, clips, or motion events from configured cameras.

## Setup

```bash
brew install steipete/tap/camsnap
```

Config file: `~/.config/camsnap/config.yaml`

## Add Camera

```bash
camsnap add --name kitchen --host 192.168.0.10 --user user --pass pass
```

## Common Commands

- Discover cameras: `camsnap discover --info`
- Snapshot: `camsnap snap kitchen --out shot.jpg`
- Clip: `camsnap clip kitchen --dur 5s --out clip.mp4`
- Motion watch: `camsnap watch kitchen --threshold 0.2 --action '...'`
- Doctor: `camsnap doctor --probe`

## Notes

- Requires `ffmpeg` on PATH
- Prefer short test capture before longer clips
