# Main checks, qwen (SPAR_DICE_LOGPROB_CROSSMODEL_v2.0)

**Overall: PASS**

| Gate | Status | Detail |
|---|---|---|
| serving | PASS | `{"model_id": "Qwen/Qwen3-32B", "model_commit": "9216db5781bf21249d130ec9da846c4624c16137", "gpu": "NVIDIA A100-SXM4-80GB", "driver": "595.91.07", "cuda": "12.8", "torch": "2.11.0+cu128", "transformers": "5.22.0", "accelerate": "1.15.0", "huggingface_hub": "2.4.0", "mistral_common": null, "chat_template_sha256": "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8", "tekken_sha256": null, "code_commit": "562421f"}` |
| template | PASS | `{"rendered_G": "<|im_start|>user\nGenerate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"}` |
| face_tokens | PASS | `{"face_ids": {"1": 16, "2": 17, "3": 18, "4": 19, "5": 20, "6": 21}, "separator_id": 220}` |
| complete | PASS | `{"n": 300, "expected": 300, "duplicates": 0}` |
| face_logprobs_finite | PASS | `{"n_steps": 1040}` |
| face_mass_direct_generation | PASS | `{"n_steps": 240, "min_six_face_mass": 0.999994639362477, "threshold": 0.5}` |
| format_references | PASS | `{"G": {"n": 20, "valid": 20, "outputs": ["5 2 6 3 1 4 6 2 5 3"], "finish": ["stop"]}, "F": {"n": 20, "valid": 20, "outputs": ["3 1 4 6 2 5 3 2 6 4"], "finish": ["stop"]}}` |
| scorer_matches_generation | PASS | `{"n_rescored": 15, "max_abs_logprob_diff": 0.0, "tol": 0.0001, "retokenisation_mismatch_valid": [], "retokenisation_mismatch_invalid": []}` |
| references_reproducible | PASS | `{"G": {"n": 20, "outputs": ["5 2 6 3 1 4 6 2 5 3"], "max_logprob_spread": 0.0}, "F": {"n": 20, "outputs": ["3 1 4 6 2 5 3 2 6 4"], "max_logprob_spread": 0.0}}` |
| numerical_floor | PASS | `{"max_abs_dp_incremental_vs_full_pass": 0.09107393562453042, "n": 115}` |
| matched_prefix_complete | PASS | `{"mp_rows": 80, "window_rows": 60}` |
| raw_files_untampered | PASS | `{"raw_attempts_sha256": "a94af1387715de866957dcb7713d2b8e5296efd24a03dd808ec44b954a396482"}` |

Information (not gated):

```json
{
 "formats": {
  "S5": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "4"
   ],
   "finish": [
    "stop"
   ]
  },
  "W1-5": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "4 2 6 3 5"
   ],
   "finish": [
    "stop"
   ]
  },
  "G": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "5 2 6 3 1 4 6 2 5 3"
   ],
   "finish": [
    "stop"
   ]
  },
  "S6": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "4"
   ],
   "finish": [
    "stop"
   ]
  },
  "W3-7": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "4 2 6 3 5"
   ],
   "finish": [
    "stop"
   ]
  },
  "S10": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "4"
   ],
   "finish": [
    "stop"
   ]
  },
  "S1": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "4"
   ],
   "finish": [
    "stop"
   ]
  },
  "S3": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "5"
   ],
   "finish": [
    "stop"
   ]
  },
  "S2": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "4"
   ],
   "finish": [
    "stop"
   ]
  },
  "S7": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "4"
   ],
   "finish": [
    "stop"
   ]
  },
  "S9": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "5"
   ],
   "finish": [
    "stop"
   ]
  },
  "S8": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "4"
   ],
   "finish": [
    "stop"
   ]
  },
  "W6-10": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "4 2 5 3 6"
   ],
   "finish": [
    "stop"
   ]
  },
  "S4": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "5"
   ],
   "finish": [
    "stop"
   ]
  },
  "F": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "3 1 4 6 2 5 3 2 6 4"
   ],
   "finish": [
    "stop"
   ]
  }
 },
 "determinism_all_conditions": {
  "G": {
   "n": 20,
   "outputs": [
    "5 2 6 3 1 4 6 2 5 3"
   ],
   "max_logprob_spread": 0.0
  },
  "F": {
   "n": 20,
   "outputs": [
    "3 1 4 6 2 5 3 2 6 4"
   ],
   "max_logprob_spread": 0.0
  },
  "S1": {
   "n": 20,
   "outputs": [
    "4"
   ],
   "max_logprob_spread": 0.0
  },
  "S2": {
   "n": 20,
   "outputs": [
    "4"
   ],
   "max_logprob_spread": 0.0
  },
  "S3": {
   "n": 20,
   "outputs": [
    "5"
   ],
   "max_logprob_spread": 0.0
  },
  "S4": {
   "n": 20,
   "outputs": [
    "5"
   ],
   "max_logprob_spread": 0.0
  },
  "S5": {
   "n": 20,
   "outputs": [
    "4"
   ],
   "max_logprob_spread": 0.0
  },
  "S6": {
   "n": 20,
   "outputs": [
    "4"
   ],
   "max_logprob_spread": 0.0
  },
  "S7": {
   "n": 20,
   "outputs": [
    "4"
   ],
   "max_logprob_spread": 0.0
  },
  "S8": {
   "n": 20,
   "outputs": [
    "4"
   ],
   "max_logprob_spread": 0.0
  },
  "S9": {
   "n": 20,
   "outputs": [
    "5"
   ],
   "max_logprob_spread": 0.0
  },
  "S10": {
   "n": 20,
   "outputs": [
    "4"
   ],
   "max_logprob_spread": 0.0
  },
  "W1-5": {
   "n": 20,
   "outputs": [
    "4 2 6 3 5"
   ],
   "max_logprob_spread": 0.0
  },
  "W3-7": {
   "n": 20,
   "outputs": [
    "4 2 6 3 5"
   ],
   "max_logprob_spread": 0.0
  },
  "W6-10": {
   "n": 20,
   "outputs": [
    "4 2 5 3 6"
   ],
   "max_logprob_spread": 0.0
  }
 },
 "same_output_as_preflight": {
  "G": true,
  "F": true,
  "S1": true,
  "S2": true,
  "S3": true,
  "S4": true,
  "S5": true,
  "S6": true,
  "S7": true,
  "S8": true,
  "S9": true,
  "S10": true,
  "W1-5": true,
  "W3-7": true,
  "W6-10": true
 },
 "floor": 0.09107393562453042,
 "prediction_prompt_min_mass_reported_not_gated": {
  "S5": 0.9999833860502079,
  "S5_first_token": 0.9999833860502079,
  "W1-5": 0.9980568067456684,
  "W1-5_first_token": 0.9980568067456684,
  "G": 0.999994639362477,
  "G_first_token": 0.999994639362477,
  "S6": 0.9999952331390973,
  "S6_first_token": 0.9999952331390973,
  "W3-7": 0.9962253497444993,
  "W3-7_first_token": 0.9962253497444993,
  "S10": 0.9999902340552893,
  "S10_first_token": 0.9999902340552893,
  "S1": 0.9999930248022554,
  "S1_first_token": 0.9999930248022554,
  "S3": 0.999976812097728,
  "S3_first_token": 0.999976812097728,
  "S2": 0.9999871351392672,
  "S2_first_token": 0.9999871351392672,
  "S7": 0.9997713842153348,
  "S7_first_token": 0.9997713842153348,
  "S9": 0.99997807783701,
  "S9_first_token": 0.99997807783701,
  "S8": 0.999990779118457,
  "S8_first_token": 0.999990779118457,
  "W6-10": 0.9981421603742561,
  "W6-10_first_token": 0.9981421603742561,
  "S4": 0.9999786277829287,
  "S4_first_token": 0.9999786277829287,
  "F": 0.9978566380683462,
  "F_first_token": 0.9978566380683462,
  "mp_G|G": 0.999994639362477,
  "mp_G|F": 0.999994639362477,
  "mp_F|G": 0.9978566380683462,
  "mp_F|F": 0.9978566380683462,
  "window_W1-5|G": 0.9980568067456684,
  "window_W1-5|F": 0.9980568067456684,
  "window_W3-7|G": 0.9962253497444993,
  "window_W3-7|F": 0.9962253497444993,
  "window_W6-10|G": 0.9981421603742561,
  "window_W6-10|F": 0.9981421603742561
 },
 "generation_seconds": 166.4,
 "gpu": "NVIDIA A100-SXM4-80GB"
}
```

