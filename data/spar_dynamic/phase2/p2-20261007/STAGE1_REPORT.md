# Stage 1 report (development only)

Generated 2026-10-08T04:09:43.845740Z. Run `p2-20261007`. Protocol SPAR_Phase2_v7.1.

## Development corpus

| source | prompt | valid / attempted | mean heads | first-H rate | switch rate | longest run | distinct strings | effective strings | distinct first-10 | effective first-10 | failures |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| astra | fair | 60/60 | 10.433 | 0.917 | 0.644 | 2.883 | 31 | 14.17 | 11 | 3.03 |  |
| astra | plain | 60/60 | 10.683 | 0.917 | 0.651 | 2.7 | 37 | 28.57 | 12 | 6.29 |  |
| fable | fair | 59/60 | 10.017 | 1.0 | 0.623 | 2.983 | 18 | 8.39 | 4 | 1.42 | {'no_list': 1} |
| fable | plain | 60/60 | 10.467 | 0.917 | 0.668 | 2.967 | 16 | 6.23 | 7 | 2.39 |  |
| qwen | fair | 6/60 | 10.333 | 1.0 | 0.754 | 1.833 | 6 | 6.0 | 6 | 6.0 | {'no_list': 38, 'wrong_length': 16} |
| qwen | plain | 59/60 | 10.085 | 1.0 | 0.898 | 1.593 | 16 | 4.39 | 7 | 2.63 | {'no_list': 1} |

Most frequent strings per cell (string, count):

- astra/fair: `HTTHHTHTTTHHTHTHHTTH` x11; `HTTHHTHTTTHHTHTHHTHT` x6; `HTTHHTHTTTHHTHHHTTHT` x6
- astra/plain: `HTTHHTHTTHTHHHTTHTHT` x4; `HTHHTTHTHTTHHTHTHHTH` x3; `HTHHTTHTTHHTHTHHTTHH` x3
- fable/fair: `HTTHHTHTTTHHTHTTHHTH` x11; `HTTHHTHTTTHHTHTHHTTH` x10; `HTTHHTHTTTHHTHHTTHTH` x9
- fable/plain: `HTTHHHTHTTHTHHTHTTHH` x15; `HTTHHHTHTTHTHHTHTTHT` x14; `HTTHHTHTTTHHTHTHHTHT` x10
- qwen/fair: `HTHHTHTTHTHHTTHTHTHH` x1; `HHTTHTHHTTHTTHTHTHTH` x1; `HTHHTTHTTHHTTHHTHTTH` x1
- qwen/plain: `HTHTHTHTHTHTHTHTHTHT` x24; `HTHHTTHTHTHTHTHTHTHT` x13; `HTHHTTHTHTHTHHTTHTHT` x4

Cells below 80% validity are NOT paused (Chris, 2026-10-07: keep going).

## Objective fixtures (invented sources, explicit rules)

| task / judge | valid | correct (max abs error <= 0.2) | valid gate (>= 11/12) |
|---|---:|---:|---|
| fixture_completion|astra | 12/12 | 12/12 | pass |
| fixture_completion|fable | 12/12 | 12/12 | pass |
| fixture_completion|qwen | 12/12 | 9/12 | pass |
| fixture_pair|astra | 12/12 | 12/12 | pass |
| fixture_pair|fable | 2/12 | 2/12 | FAIL |
| fixture_pair|qwen | 12/12 | 8/12 | pass |

## Rehearsal (development data; validity and response variability only)

| task | judge | condition/order | valid / n | mean value | SD | share exactly 0.5 |
|---|---|---|---:|---:|---:|---:|
| rehearsal_completion | astra | known | 12/12 | 0.5 | 0.176 | 0.833 |
| rehearsal_completion | astra | withheld | 12/12 | 0.501 | 0.151 | 0.833 |
| rehearsal_completion | fable | known | 12/12 | 0.502 | 0.1 | 0.725 |
| rehearsal_completion | fable | withheld | 12/12 | 0.503 | 0.091 | 0.692 |
| rehearsal_completion | qwen | known | 12/12 | 0.496 | 0.014 | 0.917 |
| rehearsal_completion | qwen | withheld | 12/12 | 0.496 | 0.014 | 0.917 |
| rehearsal_pairs | astra | designated | 12/12 | 0.537 | 0.124 | 0.917 |
| rehearsal_pairs | fable | designated | 11/12 | 0.547 | 0.177 | 0.091 |
| rehearsal_pairs | qwen | designated | 12/12 | 0.417 | 0.215 | 0.083 |

Source-linked rehearsal scores were not computed or inspected (Section 5.4).

## Headroom review (five-fold out-of-fold empirical-prefix observer)

I[g,p] = mean(B_withheld - B_known) on held-out development parents. Prefix value = source-position loss minus source-known prefix loss.

| source | prompt | I[g,p] | prefix value |
|---|---|---:|---:|
| astra | plain | +0.0294 | +0.0642 |
| astra | fair | +0.0229 | +0.0505 |
| fable | plain | -0.0069 | +0.0802 |
| fable | fair | +0.0091 | +0.0094 |
| qwen | plain | +0.0038 | +0.0169 |
| qwen | fair | +0.0066 | +0.0000 |

| source | I[g] (prompt-averaged) |
|---|---:|
| astra | +0.0261 |
| fable | +0.0011 |
| qwen | +0.0052 |

headroom_review_required = **False** (threshold 0.02 Brier units; operational reviewer threshold, not a futility test).

