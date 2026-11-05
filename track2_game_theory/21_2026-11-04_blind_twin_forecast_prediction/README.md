# 21: Can a model predict its own forecasts? (Blind Twin forecast prediction, 2026-11-04)

Astra and Fable each wrote one zero-example Python predictor of Astra's forecasts and one of Fable's forecasts as observers
of matching pennies. That was four fresh API calls, $0.32 in total. The four programs were frozen, hashed and run offline in a
sandbox on 240 archived forecast pairs from folder 07: the six condition-00 self-play games, both seats.

**Result:** Astra's code predicted both judges better, so there is no reciprocal own-model advantage. Details:
[REPORT.md](REPORT.md).

| Path | Content |
|---|---|
| [REPORT.md](REPORT.md) | Answer, 2 × 2 Brier table, references, game-level contrasts, diagnostics, secondary readouts, run record |
| `plan/` | Frozen author messages (one per target), endpoint and price snapshot, `run_plan.json` (inputs, code and message hashes, cells, settings) |
| [APPROVAL.md](APPROVAL.md) | Live approval for this plan's hash only |
| `responses/calls.jsonl` | The four original author responses (request, raw response, usage, cost, returned model and provider) |
| `programs/` | The four frozen programs and `sources_sha256.json` |
| `validation/contract.json` | Contract check on synthetic histories |
| `scoring/` | `item_predictions.csv` (240 items: labels, retest labels, player moves, four programs' p(STAR)), `results.json` |
| `dry_run/` | The same pipeline with a fake author transport, made before any paid call |
| [manifest.json](manifest.json) | Commits, endpoint metadata, cost, validation counts, deviations, file hashes |

Code: `src/blind_twin_forecast_prediction/`. Tests: `tests/test_blind_twin_forecast_prediction.py`.

Reproduce the scoring with zero API calls:

```bash
PYTHONPATH=src python -m blind_twin_forecast_prediction validate
PYTHONPATH=src python -m blind_twin_forecast_prediction score
```
