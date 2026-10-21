# Matching-pennies opponent identity disclosure: three-model factorial pilot

Run `with_makeups`. Protocol MPDisclosure3M_v1_pilot2. Exploratory pilot (2 games per cell); Player 1 = Matcher, Player 2 = Mismatcher; unit of analysis = complete 20-round game. Not pooled with RPS or the Astra-only MP pilot.

## Completion, cost and endpoint fidelity

- Games complete: 72 / 113 planned (72).
- Player calls recorded: 3746 (planned 2880); valid: 3705.
- Charged cost: $27.36 scientific + $0.00 smoke = $27.36 (hard cap $60).
- Returned providers: {('astra', 'OpenAI'): 1123, ('fable', 'Anthropic'): 1171, ('qwen', 'Alibaba'): 1452}.

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
| astra vs qwen | 00 | 2/3 | 0.425 |
| astra vs qwen | 10 | 2/3 | 0.575 |
| astra vs qwen | 01 | 2/4 | 0.400 |
| astra vs qwen | 11 | 2/6 | 0.425 |
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
| fable vs qwen | 01 | 2/4 | 0.375 |
| fable vs qwen | 11 | 2/8 | 0.450 |
| qwen vs astra | 00 | 2/3 | 0.525 |
| qwen vs astra | 10 | 2/3 | 0.625 |
| qwen vs astra | 01 | 2/3 | 0.450 |
| qwen vs astra | 11 | 2/4 | 0.450 |
| qwen vs fable | 00 | 2/3 | 0.350 |
| qwen vs fable | 10 | 2/8 | 0.550 |
| qwen vs fable | 01 | 2/6 | 0.475 |
| qwen vs fable | 11 | 2/2 | 0.575 |
| qwen vs qwen | 00 | 2/4 | 0.625 |
| qwen vs qwen | 10 | 2/3 | 0.425 |
| qwen vs qwen | 01 | 2/2 | 0.525 |
| qwen vs qwen | 11 | 2/8 | 0.425 |

## Primary: self-specific opponent-disclosure contrast D (payoff units; 1 = win, 0 = loss)

| quantity | estimate | 95% game-level bootstrap interval |
|---|---:|---|
| **D = mean(D_Astra, D_Fable, D_Qwen)** | -0.060 | [-0.100, -0.023] |
| D[astra] = S - O | -0.012 | [-0.075, +0.050] |
| S[astra] (same-model unilateral disclosure benefit) | +0.025 | [-0.025, +0.075] |
| O[astra] (other-model unilateral disclosure benefit) | +0.037 | [+0.000, +0.075] |
| D[fable] = S - O | -0.012 | [-0.081, +0.056] |
| S[fable] (same-model unilateral disclosure benefit) | -0.050 | [-0.100, +0.000] |
| O[fable] (other-model unilateral disclosure benefit) | -0.038 | [-0.081, +0.012] |
| D[qwen] = S - O | -0.156 | [-0.238, -0.081] |
| S[qwen] (same-model unilateral disclosure benefit) | -0.050 | [-0.100, +0.000] |
| O[qwen] (other-model unilateral disclosure benefit) | +0.106 | [+0.050, +0.163] |

Positive D: being told the opponent's true identity helps more when the opponent is the same model. U1 is a Matcher-seat effect and U2 a Mismatcher-seat effect, so S and O each average both roles.

## Unilateral and factorial components by ordered pairing

| Matcher vs Mismatcher | U1 | U2 | U | Matcher information effect | Mismatcher information effect | interaction (Matcher scale) |
|---|---:|---:|---:|---:|---:|---:|
| astra vs astra | -0.025 [-0.10, +0.05] | +0.075 [+0.00, +0.15] | +0.025 [-0.02, +0.08] | +0.025 [-0.03, +0.08] | +0.025 [-0.03, +0.08] | +0.100 [+0.00, +0.20] |
| astra vs fable | -0.150 [-0.25, -0.05] | +0.050 [+0.00, +0.10] | -0.050 [-0.08, -0.02] | -0.050 [-0.10, +0.00] | -0.050 [-0.10, +0.00] | +0.200 [+0.10, +0.30] |
| astra vs qwen | +0.150 [+0.05, +0.25] | +0.025 [-0.05, +0.10] | +0.087 [+0.02, +0.15] | +0.087 [+0.02, +0.15] | +0.087 [+0.02, +0.15] | -0.125 [-0.25, +0.00] |
| fable vs astra | -0.150 [-0.15, -0.15] | +0.075 [+0.05, +0.10] | -0.037 [-0.05, -0.02] | -0.025 [-0.08, +0.02] | -0.050 [-0.10, +0.00] | +0.250 [+0.15, +0.35] |
| fable vs fable | +0.025 [-0.10, +0.15] | -0.125 [-0.20, -0.05] | -0.050 [-0.10, +0.00] | -0.050 [-0.16, +0.06] | -0.050 [-0.16, +0.08] | -0.150 [-0.38, +0.10] |
| fable vs qwen | +0.075 [-0.05, +0.20] | +0.100 [-0.10, +0.30] | +0.088 [+0.00, +0.17] | +0.075 [-0.04, +0.19] | +0.100 [-0.01, +0.21] | +0.000 [-0.22, +0.23] |
| qwen vs astra | +0.100 [+0.05, +0.15] | +0.075 [+0.05, +0.10] | +0.087 [+0.07, +0.10] | +0.050 [+0.01, +0.09] | +0.125 [+0.09, +0.16] | -0.100 [-0.18, -0.02] |
| qwen vs fable | +0.200 [+0.15, +0.25] | -0.125 [-0.25, +0.00] | +0.038 [+0.00, +0.08] | +0.150 [+0.09, +0.21] | -0.075 [-0.14, -0.01] | -0.100 [-0.23, +0.02] |
| qwen vs qwen | -0.200 [-0.30, -0.10] | +0.100 [+0.05, +0.15] | -0.050 [-0.10, +0.00] | -0.150 [-0.25, -0.05] | +0.050 [-0.05, +0.15] | +0.100 [-0.10, +0.30] |

## Behaviour by model x role (complete games; informed vs uninformed, same/other-model opponent)

| model | role | opponent | informed | n seats | win % | %STAR | switch % | win-stay % | lose-shift % | longest run | entropy (bits) |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| astra | Matcher | same | False | 4 | 48.8 | 55.0 | 51.3 | 34.2 | 35.6 | 4.8 | 1.0 |
| astra | Matcher | same | True | 4 | 51.2 | 48.8 | 52.6 | 29.4 | 31.1 | 3.5 | 1.0 |
| astra | Matcher | other | False | 8 | 46.9 | 48.1 | 50.7 | 40.3 | 43.7 | 5.1 | 1.0 |
| astra | Matcher | other | True | 8 | 48.8 | 51.2 | 55.9 | 27.4 | 41.4 | 3.9 | 1.0 |
| astra | Mismatcher | same | False | 4 | 48.8 | 57.5 | 50.0 | 36.5 | 38.5 | 5.8 | 1.0 |
| astra | Mismatcher | same | True | 4 | 51.2 | 56.2 | 56.6 | 21.5 | 34.6 | 3.8 | 1.0 |
| astra | Mismatcher | other | False | 8 | 47.5 | 53.8 | 48.0 | 46.4 | 44.8 | 4.9 | 1.0 |
| astra | Mismatcher | other | True | 8 | 51.2 | 48.1 | 53.3 | 36.3 | 39.7 | 5.2 | 1.0 |
| fable | Matcher | same | False | 4 | 51.2 | 56.2 | 60.5 | 26.8 | 45.1 | 3.2 | 1.0 |
| fable | Matcher | same | True | 4 | 46.2 | 56.2 | 59.2 | 35.4 | 52.2 | 3.8 | 1.0 |
| fable | Matcher | other | False | 8 | 46.9 | 45.6 | 55.3 | 39.1 | 50.9 | 5.0 | 1.0 |
| fable | Matcher | other | True | 8 | 49.4 | 43.1 | 53.3 | 39.7 | 45.7 | 5.0 | 1.0 |
| fable | Mismatcher | same | False | 4 | 53.8 | 47.5 | 56.6 | 35.1 | 46.2 | 4.0 | 1.0 |
| fable | Mismatcher | same | True | 4 | 48.8 | 45.0 | 65.8 | 29.5 | 63.3 | 3.0 | 1.0 |
| fable | Mismatcher | other | False | 8 | 53.8 | 48.8 | 57.2 | 33.8 | 48.2 | 4.0 | 1.0 |
| fable | Mismatcher | other | True | 8 | 47.5 | 46.2 | 58.6 | 39.9 | 57.5 | 4.1 | 1.0 |
| qwen | Matcher | same | False | 4 | 57.5 | 47.5 | 46.1 | 60.8 | 57.6 | 4.5 | 1.0 |
| qwen | Matcher | same | True | 4 | 42.5 | 47.5 | 56.6 | 48.8 | 62.8 | 3.8 | 1.0 |
| qwen | Matcher | other | False | 8 | 45.0 | 52.5 | 53.3 | 51.3 | 54.2 | 4.8 | 1.0 |
| qwen | Matcher | other | True | 8 | 55.0 | 50.0 | 56.6 | 35.8 | 46.6 | 4.5 | 1.0 |
| qwen | Mismatcher | same | False | 4 | 47.5 | 52.5 | 36.8 | 63.1 | 34.9 | 6.5 | 1.0 |
| qwen | Mismatcher | same | True | 4 | 52.5 | 47.5 | 48.7 | 48.6 | 41.9 | 3.8 | 1.0 |
| qwen | Mismatcher | other | False | 8 | 49.4 | 54.4 | 50.7 | 45.4 | 47.8 | 5.1 | 1.0 |
| qwen | Mismatcher | other | True | 8 | 58.8 | 48.8 | 55.3 | 42.6 | 51.4 | 4.5 | 1.0 |

## Prospective history-only predictability / exploitability (percent of choices; chance = 50)

| model | role | informed | uniform | expanding_frequency | repeat_last | markov1_smoothed | best_response_opponent_last | win_stay_lose_shift |
|---|---|---|---:|---:|---:|---:|---:|---:|
| astra | Matcher | False | 50.0 | 43.5 | 49.2 | 44.6 | 40.0 | 40.0 |
| astra | Matcher | True | 50.0 | 44.8 | 45.4 | 43.5 | 33.8 | 33.8 |
| astra | Mismatcher | False | 50.0 | 43.5 | 51.2 | 51.5 | 44.6 | 44.6 |
| astra | Mismatcher | True | 50.0 | 43.1 | 45.8 | 47.5 | 35.8 | 35.8 |
| fable | Matcher | False | 50.0 | 44.0 | 43.3 | 47.9 | 42.9 | 42.9 |
| fable | Matcher | True | 50.0 | 49.2 | 45.0 | 47.1 | 43.3 | 43.3 |
| fable | Mismatcher | False | 50.0 | 43.1 | 43.3 | 43.8 | 40.8 | 40.8 |
| fable | Mismatcher | True | 50.0 | 44.8 | 39.6 | 48.1 | 48.8 | 48.8 |
| qwen | Matcher | False | 50.0 | 44.0 | 49.2 | 44.4 | 54.2 | 54.2 |
| qwen | Matcher | True | 50.0 | 41.9 | 43.8 | 45.4 | 46.2 | 46.2 |
| qwen | Mismatcher | False | 50.0 | 41.9 | 53.8 | 47.9 | 47.1 | 47.1 |
| qwen | Mismatcher | True | 50.0 | 44.0 | 47.1 | 44.6 | 46.7 | 46.7 |

## Conditional choice (pooled, game-clustered bootstrap; Brown-Rosenthal-style, descriptive)

A per-game multi-lag regression is not identified on 19 transitions per player; this pools transitions within model x role x informed and resamples whole games. Cells with few games or few post-loss rounds are unstable.

| model | role | informed | games | P(repeat after win) % | P(repeat after loss) % |
|---|---|---|---:|---:|---:|
| astra | Matcher | False | 12 | 37.7 [27, 48] (n=106) | 59.0 [54, 65] (n=122) |
| astra | Matcher | True | 12 | 28.1 [17, 40] (n=114) | 62.3 [49, 75] (n=114) |
| astra | Mismatcher | False | 12 | 45.5 [31, 58] (n=110) | 56.8 [50, 62] (n=118) |
| astra | Mismatcher | True | 12 | 31.4 [23, 39] (n=118) | 60.9 [53, 69] (n=110) |
| fable | Matcher | False | 12 | 34.9 [25, 44] (n=109) | 50.4 [45, 57] (n=119) |
| fable | Matcher | True | 12 | 37.0 [31, 43] (n=108) | 51.7 [47, 57] (n=120) |
| fable | Mismatcher | False | 12 | 34.7 [27, 43] (n=124) | 52.9 [46, 59] (n=104) |
| fable | Mismatcher | True | 12 | 37.3 [29, 43] (n=110) | 40.7 [36, 46] (n=118) |
| qwen | Matcher | False | 12 | 53.6 [42, 64] (n=112) | 44.8 [36, 55] (n=116) |
| qwen | Matcher | True | 12 | 39.8 [34, 46] (n=118) | 47.3 [39, 55] (n=110) |
| qwen | Mismatcher | False | 12 | 50.9 [39, 62] (n=110) | 56.8 [48, 64] (n=118) |
| qwen | Mismatcher | True | 12 | 44.2 [38, 51] (n=129) | 50.5 [44, 58] (n=99) |

## Independent rescore

`rescore.py` recomputed V and D from `rounds.csv` without the game-result routine: {"D_rescore": -0.060416666666666674, "n_complete_games": 72, "round_result_mismatches": 0}

## Interpretation boundaries

- Feasibility pilot: 2 games per cell; intervals reflect game-to-game variation within cells, are often unstable, and are neither confirmation nor evidence of absence. No multiplicity correction across 36 cells.
- Disclosure is always truthful. A self-specific effect is functional use of self-related information, not privileged introspection; model-name priors and skill differences remain alternatives.
- 'Same model' means another independently queried instance with the same name and settings.

