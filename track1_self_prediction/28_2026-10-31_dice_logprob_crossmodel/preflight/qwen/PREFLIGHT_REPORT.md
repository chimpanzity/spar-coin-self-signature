# Preflight, qwen (SPAR_DICE_LOGPROB_CROSSMODEL_v2.0)

**Overall: PASS**

| Gate | Status | Detail |
|---|---|---|
| serving | PASS | `{"model_id": "Qwen/Qwen3-32B", "model_commit": "9216db5781bf21249d130ec9da846c4624c16137", "gpu": "NVIDIA A100-SXM4-80GB", "driver": "595.91.07", "cuda": "12.8", "torch": "2.11.0+cu128", "transformers": "5.22.0", "accelerate": "1.15.0", "huggingface_hub": "2.4.0", "mistral_common": null, "chat_template_sha256": "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8", "tekken_sha256": null, "code_commit": "562421f"}` |
| template | PASS | `{"rendered_G": "<|im_start|>user\nGenerate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"}` |
| face_tokens | PASS | `{"face_ids": {"1": 16, "2": 17, "3": 18, "4": 19, "5": 20, "6": 21}, "separator_id": 220, "vocab_size": 151669, "variant_face_tokens": [], "multi_digit_ascii_tokens": []}` |
| face_logprobs_finite | PASS | `{"n_steps": 225}` |
| face_mass_direct_generation | PASS | `{"n_steps": 70, "min_six_face_mass": 0.999994639362477, "threshold": 0.5}` |
| format_references | PASS | `{"G": {"n": 3, "valid": 3, "outputs": ["5 2 6 3 1 4 6 2 5 3"], "finish": ["stop"]}, "F": {"n": 3, "valid": 3, "outputs": ["3 1 4 6 2 5 3 2 6 4"], "finish": ["stop"]}}` |
| scorer_matches_generation | PASS | `{"n_rescored": 19, "max_abs_logprob_diff": 0.0, "tol": 0.0001, "retokenisation_mismatch_valid": [], "retokenisation_mismatch_invalid": []}` |
| determinism | PASS | `{"G": {"n": 3, "outputs": ["5 2 6 3 1 4 6 2 5 3"], "max_logprob_spread": 0.0}, "F": {"n": 3, "outputs": ["3 1 4 6 2 5 3 2 6 4"], "max_logprob_spread": 0.0}}` |
| numerical_floor | PASS | `{"max_abs_dp_incremental_vs_full_pass": 0.09107393562453042, "n": 155, "stop_above": 0.25}` |
| matched_prefix_complete | PASS | `{"mp_rows": 80, "window_rows": 60}` |
| archival_regression | PASS | `{"archive": "Experiment 21 main", "conditions": {"W1-5": {"output": "4 2 6 3 5", "archived": "4 2 6 3 5", "identical": true, "max_abs_dp": 0.0}, "S8": {"output": "4", "archived": "4", "identical": true, "max_abs_dp": 0.0}, "S10": {"output": "4", "archived": "4", "identical": true, "max_abs_dp": 0.0}, "S9": {"output": "5", "archived": "5", "identical": true, "max_abs_dp": 0.0}, "F": {"output": "3 1 4 6 2 5 3 2 6 4", "archived": "3 1 4 6 2 5 3 2 6 4", "identical": true, "max_abs_dp": 0.0}, "S6": {"output": "4", "archived": "4", "identical": true, "max_abs_dp": 0.0}, "S1": {"output": "4", "archiv` |

Information (not gated):

```json
{
 "format_all_conditions_reported": {
  "all_valid": true,
  "invalid": {},
  "amendment": "v1.1"
 },
 "sec_per_job": {
  "G": 3.677748203277588,
  "W1-5": 1.811293125152588,
  "S6": 0.45409154891967773,
  "W6-10": 1.810312271118164,
  "S9": 0.45647096633911133,
  "W3-7": 1.8152234554290771,
  "F": 3.474021037419637,
  "S4": 0.447857141494751,
  "S2": 0.46183228492736816,
  "S7": 0.45419931411743164,
  "S5": 0.45598387718200684,
  "S3": 0.4702436923980713,
  "S1": 0.4537653923034668,
  "S10": 0.46038269996643066,
  "S8": 0.451585054397583
 },
 "projected_main_generation_minutes": 5.71833668814765,
 "matched_seconds": 12.9,
 "vocab_scan_seconds": 0.5,
 "floor": 0.09107393562453042,
 "prediction_prompt_min_mass_reported_not_gated": {
  "G": 0.999994639362477,
  "G_first_token": 0.999994639362477,
  "W1-5": 0.9980568067456684,
  "W1-5_first_token": 0.9980568067456684,
  "S6": 0.9999952331390973,
  "S6_first_token": 0.9999952331390973,
  "W6-10": 0.9981421603742561,
  "W6-10_first_token": 0.9981421603742561,
  "S9": 0.99997807783701,
  "S9_first_token": 0.99997807783701,
  "W3-7": 0.9962253497444993,
  "W3-7_first_token": 0.9962253497444993,
  "F": 0.9978566380683462,
  "F_first_token": 0.9978566380683462,
  "S4": 0.9999786277829287,
  "S4_first_token": 0.9999786277829287,
  "S2": 0.9999871351392672,
  "S2_first_token": 0.9999871351392672,
  "S7": 0.9997713842153348,
  "S7_first_token": 0.9997713842153348,
  "S5": 0.9999833860502079,
  "S5_first_token": 0.9999833860502079,
  "S3": 0.999976812097728,
  "S3_first_token": 0.999976812097728,
  "S1": 0.9999930248022554,
  "S1_first_token": 0.9999930248022554,
  "S10": 0.9999902340552893,
  "S10_first_token": 0.9999902340552893,
  "S8": 0.999990779118457,
  "S8_first_token": 0.999990779118457,
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
 "max_memory_allocated_gb": 66.82
}
```

