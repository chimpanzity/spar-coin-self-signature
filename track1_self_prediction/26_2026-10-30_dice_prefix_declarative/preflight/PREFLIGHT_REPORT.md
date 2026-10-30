# Preflight report (SPAR_DICE_PREFIX_DECLARATIVE_v1.0)

Run `preflight`. **Overall: PASS**

| Gate | Status | Detail |
|---|---|---|
| serving | PASS | `{"model_commit": "9216db5781bf21249d130ec9da846c4624c16137", "chat_template_sha256": "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8", "rendered_G": "5c5bb4193ac7634b82765c91ef75399166b97edadea66924d56396d4355cc185", "gpu": "NVIDIA A100-SXM4-80GB", "torch": "2.11.0+cu128", "transfo` |
| non_thinking | PASS | `"every rendered prompt ends with the empty think block; no system turn; no think text in outputs"` |
| face_tokens | PASS | `{"face_bare_ids": {"1": 16, "2": 17, "3": 18, "4": 19, "5": 20, "6": 21}, "separator_id": 220, "note": "each digit is one bare token, separated by one space token"}` |
| face_logprobs | PASS | `{"n_steps": 84, "min_six_face_mass": 0.997857}` |
| scorer_matches_generation | PASS | `{"max_abs_logprob_diff": 0.0, "tol": 0.0001}` |
| reference_reproduction | PASS | `{"sequences_identical": true, "n_G_F_runs": 6, "max_abs_dp_vs_archive": 0.0, "tol": 0.01}` |
| determinism | PASS | `{"max_spread_logprob": {"G": 0.0, "F": 0.0}}` |
| k3_outputs_valid | PASS | `{"N3": "3 1 4", "S3": "3 1 4", "H3": "3 1 4", "O3": "3 1 4"}` |
| k3_teacher_forced_complete | PASS | `{"n_rows": 12}` |

Numerical floor: incremental vs full pass max |dp| = 0.0911 over 42 distributions; near-tie floor = 0.091.
