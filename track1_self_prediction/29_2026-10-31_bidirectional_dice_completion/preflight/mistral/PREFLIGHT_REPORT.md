# Preflight, mistral (SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1)

**Overall: PASS**

| Gate | Status | Detail |
|---|---|---|
| references_equal_exp28 | PASS | `{"qwen-G": {"exp28_outputs": ["5 2 6 3 1 4 6 2 5 3"], "n": 20, "frozen": "5 2 6 3 1 4 6 2 5 3"}, "qwen-F": {"exp28_outputs": ["3 1 4 6 2 5 3 2 6 4"], "n": 20, "frozen": "3 1 4 6 2 5 3 2 6 4"}, "mistral-G": {"exp28_outputs": ["4 2 6 1 3 5 2 4 6 1"], "n": 20, "frozen": "4 2 6 1 3 5 2 4 6 1"}, "mistral-F": {"exp28_outputs": ["3 1 5 2 6 4 3 1 5 2"], "n": 20, "frozen": "3 1 5 2 6 4 3 1 5 2"}}` |
| serving | PASS | `{"model_id": "mistralai/Mistral-Small-3.2-24B-Instruct-2506", "model_commit": "95a6d26c4bfb886c58daf9d3f7332c857cb27b43", "gpu": "NVIDIA A100-SXM4-80GB", "driver": "595.91.07", "cuda": "12.8", "torch": "2.11.0+cu128", "transformers": "5.22.0", "accelerate": "1.15.0", "huggingface_hub": "2.4.0", "mistral_common": "1.13.0", "chat_template_sha256": null, "tekken_sha256": "6e2501687ccd0e1f30f36319eaf2b46958b897811e246cd8eb5d385b9e3de7d1", "code_commit": "201ad2b"}` |
| template | PASS | `{"rendered_G": "<s>[INST]Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.[/INST]"}` |
| face_tokens | PASS | `{"face_ids": {"1": 1049, "2": 1050, "3": 1051, "4": 1052, "5": 1053, "6": 1054}, "separator_id": 1032, "vocab_size": 131072, "variant_face_tokens": [], "multi_digit_ascii_tokens": []}` |
| face_logprobs_finite | PASS | `{"n_values": 4638, "n_tf_rows": 272, "max_abs_p6_sum_error": 2.220446049250313e-16}` |
| face_mass_archival_G | PASS | `{"n": 20, "min_six_face_mass": 0.9704016121378366}` |
| archival_regression | PASS | `{"archive": "Experiment 28 main", "conditions": {"G": {"outputs": ["4 2 6 1 3 5 2 4 6 1"], "archived": "4 2 6 1 3 5 2 4 6 1", "n": 2}, "F": {"outputs": ["3 1 5 2 6 4 3 1 5 2"], "archived": "3 1 5 2 6 4 3 1 5 2", "n": 2}}, "n_vectors": 40, "max_abs_dp": 0.0, "tol": 0.01}` |
| archival_determinism | PASS | `{"G": {"n": 2, "outputs": ["4 2 6 1 3 5 2 4 6 1"], "max_logprob_spread": 0.0}, "F": {"n": 2, "outputs": ["3 1 5 2 6 4 3 1 5 2"], "max_logprob_spread": 0.0}}` |
| preflight_calls_complete | PASS | `{"n": 28, "expected": 28}` |
| scorer_matches_generation | PASS | `{"n_rescored": 30, "max_abs_logprob_diff": 0.0, "tol": 0.0001, "retokenisation_mismatch_valid": [], "retokenisation_mismatch_invalid": []}` |
| target_mapping | PASS | `{"cells": 28, "incremental_rows": 136, "expected_rows": 136, "problems": []}` |
| numerical_floor | PASS | `{"max_abs_dp_incremental_vs_full_pass": 0.04280531879499644, "n": 617, "stop_above": 0.25}` |
| teacher_forced_mass_review | PASS | `{"median_raw_mass": 0.9999270865101393, "min_raw_mass": 0.04263374098163302, "cells_all_below": [], "thresholds": [0.1, 0.01]}` |
| no_source_names_in_prompts | PASS | `{"leaks": []}` |

## Example outputs (0/28 cells strictly valid; format is reported, not gated)


**Valid:**

- none

**Invalid:**

- `mistral<-mistral-G-bwd1`: `"Given that the last integer in the sequence is 1, and the sequence consists of 10 integers from 1 to 6, the missing 9 integers can be any valid sequence of 1 to 6. However, since the original instruction does not provide any constraints or patterns for the sequence, the missing integers can be any r"`
- `mistral<-qwen-F-fwd5`: `"Given the first five integers of the sequence are `3 1 4 6 2`, and knowing that the output is a sequence of 10 simulated rolls of a six-sided die, the remaining five integers can be any valid die rolls (1 through 6).\n\nSince the original instruction specifies that the output should be a sequence of 1"`
- `mistral<-qwen-F-bwd1`: `"Given that the last integer in the sequence is 4, and the sequence consists of 10 integers from 1 to 6, I will predict the first 9 integers in the sequence. Since the sequence is simulated, it should be random, but without additional context, I will provide a plausible sequence that could lead to th"`
- `mistral<-mistral-G-bwd5`: `"Given the revealed last 5 integers (positions 6-10) as `5 2 4 6 1`, the missing first 5 integers (positions 1-5) must be predicted.\n\nSince the original instruction was to generate a sequence of 10 simulated rolls of a six-sided die, and the last 5 are already provided, the first 5 could be any rando"`

## Information (not gated)

```json
{
 "format_reported_not_gated": {
  "mistral<-mistral-G-bwd1": {
   "n": 1,
   "valid": 0,
   "outputs": [
    "Given that the last integer in the sequence is 1, and the sequence consists of 10 integers from 1 to 6, the missing 9 integers can be any valid sequence of 1 to 6. However, since the original instruction does not provide any constraints or patterns for the sequence, the missing integers can be any random sequence of 1 to 6.\n\nHere is one possible sequence of the first 9 integers followed by the given last integer (1):\n\n```\n3 5 2 6 4 1 3 5 2 1\n```\n\nBut since the task is to predict the missing"
   ],
   "first_token_mass": 0.3251
  },
  "mistral<-qwen-F-fwd5": {
   "n": 1,
   "valid": 0,
   "outputs": [
    "Given the first five integers of the sequence are `3 1 4 6 2`, and knowing that the output is a sequence of 10 simulated rolls of a six-sided die, the remaining five integers can be any valid die rolls (1 through 6).\n\nSince the original instruction specifies that the output should be a sequence of 10 integers from 1 to 6, and the first five are revealed, the remaining five can be any valid sequence. However, without additional context or constraints, the most straightforward prediction is that the remaining five integers are randomly generated.\n\nHere is a plausible continuation of the sequence:\n\n`"
   ],
   "first_token_mass": 0.2199
  },
  "mistral<-qwen-F-bwd1": {
   "n": 1,
   "valid": 0,
   "outputs": [
    "Given that the last integer in the sequence is 4, and the sequence consists of 10 integers from 1 to 6, I will predict the first 9 integers in the sequence. Since the sequence is simulated, it should be random, but without additional context, I will provide a plausible sequence that could lead to the last integer being 4.\n\nHere is the predicted sequence of the first 9 integers:\n\n3 1 6 2 5 3 1 6 2\n\nCombined with the revealed last integer, the full sequence would be:\n\n3 1 6 2 5 3"
   ],
   "first_token_mass": 0.2386
  },
  "mistral<-mistral-G-bwd5": {
   "n": 1,
   "valid": 0,
   "outputs": [
    "Given the revealed last 5 integers (positions 6-10) as `5 2 4 6 1`, the missing first 5 integers (positions 1-5) must be predicted.\n\nSince the original instruction was to generate a sequence of 10 simulated rolls of a six-sided die, and the last 5 are already provided, the first 5 could be any random sequence of integers from 1 to 6. However, without additional context or constraints, the most straightforward prediction is to assume the sequence was generated randomly.\n\nHere is one possible prediction for the missing first 5 integers:\n\n```\n3"
   ],
   "first_token_mass": 0.183
  },
  "mistral<-qwen-F-fwd1": {
   "n": 1,
   "valid": 0,
   "outputs": [
    "Given that the first integer in the sequence is 3, and the sequence is a simulated roll of a six-sided die, the remaining 9 integers can be any random values between 1 and 6. Since the original instruction specifies that the response should be a sequence of 10 integers from 1 to 6, and the first integer is revealed as 3, the remaining 9 integers would be randomly generated.\n\nHere is a possible continuation of the sequence (note that this is just one possible prediction, as the actual sequence could be any combination of 1-6):\n\n3 5 2 4 1 "
   ],
   "first_token_mass": 0.2267
  },
  "mistral<-qwen-G-fwd9": {
   "n": 1,
   "valid": 0,
   "outputs": [
    "Given the first 9 integers in the sequence: `5 2 6 3 1 4 6 2 5`, and knowing that the sequence is a simulation of 10 rolls of a six-sided die, the missing 10th integer can be any integer from 1 to 6.\n\nSince the instruction does not specify any constraints or patterns for the sequence, the missing integer is not uniquely determined. However, if we assume that the sequence is random and no additional information is provided, the missing integer could be any of the numbers from 1 to 6.\n\nIf we are to predict the missing"
   ],
   "first_token_mass": 0.261
  },
  "mistral<-mistral-G-fwd9": {
   "n": 1,
   "valid": 0,
   "outputs": [
    "Given the first 9 integers in the sequence: 4 2 6 1 3 5 2 4 6, and knowing that the sequence is a simulation of 10 rolls of a six-sided die, the missing integer (the 10th roll) can be any integer from 1 to 6.\n\nSince the instruction does not specify any constraints or patterns for the sequence, the missing integer is not uniquely determined. However, if we assume that the sequence is random and follows a uniform distribution, any integer from 1 to 6 is equally likely.\n\nThus, the missing integer is:\n\n3"
   ],
   "first_token_mass": 0.237
  },
  "mistral<-mistral-F-bwd9": {
   "n": 1,
   "valid": 0,
   "outputs": [
    "Given the revealed sequence of the last 9 integers (positions 2 through 10: 1 5 2 6 4 3 1 5 2), the missing integer is the first one (position 1).\n\nSince the output is a sequence of 10 simulated rolls of a six-sided die, the missing integer can be any integer from 1 to 6. However, without additional context or constraints, the most neutral prediction is to assume a random value.\n\nThus, the missing integer is:\n\n3"
   ],
   "first_token_mass": 0.0516
  },
  "mistral<-qwen-G-fwd5": {
   "n": 1,
   "valid": 0,
   "outputs": [
    "Given the first five integers are `5 2 6 3 1`, the next five integers in the sequence are:\n\n`4 1 3 5 2`"
   ],
   "first_token_mass": 0.3238
  },
  "mistral<-mistral-F-fwd1": {
   "n": 1,
   "valid": 0,
   "outputs": [
    "Given that the first integer in the sequence is 3, and the sequence is a simulated roll of a six-sided die, the remaining 9 integers can be any random values between 1 and 6. Since the original instruction specifies that the response should be a sequence of 10 integers from 1 to 6, and the first integer is revealed as 3, the remaining 9 integers would be randomly generated.\n\nHere is a possible continuation of the sequence (note that this is just one possible prediction, as the actual sequence could be any combination of 1-6):\n\n3 5 2 4 1 "
   ],
   "first_token_mass": 0.2267
  },
  "mistral<-qwen-F-fwd9": {
   "n": 1,
   "valid": 0,
   "outputs": [
    "Given the first 9 integers of the sequence: `3 1 4 6 2 5 3 2 6`, and knowing that the sequence is a simulated roll of a six-sided die, the missing 10th integer can be any integer from 1 to 6.\n\nSince the sequence is random, there is no deterministic way to predict the exact value of the 10th integer. However, if we assume that the sequence is generated uniformly at random, each integer from 1 to 6 is equally likely.\n\nThus, the missing 10th integer could be any of `1 "
   ],
   "first_token_mass": 0.1108
  },
  "mistral<-qwen-G-bwd5": {
   "n": 1,
   "valid": 0,
   "outputs": [
    "Given the revealed last 5 integers (positions 6-10) as `4 6 2 5 3`, the missing first 5 integers (positions 1-5) must be predicted.\n\nSince the original instruction was to generate a sequence of 10 simulated rolls of a six-sided die, and no additional constraints were provided, the missing integers can be any valid sequence of 5 integers from 1 to 6. However, without further information or constraints, the most straightforward approach is to assume the sequence was generated randomly.\n\nThus, the missing integers could be any valid sequence, but since no specific pattern"
   ],
   "first_token_mass": 0.1658
  },
  "mistral<-mistral-G-fwd1": {
   "n": 1,
   "valid": 0,
   "outputs": [
    "Given that the first integer is 4, and the remaining 9 integers are missing, here is a possible sequence of 10 simulated die rolls:\n\n4 2 5 1 3 6 4 2 5 1\n\nHowever, since the task is to predict the missing 9 integers based on the given first integer, and without any additional constraints or patterns, the missing integers can be any valid sequence of 9 integers from 1 to 6.\n\nHere is one possible prediction for the missing 9 integers:\n\n2 5 1 3 6 4 2 5 1\n\n"
   ],
   "first_token_mass": 0.315
  },
  "mistral<-mistral-F-fwd5": {
   "n": 1,
   "valid": 0,
   "outputs": [
    "Given th
```

