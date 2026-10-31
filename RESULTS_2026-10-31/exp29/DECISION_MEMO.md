# Decision memo: Experiment 29 (bidirectional cross-model dice completion)

2026-10-31 · For the investigator and Christopher Ackerman · Full results in [REPORT.md](REPORT.md)

## What was decided before data

- **Prompt count.** The 76 prompt slots contain 74 distinct texts: Qwen's and Mistral's F sequences share their first two
  rolls, so the F forward k = 1, 2 prompts are identical across sources. This was accepted as documented.
- **Rental.** One rental, with main collection conditional on every hard preflight gate passing
  ([APPROVALS.md](../../track1_self_prediction/29_2026-10-31_bidirectional_dice_completion/APPROVALS.md)). Both conditions held.

## Outcome by hypothesis

| Hypothesis | Outcome |
|---|---|
| H1, forward conditioning | **Partly.** Boundary loss is lower at k = 7–9 than k = 1–3 in 7 of 8 combinations, but the curve is irregular. The clear gain is at k = 5, where every sequence's first five rolls leave one unused face: a generic rule, not a source-specific one. |
| H2, self-specific advantage | **Not supported.** The k-averaged balanced contrast is −0.002 to +0.092 nats across G/F × forward/backward. Its sign varies across k (4–6 of 9 positive), and single-k values sit within the per-position numerical noise (up to 0.69 nats for Qwen). Source difficulty dominates. |
| H3, direction asymmetry | **Present, but sequence-specific.** Backward is easier on Qwen's F and harder on Mistral's F, for both predictors; it is small on G. Overall, forward and backward are within 0.07 nats. |
| H4, free vs teacher-forced | **Diverge.** Qwen gives valid free answers in 75 of 76 cells (29% digit accuracy vs 41% teacher-forced top-1). Mistral gives 0 of 76 valid free answers (prose), yet its teacher-forced distributions are the better of the two. |
| Middle arm (supplementary) | No late-tail advantage (early 1.11 vs late 1.12 nats). Crossed contrasts of ±0.2–0.5 flip sign between G/F and between parts, so there is no consistent self effect. |

## What this means for the self-prediction line

Experiments 26–29 now agree:
- prediction framing changes the opening of a sequence, not its continuation (28);
- revealed history helps where generic structure pins the next roll (26, 29);
- no setting so far shows that a model reconstructs or predicts **its own** outputs better than a comparable model does (27, 29).

On these deterministic dice tasks, there is no behavioural signal of self-specific knowledge to take into a mechanistic
analysis.

## Recommended next steps (not run)

1. **Report 26–29 together at the midterm** as a consistent negative on dice self-prediction, with the source-difficulty
   confound as the main methodological lesson.
2. **If the line continues, change the stimuli, not the wrapper.** Use sampled sequences (as in Experiment 27's corpus), so
   that each source contributes many targets and source difficulty can be averaged out. With four fixed strings, a
   predictor × source interaction is mostly one coincidence of sequence structure.
3. **Fix Mistral's format before any free-behaviour claim.** Every Mistral completion was prose. Options: a one-line format
   instruction, already shown to be insufficient here; an assistant prefill; or reporting teacher-forced results only. Each
   is a design change and needs its own approval.
4. **A separate self/other recognition experiment remains the open question.** Experiments 22–25 show it first needs an
   instrument that passes a reading-check gate.

## Cost

One A100 for 1.04 h. The billed total is in [manifest.json](../../track1_self_prediction/29_2026-10-31_bidirectional_dice_completion/manifest.json), under the $15 cap. The instance is destroyed.
