# DICE_LOGPROB_v1.0 open-weight preflight report

Run folder: `preflight-qwen3-32b-a100`. Overall: **PASS**. Main collection not started.

Serving: `Qwen/Qwen3-32B` @ `9216db5781bf21249d130ec9da846c4624c16137`, bfloat16 weights and activations; lm_head and logits fp32, NVIDIA A100-SXM4-80GB (79.3 GB), driver 595.91.07, CUDA 12.8, torch 2.11.0+cu128, transformers 5.22.0, Python 3.11.9. Greedy, batch 1, chat template `enable_thinking=False` (template sha256 `a55ee1b1660128b7…`). Model load 15.5 s.

## Gates

| Gate | Result |
|---|---|
| serving_recorded | PASS |
| non_thinking | PASS |
| valid_numeric_outputs_all_conditions | PASS |
| complete_six_face_vectors_all_positions_G_F | PASS |
| references_repeatable_9_of_10 | PASS |
| matched_prefix_scoring_valid | PASS |

## Reproducibility

- **G**: modal `5 2 6 3 1 4 6 2 5 3` in 10/10; 1 distinct; max |Δ logprob| across identical outputs 0.00e+00
- **F**: modal `3 1 4 6 2 5 3 2 6 4` in 10/10; 1 distinct; max |Δ logprob| across identical outputs 0.00e+00

## Teacher-forced scoring vs generation (own modal history)

`incremental` (gated) feeds the history through the KV cache like generation; `full_pass` is one forward pass, and its gap to generation estimates the bf16 numerical precision floor.

- **G|incremental**: 10 positions, argmax agrees: True, max |Δ p6| 0.00e+00 (gate < 0.0001); max |Δ logprob| 0.00e+00 nats
- **G|full_pass**: 10 positions, argmax agrees: True, max |Δ p6| 3.38e-02 (reported, not gated); max |Δ logprob| 2.60e-01 nats
- **F|incremental**: 10 positions, argmax agrees: True, max |Δ p6| 0.00e+00 (gate < 0.0001); max |Δ logprob| 0.00e+00 nats
- **F|full_pass**: 10 positions, argmax agrees: False, max |Δ p6| 9.11e-02 (reported, not gated); max |Δ logprob| 4.10e-01 nats

## Responses

| Trial | Verdict | Content | Comparable positions | Ambiguity flags | Min six-face mass |
|---|---|---|---|---|---|
| F-1 | valid | `3 1 4 6 2 5 3 2 6 4` | 10/10 | 0 | 0.9979 |
| F-10 | valid | `3 1 4 6 2 5 3 2 6 4` | 10/10 | 0 | 0.9979 |
| F-2 | valid | `3 1 4 6 2 5 3 2 6 4` | 10/10 | 0 | 0.9979 |
| F-3 | valid | `3 1 4 6 2 5 3 2 6 4` | 10/10 | 0 | 0.9979 |
| F-4 | valid | `3 1 4 6 2 5 3 2 6 4` | 10/10 | 0 | 0.9979 |
| F-5 | valid | `3 1 4 6 2 5 3 2 6 4` | 10/10 | 0 | 0.9979 |
| F-6 | valid | `3 1 4 6 2 5 3 2 6 4` | 10/10 | 0 | 0.9979 |
| F-7 | valid | `3 1 4 6 2 5 3 2 6 4` | 10/10 | 0 | 0.9979 |
| F-8 | valid | `3 1 4 6 2 5 3 2 6 4` | 10/10 | 0 | 0.9979 |
| F-9 | valid | `3 1 4 6 2 5 3 2 6 4` | 10/10 | 0 | 0.9979 |
| G-1 | valid | `5 2 6 3 1 4 6 2 5 3` | 10/10 | 0 | 1.0000 |
| G-10 | valid | `5 2 6 3 1 4 6 2 5 3` | 10/10 | 0 | 1.0000 |
| G-2 | valid | `5 2 6 3 1 4 6 2 5 3` | 10/10 | 0 | 1.0000 |
| G-3 | valid | `5 2 6 3 1 4 6 2 5 3` | 10/10 | 0 | 1.0000 |
| G-4 | valid | `5 2 6 3 1 4 6 2 5 3` | 10/10 | 0 | 1.0000 |
| G-5 | valid | `5 2 6 3 1 4 6 2 5 3` | 10/10 | 0 | 1.0000 |
| G-6 | valid | `5 2 6 3 1 4 6 2 5 3` | 10/10 | 0 | 1.0000 |
| G-7 | valid | `5 2 6 3 1 4 6 2 5 3` | 10/10 | 0 | 1.0000 |
| G-8 | valid | `5 2 6 3 1 4 6 2 5 3` | 10/10 | 0 | 1.0000 |
| G-9 | valid | `5 2 6 3 1 4 6 2 5 3` | 10/10 | 0 | 1.0000 |
| S1-1 | valid | `4` | 1/1 | 0 | 1.0000 |
| S10-1 | valid | `4` | 1/1 | 0 | 1.0000 |
| S2-1 | valid | `4` | 1/1 | 0 | 1.0000 |
| S3-1 | valid | `5` | 1/1 | 0 | 1.0000 |
| S4-1 | valid | `5` | 1/1 | 0 | 1.0000 |
| S5-1 | valid | `4` | 1/1 | 0 | 1.0000 |
| S6-1 | valid | `4` | 1/1 | 0 | 1.0000 |
| S7-1 | valid | `4` | 1/1 | 0 | 0.9998 |
| S8-1 | valid | `4` | 1/1 | 0 | 1.0000 |
| S9-1 | valid | `5` | 1/1 | 0 | 1.0000 |
| W1-5-1 | valid | `4 2 6 3 5` | 5/5 | 0 | 0.9981 |
| W3-8-1 | valid | `4 2 5 3 6 1` | 6/6 | 0 | 0.9963 |
| W5-10-1 | valid | `3 6 2 5 1 4` | 6/6 | 0 | 0.9983 |
