# SPAR Phase 2 pilot: retained arms

Run `p2-mimo-20261008`, generated 2026-10-08T10:55:02.443500Z.

## Named attribution (secondary; small matched subset)

Parents judged: 36. Six per source x prompt at most; intervals are wide.

| quantity | estimate | 95% CI |
|---|---:|---|
| named R | -0.0590 | [-0.1499, +0.0388] |
| named P | -0.0637 | [-0.1887, +0.0718] |
| named D | -0.0544 | [-0.1146, +0.0116] |
- Per-prompt named (secondary; amendment A3) prompt plain: R -0.0544 [-0.1759, +0.0822], P -0.0463 [-0.2083, +0.1320], D -0.0625 [-0.1505, +0.0370]
- Per-prompt named (secondary; amendment A3) prompt fair: R -0.0637 [-0.1944, +0.0775], P -0.0810 [-0.2685, +0.1204], D -0.0463 [-0.1273, +0.0440]

| judge | prompt | n | choice counts | self-choice rate | balanced accuracy | multiclass Brier sum (uniform 0.667) |
|---|---|---:|---|---:|---:|---:|
| astra | plain | 18 | {'astra': 7, 'fable': 5, 'mimo': 6} | 0.389 | 0.389 | 0.667 |
| astra | fair | 18 | {'astra': 7, 'fable': 5, 'mimo': 6} | 0.389 | 0.278 | 0.667 |
| fable | plain | 18 | {'astra': 0, 'fable': 18, 'mimo': 0} | 1.000 | 0.333 | 0.679 |
| fable | fair | 18 | {'astra': 0, 'fable': 17, 'mimo': 1} | 0.944 | 0.389 | 0.671 |
| mimo | plain | 18 | {'astra': 5, 'fable': 6, 'mimo': 7} | 0.389 | 0.278 | 0.666 |
| mimo | fair | 18 | {'astra': 7, 'fable': 6, 'mimo': 5} | 0.278 | 0.278 | 0.721 |

No-sequence priors (probability assigned to each candidate):

- astra/plain/order 0: {'astra': 0.3333333333333333, 'fable': 0.3333333333333333, 'mimo': 0.3333333333333334}
- astra/plain/order 2: {'fable': 0.3333333333333333, 'astra': 0.3333333333333333, 'mimo': 0.3333333333333334}
- astra/plain/order 4: {'mimo': 0.3333333333333333, 'astra': 0.3333333333333333, 'fable': 0.3333333333333334}
- astra/plain/order 5: {'mimo': 0.3333333333333333, 'fable': 0.3333333333333333, 'astra': 0.3333333333333334}
- astra/plain/order 1: {'astra': 0.3333333333333333, 'mimo': 0.3333333333333333, 'fable': 0.3333333333333333}
- astra/fair/order 0: {'astra': 0.3333333333333333, 'fable': 0.3333333333333333, 'mimo': 0.3333333333333334}
- astra/plain/order 3: {'fable': 0.3333333333333333, 'mimo': 0.3333333333333333, 'astra': 0.3333333333333334}
- astra/fair/order 1: {'astra': 0.3333333333333333, 'mimo': 0.3333333333333333, 'fable': 0.3333333333333334}
- astra/fair/order 2: {'fable': 0.3333333333333333, 'astra': 0.3333333333333333, 'mimo': 0.3333333333333334}
- astra/fair/order 3: {'fable': 0.3333333333333333, 'mimo': 0.3333333333333333, 'astra': 0.3333333333333334}
- astra/fair/order 5: {'mimo': 0.3333333333333333, 'fable': 0.3333333333333333, 'astra': 0.3333333333333333}
- astra/fair/order 4: {'mimo': 0.3333333333333333, 'astra': 0.3333333333333333, 'fable': 0.3333333333333334}
- fable/plain/order 0: {'astra': 0.3333, 'fable': 0.3334, 'mimo': 0.3333}
- fable/plain/order 1: {'astra': 0.3333, 'mimo': 0.3333, 'fable': 0.3334}
- fable/plain/order 3: {'fable': 0.3333, 'mimo': 0.3333, 'astra': 0.3334}
- fable/plain/order 2: {'fable': 0.3333, 'astra': 0.3333, 'mimo': 0.3334}
- fable/plain/order 5: {'mimo': 0.3333, 'fable': 0.3333, 'astra': 0.3334}
- fable/fair/order 1: {'astra': 0.3333, 'mimo': 0.3333, 'fable': 0.3334}
- fable/fair/order 0: {'astra': 0.3333, 'fable': 0.3334, 'mimo': 0.3333}
- fable/fair/order 3: {'fable': 0.3333, 'mimo': 0.3333, 'astra': 0.3334}
- fable/plain/order 4: {'mimo': 0.3333, 'astra': 0.3333, 'fable': 0.3334}
- fable/fair/order 2: {'fable': 0.3333, 'astra': 0.3333, 'mimo': 0.3334}
- fable/fair/order 4: {'mimo': 0.3333, 'astra': 0.3333, 'fable': 0.3334}
- fable/fair/order 5: {'mimo': 0.3333, 'fable': 0.3334, 'astra': 0.3333}
- mimo/plain/order 0: {'astra': 0.3333333333333333, 'fable': 0.3333333333333333, 'mimo': 0.3333333333333333}
- mimo/plain/order 2: {'fable': 0.3333333333333333, 'astra': 0.3333333333333333, 'mimo': 0.3333333333333333}
- mimo/plain/order 3: {'fable': 0.3333333333333333, 'mimo': 0.3333333333333333, 'astra': 0.3333333333333333}
- mimo/plain/order 1: {'astra': 0.3333333333333333, 'mimo': 0.3333333333333333, 'fable': 0.3333333333333333}
- mimo/plain/order 4: {'mimo': 0.3333333333333333, 'astra': 0.3333333333333333, 'fable': 0.3333333333333333}
- mimo/fair/order 5: {'mimo': 0.3333333333333333, 'fable': 0.3333333333333333, 'astra': 0.3333333333333333}
- mimo/plain/order 5: {'mimo': 0.3333333333333333, 'fable': 0.3333333333333333, 'astra': 0.3333333333333333}
- mimo/fair/order 1: {'astra': 0.3333333333333333, 'mimo': 0.3333333333333333, 'fable': 0.3333333333333333}
- mimo/fair/order 3: {'fable': 0.3333333333333333, 'mimo': 0.3333333333333333, 'astra': 0.3333333333333333}
- mimo/fair/order 0: {'astra': 0.3333333333333333, 'fable': 0.3333333333333333, 'mimo': 0.3333333333333333}
- mimo/fair/order 2: {'fable': 0.3333333333333333, 'astra': 0.3333333333333333, 'mimo': 0.3333333333333333}
- mimo/fair/order 4: {'mimo': 0.3333333333333333, 'astra': 0.3333333333333333, 'fable': 0.3333333333333333}

Anonymous P/D/R on the same named blocks (descriptive only; different task): {'P': -0.015046296296296287, 'D': -0.11226851851851853, 'R': -0.06365740740740741}

Named fixtures: {'fixture_named|astra': {'n': 6, 'valid': 6, 'correct': 6}, 'fixture_named|fable': {'n': 6, 'valid': 6, 'correct': 6}, 'fixture_named|mimo': {'n': 6, 'valid': 4, 'correct': 4}}

## Historical Van Koevering replication check (gpt-3.5-turbo-0613, Azure)

| prompt | temperature | valid / attempted | mean heads | first-H rate | switch rate | longest run |
|---|---:|---|---:|---:|---:|---:|
| fair (development) | 0.0 | 36/36 | 11.0 | 1.0 | 0.871 | 2.0 |
| fair (development) | 0.8 | 36/36 | 10.861 | 1.0 | 0.807 | 2.0 |
| fair (development) | 1.5 | 36/36 | 10.639 | 0.972 | 0.751 | 2.056 |
| plain (development) | 0.0 | 36/36 | 10.278 | 1.0 | 0.792 | 2.0 |
| plain (development) | 0.8 | 36/36 | 10.722 | 1.0 | 0.788 | 2.0 |
| plain (development) | 1.5 | 34/36 | 10.706 | 0.971 | 0.769 | 2.059 |
| fair (holdout) | 0.0 | 24/24 | 11.0 | 1.0 | 0.871 | 2.0 |
| fair (holdout) | 0.8 | 24/24 | 10.75 | 0.958 | 0.798 | 2.0 |
| fair (holdout) | 1.5 | 23/24 | 10.478 | 0.957 | 0.746 | 2.043 |
| plain (holdout) | 0.0 | 24/24 | 10.292 | 1.0 | 0.792 | 2.0 |
| plain (holdout) | 0.8 | 24/24 | 10.708 | 1.0 | 0.789 | 2.0 |
| plain (holdout) | 1.5 | 24/24 | 10.625 | 0.958 | 0.774 | 2.042 |

First flip heads rate vs the paper's Table 2 (GPT-3.5; the paper's model version may differ from 0613):

| prompt | temperature | n valid | observed | paper |
|---|---:|---:|---:|---:|
| plain | 0.0 | 60 | 1.000 | 1.00 |
| plain | 0.8 | 60 | 1.000 | 1.00 |
| plain | 1.5 | 58 | 0.966 | 1.00 |
| fair | 0.0 | 60 | 1.000 | 1.00 |
| fair | 0.8 | 60 | 0.983 | 1.00 |
| fair | 1.5 | 59 | 0.966 | 0.86 |

No formal equivalence is claimed.

## Seven-to-one LASSO (`history7_runs14_v1`; offline; predicts flips, not identity)

Raw linear MSE averaged within parent then across parents. Improvement = baseline MSE minus LASSO MSE (positive = LASSO better).

| generator | prompt | dev parents | alpha | test parents | LASSO MSE | vs 0.5 | vs train mean | vs position mean [95% CI] |
|---|---|---:|---:|---:|---:|---:|---:|---|
| astra | plain | 60 | 0.0005623 | 24 | 0.1908 | +0.0592 | +0.0591 | +0.0422 [+0.0172, +0.0682] |
| astra | fair | 60 | 0.001 | 24 | 0.2167 | +0.0333 | +0.0327 | +0.0204 [-0.0246, +0.0660] |
| fable | plain | 60 | 0.0001 | 24 | 0.1344 | +0.1156 | +0.1158 | +0.0468 [+0.0177, +0.0809] |
| fable | fair | 59 | 0.001 | 24 | 0.1681 | +0.0819 | +0.0813 | +0.0201 [-0.0043, +0.0461] |
| mimo | plain | 56 | 0.003162 | 22 | 0.2109 | +0.0391 | +0.0388 | +0.0392 [+0.0135, +0.0600] |
| mimo | fair | 25 | 0.01 | 10 | 0.2217 | +0.0283 | +0.0287 | +0.0362 [+0.0271, +0.0470] |
| gpt35_0613 | plain|0.0 | 36 | 0.0005623 | 24 | 0.0804 | +0.1696 | +0.1693 | +0.0378 [-0.0032, +0.0852] |
| gpt35_0613 | plain|0.8 | 36 | 0.0003162 | 24 | 0.1135 | +0.1365 | +0.1362 | +0.0855 [+0.0632, +0.1104] |
| gpt35_0613 | plain|1.5 | 34 | 0.001778 | 24 | 0.1414 | +0.1086 | +0.1085 | +0.1184 [+0.0983, +0.1389] |
| gpt35_0613 | fair|0.0 | 36 | 0.0001 | 24 | 0.0726 | +0.1774 | +0.1759 | +0.1499 [+0.1287, +0.1710] |
| gpt35_0613 | fair|0.8 | 36 | 0.0001 | 24 | 0.1201 | +0.1299 | +0.1294 | +0.1300 [+0.0997, +0.1600] |
| gpt35_0613 | fair|1.5 | 36 | 0.001778 | 23 | 0.1542 | +0.0958 | +0.0959 | +0.1070 [+0.0879, +0.1269] |

An independent P(H)=0.9 source has optimal constant error 0.09, so error below 0.25 alone is not sequential knowledge. Predictability is not source recognition and is not self-awareness.

