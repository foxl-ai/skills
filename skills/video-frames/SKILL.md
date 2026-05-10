---
name: video-frames
description: Extract frames or clips from videos using ffmpeg
enabled: false
trigger: manual
requires: [ffmpeg]
---

# Video Frames

Extract frames from videos using ffmpeg.

## Setup

```bash
brew install ffmpeg
```

## Extract First Frame

```bash
ffmpeg -i video.mp4 -vframes 1 frame.jpg
```

## Extract at Timestamp

```bash
ffmpeg -ss 00:00:10 -i video.mp4 -vframes 1 frame-10s.jpg
```

## Extract Multiple Frames

```bash
# One frame per second
ffmpeg -i video.mp4 -vf fps=1 frame_%04d.jpg

# Every 5 seconds
ffmpeg -i video.mp4 -vf "select='not(mod(n,150))'" -vsync vfr frame_%04d.jpg
```

## Create Thumbnail Grid

```bash
ffmpeg -i video.mp4 -vf "select='not(mod(n,100))',scale=320:180,tile=4x4" -frames:v 1 thumbnails.jpg
```

## Extract Short Clip

```bash
ffmpeg -ss 00:00:30 -i video.mp4 -t 10 -c copy clip.mp4
```

## Notes

- Use `.jpg` for quick sharing
- Use `.png` for crisp UI frames
- `-ss` before `-i` is faster (seeks before decoding)
