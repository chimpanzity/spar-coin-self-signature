# SPAR Phase 2 pilot: retained arms

Run `p2-20261007`, generated 2026-10-08T04:28:28.591048Z.

## Named attribution (secondary; small matched subset)

Parents judged: 18. Six per source x prompt at most; intervals are wide.

| quantity | estimate | 95% CI |
|---|---:|---|
| named R | NA | [NA] |
| named P | NA | [NA] |
| named D | NA | [NA] |
- Per-prompt named (secondary; amendment A3) prompt plain: R -0.0405 [-0.1725, +0.0938], P -0.0694 [-0.2361, +0.0950], D -0.0116 [-0.1204, +0.0995]
- Per-prompt named (secondary; amendment A3) prompt fair: not estimable

| judge | prompt | n | choice counts | self-choice rate | balanced accuracy | multiclass Brier sum (uniform 0.667) |
|---|---|---:|---|---:|---:|---:|
| astra | plain | 18 | {'astra': 6, 'fable': 7, 'qwen': 5} | 0.333 | 0.278 | 0.667 |
| fable | plain | 18 | {'astra': 3, 'fable': 10, 'qwen': 5} | 0.556 | 0.611 | 0.574 |
| qwen | plain | 18 | {'astra': 6, 'fable': 6, 'qwen': 6} | 0.333 | 0.333 | 0.710 |

No-sequence priors (probability assigned to each candidate):

- astra/plain/order 3: {'fable': 0.3333333333333333, 'qwen': 0.3333333333333333, 'astra': 0.3333333333333333}
- astra/plain/order 1: {'astra': 0.3333333333333333, 'qwen': 0.3333333333333333, 'fable': 0.3333333333333334}
- astra/plain/order 0: {'astra': 0.3333333333333333, 'fable': 0.3333333333333333, 'qwen': 0.3333333333333334}
- astra/plain/order 5: {'qwen': 0.3333333333333333, 'fable': 0.3333333333333333, 'astra': 0.3333333333333334}
- astra/fair/order 0: {'astra': 0.3333333333333333, 'fable': 0.3333333333333333, 'qwen': 0.3333333333333334}
- astra/plain/order 4: {'qwen': 0.3333333333333333, 'astra': 0.3333333333333333, 'fable': 0.3333333333333334}
- astra/plain/order 2: {'fable': 0.3333333333333333, 'astra': 0.3333333333333333, 'qwen': 0.3333333333333334}
- astra/fair/order 1: {'astra': 0.3333333333333333, 'qwen': 0.3333333333333333, 'fable': 0.3333333333333334}
- astra/fair/order 3: {'fable': 0.3333333333333333, 'qwen': 0.3333333333333333, 'astra': 0.3333333333333334}
- astra/fair/order 4: {'qwen': 0.3333333333333333, 'astra': 0.3333333333333333, 'fable': 0.3333333333333334}
- astra/fair/order 5: {'qwen': 0.3333333333333333, 'fable': 0.3333333333333333, 'astra': 0.3333333333333334}
- astra/fair/order 2: {'fable': 0.3333333333333333, 'astra': 0.3333333333333333, 'qwen': 0.3333333333333334}
- fable/plain/order 2: {'fable': 0.3333, 'astra': 0.3333, 'qwen': 0.3334}
- fable/plain/order 0: {'astra': 0.3333, 'fable': 0.3333, 'qwen': 0.3334}
- fable/plain/order 1: {'astra': 0.3333, 'qwen': 0.3333, 'fable': 0.3334}
- fable/plain/order 3: {'fable': 0.3333, 'qwen': 0.3333, 'astra': 0.3334}
- fable/plain/order 4: {'qwen': 0.3333, 'astra': 0.3333, 'fable': 0.3334}
- fable/fair/order 0: {'astra': 0.3333, 'fable': 0.3333, 'qwen': 0.3334}
- fable/plain/order 5: {'qwen': 0.3333, 'fable': 0.3333, 'astra': 0.3334}
- fable/fair/order 2: {'fable': 0.3333, 'astra': 0.3333, 'qwen': 0.3334}
- fable/fair/order 1: {'astra': 0.3333, 'qwen': 0.3333, 'fable': 0.3334}
- qwen/plain/order 1: {'astra': 0.3333333333333333, 'qwen': 0.3333333333333333, 'fable': 0.3333333333333333}
- qwen/plain/order 0: {'astra': 0.3333333333333333, 'fable': 0.3333333333333333, 'qwen': 0.3333333333333333}
- qwen/plain/order 4: {'qwen': 0.5, 'astra': 0.25, 'fable': 0.25}
- fable/fair/order 4: {'qwen': 0.3333, 'astra': 0.3333, 'fable': 0.3334}
- qwen/plain/order 2: {'fable': 0.3333333333333333, 'astra': 0.3333333333333333, 'qwen': 0.3333333333333333}
- fable/fair/order 3: {'fable': 0.3333, 'qwen': 0.3333, 'astra': 0.3334}
- fable/fair/order 5: {'qwen': 0.3333, 'fable': 0.3333, 'astra': 0.3334}
- qwen/plain/order 3: {'fable': 0.3333333333333333, 'qwen': 0.3333333333333333, 'astra': 0.3333333333333333}
- qwen/plain/order 5: {'qwen': 0.5, 'fable': 0.25, 'astra': 0.25}
- qwen/fair/order 4: {'qwen': 0.5, 'astra': 0.25, 'fable': 0.25}
- qwen/fair/order 5: {'qwen': 0.5, 'fable': 0.25, 'astra': 0.25}
- qwen/fair/order 0: {'astra': 0.3333333333333333, 'fable': 0.3333333333333333, 'qwen': 0.3333333333333333}
- qwen/fair/order 1: {'astra': 0.3333333333333333, 'qwen': 0.3333333333333333, 'fable': 0.3333333333333333}
- qwen/fair/order 3: {'fable': 0.3333333333333333, 'qwen': 0.3333333333333333, 'astra': 0.3333333333333333}
- qwen/fair/order 2: {'fable': 0.3333333333333333, 'astra': 0.3333333333333333, 'qwen': 0.3333333333333333}

Anonymous P/D/R on the same named blocks (descriptive only; different task): None

Named fixtures: {'fixture_named|astra': {'n': 6, 'valid': 6, 'correct': 6}, 'fixture_named|fable': {'n': 6, 'valid': 6, 'correct': 6}, 'fixture_named|qwen': {'n': 6, 'valid': 5, 'correct': 3}}

## Historical Van Koevering replication check (gpt-3.5-turbo-0613, Azure)

| prompt | temperature | valid / attempted | mean heads | first-H rate | switch rate | longest run |
|---|---:|---|---:|---:|---:|---:|
| fair (development) | 0.0 | 36/36 | 11.0 | 1.0 | 0.876 | 2.0 |
| fair (development) | 0.8 | 35/36 | 10.657 | 1.0 | 0.806 | 2.0 |
| fair (development) | 1.5 | 33/36 | 10.576 | 0.97 | 0.748 | 2.061 |
| plain (development) | 0.0 | 36/36 | 10.389 | 1.0 | 0.784 | 2.0 |
| plain (development) | 0.8 | 36/36 | 10.722 | 1.0 | 0.792 | 2.0 |
| plain (development) | 1.5 | 36/36 | 10.778 | 1.0 | 0.763 | 2.0 |
| fair (holdout) | 0.0 | 24/24 | 11.0 | 1.0 | 0.875 | 2.0 |
| fair (holdout) | 0.8 | 24/24 | 10.708 | 1.0 | 0.792 | 2.0 |
| fair (holdout) | 1.5 | 23/24 | 10.739 | 1.0 | 0.741 | 2.043 |
| plain (holdout) | 0.0 | 24/24 | 10.333 | 1.0 | 0.785 | 2.0 |
| plain (holdout) | 0.8 | 24/24 | 10.917 | 1.0 | 0.774 | 2.0 |
| plain (holdout) | 1.5 | 24/24 | 10.708 | 1.0 | 0.77 | 2.0 |

First flip heads rate vs the paper's Table 2 (GPT-3.5; the paper's model version may differ from 0613):

| prompt | temperature | n valid | observed | paper |
|---|---:|---:|---:|---:|
| plain | 0.0 | 60 | 1.000 | 1.00 |
| plain | 0.8 | 60 | 1.000 | 1.00 |
| plain | 1.5 | 60 | 1.000 | 1.00 |
| fair | 0.0 | 60 | 1.000 | 1.00 |
| fair | 0.8 | 59 | 1.000 | 1.00 |
| fair | 1.5 | 56 | 0.982 | 0.86 |

No formal equivalence is claimed.

## Seven-to-one LASSO (`history7_runs14_v1`; offline; predicts flips, not identity)

Raw linear MSE averaged within parent then across parents. Improvement = baseline MSE minus LASSO MSE (positive = LASSO better).

| generator | prompt | dev parents | alpha | test parents | LASSO MSE | vs 0.5 | vs train mean | vs position mean [95% CI] |
|---|---|---:|---:|---:|---:|---:|---:|---|
| astra | plain | 60 | 0.0005623 | 24 | 0.1840 | +0.0660 | +0.0664 | +0.0454 [+0.0328, +0.0588] |
| astra | fair | 60 | 0.0003162 | 24 | 0.2005 | +0.0495 | +0.0495 | +0.0127 [-0.0243, +0.0497] |
| fable | plain | 60 | 0.0001778 | 24 | 0.1081 | +0.1419 | +0.1419 | +0.0298 [+0.0047, +0.0610] |
| fable | fair | 59 | 0.0005623 | 24 | 0.1679 | +0.0821 | +0.0814 | -0.0030 [-0.0311, +0.0320] |
| qwen | plain | 59 | 0.0001778 | 24 | 0.0573 | +0.1927 | +0.1914 | +0.0736 [+0.0354, +0.1195] |
| qwen | fair | 6 | | | insufficient | | | |
| gpt35_0613 | plain|0.0 | 36 | 0.0001 | 24 | 0.0870 | +0.1630 | +0.1628 | +0.0552 [+0.0293, +0.0834] |
| gpt35_0613 | plain|0.8 | 36 | 0.0001 | 24 | 0.1124 | +0.1376 | +0.1368 | +0.0718 [+0.0507, +0.0934] |
| gpt35_0613 | plain|1.5 | 36 | 0.0005623 | 24 | 0.1329 | +0.1171 | +0.1169 | +0.0929 [+0.0792, +0.1076] |
| gpt35_0613 | fair|0.0 | 36 | 0.0001 | 24 | 0.0709 | +0.1791 | +0.1776 | +0.1437 [+0.0960, +0.1914] |
| gpt35_0613 | fair|0.8 | 35 | 0.0003162 | 24 | 0.1283 | +0.1217 | +0.1214 | +0.1003 [+0.0751, +0.1285] |
| gpt35_0613 | fair|1.5 | 33 | 0.001778 | 23 | 0.1480 | +0.1020 | +0.1017 | +0.1030 [+0.0860, +0.1189] |

An independent P(H)=0.9 source has optimal constant error 0.09, so error below 0.25 alone is not sequential knowledge. Predictability is not source recognition and is not self-awareness.

