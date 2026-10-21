# Stage 1 report (development only)

Generated 2026-10-08T10:37:41.386723Z. Run `p2-mimo-20261008`. Protocol SPAR_Phase2_v7.1.

## Development corpus

| source | prompt | valid / attempted | mean heads | first-H rate | switch rate | longest run | distinct strings | effective strings | distinct first-10 | effective first-10 | failures |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| astra | fair | 60/60 | 10.533 | 0.933 | 0.641 | 2.867 | 32 | 18.18 | 13 | 3.24 |  |
| astra | plain | 60/60 | 10.567 | 0.95 | 0.657 | 2.667 | 36 | 25.35 | 9 | 5.56 |  |
| fable | fair | 59/60 | 10.203 | 0.932 | 0.631 | 2.949 | 29 | 16.19 | 8 | 2.64 | {'conflicting_lists': 1} |
| fable | plain | 60/60 | 10.633 | 0.967 | 0.682 | 2.967 | 15 | 5.23 | 6 | 2.2 |  |
| mimo | fair | 25/60 | 10.16 | 0.72 | 0.606 | 2.96 | 25 | 25.0 | 22 | 18.94 | {'conflicting_lists': 7, 'no_list': 17, 'wrong_length': 9, 'truncated_length': 2} |
| mimo | plain | 56/60 | 10.482 | 0.714 | 0.647 | 2.732 | 56 | 56.0 | 39 | 28.51 | {'no_list': 3, 'wrong_length': 1} |

Most frequent strings per cell (string, count):

- astra/fair: `HTTHHTHTTTHHTHTHHTHH` x7; `HTTHHTHTTTHHTHHHTTHT` x7; `HTTHHTHTTTHHTHTHHTTH` x5
- astra/plain: `HTTHHTHTTHTHHHTTHTHT` x5; `HTHHTTHTTHHTHTHHTTHH` x4; `HTTHHTHTTTHHTHTHHTHT` x4
- fable/fair: `HTTHHTHTTTHHTHTTHHTH` x7; `HTTHHTHTTTHHHTHTTHHT` x7; `HTTHHTHTTTHHTHTTHHHT` x6
- fable/plain: `HTTHHHTHTTHTHHTHTHTH` x17; `HTTHHHTHTTHTHHTHTTHH` x15; `HTTHHTHTTTHHTHTHHTHT` x12
- mimo/fair: `HHTTHTHHHTTHTTTHTHHT` x1; `THHTHHHTTHTTHTHTHHTH` x1; `HTTHHTHHHTTTHHTTHTHT` x1
- mimo/plain: `HTHHTHHTHTTHTHHTHTHH` x1; `HTHHTTHTHHTHHTHTTHHT` x1; `HTHHTHTHTHHTTHHHTTHT` x1

Cells below 80% validity are NOT paused (Chris, 2026-10-07: keep going).

## Objective fixtures (invented sources, explicit rules)

| task / judge | valid | correct (max abs error <= 0.2) | valid gate (>= 11/12) |
|---|---:|---:|---|
| fixture_completion|astra | 12/12 | 12/12 | pass |
| fixture_completion|fable | 12/12 | 12/12 | pass |
| fixture_completion|mimo | 12/12 | 6/12 | pass |
| fixture_pair|astra | 12/12 | 12/12 | pass |
| fixture_pair|fable | 2/12 | 2/12 | FAIL |
| fixture_pair|mimo | 9/12 | 4/12 | FAIL |

## Rehearsal (development data; validity and response variability only)

| task | judge | condition/order | valid / n | mean value | SD | share exactly 0.5 |
|---|---|---|---:|---:|---:|---:|
| rehearsal_completion | astra | known | 12/12 | 0.5 | 0.0 | 1.0 |
| rehearsal_completion | astra | withheld | 12/12 | 0.5 | 0.0 | 1.0 |
| rehearsal_completion | fable | known | 12/12 | 0.501 | 0.006 | 0.9 |
| rehearsal_completion | fable | withheld | 12/12 | 0.503 | 0.008 | 0.8 |
| rehearsal_completion | mimo | known | 12/12 | 0.5 | 0.0 | 1.0 |
| rehearsal_completion | mimo | withheld | 12/12 | 0.5 | 0.0 | 1.0 |
| rehearsal_pairs | astra | designated | 12/12 | 0.5 | 0.0 | 1.0 |
| rehearsal_pairs | fable | designated | 12/12 | 0.606 | 0.102 | 0.167 |
| rehearsal_pairs | mimo | designated | 12/12 | 0.5 | 0.0 | 1.0 |

Source-linked rehearsal scores were not computed or inspected (Section 5.4).

## Headroom review (five-fold out-of-fold empirical-prefix observer)

I[g,p] = mean(B_withheld - B_known) on held-out development parents. Prefix value = source-position loss minus source-known prefix loss.

| source | prompt | I[g,p] | prefix value |
|---|---|---:|---:|
| astra | plain | +0.0096 | +0.0767 |
| astra | fair | +0.0047 | +0.0410 |
| fable | plain | -0.0095 | +0.0759 |
| fable | fair | +0.0103 | +0.0356 |
| mimo | plain | -0.0054 | -0.0077 |
| mimo | fair | +0.0078 | -0.0016 |

| source | I[g] (prompt-averaged) |
|---|---:|
| astra | +0.0071 |
| fable | +0.0004 |
| mimo | +0.0012 |

headroom_review_required = **True** (threshold 0.02 Brier units; operational reviewer threshold, not a futility test).

Recorded decision: option (a) continue the fixed pilot with explicitly limited external evidence of disclosure headroom. Source: approvals.jsonl (inferred from Chris's go-ahead; flagged).

