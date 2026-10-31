# Preflight, mistral (SPAR_DICE_LOGPROB_CROSSMODEL_v2.0)

**Overall: PASS**

| Gate | Status | Detail |
|---|---|---|
| serving | PASS | `{"model_id": "mistralai/Mistral-Small-3.2-24B-Instruct-2506", "model_commit": "95a6d26c4bfb886c58daf9d3f7332c857cb27b43", "gpu": "NVIDIA A100-SXM4-80GB", "driver": "595.91.07", "cuda": "12.8", "torch": "2.11.0+cu128", "transformers": "5.22.0", "accelerate": "1.15.0", "huggingface_hub": "2.4.0", "mistral_common": "1.13.0", "chat_template_sha256": null, "tekken_sha256": "6e2501687ccd0e1f30f36319eaf2b46958b897811e246cd8eb5d385b9e3de7d1", "code_commit": "562421f"}` |
| template | PASS | `{"rendered_G": "<s>[INST]Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.[/INST]"}` |
| face_tokens | PASS | `{"face_ids": {"1": 1049, "2": 1050, "3": 1051, "4": 1052, "5": 1053, "6": 1054}, "separator_id": 1032, "vocab_size": 131072, "variant_face_tokens": [], "multi_digit_ascii_tokens": []}` |
| face_logprobs_finite | PASS | `{"n_steps": 243}` |
| face_mass_direct_generation | PASS | `{"n_steps": 70, "min_six_face_mass": 0.9704016121378366, "threshold": 0.5}` |
| format_references | PASS | `{"G": {"n": 3, "valid": 3, "outputs": ["4 2 6 1 3 5 2 4 6 1"], "finish": ["stop"]}, "F": {"n": 3, "valid": 3, "outputs": ["3 1 5 2 6 4 3 1 5 2"], "finish": ["stop"]}}` |
| scorer_matches_generation | PASS | `{"n_rescored": 19, "max_abs_logprob_diff": 0.0, "tol": 0.0001, "retokenisation_mismatch_valid": [], "retokenisation_mismatch_invalid": []}` |
| determinism | PASS | `{"G": {"n": 3, "outputs": ["4 2 6 1 3 5 2 4 6 1"], "max_logprob_spread": 0.0}, "F": {"n": 3, "outputs": ["3 1 5 2 6 4 3 1 5 2"], "max_logprob_spread": 0.0}}` |
| numerical_floor | PASS | `{"max_abs_dp_incremental_vs_full_pass": 0.055202138461303174, "n": 173, "stop_above": 0.25}` |
| matched_prefix_complete | PASS | `{"mp_rows": 80, "window_rows": 60}` |
| archival_regression | PASS | `{"archive": "Experiment 27 Mistral preflight", "conditions": {"G": {"output": "4 2 6 1 3 5 2 4 6 1", "archived": "4 2 6 1 3 5 2 4 6 1", "identical": true, "max_abs_dp": 0.0}, "F": {"output": "3 1 5 2 6 4 3 1 5 2", "archived": "3 1 5 2 6 4 3 1 5 2", "identical": true, "max_abs_dp": 0.0}}, "n_vectors": 50, "max_abs_dp": 0.0, "tol": 0.01}` |

Information (not gated):

```json
{
 "format_all_conditions_reported": {
  "all_valid": false,
  "invalid": {
   "W1-5": [
    "Here is the predicted output for the first 5 integers of the 10 simulated die rolls:\n\n3 1 6 4 2"
   ],
   "W3-7": [
    "Here is the predicted output for the sequence of 10 simulated die rolls, followed by the requested subset (positions 3 through 7):\n\n```\n2 5 3 1 6 4 2 5 3 1\n3 1 6 4 2\n```"
   ],
   "W6-10": [
    "Here is the predicted output for the last 5 integers (positions 6 through 10) of a simulated 10-roll sequence of a six-sided die:\n\n```\n3 1 5 2 6\n```"
   ]
  },
  "amendment": "v1.1"
 },
 "sec_per_job": {
  "F": 1.9856356779734294,
  "W1-5": 2.8985016345977783,
  "S7": 0.2657661437988281,
  "S10": 0.2660338878631592,
  "G": 1.815060297648112,
  "S9": 0.2658722400665283,
  "S3": 0.2693917751312256,
  "S4": 0.27660655975341797,
  "S8": 0.2662060260772705,
  "W3-7": 5.56817102432251,
  "S2": 0.26630687713623047,
  "S6": 0.2655375003814697,
  "W6-10": 4.33905553817749,
  "S1": 0.2651801109313965,
  "S5": 0.26567649841308594
 },
 "projected_main_generation_minutes": 6.42633393075731,
 "matched_seconds": 6.8,
 "vocab_scan_seconds": 0.4,
 "floor": 0.055202138461303174,
 "prediction_prompt_min_mass_reported_not_gated": {
  "F": 0.6045997890864474,
  "F_first_token": 0.6045997890864474,
  "W1-5": 0.8463311117327827,
  "W1-5_first_token": 0.3980035995857294,
  "S7": 0.8630204794586845,
  "S7_first_token": 0.8630204794586845,
  "S10": 0.9133087275655914,
  "S10_first_token": 0.9133087275655914,
  "G": 0.9704016121378366,
  "G_first_token": 0.9704016121378366,
  "S9": 0.888560869009088,
  "S9_first_token": 0.888560869009088,
  "S3": 0.9128954685700206,
  "S3_first_token": 0.9128954685700206,
  "S4": 0.9027303724799953,
  "S4_first_token": 0.9027303724799953,
  "S8": 0.8925284152186058,
  "S8_first_token": 0.8925284152186058,
  "W3-7": 0.7841381772963788,
  "W3-7_first_token": 0.22719054828367452,
  "S2": 0.8986852544304301,
  "S2_first_token": 0.8986852544304301,
  "S6": 0.8991219502550234,
  "S6_first_token": 0.8991219502550234,
  "W6-10": 0.9999105177096995,
  "W6-10_first_token": 0.2763423343001046,
  "S1": 0.9572233618828871,
  "S1_first_token": 0.9572233618828871,
  "S5": 0.9028791669853787,
  "S5_first_token": 0.9028791669853787,
  "mp_G|G": 0.9704016121378366,
  "mp_G|F": 0.9704016121378366,
  "mp_F|G": 0.6045997890864474,
  "mp_F|F": 0.6045997890864474,
  "window_W1-5|G": 0.3980035995857294,
  "window_W1-5|F": 0.3980035995857294,
  "window_W3-7|G": 0.22719054828367452,
  "window_W3-7|F": 0.22719054828367452,
  "window_W6-10|G": 0.2763423343001046,
  "window_W6-10|F": 0.2763423343001046
 },
 "max_memory_allocated_gb": 49.73
}
```

