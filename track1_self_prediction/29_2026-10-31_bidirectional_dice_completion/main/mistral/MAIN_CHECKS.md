# Main checks, mistral (SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1)

**Overall: PASS**

| Gate | Status | Detail |
|---|---|---|
| references_equal_exp28 | PASS | `{"qwen-G": {"exp28_outputs": ["5 2 6 3 1 4 6 2 5 3"], "n": 20, "frozen": "5 2 6 3 1 4 6 2 5 3"}, "qwen-F": {"exp28_outputs": ["3 1 4 6 2 5 3 2 6 4"], "n": 20, "frozen": "3 1 4 6 2 5 3 2 6 4"}, "mistral-G": {"exp28_outputs": ["4 2 6 1 3 5 2 4 6 1"], "n": 20, "frozen": "4 2 6 1 3 5 2 4 6 1"}, "mistral-F": {"exp28_outputs": ["3 1 5 2 6 4 3 1 5 2"], "n": 20, "frozen": "3 1 5 2 6 4 3 1 5 2"}}` |
| serving | PASS | `{"model_id": "mistralai/Mistral-Small-3.2-24B-Instruct-2506", "model_commit": "95a6d26c4bfb886c58daf9d3f7332c857cb27b43", "gpu": "NVIDIA A100-SXM4-80GB", "driver": "595.91.07", "cuda": "12.8", "torch": "2.11.0+cu128", "transformers": "5.22.0", "accelerate": "1.15.0", "huggingface_hub": "2.4.0", "mistral_common": "1.13.0", "chat_template_sha256": null, "tekken_sha256": "6e2501687ccd0e1f30f36319eaf2b46958b897811e246cd8eb5d385b9e3de7d1", "code_commit": "201ad2b"}` |
| template | PASS | `{"rendered_G": "<s>[INST]Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.[/INST]"}` |
| face_tokens | PASS | `{"face_ids": {"1": 1049, "2": 1050, "3": 1051, "4": 1052, "5": 1053, "6": 1054}, "separator_id": 1032}` |
| complete | PASS | `{"n": 232, "expected": 232, "cell_calls": 228, "distinct_cells": 76}` |
| face_logprobs_finite | PASS | `{"n_values": 24390, "n_tf_rows": 752, "max_abs_p6_sum_error": 2.220446049250313e-16}` |
| face_mass_archival_G | PASS | `{"n": 20, "min_six_face_mass": 0.9704016121378366}` |
| archival_regression | PASS | `{"archive": "Experiment 28 main", "conditions": {"G": {"outputs": ["4 2 6 1 3 5 2 4 6 1"], "archived": "4 2 6 1 3 5 2 4 6 1", "n": 2}, "F": {"outputs": ["3 1 5 2 6 4 3 1 5 2"], "archived": "3 1 5 2 6 4 3 1 5 2", "n": 2}}, "n_vectors": 40, "max_abs_dp": 0.0, "tol": 0.01}` |
| deterministic_replicates | PASS | `{}` |
| scorer_matches_generation | PASS | `{"n_rescored": 78, "max_abs_logprob_diff": 0.0, "tol": 0.0001, "retokenisation_mismatch_valid": [], "retokenisation_mismatch_invalid": []}` |
| target_mapping | PASS | `{"cells": 76, "incremental_rows": 376, "expected_rows": 376, "problems": []}` |
| numerical_floor | PASS | `{"max_abs_dp_incremental_vs_full_pass": 0.04280531879499644, "n": 1487, "stop_above": 0.25}` |
| teacher_forced_mass_review | PASS | `{"median_raw_mass": 0.9999104863394401, "min_raw_mass": 0.02367050354058216, "cells_all_below": [], "thresholds": [0.1, 0.01]}` |
| no_source_names_in_prompts | PASS | `{"leaks": []}` |
| raw_files_untampered | PASS | `{"raw_attempts_sha256": "0ae7cd77a72a4c6a99ddb6862f437b928fdfb5006e7792dac3dc1f8d7915c773"}` |

## Example outputs (0/76 cells strictly valid; format is reported, not gated)


**Valid:**

- none

**Invalid:**

- `mistral<-qwen-G-bwd7`: `"Given the revealed sequence (positions 4 through 10): 3 1 4 6 2 5 3, the missing integers are the first three positions (1 through 3) of the original 10-roll sequence.\n\nSince the original instruction specifies that the sequence is a simulated roll of a six-sided die, the missing integers must be thr"`
- `mistral<-qwen-F-bwd5`: `"Given that the last 5 integers are 5 3 2 6 4, and the response must consist of 10 integers from 1 to 6, the missing first 5 integers can be any sequence of integers from 1 to 6. Since the original instruction does not specify any constraints on the sequence (e.g., randomness, uniqueness, or pattern)"`
- `mistral<-qwen-G-fwd9`: `"Given the first 9 integers in the sequence: `5 2 6 3 1 4 6 2 5`, and knowing that the sequence is a simulation of 10 rolls of a six-sided die, the missing 10th integer can be any integer from 1 to 6.\n\nSince the instruction does not specify any constraints or patterns for the sequence, the missing in"`
- `mistral<-qwen-G-fwd2`: `"Given the first two integers are 5 and 2, here is a possible continuation of the sequence (note that the actual sequence is random, but this is a plausible continuation):\n\n3 6 1 4 5 2 3 6"`

## Information (not gated)

```json
{
 "format_reported_not_gated": {
  "mistral<-qwen-G-bwd7": {
   "n": 3,
   "valid": 0,
   "outputs": [
    "Given the revealed sequence (positions 4 through 10): 3 1 4 6 2 5 3, the missing integers are the first three positions (1 through 3) of the original 10-roll sequence.\n\nSince the original instruction specifies that the sequence is a simulated roll of a six-sided die, the missing integers must be three random integers between 1 and 6. However, without additional context or constraints, we cannot determine the exact values of the first three rolls.\n\nThus, the missing integers are not uniquely determined by the given information. However, if we assume the sequence was generated"
   ],
   "first_token_mass": 0.0702
  },
  "mistral<-qwen-F-bwd5": {
   "n": 3,
   "valid": 0,
   "outputs": [
    "Given that the last 5 integers are 5 3 2 6 4, and the response must consist of 10 integers from 1 to 6, the missing first 5 integers can be any sequence of integers from 1 to 6. Since the original instruction does not specify any constraints on the sequence (e.g., randomness, uniqueness, or pattern), the missing integers could be any valid sequence.\n\nHowever, since the task is to predict the output of another instance of the model, and the model is designed to simulate random rolls of a six-sided die, the most straightforward prediction is that the first"
   ],
   "first_token_mass": 0.1234
  },
  "mistral<-qwen-G-fwd9": {
   "n": 3,
   "valid": 0,
   "outputs": [
    "Given the first 9 integers in the sequence: `5 2 6 3 1 4 6 2 5`, and knowing that the sequence is a simulation of 10 rolls of a six-sided die, the missing 10th integer can be any integer from 1 to 6.\n\nSince the instruction does not specify any constraints or patterns for the sequence, the missing integer is not uniquely determined. However, if we assume that the sequence is random and no additional information is provided, the missing integer could be any of the numbers from 1 to 6.\n\nIf we are to predict the missing"
   ],
   "first_token_mass": 0.261
  },
  "mistral<-qwen-G-fwd2": {
   "n": 3,
   "valid": 0,
   "outputs": [
    "Given the first two integers are 5 and 2, here is a possible continuation of the sequence (note that the actual sequence is random, but this is a plausible continuation):\n\n3 6 1 4 5 2 3 6"
   ],
   "first_token_mass": 0.337
  },
  "mistral<-mistral-G-bwd2": {
   "n": 3,
   "valid": 0,
   "outputs": [
    "Given that the last two integers in the sequence are 6 and 1, and the sequence consists of 10 integers from 1 to 6, the missing integers (positions 1 through 8) could be any valid sequence of 8 integers from 1 to 6. However, since the original instruction does not provide any additional constraints or patterns, the missing integers are not uniquely determined.\n\nThus, one possible sequence for the first 8 integers is:\n\n1 2 3 4 5 6 1 2\n\nBut since the original response was not provided, and only the last two integers are known"
   ],
   "first_token_mass": 0.2468
  },
  "mistral<-mistral-F-bwd7": {
   "n": 3,
   "valid": 0,
   "outputs": [
    "Given the revealed sequence (positions 4 through 10: 2 6 4 3 1 5 2), the missing integers are the first three positions (1 through 3) of the original 10-integer sequence.\n\nSince the model is simulating a fair six-sided die, each integer from 1 to 6 is equally likely, and there is no inherent pattern or constraint provided. Therefore, the missing integers could be any combination of 1 through 6.\n\nHowever, since the task is to predict the output of another instance of the model, and no additional context or constraints are given, the"
   ],
   "first_token_mass": 0.0366
  },
  "mistral<-qwen-G-bwd8": {
   "n": 3,
   "valid": 0,
   "outputs": [
    "Given the revealed sequence (positions 3 through 10): 6 3 1 4 6 2 5 3, the missing integers are at positions 1 and 2.\n\nSince the sequence is a simulated roll of a six-sided die, the missing integers must be two integers from 1 to 6. The original response was 10 integers, so the first two integers are the missing ones.\n\nThe missing integers are:\n2 4"
   ],
   "first_token_mass": 0.0485
  },
  "mistral<-mistral-G-fwd5": {
   "n": 3,
   "valid": 0,
   "outputs": [
    "Given the first five integers are `4 2 6 1 3`, the next five integers in the sequence are:\n\n`5 1 4 2 6`"
   ],
   "first_token_mass": 0.3255
  },
  "mistral<-qwen-F-bwd3": {
   "n": 3,
   "valid": 0,
   "outputs": [
    "Given that the last three integers of the sequence are 2, 6, and 4, and the sequence consists of 10 integers in total, the missing integers (positions 1 through 7) must be randomly generated as if rolled by a fair six-sided die. Since the model's output is deterministic based on its training, we cannot predict the exact sequence, but we can simulate a plausible continuation.\n\nHere is a possible sequence for the first 7 integers:\n\n3 1 5 3 6 2 1\n\nThus, the full sequence would be:\n\n3 1 5 3 6 "
   ],
   "first_token_mass": 0.0977
  },
  "mistral<-qwen-F-fwd8": {
   "n": 3,
   "valid": 0,
   "outputs": [
    "Given the first 8 integers of the sequence, the next two integers (positions 9 and 10) are predicted to be:\n\n4 1"
   ],
   "first_token_mass": 0.1291
  },
  "mistral<-mistral-F-fwd4": {
   "n": 3,
   "valid": 0,
   "outputs": [
    "Given the first four integers (3 1 5 2), the remaining six integers in the sequence can be any valid die rolls (1 through 6). Since the original instruction specifies that the output should be a sequence of 10 simulated rolls of a six-sided die, and no additional constraints are provided, the missing integers can be any random sequence of six numbers between 1 and 6.\n\nHowever, since the task is to predict the output of another instance of the model, and no further information is given about the sequence's properties (e.g., randomness, patterns, etc.), the most straightforward approach is to assume"
   ],
   "first_token_mass": 0.1138
  },
  "mistral<-qwen-F-fwd9": {
   "n": 3,
   "valid": 0,
   "outputs": [
    "Given the first 9 integers of the sequence: `3 1 4 6 2 5 3 2 6`, and knowing that the sequence is a simulated roll of a six-sided die, the missing 10th integer can be any integer from 1 to 6.\n\nSince the sequence is random, there is no deterministic way to predict the exact value of the 10th integer. However, if we assume that the sequence is generated uniformly at random, each integer from 1 to 6 is equally likely.\n\nThus, the missing 10th integer could be any of `1 "
   ],
   "first_token_mass": 0.1108
  },
  "mistral<-mistral-F-fwd7": {
   "n": 3,
   "valid": 0,
   "outputs": [
    "Given the first 7 integers of the sequence are `3 1 5 2 6 4 3`, and the task is to predict the next 3 integers (positions 8, 9, and 10) in a sequence of 10 simulated six-sided die rolls, we can proceed as follows:\n\nSince the sequence is simulated and there is no inherent pattern or constraint provided beyond the die's properties (each roll is independent with equal probability for 1 through 6), the most reasonable prediction is that the remaining 3 integers are randomly selected from 1 to 6.\n\nThus, the missing integers"
   ],
   "first_token_mass": 0.1404
  },
  "mistral<-qwen-F-bwd8": {
   "n": 3,
   "valid": 0,
   "outputs": [
    "Given that the last 8 integers are revealed as `4 6 2 5 3 2 6 4`, and the original response consisted of 10 integers, the missing integers are the first two in the sequence.\n\nSince the model is simulating a fair six-sided die, the first two integers could be any combination of numbers from 1 to 6. However, without additional context or constraints, the most straightforward prediction is that the first two integers are also random and independent of the revealed sequence.\n\nThus, the missing integers are likely to be any two numbers from 1 to 6. For the sake of"
   ],
   "first_token_mass": 0.0349
  },
  "mistral<-mistral-G-fwd3": {
   "n": 3,
   "valid": 0,
   "outputs": [
    "Given the first three integers ar
```

