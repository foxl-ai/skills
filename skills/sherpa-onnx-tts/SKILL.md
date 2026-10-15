---
name: sherpa-onnx-tts
description: "Offline text-to-speech with sherpa-onnx: turn text into a WAV file on this computer, no cloud or API key. Use when the user wants text read aloud or saved as speech audio locally."
enabled: false
tags: tts, speech, audio, offline, local
platforms: [darwin, linux, win32]
requires: [SHERPA_ONNX_RUNTIME_DIR, SHERPA_ONNX_MODEL_DIR]
---

# sherpa-onnx TTS (offline)

Runs `sherpa-onnx-offline-tts` with a downloaded voice model. Source:
https://github.com/k2-fsa/sherpa-onnx (models: release tag `tts-models`).

- `SHERPA_ONNX_RUNTIME_DIR` - a folder whose `bin/` (Windows: `Scripts\`) holds `sherpa-onnx-offline-tts`
- `SHERPA_ONNX_MODEL_DIR` - an extracted VITS/Piper voice folder (`*.onnx`, `tokens.txt`, `espeak-ng-data/`)

Both can be saved on the Integrations page; Foxl passes them to `exec`.

## Setup (once)

Runtime in its own virtualenv (pip package `sherpa-onnx-bin` carries the binaries):

```bash
python3 -m venv ~/.foxl/tools/sherpa-onnx-tts/runtime
~/.foxl/tools/sherpa-onnx-tts/runtime/bin/pip install sherpa-onnx-bin
```

Voice (about 65 MB; other voices: same URL with another name from the `tts-models` release,
e.g. `vits-piper-en_US-ryan-medium`, `vits-piper-de_DE-thorsten-medium`):

```bash
mkdir -p ~/.foxl/tools/sherpa-onnx-tts/models && cd ~/.foxl/tools/sherpa-onnx-tts/models
curl -LO https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-en_US-lessac-medium.tar.bz2
tar xf vits-piper-en_US-lessac-medium.tar.bz2 && rm vits-piper-en_US-lessac-medium.tar.bz2
```

Then set `SHERPA_ONNX_RUNTIME_DIR=~/.foxl/tools/sherpa-onnx-tts/runtime` and
`SHERPA_ONNX_MODEL_DIR=~/.foxl/tools/sherpa-onnx-tts/models/vits-piper-en_US-lessac-medium`
(use absolute paths).

## Speak

```bash
M="$SHERPA_ONNX_MODEL_DIR"
"$SHERPA_ONNX_RUNTIME_DIR/bin/sherpa-onnx-offline-tts" \
  --vits-model="$(ls "$M"/*.onnx | head -1)" \
  --vits-tokens="$M/tokens.txt" \
  --vits-data-dir="$M/espeak-ng-data" \
  --num-threads=2 \
  --output-filename=./speech.wav \
  "Hello from local text to speech."
```

Optional: `--speed=1.2` (faster), `--sid=<n>` (speaker id for multi-speaker models).
Play only if the user asked: `afplay speech.wav` (macOS), `aplay speech.wav` (Linux),
`(New-Object Media.SoundPlayer 'speech.wav').PlaySync()` (Windows PowerShell).

## Notes

- Kokoro, Matcha and other model families take different flags (`--kokoro-model`, ...);
  run `sherpa-onnx-offline-tts --help` and read the model's folder.
- Very long text: split into paragraphs and synthesize each, so one call stays well
  under the `exec` timeout.
