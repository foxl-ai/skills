---
name: autoresearch
description: "Set up and run karpathy/autoresearch, where a coding agent repeatedly edits train.py, trains a small LLM for 5 minutes, and keeps changes that lower val_bpb. Use when the user wants to start an autonomous ML training experiment loop, check its results, or adapt it to a Mac or smaller GPU."
enabled: false
requires: [git, uv]
tags: ml, training, research, autonomous
---

# autoresearch

Upstream: https://github.com/karpathy/autoresearch (MIT). Read its `README.md` and `program.md` in the clone; they are the source of truth and change over time.

## How it works

- `train.py`: model, optimizer, training loop. The only file the research agent edits.
- `prepare.py`: data download, tokenizer, dataloader, evaluation. Never edited.
- `program.md`: the research agent's instructions. The human edits it.
- Each run trains for a fixed 5 minutes and prints `val_bpb` (validation bits per byte, lower is better). The agent commits an idea, runs it, keeps the commit if `val_bpb` improved, otherwise resets, and logs every run to `results.tsv`.

## Requirements

A single NVIDIA GPU (tested on H100), Python 3.10+, and uv (https://docs.astral.sh/uv/). On a Mac or a smaller GPU use a fork listed under "Notable forks" in the upstream README (macOS, MLX, Windows RTX, AMD) and follow its README instead.

## Setup (exec)

Ask the user where to put it; `~/autoresearch` is used below.

```bash
git clone https://github.com/karpathy/autoresearch ~/autoresearch
cd ~/autoresearch && uv sync
cd ~/autoresearch && uv run prepare.py      # one-time data + tokenizer, a few minutes
cd ~/autoresearch && uv run train.py        # one manual 5-minute run to prove the setup
```

Run `prepare.py` and `train.py` with `background: true` and a `timeout` of at least 900, then `process poll` / `process log`.

## Start the autonomous loop

The loop is run by a coding agent working inside the clone, not by Foxl itself. It runs for hours and edits files with permissions bypassed, so confirm with the user first and keep it to this folder.

- Watchable: open a `terminal` session in `~/autoresearch`, start the user's coding agent CLI there (for example `claude` or `codex`), and give it: "Read program.md and start a new experiment; do the setup first."
- Headless overnight: `exec` with `background: true` and an explicit `timeout` in seconds (for example 43200 for 12 hours), workdir `~/autoresearch`, running the agent in its non-interactive mode, for example `claude -p "Read program.md and start a new experiment; do the setup first." --dangerously-skip-permissions`. Check the agent's own `--help` for its current flags.

## Check progress

```bash
cd ~/autoresearch && column -t -s $'\t' results.tsv | tail -20   # commit, val_bpb, memory_gb, status, description
cd ~/autoresearch && git log --oneline | head -20                  # kept experiments
cd ~/autoresearch && grep -E '^(val_bpb|peak_vram_mb):' run.log    # last run
```

Report the best `val_bpb`, how many runs were kept, discarded or crashed, and what the kept changes were.

## Smaller compute

The upstream README lists the knobs: a lower-entropy dataset (TinyStories), smaller `vocab_size`, lower `MAX_SEQ_LEN` and `EVAL_TOKENS` in `prepare.py`, lower `DEPTH` and `TOTAL_BATCH_SIZE` and `WINDOW_PATTERN = "L"` in `train.py`. Results are only comparable on the same hardware.
