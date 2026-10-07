# SPAR coin-simulation project — week of 2026-09-29 to 2026-10-03

Chris Martin, written 2026-10-03.

## Abstract

This week we built a reusable behavioral stimulus corpus for LLM coin-flip simulation and ran a connected series of eight experiments probing whether LLMs can identify their own behavioral traces, attribute them to themselves, and predict the statistical features of their own outputs. The corpus (**SPAR Stimulus Corpus, pilot 5**) contains 180 trajectories: 3 models (`openai/gpt-6-astra`, `anthropic/claude-fable-5.1`, `xiaomi/mimo-v2.6-pro`) × 3 generation procedures (single-call batch, history-conditioned sequential calls, stateless independent calls) × 20 replicates of 100 flips. We added a frozen stratified 10 / 10 development / holdout split within every (model, procedure) cell. On top of this corpus we ran: FCE1 (protocol-informed producer-vs-observer identification on history-conditioned trajectories, 480 trials), FCE2 batch and independent-calls (480 each), a task-validation study with objective A/B comparisons (720 trials), a within-stimulus three-story psychophysics manipulation (480 trials of indep stimuli with a falsely-asserted batch story, plus the two already-collected story conditions), and two phenotype-prediction baselines in which judges forecast p(H) and switch-rate before seeing any sequence (360 trials each). The overall picture: **no clean privileged self-recognition in any model, but a strong procedure-belief effect — judges' attribution of a stimulus is dominated by what story they are told about how it was generated, and both astra and fable hold differentiated procedure-level beliefs about LLM behavior that they apply uniformly across target models**. Fable's procedure beliefs happen to be approximately calibrated to its own behavior; astra's are not. All work was developed on branch `fce1` of `chimpanzity/spar-coin-self-signature` and merged into `main` on 2026-10-07. Total paid API spend ~$34 against a $100 cumulative cap (see Cost accounting). Eight commits on `fce1` beyond the corpus publication.

---

## Background and goal

The project is an LLM analogue of Loula et al.'s point-light self-recognition paradigm. Point-light stimuli strip away surface identity cues while preserving dynamic structure. In Loula's work, humans show privileged recognition of their own point-light motion. The LLM analogue is 100-flip binary sequences produced by an LLM asked to simulate fair-coin flips: surface identity is stripped, but behavioral dynamics (p_H, switch rate, run structure, bigram transitions) carry model-specific signatures. The scientific questions:

1. Can a model simulate a coin flip and simulate multiple coin flips?
2. Can it predict the statistical properties of its own simulations?
3. Can it recognize its own simulations as its own, especially better than other equally informed observers?

A positive self-advantage would be consistent with (though not proof of) functional self-knowledge about one's own output distribution. The question has direct alignment relevance: if a model can accurately claim what it would produce, we can trust some kinds of self-reports; if it can't, we can't.

## Pre-week context — pilots 1 through 4 (archived)

Prior to this week we ran four smaller pilots at 50 flips with two architectures (`batch` and `online` i.e. history-conditioned) and three models (`astra`, `fable`, `qwen`). Their findings in brief:

- Pilot 1: source phenotypes exist; a nearest-centroid classifier reaches ~70% on batch, ~93% on online.
- Pilot 2: LLM judges (SAME/DIFFERENT task) reach ~92% / ~83% on online, but no selective own-model advantage.
- Pilot 3: SELF/OTHER attribution is poor — astra calls almost everything OTHER. A `told-online` cue selectively increased astra's SELF rate on its own.
- Pilot 4: Astra-only follow-up with a no-provenance control; the pilot-3 selective effect did not replicate.

These are preserved under `spar-coin-self-signature/pilots/pilot_{1,2,3,4}_*/` with their original data, prompts, and reports.

## This week's work, in order

### 1. SPAR Stimulus Corpus (pilot 5)

**Goal.** Build a frozen reference corpus large enough and clean enough that every subsequent experiment reuses the same 180 trajectories with a fixed dev/holdout split.

**Design.** 3 models × 3 procedures × 20 trajectories × 100 flips.
- `batch`: single API call produces the whole 100-flip sequence via within-completion autoregression.
- `history_conditioned`: 100 sequential calls, each sees the complete prior H/T history.
- `independent_calls`: 100 sequential calls, each receives an identical stateless prompt with no history.

**Model-selection story.** Original spec proposed `mistral-small`. Seven candidate third models (mistral-small, mistral-medium, ministral-8b, gemma-3-27b-it, llama-3.3-70b, llama-4-maverick, deepseek-chat-v3.1, nemotron-3-super-120b) failed a strict 100-char batch preflight. `xiaomi/mimo-v2.6-pro` was the only candidate that could produce `^[HT]{100}$` reliably at all; it has a very low batch success rate (~1 in 5) and needed per-trajectory retry headroom (CORPUS_BATCH_MAX_ATTEMPTS = 25) plus `reasoning: {enabled: false}` to disable its internal reasoning (which otherwise exhausts token budgets).

**Headline phenotypes** (observed from the committed corpus, mean over 20 sequences per cell):

| model | procedure | p(H) | switch_rate | longest_run |
|---|---|---:|---:|---:|
| astra | batch | 0.495 | 0.620 | 3.6 |
| astra | hist | 0.460 | 0.632 | 4.6 |
| astra | indep | 0.389 | 0.473 | 7.7 |
| fable | batch | 0.5065 | 0.643 | 3.0 |
| fable | hist | 0.744 | 0.476 | 24.3 |
| fable | indep | **0.987** | **0.026** | **78.0** |
| mimo | batch | 0.4875 | 0.624 | 3.5 |
| mimo | hist | 0.633 | 0.498 | 7.3 |
| mimo | indep | 0.860 | 0.233 | 22.2 |

**Takeaway.** The three procedures produce radically different phenotypes for the same nominal task. `batch` gives near-fair coins for all three models. `independent_calls` collapses into saturated self-flipping: fable gives ~99% H with a mean longest run of 78 out of 100. The behavioral signal that any later recognition experiment is looking for is extremely clear in independent_calls, present in history_conditioned, and nearly absent in batch.

**Outputs.** `corpus/trajectories.csv` (180 rows canonical), `corpus/flips.csv` (18,000 rows long-format), `corpus/metrics.csv` (540 rows at prefix 20/50/100), `corpus/stimulus_corpus.xlsx` (human view), `corpus/manifest.json` (seed = 20260930 for dev/holdout split), plus `data/spar_dynamic/spar-stimulus-corpus-20260930T012044Z/` (full raw provenance including `raw_attempts.jsonl` and per-trajectory JSON).

**Cost.** $7.42 for the full source-generation run.

### 2. FCE1 — producer-vs-observer identification on history-conditioned trajectories

**Goal.** The reviewer's primary question: on the method with the strongest known source signal (history-conditioned, 93% classifier accuracy at 50 flips), do fresh instances of a model identify that model's own trajectories better than other equally informed judges?

**Design.** Within each split, 10 source triplets × 3 pair types = 30 pairs. Each pair asked twice (one target version per source) × (3 NAMED judges + 1 SELF for the target-producer) = 8 trials per pair. 60 pairs × 8 = 480 trials. Pair construction and A/B balance frozen with seed 2026093001.

**Prompt structure.** A shared protocol-prefix tells the judge the exact generation procedure. A NAMED suffix asks "which sequence was generated by `{TARGET_NAME}`?"; a SELF suffix (only when judge == target) asks "which sequence was generated by the same underlying model as you?" Strict A/B parser.

**Headline (holdout).** Equal-weight mean S across targets = **+0.008**. Essentially zero combined SELF-vs-observer advantage. Astra S = −0.05, fable S = 0.00, mimo S = +0.075. Centroid baselines on p(H) alone reach 96.7% (holdout). The behavioral signal is clearly present and solvable by a trivial classifier; LLM judges' holdout NAMED accuracies range from 0.10 to 0.70, mostly at or below the 50% chance level of this two-alternative task.

**One strong observer finding.** Fable NAMED-on-astra = 0.70, NAMED-on-mimo = 0.60, but NAMED-on-fable = 0.15. Fable is the best general observer for other models yet very poor at identifying its own trajectories.

**Cost.** Preflight $0.08 + scored $2.84 = $2.92.

### 3. FCE2 — same design on batch and independent-calls trajectories

**Goal.** Does changing to a stronger-signal method (indep) or a weaker-signal method (batch) change the result?

**Protocol-mismatch bug.** First FCE2 runs used the FCE1 shared protocol prefix (which describes history-conditioned generation) even though the trajectories on display came from batch or independent_calls. Judges were truthfully told the wrong procedure. Fixed by adding per-method prefixes (`SHARED_PROTOCOL_PREFIX_BATCH`, `SHARED_PROTOCOL_PREFIX_HISTORY_CONDITIONED`, `SHARED_PROTOCOL_PREFIX_INDEPENDENT_CALLS`), reruns renamed the uncorrected runs with a `-false-protocol` suffix and preserved them as a diagnostic.

**Truthful-protocol headline (holdout mean S):**
- `history_conditioned`: +0.008
- `batch`: −0.008
- `independent_calls`: **+0.100**

The independent-calls positive mean S is driven almost entirely by fable: fable SELF-on-fable = 0.90, fable NAMED-on-fable = 0.75, fable S = +0.45 (holdout 95% CI [0.25, 0.63]). Astra does the opposite — astra NAMED-on-astra = 0.00 under truthful indep story, SELF-on-astra = 0.05.

**Cost.** Preflight + 480 batch truthful = $2.70; preflight + 480 indep truthful = $4.37; plus two false-protocol runs ($2.66, $2.84). About $12.57 total for FCE2 across all four variants.

### 4. Three analysis bugs fixed (reviewer-flagged)

A careful reviewer caught three bugs by independent recomputation.
1. **A/B reversal in `trial_level.csv` (272/480 rows).** `pairs.build_pairs()` used Python's randomized `hash()` for per-cell position-balance shuffling. The live run and the analyze re-run saw different shuffle orders. Fix: replace `hash()` with a stable integer, and have `cmd_analyze` load the saved live-run `trial_manifest.csv` instead of rebuilding trials.
2. **Narrow bootstrap CIs.** `_bootstrap_split` collapsed resampled items into a set, so duplicated triplets counted once instead of weighted by multiplicity. Fixed to a count-dict with weighted MAE. Astra S CI on batch holdout goes from a too-narrow [−0.33, 0.0] to [−0.40, +0.10], matching the reviewer's independent recomputation.
3. **Marginal baseline tie handling.** The baseline accuracy excluded ties entirely. Spec section 19 requires half-credit. Fixed: `accuracy = (correct + 0.5 × ties) / n_total`; `accuracy_conditional_on_nontie` added as a side column. Holdout marginal goes from 0.84 (conditional) to 0.783 (half-credit), matching the reviewer's number exactly.

### 5. Task-validation study — is the A-bias format-wide or source-attribution-specific?

**Goal.** FCE1/FCE2 showed heavy A-bias in judge responses (fable 97% A, astra 87%, mimo 100%). If the bias is a general A/B format failure, every result above is confounded. If it's specific to source attribution, the earlier results stand.

**Design.** Same 60 independent-calls pairs. Both natural and reversed A/B orderings. Two objectively-answerable questions: "which has more H outcomes?" and "which has more switches between H and T?" Deterministic ground truth. 3 judges × 60 pairs × 2 orderings × 2 questions = 720 trials.

**Headline:**

| judge | more_H accuracy | more_H A-rate | more_switches accuracy | more_switches A-rate |
|---|---:|---:|---:|---:|
| astra | 1.00 | 0.50 | 1.00 | 0.50 |
| fable | 1.00 | ~0.50 | 1.00 | ~0.49 |
| mimo | 0.88 | 0.62 | 0.53 | 0.97 |

Astra and fable: 100% accuracy, perfectly balanced A/B response rates. **Their source-attribution A-bias is task-specific, not format-wide.** Mimo has a feature-dependent bias: it uses the p(H) signal when it's salient (~88% on `more_H`) but collapses to always-A on switch-counting (`more_switches` ~53% + 97% A-rate).

**Cost.** $2.39 (incl. one worker crash + resume; `_call_judge` was patched to tolerate `choices=None` responses, which xiaomi/fp8 returned once).

### 6. Story-swap — within-stimulus three-story psychophysics

**Goal.** The reviewer's clean follow-up design. Same stimuli (independent_calls), three different stories about how those stimuli were generated.

**Design.** Reuse the exact same 60 pairs and A/B orientations as FCE2-indep-truthful. Decouple `source_method` (which trajectories) from `story_method` (which protocol prefix is shown). Launch one new run (indep stimuli × false batch story) and compare to the two already-collected story conditions (truthful indep, false history). Negative story-leak assertions in dry-run (no tokens from "wrong" prefixes may appear in the chosen prefix).

**Holdout SELF accuracy on the exact same 60 pairs:**

| judge | truthful indep | false hist | false batch | % answers consistent across stories |
|---|---:|---:|---:|---:|
| astra | 0.05 | 0.40 | 0.80 | 0.35 |
| fable | 0.90 | 0.05 | 0.00 | 0.15 |
| mimo | 0.60 | 0.55 | 0.60 | 0.75 |

The sign and magnitude of the attribution flip is enormous. Fable flips its SELF answer on 85% of the exact-same-stimulus items depending on which story we tell. Astra ramps the opposite direction. **Attribution is dominated by beliefs about the stated generative process, not by direct reading of the behavioral trace.**

**Cost.** $2.31 for the new 480-trial batch-story-on-indep-stimuli run.

### 7. Phenotype prediction — p(H) forecasts before any sequence is shown

**Goal.** If a judge really has a differentiated self-model (vs just procedure-level task-knowledge), its predicted p(H) for ITS OWN output under procedure X should be more accurate than its predicted p(H) for ANOTHER model's output under procedure X.

**Design.** 3 judges × 2 wordings (SELF when judge==target, NAMED otherwise) × 3 targets × 3 procedures × 10 replicates at temperature 0.7 = 360 trials. Strict parser primary; a documented loose "last-line float" parser recovers abandoned trials transparently (fable produced reasoning + a terminal numeric answer on ~20 cells).

**Headline SELF predictions vs actual p(H):**

| judge | batch | hist | indep |
|---|---|---|---|
| astra | 0.50 / 0.495 | 0.50 / 0.46 | **1.00 / 0.389** (strongly miscalibrated) |
| fable | 0.51 / 0.507 | 0.50 / 0.744 | **1.00 / 0.987** (well calibrated) |
| mimo | 0.50 / 0.487 | 0.50 / 0.633 | 0.50 / 0.860 |

**Critical NAMED result (loose parser).** Fable predicts p(H) ≈ 1 under indep for EVERY target model (fable 1.00, astra 1.00, mimo 0.995). Astra does the same (fable 1.00, astra 0.83, mimo 1.00). The "self-model" is really a **procedure-level task-model applied uniformly to any LLM**. Fable's happens to match fable's actual behavior; astra's doesn't. This completely reframes the story-swap finding: it's not protocol-conditional self-knowledge, it's protocol-conditional task-knowledge.

**Cost.** $2.81.

### 8. Baselines — switching-rate forecasts and self/observer MAE contrasts

**Goal.** The reviewer's follow-up: same elicitation framework, but ask about switch rate instead of p(H). Report MAE and self/observer contrasts for both baselines.

**Design.** Baseline 1 reuses the existing p(H) forecast run (no new API calls). Baseline 2 is a fresh 360-trial switch-rate run with the same framework.

**Observed switch rates** (per model × procedure, mean over 20 sequences):

| model | batch | hist | indep |
|---|---:|---:|---:|
| astra | 0.620 | 0.632 | 0.473 |
| fable | 0.643 | 0.476 | **0.026** |
| mimo | 0.624 | 0.498 | 0.233 |

**SELF MAE (loose parser), both features:**

| | p(H) batch | p(H) hist | p(H) indep | switch batch | switch hist | switch indep |
|---|---:|---:|---:|---:|---:|---:|
| astra | 0.005 | 0.040 | 0.611 | 0.057 | 0.088 | 0.473 |
| fable | 0.010 | 0.244 | 0.013 | 0.026 | 0.272 | 0.026 |
| mimo | 0.013 | 0.133 | 0.360 | 0.128 | 0.003 | 0.237 |

**Only fable has a positive self_advantage** on both features under indep (p(H) +0.237, switch +0.167). Astra and mimo under indep are **worse** at predicting their own behavior than other judges are. SELF-vs-OWN_NAMED differences cluster near zero: SELF wording does not elicit a privileged channel.

**Cost.** $2.81 for baseline 2.

## Overall findings synthesis

1. **No clean privileged self-recognition in any model.** Mean S across targets is near zero for history_conditioned and batch, and only positive for indep because of fable alone.
2. **Attribution is dominated by procedure-belief rather than trace-reading.** On the exact same 100-char stimulus, telling a judge a different story about how the stimulus was produced flips its attribution on up to 85% of items.
3. **The self-model is a procedure-model.** Both astra and fable predict identical p(H) and switch_rate for every target model under a given procedure. Fable's prediction happens to match fable's own actual behavior under indep; astra's doesn't. There is no evidence of model-specific introspection; there is evidence of procedure-level task knowledge that varies in calibration across judges.
4. **Position bias on source-attribution is task-specific, not format-wide.** The validation study rules out the simplest "A/B format is broken" explanation.
5. **The behavioral signal is externally decodable.** Centroid baselines reach 97–100% on holdout for history_conditioned and independent_calls (about 78% on batch). The LLM judges fail to use what a trivial classifier succeeds with.
6. **Non-redundant feature structure.** p(H) ≈ 0.49 can coexist with switch_rate = 0.62 (astra batch).

## What's defensible, what isn't

- Defensible: the within-stimulus three-story psychophysics finding; the phenotype-prediction procedure-belief finding; the position-bias task-specificity finding; the overall null for self-recognition; the fable-vs-astra miscalibration asymmetry.
- NOT defensible: any claim of privileged introspection or special SELF channel; "fable recognizes itself" (reduces to procedure beliefs); strong between-model generalization (only three models).

## Repository state

- Repo: `chimpanzity/spar-coin-self-signature`. Developed on branch `fce1`; fast-forwarded into `main` and pushed on 2026-10-07.
- Previous `main` head: `00e5cf6` (canonical corpus publication).
- Commits on `fce1` ahead of main:
  - `23ef24e` FCE1 implementation + first run
  - `c5d7199` FCE2 (uncorrected, pre-protocol fix)
  - `a94f620` gitignore zip packages
  - `3adc0de` FCE2 protocol fix + truthful reruns
  - `d2847ef` three bug fixes + task-validation study
  - `f6ec50d` story-swap + cross-story analysis
  - `33183d2` phenotype prediction (p_H)
  - `08800b9` baselines (p_H + switch_rate) + brief report

## File map (key artifacts)

- `corpus/` — canonical stimulus bank + XLSX (top-level, visible to repo visitors)
- `pilots/pilot_{1..4}_*/` — archived prior pilots
- `data/spar_dynamic/spar-stimulus-corpus-20260930T012044Z/` — pilot 5 raw run
- `data/spar_dynamic/full_corpus_experiment_1/fce1-20261001T050251Z/` — FCE1 history-conditioned
- `data/spar_dynamic/full_corpus_experiment_1_batch/fce2-batch-truthful-*/` — FCE2 batch (truthful)
- `data/spar_dynamic/full_corpus_experiment_1_batch/*-false-protocol/` — FCE2 batch (uncorrected diagnostic)
- `data/spar_dynamic/full_corpus_experiment_1_independent_calls/fce2-indep-truthful-*/` — FCE2 indep (truthful)
- `data/spar_dynamic/full_corpus_experiment_1_independent_calls/*-false-protocol/` — FCE2 indep (uncorrected)
- `data/spar_dynamic/full_corpus_experiment_1_independent_calls_story_batch/fce2-indep-storyswap-batch-*/` — story-swap
- `data/spar_dynamic/full_corpus_validation/validation-indep-*/` — task-validation study
- `data/spar_dynamic/full_corpus_phenotype_prediction/phenotype-*/` — p(H) baseline
- `data/spar_dynamic/full_corpus_phenotype_prediction_switch_rate/switchrate-*/` — switch_rate baseline
- `data/spar_dynamic/cross_story_indep_stimuli/` — three-story psychophysics summary
- `data/spar_dynamic/FCE1_FCE2_CROSS_METHOD_REPORT.md` — combined narrative report
- `data/spar_dynamic/PHENOTYPE_BASELINES_REPORT.md` — brief baselines report
- `spar_dynamic/full_corpus_exp1/` — all FCE1/FCE2 code
- `spar_dynamic/full_corpus_exp1/validation.py` — task-validation
- `spar_dynamic/full_corpus_exp1/cross_story.py` — within-stimulus trial-aligned analysis
- `spar_dynamic/full_corpus_exp1/phenotype_prediction.py` — forecast elicitation (parameterized by feature)
- `spar_dynamic/full_corpus_exp1/baselines_analysis.py` — observed-vs-predicted MAE and contrasts
- `spar_dynamic/full_corpus_exp1/baselines_report.py` — brief combined report
- `tests/test_full_corpus_exp1.py` — 26 tests, all passing

## Cost accounting

| phase | spend |
|---|---:|
| Pilot 5 corpus generation | $7.42 |
| FCE1 (history-conditioned, 480 + preflight) | $2.92 |
| FCE2 batch truthful + indep truthful | $7.07 |
| FCE2 false-protocol runs (preserved as diagnostic) | $5.50 |
| Task-validation study | $2.39 |
| Story-swap (indep stimuli × batch story) | $2.31 |
| Phenotype prediction p(H) | $2.81 |
| Phenotype prediction switch_rate | $2.81 |
| Preflight/smoke exploration during model selection | ~$1 |
| **TOTAL** | **~$34.23** |

(The $34 vs the $20 FCE1 spec cap: the cap was spec-defined for FCE1 only, which came in at $2.92. All later experiments were authorized individually in-session with their own small caps.)

## Open questions and recommended next steps

1. **Does fable's calibrated indep self-prediction reflect introspection or training-data knowledge of Claude's typical deterministic-prompt behavior?** Hard to answer without model-internal access. One experimental probe: run the phenotype-prediction task on a model variant whose training data couldn't include its own behavior patterns.
2. **Would the story-swap effect replicate with more models?** Only three were used. The pattern (one calibrated, one anti-calibrated, one flat) is intriguing but not generalizable.
3. **Can we construct a situation where SELF wording DOES add signal beyond OWN_NAMED?** We saw no evidence of a privileged SELF channel. If any future design can elicit one, that would be a very different story.
4. **Mimo's uniform 0.5 prior is itself worth characterizing.** It responds in-format at every opportunity but never differentiates. Is this a reasoning-disabled artifact (we had to disable mimo's reasoning for routing to work), or a deeper feature of this model?
5. **Can the fable procedure-belief be externally manipulated?** If we insert a plausible claim about procedure-level LLM behavior in the prefix ("most LLMs produce ~70% H under independent calls"), does fable's attribution shift?

## Known limitations an alignment reviewer will flag

- Three models is too few for strong generalization.
- Ten held-out triplets gives wide bootstrap intervals.
- Mimo had to run with reasoning disabled; this is documented but is a confound.
- "Fable predicts its own indep output accurately" is not evidence of introspection — fable predicts the same for other models' indep outputs too.
- The sign of astra's results depends heavily on whether the protocol prefix is truthful; this is a feature we exploited, but it also means the attribution channel is fragile.

## For an eventual writeup

A defensible framing: *LLMs' source-attribution for minimal binary behavior is dominated by beliefs about the stated generation process, not by reading the behavioral trace. Those beliefs are differentiated across procedures, applied uniformly across target models, and sometimes approximately calibrated to the predicting model's own actual behavior — but even accurate self-prediction can be fully accounted for by procedure-level task knowledge rather than any introspective mechanism. We demonstrate this with a within-stimulus three-story design on frozen trajectories, with position-bias and format-sensitivity controls.*

