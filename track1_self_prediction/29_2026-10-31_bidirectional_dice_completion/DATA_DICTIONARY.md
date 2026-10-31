# Data dictionary (SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1)

## `conditions.csv` (152 rows)
cell_id `<predictor><-<source>-<instruction>-<fwdK|bwdK|mid>`; predictor; source (metadata only, never in the prompt);
source_instruction G/F; task_type primary/middle; direction forward/backward (empty for middle); k (empty for middle); diagonal
(predictor = source); original (the 10-roll ground truth); revealed_positions/values; missing_positions/values (target, in
output order); n_missing; prompt_id (shared by both predictors); prompt_sha256.

## `{preflight,main}/<predictor>/raw_attempts.jsonl`: one generation per line
kind (`archival` = Experiment 28 G/F prompt, `cell`); job (G, F or cell_id); replicate; order_index; trial_id; cell metadata;
prompt, prompt_sha256, rendered_prompt; content, generated_ids, completion_tokens, finish_reason; steps[] (token, token_id,
full-vocabulary logprob, face_logprobs {"1".."6"}, top5, entropy_bits; last = EOS when stopped); digit_steps[]; own_rescored[] and
own_rescored_full_pass[] on the rescored subset; rescore_tokens_equal; latency_ms; timestamp.

## `teacher_forced.jsonl`: one forced missing position per line
cell_id, predictor, source, source_instruction, task_type, direction, k, prompt_id, prompt_sha256; method (incremental = primary,
full_pass = floor); output_step (1 = first answer digit); original_position; true_face; forced_prefix (true answer digits before
this one) and forced_prefix_ids; face_logprobs (full-vocabulary log-probs of the six bare face tokens); argmax_token_id,
argmax_logprob (unconstrained next token).

## `analysis/`
positions.csv (one row per incremental teacher-forced position: p6, raw_mass, p_true, cond_loss = -ln p6[true], full_loss =
-ln p_full[true], argmax, margin, near_tie, top_correct, entropy_bits, source_ref_js); cells.csv (per cell: first_loss,
mean_loss, ..., free validity and accuracy); crossed_*.csv (2x2 matrices and contrasts); middle_*.csv; summary.json.
