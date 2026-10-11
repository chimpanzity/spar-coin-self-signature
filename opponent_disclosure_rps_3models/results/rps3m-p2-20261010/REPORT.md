# RPS opponent identity disclosure: three-model factorial pilot

Run `rps3m-p2-20261010`. Protocol RPSDisclosure3M_v1_pilot2. Exploratory pilot (2 games per cell); unit of analysis = complete 20-round game.

## Completion, cost and endpoint fidelity

- Games complete: 71 / 72 planned (72).
- Player calls recorded: 2866 (planned 2880); valid: 2865.
- Charged cost: $22.32 scientific + $0.00 smoke = $22.32 (hard cap $60).
- Returned providers: {('astra', 'OpenAI'): 960, ('qwen', 'Alibaba'): 953, ('fable', 'Anthropic'): 953}.

| P1 \ P2 | condition | complete / planned | V = P1 payoff |
|---|---|---:|---:|
| astra vs astra | 00 | 2/2 | 0.488 |
| astra vs astra | 10 | 2/2 | 0.588 |
| astra vs astra | 01 | 2/2 | 0.475 |
| astra vs astra | 11 | 2/2 | 0.463 |
| astra vs fable | 00 | 2/2 | 0.438 |
| astra vs fable | 10 | 2/2 | 0.438 |
| astra vs fable | 01 | 2/2 | 0.475 |
| astra vs fable | 11 | 2/2 | 0.487 |
| astra vs qwen | 00 | 2/2 | 0.438 |
| astra vs qwen | 10 | 2/2 | 0.575 |
| astra vs qwen | 01 | 2/2 | 0.450 |
| astra vs qwen | 11 | 2/2 | 0.562 |
| fable vs astra | 00 | 2/2 | 0.613 |
| fable vs astra | 10 | 2/2 | 0.562 |
| fable vs astra | 01 | 2/2 | 0.537 |
| fable vs astra | 11 | 2/2 | 0.488 |
| fable vs fable | 00 | 2/2 | 0.475 |
| fable vs fable | 10 | 2/2 | 0.500 |
| fable vs fable | 01 | 2/2 | 0.412 |
| fable vs fable | 11 | 2/2 | 0.588 |
| fable vs qwen | 00 | 1/2 | 0.500 |
| fable vs qwen | 10 | 2/2 | 0.500 |
| fable vs qwen | 01 | 2/2 | 0.537 |
| fable vs qwen | 11 | 2/2 | 0.475 |
| qwen vs astra | 00 | 2/2 | 0.488 |
| qwen vs astra | 10 | 2/2 | 0.587 |
| qwen vs astra | 01 | 2/2 | 0.387 |
| qwen vs astra | 11 | 2/2 | 0.400 |
| qwen vs fable | 00 | 2/2 | 0.338 |
| qwen vs fable | 10 | 2/2 | 0.550 |
| qwen vs fable | 01 | 2/2 | 0.463 |
| qwen vs fable | 11 | 2/2 | 0.438 |
| qwen vs qwen | 00 | 2/2 | 0.525 |
| qwen vs qwen | 10 | 2/2 | 0.525 |
| qwen vs qwen | 01 | 2/2 | 0.475 |
| qwen vs qwen | 11 | 2/2 | 0.425 |

## Primary: self-specific opponent-disclosure contrast D (payoff units; 1 = win, 0.5 = tie)

| quantity | estimate | 95% game-level bootstrap interval |
|---|---:|---|
| **D = mean(D_Astra, D_Fable, D_Qwen)** | +0.011 | [-0.030, +0.052] |
| D[astra] = S - O | -0.022 | [-0.084, +0.038] |
| S[astra] (same-model unilateral disclosure benefit) | +0.056 | [+0.025, +0.087] |
| O[astra] (other-model unilateral disclosure benefit) | +0.078 | [+0.028, +0.131] |
| D[fable] = S - O | +0.097 | [+0.047, +0.150] |
| S[fable] (same-model unilateral disclosure benefit) | +0.044 | [+0.013, +0.075] |
| O[fable] (other-model unilateral disclosure benefit) | -0.053 | [-0.084, -0.022] |
| D[qwen] = S - O | -0.041 | [-0.138, +0.056] |
| S[qwen] (same-model unilateral disclosure benefit) | +0.025 | [-0.063, +0.112] |
| O[qwen] (other-model unilateral disclosure benefit) | +0.066 | [+0.028, +0.106] |

Positive D: being told the opponent's true identity helps more when the opponent is the same model. Neither sign shows introspection; model-name priors remain possible explanations.

## Unilateral and factorial components by ordered pairing

| P1 vs P2 | U1 | U2 | U | P1 information effect | P2 information effect | interaction (P1 scale) |
|---|---:|---:|---:|---:|---:|---:|
| astra vs astra | +0.100 [+0.00, +0.20] | +0.013 [-0.08, +0.10] | +0.056 [+0.03, +0.09] | +0.044 [-0.01, +0.10] | +0.069 [+0.02, +0.12] | -0.112 [-0.21, +0.00] |
| astra vs fable | +0.000 [-0.05, +0.05] | -0.037 [-0.10, +0.03] | -0.019 [-0.06, +0.02] | +0.006 [-0.04, +0.05] | -0.044 [-0.09, +0.00] | +0.013 [-0.08, +0.10] |
| astra vs qwen | +0.137 [+0.12, +0.15] | -0.013 [-0.08, +0.05] | +0.062 [+0.04, +0.09] | +0.125 [+0.07, +0.18] | -0.000 [-0.06, +0.06] | -0.025 [-0.14, +0.09] |
| fable vs astra | -0.050 [-0.10, +0.00] | +0.075 [-0.05, +0.20] | +0.013 [-0.06, +0.09] | -0.050 [-0.14, +0.04] | +0.075 [-0.01, +0.17] | +0.000 [-0.18, +0.18] |
| fable vs fable | +0.025 [-0.03, +0.08] | +0.062 [-0.05, +0.18] | +0.044 [+0.01, +0.08] | +0.100 [+0.00, +0.20] | -0.013 [-0.11, +0.09] | +0.150 [-0.05, +0.35] |
| fable vs qwen | +0.000 [-0.05, +0.05] | -0.037 [-0.12, +0.05] | -0.019 [-0.09, +0.05] | -0.031 [-0.10, +0.04] | -0.006 [-0.07, +0.06] | -0.062 [-0.20, +0.07] |
| qwen vs astra | +0.100 [+0.05, +0.15] | +0.100 [-0.02, +0.23] | +0.100 [+0.05, +0.15] | +0.056 [-0.01, +0.12] | +0.144 [+0.07, +0.21] | -0.087 [-0.22, +0.05] |
| qwen vs fable | +0.213 [+0.18, +0.25] | -0.125 [-0.17, -0.08] | +0.044 [+0.01, +0.07] | +0.094 [+0.06, +0.14] | -0.006 [-0.04, +0.04] | -0.238 [-0.31, -0.16] |
| qwen vs qwen | +0.000 [-0.15, +0.15] | +0.050 [-0.08, +0.17] | +0.025 [-0.06, +0.11] | -0.025 [-0.14, +0.09] | +0.075 [-0.04, +0.19] | -0.050 [-0.28, +0.17] |

## Behaviour (means over seats; informed vs uninformed, by same/other-model opponent)

| model | opponent | informed | n seats | %ROCK | %PAPER | %SCISSORS | switch % | win-stay % | lose-shift % | tie-shift % | entropy (bits) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| astra | same | False | 8 | 30.0 | 34.4 | 35.6 | 75.0 | 24.8 | 83.4 | 71.4 | 1.5 |
| astra | same | True | 8 | 32.5 | 33.8 | 33.8 | 77.0 | 15.6 | 68.6 | 68.8 | 1.5 |
| astra | other | False | 16 | 34.4 | 31.9 | 33.8 | 69.4 | 38.5 | 76.1 | 68.2 | 1.5 |
| astra | other | True | 16 | 32.8 | 31.6 | 35.6 | 76.3 | 21.2 | 81.1 | 71.9 | 1.5 |
| fable | same | False | 8 | 36.2 | 38.1 | 25.6 | 84.2 | 6.2 | 93.1 | 61.5 | 1.5 |
| fable | same | True | 8 | 33.8 | 35.6 | 30.6 | 81.6 | 4.7 | 76.5 | 66.8 | 1.6 |
| fable | other | False | 15 | 31.0 | 35.3 | 33.7 | 75.8 | 22.0 | 72.6 | 65.5 | 1.5 |
| fable | other | True | 16 | 28.4 | 37.2 | 34.4 | 76.6 | 14.4 | 74.2 | 62.1 | 1.5 |
| qwen | same | False | 8 | 25.0 | 36.2 | 38.8 | 59.2 | 58.3 | 73.9 | 64.9 | 1.5 |
| qwen | same | True | 8 | 32.5 | 36.9 | 30.6 | 63.2 | 49.0 | 63.9 | 74.6 | 1.5 |
| qwen | other | False | 15 | 29.7 | 38.7 | 31.7 | 71.2 | 41.8 | 80.3 | 72.3 | 1.5 |
| qwen | other | True | 16 | 31.2 | 39.7 | 29.1 | 67.4 | 35.4 | 70.4 | 63.7 | 1.5 |

## Prospective history-only predictability (percent; uniform = 33.3)

| model | informed | uniform | expanding_frequency | repeat_last | markov1_smoothed | counter_opponent_last |
|---|---|---:|---:|---:|---:|---:|
| astra | False | 33.3 | 28.4 | 29.0 | 29.9 | 35.4 |
| astra | True | 33.3 | 27.2 | 24.0 | 33.3 | 31.0 |
| fable | False | 33.3 | 26.7 | 21.9 | 34.2 | 31.2 |
| fable | True | 33.3 | 25.9 | 22.3 | 36.7 | 26.2 |
| qwen | False | 33.3 | 29.6 | 33.0 | 34.5 | 44.1 |
| qwen | True | 33.3 | 30.9 | 34.0 | 34.3 | 38.5 |

## Independent rescore

`rescore.py` recomputed V and D from `rounds.csv` without the game-result routine: {"D_rescore": 0.011458333333333343, "n_complete_games": 71, "round_result_mismatches": 0}

## Interpretation boundaries

- Exploratory: 2 games per cell; intervals reflect game-to-game variation within cells; no multiplicity correction across 36 cells.
- Disclosure is always truthful. A self-specific effect is functional use of self-related information, not privileged introspection; model-name priors and skill differences remain alternatives.
- 'Same model' means another independently queried instance with the same name and settings.

