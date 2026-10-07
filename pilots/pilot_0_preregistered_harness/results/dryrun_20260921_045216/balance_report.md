# Trial balance report

## Judge: astra

- trials: 24; per cell: {'A': 6, 'B': 6, 'C': 6, 'D': 6}; per sub-cell: {'A': 6, 'B:fable': 3, 'B:qwen': 3, 'C:fable': 3, 'C:qwen': 3, 'D': 6}
- correct answers: {'DIFFERENT': 12, 'SAME': 12}
- source-pair frequencies: {'astra-astra': 6, 'astra-fable': 3, 'astra-qwen': 3, 'fable-fable': 3, 'fable-qwen': 6, 'qwen-qwen': 3}
- String 1 / String 2 by model: {'astra': {'string_1': 9, 'string_2': 9}, 'fable': {'string_1': 8, 'string_2': 7}, 'qwen': {'string_1': 7, 'string_2': 8}}
- position balance in DIFFERENT sub-cells: {'B:qwen': {'judge_as_string_1': 2, 'judge_as_string_2': 1}, 'B:fable': {'judge_as_string_1': 1, 'judge_as_string_2': 2}, 'D': {'fable_as_string_1': 3, 'fable_as_string_2': 3}}
- use count [min, max] per model: {'astra': [1, 2], 'qwen': [1, 2], 'fable': [1, 2]}
- self pairs: 0; duplicate unordered pairs: 0
- longest run by cell: {'A': 1, 'B': 2, 'C': 2, 'D': 2} (any cell: 2)
- longest run by answer: {'SAME': 3, 'DIFFERENT': 3} (any answer: 3)
- construction seed: 20260921:astra; build attempts: 2

| check | result | detail |
|---|---|---|
| six_trials_per_cell | PASS | {'A': 6, 'B': 6, 'C': 6, 'D': 6} (expected 6 each) |
| same_different_balance | PASS | {'DIFFERENT': 12, 'SAME': 12} (expected 12 each) |
| cell_B_balanced_across_others | PASS | B per other: [3, 3] (expected [3, 3]) |
| cell_C_balanced_across_others | PASS | C per other: [3, 3] (expected [3, 3]) |
| no_self_pairs | PASS | 0 self pairs |
| no_duplicate_unordered_pairs | PASS | 0 duplicates |
| string_reuse_balanced | PASS | use-count [min,max] per model: {'astra': [1, 2], 'qwen': [1, 2], 'fable': [1, 2]} |
| display_order_balanced | PASS | B:qwen: {'judge_as_string_1': 2, 'judge_as_string_2': 1}; B:fable: {'judge_as_string_1': 1, 'judge_as_string_2': 2}; D: {'fable_as_string_1': 3, 'fable_as_string_2': 3}; astra S1/S2: 9/9; fable S1/S2: 8/7; qwen S1/S2: 7/8 |
| max_cell_run_le_2 | PASS | longest run of one cell: 2 |
| unique_positions_and_ids | PASS | positions and trial ids unique |

Use counts per string:

- astra: 001x1, 002x2, 003x2, 004x2, 005x2, 006x1, 007x2, 008x2, 009x2, 010x2
- fable: 001x1, 002x2, 003x1, 004x1, 005x1, 006x1, 007x2, 008x2, 009x2, 010x2
- qwen: 001x1, 002x2, 003x1, 004x2, 005x2, 006x2, 007x2, 008x1, 009x1, 010x1

## Judge: fable

- trials: 24; per cell: {'A': 6, 'B': 6, 'C': 6, 'D': 6}; per sub-cell: {'A': 6, 'B:astra': 3, 'B:qwen': 3, 'C:astra': 3, 'C:qwen': 3, 'D': 6}
- correct answers: {'DIFFERENT': 12, 'SAME': 12}
- source-pair frequencies: {'astra-astra': 3, 'astra-fable': 3, 'astra-qwen': 6, 'fable-fable': 6, 'fable-qwen': 3, 'qwen-qwen': 3}
- String 1 / String 2 by model: {'astra': {'string_1': 8, 'string_2': 7}, 'fable': {'string_1': 9, 'string_2': 9}, 'qwen': {'string_1': 7, 'string_2': 8}}
- position balance in DIFFERENT sub-cells: {'D': {'astra_as_string_1': 3, 'astra_as_string_2': 3}, 'B:qwen': {'judge_as_string_1': 2, 'judge_as_string_2': 1}, 'B:astra': {'judge_as_string_1': 1, 'judge_as_string_2': 2}}
- use count [min, max] per model: {'astra': [1, 2], 'qwen': [1, 2], 'fable': [1, 2]}
- self pairs: 0; duplicate unordered pairs: 0
- longest run by cell: {'A': 2, 'B': 2, 'C': 2, 'D': 2} (any cell: 2)
- longest run by answer: {'SAME': 3, 'DIFFERENT': 3} (any answer: 3)
- construction seed: 20260921:fable; build attempts: 1

| check | result | detail |
|---|---|---|
| six_trials_per_cell | PASS | {'A': 6, 'B': 6, 'C': 6, 'D': 6} (expected 6 each) |
| same_different_balance | PASS | {'DIFFERENT': 12, 'SAME': 12} (expected 12 each) |
| cell_B_balanced_across_others | PASS | B per other: [3, 3] (expected [3, 3]) |
| cell_C_balanced_across_others | PASS | C per other: [3, 3] (expected [3, 3]) |
| no_self_pairs | PASS | 0 self pairs |
| no_duplicate_unordered_pairs | PASS | 0 duplicates |
| string_reuse_balanced | PASS | use-count [min,max] per model: {'astra': [1, 2], 'qwen': [1, 2], 'fable': [1, 2]} |
| display_order_balanced | PASS | D: {'astra_as_string_1': 3, 'astra_as_string_2': 3}; B:qwen: {'judge_as_string_1': 2, 'judge_as_string_2': 1}; B:astra: {'judge_as_string_1': 1, 'judge_as_string_2': 2}; astra S1/S2: 8/7; fable S1/S2: 9/9; qwen S1/S2: 7/8 |
| max_cell_run_le_2 | PASS | longest run of one cell: 2 |
| unique_positions_and_ids | PASS | positions and trial ids unique |

Use counts per string:

- astra: 001x2, 002x2, 003x1, 004x1, 005x1, 006x1, 007x1, 008x2, 009x2, 010x2
- fable: 001x1, 002x2, 003x2, 004x1, 005x2, 006x2, 007x2, 008x2, 009x2, 010x2
- qwen: 001x1, 002x1, 003x2, 004x1, 005x2, 006x2, 007x1, 008x1, 009x2, 010x2

## Judge: qwen

- trials: 24; per cell: {'A': 6, 'B': 6, 'C': 6, 'D': 6}; per sub-cell: {'A': 6, 'B:astra': 3, 'B:fable': 3, 'C:astra': 3, 'C:fable': 3, 'D': 6}
- correct answers: {'DIFFERENT': 12, 'SAME': 12}
- source-pair frequencies: {'astra-astra': 3, 'astra-fable': 6, 'astra-qwen': 3, 'fable-fable': 3, 'fable-qwen': 3, 'qwen-qwen': 6}
- String 1 / String 2 by model: {'astra': {'string_1': 8, 'string_2': 7}, 'fable': {'string_1': 7, 'string_2': 8}, 'qwen': {'string_1': 9, 'string_2': 9}}
- position balance in DIFFERENT sub-cells: {'B:fable': {'judge_as_string_1': 2, 'judge_as_string_2': 1}, 'B:astra': {'judge_as_string_1': 1, 'judge_as_string_2': 2}, 'D': {'astra_as_string_1': 3, 'astra_as_string_2': 3}}
- use count [min, max] per model: {'fable': [1, 2], 'astra': [1, 2], 'qwen': [1, 2]}
- self pairs: 0; duplicate unordered pairs: 0
- longest run by cell: {'A': 2, 'B': 1, 'C': 2, 'D': 1} (any cell: 2)
- longest run by answer: {'SAME': 2, 'DIFFERENT': 3} (any answer: 3)
- construction seed: 20260921:qwen; build attempts: 1

| check | result | detail |
|---|---|---|
| six_trials_per_cell | PASS | {'A': 6, 'B': 6, 'C': 6, 'D': 6} (expected 6 each) |
| same_different_balance | PASS | {'DIFFERENT': 12, 'SAME': 12} (expected 12 each) |
| cell_B_balanced_across_others | PASS | B per other: [3, 3] (expected [3, 3]) |
| cell_C_balanced_across_others | PASS | C per other: [3, 3] (expected [3, 3]) |
| no_self_pairs | PASS | 0 self pairs |
| no_duplicate_unordered_pairs | PASS | 0 duplicates |
| string_reuse_balanced | PASS | use-count [min,max] per model: {'fable': [1, 2], 'astra': [1, 2], 'qwen': [1, 2]} |
| display_order_balanced | PASS | B:fable: {'judge_as_string_1': 2, 'judge_as_string_2': 1}; B:astra: {'judge_as_string_1': 1, 'judge_as_string_2': 2}; D: {'astra_as_string_1': 3, 'astra_as_string_2': 3}; astra S1/S2: 8/7; fable S1/S2: 7/8; qwen S1/S2: 9/9 |
| max_cell_run_le_2 | PASS | longest run of one cell: 2 |
| unique_positions_and_ids | PASS | positions and trial ids unique |

Use counts per string:

- astra: 001x1, 002x2, 003x1, 004x2, 005x1, 006x2, 007x1, 008x2, 009x1, 010x2
- fable: 001x1, 002x2, 003x1, 004x1, 005x2, 006x2, 007x1, 008x2, 009x2, 010x1
- qwen: 001x2, 002x1, 003x2, 004x2, 005x1, 006x2, 007x2, 008x2, 009x2, 010x2
