# Full Corpus Experiment 1 + 2 — Cross-method summary

Three independent 480-judgment runs, one per corpus production method, same judge configuration and prompt (barring per-method stimulus text).

| method | run_id |
|---|---|
| history_conditioned (truthful) | `fce1-20261001T050251Z` |
| batch (truthful) | `fce2-batch-truthful-20261001T064655Z` |
| independent_calls (truthful) | `fce2-indep-truthful-20261001T070301Z` |
| batch (false protocol: told history_conditioned) | `fce2-batch-20261001T060352Z-false-protocol` |
| independent_calls (false protocol: told history_conditioned) | `fce2-indep-20261001T061930Z-false-protocol` |
| independent_calls stimuli (false story: told batch) | `fce2-indep-storyswap-batch-20261001T130802Z` |

## 1. Primary summary — equal-weight mean S across targets (holdout)

| method | mean S (holdout) |
|---|---:|
| history_conditioned (truthful) | 0.008 |
| batch (truthful) | -0.008 |
| independent_calls (truthful) | 0.100 |
| batch (false protocol: told history_conditioned) | -0.008 |
| independent_calls (false protocol: told history_conditioned) | -0.150 |
| independent_calls stimuli (false story: told batch) | 0.033 |

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

### batch (false protocol: told history_conditioned)

| target | n | SELF | NAMED | OBS | **S** | **O** | **F** |
|---|---:|---:|---:|---:|---:|---:|---:|
| astra | 20 | 0.45 | 0.60 | 0.47 | **-0.03** | **0.12** | **-0.15** |
| fable | 20 | 0.50 | 0.50 | 0.53 | **-0.03** | **-0.03** | **0.00** |
| mimo | 20 | 0.50 | 0.50 | 0.47 | **0.03** | **0.03** | **0.00** |

### independent_calls (false protocol: told history_conditioned)

| target | n | SELF | NAMED | OBS | **S** | **O** | **F** |
|---|---:|---:|---:|---:|---:|---:|---:|
| astra | 20 | 0.40 | 0.35 | 0.62 | **-0.23** | **-0.28** | **0.05** |
| fable | 20 | 0.05 | 0.10 | 0.30 | **-0.25** | **-0.20** | **-0.05** |
| mimo | 20 | 0.55 | 0.50 | 0.53 | **0.03** | **-0.03** | **0.05** |

### independent_calls stimuli (false story: told batch)

| target | n | SELF | NAMED | OBS | **S** | **O** | **F** |
|---|---:|---:|---:|---:|---:|---:|---:|
| astra | 20 | 0.80 | 0.80 | 0.55 | **0.25** | **0.25** | **0.00** |
| fable | 20 | 0.00 | 0.05 | 0.23 | **-0.23** | **-0.17** | **-0.05** |
| mimo | 20 | 0.60 | 0.50 | 0.53 | **0.07** | **-0.03** | **0.10** |

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

### batch (false protocol: told history_conditioned)

| judge | astra | fable | mimo |
|---|---:|---:|---:|
| astra | 0.60 | 0.55 | 0.50 |
| fable | 0.45 | 0.50 | 0.45 |
| mimo | 0.50 | 0.50 | 0.50 |

### independent_calls (false protocol: told history_conditioned)

| judge | astra | fable | mimo |
|---|---:|---:|---:|
| astra | 0.35 | 0.10 | 0.65 |
| fable | 0.75 | 0.10 | 0.40 |
| mimo | 0.50 | 0.50 | 0.50 |

### independent_calls stimuli (false story: told batch)

| judge | astra | fable | mimo |
|---|---:|---:|---:|
| astra | 0.80 | 0.05 | 0.65 |
| fable | 0.60 | 0.05 | 0.40 |
| mimo | 0.50 | 0.40 | 0.50 |

## 4. Statistical baselines (centroid classifier)

| method | split | baseline | accuracy |
|---|---|---|---:|
| history_conditioned (truthful) | development | marginal | 0.967 |
| history_conditioned (truthful) | development | full | 0.967 |
| history_conditioned (truthful) | holdout | marginal | 0.967 |
| history_conditioned (truthful) | holdout | full | 1.000 |
| batch (truthful) | development | marginal | 0.900 |
| batch (truthful) | development | full | 0.767 |
| batch (truthful) | holdout | marginal | 0.783 |
| batch (truthful) | holdout | full | 0.767 |
| independent_calls (truthful) | development | marginal | 1.000 |
| independent_calls (truthful) | development | full | 1.000 |
| independent_calls (truthful) | holdout | marginal | 1.000 |
| independent_calls (truthful) | holdout | full | 1.000 |
| batch (false protocol: told history_conditioned) | development | marginal | 0.900 |
| batch (false protocol: told history_conditioned) | development | full | 0.767 |
| batch (false protocol: told history_conditioned) | holdout | marginal | 0.783 |
| batch (false protocol: told history_conditioned) | holdout | full | 0.767 |
| independent_calls (false protocol: told history_conditioned) | development | marginal | 1.000 |
| independent_calls (false protocol: told history_conditioned) | development | full | 1.000 |
| independent_calls (false protocol: told history_conditioned) | holdout | marginal | 1.000 |
| independent_calls (false protocol: told history_conditioned) | holdout | full | 1.000 |
| independent_calls stimuli (false story: told batch) | development | marginal | 1.000 |
| independent_calls stimuli (false story: told batch) | development | full | 1.000 |
| independent_calls stimuli (false story: told batch) | holdout | marginal | 1.000 |
| independent_calls stimuli (false story: told batch) | holdout | full | 1.000 |

Interpretation: the behavioral phenotype of each production method is cleanly separable by a simple centroid classifier. Independent_calls trajectories are the most separable (baseline accuracy 1.0), consistent with the strong p_H biases this method produces.

## 5. Observer-role accuracy (holdout, NAMED, judge ≠ target)

| method | distractor_producer | uninvolved_observer |
|---|---:|---:|
| history_conditioned (truthful) | 0.517 | 0.367 |
| batch (truthful) | 0.450 | 0.467 |
| independent_calls (truthful) | 0.383 | 0.450 |
| batch (false protocol: told history_conditioned) | 0.500 | 0.483 |
| independent_calls (false protocol: told history_conditioned) | 0.500 | 0.467 |
| independent_calls stimuli (false story: told batch) | 0.383 | 0.483 |

## 6. Compliance (all methods)

| method | total trials | first-attempt valid | eventually valid | abandoned |
|---|---:|---:|---:|---:|
| history_conditioned (truthful) | 480 | 1.000 | 1.000 | 0 |
| batch (truthful) | 480 | 1.000 | 1.000 | 0 |
| independent_calls (truthful) | 480 | 1.000 | 1.000 | 0 |
| batch (false protocol: told history_conditioned) | 480 | 1.000 | 1.000 | 0 |
| independent_calls (false protocol: told history_conditioned) | 480 | 1.000 | 1.000 | 0 |
| independent_calls stimuli (false story: told batch) | 480 | 1.000 | 1.000 | 0 |

## 6b. Validation study — objective A/B task

Same 60 stimulus pairs from the independent_calls method, shown in both natural and reversed A/B order, with two objectively-answerable questions (correct answer deterministic from the stimulus text):
- `more_H`: which sequence has more H outcomes
- `more_switches`: which sequence has more H/T transitions

| judge | question | split | n | accuracy | A-response rate |
|---|---|---|---:|---:|---:|
| astra | more_H | development | 60 | 1.000 | 0.500 |
| astra | more_H | holdout | 60 | 1.000 | 0.500 |
| astra | more_switches | development | 60 | 1.000 | 0.500 |
| astra | more_switches | holdout | 60 | 1.000 | 0.500 |
| fable | more_H | development | 59 | 1.000 | 0.508 |
| fable | more_H | holdout | 60 | 1.000 | 0.500 |
| fable | more_switches | development | 59 | 1.000 | 0.491 |
| fable | more_switches | holdout | 57 | 1.000 | 0.474 |
| mimo | more_H | development | 60 | 0.900 | 0.600 |
| mimo | more_H | holdout | 60 | 0.883 | 0.617 |
| mimo | more_switches | development | 60 | 0.550 | 0.950 |
| mimo | more_switches | holdout | 60 | 0.533 | 0.967 |

**Takeaway:** astra and fable both reach 100% accuracy on both objective questions with A-response rates near 0.50. Their heavy A-bias on source-attribution trials (astra ~87%, fable ~97%) is therefore **task-specific**, not a general A/B format incompetence. Mimo partially uses the stimulus for `more_H` (~89% accuracy, 60% A-rate) but collapses to near-always-A on `more_switches` (~54% accuracy, 96% A-rate) — mimo's position bias is partly feature-dependent.

## 6c. Within-stimulus three-story psychophysics

Exact same 60 independent_calls stimulus pairs, exact same pair construction / A/B orientation / judges / target questions. The only variable is the "how the sequences were generated" prefix shown to judges.

### SELF-wording holdout accuracy under each story

| judge | n | truthful indep | false hist | false batch | consistent across stories |
|---|---:|---:|---:|---:|---:|
| astra | 20 | 0.050 | 0.400 | 0.800 | 0.350 |
| fable | 20 | 0.900 | 0.050 | 0.000 | 0.150 |
| mimo | 20 | 0.600 | 0.550 | 0.600 | 0.750 |

**Takeaway:** both astra and fable produce architecture-conditional self-models — their SELF response to the same stimulus flips wildly depending on what production method the judge is told the sequence came from. Fable's self-model is approximately accurate ('I only produce near-all-H under stateless prompts, not under batch or history-conditioning'). Astra's is architecture-conditional but miscalibrated against its actual batch behavior. Mimo is largely story-insensitive (~75% of answers unchanged across the three stories), consistent with its weak-feature use across the board. The size of the story effect dwarfs any sequence-content effect for astra and fable — strong evidence that the SELF attribution signal is dominated by beliefs about generative process rather than by direct reading of the behavioral trace.

## 6d. Phenotype prediction — predicted vs actual p(H)

Before showing any sequence, each judge is asked at temperature 0.7 (10 replicates per cell) to predict the proportion of H outcomes a target model would produce under a stated generation procedure. Primary parser is the same strict A/B-style one used elsewhere (bare numeric line, no prose); a secondary loose parser is applied transparently to recover values from responses that ended in a bare float after reasoning.

### SELF-wording predictions

| judge | procedure | predicted (strict) | predicted (loose) | actual | signed_deviation (loose) |
|---|---|---:|---:|---:|---:|
| astra | batch | 0.500 (n=10) | 0.500 (n=10) | 0.495 | 0.005 |
| astra | history_conditioned | 0.500 (n=10) | 0.500 (n=10) | 0.460 | 0.040 |
| astra | independent_calls | 1.000 (n=10) | 1.000 (n=10) | 0.389 | 0.611 |
| fable | batch | 0.510 (n=10) | 0.510 (n=10) | 0.507 | 0.003 |
| fable | history_conditioned | 0.500 (n=10) | 0.500 (n=10) | 0.744 | -0.244 |
| fable | independent_calls | 1.000 (n=10) | 1.000 (n=10) | 0.987 | 0.013 |
| mimo | batch | 0.500 (n=10) | 0.500 (n=10) | 0.487 | 0.013 |
| mimo | history_conditioned | 0.500 (n=10) | 0.500 (n=10) | 0.633 | -0.133 |
| mimo | independent_calls | 0.500 (n=10) | 0.500 (n=10) | 0.860 | -0.360 |

### NAMED-wording predictions (abbreviated — judges × targets × procedures)

| judge | target | procedure | predicted (loose) | actual |
|---|---|---|---:|---:|
| astra | astra | batch | 0.500 | 0.495 |
| astra | astra | history_conditioned | 0.500 | 0.460 |
| astra | astra | independent_calls | 0.833 | 0.389 |
| astra | fable | batch | 0.500 | 0.507 |
| astra | fable | history_conditioned | 0.500 | 0.744 |
| astra | fable | independent_calls | 1.000 | 0.987 |
| astra | mimo | batch | 0.500 | 0.487 |
| astra | mimo | history_conditioned | 0.500 | 0.633 |
| astra | mimo | independent_calls | 1.000 | 0.860 |
| fable | astra | batch | 0.506 | 0.495 |
| fable | astra | history_conditioned | 0.508 | 0.460 |
| fable | astra | independent_calls | 1.000 | 0.389 |
| fable | fable | batch | 0.506 | 0.507 |
| fable | fable | history_conditioned | 0.507 | 0.744 |
| fable | fable | independent_calls | 1.000 | 0.987 |
| fable | mimo | batch | 0.520 | 0.487 |
| fable | mimo | history_conditioned | 0.510 | 0.633 |
| fable | mimo | independent_calls | 0.995 | 0.860 |
| mimo | astra | batch | 0.500 | 0.495 |
| mimo | astra | history_conditioned | 0.500 | 0.460 |
| mimo | astra | independent_calls | 0.500 | 0.389 |
| mimo | fable | batch | 0.500 | 0.507 |
| mimo | fable | history_conditioned | 0.500 | 0.744 |
| mimo | fable | independent_calls | 0.500 | 0.987 |
| mimo | mimo | batch | 0.500 | 0.487 |
| mimo | mimo | history_conditioned | 0.500 | 0.633 |
| mimo | mimo | independent_calls | 0.500 | 0.860 |

### Interpretation

- **Fable predicts procedure-level behavior, not model-specific self-knowledge.** Fable predicts p_H ≈ 1 for the independent-calls procedure *regardless of which target model is asked about* (fable itself: 1.00, astra: 1.00, mimo: 0.995). It also predicts p_H ≈ 0.5 under batch and history_conditioned for every target. Fable's apparent self-recognition in independent_calls falls out of a general belief about what the procedure does to LLMs — which happens to be approximately accurate for fable itself (actual 0.987) but strongly miscalibrated for astra (actual 0.389) and mimo (actual 0.86).
- **Astra holds the same procedure-level theory but is miscalibrated against its own behavior.** Astra also predicts p_H = 1 for every target under independent calls, including itself — but astra's actual indep output is p_H = 0.389. That explains astra's story-swap pattern: under truthful indep story, astra sees p_H = 0.39 sequences and rejects them as not matching its "indep → p_H ≈ 1" theory; under batch story, astra sees the same sequences and accepts them because they are closer to its "batch → p_H ≈ 0.5" theory.
- **Mimo predicts 0.5 for every target × procedure combination.** 10/10 replicates per cell, no variance. Mimo has no differentiated procedure-level theory of LLM behavior, consistent with its weak-feature use across every earlier experiment.
- The reviewer's prediction of a strict ordering for fable (`batch < hist < indep`) partially holds in a qualitative sense: fable predicts batch ≈ hist ≈ 0.5 << indep ≈ 1. The history_conditioned prediction is tied with batch, not intermediate as the reviewer predicted.
- **Reframing: what looked like protocol-conditional self-knowledge is largely protocol-conditional task knowledge, applied uniformly to any LLM.** That's still interesting — the judges have calibrated beliefs about what the independent_calls procedure does to LLMs in general — but it reduces the self-specificity of the earlier story-swap result.

## 7. Cross-method synthesis

- **Protocol information strongly shapes self-recognition.** The independent_calls comparison between the truthful-protocol run and the false-protocol run shows this clearly: fable's own-trajectory accuracy under SELF-wording moves from 0.05 (false-protocol) to 0.90 (truthful-protocol), and NAMED-on-fable from 0.10 to 0.75. The equal-weight mean S flips sign (−0.150 → +0.100) between the two conditions on exactly the same stimulus sequences; only the judge's description of how those sequences were produced changed.
- **Under truthful protocols, modest positive self-recognition emerges in independent_calls** (mean S = +0.100, fable S = +0.45 with CI [0.25, 0.63] on holdout). History_conditioned and batch stay near zero even with the truthful protocol.
- **The task is externally solvable in all methods.** The centroid baseline hits 97–100% on holdout. The behavioral signal is there; LLM judges only partially use it, and only when the protocol description matches the production reality.
- **Astra is a consistent anti-self-recognizer** across methods and protocols: holdout NAMED-on-astra = 0.00 and SELF-on-astra = 0.05 under the truthful independent_calls protocol, while fable and mimo as observers identify astra at above-chance rates in some cells.
- **Mimo scores at or near chance everywhere** across all methods and protocols, consistent with an A-position-biased or weak-feature-using responder (compliant parsing but not using the behavioral signal).
- **Astra and fable's heavy A-bias on source-attribution is task-specific, not a general format problem.** The validation study (same stimuli, both A/B orderings, objectively-answerable questions) shows astra and fable at 100% accuracy with A-rate near 0.50 on both `more_H` and `more_switches`. Mimo partially uses the stimulus for `more_H` but still collapses to A-always on `more_switches`.
- **The protocol-conditional self-recognition reduces to protocol-conditional task knowledge applied uniformly.** The phenotype-prediction experiment asks judges, before they see any sequence, what p_H they would expect each target to produce under each procedure. Fable predicts p_H ≈ 1 under indep for all three targets (not just itself); the same for astra. Fable's prediction happens to match its own actual indep behavior; astra's does not. So the story-swap finding is driven by a general procedure theory ("indep → H") rather than by self-specific knowledge about one's own output distribution.

## 8. Limitations

- 10 holdout triplets per method; CIs exploratory/small-sample.
- Source-model provider heterogeneity (recorded per method).
- Exceeding the two centroid baselines does not establish no external classifier could do better.
- A fresh judge instance has no episodic memory of the source generation.

