# 08 · FCE2: the same test on batch and independent-calls trajectories (2026-10-01)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | truthful: `fce2-batch-truthful-20261001T064655Z`, `fce2-indep-truthful-20261001T070301Z`; false-protocol diagnostics: `fce2-batch-20261001T060352Z-false-protocol`, `fce2-indep-20261001T061930Z-false-protocol`; dry runs `fce1-20261001T060343Z-dry`, `fce1-20261001T064619Z-dry` |
| Models | Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), MiMo (`xiaomi/mimo-v2.6-pro`) |
| Size and cost | 4 × 480 trials; about $12.57 in total per the week handoff (run ledgers: $2.20, $4.28, $2.66, $2.84; the handoff's truthful figures include preflights) |
| Previous / next | [← 07 FCE1](../07_2026-10-01_fce1_history_conditioned/) · [09 A/B task validation →](../09_2026-10-01_ab_task_validation/) |

## What was done
The FCE1 design applied to the batch and independent_calls cells of the corpus. The first runs
reused FCE1's protocol prefix, so judges were told the history-conditioned procedure while seeing
batch or independent-calls sequences. After the fix (per-method prefixes) both methods were rerun
truthfully; the uncorrected runs were kept, renamed `-false-protocol`, as a diagnostic.

## Questions
- Does a producer advantage appear when the signal is weaker (batch) or much stronger (independent calls)?
- Does what judges are told about the procedure change their answers on the same sequences?

## Results
From [`FCE1_FCE2_CROSS_METHOD_REPORT.md`](FCE1_FCE2_CROSS_METHOD_REPORT.md) (holdout, equal-weight mean S across targets):

| method | mean S |
|---|---:|
| history_conditioned, truthful (FCE1) | 0.008 |
| batch, truthful | −0.008 |
| independent_calls, truthful | **0.100** |
| batch, told history_conditioned | −0.008 |
| independent_calls, told history_conditioned | −0.150 |

- The independent-calls effect comes almost entirely from Fable: SELF on its own sequences 0.90,
  NAMED 0.75, observers 0.45, S = +0.45 (holdout 95% CI [0.25, 0.63]).
- Astra is the reverse under the truthful independent-calls story: SELF 0.05, NAMED 0.00 on its own sequences.
- On the same independent-calls sequences, Fable's SELF accuracy falls from 0.90 (truthful) to 0.05
  (told history_conditioned). Mean S changes sign (+0.100 → −0.150) with only the description changed.
- Centroid baselines: 1.000 on holdout for independent_calls; 0.783 (marginal) / 0.767 (full) for batch.

## Open questions
- Is the heavy A-response bias on these attribution trials a format failure? → [09](../09_2026-10-01_ab_task_validation/)
- Is Fable reading its own trace, or applying a belief about what the stated procedure produces? → [10](../10_2026-10-01_story_swap/), [11](../11_2026-10-01_phenotype_prediction/)

## What it led to
Before interpreting Fable's effect, the A/B format was checked with objective questions on the same
pairs: [09 A/B task validation](../09_2026-10-01_ab_task_validation/).

**Bug fixes.** A reviewer recomputed the results and found three analysis bugs, fixed in commit
`d2847ef`: (1) `pairs.build_pairs()` used Python's randomised `hash()`, so the analysis re-run had A/B
reversed in 272/480 rows of `trial_level.csv`; (2) the bootstrap counted duplicated triplets once,
making intervals too narrow; (3) the marginal baseline dropped ties instead of giving half credit.
The cross-method report post-dates the fixes. The [Phase 2 summary](../12_2026-10-07_phase2_qwen/PHASE2_PILOT_RESULTS_2026-10-08.md)
later noted `hash()`-based seeds remaining in the FCE bootstrap (`full_corpus_exp1/analysis.py`), so those intervals are not reproducible across processes.

## Files
- Cross-method summary (FCE1, FCE2, and later 09–11 sections): [`FCE1_FCE2_CROSS_METHOD_REPORT.md`](FCE1_FCE2_CROSS_METHOD_REPORT.md).
- Batch runs: [`full_corpus_experiment_1_batch/`](full_corpus_experiment_1_batch/); independent-calls runs:
  [`full_corpus_experiment_1_independent_calls/`](full_corpus_experiment_1_independent_calls/). Each run folder has
  `FULL_CORPUS_EXPERIMENT_1_REPORT.md`, `validation_report.md`, CSV tables, `raw_attempts.jsonl`, `cost_ledger.json`;
  false-protocol folders also have `NOTE_FALSE_PROTOCOL.md`.
- Background: [week handoff, §3–4](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-09-29_to_2026-10-03.md).
- Code: [`src/spar_dynamic/full_corpus_exp1/`](../../src/spar_dynamic/full_corpus_exp1/) (`combined_report.py` builds the cross-method report).
- Tests: [`tests/test_full_corpus_exp1.py`](../../tests/test_full_corpus_exp1.py).

## Re-running
From the repo root (needs `OPENROUTER_API_KEY`):

```
PYTHONPATH=src python -m spar_dynamic.full_corpus_exp1 run --live --yes --source-method batch
PYTHONPATH=src python -m spar_dynamic.full_corpus_exp1 run --live --yes --source-method independent_calls
```

`--story-method <method>` shows a different procedure description than the true one (the false-protocol
manipulation). The cross-method report is rebuilt with `python -m spar_dynamic.full_corpus_exp1.combined_report` (see its `--help`).
