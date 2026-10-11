# Blind Twin on Experiment 1 game logs (Experiment 2 pilot)

Run `btx1-20261010`. Protocol BlindTwinExp1_v1. Exploratory pilot. Judges Astra, Fable and Qwen predicted both players' next moves in the 36 Experiment 1 games where neither player was told its opponent's identity (18 RPS, 18 MP; 2 per ordered pairing), under TRUE, FALSE (fixed rotation Astra->Fable->Qwen->Astra) and ANONYMOUS identity labels.

## Completion and cost

- Judge calls: 6480 recorded of 6480 planned; valid predictions: 6452.
- Paired items (valid under all three labels): {'astra': 1440, 'fable': 1408, 'qwen': 1440} of 1440 per judge.
- Charged cost: $33.06 (hard cap $70).

## Identity indices (percentage points; 5,000 whole-game bootstrap resamples within game type x ordered pairing)

| index | estimate | 95% interval |
|---|---:|---|
| **RPS S: self-specific truth benefit (TRUE vs ANONYMOUS), primary** | +1.8 | [-0.7, +4.4] |
| RPS S_false: self-specific false-label cost (TRUE vs FALSE) | +3.9 | [+0.6, +7.4] |
| RPS S[astra] | +3.5 | [+0.2, +6.9] |
| RPS S[fable] | +4.8 | [+0.7, +8.9] |
| RPS S[qwen] | -2.8 | [-9.3, +3.7] |
| **MP S: self-specific truth benefit (TRUE vs ANONYMOUS), primary** | +1.5 | [-1.0, +4.2] |
| MP S_false: self-specific false-label cost (TRUE vs FALSE) | +3.5 | [+0.8, +6.3] |
| MP S[astra] | +3.1 | [-1.0, +7.5] |
| MP S[fable] | +3.8 | [-1.5, +9.0] |
| MP S[qwen] | -2.3 | [-4.8, +0.2] |
| Pooled S (mean of RPS and MP), secondary | +1.7 | [-0.1, +3.5] |
| Pooled S_false, secondary | +3.7 | [+1.5, +5.9] |

Positive S: telling a judge the truth helps it predict players of its own model more than it helps other judges predict that model. This measures the functional value of identity information, not introspection.

## RPS accuracy (percent; chance = 33.3)

| judge | predicted player model | TRUE | FALSE | ANONYMOUS | T (truth benefit) | F (false-label cost) |
|---|---|---:|---:|---:|---:|---:|
| astra | astra (self) | 43.8 | 46.7 | 40.0 | +3.8 | -2.9 |
| astra | fable | 46.7 | 42.9 | 40.4 | +6.2 | +3.8 |
| astra | qwen | 40.4 | 44.6 | 39.2 | +1.3 | -4.2 |
| fable | astra | 40.8 | 41.6 | 40.3 | +0.5 | -0.8 |
| fable | fable (self) | 53.4 | 38.8 | 45.0 | +8.3 | +14.5 |
| fable | qwen | 46.3 | 46.4 | 44.4 | +1.9 | -0.1 |
| qwen | astra | 31.2 | 33.8 | 31.2 | +0.0 | -2.5 |
| qwen | fable | 41.7 | 35.8 | 40.8 | +0.8 | +5.8 |
| qwen | qwen (self) | 37.5 | 36.2 | 38.8 | -1.3 | +1.3 |

History-only baselines (percent of players' choices predicted, prior rounds only; RPS):

| player model | uniform | expanding_frequency | repeat_last | markov1_smoothed | counter_opponent_last |
|---|---:|---:|---:|---:|---:|
| astra | 33.3 | 27.8 | 29.6 | 29.1 | 30.8 |
| fable | 33.3 | 25.8 | 22.1 | 33.4 | 34.2 |
| qwen | 33.3 | 27.5 | 32.5 | 32.7 | 46.7 |

## MP accuracy (percent; chance = 50.0)

| judge | predicted player model | TRUE | FALSE | ANONYMOUS | T (truth benefit) | F (false-label cost) |
|---|---|---:|---:|---:|---:|---:|
| astra | astra (self) | 58.3 | 60.8 | 55.0 | +3.3 | -2.5 |
| astra | fable | 55.4 | 55.0 | 56.2 | -0.8 | +0.4 |
| astra | qwen | 53.3 | 54.2 | 51.7 | +1.7 | -0.8 |
| fable | astra | 58.3 | 60.0 | 57.5 | +0.8 | -1.7 |
| fable | fable (self) | 65.0 | 56.2 | 62.1 | +2.9 | +8.8 |
| fable | qwen | 57.5 | 58.8 | 57.9 | -0.4 | -1.2 |
| qwen | astra | 55.4 | 57.5 | 55.8 | -0.4 | -2.1 |
| qwen | fable | 54.2 | 54.2 | 55.0 | -0.8 | +0.0 |
| qwen | qwen (self) | 56.7 | 55.0 | 58.3 | -1.7 | +1.7 |

History-only baselines (percent of players' choices predicted, prior rounds only; MP):

| player model | uniform | expanding_frequency | repeat_last | markov1_smoothed | best_response_opponent_last | win_stay_lose_shift |
|---|---:|---:|---:|---:|---:|---:|
| astra | 50.0 | 44.0 | 47.5 | 48.1 | 38.8 | 38.8 |
| fable | 50.0 | 44.4 | 44.6 | 43.8 | 47.9 | 47.9 |
| qwen | 50.0 | 41.5 | 51.2 | 47.1 | 52.5 | 52.5 |

## Responsiveness (percent of paired predictions that change between labels)

| game | judge | TRUE vs ANONYMOUS | TRUE vs FALSE | FALSE vs ANONYMOUS |
|---|---|---:|---:|---:|
| rps | astra | 18.8 | 19.7 | 21.5 |
| rps | fable | 24.9 | 28.4 | 26.8 |
| rps | qwen | 40.1 | 42.8 | 41.4 |
| mp | astra | 13.1 | 15.1 | 13.2 |
| mp | fable | 18.6 | 16.1 | 18.1 |
| mp | qwen | 29.3 | 26.8 | 26.9 |

## Interpretation boundaries

- Two games per ordered pairing: intervals reflect game-to-game variation and are wide or unstable; exploratory.
- Game logs come from Experiment 1 (including make-up games for interrupted Qwen games; MP Qwen games carry the selection caveat in EXPERIMENT1_MAKEUP_GAMES.md, though condition-00 cells were least affected).
- FALSE uses a fixed rotation, so a FALSE label can name the judge's own model for a different player (e.g. an Astra player labelled Fable for the Fable judge).

