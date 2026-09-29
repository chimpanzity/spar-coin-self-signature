# SPAR Dynamic Behavioral Self-Signature Pilot — Final Report

Run root: `data/spar_dynamic/spar-dynamic-run-20260929T081814Z`
Experiment tag: `spar_dynamic_self_signature_v1`
Judgment response mode: `json_schema`
Total spend: **$1.4316** / $25.00 cap

## Spend by phase
- batch: 56 calls, $0.1904
- judgment: 208 calls, $1.2412

## Source integrity
| architecture | model | n valid | mean p(H) | mean switch | mean runs_Z | mean longest_run |
|---|---|---|---|---|---|---|
| batch | astra | 10 | 0.496 | 0.629 | +1.66 | 3.10 |
| batch | fable | 10 | 0.504 | 0.637 | +1.77 | 3.00 |
| batch | qwen | 10 | 0.488 | 0.680 | +2.39 | 2.90 |
| online | astra | 10 | 0.460 | 0.690 | +2.59 | 3.60 |
| online | fable | 10 | 0.598 | 0.745 | +3.80 | 4.00 |
| online | qwen | 10 | 0.936 | 0.129 | +0.46 | 27.20 |

## Source-model identifiability (leave-one-out nearest centroid)

- batch: **0.700** (n=30)
  - astra->fable: 2
  - astra->astra: 6
  - astra->qwen: 2
  - fable->fable: 9
  - fable->astra: 1
  - qwen->qwen: 6
  - qwen->fable: 3
  - qwen->astra: 1
- online: **0.933** (n=30)
  - astra->astra: 9
  - astra->fable: 1
  - fable->astra: 1
  - fable->fable: 9
  - qwen->qwen: 10

Architecture contrast: online - batch = **+0.233**

## Judgment performance (per judge x architecture)

| judge | arch | n | total acc | A | B | C | D | own | other | self_adv | A-C | B-D | SAME rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| astra | online | 24 | 0.917 | 0.833 | 1.000 | 0.833 | 1.000 | 0.917 | 0.917 | +0.000 | +0.000 | +0.000 | 0.417 |
| astra | batch | 24 | 0.583 | 1.000 | 0.167 | 1.000 | 0.167 | 0.583 | 0.583 | +0.000 | +0.000 | +0.000 | 0.917 |
| fable | online | 24 | 0.833 | 0.333 | 1.000 | 1.000 | 1.000 | 0.667 | 1.000 | -0.333 | -0.667 | +0.000 | 0.333 |
| fable | batch | 24 | 0.500 | 1.000 | 0.000 | 0.833 | 0.167 | 0.500 | 0.500 | +0.000 | +0.167 | -0.167 | 0.917 |
| qwen | batch | 24 | 0.333 | 0.833 | 0.000 | 0.500 | 0.000 | 0.417 | 0.250 | +0.167 | +0.333 | +0.000 | 0.583 |
| qwen | online | 24 | 0.625 | 0.667 | 1.000 | 0.833 | 0.000 | 0.833 | 0.417 | +0.417 | -0.167 | +1.000 | 0.375 |

## Central result: dynamic self-signature gain per judge

| judge | self_advantage_batch | self_advantage_online | dynamic_self_signature_gain |
|---|---|---|---|
| astra | +0.000 | +0.000 | +0.000 |
| fable | +0.000 | -0.333 | -0.333 |
| qwen | +0.167 | +0.417 | +0.250 |

### Pooled across judges (weighted by n)

- batch: pooled self_advantage = **+0.056** (own=0.500, other=0.444)
- online: pooled self_advantage = **+0.028** (own=0.806, other=0.778)

## Feature-distance baseline (per architecture)

- online: median-threshold accuracy = 0.944 (n=72, median distance = 2.468)
- batch: median-threshold accuracy = 0.556 (n=72, median distance = 3.021)

### Per-cell feature distances
| architecture | cell | n | mean distance | sd distance |
|---|---|---|---|---|
| online | A | 18 | 1.354 | 0.807 |
| online | B | 18 | 4.640 | 1.410 |
| online | C | 18 | 0.973 | 0.587 |
| online | D | 18 | 4.433 | 1.558 |
| batch | A | 18 | 3.275 | 1.827 |
| batch | B | 18 | 3.622 | 1.499 |
| batch | C | 18 | 2.794 | 2.281 |
| batch | D | 18 | 3.630 | 2.026 |

## Interpretation notes

- One session per (judge x architecture x cell) block; 6 trials per cell means accuracy granularity is 1/6.
- `self_advantage` (own_accuracy - other_accuracy) can arise from either genuine own-model discrimination OR from own-involving trials being objectively easier at the visible-feature level. Compare against the feature-distance baseline and per-cell distances above.
- The central hypothesis is `self_advantage_online > self_advantage_batch` (positive dynamic gain).
- Descriptive pilot only; do not infer self-awareness or introspection from this data.
