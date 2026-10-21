# 08 · Post-hoc analyses of the strategic-game logs (2026-10-11)

| | |
|---|---|
| Track | 2 — game theory (complementary to track 1) |
| Run IDs | Offline; no run IDs. Four analysis folders: `experiment1_strategy_measures/`, `experiment1_sequential_structure/`, `experiment2_by_opponent/`, `experiment2_observation_equivalence/` |
| Game and models | Amended Study 1 games (72 RPS + 72 MP, Astra / Fable / Qwen3.8-27B) and the Experiment 2 judge predictions (`btx1-20261010`) |
| Size and cost | No API calls; $0 |
| Previous / next | [← Self-self judges and retest](../07_2026-10-11_selfself_judges_and_retest/) · [PACA believed-self pilot →](../09_2026-10-11_paca_believed_self/) |

## What was done

After the retest set a noise floor ([07](../07_2026-10-11_selfself_judges_and_retest/)), no new games were collected. The existing logs were analysed offline instead, in four exploratory, post-hoc analyses.

1. **Strategy measures** (`experiment1_strategy_measures/`). Does being told the opponent is a copy make a player:
   - harder for a history-only n-gram predictor to predict (defensive), or
   - more likely to counter what its own model's predictor says the opponent will do (offensive)?

   Groups cross "told / not told" with "opponent self / other". The self-specific effect is the interaction. An addendum adds log-loss versions of the measures and a judge-based "expectation alignment" matrix.
2. **Sequential structure** (`experiment1_sequential_structure/`). The same question, asked of:
   - marginal choice frequencies;
   - runs;
   - Brown–Rosenthal lag-1 dependence;
   - win rate.
3. **Self-advantage by opponent** (`experiment2_by_opponent/`). Splits Experiment 2's self-judge advantage by the target player's opponent. `ROBUSTNESS_round1.md` checks round 1 and later round bins separately.
4. **Observation equivalence** (`experiment2_observation_equivalence/`). Trains a backoff 2-gram predictor on k logged games of the target (or of the other models only). It reports the k at which the predictor matches the LLM judges.

## Questions

- Does being told it faces itself change *how* a model plays, beyond payoff?
- Where does Fable's labelled self-prediction advantage in Experiment 2 come from?
- How much is that advantage worth, measured in games of observation?

## Results

- **No self-specific change in play.** Every told × opponent-type interaction includes zero, on predictability, alignment, log loss, marginals, runs and lag-1 dependence, in both games. With 8 player-games per self cell, these interactions can resolve only effects of about ±8 pp.
- **There is a general effect of naming any opponent, in RPS only.** Told any opponent's name, players countered that model's tendencies about 5.5 pp more (34.3 → 39.8%) [+1.4, +9.9]. They were somewhat less predictable, and gained about 0.04 payoff. Being told also made play *more* dependent on the player's own previous move.
- **Pooled baselines can manufacture a self effect.** Contrasting told-self with *all* uninformed games gives a spurious +14.6 pp "self-specific" effect for Fable. It vanishes against uninformed self-pairings (45.6 → 46.9).
- **Fable's self-advantage lives in its games against other models.** With the TRUE label, Fable beats the other judges on Fable players:
  - vs Astra: +14.6 (RPS) / +16.3 (MP)
  - vs Qwen: +9.8 / +13.8
  - vs Fable: only +3.1 / +0.7

  Self-self games are the condition every judge predicts worst.
- **The RPS label effect is partly an opening-round effect.** Dropping round 1 moves RPS S from +1.8 to +1.0.
- **A simple classifier beats the LLM judges.** A 2-gram predictor trained on about 47 other games of the same model beats every LLM judge on every target. One trained only on the *other* models' games beats every judge in RPS, and every judge except Fable-on-Fable in MP.
- **Observation equivalence.**
  - Fable's labelled self-prediction is worth about 32 (RPS) and 24 (MP) of its own logged games to the 2-gram predictor, and more than 47 games of the other models' play.
  - Under ANONYMOUS it is worth about 2–3 (RPS) and 16 (MP) games.
  - Astra's labelled self-prediction is worth about 16 (RPS) and 5 (MP) games.
  - The n-gram is a weak learner, so these k values are upper bounds.

**Reading.** Where self-knowledge appears, it is cued and belongs to one model (Fable). It looks like knowledge of its own conventions, worth tens of games of observation, not privileged access.

## Open questions

- Would a stronger classifier, or outsiders given k of the target's games in context, close the gap with fewer games?
- Is the general RPS "named opponent" effect robust under probability elicitation?
- Does Fable's advantage reflect something about Fable's training, rather than about language models in general?

## What it led to

- **Framing, given to the mentor** (week record, section 8):
  - negative on non-cued self-knowledge;
  - weakly positive on cued, functional self-modelling for one model.
- **Next steps.** The track moved to manipulations of believed identity in an adaptive task. These were the PACA believed-self pilot ([09](../09_2026-10-11_paca_believed_self/)) and then closed-loop self-play ([10](../10_2026-10-20_paint_circle_selfplay/)).

## Files

- [`experiment1_strategy_measures/REPORT.md`](experiment1_strategy_measures/REPORT.md), plus `group_means.csv`, `contrasts.csv`, `player_games.csv`, `classifier_floor_condition00.csv`, `expectation_alignment_condition00.csv`
- [`experiment1_sequential_structure/REPORT.md`](experiment1_sequential_structure/REPORT.md), plus `group_summary.csv`, `contrasts.csv`, `player_games.csv`, `console_output.txt`
- [`experiment2_by_opponent/REPORT.md`](experiment2_by_opponent/REPORT.md), [`ROBUSTNESS_round1.md`](experiment2_by_opponent/ROBUSTNESS_round1.md), `self_advantage_by_opponent.csv`
- [`experiment2_observation_equivalence/REPORT.md`](experiment2_observation_equivalence/REPORT.md), `learning_curve.csv`
- Scripts:
  - [`src/experiment1_post_hoc_strategy.py`](../../src/experiment1_post_hoc_strategy.py)
  - [`src/experiment1_sequential_structure.py`](../../src/experiment1_sequential_structure.py)
  - [`src/experiment2_observation_equivalence.py`](../../src/experiment2_observation_equivalence.py)
  - No script for `experiment2_by_opponent/` is in the repository.
- Background: [`docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md`](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md), sections 3.4, 3.5, 3.8, 4 and 8

## Re-running

Run these from the repo root:

```
PYTHONPATH=src python src/experiment1_post_hoc_strategy.py
PYTHONPATH=src python src/experiment1_sequential_structure.py
PYTHONPATH=src python src/experiment2_observation_equivalence.py
```

- **No API key needed.** The scripts read the amended Study 1 logs in folder [05](../05_2026-10-10_study1_exp1_disclosure/) and the Experiment 2 predictions in folder [06](../06_2026-10-10_exp2_blind_twin_judges/).
- **Writes.** They rewrite the CSV outputs in the matching folder here, and print a console summary. Only the observation-equivalence script regenerates its `REPORT.md`; the other `REPORT.md` files were written by hand from the outputs.
- **Paths.** They locate files through `src/repo_paths.py`. See [`docs/PATH_MAP.md`](../../docs/PATH_MAP.md) and [`docs/REORGANISATION_2026-10-21.md`](../../docs/REORGANISATION_2026-10-21.md).
