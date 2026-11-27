# Experiment 38 protocol: does the SLOT prompt let a model skip ahead at every position?

Tag `SPAR_EXP38_SLOT_SKIP_AHEAD_v1.0`. Design source: the investigator's request in session (2026-11-27), recorded in `APPROVALS.md`; no separate handoff. Follow-up to Experiment 35, whose only correct roll-7 answer came from the SLOT ending (Qwen, its own sequence). Frozen before any model call.

## Question

Experiment 35's SLOT ending marks the missing roll as blank and names the target position. Generalised to every position: shown rolls 1..k, roll k+1 blank, predict roll k+2 (k = 1..8). Does SLOT move a model's forecast from the next roll (k+1) toward roll k+2, and is any such forecast closer to the model's own generation policy than to the other model's?

The Experiment 35 hit may be explained by a shared rule: after `5 2 6 3 1` the unused faces are 4 and 6, so skipping the obvious one gives 6 without tracking roll 6. This design scores against each model's exact two-step policy and against a model-free two-step rule, so the rule explanation can be separated from the model-specific one.

## Design

- **Sources.** Every G-instruction sequence on record for the two checkpoints: Experiment 28's two greedy G outputs and Experiment 27's 64 sampled G sequences (T = 0.7, 32 per generator). 66 sources, 46 distinct sequences. Prompts depend only on the rolls shown, so the unit of model computation is the unique prefix: 170 prefixes for k = 1..8 (4, 10, 17, 20, 24, 24, 33, 38).
- **Prompts** (exact bytes in `prompts_frozen.md` and `design_prompts.csv`). Experiment 32's head, then the rolls line (`The first k words rolls it produced were: ...`; for k = 1, `The first roll it produced was: r1`), then:
  - **SLOT** (k rolls shown): `Roll {k+1}: [blank]. Roll {k+2}: [predict this position]. Predict roll {k+2} of that response. Return exactly one integer, with no other text.`
  - **B** (k rolls shown): `Predict roll {k+2} of that response. Return exactly one integer, with no other text.`
  - **C** (k+1 rolls shown, the source's true roll k+1 appended): `Predict roll {k+2} ...` (the next roll). 208 unique C prompts.
  - 548 prompts in all; both predictors receive identical bytes. At k = 5 on the greedy sources, SLOT, B and C equal Experiment 35 SLOT and Experiment 32 B and C byte for byte (six anchors).
- **Models and serving.** Qwen3-32B and Mistral Small 3.2 24B at the pinned revisions, the Experiment 27-35 engine imported unchanged (bf16, fp32 head, batch 1, KV-cache incremental arithmetic, greedy). One user message, no system message, thinking disabled.
- **Readouts per prompt.** Free greedy generation (128 tokens); the six bare face log-probabilities at the first answer token, computed twice (must be bit-identical) and once by full pass (numerical floor). Free answers are valid only if exactly one digit 1-6 and generation ends by itself; no digit is extracted from prose.
- **Policy targets.** For each generator g and prefix P: the teacher-forced G policy for roll k+1 after P (T1), and for each face x the policy for roll k+2 after P + x (B(P, x)), forced as the assistant turn exactly as in Experiment 31. Two-step target T2(P) = sum over x of T1(P)[x] B(P, x). Six-face normalised at every step.

## Stop rules (per model, before the grid)

1. Vocabulary scan finds no variant face tokens.
2. Experiment 28 G and F archival replay passes (identical outputs, six-face |dp| <= 0.01, identical repeats).
3. The six k = 5 anchors reproduce Experiment 35 SLOT and Experiment 32 B and C: identical prompt ids, identical free output, first-answer six-face |dp| <= 0.01.
4. After the policy stage: the own G policy along both greedy G paths reproduces Experiment 31 (one-step rows and true-branch rows, |dp| <= 0.01), and the one-step row is bit-identical across its six branch computations.

Bit identity is recorded wherever it is checked. Any failure stops that model.

## Analysis (frozen in `src/spar_dynamic/slot_skip_ahead/analysis.py`)

Distances are Jensen-Shannon divergence in bits between six-face-normalised distributions. For forecast f by predictor m at prefix P:

- `d2_own` = JS(f, T2_m(P)) (the correct target); `d1_own` = JS(f, T1_m(P)) (the next roll); **index** = d1_own - d2_own (positive: closer to roll k+2 than to roll k+1).
- **Q1 (skip-ahead, primary).** Within prefix, index under SLOT minus index under B, and d2_own under B minus under SLOT. Mean over prefixes, per predictor, pooled and by k and by block (target roll <= 6 vs >= 7).
- **Q2.** Index under SLOT and under B.
- **Q3 (self-specificity).** Crossed own advantage per prefix: half the sum over the two predictors of [JS(f_m, target of other) - JS(f_m, own target)], which cancels target difficulty. Reported for SLOT, B (target T2) and C (target B(P, x_true)).
- **Uncertainty.** 95% percentile intervals from 10,000 cluster-bootstrap draws (seed 20261127), clusters = prefixes sharing their first two rolls (k = 1 prefixes are their own clusters). Prefixes are nested and the clusters few, so intervals are approximate. No p-values.
- **Baselines** (distance to own T2): uniform; the model-free two-step exhaustion rule (each roll uniform over faces unused in its six-roll block, positions 1-6 and 7-12); the own one-step policy T1 (a perfect next-roll answer); the other model's T2.
- **Realised rolls.** Per source sequence and k: forecast probability of the true roll k+2 and of the true roll k+1; free answers classified as target roll, roll k+1, other face or invalid; split by own- vs other-generator source. Sources are weighted as sampled (duplicated sequences count each time).
- **Exploratory.** The Experiment 35 hit is re-examined at k = 5 over all 24 prefixes. Rows with digit mass < 0.5 are flagged and counted; they are included in the primary means.

## Interpretation rules

- SLOT "helps skip ahead" only if Q1 is positive with an interval excluding zero for a predictor. A SLOT forecast that is no closer to the own T2 than the two-step exhaustion rule is explained by the shared rule.
- Self-specific anticipation requires Q3 > 0 with an interval excluding zero under SLOT, and Q1 support. A positive Q3 in C alone means the models continue their own strings better when given roll k+1, which Experiment 31 already showed.

## Cost

vast.ai A100-SXM4-80GB, one rental for both models; estimate $3-4 including download and disk; self-imposed hard cap $5. The run stops if spending approaches the cap. The instance is destroyed after the raw files are copied and hash-checked.
