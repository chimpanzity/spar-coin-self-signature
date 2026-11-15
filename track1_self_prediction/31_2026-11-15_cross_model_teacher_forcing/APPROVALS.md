# Experiments 31 and 32: investigator decisions

| Date (UTC) | Decision | By |
|---|---|---|
| 2026-11-15 | Run Experiments 31 and 32 as specified in `GPT_SPAR_Experiments_31_32_Revised_Claude_Code_Handoff.md` (handed over in-session). | Investigator |
| 2026-11-15 | After the freeze commit `bba03b5`: rent one vast.ai A100 (quoted offer 58627268, about $1 all-in, **hard cap $10**), run both models through both experiments, then destroy the instance. | Investigator (in-session approval) |

## Deviations from the approved rental

| Deviation | Cost |
|---|---:|
| The quoted offer's GPU was taken by another tenant: the instance never started, and it was destroyed. | $0.004 |
| The next offer turned out to be a 40GB A100: my search lacked a GPU-memory filter. It was destroyed before any model call. | $0.037 |
| The run used an 80GB A100 at $1.253/h with driver 595.91.07 (Experiment 30's driver). | $0.692 |
| **Total** | **$0.73** |

The total stayed under the approved $1 estimate and far under the $10 cap.

No design, prompt or code change was made after the freeze.
