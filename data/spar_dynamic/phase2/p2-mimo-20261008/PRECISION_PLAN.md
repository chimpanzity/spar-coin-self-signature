# Precision plan (written before test generation)

## Planned support

- 24 attempted test parents per source x prompt (144 total).
- At most 12 pair blocks per prompt (24 blocks, 144 unordered pairs, each judged in both orders by all three judges).
- Named arm: at most six parents per source x prompt (36 total).

## Expected usable support, from development validity rates (assumption, not a guarantee)

| source x prompt | development valid rate | expected valid test parents of 24 |
|---|---:|---:|
| astra x plain | 60/60 | 24.0 |
| astra x fair | 60/60 | 24.0 |
| fable x plain | 60/60 | 24.0 |
| fable x fair | 59/60 | 23.6 |
| mimo x plain | 56/60 | 22.4 |
| mimo x fair | 25/60 | 10.0 |

Cells expected to fall below 80% valid: mimo|fair (about 10.0 of 24). Pair blocks need at least two valid parents from every source in a prompt, so those prompts may have few or no blocks, and crossovers needing those sources may be non-estimable. Under the frozen rules a non-estimable component makes the panel summary non-estimable; it is never silently dropped. Per-prompt results are reported separately.

## Assumption-only completion half-width scenarios (Section 11.4)

Normal half-width approx 1.96 s / sqrt(144) for independent parent-level contrasts with no missingness and equal cell weights. These are arithmetic sensitivity scenarios, not estimated study intervals.

| s | half-width |
|---:|---:|
| 0.05 | 0.0082 |
| 0.10 | 0.0163 |
| 0.20 | 0.0327 |
| 0.30 | 0.0490 |

## Reporting margins (fixed before test generation)

- delta_Brier = 0.02 for H4, gains and own-advantage contrasts.
- delta_AUC = 0.05 for R/P/D and named contrasts.
- Formal equivalence/absence claims are disabled.

## Task-specific power

Task-specific power for R/P/D and the named arm is unknown: no score simulations were run. Large reliable effects may be detectable; small effects cannot be ruled out by the planned size. The twelve-parent rehearsal cannot pin down variance assumptions.

