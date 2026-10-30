# Decision memo: LOULA_DICE_YESNO_LOGPROB v3.0 (2026-10-30)

**Decision: STOP after Stage A (prespecified). Recognition screen: `NOT_RUN`.**

## Trigger

| Criterion | Required | Observed | |
|---|---|---|---|
| S > ε (ε = 0.097) | ≥ 29/36 | 32/36 | ✓ |
| Generator rule | ≥ 10/12 | 12/12 | ✓ |
| More 6s | ≥ 9/12 | 12/12 | ✓ |
| More adjacent repeats | ≥ 8/12 | 8/12 | ✓ |
| Correct under both questions | ≥ 24/36 | **20/36** | ✗ |

## What was not done, deliberately

- No recognition scoring, although the GPU was running and the screen would have taken under a minute.
- No rewording of the reversed questions, no pos-only rescoring under a new gate, no new items, no moved threshold or ε.

Spend: about $0.18 of the $5 cap (8.2 minutes on one A100-SXM4-80GB). Instance destroyed. No OpenRouter calls.

## What the stop tells us

- **Positive:** removing the A/B label worked as intended. The 6s task, which Experiment 24's "A" bias broke (4/12 in both orders), is now 12/12 under both questions. Response bias can no longer enter a score.
- **Negative:** for adjacent repeats and the generator rule, the model's answer to the reversed question ("fewer repeats?", "from S?") barely moves with the sequence. Only one wording carries the content.
- **Across 22–25:** four instruments have now been tried:
  - emitted A/B letters (22–23);
  - A/B probabilities averaged over orders (24);
  - single-sample Yes/No in both wordings (25).
  
  Each shows that Qwen3-32B's output distribution tracks obvious dice content. None passes a robustness check on repeat-type structure, which is the kind of difference that separates Qwen's and Mistral's sequences.

## Options (none authorized)

1. **Park the recognition line and write up 22–25 together (recommended).**
   - Fingerprints exist (classifier AUC about 0.72–0.76).
   - Emitted A/B judgments are position defaults; probabilities read obvious content.
   - Neither label-bias correction nor single-sample scoring yields reading that survives a change of wording or order on subtle sequential features.
   - A self-recognition test built on these instruments would not be interpretable.
2. **Adopt the single-question contrast as the instrument (new protocol).**
   - Score only the positive wording (`c_pos`), which is bias-free by construction and had c_pos > ε on 32/36 items here (6s 12, repeats 8, generator 12).
   - Replace the both-wordings check with a different robustness check, for example two paraphrases of the same positive question.
   - This needs fresh items and a fresh freeze. The c_pos result above came from this run, so it cannot validate itself.
3. **Run the recognition screen as an explicitly exploratory look**, accepting a failed calibration gate. Not recommended: a null or a positive would both be uninterpretable for the reason the gate exists.
