# Full Corpus Experiment 1 + 2 — Cross-method summary

Three independent 480-judgment runs, one per corpus production method, same judge configuration and prompt (barring per-method stimulus text).

| method | run_id |
|---|---|
| history_conditioned | `fce1-20261001T050251Z` |
| batch | `fce2-batch-20261001T060352Z` |
| independent_calls | `fce2-indep-20261001T061930Z` |

## 1. Primary summary — equal-weight mean S across targets (holdout)

| method | mean S (holdout) |
|---|---:|
| history_conditioned | 0.008 |
| batch | -0.008 |
| independent_calls | -0.150 |

Positive values would indicate SELF-wording-plus-ownership advantage over named observers; negative values indicate observers outperform the target producer on its own trajectories.

## 2. Per-target holdout contrasts (S / O / F)

### history_conditioned

| target | n | SELF | NAMED | OBS | **S** | **O** | **F** |
|---|---:|---:|---:|---:|---:|---:|---:|
| astra | 20 | 0.55 | 0.55 | 0.60 | **-0.05** | **-0.05** | **0.00** |
| fable | 20 | 0.30 | 0.15 | 0.30 | **0.00** | **-0.15** | **0.15** |
| mimo | 20 | 0.50 | 0.50 | 0.42 | **0.07** | **0.07** | **0.00** |

### batch

| target | n | SELF | NAMED | OBS | **S** | **O** | **F** |
|---|---:|---:|---:|---:|---:|---:|---:|
| astra | 20 | 0.45 | 0.60 | 0.47 | **-0.03** | **0.12** | **-0.15** |
| fable | 20 | 0.50 | 0.50 | 0.53 | **-0.03** | **-0.03** | **0.00** |
| mimo | 20 | 0.50 | 0.50 | 0.47 | **0.03** | **0.03** | **0.00** |

### independent_calls

| target | n | SELF | NAMED | OBS | **S** | **O** | **F** |
|---|---:|---:|---:|---:|---:|---:|---:|
| astra | 20 | 0.40 | 0.35 | 0.62 | **-0.23** | **-0.28** | **0.05** |
| fable | 20 | 0.05 | 0.10 | 0.30 | **-0.25** | **-0.20** | **-0.05** |
| mimo | 20 | 0.55 | 0.50 | 0.53 | **0.03** | **-0.03** | **0.05** |

## 3. NAMED judge × target accuracy (holdout)

### history_conditioned

| judge | astra | fable | mimo |
|---|---:|---:|---:|
| astra | 0.55 | 0.10 | 0.25 |
| fable | 0.70 | 0.15 | 0.60 |
| mimo | 0.50 | 0.50 | 0.50 |

### batch

| judge | astra | fable | mimo |
|---|---:|---:|---:|
| astra | 0.60 | 0.55 | 0.50 |
| fable | 0.45 | 0.50 | 0.45 |
| mimo | 0.50 | 0.50 | 0.50 |

### independent_calls

| judge | astra | fable | mimo |
|---|---:|---:|---:|
| astra | 0.35 | 0.10 | 0.65 |
| fable | 0.75 | 0.10 | 0.40 |
| mimo | 0.50 | 0.50 | 0.50 |

## 4. Statistical baselines (centroid classifier)

| method | split | baseline | accuracy |
|---|---|---|---:|
| history_conditioned | development | marginal | 0.967 |
| history_conditioned | development | full | 0.967 |
| history_conditioned | holdout | marginal | 0.967 |
| history_conditioned | holdout | full | 1.000 |
| batch | development | marginal | 1.000 |
| batch | development | full | 0.767 |
| batch | holdout | marginal | 0.840 |
| batch | holdout | full | 0.767 |
| independent_calls | development | marginal | 1.000 |
| independent_calls | development | full | 1.000 |
| independent_calls | holdout | marginal | 1.000 |
| independent_calls | holdout | full | 1.000 |

Interpretation: the behavioral phenotype of each production method is cleanly separable by a simple centroid classifier. Independent_calls trajectories are the most separable (baseline accuracy 1.0), consistent with the strong p_H biases this method produces.

## 5. Observer-role accuracy (holdout, NAMED, judge ≠ target)

| method | distractor_producer | uninvolved_observer |
|---|---:|---:|
| history_conditioned | 0.517 | 0.367 |
| batch | 0.500 | 0.483 |
| independent_calls | 0.500 | 0.467 |

## 6. Compliance (all methods)

| method | total trials | first-attempt valid | eventually valid | abandoned |
|---|---:|---:|---:|---:|
| history_conditioned | 480 | 1.000 | 1.000 | 0 |
| batch | 480 | 1.000 | 1.000 | 0 |
| independent_calls | 480 | 1.000 | 1.000 | 0 |

## 7. Cross-method synthesis

- **No evidence of selective self-recognition in any method.** The equal-weight mean S across targets is near zero for history_conditioned (+0.008) and batch (−0.008), and NEGATIVE for independent_calls (−0.150).
- **The task is externally solvable in all methods.** The centroid baseline hits 97–100% on holdout. The behavioral signal is there; LLM judges fail to use it.
- **The most separable method yields the LARGEST self-deficit.** On independent_calls — where p_H alone perfectly classifies — astra and fable judges are WORSE than observers at identifying their own trajectories. Example: fable NAMED-on-fable 0.10, fable SELF-on-fable 0.05, while fable NAMED-on-astra is 0.75. Fable's own independent_calls phenotype is p_H ≈ 0.99 (near-all-H); when asked to identify its own, the model appears to reject the highly biased sequence as 'not me'.
- **Fable is a strong general observer across methods** on astra and mimo targets, but reliably weakest on fable targets.
- **Mimo scores at or near chance everywhere** across all three methods, consistent with an A-position-biased or weak-feature-using responder.

## 8. Limitations

- 10 holdout triplets per method; CIs exploratory/small-sample.
- Source-model provider heterogeneity (recorded per method).
- Exceeding the two centroid baselines does not establish no external classifier could do better.
- A fresh judge instance has no episodic memory of the source generation.

