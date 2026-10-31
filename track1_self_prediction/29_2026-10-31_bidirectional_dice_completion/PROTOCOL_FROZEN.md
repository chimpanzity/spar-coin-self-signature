# SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1: frozen protocol

Design source: SPAR_Experiment_29_Handoff_v1_1.md (2026-10-31; v1.1 adds the middle-anchored arm before any collection). Direct sequel to Experiment 28; Experiments 26 and 27 are historical controls. Experiments
01-28 are read, never written. A descriptive, fixed-reference behavioural assay: 4 distinct ground-truth strings. No
replicate-, position- or source-based significance tests. Behaviour and output probabilities only; no mechanistic analysis.

## Questions and predeclared expectations (handoff section 1)
- H1, forward conditioning: loss at the next missing roll may fall with informative revealed prefixes (not introspection).
- H2, self-specific advantage: predictor x source interaction favouring diagonal cells beyond source difficulty, separately for
  G/F and forward/backward.
- H3, direction asymmetry: backward reconstruction (known suffix, missing prefix emitted left to right) differs from forward
  continuation. Retrospective inference in ordinary output order, not reverse-time generation.
- H4, calibration: free completions and teacher-forced six-face probabilities may diverge; both are reported.
- Supplementary (v1.1): the revealed middle (positions 3-8) may help the late tail (9, 10) more than the early head (1, 2).

## Ground truth (Experiment 28 main greedy outputs; verified against every Experiment 28 main replicate at freeze)
| Source | Instruction | Sequence |
|---|---|---|
| qwen | G | `5 2 6 3 1 4 6 2 5 3` |
| qwen | F | `3 1 4 6 2 5 3 2 6 4` |
| mistral | G | `4 2 6 1 3 5 2 4 6 1` |
| mistral | F | `3 1 5 2 6 4 3 1 5 2` |

## Models and serving
Experiment 28 exactly: `Qwen/Qwen3-32B` @ `9216db5781bf21249d130ec9da846c4624c16137` (Qwen3 template, enable_thinking=False) and `mistralai/Mistral-Small-3.2-24B-Instruct-2506` @
`95a6d26c4bfb886c58daf9d3f7332c857cb27b43` (mistral_common tekken, text path only), via Experiment 27/28's engine, unchanged. bf16 weights/activations,
fp32 output layer and logits, batch 1, KV-cache incremental decoding, full-vocabulary log-softmax, greedy argmax, no sampling,
no logit processors, no tools, no system message, max 128 new tokens. Face ids Qwen 16-21 / separator 220,
Mistral 1049-1054 / separator 1032; re-validated on the host by a full vocabulary scan. One A100-80GB on vast.ai, one checkpoint
loaded at a time; no hosted API.

## Design
- Primary grid: predictor x source x instruction (G, F) x direction (forward, backward) x k = 1..9: 144 cells.
  Forward reveals positions 1..k and asks for k+1..10; backward reveals 11-k..10 and asks for 1..10-k, both emitted in
  original left-to-right order.
- Supplementary middle-anchored arm (v1.1): reveal positions 3-8, ask for 1, 2, 9, 10 in that order: 8 cells.
- Total 152 cells; 76 prompt slots (each sent byte-identically to both predictors); the source model is
  never named. Prompts in `prompts_frozen.md`, table in `conditions.csv`.
- **Count discrepancy found at freeze (documented, nothing changed):** the handoff expects 76 unique prompt texts; the frozen
  renderer gives 74 distinct texts over 76 slots. Qwen F (`3 1 4 ...`) and Mistral F
  (`3 1 5 ...`) share their first two rolls, so these slots are byte-identical: [['qwen-F-fwd1', 'mistral-F-fwd1'], ['qwen-F-fwd2', 'mistral-F-fwd2']]. Their targets differ. Both predictors'
  free outputs for each pair must therefore be identical; teacher-forced scores differ by target. In these four cells the
  predictor cannot know the source, so their diagonal contrast measures source difficulty alone. All cells, targets, estimands
  and counts of calls and rows are as specified.
- Prompt wrapper: handoff 3.1 (primary) and 3.3 (middle), byte-exact, with Experiment 28's G or F prompt quoted verbatim inside
  `<ORIGINAL INSTRUCTION>`. No trailing newline after the final sentence (same policy for all prompts).

## Collection
1. Preflight per predictor: archival G and F (Experiment 28 prompts) x2; 28 cells once each (all
   sources/instructions/directions at k in (1, 5, 9), plus the 4 middle cells) = 56 cells in total; seeded
   shuffled order (seed 20261201 / 20261202); own-output rescoring and teacher-forced targets
   by both arithmetic paths; vocabulary scan. Diagnostic only; never substituted for main data.
2. Preflight gates (all must PASS): references equal Experiment 28; serving identity and prompt hashes; template; face tokens
   and vocabulary scan; finite face log-probs and p6 sums; archival G mass >= 0.5; archival G/F identical to
   Experiment 28 with six-face vectors within 0.01; archival repeats bit-identical; preflight calls complete;
   own-output rescoring within 0.0001 nats for valid outputs; target mapping (positions, forced faces, prefixes, row
   counts); floor (incremental vs full pass) <= 0.25; no model name in any prompt; teacher-forced mass review (STOP for
   investigator review if a predictor's median raw six-face mass over its teacher-forced rows is < 0.1, or if
   any cell has every row < 0.01). Free-output format and prediction-prompt mass are reported, not gated.
3. Main per predictor (only after its PASS preflight and explicit investigator approval): archival G and F x2
   (in addition) plus all 76 cell slots x 3 = 228 cell calls per predictor (456 total), seeded
   shuffled order (seed 20261101 / 20261102), append-only, resumable. The first record of each distinct
   (cell, output) is rescored by both paths. Then every cell's true target is teacher-forced once by both paths:
   752 incremental rows in total (720 primary + 32 middle), and the same number of full-pass rows.
4. Main checks (all must PASS before analysis): the preflight hard gates, plus completeness (each (cell, replicate) and archival
   call exactly once), deterministic text and log-probs across triplicates, and raw-file hashes unchanged since collection.

## Measurements
- Free completion: raw text, token ids, finish reason, per-step full-vocabulary log-probs, six face log-probs at every step,
  digit steps, strict validity. Valid = exactly n integers 1-6 separated by single ASCII spaces, nothing else (no leading or
  trailing whitespace, no newline), ended by EOS. Digits embedded in prose are never extracted or scored.
- Teacher-forced true targets: the true missing digits forced as the assistant answer (separators between them), never in the
  user prompt; at each missing position the six-face vector before the forced face, raw mass, p_true, conditional and
  full-vocabulary log loss, argmax, margin, forced prefix text and token ids. Middle arm: steps 1-4 score positions 1, 2, 9, 10
  after forcing the earlier true answer digits; positions 3-8 stay in the user prompt only.
- Numerical floor per predictor: max |dp6| between incremental and full-pass scoring of the same rows. A top face whose margin is
  below the floor is a near-tie (counted separately; `top_correct` requires margin >= floor).

## Analysis plan (no p-values or CIs; deterministic fixed references)
- Position-level table and condition-level table (first missing position and the equal-weighted mean over the missing span).
- Primary metric: conditional log loss -ln p6(true) in nats (uniform = ln 6 = 1.792). Secondary: full-vocabulary log loss, raw
  mass, top-face correctness beyond the floor, free validity, free digit accuracy and exact span match, entropy, and JS to the
  source's Experiment 28 I|I vector at the same original position (a source continuation reference for forward cells only;
  shown as descriptive for backward and middle cells).
- Self vs other: for each (instruction, direction, k) the 2x2 L[predictor, source] of mean span loss (and separately of
  first-position loss), its row and column effects, per-predictor self-minus-other, and
  self_advantage = (L[Q,M] + L[M,Q] - L[Q,Q] - L[M,M]) / 2 (positive = diagonal lower). Also averaged over k with equal weight per
  condition, separately for G/F and forward/backward. A positive contrast is not evidence of introspection.
- H1: forward boundary (position k+1) loss by k per predictor/source/instruction. H3: backward minus forward at equal k, mean
  span and first missing output digit (labelled: position 1 vs position k+1, not temporally equivalent). H4: free validity,
  free digit accuracy, teacher-forced top-1 rate and mean p_true, free first digit vs teacher-forced argmax.
- Middle arm, separate from all primary summaries: early pair (1, 2), late pair (9, 10), four-position mean; loss, first-digit
  loss, top-face correctness, raw mass, validity; 2x2 crossed contrasts per G/F for each part. Compared with k = 6 only as
  equal amount of revealed information.

## Budget and stop rules
Hard cap $15 total (GPU + disk + bandwidth). Stop for the investigator on any hard gate failure, the mass review
rule, unexpected cost, or any deviation. The instance is destroyed after work or failure.
