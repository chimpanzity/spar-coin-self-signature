# Results, 2026-10-31

Two experiments, both on Qwen3-32B and Mistral Small 3.2 24B open weights:

- **Experiment 28**: dice generation vs self-prediction on log-probabilities (files at this level).
- **Experiment 29**: bidirectional cross-model completion of Experiment 28's sequences (in [exp29/](exp29/)).

| What | Where |
|---|---|
| Report (midterm summary, outcome table, methods, results, caveats) | [REPORT_exp28.md](REPORT_exp28.md) |
| Figures (PNG + PDF): 1 design, 2 G vs F, 3 single positions and windows, 4 two-model comparison | [figures/](figures/) |
| Tables: `cross_model.csv` (side by side), per-model integrity, natural G vs F, matched prefix, singles, windows, overlaps; `summary.json` | [tables/](tables/) |
| Raw data (not copied): generations, matched-prefix rows, environment and gate records | [../track1_self_prediction/28_2026-10-31_dice_logprob_crossmodel/preflight/](../track1_self_prediction/28_2026-10-31_dice_logprob_crossmodel/preflight/), [../track1_self_prediction/28_2026-10-31_dice_logprob_crossmodel/main/](../track1_self_prediction/28_2026-10-31_dice_logprob_crossmodel/main/) |
| Frozen protocol, prompts, data dictionary, amendment, manifest | [../track1_self_prediction/28_2026-10-31_dice_logprob_crossmodel/](../track1_self_prediction/28_2026-10-31_dice_logprob_crossmodel/) |

Copies made from `track1_self_prediction/28_2026-10-31_dice_logprob_crossmodel/`; regenerate with `PYTHONPATH=src python -m spar_dynamic.dice_logprob_crossmodel analyse`.

## Experiment 29

| What | Where |
|---|---|
| Report and decision memo | [exp29/REPORT.md](exp29/REPORT.md), [exp29/DECISION_MEMO.md](exp29/DECISION_MEMO.md) |
| Figures (7, PNG + PDF) | [exp29/figures/](exp29/figures/) |
| Tables (positions, cells, crossed 2x2, middle arm, summary.json) | [exp29/tables/](exp29/tables/) |
| Raw data, protocol, approvals, manifest (not copied) | [track1_self_prediction/29_2026-10-31_bidirectional_dice_completion/](../track1_self_prediction/29_2026-10-31_bidirectional_dice_completion/) |
