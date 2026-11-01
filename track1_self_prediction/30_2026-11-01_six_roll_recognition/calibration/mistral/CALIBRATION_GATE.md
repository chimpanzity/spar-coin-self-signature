# Calibration gate, mistral (SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0)

**Overall: PASS**

Frozen epsilon for this judge: 0.5072 log-odds

| Gate | Status | Detail |
|---|---|---|
| preflight_passed | PASS | `"PASS"` |
| serving | PASS | `{"model_id": "mistralai/Mistral-Small-3.2-24B-Instruct-2506", "model_commit": "95a6d26c4bfb886c58daf9d3f7332c857cb27b43", "gpu": "NVIDIA A100-SXM4-80GB", "driver": "595.91.07", "cuda": "12.8", "torch": "2.11.0+cu128", "transformers": "5.22.0", "accelerate": "1.15.0", "huggingface_hub": "2.4.0", "mistral_common": "1.13.0", "chat_template_sha256": null, "tekken_sha256": "6e2501687ccd0e1f30f36319eaf2b46958b897811e246cd8eb5d385b9e3de7d1", "code_commit": "0acf376c9925630f38a415f8ff039a9f5e96dc39"}` |
| prompts | PASS | `{"hash_mismatch": [], "model_names_in_prompt": []}` |
| complete | PASS | `{"n": 36, "expected": 36, "tokenwise": 36}` |
| finite | PASS | `{"n_values": 180}` |
| floor | PASS | `{"max_abs_delta_d_preflight_and_calibration": 0.2536082682199776, "epsilon": 0.5072165364399552, "stop_at": 1.0}` |
| label_mass | PASS | `{"median_mass_AB": 0.9900722201448133, "min_mass_AB": 0.796614445666784, "threshold": 0.5}` |
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
     "s1": 8.7009,
     "s2": 7.3765,
     "S": 8.0387,
     "label_bias": 0.6622,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "last_digit-2": {
     "correct": "3 2 2 4 5 4",
     "foil": "3 2 2 4 5 6",
     "s1": 7.037,
     "s2": 3.1617,
     "S": 5.0993,
     "label_bias": 1.9376,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "last_digit-3": {
     "correct": "1 2 5 1 3 2",
     "foil": "1 2 5 1 3 1",
     "s1": 7.4846,
     "s2": 5.2341,
     "S": 6.3593,
     "label_bias": 1.1253,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "last_digit-4": {
     "correct": "4 4 1 4 1 5",
     "foil": "4 4 1 4 1 3",
     "s1": 9.3671,
     "s2": 7.7951,
     "S": 8.5811,
     "label_bias": 0.786,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "last_digit-5": {
     "correct": "6 1 6 3 2 1",
     "foil": "6 1 6 3 2 4",
     "s1": 7.3645,
     "s2": 6.1354,
     "S": 6.75,
     "label_bias": 0.6145,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "last_digit-6": {
     "correct": "3 3 1 2 2 6",
     "foil": "3 3 1 2 2 5",
     "s1": 9.9571,
     "s2": 7.5167,
     "S": 8.7369,
     "label_bias": 1.2202,
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
     "s1": 11.3502,
     "s2": 4.0449,
     "S": 7.6975,
     "label_bias": 3.6527,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "all_faces-2": {
     "correct": "5 1 4 2 6 3",
     "foil": "5 1 4 2 6 6",
     "s1": 11.6954,
     "s2": 3.3104,
     "S": 7.5029,
     "label_bias": 4.1925,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "all_faces-3": {
     "correct": "6 4 2 5 3 1",
     "foil": "6 4 2 5 3 3",
     "s1": 11.1839,
     "s2": 3.8474,
     "S": 7.5156,
     "label_bias": 3.6682,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "all_faces-4": {
     "correct": "4 2 6 5 1 3",
     "foil": "4 2 6 5 1 1",
     "s1": 12.0359,
     "s2": 3.1511,
     "S": 7.5935,
     "label_bias": 4.4424,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "all_faces-5": {
     "correct": "6 2 5 3 4 1",
     "foil": "6 2 5 3 4 4",
     "s1": 11.4093,
     "s2": 4.3219,
     "S": 7.8656,
     "label_bias": 3.5437,
     "cls": "consistent_target",
     "greedy": [
      "A",
      "B"
     ]
    },
    "all_faces-6": {
     "correct": "4 6 2 1 3 5",
     "foil": "4 6 2 1 3 3",
     "s1": 11.8205,
     "s2": 3.0473,
     "S": 7.4339,
     "label_bias": 4.3866,
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
   "S_correct": 6,
   "both_orders": 0,
   "items": {
    "order56-1": {
     "correct": "6 3 4 5 2 1",
     "foil": "6 3 4 5 1 2",
     "s1": 5.5073,
     "s2": -2.6203,
     "S": 1.4435,
     "label_bias": 4.0638,
     "cls": "mixed_or_tied",
     "greedy": [
      "A",
      "A"
     ]
    },
    "order56-2": {
     "correct": "1 6 2 4 5 3",
     "foil": "1 6 2 4 3 5",
     "s1": 5.4464,
     "s2": -3.2738,
     "S": 1.0863,
     "label_bias": 4.3601,
     "cls": "mixed_or_tied",
     "greedy": [
      "A",
      "A"
     ]
    },
    "order56-3": {
     "correct": "1 5 3 2 6 4",
     "foil": "1 5 3 2 4 6",
     "s1": 6.1135,
     "s2": -2.8918,
     "S": 1.6109,
     "label_bias": 4.5026,
     "cls": "mixed_or_tied",
     "greedy": [
      "A",
      "A"
     ]
    },
    "order56-4": {
     "correct": "4 2 1 5 6 3",
     "foil": "4 2 1 5 3 6",
     "s1": 5.425,
     "s2": -2.417,
     "S": 1.504,
     "label_bias": 3.921,
     "cls": "mixed_or_tied",
     "greedy": [
      "A",
      "A"
     ]
    },
    "order56-5": {
     "correct": "5 6 4 1 3 2",
     "foil": "5 6 4 1 2 3",
     "s1": 5.823,
     "s2": -3.5232,
     "S": 1.1499,
     "label_bias": 4.6731,
     "cls": "mixed_or_tied",
     "greedy": [
      "A",
      "A"
     ]
    },
    "order56-6": {
     "correct": "5 6 1 4 3 2",
     "foil": "5 6 1 4 2 3",
     "s1": 6.3836,
     "s2": -4.0036,
     "S": 1.19,
     "label_bias": 5.1936,
     "cls": "mixed_or_tied",
     "greedy": [
      "A",
      "A"
     ]
    }
   }
  }
 },
 "reported_not_gated": {
  "order56": {
   "n": 6,
   "S_correct": 6,
   "both_orders": 0
  }
 },
 "strict_valid": "36/36",
 "mean_label_bias": 3.1636699443980536,
 "seconds": 108.3
}
```

