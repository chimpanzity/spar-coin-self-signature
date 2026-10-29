# Generic-model control: preflight report

Run `control-preflight-qwen3-32b-a100`. Overall: **PASS**.

Serving: `Qwen/Qwen3-32B` @ `9216db5781bf21249d130ec9da846c4624c16137`, bfloat16 weights and activations; lm_head and logits fp32, NVIDIA A100-SXM4-80GB, driver 595.91.07, CUDA 12.8, torch 2.11.0+cu128, transformers 5.22.0. Greedy, batch 1, `enable_thinking=False`.

| Gate | Result |
|---|---|
| prompt_hashes_frozen | PASS |
| valid_ten_face_outputs | PASS |
| non_thinking | PASS |
| complete_six_face_vectors_all_positions | PASS |
| reproducible_within_condition | PASS |
| G_F_reproduce_experiment_21 | PASS |
| teacher_forcing_reproduces_generation | PASS |

## Reproducibility

- **G**: `5 2 6 3 1 4 6 2 5 3` in 3/3; max p6 spread 0.00e+00
- **F**: `3 1 4 6 2 5 3 2 6 4` in 3/3; max p6 spread 0.00e+00
- **N**: `1 3 5 2 6 4 2 5 1 6` in 3/3; max p6 spread 0.00e+00

## Compatibility with Experiment 21 (archived main run)

- **G**: archived `5 2 6 3 1 4 6 2 5 3`, new `5 2 6 3 1 4 6 2 5 3`; identical: True; max |Δ p6| vs archived 0.00e+00
- **F**: archived `3 1 4 6 2 5 3 2 6 4`, new `3 1 4 6 2 5 3 2 6 4`; identical: True; max |Δ p6| vs archived 0.00e+00

## Teacher forcing (incremental) vs own generation

- **G|G**: 10 positions, max |Δ p6| 0.00e+00 (gate < 0.0001)
- **F|F**: 10 positions, max |Δ p6| 0.00e+00 (gate < 0.0001)
- **N|N**: 10 positions, max |Δ p6| 0.00e+00 (gate < 0.0001)

Numerical precision floor (incremental vs full-pass, max |Δ p6|): 0.149.

## Prompt hashes

- G: `edc7a4a228d493e83a5086181c170aa052e3e7cb8b34b9911ef4dc8147fdb8fe`
- F: `8adcaddfff0d9acee6bcc9060917175e7d68167f440c42b00a3800cd32dcef03`
- N: `09afdbeec5d8c4c12bea04a8a922aee462350a50a935b776ef87ca94fc0423f1`
