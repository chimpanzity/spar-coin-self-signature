# Study 1, Experiment 1: status (2026-10-10, both runs complete)

**Update 17:35:** both cohorts collected. RPS 71/72 complete ($22.32); MP 54/72 complete ($20.28), all attrition from Qwen
bold-formatted answers. See STUDY1_EXPERIMENT1_REPORT.md. The table below is the pre-run snapshot.

Governing plan: `SPAR_Study1_Experiment1_Pilot_2_Games_Per_Cell_Claude_Handoff_2026-10-10.md` (two games per cell).

| | RPS | MP |
|---|---|---|
| Package | `opponent_disclosure_rps_3models/` | `opponent_disclosure_mp_3models/` (new) |
| Run folder | `results/rps3m-p2-20261010` | `results/mp3m-p2-20261010` |
| Protocol | RPSDisclosure3M_v1_pilot2 | MPDisclosure3M_v1_pilot2 |
| Planned cells / games / calls | 36 / 72 / 2,880 | 36 / 72 / 2,880 |
| Games attempted / complete | 0 / 0 | 0 / 0 |
| Valid choices | 0 | 0 |
| Spent / in flight | $0 / $0 | $0 / $0 |
| Schedule hash | af8e594317b1 | e2737f77779f |
| Offline validation | PASS (72 fake games, rescore matches) | PASS (72 fake games, rescore matches, Fable parser 480/480, prompt invariants) |
| Approval | not approved | not approved |
| Missing analyses | all (no data) | all (no data) |

## Existing runs (preserved unchanged)

- `opponent_disclosure_rps_3models/results/rps3m-20261009T1240Z`: eight-game RPS cohort, frozen 2026-10-09, never
  approved or executed (0 calls). Marked SUPERSEDED in its PROGRESS.md; the package code changed afterwards, so its
  manifest can no longer launch. Not resized: the two-game cohort is a new prospective cohort with its own seeds.
- `opponent_disclosure/results/od-20261009T1200Z`: Astra-vs-Astra MP pilot, 32 games, $7.05. Historical feasibility
  evidence only; different prompts and estimands; not pooled.
- Blind Twin RPS runs `rps-20261009T1024Z`, `rps-qf-20261009T1045Z`, `rps-qa-20261009T1124Z`: source of per-call cost
  estimates (1,440/1,440 valid player calls on the same endpoints).

## Deviations and notes

- The canonical `RPS_Opponent_Disclosure_Three_Model_Claude_Handoff_2026-10-09.md` is not in the repository; the RPS
  protocol is taken from `opponent_disclosure_rps_3models/protocol.md`, which was written from it.
- RPS changes for the amendment: REPLICATES 8 -> 2, protocol id, proposed cap $200 -> $60, report text. Templates,
  endpoints, parser, scoring and analysis are unchanged (template hashes identical).
- Endpoints checked live 2026-10-10: all three up, prices unchanged since the 2026-10-09 snapshot.
- MP output names follow the handoff (`manifest.json`, `baseline_predictions.csv`, `bootstrap_intervals.csv`); RPS keeps
  its existing names (`frozen_manifest.json`, `history_baselines.csv`, `bootstrap.csv`).

## Next exact steps

1. Chris approves caps (see EXPERIMENT1_BUDGET_AND_APPROVAL.md); Claude writes the approval line in each APPROVAL.md.
2. `python -m opponent_disclosure_rps_3models run --run rps3m-p2-20261010 --live`, then the same for MP. The 3-game
   technical smoke is optional.
3. Analyses run automatically at the end of each run; then write STUDY1_EXPERIMENT1_REPORT.md.
