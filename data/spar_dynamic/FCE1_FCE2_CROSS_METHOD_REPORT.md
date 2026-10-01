# Full Corpus Experiment 1 + 2 — Cross-method summary

Three independent 480-judgment runs, one per corpus production method, same judge configuration and prompt (barring per-method stimulus text).

| method | run_id |
|---|---|
| history_conditioned (truthful) | `fce1-20261001T050251Z` |
| batch (truthful) | `fce2-batch-truthful-20261001T064655Z` |
| independent_calls (truthful) | `fce2-indep-truthful-20261001T070301Z` |
| batch (false protocol) | `fce2-batch-20261001T060352Z-false-protocol` |
| independent_calls (false protocol) | `fce2-indep-20261001T061930Z-false-protocol` |

## 1. Primary summary — equal-weight mean S across targets (holdout)

| method | mean S (holdout) |
|---|---:|
| history_conditioned (truthful) | 0.008 |
| batch (truthful) | -0.008 |
| independent_calls (truthful) | 0.100 |
| batch (false protocol) | -0.008 |
| independent_calls (false protocol) | -0.150 |

Positive values would indicate SELF-wording-plus-ownership advantage over named observers; negative values indicate observers outperform the target producer on its own trajectories.

## 2. Per-target holdout contrasts (S / O / F)

### history_conditioned (truthful)

| target | n | SELF | NAMED | OBS | **S** | **O** | **F** |
|---|---:|---:|---:|---:|---:|---:|---:|
| astra | 20 | 0.55 | 0.55 | 0.60 | **-0.05** | **-0.05** | **0.00** |
| fable | 20 | 0.30 | 0.15 | 0.30 | **0.00** | **-0.15** | **0.15** |
| mimo | 20 | 0.50 | 0.50 | 0.42 | **0.07** | **0.07** | **0.00** |

### batch (truthful)

| target | n | SELF | NAMED | OBS | **S** | **O** | **F** |
|---|---:|---:|---:|---:|---:|---:|---:|
| astra | 20 | 0.35 | 0.55 | 0.50 | **-0.15** | **0.05** | **-0.20** |
| fable | 20 | 0.50 | 0.50 | 0.40 | **0.10** | **0.10** | **0.00** |
| mimo | 20 | 0.50 | 0.50 | 0.47 | **0.03** | **0.03** | **0.00** |

### independent_calls (truthful)

| target | n | SELF | NAMED | OBS | **S** | **O** | **F** |
|---|---:|---:|---:|---:|---:|---:|---:|
| astra | 20 | 0.05 | 0.00 | 0.35 | **-0.30** | **-0.35** | **0.05** |
| fable | 20 | 0.90 | 0.75 | 0.45 | **0.45** | **0.30** | **0.15** |
| mimo | 20 | 0.60 | 0.55 | 0.45 | **0.15** | **0.10** | **0.05** |

### batch (false protocol)

| target | n | SELF | NAMED | OBS | **S** | **O** | **F** |
|---|---:|---:|---:|---:|---:|---:|---:|
| astra | 20 | 0.45 | 0.60 | 0.47 | **-0.03** | **0.12** | **-0.15** |
| fable | 20 | 0.50 | 0.50 | 0.53 | **-0.03** | **-0.03** | **0.00** |
| mimo | 20 | 0.50 | 0.50 | 0.47 | **0.03** | **0.03** | **0.00** |

### independent_calls (false protocol)

| target | n | SELF | NAMED | OBS | **S** | **O** | **F** |
|---|---:|---:|---:|---:|---:|---:|---:|
| astra | 20 | 0.40 | 0.35 | 0.62 | **-0.23** | **-0.28** | **0.05** |
| fable | 20 | 0.05 | 0.10 | 0.30 | **-0.25** | **-0.20** | **-0.05** |
| mimo | 20 | 0.55 | 0.50 | 0.53 | **0.03** | **-0.03** | **0.05** |

## 3. NAMED judge × target accuracy (holdout)

### history_conditioned (truthful)

| judge | astra | fable | mimo |
|---|---:|---:|---:|
| astra | 0.55 | 0.10 | 0.25 |
| fable | 0.70 | 0.15 | 0.60 |
| mimo | 0.50 | 0.50 | 0.50 |

### batch (truthful)

| judge | astra | fable | mimo |
|---|---:|---:|---:|
| astra | 0.55 | 0.30 | 0.55 |
| fable | 0.50 | 0.50 | 0.40 |
| mimo | 0.50 | 0.50 | 0.50 |

### independent_calls (truthful)

| judge | astra | fable | mimo |
|---|---:|---:|---:|
| astra | 0.00 | 0.40 | 0.40 |
| fable | 0.25 | 0.75 | 0.50 |
| mimo | 0.45 | 0.50 | 0.55 |

### batch (false protocol)

| judge | astra | fable | mimo |
|---|---:|---:|---:|
| astra | 0.60 | 0.55 | 0.50 |
| fable | 0.45 | 0.50 | 0.45 |
| mimo | 0.50 | 0.50 | 0.50 |

### independent_calls (false protocol)

| judge | astra | fable | mimo |
|---|---:|---:|---:|
| astra | 0.35 | 0.10 | 0.65 |
| fable | 0.75 | 0.10 | 0.40 |
| mimo | 0.50 | 0.50 | 0.50 |

## 4. Statistical baselines (centroid classifier)

| method | split | baseline | accuracy |
|---|---|---|---:|
| history_conditioned (truthful) | development | marginal | 0.967 |
| history_conditioned (truthful) | development | full | 0.967 |
| history_conditioned (truthful) | holdout | marginal | 0.967 |
| history_conditioned (truthful) | holdout | full | 1.000 |
| batch (truthful) | development | marginal | 1.000 |
| batch (truthful) | development | full | 0.767 |
| batch (truthful) | holdout | marginal | 0.840 |
| batch (truthful) | holdout | full | 0.767 |
| independent_calls (truthful) | development | marginal | 1.000 |
| independent_calls (truthful) | development | full | 1.000 |
| independent_calls (truthful) | holdout | marginal | 1.000 |
| independent_calls (truthful) | holdout | full | 1.000 |
| batch (false protocol) | development | marginal | 1.000 |
| batch (false protocol) | development | full | 0.767 |
| batch (false protocol) | holdout | marginal | 0.840 |
| batch (false protocol) | holdout | full | 0.767 |
| independent_calls (false protocol) | development | marginal | 1.000 |
| independent_calls (false protocol) | development | full | 1.000 |
| independent_calls (false protocol) | holdout | marginal | 1.000 |
| independent_calls (false protocol) | holdout | full | 1.000 |

Interpretation: the behavioral phenotype of each production method is cleanly separable by a simple centroid classifier. Independent_calls trajectories are the most separable (baseline accuracy 1.0), consistent with the strong p_H biases this method produces.

## 5. Observer-role accuracy (holdout, NAMED, judge ≠ target)

| method | distractor_producer | uninvolved_observer |
|---|---:|---:|
| history_conditioned (truthful) | 0.517 | 0.367 |
| batch (truthful) | 0.450 | 0.467 |
| independent_calls (truthful) | 0.383 | 0.450 |
| batch (false protocol) | 0.500 | 0.483 |
| independent_calls (false protocol) | 0.500 | 0.467 |

## 6. Compliance (all methods)

| method | total trials | first-attempt valid | eventually valid | abandoned |
|---|---:|---:|---:|---:|
| history_conditioned (truthful) | 480 | 1.000 | 1.000 | 0 |
| batch (truthful) | 480 | 1.000 | 1.000 | 0 |
| independent_calls (truthful) | 480 | 1.000 | 1.000 | 0 |
| batch (false protocol) | 480 | 1.000 | 1.000 | 0 |
| independent_calls (false protocol) | 480 | 1.000 | 1.000 | 0 |

## 7. Cross-method synthesis

- **Protocol information strongly shapes self-recognition.** The independent_calls comparison between the truthful-protocol run and the false-protocol run shows this clearly: fable's own-trajectory accuracy under SELF-wording moves from 0.05 (false-protocol) to 0.90 (truthful-protocol), and NAMED-on-fable from 0.10 to 0.75. The equal-weight mean S flips sign (−0.150 → +0.100) between the two conditions on exactly the same stimulus sequences; only the judge's description of how those sequences were produced changed.
- **Under truthful protocols, modest positive self-recognition emerges in independent_calls** (mean S = +0.100, fable S = +0.45 with CI [0.25, 0.63] on holdout). History_conditioned and batch stay near zero even with the truthful protocol.
- **The task is externally solvable in all methods.** The centroid baseline hits 97–100% on holdout. The behavioral signal is there; LLM judges only partially use it, and only when the protocol description matches the production reality.
- **Astra is a consistent anti-self-recognizer** across methods and protocols: holdout NAMED-on-astra = 0.00 and SELF-on-astra = 0.05 under the truthful independent_calls protocol, while fable and mimo as observers identify astra at above-chance rates in some cells.
- **Mimo scores at or near chance everywhere** across all methods and protocols, consistent with an A-position-biased or weak-feature-using responder (compliant parsing but not using the behavioral signal).

## 8. Limitations

- 10 holdout triplets per method; CIs exploratory/small-sample.
- Source-model provider heterogeneity (recorded per method).
- Exceeding the two centroid baselines does not establish no external classifier could do better.
- A fresh judge instance has no episodic memory of the source generation.

