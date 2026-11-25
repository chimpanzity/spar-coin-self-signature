# Experiment 34: what does *angry* improve? Reanalysis of Experiment 33

**Exploratory.** The word *angry* was chosen after seeing Experiment 33. No model calls; this reads the archived probabilities of Experiment 33 (commit `025e50d`). Qwen is the forecaster. The targets are Qwen's and Mistral's uncued direct-generation distributions.

Rerun from the repo root: `PYTHONPATH=src python track1_self_prediction/34_2026-11-25_dice_unused_faces/analyse.py` (writes `summary.json` and `per_history.csv`).

## Verdict

*Angry* improves **repeat avoidance**. It does not reliably improve the ordering of the unused faces, and there is **no evidence of Qwen-specific improvement**.

| Question | Answer |
|---|---|
| Does *angry* make Qwen better at guessing the next face will be unused? | **Yes.** At rolls 4 and 5, forecast probability on unused faces rises from 60.6% to 72.5% (targets: 99.6% for Qwen, 97.8% for Mistral). |
| Does it improve the ordering of unused faces for both targets? | **Not reliably.** Conditional gain is +0.003 bits (Qwen) and +0.016 bits (Mistral), both intervals including zero. At roll 4 alone Mistral's is positive (+0.036); at roll 5 both are slightly negative. |
| Does it improve prediction of Qwen's distinctive preference? | **No.** Where the two targets disagree, Qwen's conditional gain is −0.042 bits, below Mistral's (−0.018), and probability on Qwen's favourite falls by 5.8 points. The interval for each includes zero, from 8 histories in 6 families. |

This fits Experiment 33: *angry*'s gain is nearly the same for both targets, because both avoid repeats.

## Method

Estimates average within opening family, then equally across contributing families. Intervals are 95% percentile bootstraps over whole families (10,000 draws, PCG64 seed 241125), keeping prompts and targets paired. The loader check reproduces the published full six-face gains over the 84 confirmation histories (+0.088 toward Qwen, +0.086 toward Mistral). The primary set is rolls 4 and 5 of the confirmation bank: 24 histories, 12 families. No conditional score had a zero denominator, and no target had a tied favourite.

## 1. Probability of an unused face

| | Rolls 4 and 5 (12 families, 24 histories) | Roll 4 (12 families) | Roll 5 (12 families) | Roll 6 check (12 families, one unused face) |
|---|---|---|---|---|
| Neutral forecast | 60.6% | 69.3% | 51.9% | 38.7% |
| *Angry* forecast | 72.5% | 77.5% | 67.6% | 82.6% |
| Change, points [95% CI] | +11.9 [+7.2, +16.3] | +8.2 [+2.4, +13.2] | +15.6 [+9.0, +23.0] | +43.9 [+27.6, +60.9] |
| Families improving | 11 of 12 | 10 of 12 | 11 of 12 | 12 of 12 |
| Qwen's actual unused mass | 99.6% | 99.9% | 99.3% | 99.4% |
| Mistral's actual unused mass | 97.8% | 99.4% | 96.2% | 94.0% |
| Error reduction vs Qwen, points [95% CI] | +11.8 [+7.1, +16.2] | +8.2 [+2.4, +13.2] | +15.4 [+8.6, +22.9] | +43.3 [+26.6, +60.4] |
| Error reduction vs Mistral, points [95% CI] | +11.5 [+6.7, +15.9] | +8.2 [+2.4, +13.2] | +14.7 [+7.2, +22.6] | +37.4 [+19.4, +55.1] |

The forecast is still well short of the targets, so the rise is in the right direction.

## 2. Ordering among the unused faces

Conditional Jensen–Shannon divergence in bits, after restricting and renormalising all four distributions to the unused faces. Gain is neutral minus *angry*.

| | Rolls 4 and 5 | Roll 4 | Roll 5 |
|---|---|---|---|
| To Qwen: neutral → *angry* | 0.221 → 0.218 | 0.265 → 0.246 | 0.176 → 0.190 |
| **Qwen gain** [95% CI] | +0.003 [−0.028, +0.034] | +0.019 [−0.036, +0.076] | −0.014 [−0.040, +0.012] |
| To Mistral: neutral → *angry* | 0.306 → 0.290 | 0.348 → 0.311 | 0.264 → 0.269 |
| **Mistral gain** [95% CI] | +0.016 [−0.009, +0.041] | +0.036 [+0.002, +0.072] | −0.005 [−0.045, +0.029] |
| **Qwen − Mistral** [95% CI] | −0.013 [−0.033, +0.007] | −0.018 [−0.047, +0.012] | −0.009 [−0.041, +0.016] |
| Families (Qwen gain > 0) | 5 of 12 | 6 of 12 | 4 of 12 |

Across both rolls, Qwen's conditional forecasts (0.221 neutral) are further from its own ordering than a uniform distribution over the unused faces (0.161); the corresponding Mistral values are 0.306 and 0.138. Roll-4 Mistral is the only interval excluding zero, and it is one of several looked at in an exploratory analysis.

## 3. Decisive comparison: histories where the targets' favourites differ

8 histories in 6 of the 12 families, chosen from the target vectors alone. The subset is sparse.

| | Mean over 6 families [95% CI] | Families > 0 |
|---|---|---|
| Qwen conditional gain | −0.042 [−0.100, +0.004] | 1 of 6 |
| Mistral conditional gain | −0.018 [−0.044, +0.009] | 2 of 6 |
| Qwen − Mistral | −0.025 [−0.062, +0.007] | 4 of 6 |
| Forecast share on Qwen's favourite, neutral → *angry* | 61.7% → 55.9%; −5.8 points [−14.1, +1.7] | 2 of 6 |
| Forecast share on Mistral's favourite, neutral → *angry* | 20.6% → 22.1%; +1.5 points [−3.0, +8.6] | 1 of 6 |

The negative means rest mainly on family c09. With any one family left out, Qwen's gain stays between −0.060 and −0.017 and the difference between −0.032 and −0.010.

| Family | Roll | History | Unused | Qwen / Mistral favourite | Qwen gain | Mistral gain | Share on Qwen's favourite | Share on Mistral's favourite |
|---|---|---|---|---|---|---|---|---|
| c06 | 4 | 4 2 5 | 1 3 6 | 6 / 1 | −0.032 | −0.026 | 0.674 → 0.643 | 0.010 → 0.003 |
| c06 | 5 | 4 2 5 6 | 1 3 | 3 / 1 | −0.014 | −0.028 | 0.972 → 0.983 | 0.028 → 0.017 |
| c08 | 4 | 2 3 4 | 1 5 6 | 6 / 1 | −0.015 | −0.017 | 0.676 → 0.666 | 0.009 → 0.004 |
| c08 | 5 | 2 3 4 5 | 1 6 | 6 / 1 | −0.012 | −0.014 | 0.996 → 0.999 | 0.004 → 0.001 |
| c09 | 4 | 5 2 6 | 1 3 4 | 3 / 1 | −0.171 | −0.069 | 0.539 → 0.323 | 0.022 → 0.007 |
| c11 | 4 | 1 6 2 | 3 4 5 | 3 / 4 | −0.060 | +0.013 | 0.376 → 0.193 | 0.315 → 0.497 |
| c13 | 5 | 5 6 1 3 | 2 4 | 2 / 4 | +0.044 | +0.033 | 0.148 → 0.199 | 0.852 → 0.801 |
| c14 | 5 | 3 4 2 5 | 1 6 | 6 / 1 | −0.030 | −0.038 | 0.979 → 0.993 | 0.021 → 0.007 |

Some disagreements are near ties: in c13 Mistral's favourite leads by 0.001, and in c14 Qwen's leads by 0.037. The gain can also be negative when the share of the favourite rises, because the forecast is already more concentrated than the target.

## 4. Worked example: prefix 5 2 6

All records are available in the archive. This is the confirmatory history of family c09, so it also appears in section 3. Six-face-normalised probabilities:

| | 1 | 3 | 4 | Unused total | Share of 3 among unused |
|---|---|---|---|---|---|
| Qwen forecast, "a shape" | 0.011 | 0.266 | 0.216 | 0.493 | 0.539 |
| Qwen forecast, *angry* | 0.004 | 0.202 | 0.420 | 0.626 | 0.323 |
| Qwen direct | 0.333 | 0.641 | 0.026 | 1.000 | 0.642 |
| Mistral direct | 0.925 | 0.072 | 0.002 | 1.000 | 0.072 |

The targets do disagree (Qwen favours 3, Mistral 1). The share on 3 **fell** from 0.539 to 0.323 as *angry* moved probability onto 4, which neither target favours. The unused total rose from 0.493 to 0.626.

## Limits

- *Angry* was picked after the fact as the word with the largest gain. It is one word, one forecaster, and two checkpoints.
- Disagreement histories number 8 in 6 families; the intervals are wide and the bootstrap over so few families is approximate.
- Whether the rise in unused mass is specific to *angry* or shared by other words was not tested here.
