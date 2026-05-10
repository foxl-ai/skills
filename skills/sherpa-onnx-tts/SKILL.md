---
name: sherpa-onnx-tts
description: Local text-to-speech via sherpa-onnx (offline, no cloud)
enabled: false
platforms: [darwin, linux, win32]
requires: [SHERPA_ONNX_RUNTIME_DIR, SHERPA_ONNX_MODEL_DIR]
---

# sherpa-onnx-tts

Local offline TTS using sherpa-onnx.

## Setup

1. Download runtime for your OS from sherpa-onnx releases
2. Download a voice model (e.g., vits-piper-en_US-lessac-high)
3. Set environment variables:

```bash
export SHERPA_ONNX_RUNTIME_DIR=~/.pilot/tools/sherpa-onnx-tts/runtime
export SHERPA_ONNX_MODEL_DIR=~/.pilot/tools/sherpa-onnx-tts/models/vits-piper-en_US-lessac-high
```

## Usage

```bash
sherpa-onnx-tts -o ./output.wav "Hello from local TTS."
```

## Options

- `-o` / `--output` - Output WAV file
- `--model-file` - Specific model file if multiple exist
- `--tokens-file` - Override tokens file
- `--data-dir` - Override data directory

## Notes

- Completely offline, no API keys needed
- Pick different models from sherpa-onnx tts-models releases
- Supports multiple languages depending on model
