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
