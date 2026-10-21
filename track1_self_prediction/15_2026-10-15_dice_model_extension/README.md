# 15 · Dice model extension: OSS-120, OSS-20, Sonnet 5.5 (2026-10-15)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | `dicepilotext-20261015T233304Z`; `dicepilotext-20261015T210100Z-preflight`, `dicepilotext-20261015T233252Z-smoke` |
| Models | OSS-120 (`openai/gpt-oss-120b`, effort low, temperature 0), OSS-20 (`openai/gpt-oss-20b`, effort low, temperature 0), Sonnet 5.5 (`anthropic/claude-sonnet-5.5`, effort minimal, no temperature control) |
| Size and cost | 75 calls, $0.0092 |
| Previous / next | [← 14 Dice v3.1](../14_2026-10-15_dice_v31/) · [16 Dice v4.1 →](../16_2026-10-16_dice_v41/) |

## What was done
The v3.1 dice task with byte-identical prompts, parsers and scoring (spec `DICE_PILOT_EXT_v1.0`),
on three further models with one reasoning setting each: 5 Phase 1 sequences and 5 Phase 2
predictions at each of positions 1, 2, 5, 9 = 25 calls per model. A smoke test confirmed that
all three endpoints reject a reasoning-off setting, so low-effort surrogates were used.

## Questions
- Does any other model anticipate its own 5th or 9th roll when the true value differs from its preferred digit?

## Results
From [`MODEL_EXTENSION_REPORT.md`](dice_pilot_ext/dicepilotext-20261015T233304Z/MODEL_EXTENSION_REPORT.md):
- No model passes the three-criterion rule after manual review (zero of nine cells across folders 14 and 15).
- OSS-120 passed automatically at position 5 (margin +0.033, one trial), but that hit came from a reasoning
  trace that wrote out the sequence `3 5 2 6 1 4 2 5 3 6` and took the 5th element: explicit prefix
  construction, which the rule excludes.
- That sequence is exactly OSS-120's Phase 1 modal sequence. OSS-120 has a stable imagined sequence it can
  reproduce when it chooses to, but under the Phase 2 prompt it usually just picks a digit.
- Sonnet 5.5 answered "4" in 20/20 Phase 2 calls. OSS-20's first six Phase 1 rolls were identical to Fable/R0's (`3 6 1 4 2 5`).
- Permutation-of-1–6 openings held for all 6 models in all 9 cells tested so far.

## Open questions
- If OSS-120 can reproduce its whole sequence, why does it not use it to answer the single-position question?
  Is it wording, or a gap between generating and anticipating?

## What it led to
[16 Dice v4.1](../16_2026-10-16_dice_v41/) added a revised single-position wording and a full-sequence
"reenactment" condition to test that gap directly.

## Files
- Run: [`dice_pilot_ext/dicepilotext-20261015T233304Z/`](dice_pilot_ext/dicepilotext-20261015T233304Z/) — `MODEL_EXTENSION_REPORT.md`,
  `reasoning_disable_smoke.json`, `prompts_frozen.txt`, `phase1_sequences.csv`, `phase2_predictions.csv`,
  `prediction_accuracy.csv`, `pilot_decision_rule.csv`, `raw_attempts.jsonl`, `figures/`.
- Preflight and smoke folders in [`dice_pilot_ext/`](dice_pilot_ext/).
- Code: [`src/spar_dynamic/dice_pilot_ext/`](../../src/spar_dynamic/dice_pilot_ext/).
- Tests: none for this package.

## Re-running
From the repo root (needs `OPENROUTER_API_KEY`):

```
PYTHONPATH=src python -m spar_dynamic.dice_pilot_ext preflight
PYTHONPATH=src python -m spar_dynamic.dice_pilot_ext smoke --live --yes
PYTHONPATH=src python -m spar_dynamic.dice_pilot_ext run --live --yes
PYTHONPATH=src python -m spar_dynamic.dice_pilot_ext analyze --run-dir <run folder>
```
