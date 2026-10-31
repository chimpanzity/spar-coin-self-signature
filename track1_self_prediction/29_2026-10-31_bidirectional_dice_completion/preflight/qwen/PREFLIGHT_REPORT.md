# Preflight, qwen (SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1)

**Overall: PASS**

| Gate | Status | Detail |
|---|---|---|
| references_equal_exp28 | PASS | `{"qwen-G": {"exp28_outputs": ["5 2 6 3 1 4 6 2 5 3"], "n": 20, "frozen": "5 2 6 3 1 4 6 2 5 3"}, "qwen-F": {"exp28_outputs": ["3 1 4 6 2 5 3 2 6 4"], "n": 20, "frozen": "3 1 4 6 2 5 3 2 6 4"}, "mistral-G": {"exp28_outputs": ["4 2 6 1 3 5 2 4 6 1"], "n": 20, "frozen": "4 2 6 1 3 5 2 4 6 1"}, "mistral-F": {"exp28_outputs": ["3 1 5 2 6 4 3 1 5 2"], "n": 20, "frozen": "3 1 5 2 6 4 3 1 5 2"}}` |
| serving | PASS | `{"model_id": "Qwen/Qwen3-32B", "model_commit": "9216db5781bf21249d130ec9da846c4624c16137", "gpu": "NVIDIA A100-SXM4-80GB", "driver": "595.91.07", "cuda": "12.8", "torch": "2.11.0+cu128", "transformers": "5.22.0", "accelerate": "1.15.0", "huggingface_hub": "2.4.0", "mistral_common": null, "chat_template_sha256": "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8", "tekken_sha256": null, "code_commit": "201ad2b"}` |
| template | PASS | `{"rendered_G": "<|im_start|>user\nGenerate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"}` |
| face_tokens | PASS | `{"face_ids": {"1": 16, "2": 17, "3": 18, "4": 19, "5": 20, "6": 21}, "separator_id": 220, "vocab_size": 151669, "variant_face_tokens": [], "multi_digit_ascii_tokens": []}` |
| face_logprobs_finite | PASS | `{"n_values": 2688, "n_tf_rows": 272, "max_abs_p6_sum_error": 2.220446049250313e-16}` |
| face_mass_archival_G | PASS | `{"n": 20, "min_six_face_mass": 0.999994639362477}` |
| archival_regression | PASS | `{"archive": "Experiment 28 main", "conditions": {"G": {"outputs": ["5 2 6 3 1 4 6 2 5 3"], "archived": "5 2 6 3 1 4 6 2 5 3", "n": 2}, "F": {"outputs": ["3 1 4 6 2 5 3 2 6 4"], "archived": "3 1 4 6 2 5 3 2 6 4", "n": 2}}, "n_vectors": 40, "max_abs_dp": 0.0, "tol": 0.01}` |
| archival_determinism | PASS | `{"G": {"n": 2, "outputs": ["5 2 6 3 1 4 6 2 5 3"], "max_logprob_spread": 0.0}, "F": {"n": 2, "outputs": ["3 1 4 6 2 5 3 2 6 4"], "max_logprob_spread": 0.0}}` |
| preflight_calls_complete | PASS | `{"n": 28, "expected": 28}` |
| scorer_matches_generation | PASS | `{"n_rescored": 30, "max_abs_logprob_diff": 0.0, "tol": 0.0001, "retokenisation_mismatch_valid": [], "retokenisation_mismatch_invalid": []}` |
| target_mapping | PASS | `{"cells": 28, "incremental_rows": 136, "expected_rows": 136, "problems": []}` |
| numerical_floor | PASS | `{"max_abs_dp_incremental_vs_full_pass": 0.09107393562453042, "n": 292, "stop_above": 0.25}` |
| teacher_forced_mass_review | PASS | `{"median_raw_mass": 0.9999999598049496, "min_raw_mass": 0.9879800146707866, "cells_all_below": [], "thresholds": [0.1, 0.01]}` |
| no_source_names_in_prompts | PASS | `{"leaks": []}` |

## Example outputs (28/28 cells strictly valid; format is reported, not gated)


**Valid:**

- `qwen<-qwen-F-fwd1`: `"4 2 6 1 5 3 2 6 1"`
- `qwen<-mistral-G-fwd5`: `"5 2 4 6 1"`
- `qwen<-qwen-F-fwd9`: `"4"`
- `qwen<-mistral-G-bwd5`: `"4 3 2 5 6"`

**Invalid:**

- none

## Information (not gated)

```json
{
 "format_reported_not_gated": {
  "qwen<-qwen-F-fwd1": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "4 2 6 1 5 3 2 6 1"
   ],
   "first_token_mass": 1.0
  },
  "qwen<-mistral-G-fwd5": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "5 2 4 6 1"
   ],
   "first_token_mass": 0.9936
  },
  "qwen<-qwen-F-fwd9": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "4"
   ],
   "first_token_mass": 0.9999
  },
  "qwen<-mistral-G-bwd5": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "4 3 2 5 6"
   ],
   "first_token_mass": 0.9902
  },
  "qwen<-mistral-F-fwd5": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "4 2 5 1 3"
   ],
   "first_token_mass": 0.9996
  },
  "qwen<-qwen-F-bwd9": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "3"
   ],
   "first_token_mass": 0.9998
  },
  "qwen<-mistral-G-bwd1": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "4 2 6 3 5 1 2 6 3"
   ],
   "first_token_mass": 0.9998
  },
  "qwen<-mistral-G-fwd9": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "5"
   ],
   "first_token_mass": 0.988
  },
  "qwen<-qwen-F-mid": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "5 3 1 4"
   ],
   "first_token_mass": 0.9999
  },
  "qwen<-mistral-G-fwd1": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "5 2 6 3 1 4 2 6 3"
   ],
   "first_token_mass": 0.9999
  },
  "qwen<-qwen-F-bwd5": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "4 1 2 5 3"
   ],
   "first_token_mass": 1.0
  },
  "qwen<-qwen-G-bwd5": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "5 1 3 4 2"
   ],
   "first_token_mass": 0.9934
  },
  "qwen<-mistral-G-bwd9": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "4"
   ],
   "first_token_mass": 0.9984
  },
  "qwen<-qwen-F-fwd5": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "5 3 1 4 2"
   ],
   "first_token_mass": 0.9998
  },
  "qwen<-mistral-F-mid": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "4 3 2 5"
   ],
   "first_token_mass": 0.9998
  },
  "qwen<-mistral-F-fwd1": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "4 2 6 1 5 3 2 6 1"
   ],
   "first_token_mass": 1.0
  },
  "qwen<-qwen-F-bwd1": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "5 2 3 1 6 4 2 6 3"
   ],
   "first_token_mass": 1.0
  },
  "qwen<-qwen-G-mid": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "4 5 5 3"
   ],
   "first_token_mass": 0.9986
  },
  "qwen<-mistral-F-bwd9": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "4"
   ],
   "first_token_mass": 0.9997
  },
  "qwen<-mistral-F-fwd9": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "2"
   ],
   "first_token_mass": 0.9993
  },
  "qwen<-mistral-G-mid": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "4 2 1 6"
   ],
   "first_token_mass": 0.9957
  },
  "qwen<-qwen-G-fwd5": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "4 2 5 6 3"
   ],
   "first_token_mass": 0.9918
  },
  "qwen<-qwen-G-fwd9": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "6"
   ],
   "first_token_mass": 0.9909
  },
  "qwen<-mistral-F-bwd5": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "5 2 6 4 3"
   ],
   "first_token_mass": 1.0
  },
  "qwen<-qwen-G-fwd1": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "4 2 6 3 1 5 2 6 3"
   ],
   "first_token_mass": 1.0
  },
  "qwen<-qwen-G-bwd1": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "5 2 6 1 3 4 2 6 1"
   ],
   "first_token_mass": 0.9997
  },
  "qwen<-mistral-F-bwd1": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "5 3 6 1 4 2 6 3 1"
   ],
   "first_token_mass": 1.0
  },
  "qwen<-qwen-G-bwd9": {
   "n": 1,
   "valid": 1,
   "outputs": [
    "4"
   ],
   "first_token_mass": 0.9982
  }
 },
 "mean_sec_per_cell_call": 0.8532857142857143,
 "projected_main_generation_minutes": 3.242485714285714,
 "generation_seconds": 60.6,
 "teacher_forced_seconds": 26.6,
 "max_memory_allocated_gb": 66.82
}
```

