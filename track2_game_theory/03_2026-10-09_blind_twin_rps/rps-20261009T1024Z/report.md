# Blind Twin RPS pilot: morning report

Run `rps-20261009T1024Z`. Protocol BlindTwinRPS_v1. Exploratory feasibility pilot, not confirmatory.

## Completion and cost

| matchup (player_a-player_b) | games complete / 3 | valid rounds |
|---|---:|---:|
| astra-astra | 3 | 60 / 60 |
| astra-fable | 3 | 60 / 60 |
| fable-astra | 3 | 60 / 60 |
| fable-fable | 3 | 60 / 60 |

- Player calls: 480 recorded, 480 valid choices.
- Judge calls: 1440 recorded, 1440 valid predictions (paired items valid in all three conditions: {'astra': 480, 'fable': 480}).
- Charged cost: $14.61 scientific + $1.03 technical smoke = $15.64 (ceiling $25).
- Incomplete games: none.

## Accuracy table (percent correct, equal-weight over seat x opponent strata and games; 33.3% = random guess)

| judge | predicted player model | TRUE | FALSE | ANONYMOUS |
|---|---|---:|---:|---:|
| astra | astra (self) | 44.6 | 42.9 | 42.1 |
| astra | fable | 44.6 | 42.9 | 40.0 |
| fable | astra | 45.8 | 42.9 | 38.3 |
| fable | fable (self) | 47.1 | 42.9 | 42.9 |

## Identity indices (percentage points; game-level bootstrap within matchup, 5,000 resamples of 3 games per type)

| index | estimate | 95% interval |
|---|---:|---|
| **S: self-specific truth benefit (TRUE vs ANONYMOUS), primary** | -2.7 | [-4.6, -0.8] |
| S_false: self-specific false-label cost (TRUE vs FALSE), key companion | +0.6 | [-3.1, +4.0] |
| T[astra,astra] truth benefit | +2.5 | [-1.7, +6.7] |
| T[astra,fable] truth benefit | +4.6 | [+1.7, +7.5] |
| T[fable,astra] truth benefit | +7.5 | [+5.0, +10.0] |
| T[fable,fable] truth benefit | +4.2 | [+1.2, +7.5] |
| F[astra,astra] false-label cost | +1.7 | [-2.9, +6.7] |
| F[astra,fable] false-label cost | +1.7 | [-1.2, +5.0] |
| F[fable,astra] false-label cost | +2.9 | [+0.4, +5.0] |
| F[fable,fable] false-label cost | +4.2 | [+0.4, +7.9] |

With 3 games per matchup these intervals describe game-to-game variation only; rounds within a game are not independent subjects.

## Label responsiveness (percent of paired items whose hard prediction differs)

| judge | seat | comparison | n | % differ |
|---|---|---|---:|---:|
| astra | player_a | TRUE vs FALSE | 240 | 21.2 |
| astra | player_a | TRUE vs ANONYMOUS | 240 | 21.7 |
| astra | player_a | FALSE vs ANONYMOUS | 240 | 15.8 |
| astra | player_b | TRUE vs FALSE | 240 | 24.6 |
| astra | player_b | TRUE vs ANONYMOUS | 240 | 21.7 |
| astra | player_b | FALSE vs ANONYMOUS | 240 | 24.6 |
| fable | player_a | TRUE vs FALSE | 240 | 15.4 |
| fable | player_a | TRUE vs ANONYMOUS | 240 | 24.2 |
| fable | player_a | FALSE vs ANONYMOUS | 240 | 22.9 |
| fable | player_b | TRUE vs FALSE | 240 | 27.1 |
| fable | player_b | TRUE vs ANONYMOUS | 240 | 27.9 |
| fable | player_b | FALSE vs ANONYMOUS | 240 | 30.0 |

## Simple history-only baselines (percent correct; round 1 and tied predictions get fractional credit; chance 33.3%)

| baseline | all valid rounds | on Astra judge items | on Fable judge items |
|---|---:|---:|---:|
| frequency | 28.8 | 28.8 | 28.8 |
| repeat_last | 32.7 | 32.7 | 32.7 |
| cycle_up | 28.5 | 28.5 | 28.5 |
| cycle_down | 38.8 | 38.8 | 38.8 |
| counter_opponent_last | 43.1 | 43.1 | 43.1 |
| win_stay_lose_shift | 43.1 | 43.1 | 43.1 |
| markov1 | 28.0 | 28.0 | 28.0 |

Both-seats-correct rate (descriptive only): astra/TRUE 22.5% of 240; astra/FALSE 19.6% of 240; astra/ANONYMOUS 18.3% of 240; fable/TRUE 22.9% of 240; fable/FALSE 21.7% of 240; fable/ANONYMOUS 17.1% of 240

## Per-judge, role-specific breakdown (all rounds, paired items)

| judge | condition | seat | player model | % correct | n |
|---|---|---|---|---:|---:|
| astra | TRUE | player_a | astra | 46.7 | 120 |
| astra | TRUE | player_a | fable | 45.0 | 120 |
| astra | TRUE | player_b | astra | 42.5 | 120 |
| astra | TRUE | player_b | fable | 44.2 | 120 |
| astra | FALSE | player_a | astra | 45.8 | 120 |
| astra | FALSE | player_a | fable | 45.8 | 120 |
| astra | FALSE | player_b | astra | 40.0 | 120 |
| astra | FALSE | player_b | fable | 40.0 | 120 |
| astra | ANONYMOUS | player_a | astra | 42.5 | 120 |
| astra | ANONYMOUS | player_a | fable | 45.8 | 120 |
| astra | ANONYMOUS | player_b | astra | 41.7 | 120 |
| astra | ANONYMOUS | player_b | fable | 34.2 | 120 |
| fable | TRUE | player_a | astra | 46.7 | 120 |
| fable | TRUE | player_a | fable | 49.2 | 120 |
| fable | TRUE | player_b | astra | 45.0 | 120 |
| fable | TRUE | player_b | fable | 45.0 | 120 |
| fable | FALSE | player_a | astra | 44.2 | 120 |
| fable | FALSE | player_a | fable | 41.7 | 120 |
| fable | FALSE | player_b | astra | 41.7 | 120 |
| fable | FALSE | player_b | fable | 44.2 | 120 |
| fable | ANONYMOUS | player_a | astra | 33.3 | 120 |
| fable | ANONYMOUS | player_a | fable | 43.3 | 120 |
| fable | ANONYMOUS | player_b | astra | 43.3 | 120 |
| fable | ANONYMOUS | player_b | fable | 42.5 | 120 |

Early vs late rounds:

| judge | condition | rounds 1-10 | rounds 11-20 |
|---|---|---:|---:|
| astra | TRUE | 46.2 | 42.9 |
| astra | FALSE | 43.3 | 42.5 |
| astra | ANONYMOUS | 40.0 | 42.1 |
| fable | TRUE | 50.8 | 42.1 |
| fable | FALSE | 45.4 | 40.4 |
| fable | ANONYMOUS | 38.8 | 42.5 |

## Players

| game | seat | model | % ROCK | % PAPER | % SCISSORS | % switch | wins | ties |
|---|---|---|---:|---:|---:|---:|---:|---:|
| GAA1 | player_a | astra | 30.0 | 25.0 | 45.0 | 63.2 | 7 | 8 |
| GAA1 | player_b | astra | 35.0 | 40.0 | 25.0 | 52.6 | 5 | 8 |
| GAF1 | player_a | astra | 20.0 | 40.0 | 40.0 | 73.7 | 6 | 8 |
| GAF1 | player_b | fable | 45.0 | 20.0 | 35.0 | 63.2 | 6 | 8 |
| GFA1 | player_a | fable | 20.0 | 50.0 | 30.0 | 73.7 | 9 | 4 |
| GFA1 | player_b | astra | 40.0 | 35.0 | 25.0 | 63.2 | 7 | 4 |
| GFF1 | player_a | fable | 45.0 | 35.0 | 20.0 | 73.7 | 6 | 8 |
| GFF1 | player_b | fable | 25.0 | 30.0 | 45.0 | 73.7 | 6 | 8 |
| GAA2 | player_a | astra | 35.0 | 35.0 | 30.0 | 68.4 | 7 | 9 |
| GAA2 | player_b | astra | 30.0 | 30.0 | 40.0 | 78.9 | 4 | 9 |
| GAF2 | player_a | astra | 20.0 | 50.0 | 30.0 | 63.2 | 9 | 1 |
| GAF2 | player_b | fable | 45.0 | 25.0 | 30.0 | 68.4 | 10 | 1 |
| GFA2 | player_a | fable | 35.0 | 25.0 | 40.0 | 73.7 | 5 | 11 |
| GFA2 | player_b | astra | 20.0 | 45.0 | 35.0 | 57.9 | 4 | 11 |
| GFF2 | player_a | fable | 35.0 | 40.0 | 25.0 | 63.2 | 3 | 8 |
| GFF2 | player_b | fable | 35.0 | 40.0 | 25.0 | 73.7 | 9 | 8 |
| GAA3 | player_a | astra | 30.0 | 30.0 | 40.0 | 84.2 | 6 | 9 |
| GAA3 | player_b | astra | 25.0 | 30.0 | 45.0 | 73.7 | 5 | 9 |
| GAF3 | player_a | astra | 40.0 | 25.0 | 35.0 | 68.4 | 1 | 16 |
| GAF3 | player_b | fable | 30.0 | 35.0 | 35.0 | 57.9 | 3 | 16 |
| GFA3 | player_a | fable | 25.0 | 35.0 | 40.0 | 63.2 | 11 | 4 |
| GFA3 | player_b | astra | 40.0 | 35.0 | 25.0 | 47.4 | 5 | 4 |
| GFF3 | player_a | fable | 20.0 | 45.0 | 35.0 | 68.4 | 7 | 8 |
| GFF3 | player_b | fable | 35.0 | 25.0 | 40.0 | 68.4 | 5 | 8 |

Player responses (protocol BlindTwinRPS_v1; player format line: "You may briefly think through your choice. End your response with the chosen move (ROCK, PAPER, or SCISSORS) alone on the final line."):

| model | responses | valid | median completion tokens | max completion tokens | % with reasoning before the shape |
|---|---:|---:|---:|---:|---:|
| astra | 240 | 240 | 34 | 158 | 1.2 |
| fable | 240 | 240 | 183 | 712 | 100.0 |

Replicate independence (first three rounds, player_a/player_b):

- astra-astra: openings ['PSP/PSP', 'PSP/PSP', 'PSP/PSP']; distinct openings 1/3; distinct full games 3/3
- astra-fable: openings ['PSR/PSP', 'PSS/PRP', 'PSP/PSP']; distinct openings 3/3; distinct full games 3/3
- fable-astra: openings ['PRP/PSR', 'PRP/PSP', 'PRP/PSR']; distinct openings 2/3; distinct full games 3/3
- fable-fable: openings ['PRR/PRR', 'PRR/PRR', 'PRS/PSP']; distinct openings 2/3; distinct full games 3/3

Per-game accuracy: `by_game.csv`; trajectories: `figures/trajectory_judge_astra.png`, `figures/trajectory_judge_fable.png`, `figures/choices_by_game.png`.

## Limitations

- Two models, three games per matchup, 20 rounds: a feasibility pilot. Effects are described at game level; no confirmatory claim.
- 'Same model' means another independently queried instance, not memory of the actions. A truth benefit measures the functional value of identity information, not introspection or privileged access.
- Neither endpoint supports temperature control; both ran at provider-default sampling with low hidden reasoning (effort=low, excluded). Hidden reasoning content is unobserved.
- Players see the full public history afresh each round; there is no carried conversation state.
- Beating 33.3% by exploiting simple action biases is not self-knowledge; compare with the history-only baselines above.
- The dollar ceiling was set by Claude from Chris's standing $100 project cap and 'build and run it' instruction; see approvals.jsonl.

