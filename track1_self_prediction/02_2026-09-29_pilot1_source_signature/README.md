# 02 · Pilot 1: source signatures in 50-flip strings, batch vs online (2026-09-29)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | `spar-dynamic-run-20260929T081814Z` (this folder is the run root) |
| Models | Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), Qwen3.8 27B (`qwen/qwen3.8-27b`) |
| Size and cost | 60 source strings (10 per model × 2 architectures); 144 SAME/DIFFERENT trials from 208 judgment calls; $1.43 reported (see note under Results) |
| Previous / next | [← 01 Preregistered harness](../01_2026-09-21_preregistered_harness/) · [03 Pilot 2: SELF/OTHER →](../03_2026-09-29_pilot2_self_vs_other/) |

## What was done
Each model produced ten 50-flip "fair coin" strings under two architectures: **batch** (one call
writes all 50 flips) and **online** (50 calls, one flip per call, each seeing the full history).
Each model then judged pairs of anonymous strings as SAME model or DIFFERENT models, in the four
cells of the preregistered design (A own+own, B own+other, C other+same other, D other1+other2),
24 trials per judge × architecture. A leave-one-out nearest-centroid classifier on simple sequence
features (p(H), switch rate, runs, longest run) gave an external baseline.

## Questions
- Do models leave an identifiable signature in coin-flip strings, and does it depend on architecture?
- Is a judge more accurate on trials that involve its own strings ("self advantage"), especially online?

## Results
From [`results/FINAL_OVERNIGHT_REPORT.md`](results/FINAL_OVERNIGHT_REPORT.md):

| | batch | online |
|---|---:|---:|
| Source classifier, 3-way LOO accuracy | 0.700 | 0.933 |
| Astra total accuracy (n=24) | 0.583 | 0.917 |
| Fable total accuracy | 0.500 | 0.833 |
| Qwen total accuracy | 0.333 | 0.625 |
| Pooled self advantage (own − other accuracy) | +0.056 | +0.028 |

- Signatures exist, and online generation makes them much clearer (classifier +0.233).
- No consistent self advantage: Astra +0.000 in both architectures; Fable +0.000 batch and −0.333
  online; Qwen +0.167 / +0.417. Granularity is 1/6 per cell.
- Online Qwen strings were degenerate (mean p(H) 0.936, mean longest run 27.2), which makes them easy to tell apart.
- A feature-distance rule reached 0.944 on online pairs and 0.556 on batch pairs.
- Cost note: the report's $1.4316 is batch generation ($0.1904) plus judgment ($1.2412). The run log
  ([`logs/orchestrator.log`](logs/orchestrator.log)) also records 30 online-generation trajectories
  costing about $0.96 in total that are not in that figure.

## Open questions
- With 6 trials per cell, the self-advantage estimates are very coarse.
- Is judge accuracy anything more than reading the same surface features the classifier uses?

## What it led to
The same 60 strings were reused for a direct SELF/OTHER attribution task in
[03 Pilot 2](../03_2026-09-29_pilot2_self_vs_other/).

**Numbering correction.** Some older documents (the week handoff
[`HANDOFF_SPAR_WEEK_2026-09-29_to_2026-10-03.md`](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-09-29_to_2026-10-03.md)
and [`docs/archive/pilots_README_2026-10-11.md`](../../docs/archive/pilots_README_2026-10-11.md))
credit the SAME/DIFFERENT judge result (online ~92% / ~83%) to "Pilot 2". It belongs to this
pilot (Pilot 1). Pilot 2 is the SELF/OTHER task.

## Files
- Report: [`results/FINAL_OVERNIGHT_REPORT.md`](results/FINAL_OVERNIGHT_REPORT.md); tables in [`results/`](results/)
  (`judge_summary.csv`, `cell_summary.csv`, `source_model_classifier.csv`, `feature_distance_baseline.csv`, `trial_level.csv`, ...).
- Raw data: [`source/`](source/) (batch and online trajectories, per-step logs for online), [`trials/`](trials/),
  [`judgment/`](judgment/) (one JSON per trial), `manifest.json`, `catalog_snapshot.json`, [`logs/`](logs/), `OVERNIGHT_RUN_COMPLETE.md`.
- Code: [`src/spar_dynamic/`](../../src/spar_dynamic/) — `orchestrator.py`, `source.py`, `trials.py`, `judgment.py`,
  `analyze.py`, `api.py`, `config.py`, `state.py`, `finalize_report.py`.
- Tests: [`tests/test_spar_dynamic.py`](../../tests/test_spar_dynamic.py).

## Re-running
From the repo root (needs `OPENROUTER_API_KEY`; both flags are required for a paid run):

```
PYTHONPATH=src python -m spar_dynamic.orchestrator --live --yes
```

New run folders are placed by `src/repo_paths.py` (under `new_runs/spar_dynamic/` unless `--data-root` is given).
