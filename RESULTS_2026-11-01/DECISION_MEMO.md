# Decision memo: Experiment 30 (six-roll self-recognition)

2026-11-01 · For the investigator · Full results in [REPORT.md](REPORT.md)

## Result in one line

Both judges passed every gate. Neither recognises its own ordering of rolls 5–6 better than the other model does: swap
D_G = −0.28 and D_F = −0.03 log-odds, with every swap pair order-inconsistent. Both generative policies favour the authentic
endings, but the advantage is generic: the other model's policy favours them more strongly for 3 of 4 sources.

## Outcome by question

| Question | Outcome |
|---|---|
| Own-source SWAP discrimination (primary) | **No.** S is −0.52 to +0.34 everywhere, inside both floors (ε 0.99 Qwen, 0.51 Mistral). The crossed D is negative in both frames. |
| Shared no-repeat rule (REPEAT, secondary) | **Generic, mainly Qwen.** Qwen's S is 3.7–5.6 (self frame) on all sources, higher on Mistral's than its own; Mistral's S is ≤ 1.3. Order-robust in 1 of 16 items. |
| Self frame vs neutral frame | The self frame raises Qwen's A bias and its repeat preference equally across sources. D_self − D_neutral: −0.08 / +0.03 (swap), −0.31 / −0.61 (repeat). No self-specific effect. |
| Generation vs recognition | **Dissociated.** Policy Δ is 0.8–7.9 nats (swap) and 8–19 nats (repeat); recognition S does not follow it. |
| Instrument | Both gated reading tasks pass 6/6 in both orders. But the swap-structured "roll 5 > roll 6" check is order-robust in only 3/6 (Qwen) and 0/6 (Mistral) items. An A bias of 2–7 log-odds dominates main. |

## What this means for the self-prediction line

Experiments 26–30 agree. Prediction framing changes the opening, not the continuation (28). Reconstruction shows no
self-advantage (27, 29). Now, minimal-pair recognition shows none either (30).

The one place where the models differ consistently is their **generative policy**. That difference is visible to either
model's next-token distribution, and it is not privileged to the source. On these dice tasks no behavioural evidence of
self-specific knowledge has appeared at any level.

## Recommended next steps (not run)

1. **Report 26–30 together at the midterm** as a consistent negative, with two methodological lessons:
   - source difficulty and generic structure confound fixed-string designs;
   - A/B answer bias swamps subtle content in single-token judgments, even after calibration passes.
2. **Do not iterate on this A/B prompt.** The roll-5/6 reading weakness would need a new instrument, and any change is a new,
   versioned protocol. One candidate: score the authentic and foil strings separately, as log P(string) under a "which would
   your model produce" continuation, instead of choosing between A and B labels.
3. **If recognition is pursued further,** use many sampled sequences per source (Experiment 27's corpus) so that items are
   not four coincidences. Gate the instrument on the exact structure being tested (here: the order of two adjacent rolls).
4. **Qwen's numerical floor (ε 0.99) deserves a note in any A/B work on this stack.** Feeding the prompt token by token rather
   than in one prefill moves d by up to 0.5 log-odds.

## Cost

One A100 for 0.36 h of GPU time; $2.09 billed in total (most of it the 103 GB model download). The instance is destroyed.
