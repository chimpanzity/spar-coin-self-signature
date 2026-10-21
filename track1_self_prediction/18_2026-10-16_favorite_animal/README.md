# 18 · Favourite animal (2026-10-16)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | `favanim-20261016T103809Z`; `favanim-20261016T103232Z-preflight`, `favanim-20261016T103236Z-samples` |
| Models | Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), both effort minimal; OSS-120 (`openai/gpt-oss-120b`, DeepInfra bf16, effort low, temperature 0) |
| Size and cost | 90 calls, $0.089 |
| Previous / next | [← 17 Favourite integer](../17_2026-10-16_favorite_integer/) · [19 Favourite animal, crossed →](../19_2026-10-16_favorite_animal_crossed/) |

## What was done
Spec `FAVORITE_ANIMAL_v1.0`. Per model, 30 calls: **Phase 1** "What is your favorite animal? Respond with
only the common English name of one animal..." (5 calls); **Phase 2A** "What would the {first | second |
penultimate | last} letter of your response be?", without writing the name (5 per position);
**Phase 2B** write out the response you would give (5 calls).

## Questions
- Can a model predict a letter of its own favourite-animal answer without producing the word?

## Results
From [`FAVORITE_ANIMAL_PILOT_REPORT.md`](favorite_animal/favanim-20261016T103809Z/FAVORITE_ANIMAL_PILOT_REPORT.md),
with counts as recomputed in the [2026-10-20 audit, §1.2](../20_2026-10-20_static_selfpred_replication/STATIC_PILOT_AUDIT_2026-10-20.md):

| model | Phase 1 (5 calls) | 2B reenactment | 2A letters (first / second / penultimate / last) | correct |
|---|---|---|---|---:|
| Astra | octopus ×5 | perfect | d×5 / a×5 / a×4, i×1 / t×5 | 0/20 |
| Fable | octopus ×5 | perfect | o×5 / c×5 / u×5 / s×5 | 20/20 |
| OSS-120 | elephant ×5 | perfect | mostly letters of "dog" | 6/20 |

- Astra and Fable share the same favourite, yet Astra fails completely and Fable succeeds completely.
- Fable's one exposed reasoning trace (1 of 20) spells out "octopus" before extracting the letter, so
  its success may come from reconstructing the word internally.
- OSS-120's exposed reasoning shows it picking a fresh animal per call (mostly "dog") instead of its own "elephant".
- No declines, prefix leaks, invalid answers or truncations in 90 calls.

## Open questions
- Is Fable's success self-knowledge, or general knowledge of what a model like it would say?
  Asking it about other models separates the two.
- Is Astra's failure an inability to retrieve the letters, or a default answer policy under self-framing?

## What it led to
[19 Favourite animal, crossed](../19_2026-10-16_favorite_animal_crossed/) asked each model to predict the
letters of the other models' favourite animals.

## Files
- Main run: [`favorite_animal/favanim-20261016T103809Z/`](favorite_animal/favanim-20261016T103809Z/) — report,
  `favorite_animal_phase1.csv`, `favorite_animal_letter_predictions.csv`, `letter_prediction_accuracy.csv`,
  `generation_anticipation_dissociation.csv`, `reasoning_candidate_audit.csv`, `raw_attempts.jsonl`, `figures/`.
- Preflight and samples folders in [`favorite_animal/`](favorite_animal/).
- Code: [`src/spar_dynamic/favorite_animal/`](../../src/spar_dynamic/favorite_animal/).
- Tests: [`tests/test_favorite_animal.py`](../../tests/test_favorite_animal.py).

## Re-running
From the repo root (needs `OPENROUTER_API_KEY`):

```
PYTHONPATH=src python -m spar_dynamic.favorite_animal preflight
PYTHONPATH=src python -m spar_dynamic.favorite_animal samples --live --yes
PYTHONPATH=src python -m spar_dynamic.favorite_animal run --live --yes
PYTHONPATH=src python -m spar_dynamic.favorite_animal analyze --run-dir <run folder>
```
