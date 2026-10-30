# LOULA_DICE_YESNO_LOGPROB_v3.0 Stage A calibration

Gate: **FAIL** (epsilon = 0.09659 log-odds). 36 new items, never scored before.

| Criterion | Result |
|---|---|
| S > eps in >= 29/36 | PASS |
| MORE_SIXES >= 9/12 | PASS |
| MORE_REPEATS >= 8/12 | PASS |
| GEN_RULE >= 10/12 | PASS |
| both polarities correct in >= 24/36 | FAIL |

## Per task (units are items; CIs bootstrap items)

| Task | S > eps | S < -eps | tie | both polarities correct | mean S [95% CI] | mean c_pos | mean c_neg | Yes bias pos / neg | coherence | min P(Yes)+P(No) | greedy separates X from Y: pos / neg |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MORE_SIXES | 12/12 | 0 | 0 | 12/12 | +3.32 [+2.56, +4.19] | +4.20 | +2.43 | -2.57 / +0.94 | -3.50 | 0.996 | 4/12 / 6/12 |
| MORE_REPEATS | 8/12 | 2 | 2 | 2/12 | +0.71 [+0.20, +1.27] | +1.46 | -0.04 | +0.05 / +0.72 | -0.67 | 0.994 | 3/12 / 0/12 |
| GEN_RULE | 12/12 | 0 | 0 | 6/12 | +3.41 [+2.90, +3.99] | +6.62 | +0.20 | +1.96 / +2.12 | -0.16 | 0.994 | 10/12 / 0/12 |
| overall | 32/36 | 2 | 2 | 20/36 | +2.48 [+1.92, +3.03] | +4.09 | +0.86 | -0.19 / +1.26 | -1.44 | 0.994 | 17/36 / 6/36 |

## Historical comparison: Experiment 24 (A/B, two orders, Experiment 23 items)

Different items and a different question format; descriptive only.

| Task | v2.1: S > eps /12 | v2.1: both orders /12 | v2.1 mean S | v2.1 mean A bias | v3.0: S > eps /12 | v3.0: both polarities /12 | v3.0 mean S |
|---|---|---|---|---|---|---|---|
| MORE_SIXES | 12 | 4 | +5.24 | +4.06 | 12 | 12 | +3.32 |
| MORE_REPEATS | 12 | 5 | +0.71 | +0.77 | 8 | 2 | +0.71 |
| GEN_RULE | 12 | 11 | +7.09 | +3.12 | 12 | 6 | +3.41 |
| overall | 36 | 20 | +4.34 | +2.65 | 32 | 20 | +2.48 |

## S by size of the count difference (X minus Y)

- **MORE_SIXES**: diff 1: n 9, mean S +2.86, min +2.10; diff 2: n 1, mean S +1.58, min +1.58; diff 3: n 2, mean S +6.26, min +5.89
- **MORE_REPEATS**: diff 1: n 5, mean S +0.25, min -0.22; diff 2: n 3, mean S +1.69, min +0.81; diff 3: n 4, mean S +0.54, min -0.94
- **GEN_RULE**: diff 6: n 3, mean S +2.99, min +2.16; diff 7: n 2, mean S +4.45, min +4.06; diff 9: n 2, mean S +4.09, min +2.61; diff 10: n 1, mean S +3.22, min +3.22; diff 11: n 2, mean S +2.50, min +2.26; diff 12: n 1, mean S +3.49, min +3.49; diff 14: n 1, mean S +3.16, min +3.16
