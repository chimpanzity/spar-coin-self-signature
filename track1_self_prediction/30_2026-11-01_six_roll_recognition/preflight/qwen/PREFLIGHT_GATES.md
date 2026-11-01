# Preflight, qwen (SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0)

**Overall: PASS**

| Gate | Status | Detail |
|---|---|---|
| references_equal_exp28 | PASS | `{"qwen-G": {"sequence10": "5 2 6 3 1 4 6 2 5 3", "authentic": "5 2 6 3 1 4", "swap": "5 2 6 3 4 1", "repeat": "5 2 6 3 1 1", "p5_authentic_swap": [0.860814, 0.139107], "handoff_p5": [0.8608, 0.1391], "p5_match": true}, "qwen-F": {"sequence10": "3 1 4 6 2 5 3 2 6 4", "authentic": "3 1 4 6 2 5", "swap": "3 1 4 6 5 2", "repeat": "3 1 4 6 2 2", "p5_authentic_swap": [0.999628, 0.000372], "handoff_p5": [0.999628, 0.000372], "p5_match": true}, "mistral-G": {"sequence10": "4 2 6 1 3 5 2 4 6 1", "authentic": "4 2 6 1 3 5", "swap": "4 2 6 1 5 3", "repeat": "4 2 6 1 3 3", "p5_authentic_swap": [0.686719, ` |
| serving | PASS | `{"model_id": "Qwen/Qwen3-32B", "model_commit": "9216db5781bf21249d130ec9da846c4624c16137", "gpu": "NVIDIA A100-SXM4-80GB", "driver": "595.91.07", "cuda": "12.8", "torch": "2.11.0+cu128", "transformers": "5.22.0", "accelerate": "1.15.0", "huggingface_hub": "2.4.0", "mistral_common": null, "chat_template_sha256": "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8", "tekken_sha256": null, "code_commit": "0acf376c9925630f38a415f8ff039a9f5e96dc39"}` |
| template | PASS | `{"rendered_G": "<|im_start|>user\nGenerate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"}` |
| face_tokens | PASS | `{"face_ids": {"1": 16, "2": 17, "3": 18, "4": 19, "5": 20, "6": 21}, "separator_id": 220, "vocab_size": 151669, "variant_face_tokens": [], "multi_digit_ascii_tokens": []}` |
| label_tokens | PASS | `{"label_tokens": {"A": {"id": 32, "n_tokens": 1, "text": "A", "space_id": 362}, "B": {"id": 33, "n_tokens": 1, "text": "B", "space_id": 425}}, "context": {"label_appends_single_token": {"A": true, "B": true}, "assistant_prefix_tail": "|im_start|>assistant\n<think>\n\n</think>\n\n"}}` |
| prompts | PASS | `{"hash_mismatch": [], "model_names_in_prompt": []}` |
| face_mass_archival_G | PASS | `{"n": 20, "min_six_face_mass": 0.9999946393624771}` |
| archival_regression | PASS | `{"archive": "Experiment 28 main", "conditions": {"G": {"outputs": ["5 2 6 3 1 4 6 2 5 3"], "archived": "5 2 6 3 1 4 6 2 5 3", "n": 2}, "F": {"outputs": ["3 1 4 6 2 5 3 2 6 4"], "archived": "3 1 4 6 2 5 3 2 6 4", "n": 2}}, "n_vectors": 40, "max_abs_dp": 0.0, "tol": 0.01}` |
| archival_determinism | PASS | `{"G": {"n": 2, "outputs": ["5 2 6 3 1 4 6 2 5 3"], "max_logprob_spread": 0.0}, "F": {"n": 2, "outputs": ["3 1 4 6 2 5 3 2 6 4"], "max_logprob_spread": 0.0}}` |
| tech_complete | PASS | `{"n": 12, "expected": 12, "tokenwise": 4}` |
| tech_finite | PASS | `{"n_values": 44}` |
| tech_repeats_identical | PASS | `{"n_prompts": 4, "differing": {}}` |
| tech_label_mass | PASS | `{"min_mass_AB": 0.9974224082165211, "threshold": 0.5}` |
| tech_arithmetic_both_orders | PASS | `{"d_by_orientation": {"1": 17.89801967144217, "2": -12.41957485677949}}` |
| tech_floor | PASS | `{"max_abs_delta_d": 0.3774873018114704, "provisional_epsilon": 0.7549746036229408, "stop_at": 1.0}` |
| policy_complete | PASS | `{"rows": 144, "incremental": 72, "finite": true}` |
| policy_shared_contexts_identical | PASS | `{"n": 24}` |
| policy_diagonal_regression | PASS | `{"archive": "Experiment 28 main generation steps 1-6", "max_abs_dp": 0.0, "tol": 0.01}` |
| policy_floor | PASS | `{"max_abs_dp_incremental_vs_full_pass": 0.0723651887546205, "stop_above": 0.25}` |
| policy_mass | PASS | `{"median_raw_mass": 0.9999999709179577, "min_raw_mass": 0.9978566380683462}` |

## Information (not gated)

```json
{
 "greedy_answers": {
  "tech-arith-o1": "A",
  "tech-selfframe-o2": "A",
  "tech-selfframe-o1": "A",
  "tech-arith-o2": "B"
 },
 "strict_valid": "12/12",
 "tech_scores": {
  "tech-arith-o1": {
   "d": 17.89801967144217,
   "mass_AB": 0.9999979903112394,
   "top": [
    [
     32,
     "A",
     -2.0265558760002023e-06
    ],
    [
     16141,
     "Answer",
     -13.121706008911133
    ],
    [
     33092,
     "Correct",
     -17.56662940979004
    ],
    [
     33,
     "B",
     -17.898021697998047
    ],
    [
     785,
     "The",
     -20.342920303344727
    ]
   ]
  },
  "tech-selfframe-o2": {
   "d": 6.199085149914026,
   "mass_AB": 0.9974224082165211,
   "top": [
    [
     32,
     "A",
     -0.004610147327184677
    ],
    [
     33,
     "B",
     -6.203695297241211
    ],
    [
     20629,
     "Both",
     -6.435342788696289
    ],
    [
     785,
     "The",
     -7.373647689819336
    ],
    [
     4854,
     "Each",
     -8.735918045043945
    ]
   ]
  },
  "tech-selfframe-o1": {
   "d": 6.767055322648957,
   "mass_AB": 0.9982068916667733,
   "top": [
    [
     32,
     "A",
     -0.0029451351147145033
    ],
    [
     20629,
     "Both",
     -6.7015380859375
    ],
    [
     33,
     "B",
     -6.770000457763672
    ],
    [
     785,
     "The",
     -7.875152587890625
    ],
    [
     4854,
     "Each",
     -9.666915893554688
    ]
   ]
  },
  "tech-arith-o2": {
   "d": -12.41957485677949,
   "mass_AB": 0.9999974822573316,
   "top": [
    [
     33,
     "B",
     -6.556489552167477e-06
    ],
    [
     32,
     "A",
     -12.419581413269043
    ],
    [
     16141,
     "Answer",
     -12.917254447937012
    ],
    [
     33092,
     "Correct",
     -16.73697853088379
    ],
    [
     785,
     "The",
     -18.041139602661133
    ]
   ]
  }
 },
 "seconds": {
  "vocab": 0.5,
  "archival": 7.4,
  "policy": 13.4,
  "tech": 24.9
 },
 "max_memory_allocated_gb": 66.82
}
```

