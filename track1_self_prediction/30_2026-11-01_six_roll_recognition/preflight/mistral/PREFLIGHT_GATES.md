# Preflight, mistral (SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0)

**Overall: PASS**

| Gate | Status | Detail |
|---|---|---|
| references_equal_exp28 | PASS | `{"qwen-G": {"sequence10": "5 2 6 3 1 4 6 2 5 3", "authentic": "5 2 6 3 1 4", "swap": "5 2 6 3 4 1", "repeat": "5 2 6 3 1 1", "p5_authentic_swap": [0.860814, 0.139107], "handoff_p5": [0.8608, 0.1391], "p5_match": true}, "qwen-F": {"sequence10": "3 1 4 6 2 5 3 2 6 4", "authentic": "3 1 4 6 2 5", "swap": "3 1 4 6 5 2", "repeat": "3 1 4 6 2 2", "p5_authentic_swap": [0.999628, 0.000372], "handoff_p5": [0.999628, 0.000372], "p5_match": true}, "mistral-G": {"sequence10": "4 2 6 1 3 5 2 4 6 1", "authentic": "4 2 6 1 3 5", "swap": "4 2 6 1 5 3", "repeat": "4 2 6 1 3 3", "p5_authentic_swap": [0.686719, ` |
| serving | PASS | `{"model_id": "mistralai/Mistral-Small-3.2-24B-Instruct-2506", "model_commit": "95a6d26c4bfb886c58daf9d3f7332c857cb27b43", "gpu": "NVIDIA A100-SXM4-80GB", "driver": "595.91.07", "cuda": "12.8", "torch": "2.11.0+cu128", "transformers": "5.22.0", "accelerate": "1.15.0", "huggingface_hub": "2.4.0", "mistral_common": "1.13.0", "chat_template_sha256": null, "tekken_sha256": "6e2501687ccd0e1f30f36319eaf2b46958b897811e246cd8eb5d385b9e3de7d1", "code_commit": "0acf376c9925630f38a415f8ff039a9f5e96dc39"}` |
| template | PASS | `{"rendered_G": "<s>[INST]Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.[/INST]"}` |
| face_tokens | PASS | `{"face_ids": {"1": 1049, "2": 1050, "3": 1051, "4": 1052, "5": 1053, "6": 1054}, "separator_id": 1032, "vocab_size": 131072, "variant_face_tokens": [], "multi_digit_ascii_tokens": []}` |
| label_tokens | PASS | `{"label_tokens": {"A": {"id": 1065, "n_tokens": 1, "text": "A", "space_id": 1349}, "B": {"id": 1066, "n_tokens": 1, "text": "B", "space_id": 1398}}, "context": {"label_appends_single_token": {"A": true, "B": true}, "note": "mistral_common encodes the prompt at token level; the answer token is appended as an id", "assistant_prefix_tail": "B: 2 + 2 = 5\n\nAnswer A or B only.[/INST]"}}` |
| prompts | PASS | `{"hash_mismatch": [], "model_names_in_prompt": []}` |
| face_mass_archival_G | PASS | `{"n": 20, "min_six_face_mass": 0.9704016121378367}` |
| archival_regression | PASS | `{"archive": "Experiment 28 main", "conditions": {"G": {"outputs": ["4 2 6 1 3 5 2 4 6 1"], "archived": "4 2 6 1 3 5 2 4 6 1", "n": 2}, "F": {"outputs": ["3 1 5 2 6 4 3 1 5 2"], "archived": "3 1 5 2 6 4 3 1 5 2", "n": 2}}, "n_vectors": 40, "max_abs_dp": 0.0, "tol": 0.01}` |
| archival_determinism | PASS | `{"G": {"n": 2, "outputs": ["4 2 6 1 3 5 2 4 6 1"], "max_logprob_spread": 0.0}, "F": {"n": 2, "outputs": ["3 1 5 2 6 4 3 1 5 2"], "max_logprob_spread": 0.0}}` |
| tech_complete | PASS | `{"n": 12, "expected": 12, "tokenwise": 4}` |
| tech_finite | PASS | `{"n_values": 44}` |
| tech_repeats_identical | PASS | `{"n_prompts": 4, "differing": {}}` |
| tech_label_mass | PASS | `{"min_mass_AB": 0.9439740805591597, "threshold": 0.5}` |
| tech_arithmetic_both_orders | PASS | `{"d_by_orientation": {"1": 12.333733048290014, "2": -9.928209310717648}}` |
| tech_floor | PASS | `{"max_abs_delta_d": 0.06303783506155014, "provisional_epsilon": 0.12607567012310028, "stop_at": 1.0}` |
| policy_complete | PASS | `{"rows": 144, "incremental": 72, "finite": true}` |
| policy_shared_contexts_identical | PASS | `{"n": 24}` |
| policy_diagonal_regression | PASS | `{"archive": "Experiment 28 main generation steps 1-6", "max_abs_dp": 0.0, "tol": 0.01}` |
| policy_floor | PASS | `{"max_abs_dp_incremental_vs_full_pass": 0.010254858376766818, "stop_above": 0.25}` |
| policy_mass | PASS | `{"median_raw_mass": 0.9999945370870762, "min_raw_mass": 0.6045997890864474}` |

## Information (not gated)

```json
{
 "greedy_answers": {
  "tech-selfframe-o2": "A",
  "tech-arith-o1": "A",
  "tech-arith-o2": "B",
  "tech-selfframe-o1": "A"
 },
 "strict_valid": "12/12",
 "tech_scores": {
  "tech-selfframe-o2": {
   "d": 3.2673988044261932,
   "mass_AB": 0.9539743434614691,
   "top": [
    [
     1065,
     "A",
     -0.08451583981513977
    ],
    [
     1066,
     "B",
     -3.351914644241333
    ],
    [
     1784,
     "The",
     -3.82494854927063
    ],
    [
     36686,
     "Both",
     -4.393846035003662
    ],
    [
     2892,
     "To",
     -4.657756328582764
    ]
   ]
  },
  "tech-arith-o1": {
   "d": 12.333733048290014,
   "mass_AB": 0.9754787256786913,
   "top": [
    [
     1065,
     "A",
     -0.02483132854104042
    ],
    [
     31106,
     "Answer",
     -3.710628032684326
    ],
    [
     1784,
     "The",
     -10.053020477294922
    ],
    [
     1066,
     "B",
     -12.358564376831055
    ],
    [
     1438,
     "**",
     -12.874256134033203
    ]
   ]
  },
  "tech-arith-o2": {
   "d": -9.928209310717648,
   "mass_AB": 0.9999400667085082,
   "top": [
    [
     1066,
     "B",
     -0.00010871296399272978
    ],
    [
     1065,
     "A",
     -9.92831802368164
    ],
    [
     1784,
     "The",
     -10.14494514465332
    ],
    [
     31106,
     "Answer",
     -11.103860855102539
    ],
    [
     1438,
     "**",
     -13.622129440307617
    ]
   ]
  },
  "tech-selfframe-o1": {
   "d": 3.218356966972351,
   "mass_AB": 0.9439740805591597,
   "top": [
    [
     1065,
     "A",
     -0.09689724445343018
    ],
    [
     1066,
     "B",
     -3.3152542114257812
    ],
    [
     1784,
     "The",
     -3.799722671508789
    ],
    [
     36686,
     "Both",
     -4.1038665771484375
    ],
    [
     2892,
     "To",
     -4.21375846862793
    ]
   ]
  }
 },
 "seconds": {
  "vocab": 0.4,
  "archival": 4.0,
  "policy": 7.1,
  "tech": 11.4
 },
 "max_memory_allocated_gb": 49.73
}
```

