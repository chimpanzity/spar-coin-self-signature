# Preflight, qwen (SPAR_CROSSED_GUIDED_SELFPRED_v1.0)

**Overall: PASS**

| Gate | Status | Detail |
|---|---|---|
| serving | PASS | `{"model_id": "Qwen/Qwen3-32B", "model_commit": "9216db5781bf21249d130ec9da846c4624c16137", "gpu": "NVIDIA A100-SXM4-80GB", "torch": "2.11.0+cu128", "transformers": "5.22.0", "cuda": "12.8", "chat_template_sha256": "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8", "tekken_sha256": null, "mistral_common": null}` |
| template | PASS | `{"rendered_G": "<|im_start|>user\nGenerate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"}` |
| face_tokens | PASS | `{"face_ids": {"1": 16, "2": 17, "3": 18, "4": 19, "5": 20, "6": 21}, "separator_id": 220}` |
| face_logprobs_finite | PASS | `{"n_steps": 278}` |
| face_mass_direct_generation | PASS | `{"n_steps": 90, "min_six_face_mass": 0.999994639362477, "amendment": "v1.1"}` |
| scorer_matches_generation | PASS | `{"max_abs_logprob_diff": 0.0, "tol": 0.0001}` |
| determinism | PASS | `{"G": {"outputs": ["5 2 6 3 1 4 6 2 5 3"], "max_spread": 0.0}, "F": {"outputs": ["3 1 4 6 2 5 3 2 6 4"], "max_spread": 0.0}}` |
| greedy_G_valid | PASS | `{"G": "5 2 6 3 1 4 6 2 5 3", "F": "3 1 4 6 2 5 3 2 6 4"}` |
| qwen_exp21_regression | PASS | `{"sequences_identical": true, "n": 90, "max_abs_dp": 0.0, "tol": 0.01}` |
| qwen_exp26_regression | PASS | `{"free_outputs_identical": {"H0": true, "N0": true, "S0": true, "O0": true, "H3": true, "N3": true, "S3": true, "O3": true, "H6": true, "N6": true, "S6": true, "O6": true}, "n": 36, "max_abs_dp": 0.0, "k3_free": {"H3": "3 1 4", "N3": "3 1 4", "S3": "3 1 4", "O3": "3 1 4"}}` |
| engine_equals_exp21_class | PASS | `[{"prompt": "G", "content_equal": true, "max_abs_face_logprob_diff": 0.0}, {"prompt": "G|G score", "max_abs_face_logprob_diff": 0.0}, {"prompt": "F", "content_equal": true, "max_abs_face_logprob_diff": 0.0}, {"prompt": "F|G score", "max_abs_face_logprob_diff": 0.0}]` |
| numerical_floor | PASS | `{"max_abs_dp_incremental_vs_full_pass": 0.09107393562453042, "n": 150, "stop_above": 0.25}` |

Information (not gated): `{"feasibility": ["4 2 6 3 1 5 2 5 3 6", "5 3 1 6 2 4 3 5 6 1", "3 6 2 1 5 4 2 6 3 1", "5 2 6 1 3 4 6 2 5 1"], "feasibility_valid": 4, "crossed_format_check": {"crossed_AH_k3": "4 3 1", "crossed_TD_m3": "4 1 3", "crossed_RI_k8": "3 5"}, "sec_per_crossed_trial": [1.9551384449005127, 1.9780404567718506, 1.371870994567871], "max_memory_allocated_gb": 66.82, "floor": 0.09107393562453042, "prediction_prompt_min_mass_reported_not_gated": {"F": 0.9978566380683462, "x26_N0": 0.9970790230562102, "Fanon": 0.9947249922859536, "x26_O6": 0.9993201729374437, "x26_H0": 0.999519194304952, "x26_N6": 0.999796712130873, "x26_S3": 0.9999974402746789, "x26_S0": 0.9984063694431788, "x26_O3": 0.9999927113759766, "x26_N3": 0.9999965039496129, "x26_S6": 0.9998922326865728, "x26_H6": 0.9990845554233302, "x26_H3": 0.9998689051941358, "x26_O0": 0.9982010817918202, "crossed_AH_k3": 0.996925668121228, "crossed_TD_m3": 0.9987260937169916, "crossed_RI_k8": 0.9980139241323177, "mp_F|G": 0.9978566380683462, "mp_F|F": 0.9978566380683462, "mp_Fanon|G": 0.9947249922859536}}`

