# Experiment 1 post hoc strategy measures (exploratory, 2026-10-11)

Offline re-analysis of the amended Experiment 1 games (72 complete RPS, 72 complete MP, `with_makeups/rounds.csv`),
following the "offensive / defensive self-modelling" proposal of 2026-10-11. No API calls. Post hoc; not a
replacement for the pre-registered payoff endpoint. Script: `experiment1_post_hoc_strategy.py`. Unit: player-game
(one seat of one game, 20 rounds). Groups cross what the player was told with the opponent type, so every contrast is
matched on opponent type; the self-specific effect is the told x opponent-type interaction.

Per player model and game type: uninformed_self 8, uninformed_other 16, told_self 8, told_other 16 player-games.

## Measures

- **Defensive (predictability):** accuracy of a history-only backoff n-gram predictor (contexts up to the last two
  own/opponent moves and the last result; argmax at the most specific context with >= 8 training observations) on the
  player's own moves. Predictor A is trained on all other games of the same model, leave-one-game-out, and applied
  unchanged to every group. Predictor B is trained within group with the training set equalised at 7 player-games.
  Lower = harder to predict. Chance RPS 33.3, MP 50.0.
- **Offensive (counter-prediction alignment):** share of rounds in which the player's move is the best response to
  the move a history-only predictor forecasts for the opponent (RPS: beats it; MP: Matcher matches, Mismatcher
  mismatches). The opponent's move is forecast either by the true opponent model's predictor (`align_opp_model`) or by
  the player's own model's predictor, i.e. what a copy of the player would do (`align_own_model`). In self-pairings
  these coincide. Chance RPS 33.3, MP 50.0.

## Matched contrasts, all models pooled (percentage points; 95% percentile bootstrap over player-games)

| game | metric | told_self - uninformed_self | told_other - uninformed_other | self-specific (interaction) |
|---|---|---|---|---|
| RPS | predictability A | -3.1 [-9.4, +3.3] | -3.2 [-7.7, +0.9] | +0.1 [-7.6, +8.1] |
| RPS | predictability B (equalised) | -2.9 [-9.6, +4.2] | +0.5 [-3.0, +4.0] | -3.4 [-11.0, +4.8] |
| RPS | alignment, opponent-model predictor | +2.1 [-4.4, +9.2] | +5.5 [+1.4, +9.9] | -3.4 [-11.2, +4.4] |
| RPS | alignment, own-model predictor | +2.1 [-4.6, +8.5] | +5.8 [+1.1, +10.3] | -3.8 [-11.8, +4.2] |
| MP | predictability A | +1.2 [-4.8, +7.7] | +1.1 [-4.1, +6.2] | +0.1 [-7.9, +8.2] |
| MP | predictability B (equalised) | -0.4 [-7.5, +6.7] | +3.1 [-0.0, +6.3] | -3.5 [-11.2, +4.1] |
| MP | alignment, opponent-model predictor | +2.1 [-3.8, +7.5] | +2.0 [-2.5, +6.5] | +0.1 [-7.3, +7.2] |
| MP | alignment, own-model predictor | +2.1 [-3.8, +7.9] | +0.9 [-3.6, +5.5] | +1.1 [-6.5, +8.3] |

Self-pairing games only (uninformed_self vs told_self; n = 8 vs 8 per cell): alignment to a copy of oneself, RPS:
Astra 31.9 -> 36.2, Fable 45.6 -> 46.9, Qwen 30.0 -> 30.6; MP: Astra 43.8 -> 41.9, Fable 55.0 -> 51.9, Qwen 42.5 -> 53.8.
Predictability A, RPS: Astra 61.9 -> 53.1, Fable 50.6 -> 55.6, Qwen 48.8 -> 43.1; MP: 68.8 -> 69.4, 66.2 -> 66.9,
58.1 -> 60.6. Full tables: `group_means.csv`, `contrasts.csv`, `player_games.csv`.

## Findings

1. **No self-specific deployment on either measure, in either game.** Every interaction interval includes zero and
   the point estimates are near zero or negative. Being told the opponent is a copy of oneself did not make players
   harder to predict, and did not make them counter their own model's tendencies more than they already do in
   uninformed self-pairings.
2. **A general disclosure effect in RPS only:** when told the opponent's identity, players countered that opponent
   model's tendencies about 5.5 pp more often than matched uninformed players (34.3 -> 39.8; chance 33.3), and were
   about 3 pp less predictable, with the same size whether the named opponent was self or other. Payoff rose by
   0.04 in both told groups. Nothing comparable in MP.
3. **Caution on pooled baselines.** Contrasting told_self against all uninformed games (regardless of opponent) gives
   a spurious "self-specific" alignment gain of +14.6 pp for Fable in RPS. It disappears when the baseline is
   restricted to uninformed self-pairings (45.6 -> 46.9), because in a self-pairing countering the opponent's
   observed tendencies and countering one's own model's tendencies are the same thing. Any future version of these
   measures must match on opponent type.
4. **Calibration of the Experiment 2 judges against a history classifier.** On the condition-00 games that
   Experiment 2 judged, stratified as in Experiment 2:

   | game | target | A: same-model n-gram | C: other-models-only n-gram | best LLM judge (TRUE label) | self-judge TRUE / ANON |
   |---|---|---:|---:|---:|---|
   | RPS | Astra | 55.8 | 50.4 | 43.8 (Astra) | 43.8 / 40.0 |
   | RPS | Fable | 55.8 | 55.0 | 53.4 (Fable) | 53.4 / 45.0 |
   | RPS | Qwen | 49.2 | 49.2 | 46.3 (Fable) | 37.5 / 38.8 |
   | MP | Astra | 68.3 | 60.4 | 58.3 (Astra, Fable) | 58.3 / 55.0 |
   | MP | Fable | 70.8 | 58.8 | 65.0 (Fable) | 65.0 / 62.1 |
   | MP | Qwen | 53.8 | 62.5 | 57.5 (Fable) | 56.7 / 58.3 |

   A 2-gram predictor trained on about 47 other games of the target model beats every LLM judge on every target; a
   predictor trained only on the *other* models' games (generic LLM play, no target-model data) beats every LLM judge
   in RPS and all but Fable-on-Fable in MP. Fable's labelled self-prediction is the only judge result at the level of
   the same-model classifier (RPS) or above the generic one (MP). Most of the exploitable structure in these games is
   shared across models (C close to A in RPS); the model-specific part is largest for Astra and Fable in MP.

## Limits

- Eight player-games per self cell; the interaction intervals are about +/- 8 pp wide, so effects below that are
  undetectable here.
- The predictor is a fixed-form n-gram, not an optimised classifier; it bounds predictability from below.
- Qwen's MP games carry the make-up selection caveat (EXPERIMENT1_MAKEUP_GAMES.md).
- The offensive measure uses a statistical stand-in for "what the player expects its twin to do". The judge-based
  version (the player's own model as Blind Twin judge, TRUE label, on the informed games) was not run: Experiment 2
  judged only condition-00 games. It would need about 1,440 new judge calls per game type (the informed player's own model as judge, TRUE
  label, 54 informed games, two judges for the 18 condition-11 games), roughly $8-10 per game type.

## Addendum (2026-10-11, morning): log-loss version and the judge-based alignment matrix

Added after a second, independent analysis (logistic classifier, held-out games, log loss) reported self-specific
defensive effects in RPS of +0.20 (Astra), +0.11 (Fable), +0.11 (Qwen) nats and small negative values in MP, without
uncertainty, and judge-based alignment of 75.4% (MP) and 53.8% (RPS) for Astra players against the Astra judge's
TRUE-label forecasts on the condition-00 games.

**Log loss (nats per round; positive = harder to predict when told).** Interpolated-backoff probabilities from the
same n-gram predictor, matched contrasts as above. `logloss_A` is model-specific (trained on the same model's other
games); `logloss_pooled` is trained on all models' games with no model identity, the external analysis's setup.

| game | predictor | told_self − uninformed_self | told_other − uninformed_other | self-specific interaction |
|---|---|---|---|---|
| RPS | model-specific | +0.094 [+0.016, +0.166] | +0.060 [+0.012, +0.109] | +0.033 [−0.059, +0.123] |
| RPS | pooled, no identity | +0.072 [−0.004, +0.144] | +0.058 [+0.012, +0.106] | +0.014 [−0.073, +0.104] |
| MP | model-specific | +0.002 [−0.062, +0.063] | −0.015 [−0.059, +0.027] | +0.017 [−0.058, +0.094] |
| MP | pooled, no identity | −0.005 [−0.056, +0.043] | +0.002 [−0.028, +0.034] | −0.007 [−0.066, +0.048] |

Per-model RPS interactions (model-specific predictor): Astra −0.007 [−0.162, +0.140], Fable +0.054 [−0.097, +0.200],
Qwen +0.053 [−0.092, +0.195]. The external point estimates lie inside these intervals. Both analyses therefore agree
on a general disclosure effect in RPS (play becomes harder to predict when the opponent is named, self or other) and
on nothing in MP; neither can distinguish the self-specific component from zero with eight player-games per self cell.

**Judge-based expectation alignment** (`expectation_alignment_condition00.csv`): share of rounds in which the player's
move is the best response to a judge's forecast of the opponent, condition-00 games only. The 75.4% and 53.8% figures
reproduce exactly (Astra judge, Astra player, TRUE label). The full matrix shows the measure is not self-specific: in
RPS the Astra judge's forecasts align with Fable players (59.6 TRUE, 65.0 ANONYMOUS) more than with Astra players
(53.8, 60.4), and the Qwen judge aligns with Astra and Fable players at 55-64. Same-model vs other-model judge under
ANONYMOUS: RPS 54.5 vs 53.1, MP 69.2 vs 63.7 (the MP gap is mostly Astra-Astra, 78.3). High values arise when the
judge's forecast heuristic for the opponent and the player's own heuristic are the same history rule (for example
"opponent repeats" and "counter the opponent's last move"), so this is a shared-heuristic measure. It cannot test the
offensive hypothesis until the informed games are judged.
