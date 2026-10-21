# 05 · Study 1, Experiment 1: telling three models who their opponent is (2026-10-10)

| | |
|---|---|
| Track | 2 — game theory (complementary to track 1) |
| Run IDs | `rps3m-p2-20261010` (RPS) and `mp3m-p2-20261010` (MP), each with a `with_makeups/` amended analysis; `superseded/rps3m-20261009T1240Z` (frozen, never run) |
| Game and models | RPS and matching pennies (MP), 20 rounds, analysed separately. Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), Qwen (`qwen/qwen3.8-27b`); reasoning effort low, no temperature control |
| Size and cost | Per game type: 3 models × 9 ordered pairings × 4 conditions × 2 games = 72 games. Calls including make-ups: 2,906 (RPS) and 3,746 (MP). Cost: $49.97 in total, of which $7.38 was make-ups (caps $60 per game type) |
| Previous / next | [← Opponent-disclosure pilot](../04_2026-10-09_opponent_disclosure_pilot/) · [Experiment 2: Blind Twin judges →](../06_2026-10-10_exp2_blind_twin_judges/) |

## What was done

This scales up the Astra-only disclosure pilot ([04](../04_2026-10-09_opponent_disclosure_pilot/)) to three models.

**Treatment.** Each player is told its own identity. It is also given one line with either its opponent's true model name or "not disclosed".

**Conditions.**
- 00: neither player told
- 10: Player 1 told
- 01: Player 2 told
- 11: both told

In MP, Player 1 is always the Matcher.

**Primary contrast.** D = mean over models of (S_i − O_i), in payoff units. S_i is model i's gain from being told when the opponent is itself; O_i is its gain when the opponent is another model.

**Approval and design history.** The design was approved on 10-10 with $60 hard caps. An earlier eight-games-per-cell RPS cohort (`superseded/rps3m-20261009T1240Z`) had been frozen on 10-09. It was never run and was superseded, not resized.

**Make-up games.** Qwen sometimes ended its answer in markdown bold (`**PAPER**`), which the frozen parser rejects. This interrupted 1 RPS game and 18 MP games. On Chris's instruction, each interrupted game was replaced by a fresh game in the same cell under the unchanged protocol, with the rules fixed before the first make-up call. This took 42 attempts.

The amended analysis (72 complete games per type) is in each run's `with_makeups/` folder. The original raw files are unchanged.

## Questions

- Does being told the opponent's identity help a player more when the opponent is itself than when it is another model (D > 0)?
- Is any such effect consistent across models and across the two games?

## Results

| Game | D [95% CI] | D_Astra | D_Fable | D_Qwen |
|---|---|---|---|---|
| RPS | +0.011 [−0.027, +0.052] | −0.022 | +0.113 [+0.056, +0.169] | −0.056 |
| MP | −0.060 [−0.100, −0.023] | −0.012 | −0.012 | −0.156 [−0.238, −0.081] |

- **RPS:** no overall self-specific disclosure effect. Fable's D is positive. The week record notes that this comes mostly from Fable playing *worse* when told it faced Astra or Qwen, not from playing better against itself.
- **MP:** D is negative and driven by Qwen. Fable's RPS pattern does not replicate in MP.
- **Qwen selection.** Qwen's MP invalid rate depended on disclosure: 3.6% when told its opponent versus 1.8% when not (30/825 vs 11/627). Complete informed Qwen games are therefore a selected subset, which can bias D_Qwen and D_MP.
- **Intervals are too narrow.** With 2 games per cell, a whole-game bootstrap understates uncertainty. A random-play null simulation in the week record gives a null SD of D of 0.032 (RPS) and 0.040 (MP), against a bootstrap-implied 0.020.
- **Analysis deviation, reported and not repaired.** The frozen contrast code required all four cells per pairing. `src/experiment1_derived.py` applies the handoff's rule, which needs only 00/10/01.

## Open questions

- Is Fable's RPS D about self-recognition, or about reacting to the *names* of other models?
- How much of the MP result is Qwen's format-dependent attrition?
- A test of these questions needs more than 2 games per cell. It also needs a parser that tolerates one layer of markdown emphasis for all models.

## What it led to

- The 36 games in condition 00 (no one told) became the stimulus set for Experiment 2, where three judges predict the players ([06](../06_2026-10-10_exp2_blind_twin_judges/)).
- The 24 self-self games in conditions 00 and 11 were used for the self-self judging pilot ([07](../07_2026-10-11_selfself_judges_and_retest/)).
- The full amended logs were re-analysed offline for strategy changes ([08](../08_2026-10-11_post_hoc_analyses/)).

## Files

- Main report: [`docs/STUDY1_EXPERIMENT1_REPORT.md`](docs/STUDY1_EXPERIMENT1_REPORT.md), including the make-up amendment
- Other docs:
  - [`docs/EXPERIMENT1_MAKEUP_GAMES.md`](docs/EXPERIMENT1_MAKEUP_GAMES.md): make-up rules and log
  - [`docs/EXPERIMENT1_BUDGET_AND_APPROVAL.md`](docs/EXPERIMENT1_BUDGET_AND_APPROVAL.md)
  - [`docs/EXPERIMENT1_STATUS.md`](docs/EXPERIMENT1_STATUS.md)
- RPS run: [`rps3m-p2-20261010/`](rps3m-p2-20261010/)
  - [`REPORT.md`](rps3m-p2-20261010/REPORT.md) (original games) and [`with_makeups/REPORT.md`](rps3m-p2-20261010/with_makeups/REPORT.md) (amended)
  - `APPROVAL.md`, `frozen_manifest.json`, `protocol.md`
  - `calls.jsonl`, `game_logs.jsonl`, `makeup_*.jsonl`, `rounds.csv`, `derived_contrasts.csv`
- MP run: [`mp3m-p2-20261010/`](mp3m-p2-20261010/)
  - [`REPORT.md`](mp3m-p2-20261010/REPORT.md) (original games) and [`with_makeups/REPORT.md`](mp3m-p2-20261010/with_makeups/REPORT.md) (amended)
  - `manifest.json`, then the same kinds of files as RPS
- Superseded cohort: [`superseded/rps3m-20261009T1240Z/`](superseded/rps3m-20261009T1240Z/) (0 calls)
- Code:
  - [`src/opponent_disclosure_rps_3models/`](../../src/opponent_disclosure_rps_3models/)
  - [`src/opponent_disclosure_mp_3models/`](../../src/opponent_disclosure_mp_3models/)
  - [`src/experiment1_makeup.py`](../../src/experiment1_makeup.py)
  - [`src/experiment1_derived.py`](../../src/experiment1_derived.py)
- Tests: [`tests/test_rps_disclosure_3models.py`](../../tests/test_rps_disclosure_3models.py), [`tests/test_mp_disclosure_3models.py`](../../tests/test_mp_disclosure_3models.py)
- Background: [`docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md`](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md), section 3.2

## Re-running

Run these from the repo root:

```
PYTHONPATH=src python -m opponent_disclosure_rps_3models analyze --run rps3m-p2-20261010   # no API calls
PYTHONPATH=src python -m opponent_disclosure_mp_3models  analyze --run mp3m-p2-20261010
PYTHONPATH=src python src/experiment1_makeup.py rps --combine-only    # rebuild with_makeups/ from logged games
PYTHONPATH=src python src/experiment1_makeup.py mp  --combine-only
PYTHONPATH=src python src/experiment1_derived.py                      # handoff-definition D and partial-game sensitivity
PYTHONPATH=src python -m pytest -q tests/test_rps_disclosure_3models.py tests/test_mp_disclosure_3models.py
```

- **Subcommands:** `plan`, `validate`, `fake`, `smoke`, `run` and `analyze`.
- **Writes.** `analyze` and `--combine-only` rewrite the reports and CSVs in place.
- **Live runs** (`smoke` and `run` with `--live`) need `OPENROUTER_API_KEY` and an approval line in the run's `APPROVAL.md`.
- **Code hash.** Live runs also check the code hash and schedule hash against the frozen manifest. The 2026-10-21 path edits changed the code hash, so these runs cannot be resumed as they stand. See [`docs/REORGANISATION_2026-10-21.md`](../../docs/REORGANISATION_2026-10-21.md) and [`docs/PATH_MAP.md`](../../docs/PATH_MAP.md).
