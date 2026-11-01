# Calibration gate, qwen (SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0)

**Overall: PASS**

Frozen epsilon for this judge: 0.9922 log-odds

| Gate | Status | Detail |
|---|---|---|
| preflight_passed | PASS | `"PASS"` |
| serving | PASS | `{"model_id": "Qwen/Qwen3-32B", "model_commit": "9216db5781bf21249d130ec9da846c4624c16137", "gpu": "NVIDIA A100-SXM4-80GB", "driver": "595.91.07", "cuda": "12.8", "torch": "2.11.0+cu128", "transformers": "5.22.0", "accelerate": "1.15.0", "huggingface_hub": "2.4.0", "mistral_common": null, "chat_template_sha256": "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8", "tekken_sha256": null, "code_commit": "0acf376c9925630f38a415f8ff039a9f5e96dc39"}` |
| prompts | PASS | `{"hash_mismatch": [], "model_names_in_prompt": []}` |
| complete | PASS | `{"n": 36, "expected": 36, "tokenwise": 36}` |
| finite | PASS | `{"n_values": 180}` |
| floor | PASS | `{"max_abs_delta_d_preflight_and_calibration": 0.4960937350988388, "epsilon": 0.9921874701976776, "stop_at": 1.0}` |
| label_mass | PASS | `{"median_mass_AB": 0.9883283023015366, "min_mass_AB": 0.9621944192503041, "threshold": 0.5}` |
| cal_last_digit | PASS | `{"n": 6, "S_correct": 6, "both_orders": 6, "required": [5, 4]}` |
| cal_all_faces | PASS | `{"n": 6, "S_correct": 6, "both_orders": 6, "required": [5, 4]}` |

## Information (not gated)

```json
{
 "tasks": {
  "last_digit": {
   "n": 6,
   "S_correct": 6,
   "both_orders": 6,
   "items": {
    "last_digit-1": {
     "correct": "6 1 1 6 2 3",
     "foil": "6 1 1 6 2 5",
     "s1": 12.5011,
     "s2": 7.5937,
     "S": 10.0474,
     "label_bias": 2.4537,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "last_digit-2": {
     "correct": "3 2 2 4 5 4",
     "foil": "3 2 2 4 5 6",
     "s1": 8.9378,
     "s2": 2.5173,
     "S": 5.7276,
     "label_bias": 3.2103,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "last_digit-3": {
     "correct": "1 2 5 1 3 2",
     "foil": "1 2 5 1 3 1",
     "s1": 9.1132,
     "s2": 6.3061,
     "S": 7.7096,
     "label_bias": 1.4035,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "last_digit-4": {
     "correct": "4 4 1 4 1 5",
     "foil": "4 4 1 4 1 3",
     "s1": 13.3336,
     "s2": 8.3234,
     "S": 10.8285,
     "label_bias": 2.5051,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "last_digit-5": {
     "correct": "6 1 6 3 2 1",
     "foil": "6 1 6 3 2 4",
     "s1": 9.3891,
     "s2": 4.6509,
     "S": 7.02,
     "label_bias": 2.3691,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "last_digit-6": {
     "correct": "3 3 1 2 2 6",
     "foil": "3 3 1 2 2 5",
     "s1": 13.9055,
     "s2": 7.7683,
     "S": 10.8369,
     "label_bias": 3.0686,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    }
   }
  },
  "all_faces": {
   "n": 6,
   "S_correct": 6,
   "both_orders": 6,
   "items": {
    "all_faces-1": {
     "correct": "3 6 2 4 5 1",
     "foil": "3 6 2 4 5 5",
     "s1": 15.5595,
     "s2": 10.8165,
     "S": 13.188,
     "label_bias": 2.3715,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "all_faces-2": {
     "correct": "5 1 4 2 6 3",
     "foil": "5 1 4 2 6 6",
     "s1": 14.9258,
     "s2": 10.3292,
     "S": 12.6275,
     "label_bias": 2.2983,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "all_faces-3": {
     "correct": "6 4 2 5 3 1",
     "foil": "6 4 2 5 3 3",
     "s1": 15.4378,
     "s2": 10.3582,
     "S": 12.898,
     "label_bias": 2.5398,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "all_faces-4": {
     "correct": "4 2 6 5 1 3",
     "foil": "4 2 6 5 1 1",
     "s1": 15.0182,
     "s2": 10.4513,
     "S": 12.7348,
     "label_bias": 2.2835,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "all_faces-5": {
     "correct": "6 2 5 3 4 1",
     "foil": "6 2 5 3 4 4",
     "s1": 15.4688,
     "s2": 10.7745,
     "S": 13.1216,
     "label_bias": 2.3472,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "all_faces-6": {
     "correct": "4 6 2 1 3 5",
     "foil": "4 6 2 1 3 3",
     "s1": 15.4373,
     "s2": 10.0891,
     "S": 12.7632,
     "label_bias": 2.6741,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    }
   }
  },
  "order56": {
   "n": 6,
   "S_correct": 5,
   "both_orders": 3,
   "items": {
    "order56-1": {
     "correct": "6 3 4 5 2 1",
     "foil": "6 3 4 5 1 2",
     "s1": 0.4938,
     "s2": 1.0448,
     "S": 0.7693,
     "label_bias": -0.2755,
     "cls": "mixed_or_tied",
     "greedy": [
      "A",
      "B"
     ]
    },
    "order56-2": {
     "correct": "1 6 2 4 5 3",
     "foil": "1 6 2 4 3 5",
     "s1": 3.9407,
     "s2": -0.1936,
     "S": 1.8736,
     "label_bias": 2.0672,
     "cls": "mixed_or_tied",
     "greedy": [
      "A",
      "A"
     ]
    },
    "order56-3": {
     "correct": "1 5 3 2 6 4",
     "foil": "1 5 3 2 4 6",
     "s1": 4.29,
     "s2": 2.1581,
     "S": 3.224,
     "label_bias": 1.066,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "order56-4": {
     "correct": "4 2 1 5 6 3",
     "foil": "4 2 1 5 3 6",
     "s1": 3.8399,
     "s2": -1.1585,
     "S": 1.3407,
     "label_bias": 2.4992,
     "cls": "mixed_or_tied",
     "greedy": [
      "A",
      "A"
     ]
    },
    "order56-5": {
     "correct": "5 6 4 1 3 2",
     "foil": "5 6 4 1 2 3",
     "s1": 4.4056,
     "s2": 2.0718,
     "S": 3.2387,
     "label_bias": 1.1669,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "order56-6": {
     "correct": "5 6 1 4 3 2",
     "foil": "5 6 1 4 2 3",
     "s1": 2.7813,
     "s2": 1.1692,
     "S": 1.9753,
     "label_bias": 0.806,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    }
   }
  }
 },
 "reported_not_gated": {
  "order56": {
   "n": 6,
   "S_correct": 5,
   "both_orders": 3
  }
 },
 "strict_valid": "36/36",
 "mean_label_bias": 2.047467457353681,
 "seconds": 237.1
}
```

