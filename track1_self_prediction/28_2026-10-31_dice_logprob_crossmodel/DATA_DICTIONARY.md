# Data dictionary (SPAR_DICE_LOGPROB_CROSSMODEL_v2.0)

## `{preflight,main}/<model>/raw_attempts.jsonl`: one generation per line
| Field | Meaning |
|---|---|
| study, stage, model, model_id, model_commit | study tag; preflight/main; qwen/mistral; HF repo and pinned commit |
| trial_id, condition, condition_type, replicate, order_index | `<model>-<cond>-<rep>`; G, F, S1..S10, W1-5, W3-7, W6-10; type G/F/S/W; 1..20; position in the seeded shuffled job order |
| target_positions, n_expected | original serial positions (1-based) in output order; number of faces a valid answer has |
| prompt, prompt_sha256, rendered_prompt, rendered_prompt_sha256, prompt_tokens | user message, its SHA-256, the chat-templated text, token count |
| content, generated_ids, completion_tokens, finish_reason | decoded output; generated token ids (EOS excluded); `stop` = EOS, `length` = 128-token cap |
| steps[] | every decoding step: token, token_id, logprob (full vocabulary), face_logprobs {"1".."6": full-vocabulary log-prob of each bare face token}, top5 [[id, logprob]], entropy_bits; last step is EOS when finish_reason = stop |
| digit_steps[] | the steps whose chosen token is a face (same fields) |
| own_rescored[], own_rescored_full_pass[] | teacher-forced six-face rows for this output (incremental; one full forward pass); present on the rescored subset |
| rescore_tokens_equal, rescored_subset | re-encoding the content gives the generated ids; main: first record of this (condition, output) |
| latency_ms, timestamp, decoding | generation wall time; UTC; decoding rule |

## `matched_prefix.jsonl`: one teacher-forced face position per line
| Field | Meaning |
|---|---|
| kind | `mp` (G or F instruction over a full reference) or `window` (a W prompt over a reference's window) |
| instruction, history, history_sequence | prompt condition; G or F reference; the forced assistant text |
| method | `incremental` (generation arithmetic, primary) or `full_pass` (numerical floor only) |
| position, original_position | index within the forced text; original serial position |
| history_face, face_logprobs, argmax_token_id, argmax_logprob | forced face; six bare-face full-vocabulary log-probs before it; the unconstrained argmax |

## Derived (analysis/)
p6 = face log-probs renormalised over the six faces; mass = their summed raw probability. JS = Jensen-Shannon divergence in bits
(0..1). Floor = max |dp6| between incremental and full-pass scoring of the same rows; near-tie = top-two margin below the floor.
