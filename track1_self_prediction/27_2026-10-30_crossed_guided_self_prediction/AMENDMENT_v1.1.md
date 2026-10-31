# Amendment v1.1: six-face mass is gated for direct generation, reported for prediction prompts

Protocol: SPAR_CROSSED_GUIDED_SELFPRED_v1.0 (`PROTOCOL_FROZEN.md`, unchanged). Approved by the investigator on 2026-10-31 (UTC),
after the Mistral preflight and before any Mistral corpus, trial file or prediction data existed. The Qwen corpus had been
collected under the unamended protocol; it uses the G prompt only and is unaffected.

## What failed
Mistral preflight gate `face_logprobs` (raw six-face mass >= 0.5 at every scored digit step) failed at three steps, all the
first digit of a response to a prompt where Mistral prefers to begin in prose:

| Record | Step | Raw six-face mass |
|---|---|---|
| crossed format check TD, m3 (teacher-forced) | position 7 (first forced) | 0.335 |
| crossed format check RI, k8 (teacher-forced) | position 9 (first forced) | 0.310 |
| Experiment 21's Fanon prompt, matched prefix on Mistral's G | position 1 | 0.430 |

Every other digit step, including all G-prompt steps, has mass >= 0.72 (almost all ~1.0). The face tokens, tokenisation,
logits and scorer checks all pass. The low mass means the model would usually write words first; it does not make the
six-face distribution wrong.

## Change
1. Preflight: `face_logprobs` is split into
   - `face_logprobs_finite` (gated): every stored face log-probability is finite;
   - `face_mass_direct_generation` (gated, >= 0.5): every digit step of a G-prompt generation (greedy and sampled) and every
     G-instruction matched-prefix row;
   - prediction-prompt mass (F, Fanon, Experiment 26 prompts, crossed prompts): reported, not gated.
2. Main checks: `policy_G_face_mass` (gated, >= 0.5) on every G-instruction policy row; prediction mass is reported, as before.
3. Analysis: the primary metric stays the six-face renormalised distribution, i.e. the prediction conditional on emitting a
   die face. Added: raw six-face mass by cell and arm (`mass_by_cell_arm.csv`) and sensitivity estimands E1s/E3s that keep
   only trials whose raw mass is >= 0.5 at every scored position (items without a surviving trial for both predictors drop out).

Prompts, models, serving, corpus sizes, seeds, trials and all other estimands are unchanged.
