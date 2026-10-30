# LOULA_DICE_YESNO_LOGPROB_v3.0 technical preflight

Overall: **PASS**.

Serving: `Qwen/Qwen3-32B` @ `9216db5781bf21249d130ec9da846c4624c16137`, bfloat16 weights and activations; lm_head and logits fp32, NVIDIA A100-SXM4-80GB (79.2 GB), driver 580.178.04, CUDA 12.8, torch 2.11.0+cu128, transformers 5.22.0, Python 3.11.9. Chat template sha256 `a55ee1b1660128b7…`. Labels: `Yes` id 9454, `No` id 2753. Model load 21.8 s.

## Gates

| Gate | Result |
|---|---|
| serving_recorded_and_revision_pinned | PASS |
| non_thinking_template_no_system_one_user_turn | PASS |
| labels_single_tokens_in_answer_context | PASS |
| greedy_first_token_Yes_or_No_4_of_5 | PASS |
| two_complete_contrasts | PASS |
| determinism_spread_lt_0.001 | PASS |
| epsilon_lt_1.0 | PASS |
| prompts_match_frozen_trial_list | PASS |

**Numerical floor:** delta = 0.04829 log-odds (max |c_prefill - c_tokenwise| over the two items); **epsilon = 0.09659** (max(0.05, 2.0 * delta)). Determinism spread over repeats: 0.

## Technical prompts

| Prompt | log P(Yes) | log P(No) | P(Yes)+P(No) | z (prefill) | z (tokenwise) | argmax | greedy completion | top 5 |
|---|---|---|---|---|---|---|---|---|
| pre\|MORE_SIXES-01\|X\|pos | -0.0814 | -2.5671 | 0.9986 | +2.4857 | +2.6572 | `Yes` | `'Yes'` | `'Yes'` -0.0814, `'No'` -2.5671, `'To'` -6.8784, `'Let'` -8.2296, `'In'` -9.8541 |
| pre\|MORE_SIXES-01\|Y\|pos | -0.5741 | -0.8347 | 0.9972 | +0.2606 | +0.4136 | `Yes` | `'Yes'` | `'Yes'` -0.5741, `'No'` -0.8347, `'To'` -6.3683, `'Let'` -7.0644, `'In'` -9.1291 |
| pre\|MORE_REPEATS-01\|X\|pos | -1.7735 | -0.1891 | 0.9974 | -1.5844 | -1.5056 | `No` | `'No.'` | `'No'` -0.1891, `'Yes'` -1.7735, `'Let'` -6.6668, `'To'` -6.7009, `'In'` -11.3019 |
| pre\|MORE_REPEATS-01\|Y\|pos | -3.7147 | -0.0273 | 0.9974 | -3.6874 | -3.5602 | `No` | `'No.'` | `'No'` -0.0273, `'Yes'` -3.7147, `'Let'` -6.2387, `'To'` -7.4363, `'First'` -10.5088 |
| pre\|GENERIC | -0.0000 | -11.4654 | 1.0000 | +11.4654 | +11.5734 | `Yes` | `'Yes'` | `'Yes'` -0.0, `'No'` -11.4654, `'yes'` -15.16, `'YES'` -16.6591, `' Yes'` -18.8518 |
