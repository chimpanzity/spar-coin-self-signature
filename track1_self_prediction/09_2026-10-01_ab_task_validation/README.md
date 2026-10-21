# 09 · A/B task validation with objective questions (2026-10-01)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | `validation-indep-20261001T080148Z`; dry run `validation-20261001T075852Z-dry` |
| Models | Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), MiMo (`xiaomi/mimo-v2.6-pro`) |
| Size and cost | 720 trials, $2.39 |
| Previous / next | [← 08 FCE2](../08_2026-10-01_fce2_batch_and_independent/) · [10 Story swap →](../10_2026-10-01_story_swap/) |

## What was done
In FCE1/FCE2 the judges answered "A" far more often than "B" on attribution trials (the week handoff
gives Fable 97%, Astra 87%, MiMo 100%). If that bias reflected a general failure of the A/B format,
every attribution result would be confounded. This study reused the same 60 independent-calls pairs,
shown in both A/B orders, with two questions whose answer is fixed by the text: which sequence has
more H (`more_H`), and which has more H/T switches (`more_switches`).
3 judges × 60 pairs × 2 orders × 2 questions = 720 trials.

## Questions
- Can the judges read these 100-flip sequences correctly in the A/B format?
- Is the A-bias general or specific to source attribution?

## Results
From [`summary_by_judge_question_split.csv`](full_corpus_validation/validation-indep-20261001T080148Z/summary_by_judge_question_split.csv)
(holdout; accuracy on non-tied items):

| judge | more_H accuracy / A-rate | more_switches accuracy / A-rate |
|---|---|---|
| Astra | 1.0 / 0.5 | 1.0 / 0.5 |
| Fable | 1.0 / 0.5 | 1.0 / 0.4737 |
| MiMo | 0.8833 / 0.6167 | 0.5333 / 0.9667 |

- Astra and Fable are 100% correct on both questions in both splits, with A-rates near 0.5.
  Their A-bias on attribution trials is specific to that task, not a format failure.
- MiMo partly uses the sequences for `more_H` but answers "A" almost always for `more_switches`, so
  its near-chance attribution results elsewhere are consistent with weak use of the stimulus.

## Open questions
- If Astra and Fable can read the sequences, why do their attribution answers depend so much on the stated procedure?

## What it led to
[10 Story swap](../10_2026-10-01_story_swap/) held the sequences fixed and varied only the story about how they were produced.

## Files
- Run: [`full_corpus_validation/validation-indep-20261001T080148Z/`](full_corpus_validation/validation-indep-20261001T080148Z/) —
  `summary_by_judge_question_split.csv`, `summary_by_ordering.csv`, `trial_level.csv`, `trial_manifest.csv`,
  `raw_attempts.jsonl`, `cost_ledger.json`, `config_frozen.json`, `logs/`.
- Dry run: [`full_corpus_validation/validation-20261001T075852Z-dry/`](full_corpus_validation/validation-20261001T075852Z-dry/).
- Summary also in section 6b of [`../08_.../FCE1_FCE2_CROSS_METHOD_REPORT.md`](../08_2026-10-01_fce2_batch_and_independent/FCE1_FCE2_CROSS_METHOD_REPORT.md);
  background in the [week handoff, §5](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-09-29_to_2026-10-03.md)
  (the run needed one worker-crash resume after MiMo's provider returned `choices=None`).
- Code: [`src/spar_dynamic/full_corpus_exp1/validation.py`](../../src/spar_dynamic/full_corpus_exp1/validation.py).
- Tests: none specific to this module; shared FCE code is covered by [`tests/test_full_corpus_exp1.py`](../../tests/test_full_corpus_exp1.py).

## Re-running
From the repo root (needs `OPENROUTER_API_KEY`); `--fce-run-dir` names the FCE run whose 60 pairs are reused:

```
PYTHONPATH=src python -m spar_dynamic.full_corpus_exp1.validation run --live --yes \
    --fce-run-dir track1_self_prediction/08_2026-10-01_fce2_batch_and_independent/full_corpus_experiment_1_independent_calls/fce2-indep-truthful-20261001T070301Z
PYTHONPATH=src python -m spar_dynamic.full_corpus_exp1.validation analyze --run-dir <run folder>
```
