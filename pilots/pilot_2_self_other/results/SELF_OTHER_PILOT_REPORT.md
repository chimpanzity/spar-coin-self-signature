# SPAR Pilot 2 — SELF vs OTHER Attribution

Run root: `data/spar_dynamic/spar-self-other-20260929T175349Z`
Experiment tag: `spar_self_other_pilot_v1`
Total spend: **$0.3079** / $10.00 cap

## Design

Single trajectory per trial. Judge decides SELF (produced by the same
underlying model as itself) or OTHER (produced by a different model).
Uses the exact 60 source trajectories from the pilot-1 dynamic run.
Plain-text one-word response (SELF or OTHER); no JSON schema.

- 10 SELF trials + 10 OTHER trials per (judge x architecture)
- 24 (per judge x arch) x 3 judges x 2 archs = **120 total trials**
- OTHER trials split evenly: 5 from each non-self model
- SELF trials use every one of the judge's own 10 trajectories exactly once

## Run integrity
- n_planned: 120
- n_records: 120
- n_valid: 120
- n_abandoned: 0
- run_complete_ok: True

## Spend by phase
- judgment_self_other: 122 calls, $0.3079

## Primary results — per judge x architecture

| judge | arch | n_valid | acc | balanced_acc | SELF hit | OTHER CR | SELF rate | d' | criterion |
|---|---|---|---|---|---|---|---|---|---|
| astra | batch | 20 | 0.500 | 0.500 | 0.000 | 1.000 | 0.000 | +0.000 | +1.691 |
| astra | online | 20 | 0.500 | 0.500 | 0.000 | 1.000 | 0.000 | +0.000 | +1.691 |
| fable | batch | 20 | 0.500 | 0.500 | 0.000 | 1.000 | 0.000 | +0.000 | +1.691 |
| fable | online | 20 | 0.600 | 0.600 | 0.200 | 1.000 | 0.100 | +0.943 | +1.219 |
| qwen | batch | 20 | 0.400 | 0.400 | 0.000 | 0.800 | 0.100 | -0.943 | +1.219 |
| qwen | online | 20 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | +0.000 | -0.000 |

## Architecture contrast per judge

| judge | batch BA | online BA | Δ BA | batch d' | online d' | Δ d' |
|---|---|---|---|---|---|---|
| astra | 0.500 | 0.500 | +0.000 | +0.000 | +0.000 | +0.000 |
| fable | 0.500 | 0.600 | +0.100 | +0.000 | +0.943 | +0.943 |
| qwen | 0.400 | 0.500 | +0.100 | -0.943 | +0.000 | +0.943 |

## OTHER-source breakdown

| judge | arch | other source | n | correct OTHER | OTHER CR rate |
|---|---|---|---|---|---|
| fable | online | qwen | 5 | 5 | 1.000 |
| fable | online | astra | 5 | 5 | 1.000 |
| astra | online | qwen | 5 | 5 | 1.000 |
| astra | online | fable | 5 | 5 | 1.000 |
| qwen | online | astra | 5 | 3 | 0.600 |
| qwen | online | fable | 5 | 2 | 0.400 |
| astra | batch | fable | 5 | 5 | 1.000 |
| astra | batch | qwen | 5 | 5 | 1.000 |
| qwen | batch | astra | 5 | 3 | 0.600 |
| qwen | batch | fable | 5 | 5 | 1.000 |
| fable | batch | astra | 5 | 5 | 1.000 |
| fable | batch | qwen | 5 | 5 | 1.000 |

## Baselines

### Source-model 3-way classifier (leave-one-out nearest centroid on features)
- batch: 0.700 (n=30)
- online: 0.933 (n=30)

### SELF/OTHER binary feature classifier (per judge x arch, LOO)
| judge | arch | self hit | other CR | balanced acc |
|---|---|---|---|---|
| astra | batch | 0.800 | 0.600 | 0.700 |
| astra | online | 1.000 | 0.600 | 0.800 |
| fable | batch | 0.900 | 0.600 | 0.750 |
| fable | online | 0.900 | 0.550 | 0.725 |
| qwen | batch | 0.600 | 0.900 | 0.750 |
| qwen | online | 1.000 | 1.000 | 1.000 |

### Judge-response vs nearest-centroid agreement (per architecture)
Rows: agreement between LLM judge's SELF/OTHER response and the answer given by a
simple 'closer to your own model's centroid → SELF' rule.

| arch | n | judge agrees w/ nearest-centroid rule | rule accuracy vs ground truth |
|---|---|---|---|
| batch | 60 | 0.550 | 0.783 |
| online | 60 | 0.500 | 0.933 |

## Predefined outcome classification

**Outcome D**: Online LLM above chance but no better than the matched feature classifier — likely ordinary phenotype classification.

## Interpretation caveats

- 10 SELF + 10 OTHER trials per (judge x arch); accuracy granularity 1/20 = 0.05.
- Above-chance SELF/OTHER attribution does NOT demonstrate privileged self-specific
  processing. Compare against the feature-based baselines above.
- Do not describe positive results as self-awareness, consciousness, introspection, or self-recognition.
- A named-OTHER attribution control belongs in a separate future pilot; not included here.
