# Data dictionary (SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0)

## `conditions.csv` (64 rows) and `calibration_items.csv` (18 rows)
cell_id `<judge><-<frame>-<source>-<G|F>-<swap|repeat>-o<1|2>`; judge; frame self/neutral; source (the model that emitted the
string; never in the prompt); source_instruction G/F; foil_type; orientation (1: A = authentic); diagonal (judge = source);
item_id; source_sequence10; authentic; foil; seq_A; seq_B; authentic_label; prompt_id (shared by both judges); prompt_sha256.
Calibration: cal_id, task (last_digit / all_faces / order56), gated, question, correct, foil.

## `{preflight,calibration,main}/<judge>/presentations.jsonl`: one call per line
prompt_id, replicate, order_index, trial_id, the cell metadata, prompt, prompt_sha256, rendered_prompt_sha256, prompt_tokens;
logp_A, logp_B (full-vocabulary log-probs of the label tokens at the first answer position, prefill arithmetic), logp_space_A/B,
argmax_id/token/logprob, entropy_nats, top [[id, text, logprob]]; d, mass_AB, pA; greedy_ids, greedy_text, finish_reason,
greedy_letter, strict_valid; on replicate 1: logp_A_tokenwise, logp_B_tokenwise, d_tokenwise, abs_delta_d; latency_ms.

## `preflight/<model>/archival.jsonl`
Experiment 28 G and F prompts regenerated (x2): content, generated ids, steps with six face log-probs, digit_steps.

## `policy_benchmark/<scorer>/policy_teacher_forced.jsonl`
scorer, source, source_instruction, source_id, candidate (authentic/swap/repeat), history (six rolls), diagonal; method
(incremental = primary, full_pass = floor); position 1-6; history_face; face_logprobs (full-vocabulary log-probs of the six
bare face tokens before that face); argmax_token_id, argmax_logprob.

## `analysis/`
policy_likelihoods.csv, policy_deltas.csv, recognition_presentations.csv, paired_scores.csv, crossed_contrasts.csv,
self_vs_neutral_items.csv, summaries.csv, calibration_gate.json (both judges), summary.json, figures/.
