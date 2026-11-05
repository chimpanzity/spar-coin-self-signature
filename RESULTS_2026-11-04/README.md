# Results, 2026-11-04

**Track 2, folder 21: Can a model predict its own forecasts?** Astra and Fable each wrote predictors of Astra's and Fable's
archived Blind Twin observer forecasts; frozen programs scored offline. No reciprocal own-model advantage: Astra's code
predicted both judges better (Fable target 0.256 vs 0.288; Astra target 0.225 vs 0.262). $0.32.

| What | Where |
|---|---|
| Report | [REPORT.md](REPORT.md) |
| The four frozen programs and their hashes | [programs/](programs/) |
| Tables: `results.json` (all contrasts and readouts), `item_predictions.csv` (240 items) | [tables/](tables/) |
| Plan, prompts, approval, raw responses, validation, dry run, manifest (not copied) | [../track2_game_theory/21_2026-11-04_blind_twin_forecast_prediction/](../track2_game_theory/21_2026-11-04_blind_twin_forecast_prediction/) |

Copies made from `track2_game_theory/21_2026-11-04_blind_twin_forecast_prediction/`; regenerate with `PYTHONPATH=src python -m blind_twin_forecast_prediction score` (zero API calls).

## Track 2, folder 22: first-level Blind Coder

Astra and Fable each wrote 10 predictors of Astra's and Fable's actual matching-pennies choices (40 calls, $3.14). Astra's code
predicted both players better (0.226 vs 0.273 for Astra; 0.214 vs 0.256 for Fable). There was no reciprocal own-model advantage,
naming the target did not help, and no program captured the players' win/loss switching.

| What | Where |
|---|---|
| Report | [exp22/REPORT.md](exp22/REPORT.md) |
| Tables: `results.json`, `generation_scores.csv` (40 programs), `item_predictions.csv` (480 decisions) | [exp22/tables/](exp22/tables/) |
| Plan, prompts, approval, raw responses, 40 programs, validation, dry run, manifest (not copied) | [../track2_game_theory/22_2026-11-04_first_level_blind_coder/](../track2_game_theory/22_2026-11-04_first_level_blind_coder/) |
