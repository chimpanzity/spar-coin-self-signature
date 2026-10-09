# Blind Twin pilot: morning report

Run `bt2-20261009T0957Z`. Protocol BlindTwin_v2. Exploratory feasibility pilot, not confirmatory.

## Completion and cost

| matchup (matcher-mismatcher) | games complete / 3 | valid rounds |
|---|---:|---:|
| astra-astra | 3 | 60 / 60 |
| astra-fable | 3 | 60 / 60 |
| fable-astra | 3 | 60 / 60 |
| fable-fable | 3 | 60 / 60 |

- Player calls: 480 recorded, 480 valid choices.
- Judge calls: 1440 recorded, 1439 valid predictions (paired items valid in all three conditions: {'astra': 480, 'fable': 478}).
- Charged cost: $14.27 scientific + $0.90 technical smoke = $15.17 (ceiling $25).
- Incomplete games: none.

## Accuracy table (percent correct, equal-weight over seat x opponent strata and games; 50% = fair guess)

| judge | predicted player model | TRUE | FALSE | ANONYMOUS |
|---|---|---:|---:|---:|
| astra | astra (self) | 60.0 | 58.8 | 56.7 |
| astra | fable | 59.2 | 62.1 | 58.8 |
| fable | astra | 55.7 | 57.0 | 57.7 |
| fable | fable (self) | 62.8 | 59.5 | 59.5 |

## Identity indices (percentage points; game-level bootstrap within matchup, 5,000 resamples of 3 games per type)

| index | estimate | 95% interval |
|---|---:|---|
| **S: self-specific truth benefit (TRUE vs ANONYMOUS), primary** | +4.2 | [+0.4, +8.5] |
| S_false: self-specific false-label cost (TRUE vs FALSE), key companion | +4.4 | [+1.7, +7.1] |
| T[astra,astra] truth benefit | +3.3 | [-1.3, +8.8] |
| T[astra,fable] truth benefit | +0.4 | [-2.9, +3.8] |
| T[fable,astra] truth benefit | -2.1 | [-6.2, +2.1] |
| T[fable,fable] truth benefit | +3.3 | [+1.2, +5.4] |
| F[astra,astra] false-label cost | +1.2 | [-2.1, +4.2] |
| F[astra,fable] false-label cost | -2.9 | [-5.0, -0.4] |
| F[fable,astra] false-label cost | -1.3 | [-3.0, +0.8] |
| F[fable,fable] false-label cost | +3.3 | [+0.4, +6.7] |

With 3 games per matchup these intervals describe game-to-game variation only; rounds within a game are not independent subjects.

## Label responsiveness (percent of paired items whose hard prediction differs)

| judge | seat | comparison | n | % differ |
|---|---|---|---:|---:|
| astra | matcher | TRUE vs FALSE | 240 | 10.4 |
| astra | matcher | TRUE vs ANONYMOUS | 240 | 12.1 |
| astra | matcher | FALSE vs ANONYMOUS | 240 | 8.3 |
| astra | mismatcher | TRUE vs FALSE | 240 | 12.9 |
| astra | mismatcher | TRUE vs ANONYMOUS | 240 | 14.2 |
| astra | mismatcher | FALSE vs ANONYMOUS | 240 | 13.8 |
| fable | matcher | TRUE vs FALSE | 240 | 5.0 |
| fable | matcher | TRUE vs ANONYMOUS | 239 | 9.6 |
| fable | matcher | FALSE vs ANONYMOUS | 239 | 7.9 |
| fable | mismatcher | TRUE vs FALSE | 240 | 22.1 |
| fable | mismatcher | TRUE vs ANONYMOUS | 239 | 27.6 |
| fable | mismatcher | FALSE vs ANONYMOUS | 239 | 26.4 |

## Simple history-only baselines (percent correct; round 1 and ties get half credit)

| baseline | all valid rounds | on Astra judge items | on Fable judge items |
|---|---:|---:|---:|
| frequency | 45.2 | 45.2 | 45.0 |
| repeat_last | 46.9 | 46.9 | 46.7 |
| alternate_last | 53.1 | 53.1 | 53.3 |
| win_stay_lose_shift | 41.5 | 41.5 | 41.4 |
| markov1 | 48.4 | 48.4 | 48.6 |

Both-seats-correct rate (descriptive only): astra/TRUE 33.8% of 240; astra/FALSE 35.4% of 240; astra/ANONYMOUS 29.2% of 240; fable/TRUE 34.7% of 239; fable/FALSE 34.7% of 239; fable/ANONYMOUS 33.1% of 239

## Per-judge, role-specific breakdown (all rounds, paired items)

| judge | condition | seat | player model | % correct | n |
|---|---|---|---|---:|---:|
| astra | TRUE | matcher | astra | 55.0 | 120 |
| astra | TRUE | matcher | fable | 59.2 | 120 |
| astra | TRUE | mismatcher | astra | 65.0 | 120 |
| astra | TRUE | mismatcher | fable | 59.2 | 120 |
| astra | FALSE | matcher | astra | 54.2 | 120 |
| astra | FALSE | matcher | fable | 60.8 | 120 |
| astra | FALSE | mismatcher | astra | 63.3 | 120 |
| astra | FALSE | mismatcher | fable | 63.3 | 120 |
| astra | ANONYMOUS | matcher | astra | 50.0 | 120 |
| astra | ANONYMOUS | matcher | fable | 58.3 | 120 |
| astra | ANONYMOUS | mismatcher | astra | 63.3 | 120 |
| astra | ANONYMOUS | mismatcher | fable | 59.2 | 120 |
| fable | TRUE | matcher | astra | 58.3 | 120 |
| fable | TRUE | matcher | fable | 63.9 | 119 |
| fable | TRUE | mismatcher | astra | 52.9 | 119 |
| fable | TRUE | mismatcher | fable | 61.7 | 120 |
| fable | FALSE | matcher | astra | 55.8 | 120 |
| fable | FALSE | matcher | fable | 61.3 | 119 |
| fable | FALSE | mismatcher | astra | 58.0 | 119 |
| fable | FALSE | mismatcher | fable | 57.5 | 120 |
| fable | ANONYMOUS | matcher | astra | 59.2 | 120 |
| fable | ANONYMOUS | matcher | fable | 60.5 | 119 |
| fable | ANONYMOUS | mismatcher | astra | 56.3 | 119 |
| fable | ANONYMOUS | mismatcher | fable | 58.3 | 120 |

Early vs late rounds:

| judge | condition | rounds 1-10 | rounds 11-20 |
|---|---|---:|---:|
| astra | TRUE | 62.1 | 57.1 |
| astra | FALSE | 65.8 | 55.0 |
| astra | ANONYMOUS | 63.3 | 52.1 |
| fable | TRUE | 62.9 | 55.5 |
| fable | FALSE | 62.1 | 54.2 |
| fable | ANONYMOUS | 60.4 | 56.7 |

## Players

| game | seat | model | % STAR | % switch | matcher wins /20 |
|---|---|---|---:|---:|---:|
| GAA1 | matcher | astra | 40.0 | 52.6 | 9 |
| GAA1 | mismatcher | astra | 65.0 | 47.4 |  |
| GAF1 | matcher | astra | 50.0 | 47.4 | 10 |
| GAF1 | mismatcher | fable | 40.0 | 47.4 |  |
| GFA1 | matcher | fable | 60.0 | 42.1 | 11 |
| GFA1 | mismatcher | astra | 55.0 | 42.1 |  |
| GFF1 | matcher | fable | 55.0 | 57.9 | 12 |
| GFF1 | mismatcher | fable | 45.0 | 63.2 |  |
| GAA2 | matcher | astra | 45.0 | 47.4 | 10 |
| GAA2 | mismatcher | astra | 55.0 | 36.8 |  |
| GAF2 | matcher | astra | 60.0 | 47.4 | 9 |
| GAF2 | mismatcher | fable | 45.0 | 47.4 |  |
| GFA2 | matcher | fable | 35.0 | 57.9 | 10 |
| GFA2 | mismatcher | astra | 45.0 | 63.2 |  |
| GFF2 | matcher | fable | 35.0 | 52.6 | 10 |
| GFF2 | mismatcher | fable | 55.0 | 57.9 |  |
| GAA3 | matcher | astra | 55.0 | 52.6 | 11 |
| GAA3 | mismatcher | astra | 60.0 | 63.2 |  |
| GAF3 | matcher | astra | 50.0 | 52.6 | 7 |
| GAF3 | mismatcher | fable | 55.0 | 57.9 |  |
| GFA3 | matcher | fable | 40.0 | 73.7 | 7 |
| GFA3 | mismatcher | astra | 55.0 | 47.4 |  |
| GFF3 | matcher | fable | 35.0 | 52.6 | 11 |
| GFF3 | mismatcher | fable | 50.0 | 68.4 |  |

Player responses (protocol BlindTwin_v2; player format line: "You may briefly think through your choice. End your response with the chosen shape (STAR or TRIANGLE) alone on the final line."):

| model | responses | valid | median completion tokens | max completion tokens | % with reasoning before the shape |
|---|---:|---:|---:|---:|---:|
| astra | 240 | 240 | 28 | 257 | 0.8 |
| fable | 240 | 240 | 159 | 531 | 100.0 |

Replicate independence (first three rounds, matcher/mismatcher):

- astra-astra: openings ['STT/TTS', 'STS/TST', 'STT/TST']; distinct openings 3/3; distinct full games 3/3
- astra-fable: openings ['STT/TST', 'STT/TST', 'STS/TST']; distinct openings 2/3; distinct full games 3/3
- fable-astra: openings ['STS/TTS', 'STT/TST', 'STS/TTT']; distinct openings 3/3; distinct full games 3/3
- fable-fable: openings ['STT/TST', 'STT/TST', 'SST/TST']; distinct openings 2/3; distinct full games 3/3

Per-game accuracy: `by_game.csv`; trajectories: `figures/trajectory_judge_astra.png`, `figures/trajectory_judge_fable.png`, `figures/choices_by_game.png`.

## Limitations

- Two models, three games per matchup, 20 rounds: a feasibility pilot. Effects are described at game level; no confirmatory claim.
- 'Same model' means another independently queried instance, not memory of the actions. A truth benefit measures the functional value of identity information, not introspection or privileged access.
- Neither endpoint supports temperature control; both ran at provider-default sampling with low hidden reasoning (effort=low, excluded). Hidden reasoning content is unobserved.
- Players see the full public history afresh each round; there is no carried conversation state.
- Beating 50% by exploiting simple action biases is not self-knowledge; compare with the history-only baselines above.
- The dollar ceiling was set by Claude from Chris's standing $100 project cap and 'build and run it' instruction; see approvals.jsonl.

