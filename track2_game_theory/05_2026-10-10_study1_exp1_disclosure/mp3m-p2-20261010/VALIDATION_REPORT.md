# VALIDATION REPORT

Generated 2026-10-10T20:20:22.516496Z for run `mp3m-p2-20261010`; code hash a10f02618e0a.

## Unit tests

```
..............                                                           [100%]
14 passed in 1.81s
```

## No-network fake full run

- Games: 72 (expected 72); complete: 72.
- Player calls: 2880 (expected 2880); transport: fake.
- Both seats received identical history in every round: True.
- D computed: 0.025000000000000005; independent rescore D: 0.025000000000000005; round-result mismatches: 0.
- Outputs: ['PROGRESS.md', 'REPORT.md', 'baseline_predictions.csv', 'behavioral_metrics.csv', 'bootstrap_intervals.csv', 'calls.jsonl', 'cell_means.csv', 'checksums.sha256', 'conditional_choice.csv', 'game_logs.jsonl', 'games.csv', 'invalids.csv', 'primary_contrasts.csv', 'results.json', 'rounds.csv']

## Parser against real Fable explanation-plus-final-answer responses

- Multi-line Fable responses re-expressed as shapes: 480; parsed to the intended shape: 480. PASS

## Prompt invariants

- Informed vs uninformed prompts differ only in the opponent-identity line, which names the true opponent, for all 9 pairings x 2 seats: PASS

Result: PASS
