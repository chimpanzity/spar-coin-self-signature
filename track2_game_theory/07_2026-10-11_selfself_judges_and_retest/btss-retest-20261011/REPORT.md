# Blind Twin judge test-retest (2026-10-11)

Games: ['mp:AA_00_1', 'mp:FF_00_1', 'mp:QQ_00_1_MU2', 'rps:AA_00_1', 'rps:FF_00_1', 'rps:QQ_00_1'] (first condition-00 self-self game per game type x model). Same items judged three times:
`btx1` (2026-10-10, no player-information line), `btss` (2026-10-11 morning, with the line) and `retest` (prompts byte-identical to btss).

- Retest calls: 1080; valid 1080; cost $5.77.

## Agreement of individual predictions (same judge, game, round, seat, label)

| comparison | what differs | judge | n | identical % | accuracy A | accuracy B |
|---|---|---|---:|---:|---:|---:|
| btss vs retest | nothing (sampling noise) | astra | 720 | 84.9 | 51.1 | 51.8 |
| btss vs retest | nothing (sampling noise) | fable | 720 | 88.1 | 45.3 | 45.8 |
| btss vs retest | nothing (sampling noise) | qwen | 720 | 67.4 | 46.5 | 47.1 |
| btss vs retest | nothing (sampling noise) | all | 2160 | 80.1 | 47.6 | 48.2 |
| btx1 vs btss | info line + noise | astra | 720 | 83.3 | 47.9 | 51.1 |
| btx1 vs btss | info line + noise | fable | 720 | 85.1 | 47.4 | 45.3 |
| btx1 vs btss | info line + noise | qwen | 720 | 66.9 | 45.0 | 46.5 |
| btx1 vs btss | info line + noise | all | 2160 | 78.5 | 46.8 | 47.6 |
| btx1 vs retest | info line + noise | astra | 720 | 84.3 | 47.9 | 51.8 |
| btx1 vs retest | info line + noise | fable | 720 | 86.2 | 47.4 | 45.8 |
| btx1 vs retest | info line + noise | qwen | 720 | 67.2 | 45.0 | 47.1 |
| btx1 vs retest | info line + noise | all | 2160 | 79.3 | 46.8 | 48.2 |

## Cell-level accuracy noise (judge x game x label cells of 40 predictions)

| comparison | n cells | mean abs diff (pp) | max abs diff (pp) | mean abs diff in T = TRUE-ANON (pp) |
|---|---:|---:|---:|---:|
| btss vs retest | 54 | 4.7 | 15.0 | 6.9 |
| btx1 vs btss | 54 | 5.2 | 15.0 | 7.2 |
| btx1 vs retest | 54 | 5.5 | 17.5 | 8.1 |

Reading: `btss vs retest` is the floor set by judge sampling alone. If `btx1 vs btss` agreement is no lower, the information line did not measurably change predictions and the differences seen earlier are noise.
