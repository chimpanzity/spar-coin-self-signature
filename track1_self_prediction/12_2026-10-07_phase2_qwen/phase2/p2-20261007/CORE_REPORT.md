# SPAR Phase 2 pilot: core report

Run `p2-20261007`, protocol SPAR_Phase2_v7.1, generated 2026-10-08T04:28:28.591048Z.
Report scope: CORE plus retained arms (named: complete; historical: complete).

Exploratory pilot. Intervals are marginal two-sided 95% percentile bootstrap intervals, not multiplicity-adjusted. Reporting margins: delta_Brier = 0.02, delta_AUC = 0.05.

## 1. H4 completion readout (key, two-sided)

Positive values mean disclosure of the true source helps the panel's own-model forecasts relatively more than other-model forecasts. Neither sign is evidence of introspection.

| quantity | estimate | 95% CI | direction | bounded within margin |
|---|---:|---|---|---|
| H4 | -0.0026 | [-0.0040, -0.0013] | resolved_negative | True |
| gain_own | -0.0002 | [-0.0006, +0.0002] | unresolved | True |
| gain_other | +0.0024 | [+0.0012, +0.0037] | resolved_positive | True |
| C_known | -0.0141 | [-0.0219, -0.0072] | resolved_negative | False |
| C_withheld | -0.0115 | [-0.0182, -0.0055] | resolved_negative | True |

Bootstrap: 5000 parent resamples within source x prompt; undefined replicates 0.000. Panel estimable: True.

### Per prompt and per judge pair (pairwise-common sets)

| crossover | H4 | gain_own | gain_other | C_known | C_withheld |
|---|---:|---:|---:|---:|---:|
| astra-fable|plain | -0.0004 | -0.0006 | -0.0002 | +0.0000 | +0.0004 |
| astra-qwen|plain | -0.0028 | +0.0001 | +0.0029 | -0.0442 | -0.0414 |
| fable-qwen|plain | -0.0094 | -0.0005 | +0.0089 | -0.0387 | -0.0293 |
| astra-fable|fair | +0.0001 | -0.0001 | -0.0002 | +0.0004 | +0.0003 |
| astra-qwen|fair | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| fable-qwen|fair | -0.0031 | -0.0001 | +0.0029 | -0.0023 | +0.0008 |
| **prompt plain (3-pair mean)** | -0.0042 [-0.0070, -0.0016] | -0.0003 | +0.0039 | -0.0276 | -0.0234 |
| **prompt fair (3-pair mean)** | -0.0010 [-0.0016, -0.0003] | -0.0001 | +0.0009 | -0.0006 | +0.0004 |

Common-three-judge sensitivity panel: H4 -0.0026 [-0.0040, -0.0013], gain_own -0.0002 [-0.0006, +0.0002], gain_other +0.0024 [+0.0012, +0.0037], C_known -0.0141 [-0.0217, -0.0064], C_withheld -0.0115 [-0.0179, -0.0050]
Worst-case complete-data bounds on panel H4 (unobserved losses set to 0/1): [-0.0078, -0.0009].

### Absolute forecast skill (mean Brier; fair coin = 0.25)

| judge | condition | astra/plain | astra/fair | fable/plain | fable/fair | qwen/plain | qwen/fair |
|---|---|---:|---:|---:|---:|---:|---:|
| astra | known | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=24) | 0.158 (n=24) | 0.250 (n=1) |
| astra | withheld | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=24) | 0.166 (n=24) | 0.250 (n=1) |
| fable | known | 0.250 (n=24) | 0.249 (n=24) | 0.250 (n=23) | 0.249 (n=24) | 0.169 (n=24) | 0.244 (n=1) |
| fable | withheld | 0.250 (n=24) | 0.249 (n=24) | 0.249 (n=24) | 0.248 (n=24) | 0.186 (n=24) | 0.250 (n=1) |
| qwen | known | 0.253 (n=24) | 0.250 (n=24) | 0.253 (n=24) | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=1) |
| qwen | withheld | 0.251 (n=24) | 0.250 (n=24) | 0.255 (n=24) | 0.250 (n=24) | 0.250 (n=24) | 0.250 (n=1) |

How often judges return 0.5 at every position (amendment A3, descriptive):

| judge | source | condition | n | share all-0.5 | mean abs deviation from 0.5 |
|---|---|---|---:|---:|---:|
| astra | astra | known | 48 | 1.000 | 0.000 |
| astra | astra | withheld | 48 | 1.000 | 0.000 |
| astra | fable | known | 48 | 1.000 | 0.000 |
| astra | fable | withheld | 48 | 1.000 | 0.000 |
| astra | qwen | known | 25 | 0.640 | 0.155 |
| astra | qwen | withheld | 25 | 0.640 | 0.124 |
| fable | astra | known | 48 | 0.833 | 0.001 |
| fable | astra | withheld | 48 | 0.417 | 0.004 |
| fable | fable | known | 47 | 0.660 | 0.004 |
| fable | fable | withheld | 48 | 0.375 | 0.006 |
| fable | qwen | known | 25 | 0.280 | 0.118 |
| fable | qwen | withheld | 25 | 0.240 | 0.084 |
| qwen | astra | known | 48 | 0.854 | 0.007 |
| qwen | astra | withheld | 48 | 0.938 | 0.003 |
| qwen | fable | known | 48 | 0.833 | 0.008 |
| qwen | fable | withheld | 48 | 0.771 | 0.011 |
| qwen | qwen | known | 25 | 1.000 | 0.000 |
| qwen | qwen | withheld | 25 | 0.880 | 0.005 |

External baselines on the same test parents (fit on development only):

| source/prompt | n | fair | pooled position | source position | observer known | observer withheld | L2 known | L2 withheld |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| astra|plain | 24 | 0.250 | 0.255 | 0.245 | 0.177 | 0.191 | 0.183 | 0.212 |
| fable|plain | 24 | 0.250 | 0.208 | 0.152 | 0.064 | 0.072 | 0.057 | 0.076 |
| qwen|plain | 24 | 0.250 | 0.199 | 0.158 | 0.129 | 0.146 | 0.141 | 0.145 |
| astra|fair | 24 | 0.250 | 0.234 | 0.219 | 0.181 | 0.209 | 0.177 | 0.217 |
| fable|fair | 24 | 0.250 | 0.202 | 0.193 | 0.191 | 0.169 | 0.206 | 0.175 |
| qwen|fair | 1 | 0.250 | 0.268 | 0.344 | 0.385 | 0.343 | 0.379 | 0.376 |

Per-model identity gains (withheld minus known loss, available case; positive = disclosure helped):

| judge | astra/plain | astra/fair | fable/plain | fable/fair | qwen/plain | qwen/fair |
|---|---:|---:|---:|---:|---:|---:|
| astra | +0.0000 *own* | +0.0000 *own* | +0.0000 | +0.0000 | +0.0078 | +0.0000 |
| fable | -0.0004 | -0.0004 | -0.0011 *own* | -0.0003 *own* | +0.0162 | +0.0059 |
| qwen | -0.0021 | +0.0000 | +0.0016 | +0.0000 | +0.0002 *own* | +0.0000 *own* |

Suffix-permutation coupling diagnostic (intact vs within-cell permuted suffixes; share of permutations with loss <= intact):

| judge | condition | intact | permuted mean | share perm <= intact |
|---|---|---:|---:|---:|
| astra | known | 0.232 | 0.239 | 0.018 |
| astra | withheld | 0.233 | 0.240 | 0.018 |
| fable | known | 0.234 | 0.239 | 0.005 |
| fable | withheld | 0.236 | 0.240 | 0.012 |
| qwen | known | 0.251 | 0.251 | 0.996 |
| qwen | withheld | 0.251 | 0.251 | 0.514 |

Completion controls on the audit parents (mean absolute difference per position):

| judge | identical repeat | P(T) polarity (canonicalized) | polarity signed |
|---|---:|---:|---:|
| astra | 0.005 | 0.001 | +0.0006 |
| fable | 0.016 | 0.015 | +0.0059 |
| qwen | 0.000 | 0.011 | -0.0114 |

## 2. Anonymous SAME/DIFFERENT recognition (primary recognition endpoint)

R = (P + D)/2, where P compares the focal-source judge with the uninvolved judge and D compares the alternative-source judge with the uninvolved judge, using AUROC of the two-order mean P(SAME). R measures own-model involvement in source-relation discrimination, not self-authorship.

| quantity | estimate | 95% CI (block bootstrap) | direction | bounded within margin |
|---|---:|---|---|---|
| R | NA | [NA] | none | False |
| P | NA | [NA] | none | False |
| D | NA | [NA] | none | False |

Support: {'n_pairs': 72, 'n_blocks': 12, 'per_prompt_pairs': {'plain': 72}}. Undefined bootstrap replicates: 1.000. Panel estimable: False.

- Per-prompt (secondary; CI added by amendment A3) prompt plain: R +0.0759 [+0.0110, +0.1298], P +0.0849 [+0.0072, +0.1561], D +0.0670 [+0.0040, +0.1174]
- Per-prompt (secondary; CI added by amendment A3) prompt fair: not estimable (no pair blocks)

| crossover | P | D | R | items |
|---|---:|---:|---:|---:|
| astra-fable|plain | -0.0114 | -0.0810 | -0.0462 | 65 |
| astra-qwen|plain | -0.0330 | +0.2326 | +0.0998 | 72 |
| fable-qwen|plain | +0.2989 | +0.0492 | +0.1741 | 65 |
| astra-fable|fair | NA | NA | NA | 0 |
| astra-qwen|fair | NA | NA | NA | 0 |
| fable-qwen|fair | NA | NA | NA | 0 |

Common-three sensitivity: not estimable; first-orientation-only: not estimable

Per-judge source-relation AUROC (all SAME vs all DIFFERENT pairs, two-order mean):

- prompt plain: astra 0.597, fable 0.785, qwen 0.572
- prompt fair: astra NA, fable NA, qwen NA

| prompt | judge | focal>alternative | role | AUC | SAME hit | false SAME | balanced acc |
|---|---|---|---|---:|---:|---:|---:|
| plain | astra | astra>fable | focal | 0.583 | 0.583 | 0.500 | 0.542 |
| plain | astra | astra>qwen | focal | 0.583 | 0.583 | 0.500 | 0.542 |
| plain | astra | fable>astra | alternative | 0.625 | 0.625 | 0.500 | 0.562 |
| plain | astra | fable>qwen | uninvolved | 0.625 | 0.625 | 0.500 | 0.562 |
| plain | astra | qwen>astra | alternative | 0.583 | 0.583 | 0.500 | 0.542 |
| plain | astra | qwen>fable | uninvolved | 0.583 | 0.583 | 0.500 | 0.542 |
| plain | fable | astra>fable | alternative | 0.545 | 1.000 | 1.000 | 0.500 |
| plain | fable | astra>qwen | uninvolved | 0.943 | 1.000 | 0.417 | 0.792 |
| plain | fable | fable>astra | focal | 0.869 | 1.000 | 1.000 | 0.500 |
| plain | fable | fable>qwen | focal | 0.955 | 1.000 | 0.591 | 0.705 |
| plain | fable | qwen>astra | uninvolved | 0.844 | 0.667 | 0.417 | 0.625 |
| plain | fable | qwen>fable | alternative | 0.682 | 0.667 | 0.591 | 0.538 |
| plain | qwen | astra>fable | uninvolved | 0.500 | 1.000 | 1.000 | 0.500 |
| plain | qwen | astra>qwen | alternative | 0.997 | 1.000 | 0.333 | 0.833 |
| plain | qwen | fable>astra | uninvolved | 0.111 | 0.875 | 1.000 | 0.438 |
| plain | qwen | fable>qwen | alternative | 0.576 | 0.875 | 0.667 | 0.604 |
| plain | qwen | qwen>astra | focal | 0.663 | 0.458 | 0.333 | 0.562 |
| plain | qwen | qwen>fable | focal | 0.434 | 0.458 | 0.667 | 0.396 |

Order effects (designated vs swapped presentation):

- astra: mean |diff| 0.031, signed +0.0089, threshold disagreement 0.083, share exactly 0.5 0.931
- fable: mean |diff| 0.035, signed +0.0011, threshold disagreement 0.062, share exactly 0.5 0.015
- qwen: mean |diff| 0.035, signed +0.0024, threshold disagreement 0.056, share exactly 0.5 0.083

External pair baselines on the same pair IDs (fit on development only); overall SAME-vs-DIFFERENT AUROC:

- prompt plain: equality 0.583, heads_count_p_same 0.694, l2_pair 0.875, neg_heads_diff 0.662, observer_p_same 0.951, positional_agreement 0.800

Pair controls on the audit block (absolute difference):

- astra: identical repeat 0.017, P(DIFFERENT) polarity 0.075 (signed +0.0750)
- fable: identical repeat 0.025, P(DIFFERENT) polarity 0.043 (signed +0.0267)
- qwen: identical repeat 0.002, P(DIFFERENT) polarity 0.139 (signed +0.1300)

Time gaps between paired parents: {"SAME": {"n": 36, "mean_gap_s": 38.07366091666667, "median_gap_s": 31.958074, "share_same_time_block": 0.2222222222222222}, "DIFFERENT": {"n": 36, "mean_gap_s": 41.62061275, "median_gap_s": 33.3782515, "share_same_time_block": 0.1111111111111111}}

## 3. Validity of every task

| task / judge | valid / n |
|---|---:|
| completion|astra | 242/242 (1.0) |
| completion|fable | 241/242 (0.996) |
| completion|qwen | 242/242 (1.0) |
| completion_polarity|astra | 22/22 (1.0) |
| completion_polarity|fable | 22/22 (1.0) |
| completion_polarity|qwen | 22/22 (1.0) |
| completion_prior|astra | 8/8 (1.0) |
| completion_prior|fable | 8/8 (1.0) |
| completion_prior|qwen | 8/8 (1.0) |
| completion_repeat|astra | 22/22 (1.0) |
| completion_repeat|fable | 22/22 (1.0) |
| completion_repeat|qwen | 22/22 (1.0) |
| fixture_completion|astra | 12/12 (1.0) |
| fixture_completion|fable | 12/12 (1.0) |
| fixture_completion|qwen | 12/12 (1.0) |
| fixture_named|astra | 6/6 (1.0) |
| fixture_named|fable | 6/6 (1.0) |
| fixture_named|qwen | 5/6 (0.833) |
| fixture_pair|astra | 12/12 (1.0) |
| fixture_pair|fable | 2/12 (0.167) |
| fixture_pair|qwen | 12/12 (1.0) |
| named|astra | 18/18 (1.0) |
| named|fable | 18/18 (1.0) |
| named|qwen | 18/18 (1.0) |
| named_prior|astra | 12/12 (1.0) |
| named_prior|fable | 12/12 (1.0) |
| named_prior|qwen | 12/12 (1.0) |
| pair_polarity|astra | 6/6 (1.0) |
| pair_polarity|fable | 6/6 (1.0) |
| pair_polarity|qwen | 6/6 (1.0) |
| pair_prior|astra | 4/4 (1.0) |
| pair_prior|fable | 4/4 (1.0) |
| pair_prior|qwen | 4/4 (1.0) |
| pair_repeat|astra | 6/6 (1.0) |
| pair_repeat|fable | 6/6 (1.0) |
| pair_repeat|qwen | 6/6 (1.0) |
| pairs|astra | 144/144 (1.0) |
| pairs|fable | 136/144 (0.944) |
| pairs|qwen | 144/144 (1.0) |
| rehearsal_completion|astra | 24/24 (1.0) |
| rehearsal_completion|fable | 24/24 (1.0) |
| rehearsal_completion|qwen | 24/24 (1.0) |
| rehearsal_pairs|astra | 12/12 (1.0) |
| rehearsal_pairs|fable | 11/12 (0.917) |
| rehearsal_pairs|qwen | 12/12 (1.0) |

## 4. Independent rescore

`rescore.py` recomputed the headline numbers from `scores.csv` with separate code: {"H4_rescore": -0.002589100241545896, "H4_main": -0.0025891002415458957, "H4_agree": true, "R_rescore": null, "R_main": null, "R_agree": true}

## 5. Interpretation boundaries

- 'Own model' means another independently queried instance of the same documented model configuration, not memory of the test string.
- Three model configurations are three subjects. Thousands of calls are not thousands of independent models.
- An unresolved direction is not evidence of no effect; a bounded-small interval is bounded only for this configuration and assay.
- Similar training, brand associations, shared output preferences and skill-by-difficulty interactions remain possible explanations.
- The pair task borrows a naming control from Loula et al.; it is not a Loula replication.

