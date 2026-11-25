# 34 · Unused faces: what does "angry" improve? (2026-11-25)

| | |
|---|---|
| Track | 1: static self-prediction |
| Status | **Complete.** Exploratory offline reanalysis of [33](../33_2026-11-24_dice_scaffolding/) (commit `025e50d`); no model calls, $0. |
| Design source | `docs/handoffs/GPT_SPAR_Dice_Unused_Faces_Handoff.md` |
| Report | [**REPORT.md**](REPORT.md) · [summary.json](summary.json) · [per_history.csv](per_history.csv) · [analyse.py](analyse.py) |

**Result.** *Angry* improves Qwen's repeat avoidance (unused-face probability +11.9 points at rolls 4-5, 95% CI +7.2 to +16.3) but not its ordering of the unused faces (+0.003 bits, CI -0.028 to +0.034). Where Qwen's and Mistral's favourite unused faces differ (8 histories, 6 families), Qwen's conditional gain is -0.042 (CI -0.100 to +0.004): no Qwen-specific improvement.

Rerun: `PYTHONPATH=src python track1_self_prediction/34_2026-11-25_dice_unused_faces/analyse.py`
