# LOULA_DICE_AB_LOGPROB_v2.1 technical preflight

Overall: **PASS**.

Serving: `Qwen/Qwen3-32B` @ `9216db5781bf21249d130ec9da846c4624c16137`, bfloat16 weights and activations; lm_head and logits fp32, NVIDIA A100-SXM4-80GB (79.2 GB), driver 580.159.03, CUDA 12.8, torch 2.11.0+cu128, transformers 5.22.0, Python 3.11.9. Chat template sha256 `a55ee1b1660128b7…`. Labels: `A` id 32, `B` id 33. Model load 19.3 s.

## Gates

| Gate | Result |
|---|---|
| serving_recorded_and_revision_pinned | PASS |
| non_thinking_template_no_system_one_user_turn | PASS |
| labels_single_tokens_in_answer_context | PASS |
| greedy_first_token_A_or_B_4_of_5 | PASS |
| two_complete_pairs | PASS |
| determinism_spread_lt_0.001 | PASS |
| epsilon_lt_1.0 | PASS |
| prompts_match_frozen_trial_list | PASS |

**Numerical floor:** delta = 0.02902 log-odds (max |S_prefill - S_tokenwise| over the two pairs); **epsilon = 0.05804** (max(0.05, 2.0 * delta)). Determinism spread over repeats: 0.

## Technical prompts

| Prompt | log P(A) | log P(B) | P(A)+P(B) | d (prefill) | d (tokenwise) | argmax | greedy completion | top 5 |
|---|---|---|---|---|---|---|---|---|
| pre\|MORE_SIXES-01\|XA | -0.0137 | -5.1179 | 0.9924 | +5.1042 | +5.0618 | `A` | `'A'` | `'A'` -0.0137, `'B'` -5.1179, `'Let'` -5.5083, `'Sample'` -5.7766, `'Count'` -8.5446 |
| pre\|MORE_SIXES-01\|XB | -0.0866 | -2.7235 | 0.9827 | +2.6370 | +2.6049 | `A` | `'A'` | `'A'` -0.0866, `'B'` -2.7235, `'Let'` -4.5883, `'Sample'` -5.1193, `'First'` -7.5971 |
| pre\|MORE_REPEATS-01\|XA | -0.1746 | -2.3869 | 0.9317 | +2.2124 | +2.2738 | `A` | `'A'` | `'A'` -0.1746, `'B'` -2.3869, `'Let'` -3.0194, `'Sample'` -4.5783, `'To'` -5.336 |
| pre\|MORE_REPEATS-01\|XB | -0.9634 | -0.8460 | 0.8107 | -0.1173 | +0.0022 | `B` | `'B'` | `'B'` -0.846, `'A'` -0.9634, `'Let'` -1.877, `'Sample'` -3.6123, `'To'` -5.3196 |
| pre\|GENERIC | -0.0000 | -16.0548 | 1.0000 | +16.0548 | +16.0367 | `A` | `'A'` | `'A'` -0.0, `'Option'` -15.0244, `'B'` -16.0548, `'The'` -16.626, `'Answer'` -17.276 |
