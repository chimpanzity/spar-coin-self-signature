# SPAR handoff · Does a frozen probe follow Qwen when its dice policy changes?

Implement and run this as a new follow-up in `chimpanzity/spar-coin-self-signature`. It builds on `SPAR_Hidden_Activation_Dice_Policy_Claude_Code_Handoff.md`. Use the repo's existing pinned open-weight runner and Vast workflow. Do not modify frozen experiments, substitute checkpoints, or use API outputs as hidden states. If the first study hasn't run yet, implement and validate its baseline probe first. The intervention result is not interpretable without that baseline.

## Question

A supervised probe might look as if it reads Qwen's own dice policy while actually learning a lookup rule from the training labels. Hold the dice history and forecast prompt **byte-identical**, change Qwen's actual direct-generation preferences with an internal intervention, and ask whether the **original, frozen** probe's forecast-state readout follows the change. Nothing in the forecast text or in the probe's training labels tells it which intervention is active.

In scope: **next face after three or four distinct rolls** (rolls 4 and 5), conditional preference **among unused faces**. Not the skip-roll-6 task, adjective sweep, or a test of whether Qwen can avoid repeats.

## Study at a glance

| Arm | What changes | Direct generation | Forecast |
|---|---|---|---|
| Base | Original Qwen | Measure actual unused-face ranking | Save pre-answer state; read through frozen probe |
| Swap A | Qwen with a small dice-generation adapter | Measure actual changed ranking | Identical forecast tokens; same frozen probe |
| Swap B | A separately trained adapter with an opposed, context-dependent ranking target | Measure actual changed ranking | Identical forecast tokens; same frozen probe |
| Disabled adapter | Same runtime path with adapter contribution zeroed | Must reproduce Base | Must reproduce Base and its readout |
| Neutral adapter, if practical | Same trainable sites and training schedule, trained to reproduce the base policy | Should leave ranking mostly unchanged | Checks whether adapter training or state drift moves the readout without a corresponding behavioral change |

Run A and B before drawing the main conclusion. This need not involve another full Mistral run. The earlier crossed comparison establishes the context; this study's primary contrast is **within Qwen**.

## Locked checkpoint and prompts

Use `Qwen/Qwen3-32B`, revision `9216db5781bf21249d130ec9da846c4624c16137`, subject to verification against the repo's frozen model metadata. One user message, no system message, no tools, Qwen `enable_thinking=False`, exact chat template. Preserve the original scoring arithmetic and verify base replay before training. Main forecast wrapper (LF, no trailing newline):

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is an agent.
Earlier rolls in order: {prefix}.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

For the matched shape control replace just `The roller is an agent.` with `The roller is a shape.` Run both wrappers in all arms. Agent is primary; shape tests transfer of the **same** agent-trained probe with no refit. Preserve the direct-generation instruction above as its own user prompt, with the ordered history teacher-forced as an assistant continuation and the next-face separator in the same position as Experiment 33. Neither direct-generation nor forecast input mentions the adapter, variant, training rule, or true next face. Hash both user-facing and rendered inputs and verify that the corresponding hashes are identical across arms within each mode.

## Stage 1 · Freeze the readout and holdouts

- Use the earlier handoff's grouped families (unordered set of first three faces, including permutations and all four-face extensions), and its capture point at the pre-answer token, 75%-depth post-block by default. If reusing outer-fold probes, a history gets **only the probe and feature transforms from its original held-out fold**. If creating a single designated holdout instead, freeze that split and fit only on base Qwen outside it. Preserve a locked family holdout for the adapter as well. No held-out family in adapter training or tuning, even if the baseline probe used it in another fold. Reuse the same fixed evaluation histories across all arms. Report the design actually used.
- Freeze the probe coefficients and intercept, PCA/scalers, feature recipe and layer, and the **base-trained** input-only and history-plus-forecast-output comparators. Exclude adapter labels, outputs and activations from all feature fitting, layer selection, calibration, and readout training. At evaluation time the output comparator may receive current-arm output scores, but its fitted parameters remain frozen.
- Validate that the base forward pass recovers the original forecast probabilities and that the baseline probe and generation-state positive control are informative on untouched baseline histories. Fix any implementation issue on development data only. If the forecast probe never shows a credible baseline signal, report that and treat any swap analysis as exploratory, not a decisive null or success.
- Reserve a separate development bank for adapter hyperparameters and behavioral checks. Freeze arm definitions and success gates before scoring held-out forecasts. Store checkpoint, probe, split and adapter hashes. Use the repo's existing spend workflow and estimate the training cost before launching full jobs.

## Stage 2 · Change generation, not just the scoring function

Preferred implementation: train two small low-rank adapters on **direct-generation contexts only**, with Qwen's base weights and output head frozen. Place the trainable modules in a narrow band of blocks upstream of the fixed probe site (for example around mid-depth). Apply each trained adapter through the **same unconditional model path** for generation and forecasting. Do not gate the adapter on prompt type, attach an output-only logit bias as the primary intervention, alter the token sequence, or manipulate the recorded activation after capture.

- For each direct-generation training prefix, use base Qwen's conditional logits over the unused faces. Construct a target by **permuting those preferences within the unused set**, preserving total mass on the unused set. One concrete starting policy is to choose ordered unused faces by numeric value; rotate their logit profile one step forward when the first supplied face is less than the last, and one step backward otherwise. Reverse those mappings for B when three unused faces remain. When only two faces remain, opposite rotations are identical, so use complementary swap-versus-identity masks for A and B on the same history predicate. Keep the base probabilities on used faces and non-digit tokens as a preservation target. Train on measured distribution targets rather than a single sampled digit. A practical loss is KL over the conditional unused distribution plus preservation penalties for unused-face mass and the rest of the distribution. Implement one exact frozen rule, not a best-of-many search on the test bank.
- Balance and report which digits gain or lose rank. Check on development histories that the adapters do not just favor a fixed digit across contexts. If training is too costly or the targets don't transfer on development, simplify the rule **before** opening the held-out data. Record the exact target constructor, seeds, placement, rank, optimizer, steps, stopping rules, and whether the neutral adapter was feasible.
- **The ground truth is what the adapted model actually does in direct generation**, not what the adapter was trained to do. On held-out histories measure all six raw face log-probabilities, digit mass, mass on unused faces, and the actual log-odds for each unused-face pair. Save base, A, B, and controls. Reproduce base with the disabled adapter and capture hooks on/off. Verify no future tokens or direct-generation answers enter the forecast capture.
- Predefine an intervention-strength gate on development and freeze it before held-out evaluation. Suggested defaults: the held-out median absolute change in unused-pair log-odds is at least 0.5 nats per active arm, at least 20% of prefixes switch their preferred unused face per arm, and median absolute unused-face mass change is at most 3 percentage points (computed within six-face-normalized probabilities). Report total digit mass separately so preserving the normalized metric doesn't hide broken formatting. Report rates by roll and face, A versus B separation, and every failed gate. A policy that failed to change, or broke repeat avoidance broadly, does not yield a clean negative test of probe tracking.

## Stage 3 · Measure whether the original probe moves with the policy

Capture the last rendered forecast-token state before any generated token for every arm. Feed it through the original probe with all transforms frozen. Reuse the parent experiment's signed pairwise unused-face log-odds readout. For each prefix and unused pair i < j compute:

- **Actual policy change** = adapted direct-generation log-odds(i vs j) minus base direct-generation log-odds.
- **Probe change** = frozen probe's adapted forecast-state readout minus its base forecast-state readout.
- **Visible-output change** = same difference in the forecast's raw pairwise digit log-odds. Also score the frozen calibrated output readout and, if available, its full-logit sensitivity version.

Paired changes remove stable prefix preferences. History-only controls receive exactly the same input, so their predicted change is zero. Nevertheless include **training-free generic-shift controls**: compare with matching a readout to the wrong history's measured change within the same arm, roll, and candidate face pair, and report a sensitivity analysis subtracting the mean arm × roll × face-pair shift (fixed digit bias). Preserve matched history structure when shuffling; label sparse strata and do not force a null that breaks candidate availability. Also report within-history A-minus-B changes. These checks distinguish tracking context-dependent changes from reading a global increase in a digit or just detecting which adapter is active.

### Primary analysis and controls

1. Agent prompts, all eligible held-out prefixes, both A and B. Report the family-weighted correlation of actual and decoded changes, the error on predicting the change versus a zero-change baseline, and the same comparison for the frozen output readout. Average pair errors within prefix, prefixes within family, and families equally. Give A and B separately and a balanced aggregate; include paired family bootstrap intervals and sample counts. Do not refit the probe or a post-hoc scale factor on held-out changes. Report both direction and calibration even if they disagree.
2. Show a diagnostic table for cases where the actual adapted ranking reverses the base favorite. Show which face gained, whether the probe moved in the same direction, what the raw forecast did, and whether unused-face mass stayed stable. Define the subset from direct-generation behavior alone, not forecast or probe success. Include results for shape with no refitting.
3. Use the base-trained **generation-state** probe on the adapted generation boundary as a portability control. If it cannot follow a verified change even where the altered policy is being executed, a forecast probe null is difficult to interpret. This control is not itself evidence about forecasting. Report disabled adapter behavior and the neutral-adapter comparison if run.
4. Save one example each of a correctly tracked switch, a miss, and a case where the forecast itself tracks the switch, if these exist. Include raw masses, the relevant distributions/readouts, and fold IDs.

## How to call the result

- **The original probe follows verified internal policy changes on new histories, under identical prompts, better than fixed-digit and output controls.** Stronger evidence that the forecast states carry information tied to the currently implemented policy. It is harder to explain as the probe learning a static mapping from history to base Qwen preferences.
- **Both probe and ordinary forecast logits track the change.** The policy change affects forecasting, but there is no demonstrated advantage of hidden-state access over the measured output readout.
- **Generation changed, but the probe did not move or moved in the wrong direction.** No evidence of transfer for this probe and intervention; check the generation-state portability control before treating it as meaningful negative evidence.
- **The policy swap failed its manipulation checks.** Inconclusive, even if a readout moves. Do not substitute the intended ranking for the actual measured ranking.

Even a clean positive can come from the same first-order computation or adapter-induced feature changes in both contexts. It does **not** establish that Qwen consults a separate self-model or uses the decoded signal to answer. A distinct later intervention on the decoded forecast feature would be needed to test use.

## Deliverables

Write a new frozen protocol, split and prompt hash manifests, probe and adapter manifest, capture/scoring code, checks, paired per-history results, and a short `REPORT.md`. Make the treatment-level comparison reproducible from archived weights/configs and structured outputs. Keep bulky weights and activations out of ordinary Git history, retain hashes and the reproduction/retrieval path, and document actual GPU cost and deviations.
