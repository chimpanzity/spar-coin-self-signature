# 17 · Favourite ten-digit integer (2026-10-16)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | `favint-20261016T054030Z`; `favint-20261016T053611Z-preflight`, `favint-20261016T053622Z-samples` |
| Models | Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), both effort minimal; OSS-120 (`openai/gpt-oss-120b`, DeepInfra bf16, effort low, temperature 0) |
| Size and cost | 90 calls, $0.145 |
| Previous / next | [← 16 Dice v4.1](../16_2026-10-16_dice_v41/) · [18 Favourite animal →](../18_2026-10-16_favorite_animal/) |

## What was done
The v4.1 design moved from simulated randomness to a preference-like answer (spec `FAVORITE_INTEGER_v1.0`).
Per model, 30 calls: **Phase 1** "What is your favorite ten-digit positive integer?" (5 calls);
**Phase 2A** predict the 1st, 2nd, 5th or 9th digit of that response without writing earlier digits
(5 per position); **Phase 2B** write out the full response you would give (5 calls). 2A and 2B interleaved.

## Questions
- Is the object-level preference stable?
- Can a model predict single digits of its own favourite, and does that dissociate from reproducing it whole?

## Results
From [`FAVORITE_INTEGER_PILOT_REPORT.md`](favorite_integer/favint-20261016T054030Z/FAVORITE_INTEGER_PILOT_REPORT.md):
- All three chose a widely known integer: Astra π's first ten digits `3141592653` (5/5), Fable π (4/5;
  the fifth was `1234567890`), OSS-120 `1234567890` (5/5).
- Reenactment (2B) was near perfect: positional agreement 1.00 for Astra and OSS-120, 0.82 for Fable
  (all five Fable reenactments were π; the 0.82 comes from its one non-π Phase 1 answer).
- Single digits (2A) dissociate for Astra: it answered **"7"** at position 1 in 5/5 calls (true digit 3)
  and at position 9 in 4/5 (true digit 5); soft accuracy 0.00 at both. The report calls this a "lucky 7" default.
- Fable declined twice and leaked a prefix once in 2A, and also drifted toward "7".
- OSS-120 was correct at positions 1, 5 and 9, but its favourite is `1234567890`, where the i-th digit is i; this is not evidence of introspection.

## Open questions
- Are these defaults ("7" here, "4" for dice) properties of each model, or shared by many models?
- Would a domain whose answer is a word, scored by letters, behave differently?

## What it led to
[18 Favourite animal](../18_2026-10-16_favorite_animal/) applied the same three conditions to a favourite
animal, with single letters as the predicted property.

**Note.** The 2026-10-20 audit ([20, §1.1](../20_2026-10-20_static_selfpred_replication/STATIC_PILOT_AUDIT_2026-10-20.md))
found that a "7" described in a handoff as a dice default actually comes from this pilot; no dice hypothetical was ever 7.

## Files
- Main run: [`favorite_integer/favint-20261016T054030Z/`](favorite_integer/favint-20261016T054030Z/) — report, CSV tables
  (`favorite_phase1_integers.csv`, `favorite_phase2_digit_predictions.csv`, `favorite_digit_accuracy.csv`,
  `favorite_dissociation.csv`, ...), `raw_attempts.jsonl`, `figures/`.
- Preflight and samples folders in [`favorite_integer/`](favorite_integer/).
- Code: [`src/spar_dynamic/favorite_integer/`](../../src/spar_dynamic/favorite_integer/).
- Tests: [`tests/test_favorite_integer.py`](../../tests/test_favorite_integer.py).

## Re-running
From the repo root (needs `OPENROUTER_API_KEY`):

```
PYTHONPATH=src python -m spar_dynamic.favorite_integer preflight
PYTHONPATH=src python -m spar_dynamic.favorite_integer samples --live --yes
PYTHONPATH=src python -m spar_dynamic.favorite_integer run --live --yes
PYTHONPATH=src python -m spar_dynamic.favorite_integer analyze --run-dir <run folder>
```
