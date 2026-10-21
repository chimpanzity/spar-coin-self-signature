# Blind Twin self-self pilot: does truthful identity help observers more when the players knew?

Run `btss-20261011`. Protocol BlindTwinSelfSelf_v1. Exploratory pilot. Judges Astra, Fable and Qwen predicted both players' moves in the 24 Experiment 1 self-self games (each model vs itself; condition 00 = neither told, 11 = both told; RPS and MP; 2 games per cell) under TRUE, FALSE and ANONYMOUS labels. Every prompt states, without naming a model, what the players were told.

## Completion and cost

- Judge calls: 4320 recorded of 4320 planned; valid predictions: 4318.
- Paired items (valid under all three labels): {'astra': 960, 'fable': 956, 'qwen': 960} of 960 per judge.
- Charged cost: $23.40 (hard cap $40).

## Interaction indices (percentage points; 5,000 whole-game bootstrap resamples within game type x model x condition)

Delta = (TRUE - ANONYMOUS in 11 games) - (TRUE - ANONYMOUS in 00 games). Self: judge predicts its own model. Other: judges predict a different model. Self-specific = self - other (primary, per game type).

| index | estimate | 95% interval |
|---|---:|---|
| **RPS Delta self-specific (primary)** | -4.8 | [-9.6, +0.0] |
| RPS Delta self | -1.6 | [-6.2, +3.0] |
| RPS Delta other | +3.2 | [+0.8, +5.5] |
| RPS DeltaF self-specific (TRUE vs FALSE) | +1.6 | [-4.3, +7.2] |
| RPS Delta[astra judging astra] | -5.0 | [-17.5, +7.5] |
| RPS Delta[fable judging fable] | -4.9 | [-10.0, +0.1] |
| RPS Delta[qwen judging qwen] | +5.0 | [+2.5, +7.5] |
| RPS S within condition 00 | +2.9 | [-0.8, +6.7] |
| RPS S within condition 11 | -1.9 | [-4.2, +0.4] |
| **MP Delta self-specific (primary)** | +0.0 | [-7.3, +7.5] |
| MP Delta self | -1.7 | [-6.3, +2.9] |
| MP Delta other | -1.7 | [-6.7, +3.1] |
| MP DeltaF self-specific (TRUE vs FALSE) | -3.7 | [-9.0, +1.5] |
| MP Delta[astra judging astra] | +2.5 | [-5.0, +10.0] |
| MP Delta[fable judging fable] | -11.2 | [-15.0, -7.5] |
| MP Delta[qwen judging qwen] | +3.8 | [-7.5, +15.0] |
| MP S within condition 00 | -0.2 | [-5.6, +5.2] |
| MP S within condition 11 | -0.2 | [-4.8, +4.4] |
| Pooled Delta self-specific, secondary | -2.4 | [-6.9, +2.1] |
| Pooled DeltaF self-specific, secondary | -1.1 | [-5.1, +2.8] |

## RPS accuracy (percent; chance = 33.3)

| judge | player model | 00 TRUE | 00 FALSE | 00 ANON | 11 TRUE | 11 FALSE | 11 ANON | T00 | T11 | Delta |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| astra | astra (self) | 50.0 | 56.2 | 43.8 | 52.5 | 51.2 | 51.2 | +6.2 | +1.3 | -5.0 |
| astra | fable | 45.0 | 46.2 | 42.5 | 41.2 | 35.0 | 38.8 | +2.5 | +2.5 | +0.0 |
| astra | qwen | 47.5 | 45.0 | 46.2 | 43.8 | 41.2 | 37.5 | +1.2 | +6.2 | +5.0 |
| fable | astra | 40.0 | 37.5 | 40.0 | 36.2 | 37.5 | 41.2 | +0.0 | -5.0 | -5.0 |
| fable | fable (self) | 36.2 | 32.5 | 31.2 | 37.2 | 39.9 | 37.2 | +5.0 | +0.1 | -4.9 |
| fable | qwen | 37.5 | 47.5 | 42.5 | 47.5 | 43.7 | 41.1 | -5.0 | +6.4 | +11.4 |
| qwen | astra | 38.8 | 30.0 | 37.5 | 37.5 | 35.0 | 37.5 | +1.2 | +0.0 | -1.2 |
| qwen | fable | 37.5 | 30.0 | 37.5 | 33.8 | 32.5 | 25.0 | +0.0 | +8.8 | +8.8 |
| qwen | qwen (self) | 31.2 | 31.2 | 33.8 | 42.5 | 36.2 | 40.0 | -2.5 | +2.5 | +5.0 |

External history-only classifiers on the same RPS games (percent of choices predicted; best_rule = best single rule per player-game, optimistic):

| player model | condition | uniform | expanding_frequency | repeat_last | markov1_smoothed | counter_opponent_last | best_rule |
|---|---|---:|---:|---:|---:|---:|---:|
| astra | 00 | 33.3 | 23.5 | 20.4 | 30.4 | 21.7 | 31.7 |
| astra | 11 | 33.3 | 27.5 | 19.2 | 39.4 | 25.4 | 39.4 |
| fable | 00 | 33.3 | 26.5 | 17.9 | 35.0 | 30.4 | 38.1 |
| fable | 11 | 33.3 | 25.8 | 21.7 | 33.1 | 21.7 | 34.0 |
| qwen | 00 | 33.3 | 29.4 | 37.9 | 29.6 | 49.2 | 49.2 |
| qwen | 11 | 33.3 | 32.7 | 39.2 | 33.8 | 49.2 | 49.2 |

## MP accuracy (percent; chance = 50.0)

| judge | player model | 00 TRUE | 00 FALSE | 00 ANON | 11 TRUE | 11 FALSE | 11 ANON | T00 | T11 | Delta |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| astra | astra (self) | 52.5 | 52.5 | 57.5 | 63.7 | 66.2 | 66.2 | -5.0 | -2.5 | +2.5 |
| astra | fable | 60.0 | 57.5 | 58.7 | 52.5 | 53.8 | 56.2 | +1.3 | -3.8 | -5.0 |
| astra | qwen | 43.8 | 41.2 | 42.5 | 50.0 | 56.2 | 46.2 | +1.2 | +3.8 | +2.5 |
| fable | astra | 58.8 | 53.8 | 61.3 | 60.0 | 52.5 | 58.7 | -2.5 | +1.3 | +3.8 |
| fable | fable (self) | 56.2 | 52.5 | 52.5 | 55.0 | 61.3 | 62.5 | +3.8 | -7.5 | -11.2 |
| fable | qwen | 46.2 | 50.0 | 53.8 | 57.5 | 55.0 | 61.2 | -7.5 | -3.8 | +3.8 |
| qwen | astra | 51.2 | 72.5 | 58.8 | 50.0 | 53.8 | 60.0 | -7.5 | -10.0 | -2.5 |
| qwen | fable | 56.2 | 50.0 | 50.0 | 45.0 | 52.5 | 51.2 | +6.2 | -6.2 | -12.5 |
| qwen | qwen (self) | 62.5 | 60.0 | 66.3 | 53.8 | 50.0 | 53.8 | -3.8 | +0.0 | +3.8 |

External history-only classifiers on the same MP games (percent of choices predicted; best_rule = best single rule per player-game, optimistic):

| player model | condition | uniform | expanding_frequency | repeat_last | markov1_smoothed | best_response_opponent_last | win_stay_lose_shift | best_rule |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| astra | 00 | 50.0 | 43.1 | 48.8 | 46.2 | 36.2 | 36.2 | 51.2 |
| astra | 11 | 50.0 | 40.0 | 43.8 | 47.5 | 21.2 | 21.2 | 48.8 |
| fable | 00 | 50.0 | 45.0 | 41.2 | 44.4 | 43.8 | 43.8 | 52.5 |
| fable | 11 | 50.0 | 48.1 | 38.8 | 51.9 | 51.2 | 51.2 | 58.1 |
| qwen | 00 | 50.0 | 41.2 | 61.2 | 48.1 | 58.8 | 58.8 | 67.5 |
| qwen | 11 | 50.0 | 39.4 | 47.5 | 41.9 | 50.0 | 50.0 | 56.2 |

## Interpretation boundaries

- Pilot: 2 games per (game type, model, condition); each judge x label x cell has 80 predictions. Delta is a difference of differences, so intervals are wide. Not a test of privileged access.
- The 00 self-self games were judged before (BlindTwinExp1_v1) without the player-information sentence; they are re-judged here so both conditions share one prompt. The earlier run is not pooled with this one.
- MP Qwen self-self games include make-ups (QQ_00_1_MU2, QQ_11_1_MU6) with the condition-dependent selection caveat in EXPERIMENT1_MAKEUP_GAMES.md.
- A positive Delta_self can reflect generic behaviour change under mutual disclosure; Delta_other is the control.

