# Main checks, mistral (SPAR_DICE_LOGPROB_CROSSMODEL_v2.0)

**Overall: PASS**

| Gate | Status | Detail |
|---|---|---|
| serving | PASS | `{"model_id": "mistralai/Mistral-Small-3.2-24B-Instruct-2506", "model_commit": "95a6d26c4bfb886c58daf9d3f7332c857cb27b43", "gpu": "NVIDIA A100-SXM4-80GB", "driver": "595.91.07", "cuda": "12.8", "torch": "2.11.0+cu128", "transformers": "5.22.0", "accelerate": "1.15.0", "huggingface_hub": "2.4.0", "mistral_common": "1.13.0", "chat_template_sha256": null, "tekken_sha256": "6e2501687ccd0e1f30f36319eaf2b46958b897811e246cd8eb5d385b9e3de7d1", "code_commit": "562421f"}` |
| template | PASS | `{"rendered_G": "<s>[INST]Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.[/INST]"}` |
| face_tokens | PASS | `{"face_ids": {"1": 1049, "2": 1050, "3": 1051, "4": 1052, "5": 1053, "6": 1054}, "separator_id": 1032}` |
| complete | PASS | `{"n": 300, "expected": 300, "duplicates": 0}` |
| face_logprobs_finite | PASS | `{"n_steps": 1400}` |
| face_mass_direct_generation | PASS | `{"n_steps": 240, "min_six_face_mass": 0.9704016121378366, "threshold": 0.5}` |
| format_references | PASS | `{"G": {"n": 20, "valid": 20, "outputs": ["4 2 6 1 3 5 2 4 6 1"], "finish": ["stop"]}, "F": {"n": 20, "valid": 20, "outputs": ["3 1 5 2 6 4 3 1 5 2"], "finish": ["stop"]}}` |
| scorer_matches_generation | PASS | `{"n_rescored": 15, "max_abs_logprob_diff": 0.0, "tol": 0.0001, "retokenisation_mismatch_valid": [], "retokenisation_mismatch_invalid": []}` |
| references_reproducible | PASS | `{"G": {"n": 20, "outputs": ["4 2 6 1 3 5 2 4 6 1"], "max_logprob_spread": 0.0}, "F": {"n": 20, "outputs": ["3 1 5 2 6 4 3 1 5 2"], "max_logprob_spread": 0.0}}` |
| numerical_floor | PASS | `{"max_abs_dp_incremental_vs_full_pass": 0.055202138461303174, "n": 133}` |
| matched_prefix_complete | PASS | `{"mp_rows": 80, "window_rows": 60}` |
| raw_files_untampered | PASS | `{"raw_attempts_sha256": "b4fee4a55fcdbef5025df0e0c9fc4be32e3a0a2dec2147e9f65272c82fe2a000"}` |

Information (not gated):

```json
{
 "formats": {
  "W6-10": {
   "n": 20,
   "valid": 0,
   "outputs": [
    "Here is the predicted output for the last 5 integers (positions 6 through 10) of a simulated 10-roll sequence of a six-sided die:\n\n```\n3 1 5 2 6\n```"
   ],
   "finish": [
    "stop"
   ]
  },
  "S6": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "3"
   ],
   "finish": [
    "stop"
   ]
  },
  "W3-7": {
   "n": 20,
   "valid": 0,
   "outputs": [
    "Here is the predicted output for the sequence of 10 simulated die rolls, followed by the requested subset (positions 3 through 7):\n\n```\n2 5 3 1 6 4 2 5 3 1\n3 1 6 4 2\n```"
   ],
   "finish": [
    "stop"
   ]
  },
  "S7": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "3"
   ],
   "finish": [
    "stop"
   ]
  },
  "S1": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "3"
   ],
   "finish": [
    "stop"
   ]
  },
  "S2": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "3"
   ],
   "finish": [
    "stop"
   ]
  },
  "G": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "4 2 6 1 3 5 2 4 6 1"
   ],
   "finish": [
    "stop"
   ]
  },
  "S4": {
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
    "3"
   ],
   "finish": [
    "stop"
   ]
  },
  "W1-5": {
   "n": 20,
   "valid": 0,
   "outputs": [
    "Here is the predicted output for the first 5 integers of the 10 simulated die rolls:\n\n3 1 6 4 2"
   ],
   "finish": [
    "stop"
   ]
  },
  "S10": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "3"
   ],
   "finish": [
    "stop"
   ]
  },
  "F": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "3 1 5 2 6 4 3 1 5 2"
   ],
   "finish": [
    "stop"
   ]
  },
  "S3": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "3"
   ],
   "finish": [
    "stop"
   ]
  },
  "S8": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "3"
   ],
   "finish": [
    "stop"
   ]
  },
  "S5": {
   "n": 20,
   "valid": 20,
   "outputs": [
    "3"
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
    "4 2 6 1 3 5 2 4 6 1"
   ],
   "max_logprob_spread": 0.0
  },
  "F": {
   "n": 20,
   "outputs": [
    "3 1 5 2 6 4 3 1 5 2"
   ],
   "max_logprob_spread": 0.0
  },
  "S1": {
   "n": 20,
   "outputs": [
    "3"
   ],
   "max_logprob_spread": 0.0
  },
  "S2": {
   "n": 20,
   "outputs": [
    "3"
   ],
   "max_logprob_spread": 0.0
  },
  "S3": {
   "n": 20,
   "outputs": [
    "3"
   ],
   "max_logprob_spread": 0.0
  },
  "S4": {
   "n": 20,
   "outputs": [
    "4"
   ],
   "max_logprob_spread": 0.0
  },
  "S5": {
   "n": 20,
   "outputs": [
    "3"
   ],
   "max_logprob_spread": 0.0
  },
  "S6": {
   "n": 20,
   "outputs": [
    "3"
   ],
   "max_logprob_spread": 0.0
  },
  "S7": {
   "n": 20,
   "outputs": [
    "3"
   ],
   "max_logprob_spread": 0.0
  },
  "S8": {
   "n": 20,
   "outputs": [
    "3"
   ],
   "max_logprob_spread": 0.0
  },
  "S9": {
   "n": 20,
   "outputs": [
    "3"
   ],
   "max_logprob_spread": 0.0
  },
  "S10": {
   "n": 20,
   "outputs": [
    "3"
   ],
   "max_logprob_spread": 0.0
  },
  "W1-5": {
   "n": 20,
   "outputs": [
    "Here is the predicted output for the first 5 integers of the 10 simulated die rolls:\n\n3 1 6 4 2"
   ],
   "max_logprob_spread": 0.0
  },
  "W3-7": {
   "n": 20,
   "outputs": [
    "Here is the predicted output for the sequence of 10 simulated die rolls, followed by the requested subset (positions 3 through 7):\n\n```\n2 5 3 1 6 4 2 5 3 1\n3 1 6 4 2\n```"
   ],
   "max_logprob_spread": 0.0
  },
  "W6-10": {
   "n": 20,
   "outputs": [
    "Here is the predicted output for the last 5 integers (positions 6 through 10) of a simulated 10-roll sequence of a six-sided die:\n\n```\n3 1 5 2 6\n```"
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
 "floor": 0.055202138461303174,
 "prediction_prompt_min_mass_reported_not_gated": {
  "W6-10": 0.9999105177096995,
  "W6-10_first_token": 0.2763423343001046,
  "S6": 0.8991219502550234,
  "S6_first_token": 0.8991219502550234,
  "W3-7": 0.7841381772963788,
  "W3-7_first_token": 0.22719054828367452,
  "S7": 0.8630204794586845,
  "S7_first_token": 0.8630204794586845,
  "S1": 0.9572233618828871,
  "S1_first_token": 0.9572233618828871,
  "S2": 0.8986852544304301,
  "S2_first_token": 0.8986852544304301,
  "G": 0.9704016121378366,
  "G_first_token": 0.9704016121378366,
  "S4": 0.9027303724799953,
  "S4_first_token": 0.9027303724799953,
  "S9": 0.888560869009088,
  "S9_first_token": 0.888560869009088,
  "W1-5": 0.8463311117327827,
  "W1-5_first_token": 0.3980035995857294,
  "S10": 0.9133087275655914,
  "S10_first_token": 0.9133087275655914,
  "F": 0.6045997890864474,
  "F_first_token": 0.6045997890864474,
  "S3": 0.9128954685700206,
  "S3_first_token": 0.9128954685700206,
  "S8": 0.8925284152186058,
  "S8_first_token": 0.8925284152186058,
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
 "generation_seconds": 190.7,
 "gpu": "NVIDIA A100-SXM4-80GB"
}
```

