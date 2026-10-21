# Opponent self-identity disclosure: Astra vs Astra matching pennies (pilot report)

Run `od-20261009T1200Z`. Protocol OpponentDisclosure_v1. Exploratory pilot; game-level bootstrap (8 games per condition); no multiplicity correction.

## Completion and cost

| condition (matcher, mismatcher informed) | games complete / 8 | valid rounds |
|---|---:|---:|
| 00 | 8 | 160 / 160 |
| 10 | 8 | 160 / 160 |
| 01 | 8 | 160 / 160 |
| 11 | 8 | 160 / 160 |

- Player calls: 1280 recorded, 1280 valid.
- Charged cost: $6.65 scientific + $0.40 technical smoke = $7.05 (ceiling $25).
- Incomplete games: none.

## Primary outcome: Matcher win rate (percent of rounds; 50% = equilibrium)

| condition | mean Matcher win rate |
|---|---:|
| 00 | 53.1 |
| 10 | 57.5 |
| 01 | 53.1 |
| 11 | 58.8 |

| contrast (percentage points) | estimate | 95% bootstrap interval |
|---|---:|---|
| Informing the Matcher: mean(10,11) - mean(00,01) | +5.0 | [+0.6, +9.7] |
| Informing the Mismatcher: mean(01,11) - mean(00,10) | +0.6 | [-3.4, +5.3] |
| Interaction: (11-01) - (10-00) | +1.2 | [-7.5, +9.4] |
| Unilateral Matcher (10) - mutual (11) | -1.2 | [-5.6, +3.1] |
| Unilateral Mismatcher (01) - mutual (11) | -5.6 | [-11.2, +0.0] |
| Mutual (11) - neither (00) | +5.6 | [-1.2, +13.1] |

Undefined bootstrap replicates: 0.000. A positive Matcher-informed effect means informing the Matcher raised its win rate.

## Player behaviour by condition (means over games)

| outcome | 00 | 10 | 01 | 11 | own-informed effect | opponent-informed effect |
|---|---:|---:|---:|---:|---:|---:|
| matcher_pct_star | 53.8 | 51.2 | 50.0 | 55.0 | +1.2 [-3.1, +5.9] | +0.0 [-4.4, +4.4] |
| matcher_switch_rate | 53.3 | 57.9 | 48.7 | 51.3 | +3.6 [+0.7, +6.6] | -5.6 [-8.6, -2.6] |
| matcher_longest_run | 3.9 | 4.4 | 5.0 | 5.0 | +0.2 [-0.6, +1.1] | +0.9 [+0.1, +1.7] |
| matcher_pred_best | 58.8 | 58.1 | 55.0 | 54.4 | -0.6 [-3.8, +2.5] | -3.8 [-6.9, -0.6] |
| matcher_pred_repeat_last | 46.9 | 42.5 | 51.2 | 48.8 | -3.4 [-6.2, -0.6] | +5.3 [+2.5, +8.1] |
| matcher_pred_alternate_last | 53.1 | 57.5 | 48.8 | 51.2 | +3.4 [+0.6, +6.2] | -5.3 [-8.1, -2.5] |
| matcher_pred_win_stay_lose_shift | 44.4 | 40.0 | 34.4 | 35.0 | -1.9 [-12.2, +8.1] | -7.5 [-17.5, +2.5] |
| mismatcher_pct_star | 58.1 | 51.2 | 50.6 | 46.2 | -6.2 [-11.6, -0.6] | -5.6 [-10.9, -0.3] |
| mismatcher_switch_rate | 51.3 | 45.4 | 53.9 | 50.0 | +3.6 [-1.3, +8.2] | -4.9 [-9.5, +0.0] |
| mismatcher_longest_run | 5.1 | 5.9 | 4.5 | 4.6 | -0.9 [-1.9, +0.1] | +0.4 [-0.6, +1.4] |
| mismatcher_pred_best | 57.8 | 59.4 | 55.6 | 55.0 | -3.3 [-5.2, -1.4] | +0.5 [-1.4, +2.5] |
| mismatcher_pred_repeat_last | 48.8 | 54.4 | 46.2 | 50.0 | -3.4 [-7.8, +1.6] | +4.7 [+0.0, +9.1] |
| mismatcher_pred_alternate_last | 51.2 | 45.6 | 53.8 | 50.0 | +3.4 [-1.6, +7.8] | -4.7 [-9.1, +0.0] |
| mismatcher_pred_win_stay_lose_shift | 38.8 | 49.4 | 34.4 | 43.8 | -5.0 [-10.3, +0.3] | +10.0 [+4.7, +15.3] |

`pred_*` = percent of a player's choices predicted by a history-only rule (round 1 and ties = half credit); `pred_best` = the best of five rules per game (optimistic exploitability index).

## Manipulation check (descriptive)

| role | informed | responses | % mentioning same model / instance / Astra / self | % with reasoning lines | median completion tokens |
|---|---|---:|---:|---:|---:|
| matcher | False | 320 | 0.0 | 0.0 | 38.0 |
| matcher | True | 320 | 0.0 | 0.0 | 43.5 |
| mismatcher | False | 320 | 0.0 | 0.0 | 34.0 |
| mismatcher | True | 320 | 0.0 | 0.0 | 42.0 |

## Games

| game | condition | rounds | Matcher wins | matcher %STAR | mismatcher %STAR |
|---|---|---:|---:|---:|---:|
| D00_1 | 00 | 20 | 9 | 55.0 | 70.0 |
| D11_1 | 11 | 20 | 11 | 55.0 | 50.0 |
| D01_1 | 01 | 20 | 11 | 55.0 | 50.0 |
| D10_1 | 10 | 20 | 13 | 40.0 | 55.0 |
| D01_2 | 01 | 20 | 12 | 35.0 | 45.0 |
| D11_2 | 11 | 20 | 11 | 60.0 | 45.0 |
| D00_2 | 00 | 20 | 7 | 55.0 | 40.0 |
| D10_2 | 10 | 20 | 11 | 65.0 | 50.0 |
| D11_3 | 11 | 20 | 11 | 50.0 | 55.0 |
| D10_3 | 10 | 20 | 12 | 55.0 | 45.0 |
| D01_3 | 01 | 20 | 10 | 45.0 | 65.0 |
| D00_3 | 00 | 20 | 10 | 45.0 | 65.0 |
| D10_4 | 10 | 20 | 10 | 55.0 | 55.0 |
| D01_4 | 01 | 20 | 10 | 50.0 | 50.0 |
| D00_4 | 00 | 20 | 12 | 50.0 | 60.0 |
| D11_4 | 11 | 20 | 12 | 55.0 | 35.0 |
| D10_5 | 10 | 20 | 12 | 40.0 | 60.0 |
| D00_5 | 00 | 20 | 13 | 60.0 | 65.0 |
| D01_5 | 01 | 20 | 10 | 50.0 | 40.0 |
| D11_5 | 11 | 20 | 11 | 55.0 | 50.0 |
| D11_6 | 11 | 20 | 12 | 45.0 | 45.0 |
| D00_6 | 00 | 20 | 12 | 50.0 | 60.0 |
| D10_6 | 10 | 20 | 11 | 45.0 | 60.0 |
| D01_6 | 01 | 20 | 13 | 55.0 | 50.0 |
| D11_7 | 11 | 20 | 12 | 55.0 | 45.0 |
| D00_7 | 00 | 20 | 11 | 60.0 | 65.0 |
| D01_7 | 01 | 20 | 9 | 50.0 | 55.0 |
| D10_7 | 10 | 20 | 12 | 55.0 | 45.0 |
| D11_8 | 11 | 20 | 14 | 65.0 | 45.0 |
| D10_8 | 10 | 20 | 11 | 55.0 | 40.0 |
| D00_8 | 00 | 20 | 11 | 55.0 | 40.0 |
| D01_8 | 01 | 20 | 10 | 60.0 | 50.0 |

## Limitations

- One model (Astra), 8 games per condition, 20 rounds: exploratory. Intervals reflect game-to-game variation only.
- 'Same model' means another independently queried instance; an effect shows the behavioural consequence of the identity sentence, not introspection.
- Astra's endpoint has no temperature control; games ran at provider-default sampling with low hidden reasoning.
- The handoff text ended mid-way through the parsing section. Invalid-answer handling, the analysis plan and the budget are Claude's prespecified defaults (protocol.md), fixed before data.

