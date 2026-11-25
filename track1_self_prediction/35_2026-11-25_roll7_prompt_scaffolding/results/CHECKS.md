# Experiment 35 checks

- PASS: 36 cells x 2 replicates
- PASS: prompt bytes and hashes equal the frozen design
- PASS: baseline hashes equal Experiment 32 prompts_frozen.md
- PASS: archival G/F replay (Experiment 28)
- PASS: Experiment 32 B replay
- PASS: Experiment 32 B replay bit-identical
- PASS: pinned revisions
- PASS: replicates bit-identical
- PASS: standard answer scores equal the generation step
- PASS: standard boundary: rendered prompt ends with the empty think block (Qwen)
- PASS: thinking prompt ends at the assistant header
- PASS: thinking boundary follows </think> and whitespace only
- PASS: thinking without a boundary has no scores
- PASS: supplementary runs extend the primary greedy path
- PASS: face token ids
- PASS: six-face probabilities sum to one, mass <= 1
- PASS: raw file hashes

Full-pass floor (standard cells): max |dp| = 0.0000
