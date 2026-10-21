# Blind Twin pilot: morning report

Run `bt-20261009T0455Z`. Protocol BlindTwin_v1. Exploratory feasibility pilot, not confirmatory.

## Completion and cost

| matchup (matcher-mismatcher) | games complete / 3 | valid rounds |
|---|---:|---:|
| astra-astra | 3 | 60 / 60 |
| astra-fable | 0 | 18 / 60 |
| fable-astra | 0 | 9 / 60 |
| fable-fable | 0 | 16 / 60 |

- Player calls: 224 recorded, 214 valid choices.
- Judge calls: 618 recorded, 618 valid predictions (paired items valid in all three conditions: {'astra': 206, 'fable': 206}).
- Charged cost: $4.60 scientific + $0.01 technical smoke = $4.62 (ceiling $25).
- Incomplete games: GAF1 (invalid round 7: {'mismatcher': 'not_a_single_shape'}), GFA1 (invalid round 4: {'matcher': 'not_a_single_shape'}), GFF1 (invalid round 7: {'matcher': 'not_a_single_shape'}), GAF2 (invalid round 5: {'mismatcher': 'not_a_single_shape'}), GFA2 (invalid round 4: {'matcher': 'not_a_single_shape'}), GFF2 (invalid round 5: {'mismatcher': 'not_a_single_shape'}), GAF3 (invalid round 9: {'mismatcher': 'not_a_single_shape'}), GFA3 (invalid round 4: {'matcher': 'not_a_single_shape'}), GFF3 (invalid round 7: {'mismatcher': 'not_a_single_shape', 'matcher': 'not_a_single_shape'}).

## Accuracy table (percent correct, equal-weight over seat x opponent strata and games; 50% = fair guess)

| judge | predicted player model | TRUE | FALSE | ANONYMOUS |
|---|---|---:|---:|---:|
| astra | astra (self) | 63.7 | 69.2 | 67.8 |
| astra | fable | 62.5 | 62.8 | 65.6 |
| fable | astra | 61.4 | 70.8 | 58.3 |
| fable | fable (self) | 71.2 | 68.4 | 71.5 |

## Identity indices (percentage points; game-level bootstrap within matchup, 5,000 resamples of 3 games per type)

| index | estimate | 95% interval |
|---|---:|---|
| **S: self-specific truth benefit (TRUE vs ANONYMOUS), primary** | -2.2 | [-8.5, +3.5] |
| S_false: self-specific false-label cost (TRUE vs FALSE), key companion | +3.5 | [-3.1, +9.4] |
| T[astra,astra] truth benefit | -4.0 | [-9.6, +0.0] |
| T[astra,fable] truth benefit | -3.1 | [-8.7, +1.7] |
| T[fable,astra] truth benefit | +3.1 | [-4.6, +12.9] |
| T[fable,fable] truth benefit | -0.3 | [-8.3, +5.9] |
| F[astra,astra] false-label cost | -5.5 | [-11.0, -1.7] |
| F[astra,fable] false-label cost | -0.3 | [-6.2, +4.9] |
| F[fable,astra] false-label cost | -9.4 | [-17.5, +0.0] |
| F[fable,fable] false-label cost | +2.8 | [-5.6, +12.5] |

With 3 games per matchup these intervals describe game-to-game variation only; rounds within a game are not independent subjects.

## Label responsiveness (percent of paired items whose hard prediction differs)

| judge | seat | comparison | n | % differ |
|---|---|---|---:|---:|
| astra | matcher | TRUE vs FALSE | 103 | 7.8 |
| astra | matcher | TRUE vs ANONYMOUS | 103 | 6.8 |
| astra | matcher | FALSE vs ANONYMOUS | 103 | 10.7 |
| astra | mismatcher | TRUE vs FALSE | 103 | 12.6 |
| astra | mismatcher | TRUE vs ANONYMOUS | 103 | 11.7 |
| astra | mismatcher | FALSE vs ANONYMOUS | 103 | 10.7 |
| fable | matcher | TRUE vs FALSE | 103 | 4.9 |
| fable | matcher | TRUE vs ANONYMOUS | 103 | 6.8 |
| fable | matcher | FALSE vs ANONYMOUS | 103 | 7.8 |
| fable | mismatcher | TRUE vs FALSE | 103 | 25.2 |
| fable | mismatcher | TRUE vs ANONYMOUS | 103 | 30.1 |
| fable | mismatcher | FALSE vs ANONYMOUS | 103 | 26.2 |

## Simple history-only baselines (percent correct; round 1 and ties get half credit)

| baseline | all valid rounds | on Astra judge items | on Fable judge items |
|---|---:|---:|---:|
| frequency | 43.7 | 43.7 | 43.7 |
| repeat_last | 46.1 | 46.1 | 46.1 |
| alternate_last | 53.9 | 53.9 | 53.9 |
| win_stay_lose_shift | 53.4 | 53.4 | 53.4 |
| markov1 | 46.4 | 46.4 | 46.4 |

Both-seats-correct rate (descriptive only): astra/TRUE 29.1% of 103; astra/FALSE 36.9% of 103; astra/ANONYMOUS 31.1% of 103; fable/TRUE 33.0% of 103; fable/FALSE 35.9% of 103; fable/ANONYMOUS 36.9% of 103

## Per-judge, role-specific breakdown (all rounds, paired items)

| judge | condition | seat | player model | % correct | n |
|---|---|---|---|---:|---:|
| astra | TRUE | matcher | astra | 62.8 | 78 |
| astra | TRUE | matcher | fable | 72.0 | 25 |
| astra | TRUE | mismatcher | astra | 56.5 | 69 |
| astra | TRUE | mismatcher | fable | 47.1 | 34 |
| astra | FALSE | matcher | astra | 66.7 | 78 |
| astra | FALSE | matcher | fable | 76.0 | 25 |
| astra | FALSE | mismatcher | astra | 65.2 | 69 |
| astra | FALSE | mismatcher | fable | 44.1 | 34 |
| astra | ANONYMOUS | matcher | astra | 64.1 | 78 |
| astra | ANONYMOUS | matcher | fable | 80.0 | 25 |
| astra | ANONYMOUS | mismatcher | astra | 60.9 | 69 |
| astra | ANONYMOUS | mismatcher | fable | 44.1 | 34 |
| fable | TRUE | matcher | astra | 67.9 | 78 |
| fable | TRUE | matcher | fable | 80.0 | 25 |
| fable | TRUE | mismatcher | astra | 50.7 | 69 |
| fable | TRUE | mismatcher | fable | 55.9 | 34 |
| fable | FALSE | matcher | astra | 66.7 | 78 |
| fable | FALSE | matcher | fable | 80.0 | 25 |
| fable | FALSE | mismatcher | astra | 52.2 | 69 |
| fable | FALSE | mismatcher | fable | 52.9 | 34 |
| fable | ANONYMOUS | matcher | astra | 71.8 | 78 |
| fable | ANONYMOUS | matcher | fable | 80.0 | 25 |
| fable | ANONYMOUS | mismatcher | astra | 52.2 | 69 |
| fable | ANONYMOUS | mismatcher | fable | 55.9 | 34 |

Early vs late rounds:

| judge | condition | rounds 1-10 | rounds 11-20 |
|---|---|---:|---:|
| astra | TRUE | 63.7 | 48.3 |
| astra | FALSE | 65.8 | 58.3 |
| astra | ANONYMOUS | 65.1 | 53.3 |
| fable | TRUE | 61.6 | 61.7 |
| fable | FALSE | 64.4 | 53.3 |
| fable | ANONYMOUS | 63.0 | 65.0 |

## Players

| game | seat | model | % STAR | % switch | matcher wins /20 |
|---|---|---|---:|---:|---:|
| GAA1 | matcher | astra | 50.0 | 47.4 | 9 |
| GAA1 | mismatcher | astra | 55.0 | 47.4 |  |
| GAF1 | matcher | astra | 66.7 | 80.0 | 2 |
| GAF1 | mismatcher | fable | 66.7 | 60.0 |  |
| GFA1 | matcher | fable | 66.7 | 100.0 | 0 |
| GFA1 | mismatcher | astra | 33.3 | 100.0 |  |
| GFF1 | matcher | fable | 66.7 | 60.0 | 1 |
| GFF1 | mismatcher | fable | 50.0 | 60.0 |  |
| GAA2 | matcher | astra | 50.0 | 42.1 | 9 |
| GAA2 | mismatcher | astra | 45.0 | 42.1 |  |
| GAF2 | matcher | astra | 50.0 | 100.0 | 2 |
| GAF2 | mismatcher | fable | 50.0 | 66.7 |  |
| GFA2 | matcher | fable | 66.7 | 100.0 | 0 |
| GFA2 | mismatcher | astra | 33.3 | 100.0 |  |
| GFF2 | matcher | fable | 75.0 | 66.7 | 2 |
| GFF2 | mismatcher | fable | 25.0 | 33.3 |  |
| GAA3 | matcher | astra | 45.0 | 57.9 | 11 |
| GAA3 | mismatcher | astra | 60.0 | 57.9 |  |
| GAF3 | matcher | astra | 75.0 | 28.6 | 4 |
| GAF3 | mismatcher | fable | 75.0 | 28.6 |  |
| GFA3 | matcher | fable | 66.7 | 100.0 | 0 |
| GFA3 | mismatcher | astra | 33.3 | 100.0 |  |
| GFF3 | matcher | fable | 83.3 | 40.0 | 2 |
| GFF3 | mismatcher | fable | 50.0 | 80.0 |  |

Per-game accuracy: `by_game.csv`; trajectories: `figures/trajectory_judge_astra.png`, `figures/trajectory_judge_fable.png`, `figures/choices_by_game.png`.

## Limitations

- Two models, three games per matchup, 20 rounds: a feasibility pilot. Effects are described at game level; no confirmatory claim.
- 'Same model' means another independently queried instance, not memory of the actions. A truth benefit measures the functional value of identity information, not introspection or privileged access.
- Neither endpoint supports temperature control; both ran at provider-default sampling with low hidden reasoning (effort=low, excluded). Hidden reasoning content is unobserved.
- Players see the full public history afresh each round; there is no carried conversation state.
- Beating 50% by exploiting simple action biases is not self-knowledge; compare with the history-only baselines above.
- The dollar ceiling was set by Claude from Chris's standing $100 project cap and 'build and run it' instruction; see approvals.jsonl.

