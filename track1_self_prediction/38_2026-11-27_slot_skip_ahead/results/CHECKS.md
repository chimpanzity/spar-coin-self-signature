# Experiment 38 checks

- PASS: 548 prompts per predictor, prompt bytes and hashes equal the frozen design
- PASS: 170 policy prefixes per generator
- PASS: archival G/F replay (Experiment 28)
- PASS: anchors reproduce (Experiment 35 SLOT, Experiment 32 B and C)
- PASS: policy reproduces Experiment 31 (|dp| <= 0.01)
- PASS: pinned revisions
- PASS: first-answer replicate bit-identical
- PASS: first-answer scores equal the generation step
- PASS: one-step copies across the six branches bit-identical
- PASS: Qwen standard boundary: rendered prompt ends with the empty think block
- PASS: face token ids
- PASS: anchor prompts in the grid give the anchor outputs
- PASS: raw file hashes

Full-pass floor: prompts max |dp| = 0.0000; policy max |dp| = 0.1017. Experiment 31 rows bit-identical: {'qwen': '32/32', 'mistral': '32/32'}.
