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
