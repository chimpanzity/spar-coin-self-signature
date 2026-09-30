# SPAR Stimulus Corpus — Three Production Architectures

Run root: `data/spar_dynamic/spar-stimulus-corpus-20260930T012044Z`
Experiment tag: `spar_stimulus_corpus_v1`
Total spend (from persisted raw attempts): **$7.4197** / $60.00 cap

## Canonical dataset

The canonical stimulus bank is `corpus/trajectories.csv` (180 rows, one row
per valid trajectory). `source_trajectories.csv` in this directory is the
raw analysis-side view and retains 187 rows including 7 abandoned
mimo/history_conditioned trajectories (the backfill re-ran under fresh
replicate indices and succeeded). Use `corpus/` for any downstream work;
this file is the study writeup.

## 1. Scientific question

For the same nominal task ("simulate a sequence of fair coin flips"),
how does the architecture of sequence production alter the behavioral
phenotype of astra / fable / mimo?

Three architectures compared:
- **batch**: one API call generates all 100 flips via within-completion autoregression
- **history_conditioned**: 100 sequential API calls; each receives the complete prior history
- **independent_calls**: 100 sequential API calls; every call receives an identical fixed prompt, no history

## 2. Run integrity

- n_records: 187
- cell_counts: {'astra/batch': 20, 'astra/history_conditioned': 20, 'astra/independent_calls': 20, 'fable/batch': 20, 'fable/history_conditioned': 20, 'fable/independent_calls': 20, 'mimo/batch': 20, 'mimo/history_conditioned': 20, 'mimo/independent_calls': 20}
- cell_counts_ok: True
- cell_counts_min_required: 20
- invalid_trajectories: 7 entries (first 5 shown): [('mimo_history_conditioned_04', 'status=failed len=0'), ('mimo_history_conditioned_08', 'status=failed len=0'), ('mimo_history_conditioned_09', 'status=failed len=0'), ('mimo_history_conditioned_14', 'status=failed len=0'), ('mimo_history_conditioned_16', 'status=failed len=0')]
- run_complete_ok: True

## 3. Behavioral phenotypes (per model x method, mean +/- SD over trajectories)

### At prefix length 100 (full trajectory)

| model | method | n | mean p_H | mean switch | mean runs_Z | mean longest_run | mean HT | mean TH |
|---|---|---|---|---|---|---|---|---|
| astra | batch | 20 | 0.495 | 0.620 | +2.30 | 3.6 | 0.313 | 0.308 |
| astra | history_conditioned | 20 | 0.460 | 0.632 | +2.63 | 4.6 | 0.315 | 0.317 |
| astra | independent_calls | 20 | 0.389 | 0.473 | -0.07 | 7.7 | 0.237 | 0.236 |
| fable | batch | 20 | 0.507 | 0.643 | +2.76 | 3.0 | 0.326 | 0.318 |
| fable | history_conditioned | 20 | 0.744 | 0.476 | +2.50 | 24.3 | 0.239 | 0.237 |
| fable | independent_calls | 20 | 0.987 | 0.026 | +0.22 | 78.0 | 0.013 | 0.013 |
| mimo | batch | 20 | 0.487 | 0.624 | +2.39 | 3.5 | 0.315 | 0.309 |
| mimo | history_conditioned | 20 | 0.633 | 0.497 | +0.74 | 7.3 | 0.251 | 0.247 |
| mimo | independent_calls | 20 | 0.860 | 0.233 | -0.30 | 22.2 | 0.116 | 0.118 |

## 4. Architecture comparison — per model, per prefix length

| model | method | prefix | mean p_H | mean switch | mean runs_Z | mean longest_run |
|---|---|---|---|---|---|---|
| astra | batch | 20 | 0.497 | 0.642 | +1.01 | 2.8 |
| astra | batch | 50 | 0.493 | 0.615 | +1.48 | 3.4 |
| astra | batch | 100 | 0.495 | 0.620 | +2.30 | 3.6 |
| astra | history_conditioned | 20 | 0.483 | 0.774 | +2.19 | 2.4 |
| astra | history_conditioned | 50 | 0.473 | 0.687 | +2.52 | 3.2 |
| astra | history_conditioned | 100 | 0.460 | 0.632 | +2.63 | 4.6 |
| astra | independent_calls | 20 | 0.357 | 0.471 | +0.17 | 5.2 |
| astra | independent_calls | 50 | 0.386 | 0.465 | -0.16 | 6.8 |
| astra | independent_calls | 100 | 0.389 | 0.473 | -0.07 | 7.7 |
| fable | batch | 20 | 0.505 | 0.605 | +0.69 | 3.0 |
| fable | batch | 50 | 0.505 | 0.620 | +1.55 | 3.0 |
| fable | batch | 100 | 0.507 | 0.643 | +2.76 | 3.0 |
| fable | history_conditioned | 20 | 0.545 | 0.824 | +2.69 | 2.6 |
| fable | history_conditioned | 50 | 0.610 | 0.726 | +3.60 | 4.7 |
| fable | history_conditioned | 100 | 0.744 | 0.476 | +2.50 | 24.3 |
| fable | independent_calls | 20 | 0.990 | 0.021 | +0.33 | 19.4 |
| fable | independent_calls | 50 | 0.990 | 0.019 | -0.35 | 44.3 |
| fable | independent_calls | 100 | 0.987 | 0.026 | +0.22 | 78.0 |
| mimo | batch | 20 | 0.500 | 0.600 | +0.68 | 3.1 |
| mimo | batch | 50 | 0.490 | 0.614 | +1.47 | 3.4 |
| mimo | batch | 100 | 0.487 | 0.624 | +2.39 | 3.5 |
| mimo | history_conditioned | 20 | 0.615 | 0.621 | +1.22 | 3.9 |
| mimo | history_conditioned | 50 | 0.614 | 0.535 | +0.82 | 6.0 |
| mimo | history_conditioned | 100 | 0.633 | 0.497 | +0.74 | 7.3 |
| mimo | independent_calls | 20 | 0.857 | 0.234 | -0.26 | 10.2 |
| mimo | independent_calls | 50 | 0.854 | 0.246 | -0.00 | 16.4 |
| mimo | independent_calls | 100 | 0.860 | 0.233 | -0.30 | 22.2 |

## 5. Source-model identifiability (LOO nearest centroid, per method x prefix)

Chance = 1/3 = 0.333

| method | prefix | n | accuracy | vs chance |
|---|---|---|---|---|
| batch | 20 | 60 | 0.567 | +0.233 |
| batch | 50 | 60 | 0.383 | +0.050 |
| batch | 100 | 60 | 0.533 | +0.200 |
| history_conditioned | 20 | 60 | 0.683 | +0.350 |
| history_conditioned | 50 | 60 | 0.883 | +0.550 |
| history_conditioned | 100 | 60 | 0.900 | +0.567 |
| independent_calls | 20 | 60 | 0.333 | +0.000 |
| independent_calls | 50 | 60 | 0.667 | +0.333 |
| independent_calls | 100 | 60 | 0.667 | +0.333 |

## 6. Representative trajectories (closest to standardized cell centroid)

| model | method | p_H | switch | runs_Z | longest_run | sequence |
|---|---|---|---|---|---|---|
| astra | batch | 0.50 | 0.62 | +2.21 | 4 | `HTTHHTHTTTTHHHTTHTHHTTHTHTHHTTHHTTTHTHHHTHTHHTTHTHHHHTTTHTTHTTHHHTHTHTHTHTTTHHTHTHHTHTHHTTHTTHTHHHTT` |
| astra | history_conditioned | 0.46 | 0.62 | +2.29 | 5 | `HTHTTTHTHTTHHHTHHTTHTHTTHHHTHHHTHTTHHTTTHTTTHHTTHTHHTHTTHTHTTHTHTTHTTTHHHTHTTHTHHHTHTTHTHTHHTTHTTTTT` |
| astra | independent_calls | 0.38 | 0.46 | -0.24 | 7 | `TTTTHTHTHTTHHHHHTTTHHHTHTTTTTTTHHTTHTHTTTTTHTTTHTTTHTHTTTHHTHHTHTHTHTTTHTTTHTTHHTTHHHHHTTTTHHTTTTTTT` |
| fable | batch | 0.51 | 0.64 | +2.62 | 3 | `HTTHHTHTTTHHTHTHHHTTHTHHTTTHTHHTTHTHHHTTHTTHHTHTHHTTTHHTHTHTTHHHTHTTHTHHTTHTHHHTTHTHTTHHTTHHTHTHTHHT` |
| fable | history_conditioned | 0.74 | 0.46 | +1.97 | 19 | `HTHTHTTHTHTHTHTHTHHTHTHTHTHTTHHHTHHHHHTHHHHHTHHTHTHHHHHHHHHHHHHHHHHHHTTHHHTHHHHHHHTHHHHHHHHHHTHHTHHH` |
| fable | independent_calls | 1.00 | 0.00 | +nan | 100 | `HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH` |
| mimo | batch | 0.49 | 0.64 | +2.62 | 3 | `HTHTTHHTTHHTHHHTHTTHHHTTHTTHHTTHHTTTHTHTTHTHHHTTHTHHTTHTHTTHHTHTHTHTTHTHTHHHTTHTHTTHTTHHTHTTTHTHHHTT` |
| mimo | history_conditioned | 0.65 | 0.51 | +1.00 | 7 | `HHTTHHHHTHHHTHHTHTHHHHHTTTHHTHTHTTHHHTHHHHTHHHTTHHHHHHHTHHHTTHHTHHTHTTHHHTHHHHHTTHTHTHTTHHHTTHHTHTHH` |
| mimo | independent_calls | 0.85 | 0.24 | -0.60 | 28 | `HHHHHHTHHHHHHHHHTHHHTHTHHHHHTHHHHTHHHHHHHHHHHHHHHHHHHHHHHHHHHHTHTTHHHHTTHHHHTTHHTHHHHHHHHHHHTHHHHHHH` |

## 7. Temporal emergence — classification accuracy vs prefix length

| method | acc @ 20 | acc @ 50 | acc @ 100 |
|---|---|---|---|
| batch | 0.567 | 0.383 | 0.533 |
| history_conditioned | 0.683 | 0.883 | 0.900 |
| independent_calls | 0.333 | 0.667 | 0.667 |

## 8. Relation to prior 50-flip pilot

The previous 50-flip source pilot compared batch vs history_conditioned only
and found substantially stronger source-model identifiability under
history_conditioned generation (0.933 online vs 0.700 batch). The current
100-flip corpus adds an independent_calls control and Mimo in place of Qwen.
The independent_calls vs batch comparison indexes the effect of crossing
fresh inference boundaries WITHOUT explicit accumulated history; the
independent_calls vs history_conditioned comparison indexes the additional
effect of explicit history conditioning.

## 9. Implications for self-recognition studies (no judgments here)

This corpus is stimulus-only. Judgments belong to a later study. The
architecture-effect results above can inform which cells look most
informative to include as stimuli in a follow-up recognition experiment.

## 10. Relevance to PACA baseline

Each trajectory is 100 binary outcomes — the same length as a PACA / Proteus
matching-pennies session. Later work can compare these context-free coin
phenotypes against 100-trial PACA choice streams from the same models,
bearing in mind that PACA adds an adaptive opponent, outcomes, and game history.

## 11. Limitations

- Only 20 trajectories per (model, method) cell (10 development + 10 evaluation); feature-classifier estimates are noisy.
- Model/API dependence: OpenRouter serving of the exact same model_id may vary over time.
- Call architecture may alter hidden serving behavior beyond what we can observe.
- Prefix analyses reflect prefixes of a 100-flip generation, NOT separately requested lengths.
- Coin simulation is not equivalent to strategic play.

## Spend breakdown (derived from raw_attempts.jsonl)

| kind | calls | cost |
|---|---|---|
| corpus_batch | 238 | $0.6041 |
| corpus_history_conditioned | 6722 | $4.3856 |
| corpus_independent_calls | 6016 | $2.4300 |
| **TOTAL** | 12976 | **$7.4197** |
