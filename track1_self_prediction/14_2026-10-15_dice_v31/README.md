# 14 · Dice v3.1: hypothetical self-prediction of die rolls (2026-10-15)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | `dicepilot-20261015T193746Z`; preflights `dicepilot-20261015T193518Z-preflight`, `dicepilot-20261015T193741Z-preflight` |
| Models | Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), Qwen3-32B (`qwen/qwen3-32b`); each at R0 (reasoning minimised) and R1 (effort medium) |
| Size and cost | 150 calls, $0.199 ($0.1987). The six Oct 15–16 pilots (folders 14–19) together: 735 calls, about $0.91 |
| Previous / next | [← 13 Phase 2, run 2 (MiMo)](../13_2026-10-08_phase2_mimo/) · [15 Dice model extension →](../15_2026-10-15_dice_model_extension/) |

## What was done
First pilot after the track resumed, adapting Binder et al.'s split between an object-level answer
and a hypothetical prediction about a property of that answer (spec `DICE_PILOT_v3.1`).
**Phase 1:** in fresh contexts, each model × configuration writes 5 sequences of 10 simulated d6 rolls.
**Phase 2:** in new contexts, the model is asked what the 1st, 2nd, 5th or 9th roll of its response
*would be*, without writing the earlier rolls (5 replicates per position). Scoring: soft accuracy =
probability that the Phase 1 roll at that position equals the prediction, against chance (1/6) and a
position-agnostic "pooled-digit" baseline. A three-criterion rule (predictive advantage at position 5
or 9; no visible prefix construction; answers vary with position) decides whether a cell merits follow-up.

## Questions
- Can a model anticipate a later element of its own output without generating it?

## Results
From [`PILOT_REPORT.md`](dice_pilot/dicepilot-20261015T193746Z/PILOT_REPORT.md):
- Only **Fable/R1 at position 9** nominally passed (soft accuracy 0.60 vs chance 0.167 and pooled baseline 0.00).
- That pass is a coincidence of defaults: Fable/R1 answered "4" at almost every position, and its
  Phase 1 roll at position 9 happened to be 4 in 3 of 5 sequences. Exposed reasoning shows no
  internal sequence construction ("I'll just pick a plausible single-digit value").
- Astra answered "4" at every position in both configurations.
- Qwen: 20 of its 40 Phase 2 calls were unparseable (R0 8/20, R1 12/20).
- In Phase 1, every model's first six rolls were a permutation of 1–6 with no repeats.
- R0 is a low-effort surrogate for Astra and Fable (OpenRouter will not disable their reasoning), so their R0 vs R1 comparison is confounded.
- Conclusion in the report: no evidence of behavioural self-prediction at the digit level.

## Open questions
- Is the default "4" a property of these two models, or shared by others?
- Later audit ([20](../20_2026-10-20_static_selfpred_replication/STATIC_PILOT_AUDIT_2026-10-20.md), §2.3a) found that the
  pilots' Qwen "reasoning off" settings on DeepInfra still produced about 1,200 reasoning tokens per call.

## What it led to
The same prompts were run on three more models the same day: [15 Dice model extension](../15_2026-10-15_dice_model_extension/).

## Files
- Run: [`dice_pilot/dicepilot-20261015T193746Z/`](dice_pilot/dicepilot-20261015T193746Z/) — `PILOT_REPORT.md`,
  `phase1_sequences.csv`, `phase2_predictions.csv`, `prediction_accuracy.csv`, `pooled_digit_baseline.csv`,
  `pilot_decision_rule.csv`, `response_failures.csv`, `raw_attempts.jsonl`, `figures/`.
- Preflights: the two `*-preflight` folders in [`dice_pilot/`](dice_pilot/).
- Context for folders 14–19: [`docs/SPAR_Self_Modeling_Research_Synthesis_2026-10-16.md`](../../docs/SPAR_Self_Modeling_Research_Synthesis_2026-10-16.md).
- Code: [`src/spar_dynamic/dice_pilot/`](../../src/spar_dynamic/dice_pilot/).
- Tests: [`tests/test_dice_pilot.py`](../../tests/test_dice_pilot.py).

## Re-running
From the repo root (needs `OPENROUTER_API_KEY`):

```
PYTHONPATH=src python -m spar_dynamic.dice_pilot preflight
PYTHONPATH=src python -m spar_dynamic.dice_pilot run --live --yes
PYTHONPATH=src python -m spar_dynamic.dice_pilot analyze --run-dir <run folder>
```
