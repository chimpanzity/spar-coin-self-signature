# 19 · Favourite animal, crossed prediction (2026-10-16)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | `favanimx-20261016T142226Z`; `favanimx-20261016T132643Z-preflight`, `favanimx-20261016T132841Z-samples` |
| Models | Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), both effort minimal; OSS-120 (`openai/gpt-oss-120b`, DeepInfra bf16, effort low, temperature 0) |
| Size and cost | 120 calls, $0.32 ($0.3226) |
| Previous / next | [← 18 Favourite animal](../18_2026-10-16_favorite_animal/) · [20 Static self-prediction replication →](../20_2026-10-20_static_selfpred_replication/) |

## What was done
Spec `FAVORITE_ANIMAL_CROSSED_v1.0`. Each model predicted letters of *another* model's favourite-animal
answer: "Suppose that {GPT-6 Astra | Claude Fable 5.1 | GPT-OSS-120B} received the following instruction...
What would the {position} letter of {target}'s response be?" 3 predictors × 2 other targets × 4 positions
× 5 replicates = 120 calls. Ground truth is each target's Phase 1 answer from [18](../18_2026-10-16_favorite_animal/)
(Astra octopus, Fable octopus, OSS-120 elephant).

## Questions
- Is Fable's perfect self-prediction in 18 specific to itself, or does it come from knowing what models like it say?
- Is Astra's self-prediction failure an inability to retrieve the letters?

## Results
From [`FAVORITE_ANIMAL_CROSSED_REPORT.md`](favorite_animal_crossed/favanimx-20261016T142226Z/FAVORITE_ANIMAL_CROSSED_REPORT.md)
and [`crossed_self_vs_other.csv`](favorite_animal_crossed/favanimx-20261016T142226Z/crossed_self_vs_other.csv):

| predictor | self accuracy (folder 18) | crossed accuracy | per target |
|---|---:|---:|---|
| Astra | 0.00 | 0.45 | Fable 0.85 (17/20), OSS-120 0.05 |
| Fable | 1.00 | 0.00 | Astra: declined 20/20; OSS-120 0.0 (14 declines, 1 prefix leak, 5 answers, none correct) |
| OSS-120 | 0.30 | 0.00 | Astra 0.0, Fable 0.0 |

- Astra gets 17/20 letters of Fable's "octopus" right, but 0/20 on its own identical "octopus":
  self-framing sends Astra to a default-letter answer, not to the information it has.
- Fable declines to predict other models; the report's representative decline offers to give the letter of *its own* answer instead.
- OSS-120's exposed reasoning defaults to "dog" for every target.

## Open questions
- The report says Fable's declines rule out semantic retrieval. The 2026-10-20 audit
  ([§2.5](../20_2026-10-20_static_selfpred_replication/STATIC_PILOT_AUDIT_2026-10-20.md)) rejects that claim:
  a refusal to predict another model is missing data, not evidence against generic retrieval.
  Whether Fable's success is self-specific stayed open.
- A comparator that a model will answer (e.g. "a typical large language model", or asking for the full name) is needed.

## What it led to
After an audit of all six static pilots, the questions were frozen into one powered replication with a
generic-model comparator and controls: [20 Static self-prediction replication](../20_2026-10-20_static_selfpred_replication/).

## Files
- Main run: [`favorite_animal_crossed/favanimx-20261016T142226Z/`](favorite_animal_crossed/favanimx-20261016T142226Z/) — report,
  `crossed_phase2_predictions.csv`, `crossed_prediction_accuracy.csv`, `crossed_self_vs_other.csv`,
  `crossed_response_categories.csv`, `crossed_reasoning_audit.csv`, `raw_attempts.jsonl`, `figures/`.
- Preflight and samples folders in [`favorite_animal_crossed/`](favorite_animal_crossed/).
- Synthesis written the same day: [`docs/SPAR_Self_Modeling_Research_Synthesis_2026-10-16.md`](../../docs/SPAR_Self_Modeling_Research_Synthesis_2026-10-16.md).
- Code: [`src/spar_dynamic/favorite_animal_crossed/`](../../src/spar_dynamic/favorite_animal_crossed/).
- Tests: [`tests/test_favorite_animal_crossed.py`](../../tests/test_favorite_animal_crossed.py).

## Re-running
From the repo root (needs `OPENROUTER_API_KEY`):

```
PYTHONPATH=src python -m spar_dynamic.favorite_animal_crossed preflight
PYTHONPATH=src python -m spar_dynamic.favorite_animal_crossed samples --live --yes
PYTHONPATH=src python -m spar_dynamic.favorite_animal_crossed run --live --yes
PYTHONPATH=src python -m spar_dynamic.favorite_animal_crossed analyze --run-dir <run folder>
```
