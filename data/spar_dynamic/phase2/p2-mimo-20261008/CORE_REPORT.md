# SPAR Phase 2 pilot: core report

Run `p2-mimo-20261008`, protocol SPAR_Phase2_v7.1, generated 2026-10-08T10:55:02.443500Z.
Report scope: CORE plus retained arms (named: complete; historical: complete).

Exploratory pilot. Intervals are marginal two-sided 95% percentile bootstrap intervals, not multiplicity-adjusted. Reporting margins: delta_Brier = 0.02, delta_AUC = 0.05.

## 1. H4 completion readout (key, two-sided)

Positive values mean disclosure of the true source helps the panel's own-model forecasts relatively more than other-model forecasts. Neither sign is evidence of introspection.

| quantity | estimate | 95% CI | direction | bounded within margin |
|---|---:|---|---|---|
| H4 | -0.0004 | [-0.0010, +0.0002] | unresolved | True |
| gain_own | -0.0001 | [-0.0004, +0.0002] | unresolved | True |
| gain_other | +0.0003 | [-0.0002, +0.0008] | unresolved | True |
| C_known | -0.0019 | [-0.0059, +0.0002] | unresolved | True |
| C_withheld | -0.0015 | [-0.0050, +0.0004] | unresolved | True |

Bootstrap: 5000 parent resamples within source x prompt; undefined replicates 0.000. Panel estimable: True.

### Per prompt and per judge pair (pairwise-common sets)

| crossover | H4 | gain_own | gain_other | C_known | C_withheld |
|---|---:|---:|---:|---:|---:|
| astra-fable|plain | +0.0002 | +0.0002 | +0.0001 | +0.0002 | +0.0001 |
| astra-mimo|plain | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| fable-mimo|plain | -0.0000 | +0.0002 | +0.0002 | -0.0005 | -0.0005 |
| astra-fable|fair | -0.0008 | -0.0006 | +0.0002 | -0.0002 | +0.0006 |
| astra-mimo|fair | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| fable-mimo|fair | -0.0018 | -0.0006 | +0.0013 | -0.0112 | -0.0094 |
| **prompt plain (3-pair mean)** | +0.0000 [-0.0007, +0.0009] | +0.0001 | +0.0001 | -0.0001 | -0.0001 |
| **prompt fair (3-pair mean)** | -0.0009 [-0.0019, -0.0001] | -0.0004 | +0.0005 | -0.0038 | -0.0029 |

Common-three-judge sensitivity panel: H4 -0.0004 [-0.0010, +0.0002], gain_own -0.0001 [-0.0004, +0.0002], gain_other +0.0003 [-0.0002, +0.0008], C_known -0.0019 [-0.0058, +0.0002], C_withheld -0.0015 [-0.0051, +0.0004]
Worst-case complete-data bounds on panel H4 (unobserved losses set to 0/1): [-0.0021, +0.0048].

### Absolute forecast skill (mean Brier; fair coin = 0.25)

| judge | condition | astra/plain | astra/fair | fable/plain | fable/fair | mimo/plain | mimo/fair |
|---|---|---:|---:|---:|---:|---:|---:|
| astra | known | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=22) | 0.250 (n=10) |
| astra | withheld | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=22) | 0.250 (n=10) |
| fable | known | 0.250 (n=24) | 0.249 (n=24) | 0.250 (n=24) | 0.250 (n=24) | 0.249 (n=22) | 0.227 (n=10) |
| fable | withheld | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=23) | 0.249 (n=24) | 0.249 (n=22) | 0.230 (n=10) |
| mimo | known | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=22) | 0.250 (n=10) |
| mimo | withheld | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=22) | 0.250 (n=10) |

How often judges return 0.5 at every position (amendment A3, descriptive):

| judge | source | condition | n | share all-0.5 | mean abs deviation from 0.5 |
|---|---|---|---:|---:|---:|
| astra | astra | known | 48 | 1.000 | 0.000 |
| astra | astra | withheld | 48 | 1.000 | 0.000 |
| astra | fable | known | 48 | 1.000 | 0.000 |
| astra | fable | withheld | 48 | 1.000 | 0.000 |
| astra | mimo | known | 32 | 1.000 | 0.000 |
| astra | mimo | withheld | 32 | 1.000 | 0.000 |
| fable | astra | known | 48 | 0.812 | 0.001 |
| fable | astra | withheld | 48 | 0.479 | 0.004 |
| fable | fable | known | 48 | 0.646 | 0.003 |
| fable | fable | withheld | 47 | 0.574 | 0.003 |
| fable | mimo | known | 32 | 0.719 | 0.013 |
| fable | mimo | withheld | 32 | 0.750 | 0.011 |
| mimo | astra | known | 48 | 1.000 | 0.000 |
| mimo | astra | withheld | 48 | 1.000 | 0.000 |
| mimo | fable | known | 48 | 1.000 | 0.000 |
| mimo | fable | withheld | 48 | 1.000 | 0.000 |
| mimo | mimo | known | 32 | 1.000 | 0.000 |
| mimo | mimo | withheld | 32 | 1.000 | 0.000 |

External baselines on the same test parents (fit on development only):

| source/prompt | n | fair | pooled position | source position | observer known | observer withheld | L2 known | L2 withheld |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| astra|plain | 24 | 0.250 | 0.247 | 0.238 | 0.186 | 0.195 | 0.207 | 0.210 |
| fable|plain | 24 | 0.250 | 0.213 | 0.198 | 0.148 | 0.136 | 0.132 | 0.133 |
| mimo|plain | 22 | 0.250 | 0.266 | 0.250 | 0.258 | 0.251 | 0.260 | 0.272 |
| astra|fair | 24 | 0.250 | 0.243 | 0.232 | 0.184 | 0.195 | 0.211 | 0.222 |
| fable|fair | 24 | 0.250 | 0.228 | 0.211 | 0.186 | 0.185 | 0.188 | 0.201 |
| mimo|fair | 10 | 0.250 | 0.248 | 0.255 | 0.259 | 0.250 | 0.260 | 0.254 |

Per-model identity gains (withheld minus known loss, available case; positive = disclosure helped):

| judge | astra/plain | astra/fair | fable/plain | fable/fair | mimo/plain | mimo/fair |
|---|---:|---:|---:|---:|---:|---:|
| astra | +0.0000 *own* | +0.0000 *own* | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| fable | +0.0001 | +0.0004 | +0.0004 *own* | -0.0011 *own* | +0.0004 | +0.0026 |
| mimo | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 *own* | +0.0000 *own* |

Suffix-permutation coupling diagnostic (intact vs within-cell permuted suffixes; share of permutations with loss <= intact):

| judge | condition | intact | permuted mean | share perm <= intact |
|---|---|---:|---:|---:|
| astra | known | 0.250 | 0.250 | 1.000 |
| astra | withheld | 0.250 | 0.250 | 1.000 |
| fable | known | 0.248 | 0.248 | 0.479 |
| fable | withheld | 0.248 | 0.248 | 0.502 |
| mimo | known | 0.250 | 0.250 | 1.000 |
| mimo | withheld | 0.250 | 0.250 | 1.000 |

Completion controls on the audit parents (mean absolute difference per position):

| judge | identical repeat | P(T) polarity (canonicalized) | polarity signed |
|---|---:|---:|---:|
| astra | 0.018 | 0.016 | +0.0000 |
| fable | 0.007 | 0.007 | +0.0029 |
| mimo | 0.000 | 0.000 | +0.0000 |

## 2. Anonymous SAME/DIFFERENT recognition (primary recognition endpoint)

R = (P + D)/2, where P compares the focal-source judge with the uninvolved judge and D compares the alternative-source judge with the uninvolved judge, using AUROC of the two-order mean P(SAME). R measures own-model involvement in source-relation discrimination, not self-authorship.

| quantity | estimate | 95% CI (block bootstrap) | direction | bounded within margin |
|---|---:|---|---|---|
| R | -0.0189 | [-0.0739, +0.0343] | none | False |
| P | +0.0326 | [-0.0328, +0.0864] | none | False |
| D | -0.0704 | [-0.1303, -0.0056] | none | False |

Support: {'n_pairs': 96, 'n_blocks': 16, 'per_prompt_pairs': {'plain': 66, 'fair': 30}}. Undefined bootstrap replicates: 0.011. Panel estimable: True.

- Per-prompt (secondary; CI added by amendment A3) prompt plain: R -0.0498 [-0.1230, +0.0264], P -0.0228 [-0.1226, +0.0775], D -0.0769 [-0.1347, -0.0139]
- Per-prompt (secondary; CI added by amendment A3) prompt fair: R +0.0121 [-0.0550, +0.0856], P +0.0881 [+0.0067, +0.1400], D -0.0639 [-0.1733, +0.0483]

| crossover | P | D | R | items |
|---|---:|---:|---:|---:|
| astra-fable|plain | -0.0281 | -0.0647 | -0.0464 | 57 |
| astra-mimo|plain | -0.0207 | -0.0186 | -0.0196 | 66 |
| fable-mimo|plain | -0.0197 | -0.1472 | -0.0835 | 57 |
| astra-fable|fair | +0.1375 | -0.0500 | +0.0438 | 26 |
| astra-mimo|fair | +0.0000 | +0.0000 | +0.0000 | 30 |
| fable-mimo|fair | +0.1267 | -0.1417 | -0.0075 | 26 |

Common-three sensitivity: P +0.0281, D -0.0714, R -0.0217, D_legacy +0.0638; first-orientation-only: P +0.0451, D -0.0618, R -0.0084

Per-judge source-relation AUROC (all SAME vs all DIFFERENT pairs, two-order mean):

- prompt plain: astra 0.546, fable 0.443, mimo 0.500
- prompt fair: astra 0.500, fable 0.645, mimo 0.500

| prompt | judge | focal>alternative | role | AUC | SAME hit | false SAME | balanced acc |
|---|---|---|---|---:|---:|---:|---:|
| plain | astra | astra>fable | focal | 0.504 | 0.545 | 0.545 | 0.500 |
| plain | astra | astra>mimo | focal | 0.545 | 0.545 | 0.500 | 0.523 |
| plain | astra | fable>astra | alternative | 0.554 | 0.591 | 0.545 | 0.523 |
| plain | astra | fable>mimo | uninvolved | 0.591 | 0.591 | 0.500 | 0.545 |
| plain | astra | mimo>astra | alternative | 0.545 | 0.545 | 0.500 | 0.523 |
| plain | astra | mimo>fable | uninvolved | 0.545 | 0.545 | 0.500 | 0.523 |
| plain | fable | astra>fable | alternative | 0.372 | 1.000 | 1.000 | 0.500 |
| plain | fable | astra>mimo | uninvolved | 0.667 | 1.000 | 0.944 | 0.528 |
| plain | fable | fable>astra | focal | 0.400 | 1.000 | 1.000 | 0.500 |
| plain | fable | fable>mimo | focal | 0.610 | 1.000 | 1.000 | 0.500 |
| plain | fable | mimo>astra | uninvolved | 0.439 | 0.773 | 0.944 | 0.414 |
| plain | fable | mimo>fable | alternative | 0.310 | 0.773 | 1.000 | 0.386 |
| plain | mimo | astra>fable | uninvolved | 0.500 | 0.500 | 0.500 | 0.500 |
| plain | mimo | astra>mimo | alternative | 0.500 | 0.500 | 0.500 | 0.500 |
| plain | mimo | fable>astra | uninvolved | 0.500 | 0.500 | 0.500 | 0.500 |
| plain | mimo | fable>mimo | alternative | 0.500 | 0.500 | 0.500 | 0.500 |
| plain | mimo | mimo>astra | focal | 0.500 | 0.500 | 0.500 | 0.500 |
| plain | mimo | mimo>fable | focal | 0.500 | 0.500 | 0.500 | 0.500 |
| fair | astra | astra>fable | focal | 0.500 | 0.500 | 0.500 | 0.500 |
| fair | astra | astra>mimo | focal | 0.500 | 0.500 | 0.500 | 0.500 |
| fair | astra | fable>astra | alternative | 0.500 | 0.500 | 0.500 | 0.500 |
| fair | astra | fable>mimo | uninvolved | 0.500 | 0.500 | 0.500 | 0.500 |
| fair | astra | mimo>astra | alternative | 0.500 | 0.500 | 0.500 | 0.500 |
| fair | astra | mimo>fable | uninvolved | 0.500 | 0.500 | 0.500 | 0.500 |
| fair | fable | astra>fable | alternative | 0.417 | 0.875 | 1.000 | 0.438 |
| fair | fable | astra>mimo | uninvolved | 0.700 | 0.875 | 0.700 | 0.588 |
| fair | fable | fable>astra | focal | 0.833 | 1.000 | 1.000 | 0.500 |
| fair | fable | fable>mimo | focal | 0.975 | 1.000 | 0.800 | 0.600 |
| fair | fable | mimo>astra | uninvolved | 0.580 | 0.800 | 0.700 | 0.550 |
| fair | fable | mimo>fable | alternative | 0.480 | 0.800 | 0.800 | 0.500 |
| fair | mimo | astra>fable | uninvolved | 0.500 | 0.500 | 0.500 | 0.500 |
| fair | mimo | astra>mimo | alternative | 0.500 | 0.500 | 0.500 | 0.500 |
| fair | mimo | fable>astra | uninvolved | 0.500 | 0.500 | 0.500 | 0.500 |
| fair | mimo | fable>mimo | alternative | 0.500 | 0.500 | 0.500 | 0.500 |
| fair | mimo | mimo>astra | focal | 0.500 | 0.500 | 0.500 | 0.500 |
| fair | mimo | mimo>fable | focal | 0.500 | 0.500 | 0.500 | 0.500 |

Order effects (designated vs swapped presentation):

- astra: mean |diff| 0.020, signed -0.0160, threshold disagreement 0.052, share exactly 0.5 0.990
- fable: mean |diff| 0.038, signed +0.0048, threshold disagreement 0.084, share exactly 0.5 0.108
- mimo: mean |diff| 0.000, signed +0.0000, threshold disagreement 0.000, share exactly 0.5 1.000

External pair baselines on the same pair IDs (fit on development only); overall SAME-vs-DIFFERENT AUROC:

- prompt plain: equality 0.515, heads_count_p_same 0.417, l2_pair 0.599, neg_heads_diff 0.401, observer_p_same 0.779, positional_agreement 0.694
- prompt fair: equality 0.500, heads_count_p_same 0.620, l2_pair 0.660, neg_heads_diff 0.573, observer_p_same 0.836, positional_agreement 0.691

Pair controls on the audit block (absolute difference):

- astra: identical repeat 0.000, P(DIFFERENT) polarity 0.000 (signed +0.0000)
- fable: identical repeat 0.011, P(DIFFERENT) polarity 0.049 (signed +0.0489)
- mimo: identical repeat 0.000, P(DIFFERENT) polarity 0.000 (signed +0.0000)

Time gaps between paired parents: {"SAME": {"n": 48, "mean_gap_s": 60.47647679166667, "median_gap_s": 38.099326500000004, "share_same_time_block": 0.20833333333333334}, "DIFFERENT": {"n": 48, "mean_gap_s": 72.05334175, "median_gap_s": 64.09870099999999, "share_same_time_block": 0.0625}}

## 3. Validity of every task

| task / judge | valid / n |
|---|---:|
| completion|astra | 256/256 (1.0) |
| completion|fable | 255/256 (0.996) |
| completion|mimo | 256/256 (1.0) |
| completion_polarity|astra | 24/24 (1.0) |
| completion_polarity|fable | 24/24 (1.0) |
| completion_polarity|mimo | 24/24 (1.0) |
| completion_prior|astra | 8/8 (1.0) |
| completion_prior|fable | 8/8 (1.0) |
| completion_prior|mimo | 8/8 (1.0) |
| completion_repeat|astra | 24/24 (1.0) |
| completion_repeat|fable | 24/24 (1.0) |
| completion_repeat|mimo | 24/24 (1.0) |
| fixture_completion|astra | 12/12 (1.0) |
| fixture_completion|fable | 12/12 (1.0) |
| fixture_completion|mimo | 12/12 (1.0) |
| fixture_named|astra | 6/6 (1.0) |
| fixture_named|fable | 6/6 (1.0) |
| fixture_named|mimo | 4/6 (0.667) |
| fixture_pair|astra | 12/12 (1.0) |
| fixture_pair|fable | 2/12 (0.167) |
| fixture_pair|mimo | 9/12 (0.75) |
| named|astra | 36/36 (1.0) |
| named|fable | 36/36 (1.0) |
| named|mimo | 36/36 (1.0) |
| named_prior|astra | 12/12 (1.0) |
| named_prior|fable | 12/12 (1.0) |
| named_prior|mimo | 12/12 (1.0) |
| pair_polarity|astra | 12/12 (1.0) |
| pair_polarity|fable | 11/12 (0.917) |
| pair_polarity|mimo | 12/12 (1.0) |
| pair_prior|astra | 4/4 (1.0) |
| pair_prior|fable | 4/4 (1.0) |
| pair_prior|mimo | 4/4 (1.0) |
| pair_repeat|astra | 12/12 (1.0) |
| pair_repeat|fable | 9/12 (0.75) |
| pair_repeat|mimo | 12/12 (1.0) |
| pairs|astra | 192/192 (1.0) |
| pairs|fable | 175/192 (0.911) |
| pairs|mimo | 192/192 (1.0) |
| rehearsal_completion|astra | 24/24 (1.0) |
| rehearsal_completion|fable | 24/24 (1.0) |
| rehearsal_completion|mimo | 24/24 (1.0) |
| rehearsal_pairs|astra | 12/12 (1.0) |
| rehearsal_pairs|fable | 12/12 (1.0) |
| rehearsal_pairs|mimo | 12/12 (1.0) |

## 4. Independent rescore

`rescore.py` recomputed the headline numbers from `scores.csv` with separate code: {"H4_rescore": -0.0004106899978041321, "H4_main": -0.0004106899978041321, "H4_agree": true, "R_rescore": -0.018879350867987216, "R_main": -0.01887935086798722, "R_agree": true}

## 5. Interpretation boundaries

- 'Own model' means another independently queried instance of the same documented model configuration, not memory of the test string.
- Three model configurations are three subjects. Thousands of calls are not thousands of independent models.
- An unresolved direction is not evidence of no effect; a bounded-small interval is bounded only for this configuration and assay.
- Similar training, brand associations, shared output preferences and skill-by-difficulty interactions remain possible explanations.
- The pair task borrows a naming control from Loula et al.; it is not a Loula replication.

