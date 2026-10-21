# 16 · Dice v4.1: construal, reenactment and anticipation (2026-10-16)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | `dicepilotv41-20261016T030505Z` (OSS-20 cells added by a same-ID resume after a provider switch); `dicepilotv41-20261016T004257Z-preflight`, `dicepilotv41-20261016T004350Z-samples`, `dicepilotv41-v2-preflight` |
| Models | Astra, Fable, Sonnet 5.5 (effort minimal); OSS-120 (DeepInfra bf16) and OSS-20 (DekaLLM bf16), effort low, temperature 0; Qwen3-32B (DeepInfra fp8, `reasoning.enabled = false`, temperature 0) |
| Size and cost | 210 calls, $0.146 |
| Previous / next | [← 15 Dice model extension](../15_2026-10-15_dice_model_extension/) · [17 Favourite integer →](../17_2026-10-16_favorite_integer/) |

## What was done
Spec `DICE_PILOT_v4.1`. Per model: 5 Phase 1 sequences, then three interleaved Phase 2 conditions:
**2A** the original v3.1 single-position prompt (position 2 only, 5 calls); **2B** a revised wording
stressing that the target is one element of one specific 10-integer response (positions 1, 2, 5, 9;
20 calls); **2C** "write out exactly the response you would give" (full-sequence reenactment, 5 calls).
The contrast of interest is between reenacting the whole sequence and anticipating one position of it.

## Questions
- Does clearer wording (2B) produce position-specific answers? (construal)
- Can a model reproduce its own typical sequence (2C), and does that dissociate from single-position prediction?

## Results
From [`PILOT_V4_1_REPORT.md`](dice_pilot_v41/dicepilotv41-20261016T030505Z/PILOT_V4_1_REPORT.md):

| model | 2C reenactment, positional agreement with Phase 1 | 2B single-position behaviour |
|---|---|---|
| OSS-120 | perfect (5/5 identical, 10/10 positions) | declines 70%; soft accuracy 0.00 where answered |
| OSS-20 | perfect | declines 45%; soft accuracy 0.00 where answered |
| Astra | 83% | "4" at every position |
| Sonnet 5.5 | 50% | "4" at every position |
| Fable | 31% | "4" at every position |
| Qwen3-32B | 26% (5 different sequences) | position-sensitive; 0.52 soft accuracy at position 5 |

- A generation–anticipation dissociation: the OSS models reproduce their sequence perfectly but decline
  to name one element ("can't determine without generating the full sequence").
- Revised wording changed nothing for Astra, Fable and Sonnet. Only Qwen moved, and only Qwen passed the
  follow-up criterion (position 5, margin +0.35).
- The [Qwen position-5 audit](dice_pilot_v41/dicepilotv41-20261016T030505Z/QWEN_POS5_REASONING_AUDIT.md) found that hit is
  not explicit simulation: Qwen gives up and picks "3", which is its modal Phase 1 roll at position 5 (frequency 0.6);
  in the one trial where simulation drove the answer, the answer ("5") was wrong.
- Parser fix during analysis: declines written with a typographic apostrophe (U+2019) had been counted as `invalid`.

## Open questions
- Why does a model that can reproduce its sequence fail to report one element of it?
- The audit notes that Qwen's pooled-digit baseline at position 5 equals 0.6, not the 0.0 used in the
  report's decision rule, so the Qwen "pass" is weaker than the report's table suggests.
- The later audit ([20, §2.3a](../20_2026-10-20_static_selfpred_replication/STATIC_PILOT_AUDIT_2026-10-20.md)) found that
  Qwen3-32B on DeepInfra reasons about 1,200 tokens per call even with reasoning disabled, so this "reasoning off" Qwen was not reasoning-free.

## What it led to
The same object-level / hypothetical / reenactment design was moved to a preference-like task:
[17 Favourite integer](../17_2026-10-16_favorite_integer/).

## Files
- Main run: [`dice_pilot_v41/dicepilotv41-20261016T030505Z/`](dice_pilot_v41/dicepilotv41-20261016T030505Z/) — `PILOT_V4_1_REPORT.md`,
  `QWEN_POS5_REASONING_AUDIT.md`, CSV tables, `raw_attempts.jsonl`, `figures/`.
- Preflight, samples and v2 preflight folders in [`dice_pilot_v41/`](dice_pilot_v41/).
- Code: [`src/spar_dynamic/dice_pilot_v41/`](../../src/spar_dynamic/dice_pilot_v41/).
- Tests: [`tests/test_dice_pilot_v41.py`](../../tests/test_dice_pilot_v41.py).

## Re-running
From the repo root (needs `OPENROUTER_API_KEY`):

```
PYTHONPATH=src python -m spar_dynamic.dice_pilot_v41 preflight
PYTHONPATH=src python -m spar_dynamic.dice_pilot_v41 samples --live --yes
PYTHONPATH=src python -m spar_dynamic.dice_pilot_v41 run --live --yes
PYTHONPATH=src python -m spar_dynamic.dice_pilot_v41 analyze --run-dir <run folder>
```
