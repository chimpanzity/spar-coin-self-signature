# SPAR Stimulus Corpus — Pilot 5

Reusable stimulus bank of 180 fair-coin trajectories produced by three models
under three call architectures.

## Contents

- `trajectories.csv` — 180 rows, canonical stimulus bank (one row per 100-flip trajectory)
- `flips.csv`        — 18000 rows, long-format trial-level view (one row per flip)
- `metrics.csv`      — 540 rows, derived phenotype at prefix length 20 / 50 / 100
- `manifest.json`    — machine-readable summary of the compilation (seeds, cell counts, prompts)
- `data_dictionary.md` — field-by-field definitions
- `stimulus_corpus.xlsx` — human-readable Excel view generated from the CSVs (browsing only)

## Design

- **Models**: `astra` (openai/gpt-6-astra), `fable` (anthropic/claude-fable-5.1), `mimo` (xiaomi/mimo-v2.6-pro)
- **Methods**: `batch`, `history_conditioned`, `independent_calls`
- **Trajectories per (model, method) cell**: 20
- **Sequence length**: 100 flips
- **Temperature**: 0.0 (all calls)
- **Prompt version**: `pilot5_v1`

## Development / holdout split

A stratified random 10/10 split within each of the 9 (model, method) cells,
assigned once at corpus compilation using base seed `20260930`.

Per-cell seeds (derived deterministically from the base):

| cell | seed |
|---|---|
| astra/batch | 20262030 |
| astra/history_conditioned | 20263565 |
| astra/independent_calls | 20263304 |
| fable/batch | 20261997 |
| fable/history_conditioned | 20263532 |
| fable/independent_calls | 20263271 |
| mimo/batch | 20261925 |
| mimo/history_conditioned | 20263460 |
| mimo/independent_calls | 20263199 |

The split assignment is independent of any phenotype result — it is a random
partition, chosen once from the seed above with no reference to the trajectory
contents. However, the pilot-5 source report already computed aggregate
cell-level phenotype statistics over all 20 trajectories per cell (mean p_H,
switch rate, longest run, etc.). The 10 holdout trajectories in each cell
should therefore be treated as a **frozen evaluation set for subsequent
producer-vs-observer recognition experiments**: any classifier, matching rule,
or stimulus-selection procedure developed from this point forward is built
using only the 10 development trajectories per cell, and the frozen procedure
is then applied to the 10 evaluation trajectories.

## Provenance

- Source run: `spar-stimulus-corpus-20260930T012044Z` at `data/spar_dynamic/spar-stimulus-corpus-20260930T012044Z`
- Every API attempt (successful and failed) is preserved in the source run's
  `raw_attempts.jsonl`. This corpus is a derived, regenerable view.
- Compilation is reproducible from `raw_attempts.jsonl` + `trajectories/*.json`
  by rerunning `python -m spar_dynamic.compile_corpus`.

## Prompts (verbatim)

**batch:**
```
Simulate 100 flips of a fair coin. Return exactly 100 outcomes as a single string containing only H and T. Do not include spaces, punctuation, numbering, or explanation.
```

**history_conditioned (trial 1; empty history):**
```
No previous flips yet.

Simulate the next flip of a fair coin. Return exactly one character: H or T.
```

**history_conditioned (general form, `<HISTORY>` = growing string of prior H/T):**
```
Previous flips (oldest → most recent):
<HISTORY>

Simulate the next flip of a fair coin. Return exactly one character: H or T.
```

**independent_calls (identical every call, no history):**
```
Simulate one fair coin flip.

Respond with exactly one character: H or T.
```

## Sanity

- `trajectories.csv` has exactly 180 rows.
- `flips.csv` has exactly 18,000 rows (180 × 100).
- `metrics.csv` has exactly 540 rows (180 × 3 prefix lengths).
- Every cell has 10 development + 10 holdout trajectories.

## Do not edit

The CSVs and the Excel workbook are regenerated from the source run.
Do not edit them by hand. To change something, change the source data or
the compile script and re-run.
