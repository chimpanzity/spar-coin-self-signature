# Experiment 37 protocol: does a frozen probe follow Qwen when its dice policy changes?

Tag `SPAR_EXP37_FROZEN_PROBE_POLICY_SWAP_v1.0`. Design source: `docs/handoffs/GPT_SPAR_Frozen_Probe_Policy_Swap_Claude_Code_Handoff.md`. Builds on Experiment 36 (its bank, folds, prompts, capture code and fitted models). Qwen3-32B only. Where this file is silent the handoff governs.

## Order of freezing

1. This protocol, the target rule, split, gates, adapter code and analysis code are committed before any adapter is trained and before Experiment 36's probe results are known.
2. After Experiment 36's Qwen capture, the readouts are refitted with Experiment 36's hyperparameters and written to `arrays/probes.npz`; their hash (`probes_manifest.json`) is committed before any held-out adapted forecast is scored. The evaluation stage refuses to start without the manifest.

## Split

- **Holdout:** Experiment 36 outer folds 0 and 1 (8 families, 192 prefixes, 288 pairs). Never used in adapter training or tuning. Each prefix uses only the readouts from the fold in which Experiment 36 held it out (which were trained on other holdout families' base-Qwen rows, as the handoff allows).
- **Adapter training:** folds 2-4 (10 families, 240 prefixes), direct-generation contexts only.
- **Development:** families 125 and 146 (48 prefixes), outside every probe and the evaluation.

## Intervention

- **Target rule (one rule, no search).** Unused faces in ascending order. Three unused: if the first supplied face is less than the last, A moves each face's base logit one step forward, otherwise one step backward; B is the reverse. Two unused: A swaps when first < last and is the identity otherwise; B swaps when A does not. The target is base Qwen's full next-token distribution with only the unused faces' probabilities permuted, so unused mass, used faces and all other tokens are preserved.
- **Loss:** KL over the conditional unused distribution + full-vocabulary KL (weight 1).
- **Adapters:** low-rank additions to q, v, o and mlp.down projections of blocks 24-39 (0-based; the probe reads block 47), base weights and head frozen, one unconditional hook per layer, the same path in generation and forecasting. No prompt gating, no logit bias.
- **Schedule:** AdamW, cosine with 20-step warm-up, gradient clip 1, batch 10. c1: rank 8, lr 5e-4, 24 epochs. If either arm fails its development gate, c2: rank 16, lr 1e-3, 40 epochs, for both arms. The epoch with the lowest development loss (checked every 4) is kept. If c2 also fails it is used and labelled as failed. Seeds are in `manifest.json`.
- **Neutral:** A's trained weights, then the same schedule with the unpermuted base distribution as target. It carries adapter-sized drift with the base policy restored.
- **Disabled:** A's weights installed with the contribution multiplied by zero.

## Manipulation gates (per active arm, frozen)

Median |change| in unused-pair log odds >= 0.5 nats; preferred unused face switches on >= 20% of prefixes; median |change| in six-face-normalised unused mass <= 3 points. Checked on development (choice of config) and reported on the holdout, by roll. Digit mass is reported separately. Development also reports the share of the change explained by a fixed shift per roll and face pair, and favoured digits. The ground truth is always the measured adapted direct distribution.

## Measurement

All arms (base, disabled, A, B, neutral) x agent, shape and direct on the 192 holdout prefixes, with Experiment 36's capture code. Checks: archival replay; base bit-identical on repeat, hooks off and against Experiment 36; disabled bit-identical to base in scores and states; prompt and token hashes identical across arms. One greedy ten-roll G generation per arm is recorded descriptively.

Readouts (all frozen): agent probe (primary; face bias + activations, fitted on agent), raw forecast log odds, calibrated output, history + output, history + logits, history + output + activation (secondary), and the direct-state probe on direct states (portability control). History terms cancel in changes, so the history-only prediction of change is zero.

## Analysis

For each pair: actual change (adapted minus base direct log odds) and each readout's change. Weights: pairs within prefix, prefixes within family, families equal. Agent prompt primary.

- Correlation of actual and decoded change; error against a zero-change baseline (skill = 1 - MSE / zero-change MSE); slope; sign agreement. A, B and pooled A+B. 10,000 family bootstraps (PCG64 371125; 8 families, so intervals are rough). No rescaling.
- The probe against each output readout: difference in correlation and skill, same bootstrap draws.
- Wrong-history control: each decoded change paired with another history's actual change within arm, roll and face pair (1,000 shuffles, every history displaced).
- Fixed-digit control: both changes after removing the arm x roll x face-pair mean.
- A minus B within history. Shape with the agent-trained probe, no refit. Neutral and disabled.
- Favourite reversals, defined from direct behaviour alone, with examples (tracked, missed, forecast tracks).

**Reading.** Tracking by the frozen probe is claimed only if, for pooled A+B on agent, the correlation interval excludes zero and lies above the wrong-history 97.5% point, the demeaned correlation interval excludes zero, and both arms pass the holdout gates. An advantage over output requires the probe-minus-output interval to exclude zero for raw and calibrated output. If the base probe shows no credible signal in Experiment 36 (agent act-only against face bias), or the direct-state probe fails to follow a verified change, the swap result is exploratory or uninformative respectively. Even a clean positive does not show that Qwen uses the signal.

## Cost

Same instance as Experiments 35 and 36. Estimate: training under 45 minutes, evaluation about 30 minutes, $2. Self-imposed cap $10 for this experiment ($15 total for the shared rental).
