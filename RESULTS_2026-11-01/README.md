# Results, 2026-11-01

**Experiment 30**: six-roll self-recognition by minimal-pair discrimination, on Qwen3-32B and Mistral Small 3.2 24B open
weights (one A100, $2.09). No self-specific recognition: swap D_G = −0.28, D_F = −0.03 log-odds; both judges passed every gate.

| What | Where |
|---|---|
| Report and decision memo | [REPORT.md](REPORT.md), [DECISION_MEMO.md](DECISION_MEMO.md) |
| Figures (PNG + PDF): 1 policy benchmark, 2 swap scores, 2b repeat scores, 3 crossed contrasts, 4 calibration, 5 generation vs recognition | [figures/](figures/) |
| Tables: policy likelihoods and deltas, presentations, paired scores, crossed contrasts, self vs neutral, summaries; `summary.json`, `calibration_gate.json` | [tables/](tables/) |
| Raw data, frozen protocol, prompts, approvals, gates, host logs, manifest (not copied) | [../track1_self_prediction/30_2026-11-01_six_roll_recognition/](../track1_self_prediction/30_2026-11-01_six_roll_recognition/) |

Copies made from `track1_self_prediction/30_2026-11-01_six_roll_recognition/`; regenerate with `PYTHONPATH=src python -m spar_dynamic.dice_six_roll_recognition analyse`.
