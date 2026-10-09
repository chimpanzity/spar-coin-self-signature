# Blind Twin RPS pilot: morning report

Run `rps-qa-20261009T1124Z`. Protocol BlindTwinRPS_v1. Exploratory feasibility pilot, not confirmatory.

## Completion and cost

| matchup (player_a-player_b) | games complete / 3 | valid rounds |
|---|---:|---:|
| qwen-qwen | 3 | 60 / 60 |
| qwen-astra | 3 | 60 / 60 |
| astra-qwen | 3 | 60 / 60 |
| astra-astra | 3 | 60 / 60 |

- Player calls: 480 recorded, 480 valid choices.
- Judge calls: 1440 recorded, 1440 valid predictions (paired items valid in all three conditions: {'qwen': 480, 'astra': 480}).
- Charged cost: $7.34 scientific + $0.35 technical smoke = $7.69 (ceiling $25).
- Incomplete games: none.

## Accuracy table (percent correct, equal-weight over seat x opponent strata and games; 33.3% = random guess)

| judge | predicted player model | TRUE | FALSE | ANONYMOUS |
|---|---|---:|---:|---:|
| qwen | qwen (self) | 37.9 | 38.3 | 39.2 |
| qwen | astra | 35.4 | 38.8 | 36.7 |
| astra | qwen | 42.9 | 49.2 | 45.4 |
| astra | astra (self) | 59.2 | 52.1 | 52.9 |

## Identity indices (percentage points; game-level bootstrap within matchup, 5,000 resamples of 3 games per type)

| index | estimate | 95% interval |
|---|---:|---|
| **S: self-specific truth benefit (TRUE vs ANONYMOUS), primary** | +4.4 | [-2.3, +11.7] |
| S_false: self-specific false-label cost (TRUE vs FALSE), key companion | +8.1 | [+3.5, +13.1] |
| T[qwen,qwen] truth benefit | -1.2 | [-7.5, +4.2] |
| T[qwen,astra] truth benefit | -1.2 | [-10.4, +7.1] |
| T[astra,qwen] truth benefit | -2.5 | [-7.5, +2.1] |
| T[astra,astra] truth benefit | +6.2 | [+2.9, +10.4] |
| F[qwen,qwen] false-label cost | -0.4 | [-5.4, +4.6] |
| F[qwen,astra] false-label cost | -3.3 | [-9.6, +2.5] |
| F[astra,qwen] false-label cost | -6.2 | [-10.0, -2.5] |
| F[astra,astra] false-label cost | +7.1 | [+5.0, +10.0] |

With 3 games per matchup these intervals describe game-to-game variation only; rounds within a game are not independent subjects.

## Label responsiveness (percent of paired items whose hard prediction differs)

| judge | seat | comparison | n | % differ |
|---|---|---|---:|---:|
| qwen | player_a | TRUE vs FALSE | 240 | 31.7 |
| qwen | player_a | TRUE vs ANONYMOUS | 240 | 32.9 |
| qwen | player_a | FALSE vs ANONYMOUS | 240 | 32.5 |
| qwen | player_b | TRUE vs FALSE | 240 | 33.8 |
| qwen | player_b | TRUE vs ANONYMOUS | 240 | 37.1 |
| qwen | player_b | FALSE vs ANONYMOUS | 240 | 38.8 |
| astra | player_a | TRUE vs FALSE | 240 | 19.2 |
| astra | player_a | TRUE vs ANONYMOUS | 240 | 16.7 |
| astra | player_a | FALSE vs ANONYMOUS | 240 | 15.0 |
| astra | player_b | TRUE vs FALSE | 240 | 21.7 |
| astra | player_b | TRUE vs ANONYMOUS | 240 | 20.0 |
| astra | player_b | FALSE vs ANONYMOUS | 240 | 17.5 |

## Simple history-only baselines (percent correct; round 1 and tied predictions get fractional credit; chance 33.3%)

| baseline | all valid rounds | on qwen judge items | on astra judge items |
|---|---:|---:|---:|
| frequency | 30.2 | 30.2 | 30.2 |
| repeat_last | 35.6 | 35.6 | 35.6 |
| cycle_up | 27.7 | 27.7 | 27.7 |
| cycle_down | 36.7 | 36.7 | 36.7 |
| counter_opponent_last | 47.9 | 47.9 | 47.9 |
| win_stay_lose_shift | 47.9 | 47.9 | 47.9 |
| markov1 | 33.5 | 33.5 | 33.5 |

Both-seats-correct rate (descriptive only): qwen/TRUE 14.6% of 240; qwen/FALSE 14.2% of 240; qwen/ANONYMOUS 13.8% of 240; astra/TRUE 25.4% of 240; astra/FALSE 26.2% of 240; astra/ANONYMOUS 24.2% of 240

## Per-judge, role-specific breakdown (all rounds, paired items)

| judge | condition | seat | player model | % correct | n |
|---|---|---|---|---:|---:|
| qwen | TRUE | player_a | qwen | 35.8 | 120 |
| qwen | TRUE | player_a | astra | 37.5 | 120 |
| qwen | TRUE | player_b | qwen | 40.0 | 120 |
| qwen | TRUE | player_b | astra | 33.3 | 120 |
| qwen | FALSE | player_a | qwen | 33.3 | 120 |
| qwen | FALSE | player_a | astra | 42.5 | 120 |
| qwen | FALSE | player_b | qwen | 43.3 | 120 |
| qwen | FALSE | player_b | astra | 35.0 | 120 |
| qwen | ANONYMOUS | player_a | qwen | 38.3 | 120 |
| qwen | ANONYMOUS | player_a | astra | 35.8 | 120 |
| qwen | ANONYMOUS | player_b | qwen | 40.0 | 120 |
| qwen | ANONYMOUS | player_b | astra | 37.5 | 120 |
| astra | TRUE | player_a | qwen | 45.0 | 120 |
| astra | TRUE | player_a | astra | 54.2 | 120 |
| astra | TRUE | player_b | qwen | 40.8 | 120 |
| astra | TRUE | player_b | astra | 64.2 | 120 |
| astra | FALSE | player_a | qwen | 50.8 | 120 |
| astra | FALSE | player_a | astra | 51.7 | 120 |
| astra | FALSE | player_b | qwen | 47.5 | 120 |
| astra | FALSE | player_b | astra | 52.5 | 120 |
| astra | ANONYMOUS | player_a | qwen | 48.3 | 120 |
| astra | ANONYMOUS | player_a | astra | 52.5 | 120 |
| astra | ANONYMOUS | player_b | qwen | 42.5 | 120 |
| astra | ANONYMOUS | player_b | astra | 53.3 | 120 |

Early vs late rounds:

| judge | condition | rounds 1-10 | rounds 11-20 |
|---|---|---:|---:|
| qwen | TRUE | 34.2 | 39.2 |
| qwen | FALSE | 35.8 | 41.2 |
| qwen | ANONYMOUS | 35.0 | 40.8 |
| astra | TRUE | 50.0 | 52.1 |
| astra | FALSE | 47.5 | 53.8 |
| astra | ANONYMOUS | 45.8 | 52.5 |

## Players

| game | seat | model | % ROCK | % PAPER | % SCISSORS | % switch | wins | ties |
|---|---|---|---:|---:|---:|---:|---:|---:|
| GQQ1 | player_a | qwen | 45.0 | 35.0 | 20.0 | 73.7 | 7 | 8 |
| GQQ1 | player_b | qwen | 15.0 | 45.0 | 40.0 | 57.9 | 5 | 8 |
| GQA1 | player_a | qwen | 35.0 | 15.0 | 50.0 | 42.1 | 6 | 5 |
| GQA1 | player_b | astra | 35.0 | 45.0 | 20.0 | 63.2 | 9 | 5 |
| GAQ1 | player_a | astra | 35.0 | 40.0 | 25.0 | 68.4 | 3 | 8 |
| GAQ1 | player_b | qwen | 35.0 | 25.0 | 40.0 | 57.9 | 9 | 8 |
| GAA1 | player_a | astra | 30.0 | 20.0 | 50.0 | 73.7 | 5 | 10 |
| GAA1 | player_b | astra | 35.0 | 40.0 | 25.0 | 78.9 | 5 | 10 |
| GQQ2 | player_a | qwen | 45.0 | 30.0 | 25.0 | 57.9 | 7 | 6 |
| GQQ2 | player_b | qwen | 25.0 | 25.0 | 50.0 | 42.1 | 7 | 6 |
| GQA2 | player_a | qwen | 45.0 | 30.0 | 25.0 | 78.9 | 3 | 11 |
| GQA2 | player_b | astra | 25.0 | 40.0 | 35.0 | 78.9 | 6 | 11 |
| GAQ2 | player_a | astra | 25.0 | 40.0 | 35.0 | 63.2 | 7 | 8 |
| GAQ2 | player_b | qwen | 35.0 | 30.0 | 35.0 | 63.2 | 5 | 8 |
| GAA2 | player_a | astra | 25.0 | 50.0 | 25.0 | 68.4 | 4 | 12 |
| GAA2 | player_b | astra | 45.0 | 25.0 | 30.0 | 73.7 | 4 | 12 |
| GQQ3 | player_a | qwen | 45.0 | 35.0 | 20.0 | 57.9 | 6 | 7 |
| GQQ3 | player_b | qwen | 25.0 | 40.0 | 35.0 | 63.2 | 7 | 7 |
| GQA3 | player_a | qwen | 30.0 | 40.0 | 30.0 | 73.7 | 8 | 5 |
| GQA3 | player_b | astra | 30.0 | 30.0 | 40.0 | 63.2 | 7 | 5 |
| GAQ3 | player_a | astra | 35.0 | 50.0 | 15.0 | 57.9 | 8 | 4 |
| GAQ3 | player_b | qwen | 20.0 | 35.0 | 45.0 | 63.2 | 8 | 4 |
| GAA3 | player_a | astra | 40.0 | 35.0 | 25.0 | 63.2 | 8 | 3 |
| GAA3 | player_b | astra | 25.0 | 30.0 | 45.0 | 57.9 | 9 | 3 |

Player responses (protocol BlindTwinRPS_v1; player format line: "You may briefly think through your choice. End your response with the chosen move (ROCK, PAPER, or SCISSORS) alone on the final line."):

| model | responses | valid | median completion tokens | max completion tokens | % with reasoning before the shape |
|---|---:|---:|---:|---:|---:|
| qwen | 240 | 240 | 686 | 2824 | 98.3 |
| astra | 240 | 240 | 32 | 201 | 3.3 |

Replicate independence (first three rounds, player_a/player_b):

- qwen-qwen: openings ['PSP/PSP', 'PSP/PRP', 'PSP/PSP']; distinct openings 2/3; distinct full games 3/3
- qwen-astra: openings ['PSR/PSP', 'PSR/PSR', 'RSP/PSR']; distinct openings 3/3; distinct full games 3/3
- astra-qwen: openings ['PSR/PSP', 'PSP/PSP', 'PSP/PRP']; distinct openings 3/3; distinct full games 3/3
- astra-astra: openings ['PSP/PSP', 'PSP/PSP', 'PSP/PSR']; distinct openings 2/3; distinct full games 3/3

Per-game accuracy: `by_game.csv`; trajectories: `figures/trajectory_judge_<model>.png`, `figures/choices_by_game.png`.

## Limitations

- Two models, three games per matchup, 20 rounds: a feasibility pilot. Effects are described at game level; no confirmatory claim.
- 'Same model' means another independently queried instance, not memory of the actions. A truth benefit measures the functional value of identity information, not introspection or privileged access.
- Neither endpoint supports temperature control; both ran at provider-default sampling with low hidden reasoning (effort=low, excluded). Hidden reasoning content is unobserved.
- Players see the full public history afresh each round; there is no carried conversation state.
- Beating 33.3% by exploiting simple action biases is not self-knowledge; compare with the history-only baselines above.
- The dollar ceiling was set by Claude from Chris's standing $100 project cap and 'build and run it' instruction; see approvals.jsonl.

