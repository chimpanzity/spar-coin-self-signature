# Experiment 36 checks

- qwen: PASS: pilot gates
- qwen: PASS: full gates (replay, repeat, hooks off, projection, finite)
- qwen: PASS: archival G/F replay
- qwen: PASS: 2,400 rows, frozen order and prompt hashes
- qwen: PASS: array rows match metadata
- qwen: PASS: pinned revision
- qwen: PASS: array hashes
- qwen: {"shape": {"n": 47, "max_dp": 0.0, "bit_identical": 47}, "self": {"n": 8, "max_dp": 0.0, "bit_identical": 8}, "generic": {"n": 8, "max_dp": 0.0, "bit_identical": 8}, "direct": {"n": 61, "max_dp": 0.0, "bit_identical": 61}}: replay detail
- qwen: 0.00012969970703125: projection_max_abs
- mistral: PASS: pilot gates
- mistral: PASS: full gates (replay, repeat, hooks off, projection, finite)
- mistral: PASS: archival G/F replay
- mistral: PASS: 2,400 rows, frozen order and prompt hashes
- mistral: PASS: array rows match metadata
- mistral: PASS: pinned revision
- mistral: PASS: array hashes
- mistral: {"shape": {"n": 47, "max_dp": 0.0, "bit_identical": 47}, "self": {"n": 8, "max_dp": 0.0, "bit_identical": 8}, "generic": {"n": 8, "max_dp": 0.0, "bit_identical": 8}, "direct": {"n": 61, "max_dp": 0.0, "bit_identical": 61}}: replay detail
- mistral: 0.000110626220703125: projection_max_abs
