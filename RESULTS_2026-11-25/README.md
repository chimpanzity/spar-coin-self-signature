# Results, 2026-11-25

**Track 1, experiment 33: dice forecast scaffolding.** Qwen3-32B and Mistral Small 3.2 forecast the next die roll of a described
roller; independently measured SELF/OTHER word associations were tested as predictors of which words help. No support for
self-specific forecasting (joint association test -0.0018 bits, 95% CI -0.0098 to +0.0042). The null is weak: Mistral answers in
prose, and neither model forecasts its own policy better than a uniform vector. $3.88.

| What | Where |
|---|---|
| Report | [REPORT.md](REPORT.md) |
| Tables | [tables/](tables/) (`core_pairs_primary.csv` is the primary) |
| Figures | [figures/](figures/) |
| Protocol, raw data, checks, run record (not copied) | [../track1_self_prediction/33_2026-11-24_dice_scaffolding/](../track1_self_prediction/33_2026-11-24_dice_scaffolding/) |

Copies made from the experiment folder; regenerate with `PYTHONPATH=src python -m spar_dynamic.dice_scaffolding analyse --phase all` (no model calls).

## Experiment 34: unused faces (exploratory reanalysis of 33)

*Angry* raises Qwen's probability of an unused face (+11.9 points at rolls 4-5) but does not improve its ordering of the unused faces,
and there is no Qwen-specific improvement where the two models' favourites differ (8 histories, 6 families). No model calls.

| What | Where |
|---|---|
| Report | [exp34/REPORT.md](exp34/REPORT.md) |
| Estimates and per-history rows | [exp34/summary.json](exp34/summary.json), [exp34/per_history.csv](exp34/per_history.csv) |
| Script (not copied) | [../track1_self_prediction/34_2026-11-25_dice_unused_faces/](../track1_self_prediction/34_2026-11-25_dice_unused_faces/) |

## Experiment 35: roll-7 prompt scaffolding

No scaffold reliably helps a model skip to roll 7 (1 of 24 standard cells correct, 15 give the sixth). Qwen thinking is cut off at
1,024 tokens in all 12 cells; supplementary 4,096-token runs finish in 10 and none is correct.

| What | Where |
|---|---|
| Report and figure | [exp35/REPORT.md](exp35/REPORT.md) |
| Tables | [exp35/](exp35/) |
| Protocol, raw data, checks (not copied) | [../track1_self_prediction/35_2026-11-25_roll7_prompt_scaffolding/](../track1_self_prediction/35_2026-11-25_roll7_prompt_scaffolding/) |
