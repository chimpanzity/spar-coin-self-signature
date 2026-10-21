# 20 · Static self-prediction replication, STATIC_SELFPRED_v1.0 (2026-10-20 to 10-21)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | main `main-20261021T021451Z`; Qwen parse check `parsecheck-qwen-20261021T000345Z`; prompts frozen as `STATIC_SELFPRED_v1.0` (git tag `static-selfpred-v1.0`) |
| Models | Astra (OpenAI pin) and Fable (Anthropic pin), reasoning effort minimal, no temperature setting; Qwen3-32B on SiliconFlow at temperature 0, reasoning off (`R_off`) and reasoning effort high (`R_high`) |
| Size and cost | 9,920 calls (100 per cell), $14.88 ($14.8838); parse check $0.22 ($0.2239) |
| Previous / next | [← 19 Favourite animal, crossed](../19_2026-10-16_favorite_animal_crossed/) · (last track 1 experiment) |

## What was done
1. **Audit** ([`STATIC_PILOT_AUDIT_2026-10-20.md`](STATIC_PILOT_AUDIT_2026-10-20.md)): every count from the six pilots (folders 14–19)
   recomputed from their CSVs. Corrections: the "7" attributed to dice came from the favourite-integer pilot
   (no dice hypothetical was ever 7; the dice default is 4); the animal result is a two-model dissociation
   (Astra 0/20, Fable 20/20); the crossed pilot's "semantic retrieval ruled out" claim does not hold;
   the pilots' Qwen "reasoning off" on DeepInfra actually reasoned about 1,200 tokens per call.
2. **Qwen parse check** on SiliconFlow (reasoning really off): 140/140 usable answers with reasoning off, 137/140 with reasoning high.
3. **Main run** with frozen prompts. Animal and dice tasks; 100 fresh calls per cell; cells:
   object level; self hypothetical (pilot wording, byte-identical); generic comparator ("a typical large
   language model"); generic name (animal: a typical model's full answer, letters derived offline);
   neutral wording without "you" (animal); supplied answer (animal: extract a letter from a given name);
   single roll (dice). Metric: `match` = probability that a comparator draw equals an independent object-level
   draw. Key contrast: match(self) − match(generic), with 95% bootstrap CIs.

## Questions
- Does asking about "you" track the model's own behaviour better than asking about "a typical large language model"?

## Results
From [Part I of the results report](../../docs/reports/SPAR_RESULTS_STATIC_AND_SELFPLAY_2026-10-21.md) and
[`results_summary/comparison_table.csv`](results_summary/comparison_table.csv) (match with the model's own object-level answers):

| model (own animal) | self, letters 1 / 2 / penult. / last | generic | dice: self answer |
|---|---|---|---|
| Astra (octopus) | .04 / .00 / .08 / .02 | 0 / 0 / 0 / 0 | "4" at every position |
| Fable (octopus) | 1 / 1 / 1 / 1 | 1 / 1 / 1 / .94 | mostly "4" |
| Qwen `R_off` (cat) | 1 / 0 / 0 / 0 | 1 / .32 / 0 / 0 | "5" at every position |
| Qwen `R_high` (dolphin) | .76 / .77 / .07 / .18 | .78 / .83 / .03 / .04 | "3" at every position |

- No model predicts itself better than it predicts a typical model in any consistent way.
- Fable's perfect O-C-U-S is matched by its answers about a typical model: a shared default, not self-specific knowledge.
- Dice hypotheticals are a position-invariant default; every model's single-roll answer is 4. Matches occur only where the real roll equals the default.
- The only self-specific signal is small, in Qwen `R_high`'s animal letters: last letter +.14 [.08, .22], penultimate +.05 [.01, .09].
  Qwen also shows small dice differences in both directions (e.g. `R_off` +.18 [.12, .24] at position 9; `R_high` −.10 [−.17, −.03] at position 1).
- Supplied-answer letter extraction: 20/20 at every position for every model, so failures are not about spelling.
- The generic dice question was often declined (Astra 192/400, Fable 173/400 calls; [`run_summary.json`](results_summary/run_summary.json)).

## Open questions
- These untrained prompts do not elicit self-simulation; that does not show it is impossible.
  Binder-style self-prediction finetuning against a matched external predictor was not attempted.
- Effects are exploratory, with many uncorrected contrasts.

## What it led to
This closes the static self-prediction line for the mid-term report. Work in the same period continued in
track 2 (paint-and-circle self-play, [`../../track2_game_theory/`](../../track2_game_theory/)).

## Files
- Audit: [`STATIC_PILOT_AUDIT_2026-10-20.md`](STATIC_PILOT_AUDIT_2026-10-20.md). Frozen prompts: [`STATIC_SELFPRED_PROMPTS_v1.0_FROZEN_2026-10-20.txt`](STATIC_SELFPRED_PROMPTS_v1.0_FROZEN_2026-10-20.txt).
- Main run: [`static_selfpred/main-20261021T021451Z/`](static_selfpred/main-20261021T021451Z/) — `responses.csv`, `raw_attempts.jsonl`,
  `manifest.json`, `summary.json`, `progress.log`, and `analysis/` (`comparison_table.csv`, `response_categories.csv`, `supplied_answer_check.csv`, figures).
- Parse check: [`static_selfpred/parsecheck-qwen-20261021T000345Z/`](static_selfpred/parsecheck-qwen-20261021T000345Z/).
- Summary copies for the report: [`results_summary/`](results_summary/) (tables, `match_animal.png`, `match_dice.png`, `run_summary.json`, `qwen_parse_check_summary.json`).
- Full write-up: [`docs/reports/SPAR_RESULTS_STATIC_AND_SELFPLAY_2026-10-21.md`](../../docs/reports/SPAR_RESULTS_STATIC_AND_SELFPLAY_2026-10-21.md), Part I.
- Code: [`src/spar_dynamic/static_selfpred/`](../../src/spar_dynamic/static_selfpred/) (`prompts.py`, `config.py`, `parse_check.py`, `main_run.py`, `analysis.py`).
- Tests: [`tests/test_static_selfpred.py`](../../tests/test_static_selfpred.py).

## Re-running
From the repo root (needs `OPENROUTER_API_KEY`; the main run refuses to resume if the prompts have changed):

```
PYTHONPATH=src python -m spar_dynamic.static_selfpred.parse_check qwen
PYTHONPATH=src python -m spar_dynamic.static_selfpred.main_run
PYTHONPATH=src python -m spar_dynamic.static_selfpred.main_run --resume <run folder>
PYTHONPATH=src python -m spar_dynamic.static_selfpred.analysis <run folder>
```
