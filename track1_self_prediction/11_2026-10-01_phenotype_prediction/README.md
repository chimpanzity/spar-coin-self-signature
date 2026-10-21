# 11 · Phenotype prediction: p(H) and switch-rate forecasts (2026-10-01)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | p(H): `phenotype-20261001T165443Z` (dry `phenotype-20261001T165429Z-dry`); switch rate: `switchrate-20261001T175124Z` (dry `phenotype-switch_rate-20261001T175110Z-dry`) |
| Models | Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), MiMo (`xiaomi/mimo-v2.6-pro`) |
| Size and cost | 360 forecasts per feature; $2.81 each ($2.8123 and $2.8088 in the run ledgers) |
| Previous / next | [← 10 Story swap](../10_2026-10-01_story_swap/) · [12 Phase 2, run 1 (Qwen3-8B) →](../12_2026-10-07_phase2_qwen/) |

## What was done
Before seeing any sequence, each judge forecast a statistic of a target model's 100-flip output
under a stated procedure (batch, history_conditioned, independent_calls): first the proportion of
heads, p(H), then, in a second run, the switch rate. 3 judges × 3 targets × 3 procedures ×
10 replicates at temperature 0.7, with SELF wording when judge = target and NAMED wording otherwise
(the own model was also asked about under NAMED wording). Forecasts were scored by mean absolute error (MAE)
against the corpus phenotypes. A strict parser is primary; a documented loose "last-line number"
parser recovers answers written after visible reasoning (Fable did this on all 40 of its
NAMED-on-other-target independent-calls cells).

## Questions
- Does a model predict its own phenotype more accurately than other models predict it (self advantage)?
- Does SELF wording add anything over naming the same model?
- Are the forecasts model-specific, or procedure-level beliefs applied to every model?

## Results
From [`PHENOTYPE_BASELINES_REPORT.md`](PHENOTYPE_BASELINES_REPORT.md) (loose parser):

| independent_calls | SELF MAE p(H) | self advantage p(H) | SELF MAE switch | self advantage switch |
|---|---:|---:|---:|---:|
| Astra | 0.611 | −0.250 | 0.473 | −0.201 |
| Fable | 0.013 | +0.237 | 0.026 | +0.167 |
| MiMo | 0.360 | −0.223 | 0.237 | −0.004 |

- Only Fable has a positive self advantage on both features, and only for independent calls.
- Judges forecast the same value whatever the target: under independent calls both Fable and Astra
  predict p(H) near 1 for every model (section 6d of the
  [cross-method report](../08_2026-10-01_fce2_batch_and_independent/FCE1_FCE2_CROSS_METHOD_REPORT.md)), and MiMo predicts 0.5 for everything.
  Fable's belief happens to fit its own degenerate behaviour (actual p(H) 0.987); Astra's does not (actual 0.389).
- SELF wording adds nothing over naming the same model: the SELF − OWN_NAMED MAE difference is at most
  0.03 in 17 of 18 cells. The exception is Astra's p(H) under independent calls, where SELF wording is
  worse (MAE 0.611 vs 0.461; −0.150). The report's text says all differences are ≤ 0.03, but its own table shows this cell.
- So the story-swap pattern in [10](../10_2026-10-01_story_swap/) reflects procedure-level task beliefs, not model-specific self-knowledge.

## Open questions
- Is Fable's calibrated forecast introspection or training-data knowledge of Claude-like behaviour under stateless prompts? These data cannot separate the two.
- MiMo answers 0.5 everywhere; is that due to running it with reasoning disabled?

## What it led to
The coin-flip work was redesigned as Phase 2 (a frozen, pre-registered pipeline with completion
forecasting, anonymous SAME/DIFFERENT and named attribution): [12 Phase 2, run 1](../12_2026-10-07_phase2_qwen/).

## Files
- Combined brief report: [`PHENOTYPE_BASELINES_REPORT.md`](PHENOTYPE_BASELINES_REPORT.md).
- p(H) run: [`full_corpus_phenotype_prediction/`](full_corpus_phenotype_prediction/) (`summary_by_cell.csv`, `trial_level.csv`, `raw_attempts.jsonl`, `baseline_p_H/`).
- Switch-rate run: [`full_corpus_phenotype_prediction_switch_rate/`](full_corpus_phenotype_prediction_switch_rate/) (`raw_attempts.jsonl`, `baseline_switch_rate/`).
- Background: [week handoff, §7–8](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-09-29_to_2026-10-03.md).
- Code: [`src/spar_dynamic/full_corpus_exp1/phenotype_prediction.py`](../../src/spar_dynamic/full_corpus_exp1/phenotype_prediction.py),
  `baselines_analysis.py`, `baselines_report.py` (same folder).
- Tests: none specific to these modules.

## Re-running
From the repo root (needs `OPENROUTER_API_KEY` for `run`; analysis is offline):

```
PYTHONPATH=src python -m spar_dynamic.full_corpus_exp1.phenotype_prediction run --live --yes --feature p_H
PYTHONPATH=src python -m spar_dynamic.full_corpus_exp1.phenotype_prediction run --live --yes --feature switch_rate
PYTHONPATH=src python -m spar_dynamic.full_corpus_exp1.baselines_analysis --run-dir <run folder> --feature p_H
PYTHONPATH=src python -m spar_dynamic.full_corpus_exp1.baselines_report --p-h-dir <dir> --switch-dir <dir> --out <file>
```
