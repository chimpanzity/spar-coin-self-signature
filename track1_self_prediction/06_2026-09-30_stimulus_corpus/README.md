# 06 · Stimulus corpus: three models × three production methods, "Pilot 5" (2026-09-30)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | `spar-stimulus-corpus-20260930T012044Z` (stopped once on an analysis error, then resumed and completed) |
| Models | Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), MiMo (`xiaomi/mimo-v2.6-pro`, reasoning disabled) |
| Size and cost | 180 trajectories × 100 flips; 12,976 API attempts; $7.42 ($7.4197) |
| Previous / next | [← 05 Pilot 4: Astra follow-up](../05_2026-09-29_pilot4_astra_followup/) · [07 FCE1 →](../07_2026-10-01_fce1_history_conditioned/) |

## What was done
A frozen, reusable stimulus bank replacing the small 50-flip pilot sets. Three models × three
production methods × 20 trajectories of 100 flips, all at temperature 0:
- **batch**: one call writes all 100 flips;
- **history_conditioned** (the pilots' "online"): 100 calls, each seeing the full prior history;
- **independent_calls**: 100 calls with an identical stateless prompt and no history.

MiMo replaced Qwen after the other candidate third models failed a strict 100-character batch
preflight (see the [week handoff](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-09-29_to_2026-10-03.md)). Within each (model, method) cell the trajectories were split 10 development / 10
holdout with base seed 20260930; later recognition experiments develop on the first half and evaluate on the second.

## Questions
- How much does the production method change a model's coin-flip phenotype?
- How identifiable is the source model under each method, and how does that grow with sequence length?

## Results
From [`corpus/THREE_ARCHITECTURE_SOURCE_REPORT.md`](corpus/THREE_ARCHITECTURE_SOURCE_REPORT.md) (means over 20 trajectories, full length):

| model | batch p(H) / switch | history_conditioned | independent_calls |
|---|---|---|---|
| Astra | 0.495 / 0.620 | 0.460 / 0.632 | 0.389 / 0.473 |
| Fable | 0.507 / 0.643 | 0.744 / 0.476 | **0.987 / 0.026** (mean longest run 78.0) |
| MiMo | 0.487 / 0.624 | 0.633 / 0.497 | 0.860 / 0.233 |

- Batch gives near-fair heads frequencies for every model; independent calls collapse toward
  repeated "H", most strongly for Fable.
- Source classifier (LOO nearest centroid, chance 0.333), at prefix 20 / 50 / 100 flips:
  history_conditioned 0.683 / 0.883 / 0.900; independent_calls 0.333 / 0.667 / 0.667; batch 0.567 / 0.383 / 0.533.
- Seven MiMo history_conditioned trajectories were abandoned and re-run under fresh replicate indices;
  the canonical [`corpus/trajectories.csv`](corpus/trajectories.csv) has exactly 180 valid rows.

## Open questions
- Can models recognise their own trajectories when the signal is this strong and the procedure is stated? (tested next)
- Twenty trajectories per cell keeps classifier estimates noisy.

## What it led to
[07 FCE1](../07_2026-10-01_fce1_history_conditioned/) used the history_conditioned cells, the method
with the strongest pilot signal, for a producer-vs-observer identification test.

## Files
- Canonical corpus: [`corpus/`](corpus/) — [`README.md`](corpus/README.md) (design, verbatim prompts, split seeds),
  `trajectories.csv` (180 rows), `flips.csv` (18,000 rows), `metrics.csv` (540 rows, prefixes 20/50/100),
  `manifest.json`, [`data_dictionary.md`](corpus/data_dictionary.md), `stimulus_corpus.xlsx` (browsing only).
- Raw run: [`spar-stimulus-corpus-20260930T012044Z/`](spar-stimulus-corpus-20260930T012044Z/) — `raw_attempts.jsonl`
  (every attempt), `trajectories/`, `results/` (report, `cost_summary.csv`, `classification_results.csv`, ...),
  `OVERNIGHT_RUN_STOPPED.md` (KeyError `prop_T` at $7.33) and `OVERNIGHT_RUN_COMPLETE.md`. Its `results/corpus/` is the compiled copy the FCE code reads by default.
- Background: [`docs/COIN_FLIP_STUDY.md`](../../docs/COIN_FLIP_STUDY.md).
- Code: [`src/spar_dynamic/stimulus_corpus.py`](../../src/spar_dynamic/stimulus_corpus.py),
  [`orchestrator_stimulus_corpus.py`](../../src/spar_dynamic/orchestrator_stimulus_corpus.py),
  [`compile_corpus.py`](../../src/spar_dynamic/compile_corpus.py), [`backfill_mimo_history.py`](../../src/spar_dynamic/backfill_mimo_history.py).
- Tests: [`tests/test_spar_stimulus_corpus.py`](../../tests/test_spar_stimulus_corpus.py).

## Re-running
From the repo root. Recompiling the CSVs from the saved raw run makes no API calls:

```
PYTHONPATH=src python -m spar_dynamic.compile_corpus --run-id spar-stimulus-corpus-20260930T012044Z
```

A new generation run needs `OPENROUTER_API_KEY`:

```
PYTHONPATH=src python -m spar_dynamic.orchestrator_stimulus_corpus --live --yes
```
