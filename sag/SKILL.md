---
name: sag
description: ElevenLabs text-to-speech with mac-style say UX
trigger: manual
requires: [sag, ELEVENLABS_API_KEY]
---

# sag (ElevenLabs TTS)

Text-to-speech with ElevenLabs.

## Setup

```bash
brew install steipete/tap/sag
export ELEVENLABS_API_KEY="your-key"
```

## Quick Start

```bash
sag "Hello there"
sag speak -v "Roger" "Hello"
sag voices  # List available voices
```

## Models

- `eleven_v3` - Expressive (default)
- `eleven_multilingual_v2` - Stable, multilingual
- `eleven_flash_v2_5` - Fast

## Audio Tags (v3)

Put at the start of a line:
- `[whispers]`, `[shouts]`, `[sings]`
- `[laughs]`, `[sighs]`, `[exhales]`
- `[sarcastic]`, `[curious]`, `[excited]`, `[crying]`

```bash
sag "[whispers] keep this quiet. [short pause] ok?"
sag "[excited] This is amazing!"
```

## Pauses

- `[pause]`, `[short pause]`, `[long pause]`

## Save to File

```bash
sag -v Roger -o /tmp/output.mp3 "Your message here"
```

## Pronunciation Tips

- Respell words: "key-note" instead of "keynote"
- Add hyphens for emphasis
- Use `--normalize auto` for numbers/URLs
- Use `--lang en|de|fr` for language bias
