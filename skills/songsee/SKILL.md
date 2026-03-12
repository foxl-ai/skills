---
name: songsee
description: Generate spectrograms and audio visualizations
trigger: manual
requires: [songsee]
---

# songsee

Generate spectrograms and feature panels from audio.

## Setup

```bash
brew install steipete/tap/songsee
```

## Quick Start

```bash
songsee track.mp3
songsee track.mp3 --viz spectrogram,mel,chroma
songsee track.mp3 --start 12.5 --duration 8 -o slice.jpg
```

## Visualizations

```bash
songsee track.mp3 --viz spectrogram,mel,chroma,hpss,selfsim,loudness,tempogram,mfcc,flux
```

Multiple `--viz` renders a grid.

## Options

- `--style` - Palette: classic, magma, inferno, viridis, gray
- `--width` / `--height` - Output size
- `--window` / `--hop` - FFT settings
- `--min-freq` / `--max-freq` - Frequency range
- `--start` / `--duration` - Time slice
- `--format` - jpg or png

## Stdin

```bash
cat track.mp3 | songsee - --format png -o out.png
```

## Notes

- WAV/MP3 decode native
- Other formats use ffmpeg if available
