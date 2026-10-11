# Experiment 1 in the hypothesis's own terms: marginals, runs, sequential dependence, win rate (post hoc, 2026-10-11)

Hypothesis as stated: telling a model that its opponent is another instance of itself changes its strategy (because it
simulates the opponent from what it knows about itself), visible as changes in marginal choice frequencies, run
structure and Brown-Rosenthal-style sequential dependence, and reflected in win rate. Script:
`experiment1_sequential_structure.py`; data: the amended Experiment 1 games (72 complete per game type). Groups are
player-games crossed by told x opponent type; contrasts are matched on opponent type and the self-specific effect is
the interaction. Percentile bootstrap over player-games (3,000). Lag-1 dependence is Cramer's V from the pooled
current-choice x lagged-variable table (rounds 2-20), with a G-test p-value.

## All models pooled

| game | group | n | marginals (%) | entropy (bits) | switch % | runs z | V own lag-1 (p) | V opp lag-1 (p) | V outcome lag-1 (p) | V joint lag-1 (p) | payoff |
|---|---|---:|---|---:|---:|---:|---|---|---|---|---:|
| RPS | uninformed_self | 24 | R 30 / P 36 / S 33 | 1.519 | 72.8 | +0.54 | 0.115 (.016) | 0.114 (.016) | 0.060 (.52) | 0.183 (.008) | 0.479 |
| RPS | uninformed_other | 48 | R 32 / P 35 / S 33 | 1.539 | 71.3 | +0.32 | 0.112 (<.001) | 0.128 (<.001) | 0.038 (.63) | 0.169 (<.001) | 0.485 |
| RPS | told_self | 24 | R 33 / P 35 / S 32 | 1.538 | 73.9 | +0.56 | 0.185 (<.001) | 0.110 (.030) | 0.066 (.41) | 0.234 (<.001) | 0.521 |
| RPS | told_other | 48 | R 31 / P 36 / S 33 | 1.528 | 73.5 | +0.57 | 0.181 (<.001) | 0.131 (<.001) | 0.047 (.41) | 0.230 (<.001) | 0.515 |
| MP | uninformed_self | 24 | STAR 53 | 0.987 | 50.2 | -0.13 | 0.007 (.85) | 0.011 (.81) | 0.071 (.12) | 0.028 (.95) | 0.513 |
| MP | uninformed_other | 48 | STAR 51 | 0.988 | 52.5 | +0.06 | 0.050 (.12) | 0.018 (.60) | 0.053 (.11) | 0.063 (.30) | 0.482 |
| MP | told_self | 24 | STAR 50 | 0.987 | 56.6 | +0.44 | 0.132 (.005) | 0.018 (.71) | 0.040 (.40) | 0.162 (.007) | 0.487 |
| MP | told_other | 48 | STAR 48 | 0.981 | 55.5 | +0.38 | 0.112 (.001) | 0.052 (.11) | 0.085 (.010) | 0.132 (.001) | 0.518 |

## Matched contrasts, all models pooled (95% bootstrap intervals)

| game | measure | told_self - uninformed_self | told_other - uninformed_other | self-specific interaction |
|---|---|---|---|---|
| RPS | entropy | +0.019 [-0.020, +0.052] | -0.010 [-0.028, +0.007] | +0.030 [-0.013, +0.066] |
| RPS | switch % | +1.1 [-6.8, +8.3] | +2.2 [-2.4, +6.6] | -1.1 [-10.0, +7.8] |
| RPS | runs z | +0.02 [-0.66, +0.66] | +0.26 [-0.17, +0.65] | -0.24 [-1.02, +0.56] |
| RPS | V own lag-1 | +0.071 [-0.035, +0.156] | +0.070 [-0.005, +0.137] | +0.001 [-0.125, +0.115] |
| RPS | V joint lag-1 | +0.051 [-0.061, +0.155] | +0.061 [-0.012, +0.123] | -0.010 [-0.134, +0.114] |
| RPS | payoff | +0.042 [-0.008, +0.090] | +0.030 [-0.003, +0.063] | +0.011 [-0.047, +0.068] |
| MP | entropy | +0.000 [-0.009, +0.010] | -0.007 [-0.015, +0.001] | +0.007 [-0.005, +0.020] |
| MP | switch % | +6.4 [+0.4, +12.5] | +3.0 [-0.2, +6.1] | +3.4 [-3.2, +10.0] |
| MP | runs z | +0.57 [+0.05, +1.11] | +0.32 [+0.05, +0.59] | +0.26 [-0.34, +0.84] |
| MP | V own lag-1 | +0.124 [-0.002, +0.187] | +0.061 [-0.002, +0.121] | +0.063 [-0.081, +0.147] |
| MP | V joint lag-1 | +0.134 [-0.021, +0.209] | +0.069 [-0.014, +0.137] | +0.065 [-0.104, +0.162] |
| MP | payoff | -0.025 [-0.075, +0.027] | +0.035 [-0.000, +0.072] | -0.060 [-0.121, +0.002] |

Per-model interactions are in `contrasts.csv`; none is resolved except Qwen's MP payoff (-0.147 [-0.263, -0.019]),
which carries the make-up selection caveat.

## Reading

1. Marginals do not move. All groups are near-uniform (RPS entropy 1.52-1.54 of 1.585 bits; MP 48-53% STAR).
2. Runs: LLMs over-alternate in RPS in every condition (switch 71-74% vs 67% for random play; runs z +0.3 to +0.6)
   and disclosure does not change that. In MP, uninformed play is at the random switch rate (50-52%) and disclosure
   pushes it toward over-alternation (+6.4 pp told-self, +3.0 told-other).
3. Sequential dependence: RPS play is Brown-Rosenthal-dependent in every condition (joint lag-1 V 0.17-0.23, all
   p < 0.01), and being told any opponent's identity makes it more dependent on the player's own previous move
   (V 0.11 -> 0.18, the same +0.07 for self and other). Uninformed MP play shows no detectable lag-1 dependence
   (joint V 0.03, p 0.95); told MP play does (V 0.13-0.16, p < 0.01). Play becomes more patterned when told, not less.
4. Win rate: in RPS, told players gain 0.03-0.04 over their untold opponents whether the opponent is self or other.
   In MP the pooled interaction is -0.06 [-0.12, +0.00], all of it Qwen.
5. Nothing is self-specific. Every interaction interval includes zero, and the point estimates are small relative to
   the matched disclosure effects. With 8 player-games per self cell the design resolves interactions of roughly
   +/-8 pp in switch rate, +/-0.12 in V and +/-0.06 in payoff.
