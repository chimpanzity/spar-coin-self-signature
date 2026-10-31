# Amendment v1.1: prediction-prompt format is reported, not gated

Protocol: SPAR_DICE_LOGPROB_CROSSMODEL_v2.0 (`PROTOCOL_FROZEN.md`, frozen at commit `562421f`). The investigator decided this
rule on 2026-10-31 **before** any preflight data existed ("if Mistral's S or W outputs are not numeric-only: proceed and report
it"). It was applied after the Mistral preflight and before any main-run data.

## What failed
Mistral preflight gate `format_all_conditions`. Every other gate passed (11/12), including the exact regression to
Experiment 27 (G and F identical, max |dp| = 0.0). S1-S10 were all valid single digits. All three window prompts were answered
with a prose preface, then digits:

| Condition | Output (verbatim) |
|---|---|
| W1-5 | `Here is the predicted output for the first 5 integers of the 10 simulated die rolls:\n\n3 1 6 4 2` |
| W3-7 | `Here is the predicted output for the sequence of 10 simulated die rolls, followed by the requested subset (positions 3 through 7):\n\n```\n2 5 3 1 6 4 2 5 3 1\n3 1 6 4 2\n```` |
| W6-10 | `Here is the predicted output for the last 5 integers (positions 6 through 10) of a simulated 10-roll sequence of a six-sided die:\n\n```\n3 1 5 2 6\n```` |

Qwen passed all 12 gates; its format gate is unaffected.

## Change
1. Gate `format_all_conditions` becomes information (`format_all_conditions_reported`), for both models. `format_references`
   (G and F numeric-only, gated) is unchanged, so matched-prefix scoring still rests on valid references.
2. Strict parsing is unchanged. A prose answer is **invalid**: it contributes no free-output face at any original position, is
   never re-encoded as faces, and is never substituted. Its first-token six-face vector is reported only with its raw six-face
   mass, labelled as conditional on emitting a face, as in Experiment 27 amendment v1.1.
3. The digits inside prose answers are quoted verbatim in the report as a descriptive observation and are never scored.
4. The window prompts' teacher-forced matched-window rows are kept (prespecified). Their raw six-face mass at the first forced
   position is low for Mistral (0.23-0.40 in preflight) because the model would rather write words first. This is reported
   next to every matched-window comparison.

Prompts, models, serving, sample size, seeds, all other gates and the analysis plan are unchanged.
