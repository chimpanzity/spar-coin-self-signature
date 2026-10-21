# 10 · Story swap: same sequences, three stated procedures (2026-10-01)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | new run `fce2-indep-storyswap-batch-20261001T130802Z` (dry run `fce1-20261001T130751Z-dry`); compared with `fce2-indep-truthful-20261001T070301Z` and `fce2-indep-20261001T061930Z-false-protocol` from [08](../08_2026-10-01_fce2_batch_and_independent/) |
| Models | Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), MiMo (`xiaomi/mimo-v2.6-pro`) |
| Size and cost | 480 new trials, $2.31 |
| Previous / next | [← 09 A/B task validation](../09_2026-10-01_ab_task_validation/) · [11 Phenotype prediction →](../11_2026-10-01_phenotype_prediction/) |

## What was done
A within-stimulus manipulation. The 60 independent-calls pairs, A/B orientations, judges and
questions of FCE2 were held fixed; only the protocol prefix ("how the sequences were generated")
changed. One new run told judges the sequences came from **batch** generation. It was aligned trial
by trial with the two existing runs: the **truthful** independent-calls story and the **false
history-conditioned** story. Dry-run checks asserted that no wording from the other stories leaked into the chosen prefix.

## Questions
- Does attribution follow the sequence itself, or the story about how it was produced?

## Results
From [`cross_story_summary.csv`](cross_story_indep_stimuli/cross_story_summary.csv) (holdout, SELF wording, n = 20 per judge):

| judge | truthful indep | false history | false batch | answers unchanged across all three stories |
|---|---:|---:|---:|---:|
| Astra | 0.05 | 0.4 | 0.8 | 0.35 |
| Fable | 0.9 | 0.05 | 0.0 | 0.15 |
| MiMo | 0.6 | 0.55 | 0.6 | 0.75 |

- On identical stimuli, Fable's SELF answer changes with the story on 85% of items. It is correct
  only under the true (independent-calls) story.
- Astra moves in the opposite direction: most accurate when told "batch", least when told the truth.
- MiMo is largely story-insensitive.
- For Astra and Fable the story effect is far larger than any effect of sequence content. Attribution
  follows beliefs about the stated generative process, not a reading of the trace.

## Open questions
- Is Fable's accurate answer under the true story self-knowledge, or a general belief about what
  stateless repeated calls do to any LLM? This needs the judges' predictions before they see any sequence.

## What it led to
[11 Phenotype prediction](../11_2026-10-01_phenotype_prediction/) asked each judge to forecast p(H) and
switch rate for itself and for the other models under each procedure.

## Files
- New run: [`full_corpus_experiment_1_independent_calls_story_batch/fce2-indep-storyswap-batch-20261001T130802Z/`](full_corpus_experiment_1_independent_calls_story_batch/fce2-indep-storyswap-batch-20261001T130802Z/)
  (`FULL_CORPUS_EXPERIMENT_1_REPORT.md`, CSV tables, `raw_attempts.jsonl`, `cost_ledger.json`).
- Trial-aligned three-story analysis (no API calls): [`cross_story_indep_stimuli/`](cross_story_indep_stimuli/)
  (`cross_story_summary.csv`, `cross_story_trials.csv`).
- Narrative: section 6c of [`FCE1_FCE2_CROSS_METHOD_REPORT.md`](../08_2026-10-01_fce2_batch_and_independent/FCE1_FCE2_CROSS_METHOD_REPORT.md);
  [week handoff, §6](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-09-29_to_2026-10-03.md).
- Code: [`src/spar_dynamic/full_corpus_exp1/`](../../src/spar_dynamic/full_corpus_exp1/) (`--story-method` in `__main__.py`; `cross_story.py`).
- Tests: [`tests/test_full_corpus_exp1.py`](../../tests/test_full_corpus_exp1.py) (shared FCE code; `cross_story.py` has no dedicated test).

## Re-running
From the repo root (needs `OPENROUTER_API_KEY` for the run; the cross-story step is offline):

```
PYTHONPATH=src python -m spar_dynamic.full_corpus_exp1 run --live --yes \
    --source-method independent_calls --story-method batch
PYTHONPATH=src python -m spar_dynamic.full_corpus_exp1.cross_story \
    --truthful-run <truthful run> --false-history-run <false-protocol run> \
    --false-batch-run <story-swap run> --out-dir <output folder>
```
