---
name: nano-banana-pro
description: Generate or edit images via Gemini 3 Pro Image
trigger: manual
requires: [uv, GEMINI_API_KEY]
---

# Nano Banana Pro (Gemini Image)

Generate or edit images using Gemini 3 Pro Image.

## Generate

```bash
uv run scripts/generate_image.py --prompt "your image description" --filename "output.png" --resolution 1K
```

## Edit Single Image

```bash
uv run scripts/generate_image.py --prompt "edit instructions" --filename "output.png" -i "/path/input.png" --resolution 2K
```

## Multi-Image Composition

```bash
uv run scripts/generate_image.py --prompt "combine these into one scene" --filename "output.png" -i img1.png -i img2.png -i img3.png
```

Supports up to 14 input images.

## Resolutions

- `1K` (default)
- `2K`
- `4K`

## API Key

Set `GEMINI_API_KEY` environment variable.

## Notes

- Use timestamps in filenames: `yyyy-mm-dd-hh-mm-ss-name.png`
- Script prints `MEDIA:` line for auto-attachment
