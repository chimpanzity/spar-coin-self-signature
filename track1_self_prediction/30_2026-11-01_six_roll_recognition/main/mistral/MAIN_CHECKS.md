# Main checks, mistral (SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0)

**Overall: PASS**

| Gate | Status | Detail |
|---|---|---|
| calibration_passed | PASS | `{"epsilon": 0.5072165364399552}` |
| references_equal_exp28 | PASS | `null` |
| serving | PASS | `{"model_id": "mistralai/Mistral-Small-3.2-24B-Instruct-2506", "model_commit": "95a6d26c4bfb886c58daf9d3f7332c857cb27b43", "gpu": "NVIDIA A100-SXM4-80GB", "driver": "595.91.07", "cuda": "12.8", "torch": "2.11.0+cu128", "transformers": "5.22.0", "accelerate": "1.15.0", "huggingface_hub": "2.4.0", "mistral_common": "1.13.0", "chat_template_sha256": null, "tekken_sha256": "6e2501687ccd0e1f30f36319eaf2b46958b897811e246cd8eb5d385b9e3de7d1", "code_commit": "0acf376c9925630f38a415f8ff039a9f5e96dc39"}` |
| prompts | PASS | `{"hash_mismatch": [], "model_names_in_prompt": []}` |
| complete | PASS | `{"n": 96, "expected": 96, "tokenwise": 32}` |
| finite | PASS | `{"n_values": 352}` |
| deterministic_replicates | PASS | `{"n_prompts": 32, "differing": {}}` |
| raw_files_untampered | PASS | `{"presentations_sha256": "cfed96d0ffe25f19cc5a7cea6e8cb257462300d376f411fb51e619b17d4675eb"}` |

## Information (not gated)

```json
{
 "epsilon": 0.5072165364399552,
 "main_floor": 0.09471498429775238,
 "main_floor_exceeds_epsilon": false,
 "median_mass_AB": 0.9439109357046297,
 "low_mass_presentations": [],
 "strict_valid": "96/96",
 "seconds": 111.5
}
```

