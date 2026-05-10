---
name: autoresearch
description: Run Karpathy's autoresearch, an autonomous AI agent that experiments with LLM training code. The agent modifies train.py, runs 5-minute training experiments, evaluates val_bpb, keeps improvements or discards failures, and loops indefinitely. Use when user wants to start autonomous ML research, check experiment results, or manage autoresearch runs.
enabled: false
tags: [ml, training, research, autonomous, karpathy]
---

# autoresearch

Autonomous LLM training research by [karpathy/autoresearch](https://github.com/karpathy/autoresearch).

An AI agent edits `train.py`, trains for 5 minutes, checks val_bpb (lower = better), keeps or discards the change, and repeats indefinitely. You sleep, it researches.

## Quick Reference

| Task | Guide |
|------|-------|
| Understand the research protocol | Read [scripts/program.md](scripts/program.md) |
| See the editable training code | Read [scripts/train.py](scripts/train.py) |
| See the fixed eval/data infra | Read [scripts/prepare.py](scripts/prepare.py) |
| Check dependencies | Read [scripts/pyproject.toml](scripts/pyproject.toml) |

## Repo Location

`~/workspaces/autoresearch`

## Packaged Scripts

This skill bundles the core autoresearch files for reference:

```
scripts/
├── program.md        # Agent instructions / research protocol (human edits)
├── train.py          # Model, optimizer, training loop (agent edits)
├── prepare.py        # Data prep, tokenizer, eval (read-only)
├── pyproject.toml    # Dependencies
└── .python-version   # Python version
```

These are reference copies. The live working copies are in `~/workspaces/autoresearch/`.

## Requirements

- Single NVIDIA GPU (tested on H100). For Mac/RTX, see "Smaller Compute" section below.
- Python 3.10+, uv

## Key Files

| File | Role | Who edits |
|---|---|---|
| `train.py` | Model, optimizer, training loop | Agent (the only editable file) |
| `prepare.py` | Data prep, tokenizer, eval, constants | Nobody (read-only) |
| `program.md` | Agent instructions / research protocol | Human |
| `results.tsv` | Experiment log (TSV, untracked) | Auto-generated |

## One-time Setup

```bash
cd ~/workspaces/autoresearch
uv sync
uv run prepare.py
```

Downloads ClimbMix 400B shards to `~/.cache/autoresearch/` and trains BPE tokenizer (vocab 8192). Takes ~2 min.

## Manual Test Run

```bash
cd ~/workspaces/autoresearch
uv run train.py
```

5 minutes wall clock. Prints val_bpb and metrics at the end.

## Running Autonomous Research via Coding Agent

The recommended way is to point a coding agent at the repo and let it follow `program.md`:

```bash
# Claude Code (preferred)
cd ~/workspaces/autoresearch
claude --dangerously-skip-permissions "Read program.md and start autonomous experimentation"
```

Or via Foxl exec (background mode for overnight runs):

```bash
exec command:"cd ~/workspaces/autoresearch && claude --dangerously-skip-permissions 'Read program.md and start autonomous experimentation'" background:true timeout:86400
```

### What the agent does (program.md protocol)

1. Agrees on a run tag (e.g. `mar11`), creates branch `autoresearch/<tag>`
2. Reads README.md, prepare.py, train.py for full context
3. Verifies data exists in `~/.cache/autoresearch/`
4. Initializes `results.tsv` with header row
5. Runs baseline (unmodified train.py), records result
6. **Loops forever**:
   - Modifies train.py with an experimental idea
   - `git commit`
   - `uv run train.py > run.log 2>&1`
   - `grep "^val_bpb:\|^peak_vram_mb:" run.log`
   - If improved (lower val_bpb): keep commit, advance branch
   - If worse or equal: `git reset` to previous state
   - If crash: attempt fix or skip, log as "crash"
   - Record everything in results.tsv
   - **Never stops** until manually interrupted

### What the agent CAN change

Everything in `train.py`: architecture, hyperparameters, optimizer, batch size, model size, depth, attention patterns, activation functions, learning rate schedules, etc.

### What the agent CANNOT change

- `prepare.py` (fixed eval, dataloader, constants)
- Dependencies (only what's in pyproject.toml)
- Time budget (always 5 minutes wall clock)
- Evaluation metric (evaluate_bpb in prepare.py)

## Metric

`val_bpb` (validation bits per byte). Lower is better. Vocab-size-independent so architectural changes are fairly compared.

## Output Format

After each 5-min run, the script prints:

```
val_bpb:          0.997900
training_seconds: 300.1
total_seconds:    325.9
peak_vram_mb:     45060.2
mfu_percent:      39.80
total_tokens_M:   499.6
num_steps:        953
num_params_M:     50.3
depth:            8
```

## results.tsv Format

Tab-separated, 5 columns (do NOT use commas):

```
commit	val_bpb	memory_gb	status	description
a1b2c3d	0.997900	44.0	keep	baseline
b2c3d4e	0.993200	44.2	keep	increase LR to 0.04
c3d4e5f	1.005000	44.0	discard	switch to GeLU activation
d4e5f6g	0.000000	0.0	crash	double model width (OOM)
```

## Monitoring Experiments

```bash
# View experiment log
cat ~/workspaces/autoresearch/results.tsv

# Git log of kept experiments
cd ~/workspaces/autoresearch && git log --oneline

# Last run output
tail -50 ~/workspaces/autoresearch/run.log

# Extract just the metric
grep "^val_bpb:" ~/workspaces/autoresearch/run.log
```

## Default Model Config

- ~50M params, depth 8, 768d, 6 heads, 128 head dim
- RoPE, Flash Attention 3, sliding window (SSSL pattern)
- Value Embeddings (ResFormer style, gated residual)
- ReLU^2 activation, logit softcapping at 15
- MuonAdamW optimizer (Muon for 2D matrices via polar express orthogonalization + NorMuon, AdamW for embeddings/scalars)
- ~524K tokens per batch, gradient accumulation

## Smaller Compute (Mac, RTX, etc.)

For non-H100 setups, consider these forks or tune defaults:

- Use TinyStories dataset (lower entropy, works with smaller models)
- Lower `vocab_size`: 4096, 2048, 1024, or 256 (byte-level)
- Lower `MAX_SEQ_LEN` in prepare.py: down to 256
- Lower `DEPTH` in train.py: e.g. 4 instead of 8
- Use `WINDOW_PATTERN = "L"` (no alternating banded attention)
- Lower `TOTAL_BATCH_SIZE`: down to 2**14 (~16K)
- Lower `EVAL_TOKENS` for faster validation

### Notable Forks

- [miolini/autoresearch-macos](https://github.com/miolini/autoresearch-macos) (MacOS)
- [trevin-creator/autoresearch-mlx](https://github.com/trevin-creator/autoresearch-mlx) (MacOS MLX)
- [jsegov/autoresearch-win-rtx](https://github.com/jsegov/autoresearch-win-rtx) (Windows RTX)

## Simplicity Criterion

From program.md: "All else being equal, simpler is better." A small val_bpb improvement that adds ugly complexity is not worth it. Removing code and getting equal or better results is a great outcome. Weigh complexity cost against improvement magnitude.

## Timeout / Crash Handling

- Each experiment: ~5 min (+ startup overhead)
- If a run exceeds 10 min: kill it, treat as failure, revert
- Crashes: if trivial fix (typo, missing import), fix and re-run. If fundamentally broken, log as crash and move on.
