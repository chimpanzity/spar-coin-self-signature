# Blind Twin RPS pilot: morning report

Run `rps-qf-20261009T1045Z`. Protocol BlindTwinRPS_v1. Exploratory feasibility pilot, not confirmatory.

## Completion and cost

| matchup (player_a-player_b) | games complete / 3 | valid rounds |
|---|---:|---:|
| qwen-qwen | 3 | 60 / 60 |
| qwen-fable | 3 | 60 / 60 |
| fable-qwen | 3 | 60 / 60 |
| fable-fable | 3 | 60 / 60 |

- Player calls: 480 recorded, 480 valid choices.
- Judge calls: 1440 recorded, 1435 valid predictions (paired items valid in all three conditions: {'qwen': 480, 'fable': 472}).
- Charged cost: $10.86 scientific + $0.96 technical smoke = $11.82 (ceiling $25).
- Incomplete games: none.

## Accuracy table (percent correct, equal-weight over seat x opponent strata and games; 33.3% = random guess)

| judge | predicted player model | TRUE | FALSE | ANONYMOUS |
|---|---|---:|---:|---:|
| qwen | qwen (self) | 40.0 | 41.2 | 39.6 |
| qwen | fable | 35.8 | 32.1 | 33.8 |
| fable | qwen | 38.6 | 48.6 | 44.7 |
| fable | fable (self) | 46.9 | 39.3 | 40.0 |

## Identity indices (percentage points; game-level bootstrap within matchup, 5,000 resamples of 3 games per type)

| index | estimate | 95% interval |
|---|---:|---|
| **S: self-specific truth benefit (TRUE vs ANONYMOUS), primary** | +5.7 | [+1.2, +10.9] |
| S_false: self-specific false-label cost (TRUE vs FALSE), key companion | +6.3 | [+3.2, +9.8] |
| T[qwen,qwen] truth benefit | +0.4 | [-4.2, +5.8] |
| T[qwen,fable] truth benefit | +2.1 | [-3.7, +7.9] |
| T[fable,qwen] truth benefit | -6.2 | [-12.5, +0.6] |
| T[fable,fable] truth benefit | +6.9 | [+3.8, +10.9] |
| F[qwen,qwen] false-label cost | -1.2 | [-4.2, +1.7] |
| F[qwen,fable] false-label cost | +3.8 | [+0.0, +8.3] |
| F[fable,qwen] false-label cost | -10.0 | [-14.2, -5.9] |
| F[fable,fable] false-label cost | +7.6 | [+4.6, +10.5] |

With 3 games per matchup these intervals describe game-to-game variation only; rounds within a game are not independent subjects.

## Label responsiveness (percent of paired items whose hard prediction differs)

| judge | seat | comparison | n | % differ |
|---|---|---|---:|---:|
| qwen | player_a | TRUE vs FALSE | 240 | 37.1 |
| qwen | player_a | TRUE vs ANONYMOUS | 240 | 38.8 |
| qwen | player_a | FALSE vs ANONYMOUS | 240 | 37.9 |
| qwen | player_b | TRUE vs FALSE | 240 | 38.8 |
| qwen | player_b | TRUE vs ANONYMOUS | 240 | 37.9 |
| qwen | player_b | FALSE vs ANONYMOUS | 240 | 36.7 |
| fable | player_a | TRUE vs FALSE | 238 | 21.0 |
| fable | player_a | TRUE vs ANONYMOUS | 237 | 15.2 |
| fable | player_a | FALSE vs ANONYMOUS | 236 | 16.9 |
| fable | player_b | TRUE vs FALSE | 238 | 34.5 |
| fable | player_b | TRUE vs ANONYMOUS | 237 | 25.3 |
| fable | player_b | FALSE vs ANONYMOUS | 236 | 30.1 |

## Simple history-only baselines (percent correct; round 1 and tied predictions get fractional credit; chance 33.3%)

| baseline | all valid rounds | on qwen judge items | on fable judge items |
|---|---:|---:|---:|
| frequency | 29.5 | 29.5 | 29.6 |
| repeat_last | 30.8 | 30.8 | 30.9 |
| cycle_up | 30.2 | 30.2 | 29.9 |
| cycle_down | 39.0 | 39.0 | 39.2 |
| counter_opponent_last | 39.4 | 39.4 | 39.6 |
| win_stay_lose_shift | 39.4 | 39.4 | 39.6 |
| markov1 | 33.5 | 33.5 | 33.3 |

Both-seats-correct rate (descriptive only): qwen/TRUE 13.3% of 240; qwen/FALSE 11.7% of 240; qwen/ANONYMOUS 12.5% of 240; fable/TRUE 17.8% of 236; fable/FALSE 19.1% of 236; fable/ANONYMOUS 16.9% of 236

## Per-judge, role-specific breakdown (all rounds, paired items)

| judge | condition | seat | player model | % correct | n |
|---|---|---|---|---:|---:|
| qwen | TRUE | player_a | qwen | 35.0 | 120 |
| qwen | TRUE | player_a | fable | 32.5 | 120 |
| qwen | TRUE | player_b | qwen | 45.0 | 120 |
| qwen | TRUE | player_b | fable | 39.2 | 120 |
| qwen | FALSE | player_a | qwen | 40.0 | 120 |
| qwen | FALSE | player_a | fable | 31.7 | 120 |
| qwen | FALSE | player_b | qwen | 42.5 | 120 |
| qwen | FALSE | player_b | fable | 32.5 | 120 |
| qwen | ANONYMOUS | player_a | qwen | 38.3 | 120 |
| qwen | ANONYMOUS | player_a | fable | 33.3 | 120 |
| qwen | ANONYMOUS | player_b | qwen | 40.8 | 120 |
| qwen | ANONYMOUS | player_b | fable | 34.2 | 120 |
| fable | TRUE | player_a | qwen | 39.0 | 118 |
| fable | TRUE | player_a | fable | 43.2 | 118 |
| fable | TRUE | player_b | qwen | 37.8 | 119 |
| fable | TRUE | player_b | fable | 50.4 | 117 |
| fable | FALSE | player_a | qwen | 48.3 | 118 |
| fable | FALSE | player_a | fable | 37.3 | 118 |
| fable | FALSE | player_b | qwen | 48.7 | 119 |
| fable | FALSE | player_b | fable | 41.0 | 117 |
| fable | ANONYMOUS | player_a | qwen | 43.2 | 118 |
| fable | ANONYMOUS | player_a | fable | 34.7 | 118 |
| fable | ANONYMOUS | player_b | qwen | 46.2 | 119 |
| fable | ANONYMOUS | player_b | fable | 45.3 | 117 |

Early vs late rounds:

| judge | condition | rounds 1-10 | rounds 11-20 |
|---|---|---:|---:|
| qwen | TRUE | 34.2 | 41.7 |
| qwen | FALSE | 30.4 | 42.9 |
| qwen | ANONYMOUS | 31.2 | 42.1 |
| fable | TRUE | 40.8 | 44.4 |
| fable | FALSE | 41.6 | 46.2 |
| fable | ANONYMOUS | 39.1 | 45.7 |

## Players

| game | seat | model | % ROCK | % PAPER | % SCISSORS | % switch | wins | ties |
|---|---|---|---:|---:|---:|---:|---:|---:|
| GQQ1 | player_a | qwen | 30.0 | 30.0 | 40.0 | 57.9 | 5 | 7 |
| GQQ1 | player_b | qwen | 25.0 | 40.0 | 35.0 | 57.9 | 8 | 7 |
| GQF1 | player_a | qwen | 25.0 | 40.0 | 35.0 | 94.7 | 5 | 6 |
| GQF1 | player_b | fable | 45.0 | 25.0 | 30.0 | 84.2 | 9 | 6 |
| GFQ1 | player_a | fable | 45.0 | 30.0 | 25.0 | 68.4 | 7 | 6 |
| GFQ1 | player_b | qwen | 20.0 | 35.0 | 45.0 | 63.2 | 7 | 6 |
| GFF1 | player_a | fable | 30.0 | 35.0 | 35.0 | 73.7 | 8 | 8 |
| GFF1 | player_b | fable | 45.0 | 25.0 | 30.0 | 68.4 | 4 | 8 |
| GQQ2 | player_a | qwen | 25.0 | 50.0 | 25.0 | 63.2 | 6 | 7 |
| GQQ2 | player_b | qwen | 25.0 | 30.0 | 45.0 | 63.2 | 7 | 7 |
| GQF2 | player_a | qwen | 20.0 | 45.0 | 35.0 | 63.2 | 8 | 5 |
| GQF2 | player_b | fable | 30.0 | 30.0 | 40.0 | 84.2 | 7 | 5 |
| GFQ2 | player_a | fable | 35.0 | 20.0 | 45.0 | 84.2 | 8 | 5 |
| GFQ2 | player_b | qwen | 25.0 | 45.0 | 30.0 | 84.2 | 7 | 5 |
| GFF2 | player_a | fable | 25.0 | 45.0 | 30.0 | 68.4 | 6 | 10 |
| GFF2 | player_b | fable | 35.0 | 35.0 | 30.0 | 52.6 | 4 | 10 |
| GQQ3 | player_a | qwen | 35.0 | 30.0 | 35.0 | 63.2 | 9 | 6 |
| GQQ3 | player_b | qwen | 20.0 | 35.0 | 45.0 | 52.6 | 5 | 6 |
| GQF3 | player_a | qwen | 20.0 | 35.0 | 45.0 | 47.4 | 6 | 8 |
| GQF3 | player_b | fable | 35.0 | 35.0 | 30.0 | 68.4 | 6 | 8 |
| GFQ3 | player_a | fable | 20.0 | 35.0 | 45.0 | 73.7 | 10 | 6 |
| GFQ3 | player_b | qwen | 35.0 | 50.0 | 15.0 | 47.4 | 4 | 6 |
| GFF3 | player_a | fable | 30.0 | 45.0 | 25.0 | 94.7 | 4 | 5 |
| GFF3 | player_b | fable | 15.0 | 40.0 | 45.0 | 84.2 | 11 | 5 |

Player responses (protocol BlindTwinRPS_v1; player format line: "You may briefly think through your choice. End your response with the chosen move (ROCK, PAPER, or SCISSORS) alone on the final line."):

| model | responses | valid | median completion tokens | max completion tokens | % with reasoning before the shape |
|---|---:|---:|---:|---:|---:|
| qwen | 240 | 240 | 815 | 3462 | 96.7 |
| fable | 240 | 240 | 181 | 489 | 100.0 |

Replicate independence (first three rounds, player_a/player_b):

- qwen-qwen: openings ['PSP/PRP', 'PPS/PRS', 'PRP/PSP']; distinct openings 3/3; distinct full games 3/3
- qwen-fable: openings ['PRR/PRR', 'PRP/PSP', 'PRP/PSP']; distinct openings 2/3; distinct full games 3/3
- fable-qwen: openings ['PRP/PSR', 'PRS/PSP', 'PRP/PSR']; distinct openings 2/3; distinct full games 3/3
- fable-fable: openings ['PRP/PSP', 'PRR/PRR', 'PRS/PSP']; distinct openings 3/3; distinct full games 3/3

Per-game accuracy: `by_game.csv`; trajectories: `figures/trajectory_judge_<model>.png`, `figures/choices_by_game.png`.

## Limitations

- Two models, three games per matchup, 20 rounds: a feasibility pilot. Effects are described at game level; no confirmatory claim.
- 'Same model' means another independently queried instance, not memory of the actions. A truth benefit measures the functional value of identity information, not introspection or privileged access.
- Neither endpoint supports temperature control; both ran at provider-default sampling with low hidden reasoning (effort=low, excluded). Hidden reasoning content is unobserved.
- Players see the full public history afresh each round; there is no carried conversation state.
- Beating 33.3% by exploiting simple action biases is not self-knowledge; compare with the history-only baselines above.
- The dollar ceiling was set by Claude from Chris's standing $100 project cap and 'build and run it' instruction; see approvals.jsonl.

