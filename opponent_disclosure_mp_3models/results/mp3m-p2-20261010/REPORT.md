# Matching-pennies opponent identity disclosure: three-model factorial pilot

Run `mp3m-p2-20261010`. Protocol MPDisclosure3M_v1_pilot2. Exploratory pilot (2 games per cell); Player 1 = Matcher, Player 2 = Mismatcher; unit of analysis = complete 20-round game. Not pooled with RPS or the Astra-only MP pilot.

## Completion, cost and endpoint fidelity

- Games complete: 54 / 72 planned (72).
- Player calls recorded: 2576 (planned 2880); valid: 2558.
- Charged cost: $20.28 scientific + $0.00 smoke = $20.28 (hard cap $60).
- Returned providers: {('astra', 'OpenAI'): 895, ('fable', 'Anthropic'): 918, ('qwen', 'Alibaba'): 763}.

| Matcher (P1) vs Mismatcher (P2) | condition | complete / planned | V = Matcher payoff |
|---|---|---:|---:|
| astra vs astra | 00 | 2/2 | 0.525 |
| astra vs astra | 10 | 2/2 | 0.500 |
| astra vs astra | 01 | 2/2 | 0.450 |
| astra vs astra | 11 | 2/2 | 0.525 |
| astra vs fable | 00 | 2/2 | 0.550 |
| astra vs fable | 10 | 2/2 | 0.400 |
| astra vs fable | 01 | 2/2 | 0.500 |
| astra vs fable | 11 | 2/2 | 0.550 |
| astra vs qwen | 00 | 1/2 | 0.450 |
| astra vs qwen | 10 | 1/2 | 0.650 |
| astra vs qwen | 01 | 1/2 | 0.350 |
| astra vs qwen | 11 | 0/2 | NA |
| fable vs astra | 00 | 2/2 | 0.550 |
| fable vs astra | 10 | 2/2 | 0.400 |
| fable vs astra | 01 | 2/2 | 0.475 |
| fable vs astra | 11 | 2/2 | 0.575 |
| fable vs fable | 00 | 2/2 | 0.450 |
| fable vs fable | 10 | 2/2 | 0.475 |
| fable vs fable | 01 | 2/2 | 0.575 |
| fable vs fable | 11 | 2/2 | 0.450 |
| fable vs qwen | 00 | 2/2 | 0.475 |
| fable vs qwen | 10 | 2/2 | 0.550 |
| fable vs qwen | 01 | 1/2 | 0.500 |
| fable vs qwen | 11 | 1/2 | 0.500 |
| qwen vs astra | 00 | 1/2 | 0.500 |
| qwen vs astra | 10 | 1/2 | 0.650 |
| qwen vs astra | 01 | 1/2 | 0.450 |
| qwen vs astra | 11 | 0/2 | NA |
| qwen vs fable | 00 | 1/2 | 0.400 |
| qwen vs fable | 10 | 1/2 | 0.550 |
| qwen vs fable | 01 | 1/2 | 0.550 |
| qwen vs fable | 11 | 2/2 | 0.575 |
| qwen vs qwen | 00 | 1/2 | 0.650 |
| qwen vs qwen | 10 | 1/2 | 0.500 |
| qwen vs qwen | 01 | 2/2 | 0.525 |
| qwen vs qwen | 11 | 1/2 | 0.550 |

## Primary: self-specific opponent-disclosure contrast D (payoff units; 1 = win, 0 = loss)

| quantity | estimate | 95% game-level bootstrap interval |
|---|---:|---|
| **D = mean(D_Astra, D_Fable, D_Qwen)** | NA | [NA, NA] (unstable) |
| D[astra] = S - O | NA | [NA, NA] (unstable) |
| S[astra] (same-model unilateral disclosure benefit) | NA | [NA, NA] (unstable) |
| O[astra] (other-model unilateral disclosure benefit) | NA | [NA, NA] (unstable) |
| D[fable] = S - O | -0.006 | [-0.069, +0.056] |
| S[fable] (same-model unilateral disclosure benefit) | -0.050 | [-0.100, +0.000] |
| O[fable] (other-model unilateral disclosure benefit) | -0.044 | [-0.075, -0.013] |
| D[qwen] = S - O | NA | [NA, NA] (unstable) |
| S[qwen] (same-model unilateral disclosure benefit) | NA | [NA, NA] (unstable) |
| O[qwen] (other-model unilateral disclosure benefit) | NA | [NA, NA] (unstable) |

Positive D: being told the opponent's true identity helps more when the opponent is the same model. U1 is a Matcher-seat effect and U2 a Mismatcher-seat effect, so S and O each average both roles.

## Unilateral and factorial components by ordered pairing

| Matcher vs Mismatcher | U1 | U2 | U | Matcher information effect | Mismatcher information effect | interaction (Matcher scale) |
|---|---:|---:|---:|---:|---:|---:|
| astra vs astra | -0.025 [-0.10, +0.05] | +0.075 [+0.00, +0.15] | +0.025 [-0.02, +0.08] | +0.025 [-0.03, +0.08] | +0.025 [-0.03, +0.08] | +0.100 [+0.00, +0.20] |
| astra vs fable | -0.150 [-0.25, -0.05] | +0.050 [+0.00, +0.10] | -0.050 [-0.08, -0.02] | -0.050 [-0.10, +0.00] | -0.050 [-0.10, +0.00] | +0.200 [+0.10, +0.30] |
| astra vs qwen | NA [NA, NA] | NA [NA, NA] | NA [NA, NA] | NA [NA, NA] | NA [NA, NA] | NA [NA, NA] |
| fable vs astra | -0.150 [-0.15, -0.15] | +0.075 [+0.05, +0.10] | -0.037 [-0.05, -0.02] | -0.025 [-0.08, +0.02] | -0.050 [-0.10, +0.00] | +0.250 [+0.15, +0.35] |
| fable vs fable | +0.025 [-0.10, +0.15] | -0.125 [-0.20, -0.05] | -0.050 [-0.10, +0.00] | -0.050 [-0.16, +0.07] | -0.050 [-0.16, +0.06] | -0.150 [-0.38, +0.08] |
| fable vs qwen | +0.075 [-0.05, +0.20] | -0.025 [-0.10, +0.05] | +0.025 [+0.00, +0.05] | +0.038 [-0.03, +0.10] | +0.013 [-0.05, +0.08] | -0.075 [-0.20, +0.05] |
| qwen vs astra | NA [NA, NA] | NA [NA, NA] | NA [NA, NA] | NA [NA, NA] | NA [NA, NA] | NA [NA, NA] |
| qwen vs fable | +0.150 [+0.15, +0.15] | -0.150 [-0.15, -0.15] | +0.000 [+0.00, +0.00] | +0.087 [+0.08, +0.10] | -0.087 [-0.10, -0.08] | -0.125 [-0.15, -0.10] |
| qwen vs qwen | -0.150 [-0.15, -0.15] | +0.125 [+0.10, +0.15] | -0.013 [-0.03, +0.00] | -0.062 [-0.08, -0.05] | +0.037 [+0.02, +0.05] | +0.175 [+0.15, +0.20] |

## Behaviour by model x role (complete games; informed vs uninformed, same/other-model opponent)

| model | role | opponent | informed | n seats | win % | %STAR | switch % | win-stay % | lose-shift % | longest run | entropy (bits) |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| astra | Matcher | same | False | 4 | 48.8 | 55.0 | 51.3 | 34.2 | 35.6 | 4.8 | 1.0 |
| astra | Matcher | same | True | 4 | 51.2 | 48.8 | 52.6 | 29.4 | 31.1 | 3.5 | 1.0 |
| astra | Matcher | other | False | 6 | 48.3 | 48.3 | 50.9 | 37.1 | 41.6 | 5.3 | 1.0 |
| astra | Matcher | other | True | 5 | 51.0 | 50.0 | 58.9 | 33.2 | 52.4 | 3.8 | 1.0 |
| astra | Mismatcher | same | False | 4 | 48.8 | 57.5 | 50.0 | 36.5 | 38.5 | 5.8 | 1.0 |
| astra | Mismatcher | same | True | 4 | 51.2 | 56.2 | 56.6 | 21.5 | 34.6 | 3.8 | 1.0 |
| astra | Mismatcher | other | False | 6 | 49.2 | 54.2 | 45.6 | 53.5 | 46.2 | 5.2 | 1.0 |
| astra | Mismatcher | other | True | 5 | 49.0 | 47.0 | 55.8 | 37.2 | 45.0 | 5.6 | 1.0 |
| fable | Matcher | same | False | 4 | 51.2 | 56.2 | 60.5 | 26.8 | 45.1 | 3.2 | 1.0 |
| fable | Matcher | same | True | 4 | 46.2 | 56.2 | 59.2 | 35.4 | 52.2 | 3.8 | 1.0 |
| fable | Matcher | other | False | 7 | 50.0 | 45.7 | 53.4 | 41.8 | 49.0 | 5.4 | 1.0 |
| fable | Matcher | other | True | 7 | 50.7 | 43.6 | 52.6 | 40.0 | 44.5 | 4.9 | 1.0 |
| fable | Mismatcher | same | False | 4 | 53.8 | 47.5 | 56.6 | 35.1 | 46.2 | 4.0 | 1.0 |
| fable | Mismatcher | same | True | 4 | 48.8 | 45.0 | 65.8 | 29.5 | 63.3 | 3.0 | 1.0 |
| fable | Mismatcher | other | False | 6 | 52.5 | 50.0 | 58.8 | 30.5 | 46.5 | 3.7 | 1.0 |
| fable | Mismatcher | other | True | 7 | 45.7 | 46.4 | 57.1 | 40.8 | 55.5 | 4.3 | 1.0 |
| qwen | Matcher | same | False | 3 | 56.7 | 46.7 | 47.4 | 56.1 | 53.0 | 4.3 | 1.0 |
| qwen | Matcher | same | True | 2 | 52.5 | 47.5 | 57.9 | 52.3 | 70.1 | 3.0 | 1.0 |
| qwen | Matcher | other | False | 4 | 47.5 | 47.5 | 55.3 | 55.9 | 64.3 | 4.8 | 1.0 |
| qwen | Matcher | other | True | 4 | 58.8 | 48.8 | 56.6 | 35.9 | 43.4 | 4.2 | 1.0 |
| qwen | Mismatcher | same | False | 2 | 42.5 | 50.0 | 47.4 | 50.0 | 43.1 | 5.0 | 1.0 |
| qwen | Mismatcher | same | True | 3 | 46.7 | 46.7 | 49.1 | 51.9 | 50.3 | 3.7 | 1.0 |
| qwen | Mismatcher | other | False | 6 | 47.5 | 54.2 | 49.1 | 50.8 | 50.8 | 5.8 | 1.0 |
| qwen | Mismatcher | other | True | 3 | 55.0 | 45.0 | 52.6 | 40.2 | 42.6 | 4.0 | 1.0 |

## Prospective history-only predictability / exploitability (percent of choices; chance = 50)

| model | role | informed | uniform | expanding_frequency | repeat_last | markov1_smoothed | best_response_opponent_last | win_stay_lose_shift |
|---|---|---|---:|---:|---:|---:|---:|---:|
| astra | Matcher | False | 50.0 | 43.5 | 49.0 | 44.8 | 38.0 | 38.0 |
| astra | Matcher | True | 50.0 | 41.9 | 44.2 | 43.1 | 37.5 | 37.5 |
| astra | Mismatcher | False | 50.0 | 45.2 | 52.5 | 51.8 | 46.5 | 46.5 |
| astra | Mismatcher | True | 50.0 | 44.7 | 44.2 | 50.6 | 36.4 | 36.4 |
| fable | Matcher | False | 50.0 | 45.2 | 44.3 | 47.3 | 42.0 | 42.0 |
| fable | Matcher | True | 50.0 | 48.9 | 45.2 | 46.4 | 43.0 | 43.0 |
| fable | Mismatcher | False | 50.0 | 42.2 | 42.5 | 44.5 | 39.5 | 39.5 |
| fable | Mismatcher | True | 50.0 | 44.3 | 40.2 | 47.7 | 48.9 | 48.9 |
| qwen | Matcher | False | 50.0 | 42.1 | 48.2 | 43.6 | 57.5 | 57.5 |
| qwen | Matcher | True | 50.0 | 41.2 | 43.3 | 41.7 | 46.7 | 46.7 |
| qwen | Mismatcher | False | 50.0 | 41.2 | 51.2 | 45.3 | 49.4 | 49.4 |
| qwen | Mismatcher | True | 50.0 | 46.7 | 49.2 | 42.5 | 46.7 | 46.7 |

## Conditional choice (pooled, game-clustered bootstrap; Brown-Rosenthal-style, descriptive)

A per-game multi-lag regression is not identified on 19 transitions per player; this pools transitions within model x role x informed and resamples whole games. Cells with few games or few post-loss rounds are unstable.

| model | role | informed | games | P(repeat after win) % | P(repeat after loss) % |
|---|---|---|---:|---:|---:|
| astra | Matcher | False | 10 | 35.6 [24, 47] (n=90) | 61.0 [55, 67] (n=100) |
| astra | Matcher | True | 9 | 31.0 [17, 45] (n=87) | 57.1 [42, 72] (n=84) |
| astra | Mismatcher | False | 10 | 48.9 [36, 61] (n=94) | 56.2 [49, 63] (n=96) |
| astra | Mismatcher | True | 9 | 29.9 [19, 40] (n=87) | 58.3 [49, 66] (n=84) |
| fable | Matcher | False | 11 | 35.6 [25, 46] (n=104) | 52.4 [47, 58] (n=105) |
| fable | Matcher | True | 11 | 37.0 [30, 43] (n=100) | 52.3 [47, 58] (n=109) |
| fable | Mismatcher | False | 10 | 32.4 [25, 40] (n=102) | 53.4 [46, 60] (n=88) |
| fable | Mismatcher | True | 11 | 37.8 [29, 44] (n=98) | 41.4 [36, 47] (n=111) |
| qwen | Matcher | False | 7 | 55.9 [50, 62] (n=68) | 40.0 [28, 55] (n=65) |
| qwen | Matcher | True | 6 | 40.9 [33, 48] (n=66) | 45.8 [33, 61] (n=48) |
| qwen | Mismatcher | False | 8 | 50.7 [37, 64] (n=71) | 51.9 [43, 62] (n=81) |
| qwen | Mismatcher | True | 6 | 45.8 [37, 55] (n=59) | 52.7 [49, 58] (n=55) |

## Independent rescore

`rescore.py` recomputed V and D from `rounds.csv` without the game-result routine: {"D_rescore": -0.04375000000000001, "n_complete_games": 54, "round_result_mismatches": 0}

## Interpretation boundaries

- Feasibility pilot: 2 games per cell; intervals reflect game-to-game variation within cells, are often unstable, and are neither confirmation nor evidence of absence. No multiplicity correction across 36 cells.
- Disclosure is always truthful. A self-specific effect is functional use of self-related information, not privileged introspection; model-name priors and skill differences remain alternatives.
- 'Same model' means another independently queried instance with the same name and settings.

