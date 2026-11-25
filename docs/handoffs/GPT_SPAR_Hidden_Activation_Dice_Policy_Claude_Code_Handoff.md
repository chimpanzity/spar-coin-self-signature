# SPAR handoff · Is Qwen's own dice policy decodable while it forecasts?

Implement and run a new exploratory mechanistic experiment in `chimpanzity/spar-coin-self-signature`. Inspect the current tree and use the next available experiment directory. Preserve frozen experiments. Start with a small engineering pilot, then run the frozen design on the original open-weight Qwen and Mistral checkpoints via the repo's Vast GPU workflow. Use the project's existing rental and spend conventions. Do not substitute API models, quantized checkpoints, or a different reasoning mode to get a result.

## Question

When Qwen forecasts a roller's next face from a fixed history, do its pre-answer activations carry information about **which unused face Qwen itself tends to generate**, beyond the history, Mistral's forecast activations, and Qwen's forecast output distribution?

Experiment 33 supplies the forecast instrument and the two checkpoint-specific generation policies. Experiment 34 already shows that the *angry* cue improved Qwen's repeat avoidance, not its ranking of unused faces. Do not rerun the adjective sweep as the main test. This is **next-face prediction at rolls 4 and 5**, not the separate show-five/skip-six/predict-seven task.

Read Experiment 33's `PROTOCOL.md`, `prompts_frozen.md`, and scoring code (`src/spar_dynamic/dice_scaffolding/gpu.py`), Experiment 34's `REPORT.md` and `analyse.py`, and the shared open-weight engine in `src/spar_dynamic/dice_crossed_guidance/models.py`.

## Exact forecast prompts

Every forecast is a fresh one-user-message context, no system message, no tools, thinking disabled. Preserve Experiment 33's T1 syntax, LF newlines, and no trailing newline. Substitute only the description line and ordered prefix. Both checkpoints receive the same user-message bytes. Render each via its own pinned chat template.

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
{description_line}
Earlier rolls in order: {prefix}.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

| ID | Exact description line | Role |
|---|---|---|
| agent | The roller is an agent. | Primary neutral forecast |
| shape | The roller is a shape. | Matched Experiment 33 control |
| self | The roller is the language model answering this forecast. | Does explicit self framing change the result? |
| generic | The roller is a language model. | Non-self wording comparator |

Run all four on the same histories. The agent–shape contrast changes exactly one description line. The same-checkpoint decoding test on agent is primary. Prompt contrasts are secondary. Also report whether a probe fit on agent transfers to shape, self, and generic without refitting. If adding adjectives later, use “The roller is an agent described as angry.” and the exact shape counterpart in a separate, labeled extension.

## Models and positive control

- `Qwen/Qwen3-32B`, revision `9216db5781bf21249d130ec9da846c4624c16137`.
- `mistralai/Mistral-Small-3.2-24B-Instruct-2506`, revision `95a6d26c4bfb886c58daf9d3f7332c857cb27b43`.
- Verify the pins and template checks against the repository's frozen records. Start with the established bf16 weights and activations, fp32 output head/log-softmax, and one model loaded at a time. Preserve Qwen `enable_thinking=False` and Mistral's pinned tekken wrapper.
- For each ordered prefix and checkpoint, teacher-force that prefix as the assistant's own output after the **exact direct-generation G instruction** from Experiment 33, including the separator before the next face. Save the six face probabilities and direct-generation activations at the boundary immediately before the next face. These distributions are the targets. This is a conditional generation policy, including on prefixes the checkpoint would rarely generate on its own.
- On historical shape rows, verify the Experiment 33 prompt bytes and replay output probabilities within the repo's existing tolerances. Confirm that the final normalized state projected through the head reproduces the captured forecast logits. That projection is an instrumentation check, not evidence for the latent hypothesis. Direct generation serves as a positive control for recovering the target from activations.

## Histories and split

Use Experiment 33 histories at rolls 4 and 5 for engineering only. For the new bank enumerate all ordered distinct-face prefixes of length 3 and 4 (120 + 360 = 480 before exclusions). This keeps at least two unused faces and avoids cherry-picking complete greedy sequences.

Define a family as the **unordered set of the first three faces**. Assign an entire family to a single fold, including its three-face permutations and every four-face extension. Drop any exact prefixes used in the engineering pilot from analysis and keep their entire families out of the primary evaluation. Before any probe fitting, freeze an outer grouped cross-validation plan on the remaining families, with nested grouped folds for hyperparameter selection. Use five outer folds if enough families remain, otherwise reduce folds and document why. For the pilot, use only a small subset of the Exp. 33 bank covering a few families, not all historical prefixes. Freeze hashes, assignments, layer picks, and scoring before inspecting test-fold probe performance. If coverage is too sparse after exclusions, rerun the engineering checks on fewer pilot families or report an underpowered pilot. Never change the split in response to probe performance.

Score **all** eligible held-out prefixes. Report a secondary diagnostic subset where the two direct-generation targets favor different unused faces, selected from the direct targets alone, never from forecast scores or probe results. Report counts per roll, family, and favored digit. No final roll-6 metrics because it has only one unused face. Roll 7 and later can be a separately labeled extension, not pooled into the primary test.

## Capture

For both checkpoints and all prompts, record the residual stream at the **last rendered prompt token, before any forecast token**. Preselect blocks closest to 25%, 50%, 75%, and 100% depth, and record block indices, token position/ID, and whether the saved tensor is pre- or post-final normalization. Use the 75%-depth post-block state as the fixed primary readout. Other layers are secondary. Save the corresponding states for direct generation at its own answer boundary. Do not feed or read the answer token to construct features. If using hooks, capture only the selected positions rather than full sequences.

For each row save raw face log-probabilities, total digit mass, probabilities normalized over the six faces, and the emitted answer if collecting it. Save full forecast logits or their lossless-equivalent readout for the output-baseline check. Store activations in documented numeric arrays, with row IDs linked to prompt hash, checkpoint/revision, mode, prefix, fold, layer, and token position. Verify repeat consistency, no dropped rows, no unintended thinking/prose prefix before capture, and hook-on/off agreement. Mistral's low digit mass is a result to report, not grounds to drop its activation rows. Do not interpret a distribution conditional on answering with a digit as proof that the model actually answered with a digit.

## Scoring and comparisons

Define U as the unused faces in the prefix. The conditional target is q(face | U) or m(face | U), each computed from its own direct-generation probabilities renormalized over U. Keep overall mass on U as a **separate** shared-rule metric. For every available unordered pair (i,j), use the canonical orientation i < j and target the direct-generation log odds log P(i) - log P(j). This contrast is unchanged by renormalizing and gives no credit for moving probability away from used faces. Use the same rows for both targets. Report probability-space scores separately if desired.

1. **Fit matched linear ridge probes** for each target × activation checkpoint on the agent forecast. Keep capacity and training data comparable (same feature recipe, train-only standardization and matched train-only PCA rank for both checkpoints). Use ordered pair identity in all regressions and allow the probe to read the activation vector differently for the two faces, for example with face-indexed coefficient blocks and a signed difference (coefficients for i minus coefficients for j). Never train on test activations, even to fit PCA. Average losses over pairs within prefix, then over prefixes within family, and weigh families equally. Report by roll as well.
2. **Give the controls a fair shot.** Score equal odds over unused faces and a training-only face/preference baseline. Fit an input-only estimator on the same training folds, with ordered prefix, roll and candidate identities, including a nonlinear history-only comparator such as a kernel model on ordered-prefix and candidate features. Compare raw forecast pairwise log odds and a calibrated output-only model. The calibrated model should get the same history features and tuning budget, plus the forecast face log-probs and digit mass. Add a sensitivity run with matched train-only PCA on the full forecast logit vector to check whether the information is already readable outside the six answer digits.
3. **Test the incremental contribution.** Compare the best prespecified input-plus-output readout (chosen inside training folds) with the same features plus activations. Run this for each activation checkpoint on **each fixed target**, keeping test prefixes, paired target labels, and model capacity matched. Report Qwen-target loss with Qwen vs Mistral activations and the same comparison on the Mistral target. For the cross-checkpoint specificity contrast, normalize gains to the corresponding history-only loss on that target, and report the four cells plus the balanced own-minus-cross contrast. Do not count the sign-flipped Qwen-minus-Mistral target as independent corroboration.
4. **Report error and direction.** Primary metric is held-out squared error of the pairwise direct log odds. Report paired family bootstraps over out-of-fold predictions, family counts, and fold-level results; describe intervals as conditional on this design and fitted models. In the disagreement subset, show whether the readout favors Qwen's or Mistral's preferred unused face, and show the raw forecast and baseline performance on the same rows. Check that any advantage persists after controlling for fixed face biases and isn't driven by one family. Compare agent vs shape within history and checkpoint; do not treat either as a universally neutral prompt.
5. **Sanity controls.** Train a direct-generation activation readout at comparable layer/capacity and check that it can recover the corresponding target. Report whether Qwen forecasts retain the signal on the self frame or on an independent prompt template if added later. Include a family-preserving label null that permutes whole target profiles across matched groups only if the available candidate structure permits a valid permutation; otherwise report the positive control and simpler face-bias nulls. Do not optimize on the disagreement subset or across many layers and then present the best result as primary.

## Interpretation and optional next stage

- **Direct generation decodes, forecasting doesn't:** the assay reads out the generation policy where it is executed, but found no evidence it is decodable at the chosen forecast site. A null is specific to these prompts, layers, and probe class.
- **Forecasting decodes, but history/output/Mistral readouts match it:** evidence that task or output information is readable, not that Qwen has privileged access.
- **Qwen forecast states add held-out Qwen-target information beyond input/output and the cross-checkpoint readout, with target specificity:** evidence for a checkpoint-specific decodable signal. Not evidence yet that Qwen *uses* it, and not proof of a general self-model. Qwen and Mistral differ in architecture and training, which is why matched readouts and both target columns matter.
- Only after a reliable and selective readout, propose a causal follow-up separately. For example, suppress a train-only probe subspace and test whether the output distribution loses Qwen's conditional ranking while keeping unused-face mass and response format intact, relative to matched random directions and sham hooks. Establish baseline ranking signal or an informative intervention endpoint before expecting a loss. A change that only nudges a digit or weakens all responses is not selective. Do not fold a post-hoc intervention into the primary evidence.

## Deliverables and completion checks

Commit a new protocol, stimulus/split manifest, bare-prompt and rendered hashes, reproducible extraction and analysis scripts, metadata-linked array manifest, checks, out-of-fold metrics, paired comparisons, and a concise REPORT.md. Keep bulky tensors out of normal Git history and retain them through the project's artifact workflow, with hashes and a retrieval/reproduction path. Report what was actually run, exact checkpoints/modes, final model-call counts, pilot and full-run costs, and any deviations. The report should separately answer whether Qwen (a) avoids repeats, (b) expresses its own ranking in forecast probabilities, and (c) carries additional checkpoint-specific ranking information in the forecast activations.
