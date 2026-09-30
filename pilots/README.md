# Prior pilots (historical)

These four pilots (Sept 2026) established the setup that led to the current
canonical stimulus corpus. They are preserved here as read-only historical
artifacts. **Moving forward, the reference dataset is `../corpus/`, not any
of these pilots.** Do not build new analyses on this data unless you
specifically need to reproduce a prior finding.

| pilot | folder | question |
|---|---|---|
| 1 | `pilot_1_dynamic_source/` | Does model identity exist in coin-flip trajectories? (batch vs online) |
| 2 | `pilot_2_self_other/` | Can models perceive those identities in SAME/DIFFERENT judgment? |
| 3 | `pilot_3_provenance/` | Does telling a model the stated architecture change its self-attribution? |
| 4 | `pilot_4_astra_followup/` | Astra-only provenance replication with a no-provenance control. |

## Why they are archived here

The prior pilots used 50-flip sequences and two production architectures
(`batch`, `online`) with three models (`astra`, `fable`, `qwen`). The
canonical corpus supersedes them along three dimensions:

- **Longer sequences**: 100 flips instead of 50 (more statistical power per trajectory).
- **Three production architectures**: `batch`, `history_conditioned` (renamed
  from `online`), and a new `independent_calls` control (fresh stateless
  call with an identical fixed prompt every trial).
- **Different third model**: `mimo-v2.6-pro` instead of `qwen` (chosen after
  a batch-compliance preflight over seven candidate open-weight models).
- **Frozen dev / holdout split**: the corpus commits to a stratified random
  10/10 split within every (model, method) cell, so recognition experiments
  can develop matching procedures on one half and evaluate on the other.

The findings from these pilots are still valid for what they measured; the
canonical corpus just gives future work a cleaner, larger, better-partitioned
stimulus bank to build on.

## Provenance chain preserved

Each pilot folder contains the original `raw_attempts.jsonl` and per-cell
result files exactly as they were at the time of the run. Their code lives
in the `spar_dynamic/` package at the repository root (e.g. `source.py`,
`self_other.py`, `provenance.py`, `astra_followup.py` and their
orchestrator counterparts).
