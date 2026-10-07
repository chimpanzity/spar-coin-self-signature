# Review guide

This page is for anyone, human or LLM, asked to evaluate this project. It
gives a reading order, maps each claim to the files that support it, marks
which runs are canonical, and lists files that are too large to fetch whole.

All links below are raw-text URLs on `main`, so a fetch tool gets plain
Markdown or CSV rather than GitHub's HTML. Base:
`https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/`

## What the project asks

LLMs asked to simulate fair coin flips produce structured, model-specific
sequences. The project asks whether a model can identify its own 100-flip
sequences, and predict their statistics, better than other models can. It is
an LLM version of Loula et al.'s point-light self-recognition paradigm.
Models: `astra` (openai/gpt-6-astra), `fable` (anthropic/claude-fable-5.1),
`mimo` (xiaomi/mimo-v2.6-pro), all called through OpenRouter.

## Reading order

**Quick review (about 60 KB of text):**

1. [README.md](https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/README.md): summary table of every study and the headline claims.
2. [Weekly handoff notes, 2026-09-29 to 10-03](https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/docs/handoffs/HANDOFF_SPAR_WEEK_2026-09-29_to_2026-10-03.md): design, numbers, bugs fixed, costs, limitations and next steps for each experiment. This is the most complete single document.
3. [FCE1/FCE2 cross-method report](https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/data/spar_dynamic/FCE1_FCE2_CROSS_METHOD_REPORT.md): all identification results side by side, plus validation, story swap and phenotype prediction.
4. [Phenotype baselines report](https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/data/spar_dynamic/PHENOTYPE_BASELINES_REPORT.md): forecast MAE and self/observer contrasts.

**Context and design history:**

5. [Corpus README](https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/corpus/README.md), [data dictionary](https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/corpus/data_dictionary.md), and [corpus source report](https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/corpus/THREE_ARCHITECTURE_SOURCE_REPORT.md).
6. [Pilots overview](https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/pilots/README.md), plus the reports for [pilot 1](https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/pilots/pilot_1_dynamic_source/results/FINAL_OVERNIGHT_REPORT.md), [pilot 2](https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/pilots/pilot_2_self_other/results/SELF_OTHER_PILOT_REPORT.md), [pilot 3](https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/pilots/pilot_3_provenance/results/PROVENANCE_SELF_ATTRIBUTION_REPORT.md) and [pilot 4](https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/pilots/pilot_4_astra_followup/results/ASTRA_PROVENANCE_REPLICATION_REPORT.md).
7. [Key references](https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/docs/references.md): Loula, Couchman, Kaneko & Tomonaga, and Van Koevering & Kleinberg, with notes on how each relates to the design. It includes the temperature-0 caveat for independent calls.
8. [Preregistration v1.0 (2026-09-21)](https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/docs/preregistration/preregistration_v1.0_2026-09-21.md). It covers the original SAME/DIFFERENT pilot only. The later experiments were not preregistered (see "Things a reviewer should check").

## Key terms

- **Procedures** (how a sequence was generated): `batch` (one call returns all 100 flips); `history_conditioned` (100 calls, each shown the prior flips; called `online` in pilots 1–4); `independent_calls` (100 calls with an identical prompt and no history).
- **Split:** each (model, procedure) cell has 20 sequences, split 10 development / 10 holdout (seed 20260930). Headline numbers are holdout.
- **FCE identification task:** two-alternative A/B. Each trial shows two sequences from different models and asks which one came from a given target. **Chance = 0.50.** SELF wording ("the same underlying model as you") is used only when judge = target. NAMED wording names the target model.
- **Contrasts** (per target, from [`analysis.py`](https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/spar_dynamic/full_corpus_exp1/analysis.py), `_contrast_target`): OBS = mean NAMED accuracy of the two non-target judges. **S = SELF − OBS** (the primary self-advantage), **O = NAMED(by target) − OBS**, **F = SELF − NAMED(by target)** (effect of the SELF wording). The primary summary is the equal-weight mean S across the three targets.

## Claims and where the evidence is

Run folders are under `data/spar_dynamic/`. Each FCE run folder contains a `FULL_CORPUS_EXPERIMENT_1_REPORT.md`, `trial_level.csv` (one row per judgment), `producer_observer_contrasts.csv`, `bootstrap_intervals.csv` and `baseline_summary.csv`.

| claim | evidence | data to recompute it |
|---|---|---|
| Procedures produce very different phenotypes (e.g. fable indep p(H) = .987) | corpus source report | `corpus/trajectories.csv`, `corpus/metrics.csv` |
| No self-advantage on history_conditioned (mean S = +0.008) | cross-method report §1–2 | `full_corpus_experiment_1/fce1-20261001T050251Z/trial_level.csv` |
| Same on batch (−0.008); indep +0.100, driven by fable (S = +0.45, CI [0.25, 0.63]) | cross-method report §1–2 | `fce2-batch-truthful-20261001T064655Z/`, `fce2-indep-truthful-20261001T070301Z/` |
| A simple centroid classifier reaches 97–100% on holdout for history_conditioned and indep (~78% on batch), far above the LLM judges | cross-method report §4 | `baseline_summary.csv`, `baseline_predictions.csv` in each run |
| A/B position bias is specific to source attribution, not format-wide | cross-method report §6b | `full_corpus_validation/validation-indep-20261001T080148Z/trial_level.csv` |
| Attribution follows the stated procedure, not the trace (fable flips SELF answers on 85% of identical items) | cross-method report §6c | `cross_story_indep_stimuli/cross_story_trials.csv`, `cross_story_summary.csv` |
| Judges predict the same p(H) and switch rate for every target model | phenotype baselines report; cross-method §6d | `full_corpus_phenotype_prediction/phenotype-20261001T165443Z/trial_level.csv` and `baseline_p_H/`; `full_corpus_phenotype_prediction_switch_rate/switchrate-20261001T175124Z/baseline_switch_rate/` |

Code for all of the above is in [`spar_dynamic/full_corpus_exp1/`](https://github.com/chimpanzity/spar-coin-self-signature/tree/main/spar_dynamic/full_corpus_exp1). Tests are in `tests/test_full_corpus_exp1.py`.

## Run index: which folders count

| folder (under `data/spar_dynamic/`) | status |
|---|---|
| `spar-stimulus-corpus-20260930T012044Z/` | **Canonical** corpus source run (the `corpus/` folder is compiled from it) |
| `full_corpus_experiment_1/fce1-20261001T050251Z/` | **Canonical** FCE1 (history_conditioned) |
| `full_corpus_experiment_1/fce1-20261001T042009Z/`, `…042738Z/`, `…044945Z/` | Failed or aborted preflights before the canonical FCE1 run. Not results |
| `full_corpus_experiment_1_batch/fce2-batch-truthful-20261001T064655Z/` | **Canonical** FCE2 batch |
| `full_corpus_experiment_1_independent_calls/fce2-indep-truthful-20261001T070301Z/` | **Canonical** FCE2 independent_calls |
| `*/fce2-*-false-protocol/` | Diagnostic only: judges were shown the history_conditioned description by mistake. Kept deliberately and reused as a "false story" condition in the story swap |
| `full_corpus_experiment_1_independent_calls_story_batch/fce2-indep-storyswap-batch-20261001T130802Z/` | **Canonical** story swap (indep stimuli, batch story) |
| `full_corpus_validation/validation-indep-20261001T080148Z/` | **Canonical** task-validation study |
| `full_corpus_phenotype_prediction/phenotype-20261001T165443Z/` | **Canonical** p(H) forecasts |
| `full_corpus_phenotype_prediction_switch_rate/switchrate-20261001T175124Z/` | **Canonical** switch-rate forecasts |
| any folder ending in `-dry` | Dry runs: prompts and manifests only, no API calls |

## Large files

These are over 500 KB. Most fetch tools will truncate them, and none are
needed to evaluate the claims:

- `data/spar_dynamic/spar-stimulus-corpus-20260930T012044Z/raw_attempts.jsonl` (11 MB, every source API attempt)
- `prompts.jsonl` in each FCE run folder (about 1 MB each, full judge prompts). For one example prompt, read the first line or see the protocol prefixes in `spar_dynamic/full_corpus_exp1/config.py`
- `corpus/flips.csv` (1.4 MB long format). `corpus/trajectories.csv` has the same data as one row per sequence
- `corpus/stimulus_corpus.xlsx` (binary, a human view of the CSVs)

## Things a reviewer should check

- **Not preregistered.** Only the original SAME/DIFFERENT pilot was preregistered, and its harness ([`pilots/pilot_0_preregistered_harness/`](https://github.com/chimpanzity/spar-coin-self-signature/tree/main/pilots/pilot_0_preregistered_harness)) was never run live. Pilots 1–4 and every corpus experiment were designed afterwards, several of them in response to earlier results. The dev/holdout split is the main safeguard.
- **Small samples.** 10 holdout triplets per cell, so the bootstrap intervals are wide. Three models.
- **Temperature.** The corpus and the judge prompts say temperature 0.0, but Astra and Fable do not support a temperature parameter on OpenRouter, so their sequences were most likely generated at default sampling. Only Mimo's were reliably at temperature 0. Details are in [references](https://raw.githubusercontent.com/chimpanzity/spar-coin-self-signature/main/docs/references.md), under Van Koevering.
- **Mimo** ran with reasoning disabled, because its internal reasoning otherwise used up the token budget. It is also the only one of eight candidate third models that passed the 100-flip batch preflight.
- **Fixed analysis bugs.** Three were fixed after an independent recomputation (A/B reversal in `trial_level.csv`, bootstrap multiplicity, baseline tie handling); see handoff §4. Results in the repo are post-fix.
- **Wording differs between documents.** The cross-method report §7 says "modest positive self-recognition emerges in independent_calls". The handoff and README conclude that this reduces to procedure-level beliefs, because fable predicts the same indep behavior for every model. Judge which reading the evidence supports.
- **Language boundary.** The preregistration commits to describing results as "behavioral self-signature" or "own-model discrimination advantage", not self-recognition or introspection.
- **Costs.** Itemized in the handoff, about $38 total.

## Useful feedback

- Do the conclusions follow from the data, especially the procedure-belief interpretation?
- Are there confounds or alternative explanations not addressed?
- Which next experiment would most reduce uncertainty? The handoff lists five candidates.
