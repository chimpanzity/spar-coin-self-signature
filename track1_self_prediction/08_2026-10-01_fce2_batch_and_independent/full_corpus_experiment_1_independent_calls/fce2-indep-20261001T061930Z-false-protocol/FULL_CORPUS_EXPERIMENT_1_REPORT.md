# Full Corpus Experiment 1 — Producer-vs-Observer Identification

Specification: `FCE1_v1.0`
Experiment status: **COMPLETE**

## 1. Integrity and actual counts

- planned trials: 480
- ok trials: 480
- abandoned: 0
- source integrity hard errors: 0
- duplicates present: True

## 2. Primary holdout results (per-target contrasts)

| target | n_items | SELF | NAMED | OBS | S | O | F |
|---|---:|---:|---:|---:|---:|---:|---:|
| astra | 20 | 0.4 | 0.35 | 0.625 | -0.225 | -0.275 | 0.05 |
| fable | 20 | 0.05 | 0.1 | 0.3 | -0.25 | -0.2 | -0.05 |
| mimo | 20 | 0.55 | 0.5 | 0.525 | 0.025 | -0.025 | 0.05 |

**Primary summary (equal-weight mean S across targets, holdout): -0.150**

## 3. S / O / F decomposition — holdout bootstrap 95% intervals

| target | stat | mean | 95% CI (triplet bootstrap) |
|---|---|---:|---|
| astra | S | -0.2264 | [-0.4, -0.075] |
| astra | O | -0.2769 | [-0.525, -0.025] |
| astra | F | 0.0505 | [-0.15, 0.25] |
| fable | S | -0.2498 | [-0.35, -0.15] |
| fable | O | -0.2008 | [-0.325, -0.075] |
| fable | F | -0.049 | [-0.15, 0.0] |
| mimo | S | 0.0232 | [-0.1, 0.15] |
| mimo | O | -0.0258 | [-0.15, 0.1] |
| mimo | F | 0.049 | [0.0, 0.15] |

## 4. NAMED judge x target accuracy matrix

### Holdout
| judge | astra | fable | mimo |
|---|---:|---:|---:|
| astra | 0.35 | 0.1 | 0.65 |
| fable | 0.75 | 0.1 | 0.4 |
| mimo | 0.5 | 0.5 | 0.5 |

## 5. Observer-role accuracy (NAMED, judge != target)

| split | role | n | accuracy |
|---|---|---:|---:|
| development | distractor_producer | 60 | 0.5333 |
| development | uninvolved_observer | 60 | 0.4667 |
| holdout | distractor_producer | 60 | 0.5 |
| holdout | uninvolved_observer | 60 | 0.4667 |

## 6. Statistical baselines (centroid classifier)

| split | baseline | n_scored | n_ties | accuracy |
|---|---|---:|---:|---:|
| development | marginal | 60 | 0 | 1.0 |
| development | full | 60 | 0 | 1.0 |
| holdout | marginal | 60 | 0 | 1.0 |
| holdout | full | 60 | 0 | 1.0 |

## 7. Compliance (first-attempt and eventual)

| judge | wording | n | first-attempt valid | eventually valid | abandoned |
|---|---|---:|---:|---:|---:|
| astra | NAMED | 120 | 1.0 | 1.0 | 0 |
| astra | SELF | 40 | 1.0 | 1.0 | 0 |
| fable | NAMED | 120 | 1.0 | 1.0 | 0 |
| fable | SELF | 40 | 1.0 | 1.0 | 0 |
| mimo | NAMED | 120 | 1.0 | 1.0 | 0 |
| mimo | SELF | 40 | 1.0 | 1.0 | 0 |

## 8. Limitations and interpretive guardrails

- Fresh instances do not have episodic memory of the original calls; SELF here means model-identity.
- Only 10 holdout triplets; triplet-bootstrap intervals are exploratory/small-sample.
- Source trajectories were served by heterogeneous providers (recorded in source_provider_audit.csv).
- Exceeding the two centroid baselines does not establish that no classifier could do better.
- A single judge excelling on all targets does not establish self-specific access.

See `producer_observer_contrasts.csv`, `bootstrap_intervals.csv`, `baseline_summary.csv`, `compliance_summary.csv`, `target_complementarity.csv`, and `named_judge_target_matrix.csv` for the raw numbers underlying each table above.
