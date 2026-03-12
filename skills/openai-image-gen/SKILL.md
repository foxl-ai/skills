---
name: openai-image-gen
description: Generate images via OpenAI Images API (DALL-E, GPT-image)
trigger: manual
requires: [python3, OPENAI_API_KEY]
---

# OpenAI Image Gen

Generate images via OpenAI Images API.

## Quick Start

```bash
python3 scripts/gen.py --count 4 --model gpt-image-1
python3 scripts/gen.py --prompt "ultra-detailed photo of a robot" --count 4
```

## Models

### GPT Image Models
```bash
python3 scripts/gen.py --model gpt-image-1 --size 1536x1024 --quality high
python3 scripts/gen.py --model gpt-image-1.5 --background transparent --output-format webp
```

Sizes: `1024x1024`, `1536x1024` (landscape), `1024x1536` (portrait), `auto`
Quality: `auto`, `high`, `medium`, `low`

### DALL-E 3
```bash
python3 scripts/gen.py --model dall-e-3 --quality hd --size 1792x1024 --style vivid
python3 scripts/gen.py --model dall-e-3 --style natural --prompt "serene landscape"
```

Sizes: `1024x1024`, `1792x1024`, `1024x1792`
Quality: `hd`, `standard`
Style: `vivid`, `natural`
Note: Only generates 1 image at a time

### DALL-E 2
```bash
python3 scripts/gen.py --model dall-e-2 --size 512x512 --count 4
```

Sizes: `256x256`, `512x512`, `1024x1024`

## Output

- Images in specified format (png, jpeg, webp)
- `prompts.json` - prompt to file mapping
- `index.html` - thumbnail gallery
