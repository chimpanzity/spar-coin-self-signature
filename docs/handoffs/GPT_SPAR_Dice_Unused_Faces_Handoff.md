# SPAR dice follow-up for Claude Code

Run a quick offline reanalysis of Experiment 33. When the roller is described as *angry*, does Qwen get better at guessing that the next face will be unused? Or, among the unused faces, does it get better at predicting **which one Qwen itself favors**?

Use the archived probabilities. The word *angry* was selected after seeing Experiment 33, so label this analysis exploratory. It requires no model calls or GPU rental.

## Inputs and sanity check

Use `chimpanzity/spar-coin-self-signature`, with Experiment 33 results at commit `025e50dcbdd5ee889f96cf5ea450184d1571faea`. Reuse `Data`, `bank`, `unused_faces`, and `js` from `src/spar_dynamic/dice_scaffolding/analysis.py`. Use Qwen as the forecaster and the two **uncued direct-generation** distributions as targets. Mistral’s difficulty answering forecast prompts does not affect its use as a direct-generation target.

Pair the plain T1 forecasts for “a shape” and “a shape described as angry” at identical histories. As a loader check, reproduce the published full six-face gains over the 84 confirmation histories, rounded to three decimals: **+0.088 bits** toward Qwen and **+0.086 bits** toward Mistral. Then narrow the primary analysis to rolls **4 and 5** in `bank("confirmation")`. These give 24 paired histories across 12 opening families, with three or two unused faces respectively. Roll 6, with only one unused face, is a useful check for repeat avoidance alone.

## Two measurements on each history

1. **Does the cue help Qwen predict an unused face?** Sum the forecast probabilities of the unused faces under each prompt. Report the change from neutral to angry in percentage points. Also report the actual unused-face probability for each target and whether the cue reduced the absolute error against it. Increasing unused-face probability helps only when it moves the forecast closer to the target.
2. **Does the cue help Qwen predict its own preference among those faces?** Restrict each of the four distributions (neutral forecast, angry forecast, Qwen target, Mistral target) to the same unused faces and renormalize each to sum to one. For each target compute the Jensen–Shannon divergence in bits from neutral and from angry. Define gain as neutral divergence minus angry divergence. Report Qwen gain, Mistral gain, and their paired difference **Qwen gain − Mistral gain**. These are separate diagnostics from the full six-face score. Omit a conditional score if its denominator is zero and report the count.

**Decisive comparison.** Select histories where the two direct-generation targets have different, unique favorite unused faces. Select using target vectors alone and report the number of histories and families retained. On these same histories, report both conditional gains above. Also show how the cue changed Qwen’s conditional forecast probability for **Qwen’s favorite** and for **Mistral’s favorite**. This directly tests whether the cue shifts probability toward the face that distinguishes Qwen from Mistral. If the subset is sparse, show the individual histories and describe the uncertainty.

## Worked example and output

Look up the exact prefix **5, 2, 6** in the archived core and extension forecasts (`Data(phases=("core", "extensions"))`). If matched records exist, show one small table with columns for faces **1, 3, 4** and total probability on unused faces. Use rows for Qwen’s neutral forecast, Qwen’s angry forecast, and each model’s direct generation. Show the original six-face-normalized probabilities in the table so the three entries add to the unused total. State whether the *share* assigned to 3 among the unused faces increased and whether the two targets actually disagree here. If that prefix lacks a matched condition, say so and show the first eligible disagreement history by family ID and roll. Keep the example separate from the aggregate.

Average within opening family first, then across contributing families. Give paired 95% bootstrap intervals by resampling whole families with a fixed seed, retaining both prompts and targets together. Report the family count beside each estimate. If just one family contributes, show its values without an interval.

Put a reproducible script, a per-history CSV, and a short Markdown report in a new follow-up folder alongside Experiment 33. Include the command to rerun it. End with a plain-language verdict: did *angry* improve repeat avoidance, the ordering of unused faces for both targets, or the prediction of Qwen’s distinctive preferences? More than one can hold. Claim Qwen-specific improvement only if Qwen’s conditional gain is positive and exceeds Mistral’s on disagreement histories, with uncertainty supporting both. Describe ambiguous results as such.
