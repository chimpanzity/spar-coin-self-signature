# SPAR_EXP31_CROSS_MODEL_TEACHER_FORCING_v1.0 post-run checks: **PASS**

| Check | Status | Detail |
|---|---|---|
| ground_truth | PASS |  |
| both_models_ran | PASS | ["mistral", "qwen"] |
| serving_identity | PASS |  |
| no_variant_face_tokens | PASS |  |
| archival_reproduces_exp28 | PASS | {"qwen": {"G": {"max_dp": 0.0, "equal": true}, "F": {"max_dp": 0.0, "equal": true}}, "mistral": {"G": {"max_dp": 0.0, "equal": true}, "F": {"max_dp": 0.0, "equa |
| raw_file_hashes | PASS |  |
| prompt_hashes | PASS |  |
| stream_records | PASS | 48 |
| labeled_rows_160 | PASS |  |
| finite | PASS |  |
| mass_in_0_1 | PASS |  |
| normalised_sum_1 | PASS |  |
| logprob_consistency | PASS |  |
| js_identity_and_bounds | PASS |  |
| indexing_prefix_j_minus_1_no_target | PASS |  |
| identical_contexts_identical_scores | PASS | {"labeled_rows": 160, "unique_contexts": 140, "shared_contexts": 12, "max_rows_per_context": 4, "mismatched_contexts": []} |
| replicates_bit_identical | PASS |  |
| floor_incremental_vs_full_pass | PASS | {"max_dp": 0.0910739699815809} |
| archival_equivalents_agree | PASS | {"rows_with_archive": 104, "max_abs_dlogp": 0.0} |
| no_model_names_in_prompts | PASS |  |
