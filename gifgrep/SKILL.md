---
name: gifgrep
description: Search GIF providers, download, and extract stills/sheets
trigger: manual
requires: [gifgrep]
---

# gifgrep

Search GIF providers (Tenor/Giphy), browse in TUI, download, and extract stills.

## Setup

```bash
brew install steipete/tap/gifgrep
```

## Quick Start

```bash
gifgrep cats --max 5
gifgrep cats --format url | head -n 5
gifgrep search --json cats | jq '.[0].url'
```

## TUI Mode

```bash
gifgrep tui "office handshake"
```

## Download

```bash
gifgrep cats --download --max 1 --format url
gifgrep cats --download --reveal  # Open in Finder
```

## Extract Stills/Sheets

```bash
# Single frame
gifgrep still ./clip.gif --at 1.5s -o still.png

# Grid of frames
gifgrep sheet ./clip.gif --frames 9 --cols 3 -o sheet.png
```

Sheet options:
- `--frames` - Number of frames to sample
- `--cols` - Grid width
- `--padding` - Spacing between frames

## Providers

```bash
gifgrep cats --source tenor
gifgrep cats --source giphy  # Requires GIPHY_API_KEY
```

## Output Formats

```bash
gifgrep cats --json
gifgrep cats --format url
```

JSON fields: `id`, `title`, `url`, `preview_url`, `tags`, `width`, `height`
