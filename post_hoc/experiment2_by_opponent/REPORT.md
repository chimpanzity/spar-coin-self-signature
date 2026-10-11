# Experiment 2 self-prediction advantage by the player's opponent (exploratory, 2026-10-11)

Run btx1-20261010, condition-00 games, paired items, equal weight over seats then games; 80 predictions per cell.
Self advantage = self-judge accuracy minus the mean of the two other judges on the same target and opponent.

| game | target | opponent | self TRUE | others TRUE | adv TRUE | self ANON | others ANON | adv ANON |
|---|---|---|---:|---:|---:|---:|---:|---:|
| rps | astra | astra (self-self) | 40.0 | 33.8 | +6.2 | 40.0 | 33.8 | +6.2 |
| rps | astra | fable | 38.7 | 33.1 | +5.6 | 36.2 | 33.1 | +3.1 |
| rps | astra | qwen | 52.5 | 41.2 | +11.3 | 43.8 | 40.5 | +3.3 |
| rps | fable | astra | 53.4 | 38.8 | +14.6 | 41.5 | 36.2 | +5.3 |
| rps | fable | fable (self-self) | 42.5 | 39.4 | +3.1 | 38.7 | 38.8 | -0.1 |
| rps | fable | qwen | 64.2 | 54.4 | +9.8 | 54.8 | 46.9 | +7.9 |
| rps | qwen | astra | 35.0 | 39.9 | -4.9 | 35.0 | 38.7 | -3.7 |
| rps | qwen | fable | 45.0 | 48.9 | -3.9 | 45.0 | 46.7 | -1.7 |
| rps | qwen | qwen (self-self) | 32.5 | 41.2 | -8.7 | 36.3 | 40.0 | -3.7 |
| mp | astra | astra (self-self) | 57.5 | 58.8 | -1.3 | 50.0 | 58.8 | -8.8 |
| mp | astra | fable | 57.5 | 55.6 | +1.9 | 55.0 | 55.0 | +0.0 |
| mp | astra | qwen | 60.0 | 56.2 | +3.8 | 60.0 | 56.2 | +3.8 |
| mp | fable | astra | 67.5 | 51.2 | +16.3 | 66.3 | 56.2 | +10.1 |
| mp | fable | fable (self-self) | 58.8 | 58.1 | +0.7 | 52.5 | 57.5 | -5.0 |
| mp | fable | qwen | 68.8 | 55.0 | +13.8 | 67.5 | 53.1 | +14.4 |
| mp | qwen | astra | 52.5 | 56.2 | -3.7 | 65.0 | 58.8 | +6.2 |
| mp | qwen | fable | 60.0 | 65.0 | -5.0 | 53.8 | 58.1 | -4.3 |
| mp | qwen | qwen (self-self) | 57.5 | 45.0 | +12.5 | 56.2 | 47.5 | +8.7 |

Reading: Fable's self advantage is carried by its games against Astra and Qwen (RPS +14.6 and +9.8 TRUE; MP +16.3 and +13.8) and is
near zero in Fable-Fable games (RPS +3.1, MP +0.7). The self-self games, which the btss-20261011 pilot used exclusively, are the
condition in which every judge, the self-judge included, predicts least well. The test-retest run (btss-retest-20261011) puts the
noise of an 80-prediction cell at about 5 pp and of a T = TRUE - ANON difference at about 7 pp, so single cells here are not
individually interpretable; the pattern across the six Fable cells is what is worth noting.