# Decision memo: LOULA_DICE_RECOGNITION v2.0 (2026-10-29)

**Decision: STOP after Stage A (prespecified hard stop). Go/no-go for a confirmatory study: NO-GO.**

## Trigger

Handoff §4.4 and §9: "If neither judge passes in either format, STOP the experiment after Stage A and report methodological failure."

| Judge | bare | brief |
|---|---|---|
| Qwen3-32B | FAIL (repeats: always "A"; 6s 16/24) | FAIL (repeats 19/24 correct and 9/12 consistent; gates 20 and 10) |
| Mistral Small 3.2 24B | FAIL (repeats: always "A"; 6s 8/12 consistent) | FAIL (6s 9/12 consistent; repeats 19/24 and 7/12) |

Primary-format freeze: no judge qualified. Stages B, C, D1 and D2: `NOT_RUN`.

## What was not done, deliberately

- No rerun of near-miss cells, no wording change, no gate relaxation.
- No Stage B on any judge, although Qwen brief nearly passed.
- No GPU.

Spend: $0.0074 of $5 (300 calls).

## What the stop tells us

- In free-text A/B form at temperature 0, both judges show position defaults whenever the content difference is small. On adjacent repeats in the bare format, they answer "A" every time.
- A one-sentence observation largely removes the default but leaves counting errors, often with incorrect stated counts.
- An obvious source rule (70% vs 5% repeats) is applied correctly. The real Qwen/Mistral difference is much subtler.
- The Experiment 22 null therefore remains uninterpretable as a self-recognition result. The bottleneck is the response instrument.

## Options (none authorized; each needs a new versioned protocol and approval)

1. **Open-weight scored choice (recommended).**
   - On the Experiment 21 A100 pipeline, read log P(A) − log P(B) for both orders and average them. This cancels position bias.
   - Calibrate first on the same Stage A battery, scored the same way.
   - It needs open weights for both models (Qwen3-32B is ready; Mistral Small 3.2 24B is also open) and a GPU budget approval, likely a few dollars.
2. **Structured-tally elicitation over the API.**
   - Ask for per-sample counts or features in a fixed format, then the answer.
   - Freeze it as v2.1 and rerun Stage A only. Proceed only if it passes.
   - Risk: this turns recognition into explicit feature computation.
3. **Park the recognition line.** Report Experiments 22–23 together: fingerprints exist (classifier), but these judges lack a validated two-alternative reading instrument at this resolution.
