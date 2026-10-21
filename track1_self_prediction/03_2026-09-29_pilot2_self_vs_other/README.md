# 03 · Pilot 2: SELF vs OTHER attribution (2026-09-29)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | `spar-self-other-20260929T175349Z` (this folder is the run root) |
| Models | Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), Qwen3.8 27B (`qwen/qwen3.8-27b`) as judges |
| Size and cost | 120 trials (122 calls), $0.31 ($0.3079) |
| Previous / next | [← 02 Pilot 1: source signatures](../02_2026-09-29_pilot1_source_signature/) · [04 Pilot 3: provenance →](../04_2026-09-29_pilot3_provenance/) |

## What was done
One trajectory per trial, reusing the 60 Pilot 1 strings. The judge answered in one word whether
the string was produced by the same underlying model as itself (SELF) or by a different model
(OTHER). Per judge × architecture: 10 SELF trials (every own string once) and 10 OTHER trials
(5 from each other model). 3 judges × 2 architectures × 20 = 120 trials. Baselines: the 3-way source
classifier and a per-judge SELF/OTHER feature classifier.

## Questions
- Can a model tell its own coin-flip strings from other models' strings?
- Does online generation (the clearer signature in Pilot 1) help?

## Results
From [`results/SELF_OTHER_PILOT_REPORT.md`](results/SELF_OTHER_PILOT_REPORT.md):

| judge | arch | balanced acc. | SELF response rate |
|---|---|---:|---:|
| Astra | batch / online | 0.500 / 0.500 | 0.000 / 0.000 |
| Fable | batch / online | 0.500 / 0.600 | 0.000 / 0.100 |
| Qwen | batch / online | 0.400 / 0.500 | 0.100 / 0.500 |

- Astra and Fable almost never answer SELF; the only exception is Fable online (SELF rate 0.10, 2 of 10 own strings).
- The SELF/OTHER feature classifier reaches balanced accuracy 0.700–1.000 per judge × architecture,
  above every LLM judge. The report classifies the outcome as "Outcome D": above chance online but no
  better than the feature classifier, i.e. ordinary phenotype classification.
- Granularity is 0.05 per cell.

## Open questions
- Is the near-zero SELF rate a judgment about the strings, or a general reluctance to claim authorship?
- Would telling the judge how a string was produced change its answer? (tested next)

## What it led to
[04 Pilot 3](../04_2026-09-29_pilot3_provenance/) added a stated-provenance manipulation
(told batch vs told online) to the same SELF/OTHER task.

**Numbering correction.** Some older documents
([week handoff](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-09-29_to_2026-10-03.md),
[archived pilots README](../../docs/archive/pilots_README_2026-10-11.md)) describe Pilot 2 as a
SAME/DIFFERENT task with ~92% / ~83% judge accuracy. That result is in
[02 Pilot 1](../02_2026-09-29_pilot1_source_signature/). This folder (Pilot 2) is SELF/OTHER.
The report's design section also says "24 (per judge x arch)"; the tables and the total of 120 imply 20.

## Files
- Report: [`results/SELF_OTHER_PILOT_REPORT.md`](results/SELF_OTHER_PILOT_REPORT.md); tables in [`results/`](results/)
  (`judge_summary.csv`, `architecture_contrast.csv`, `self_other_feature_classifier_baseline.csv`, `trial_level.csv`, ...).
- Raw data: [`trials/`](trials/), [`judgment/`](judgment/), `manifest.json`, `catalog_snapshot.json`, [`logs/`](logs/).
- Code: [`src/spar_dynamic/self_other.py`](../../src/spar_dynamic/self_other.py),
  [`src/spar_dynamic/orchestrator_self_other.py`](../../src/spar_dynamic/orchestrator_self_other.py) (plus shared `api.py`, `analyze.py`, `config.py`).
- Tests: [`tests/test_spar_self_other.py`](../../tests/test_spar_self_other.py).

## Re-running
From the repo root (needs `OPENROUTER_API_KEY`); the source strings come from Pilot 1's folder:

```
PYTHONPATH=src python -m spar_dynamic.orchestrator_self_other --live --yes \
    --source-run-root track1_self_prediction/02_2026-09-29_pilot1_source_signature
```
