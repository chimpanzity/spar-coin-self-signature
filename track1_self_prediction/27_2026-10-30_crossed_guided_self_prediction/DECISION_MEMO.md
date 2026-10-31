# Decision memo: Experiment 27 (crossed Qwen × Mistral guided self-prediction)

**Status:** complete. Both models, all four predictor × generator cells, all 9 arms × 6 history conditions: 5,400 trials,
all main checks PASS. GPU spend $12.12 of the $15 cap. Full detail: [reports/REPORT.md](reports/REPORT.md).

## What we learned

1. **No self-advantage when a model predicts.** Across 48 sampled targets (37 distinct strings), the predictor ×
   generator interaction is −0.006 bits JS [−0.026, 0.011]. KL, TV, log score, all-arm and tempered variants are also null.
   On the single next roll, the *other* model is closer: −0.089 [−0.119, −0.048].
2. **The self-advantage lives in generation, not prediction.** Each model's plain generation policy matches its own
   targets exactly and the other model's at 0.14–0.20 bits. Wrapping the same history in a prediction prompt puts every
   cell, self included, 0.34–0.36 bits from the target in the AH arm (0.30–0.41 across all arms).
3. **Experiment 26's `3 1 4` was not self-knowledge.** Mistral produces `3 1 4` after Qwen's `5 2 6`, under the anonymous
   prompt, where Qwen itself does not.
4. **Identity cues are prompt effects.**
   - Naming the target helps both predictors on both targets (DiD +0.001 [−0.003, 0.005]).
   - "Your own model" vs "not your own model" gives a 0.011-bit diagonal effect on Qwen targets. It is wording-confounded,
     coincides with Mistral refusing to answer in digits, and is not estimable under the mass sensitivity filter.
5. **Showing an earlier real output of the target model makes predictions worse** in all four cells (+0.03 to +0.07 bits).
6. Qwen's G-vs-F gap from Experiment 21 reproduces exactly. Mistral's hypothetical framing moves its first roll much less.

## Rival explanations (handoff §1)

| Explanation | Verdict |
|---|---|
| (a) target predictability | Controlled: the reference is the target's own distribution, and the contrasts are paired per target |
| (b) general predictor competence | Present: under KL and log score Mistral is the better predictor on both targets |
| (c) shared generation style | Present in the native policy only; it does not carry over into prediction |
| (d) prompt changes regardless of relevance | Present: T, I and R move both predictors, with effect sizes like the irrelevant die fact |
| (e) identity-sensitive self-modelling | No support beyond one small, confounded R contrast |

## Recommendations

- **Stop treating verbal self-prediction of die rolls as a self-knowledge probe** for these models. The prediction framing
  overrides the generation policy. Any "self" signal must first beat the native-policy baseline, which nothing here does.
- If the track continues, the informative direction is **why prediction prompts abandon the native policy.** Cheap
  measurements of this are now in place: prediction vs native on identical histories, by position and model. A logit-lens
  or activation-patching study on Qwen could locate where the wrapper overrides the policy.
- Any future Mistral prediction work needs a format fix that the investigator approves before collection, for example a
  prefilled assistant answer or a stricter answer template. Prose-first responses leave only 21–57% average digit mass at
  the first scored position.
- Budget future rentals with **disk and bandwidth** included. On this host they were 49% of the bill.
