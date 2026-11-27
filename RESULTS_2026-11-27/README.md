# Results, 2026-11-27

**Track 1, experiment 38: SLOT at every position.** Experiment 35's SLOT ending (roll k+1 marked blank, predict roll k+2) at every k = 1..8 over 170 prefixes from all 66 Qwen3-32B and Mistral Small 3.2 G sequences, scored against each model's exact two-step generation policy.
- **SLOT does not help either model skip ahead.** Qwen stops answering the missing roll but moves further from its own roll-(k+2) policy (−0.072 bits). Mistral moves slightly closer, mostly because it stops answering in prose.
- **Simple baselines win.** Neither model beats a uniform guess or a "use each face once per six" rule.
- **No self-specific advantage:** −0.004 bits, 95% CI −0.010 to +0.005.
- **Experiment 35's correct roll 7 was a face already shown:** at k = 5 Qwen never answers the missing face (0 of 24).

$1.63.

| What | Where |
|---|---|
| Report | [exp38/REPORT.md](exp38/REPORT.md) |
| Tables | [exp38/tables/](exp38/tables/) (`primary.csv` is the primary; `by_k.csv` per position; `summary.json` post-hoc free-answer counts) |
| Figure | [exp38/figures/fig38_slot_by_k.png](exp38/figures/fig38_slot_by_k.png) |
| Protocol, raw data, checks, run record (not copied) | [../track1_self_prediction/38_2026-11-27_slot_skip_ahead/](../track1_self_prediction/38_2026-11-27_slot_skip_ahead/) |

Copies made from the experiment folder; regenerate with `PYTHONPATH=src python -m spar_dynamic.slot_skip_ahead analyse` (no model calls).
