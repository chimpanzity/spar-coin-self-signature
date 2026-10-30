# LOULA_DICE_AB_LOGPROB_v2.1 Stage A calibration

Gate: **FAIL** (epsilon = 0.05804 log-odds). Exploratory: these 36 items were already used in Experiment 23.

| Criterion | Result |
|---|---|
| S_correct > eps in >= 29/36 | PASS |
| MORE_SIXES >= 9/12 | PASS |
| MORE_REPEATS >= 8/12 | PASS |
| GEN_RULE >= 10/12 | PASS |
| both orders correct in >= 24/36 | FAIL |

## Per task (units are items; CIs bootstrap items)

| Task | S > eps | S < -eps | tie | both orders correct | mean S [95% CI] | median S | mean B_pair | min P(A)+P(B) | greedy argmax correct /24 (consistent /12) |
|---|---|---|---|---|---|---|---|---|---|
| MORE_SIXES | 12/12 | 0 | 0 | 4/12 | +5.24 [+3.29, +7.43] | +4.03 | +4.06 | 0.931 | 16/24 (4/12) |
| MORE_REPEATS | 12/12 | 0 | 0 | 5/12 | +0.71 [+0.50, +0.90] | +0.74 | +0.77 | 0.801 | 19/24 (7/12) |
| GEN_RULE | 12/12 | 0 | 0 | 11/12 | +7.09 [+6.24, +8.05] | +6.54 | +3.12 | 0.969 | 23/24 (11/12) |
| overall | 36/36 | 0 | 0 | 20/36 | +4.34 [+3.20, +5.55] | +4.03 | +2.65 | 0.801 | 58/72 (22/36) |

## Historical benchmark: Experiment 23 emitted Qwen answers (OpenRouter/SiliconFlow, temperature 0)

Different serving and different answer instruction; descriptive only, not paired trials.

| Task | bare: correct /24, consistent /12, A-rate | brief: correct /24, consistent /12, A-rate |
|---|---|---|
| MORE_SIXES | 16, 4, 0.83 | 23, 11, 0.52 |
| MORE_REPEATS | 12, 0, 1.00 | 19, 9, 0.54 |
| GEN_RULE | 19, 7, 0.71 | 24, 12, 0.50 |

## S by size of the count difference (X minus Y)

- **MORE_SIXES**: diff 1: n 7, mean S +4.71, min +1.23; diff 2: n 5, mean S +5.98, min +3.84
- **MORE_REPEATS**: diff 1: n 3, mean S +0.82, min +0.75; diff 2: n 4, mean S +0.62, min +0.07; diff 3: n 5, mean S +0.71, min +0.45
- **GEN_RULE**: diff 7: n 1, mean S +10.65, min +10.65; diff 8: n 1, mean S +9.57, min +9.57; diff 10: n 1, mean S +4.77, min +4.77; diff 11: n 3, mean S +7.12, min +6.22; diff 12: n 1, mean S +7.53, min +7.53; diff 13: n 3, mean S +6.48, min +6.36; diff 14: n 1, mean S +6.38, min +6.38; diff 16: n 1, mean S +5.35, min +5.35
