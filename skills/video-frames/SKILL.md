---
name: video-frames
description: "Extract still frames, contact sheets or short clips from a video file with ffmpeg, then inspect them with view_image. Use when the user asks what is in a video, wants a screenshot at a timestamp, a thumbnail grid, or a trimmed clip."
enabled: false
tags: video, ffmpeg, frames, thumbnails, media
platforms: [darwin, linux, win32]
requires: [ffmpeg]
---

# Video Frames (ffmpeg)

Install: `brew install ffmpeg` (macOS), the distro package (Linux), or
`winget install Gyan.FFmpeg` (Windows). `ffprobe` ships with it.

Write output to a fresh folder (e.g. `frames/`), then look at results with the
`view_image` tool. Add `-y` to overwrite and `-v warning` to keep logs short.

## Inspect first

```bash
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate -of default=nw=1 video.mp4
```

## One frame

```bash
ffmpeg -ss 00:00:10 -i video.mp4 -frames:v 1 -update 1 -q:v 2 frame-10s.jpg   # at 10 s
ffmpeg -sseof -1 -i video.mp4 -frames:v 1 -update 1 last.png                  # near the end
```

`-ss` before `-i` seeks fast. `-update 1` is needed for a single-image output on
current ffmpeg. Use `.png` for crisp UI or text, `.jpg` for photos.

## Many frames

```bash
ffmpeg -i video.mp4 -vf fps=1 frames/f_%04d.jpg              # 1 per second
ffmpeg -i video.mp4 -vf fps=1/5 frames/f_%04d.jpg            # 1 every 5 seconds
ffmpeg -i video.mp4 -vf "select='gt(scene,0.3)'" -fps_mode vfr frames/s_%03d.jpg   # scene changes
```

For a long video, prefer `fps=1/N` with a large N or a contact sheet: every frame
you view costs tokens.

## Contact sheet (one image)

```bash
ffmpeg -i video.mp4 -vf "fps=1/10,scale=320:-2,tile=4x4" -frames:v 1 -update 1 sheet.jpg
```

Pick the `fps` so frames x interval covers the duration (16 tiles x 10 s = 160 s).

## Clip

```bash
ffmpeg -ss 00:00:30 -i video.mp4 -t 10 -c copy clip.mp4                 # fast, cuts on keyframes
ffmpeg -ss 00:00:30 -i video.mp4 -t 10 -c:v libx264 -c:a aac clip.mp4   # frame-accurate
```

Long encodes can exceed the default 180 s `exec` timeout; pass a larger `timeout`
or run with `background: true` and check it with `process`.
