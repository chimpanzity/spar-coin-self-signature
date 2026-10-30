# Decision memo: LOULA_DICE_AB_LOGPROB v2.1 (2026-10-30)

**Decision: STOP after Stage A (prespecified). Recognition screen: `NOT_RUN`. No confirmatory study.**

## Trigger

Handoff §6: "If either gate fails: STOP before the recognition screen."

| Criterion | Required | Observed | |
|---|---|---|---|
| S_correct > ε (ε = 0.058) | ≥ 29/36 | 36/36 | ✓ |
| Generator rule | ≥ 10/12 | 12/12 | ✓ |
| More 6s | ≥ 9/12 | 12/12 | ✓ |
| More adjacent repeats | ≥ 8/12 | 12/12 | ✓ |
| Correct in both orders | ≥ 24/36 | **20/36** | ✗ |

## What was not done, deliberately

- No AUTH, TYP or named-model scoring, although the GPU was already running and the screen would have taken seconds.
- No rescoring with other label wording, no reasoning, no model names in calibration, no moved threshold, no change to ε.
- No Mistral judge, no new stimuli.

Spend: about $0.28 of the $8 GPU cap (13.9 minutes on one A100-SXM4-80GB). Instance destroyed. No OpenRouter calls.

## What the stop tells us

- **Positive:** Qwen3-32B's next-token distribution is content-sensitive on all 36 reading-check items once the constant A/B bias is averaged out. The emitted "A" default (Experiments 22–23) hid real information. This is the first instrument in the line to show that.
- **Negative:** a large "A" bias (about +2.7 log-odds on average) wins in the B orientation on 16/36 items. On adjacent repeats, the content effect (about +0.7) is no larger than the bias. Order-robust discrimination therefore fails the prespecified bar.
- **For recognition:** the Qwen-vs-Mistral difference is subtler than any calibration task, so its scores would likely fall in the weak, bias-dominated regime where this pilot could not show order robustness.

## Options (none authorized; each needs a new versioned protocol and new stimuli)

1. **Accept the order-averaged score as the instrument, with a new gate.**
   - Freeze a gate on S alone (it passed 36/36 here), plus an explicit check of order-by-content interaction.
   - Validate it on **new** calibration items, including subtler feature differences closer to the real phenotype (face frequencies, specific transitions).
   - Then score fresh held-out recognition pairs.
   - The cost is GPU minutes, but the trade-off is the one the handoff warned about: a subtractive score can hide an interaction between content and order.
2. **Reduce the label bias by design, not by subtraction.**
   - For example, neutral labels (two arbitrary symbols, counterbalanced) or asking "Is Sample 1 more likely…? Yes/No" for each sample separately.
   - Recalibrate first, on new items.
3. **Park the recognition line.**
   - Report Experiments 22–24 together: fingerprints exist (classifier AUC about 0.72–0.76).
   - Emitted A/B judgments are position defaults, but the underlying probabilities do read obvious content.
   - Order-robust reading of small differences is not established.
