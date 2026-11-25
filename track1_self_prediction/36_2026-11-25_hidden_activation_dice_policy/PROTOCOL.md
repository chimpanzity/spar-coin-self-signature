# Experiment 36 protocol: is Qwen's own dice policy decodable while it forecasts?

Tag `SPAR_EXP36_HIDDEN_ACTIVATION_DICE_POLICY_v1.0`. Design source: `docs/handoffs/GPT_SPAR_Hidden_Activation_Dice_Policy_Claude_Code_Handoff.md`. Exploratory. Frozen, with the analysis code, before any model call. Where this file is silent the handoff governs.

## Data

- **Bank:** all 480 ordered distinct-face prefixes of length 3 and 4 (rolls 4 and 5). Family = unordered set of the first three faces (20 families, 24 prefixes each).
- **Pilot:** Experiment 33 prefixes at rolls 4 and 5 in families 146 and 125 (6 prefixes, from c01, c02 and c10). Both whole families are excluded from the primary evaluation, leaving 18 families, 432 prefixes and 648 pairs.
- **Forecasts:** four prompts (agent, shape, self, generic) on every prefix, one user message, no system message, no tools, thinking off.
- **Direct:** the archived G instruction with the prefix and a trailing separator forced as the assistant turn. The six-face log-probabilities there are the targets.
- **Capture:** last rendered prompt token (forecast), last forced separator (direct), before any generated token. Post-block residuals nearest 25, 50, 75 and 100% depth (Qwen blocks 15, 31, 47, 63 of 64; Mistral 9, 19, 29, 39 of 40; 0-based; pre final normalisation) plus the final-normalised state. Stored as raw bf16 bits. Primary site: 75% post-block.
- Full logits are stored losslessly as the final-normalised state and the pinned head; the row-centred head Gram matrix is saved for logit PCA.
- The agent forecast also records up to 16 greedily emitted tokens.

## Gates (pilot, then full bank)

Archival G/F replay; Experiment 33 shape and direct rows (same prompt hash and prefix) replay within six-face |dp| <= 0.01; every row rescored with identical scores and identical stored states; scores identical with hooks off; projection of the final-normalised state through the head within 0.001 nats of the captured logits; finite arrays; one last-token id per mode type. A failed gate stops the run.

Experiment 33's direct targets for its own prefixes were already known. The probe results were not.

## Split

Families in hash order, round robin into five outer folds (sizes 4, 4, 4, 3, 3). Hyperparameters by four inner family folds within each outer training set. Four-face prefixes whose unordered faces agree but whose first three differ can fall in different folds; this follows the handoff's family definition.

## Models

Target: canonical pair (i < j) direct log odds, for each unused pair; Qwen and Mistral targets on the same rows. Every fitted model is a kernel ridge on pairs whose activation block is exactly the face-indexed, signed-difference linear probe (tests check the identity). Train-only standardisation and PCA, rank 32 for both checkpoints (ranks 8, 16, 64 as sensitivity). Ridge grid 10^-3 to 10^2 in half decades. Equal family weights.

| Name | Features |
|---|---|
| equal odds; face bias | none; training-only face preferences |
| history | face bias + one of five history kernels: linear ordered-prefix, two RBF, relational candidate-versus-recent-rolls, RBF + relational (chosen in inner folds) |
| raw forecast; calibrated output | pairwise forecast log odds; face bias + output block |
| history + output | history kernel + output block (candidate log-probability slope, six log-probabilities, log digit mass), weight 0.1, 1 or 10 |
| + act | the fold's chosen history + output model plus the activation block, weight 0, 0.1, 1 or 10 |
| history + logits (+ act) | history plus train-only PCA of the full forecast logits |
| stack | history + both models' outputs + the other model's activations, then + own activations |
| act only | face bias + activations, forecast or direct (positive control) |

For each activation checkpoint, "output" is that checkpoint's own forecast output. Loss: held-out squared error of the pairwise log odds, averaged over pairs within prefix, prefixes within family, families. Intervals: 10,000 paired family bootstraps over out-of-fold predictions (PCG64 seed 361125), conditional on this design and the fitted models.

## Estimates

1. Primary: act beyond history + output, Qwen agent activations, Qwen target, 75% depth.
2. Specificity: gains for the four activation x target cells divided by the history-only loss on that target; balanced own-minus-cross contrast, and the Qwen-target contrast.
3. Stack: Qwen activations beyond history, both outputs and Mistral activations.
4. Positive control: direct activations against face bias and against history.
5. Disagreement subset (direct favourites differ): which model's favourite each readout prefers, on the same rows.
6. Secondary: other depths, ranks, the other prompts (refit, and the agent probe transferred without refit), logits.
7. Null: 100 permutations of whole target profiles among the six prefixes sharing a family and an unused set, for estimate 1. This null removes order-dependent target information only.

**Reading.** A checkpoint-specific decodable signal is claimed only if 1, 3 and the own-minus-cross contrast all have intervals above zero and the positive control beats history. If the direct positive control does not beat history, a null in 1 is uninformative. Decodability is not use.

## Cost

Run on the instance rented for Experiment 35 (A100-SXM4-80GB), under that $10 cap extended to both. Arrays (about 270 MB per checkpoint) stay out of git; hashes are in `raw/<model>/env.json`.
