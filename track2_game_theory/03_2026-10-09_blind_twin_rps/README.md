# 03 · Blind Twin in rock-paper-scissors: three model pairs (2026-10-09)

| | |
|---|---|
| Track | 2 — game theory (complementary to track 1) |
| Run IDs | `rps-20261009T1024Z` (Astra–Fable), `rps-qf-20261009T1045Z` (Qwen–Fable), `rps-qa-20261009T1124Z` (Qwen–Astra); `_preflight/` |
| Game and models | Rock-paper-scissors (RPS), 20 rounds, chance 33.3%. Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), Qwen (`qwen/qwen3.8-27b`, Alibaba endpoint); reasoning effort low, no temperature control |
| Size and cost | Each run has 12 games, 480 player calls and 1,440 judge calls. Cost per run, including smoke: $15.64 (A–F), $11.82 (Q–F), $7.69 (Q–A); $35.15 in total (cap $25 per run) |
| Previous / next | [← Blind Twin v2 (MP)](../02_2026-10-09_blind_twin_v2_mp/) · [Opponent-disclosure pilot →](../04_2026-10-09_opponent_disclosure_pilot/) |

## What was done

This applies the Blind Twin v2 design ([02](../02_2026-10-09_blind_twin_v2_mp/)) to rock-paper-scissors.

**Unchanged from v2:**
- four ordered matchups × 3 games × 20 rounds;
- two judges (the two playing models) predicting both players' next moves under TRUE, FALSE and ANONYMOUS labels;
- brief reasoning allowed, with the move alone on the final line;
- the same indices S (TRUE vs ANONYMOUS, self-specific) and S_false (TRUE vs FALSE).

**Changed for RPS:** the seats are symmetric (Player A and Player B), there are three moves, and the history-only baselines are adapted to RPS.

**Three runs, one per model pair.** The first used Astra–Fable. Qwen was added to give a third model, first paired with Fable and then with Astra.

**Preflight.** `_preflight/` holds a 5-call Qwen3.8 determinism check. It was used to decide whether to send a seed to Qwen.

## Questions

- Does the v2 matching-pennies result (S = +4.2) carry over to a three-move game?
- Is any self-specific label effect general, or tied to one model?

## Results

| Run | S (TRUE vs ANON) | S_false (TRUE vs FALSE) | Self cells T / F, model 1 | Self cells T / F, model 2 |
|---|---|---|---|---|
| Astra–Fable | −2.7 [−4.6, −0.8] | +0.6 [−3.1, +4.0] | Astra +2.5 / +1.7 | Fable +4.2 / +4.2 |
| Qwen–Fable | +5.7 [+1.2, +10.9] | +6.3 [+3.2, +9.8] | Qwen +0.4 / −1.2 | Fable +6.9 / +7.6 |
| Qwen–Astra | +4.4 [−2.3, +11.7] | +8.1 [+3.5, +13.1] | Qwen −1.2 / −0.4 | Astra +6.2 / +7.1 |

- **Completion:** all 36 games were complete. Five judge predictions were invalid in the Q–F run, and none in the other runs.
- **S** was positive in two of the three runs. **S_false** was positive in all three.
- **Fable's self cells** were positive in both runs that include Fable. The week record names Fable's self cells as the consistent positive contributor across the five Oct 9 Blind Twin runs (01–03).
- **Astra's self cells** were positive against Qwen, but small and uncertain in the Astra–Fable run.
- **Qwen's self cells** were near zero in both runs.
- **Interval width.** All intervals come from a game-level bootstrap of 3 games per matchup.

## Open questions

- Is Fable's apparent self-advantage self-knowledge, or does Fable simply play a crisper, more conventional policy that is easier to predict once named?
- Does a TRUE label help with a model's own moves in particular, or only with "which model is this"? The FALSE label partly separates these.
- Would the pattern hold with more games, more judges, and games in which neither player was told anything?

## What it led to

The Oct 9 Blind Twin runs set the per-call costs and the harness used later. The same day, the opponent-disclosure pilot ([04](../04_2026-10-09_opponent_disclosure_pilot/)) asked the other direction: does telling a *player* that its opponent is itself change how it plays?

Blind Twin judging was later repeated at scale with three judges on the Study 1 game logs ([06](../06_2026-10-10_exp2_blind_twin_judges/)).

## Files

- Run folders: [`rps-20261009T1024Z/`](rps-20261009T1024Z/), [`rps-qf-20261009T1045Z/`](rps-qf-20261009T1045Z/), [`rps-qa-20261009T1124Z/`](rps-qa-20261009T1124Z/)
  - Each contains `report.md`, `predictions.csv`, `by_game.csv`, `breakdown.csv`, `responsiveness.csv`, `baseline_scores.csv`, `results.json`, `figures/`, raw `calls.jsonl` and `game_logs.jsonl`, `config.json`, `freeze.json` and `approvals.jsonl`.
- Reports: [A–F](rps-20261009T1024Z/report.md), [Q–F](rps-qf-20261009T1045Z/report.md), [Q–A](rps-qa-20261009T1124Z/report.md)
- Preflight: [`_preflight/qwen38_determinism_20261009.json`](_preflight/qwen38_determinism_20261009.json)
- Code: [`src/blind_twin_rps/`](../../src/blind_twin_rps/), including `protocol.md` and `templates/`
- Tests: [`tests/test_blind_twin_rps.py`](../../tests/test_blind_twin_rps.py)
- Background: [`docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md`](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md), sections 1 and 3.1

## Re-running

Run these from the repo root. The model pair comes from the `BT_MODELS` environment variable (default `astra,fable`).

```
PYTHONPATH=src python -m blind_twin_rps analyze --run rps-20261009T1024Z                         # no API calls
PYTHONPATH=src BT_MODELS=qwen,fable python -m blind_twin_rps analyze --run rps-qf-20261009T1045Z
PYTHONPATH=src BT_MODELS=qwen,astra python -m blind_twin_rps analyze --run rps-qa-20261009T1124Z
PYTHONPATH=src python -m blind_twin_rps fake --run <new-id>                                      # offline
PYTHONPATH=src BT_MODELS=<m1>,<m2> python -m blind_twin_rps run --run <new-id> --live
PYTHONPATH=src python -m pytest -q tests/test_blind_twin_rps.py
```

- **Subcommands:** `fake`, `smoke`, `smoke-games`, `run` and `analyze`.
- **Live runs** need `OPENROUTER_API_KEY`. There is no `APPROVAL.md` gate; caps are in `config.py` and `approvals.jsonl`.
- **Code hash.** `run` refuses to resume a run whose stored code hash differs from the current code. The 2026-10-21 path edits changed that hash. See [`docs/REORGANISATION_2026-10-21.md`](../../docs/REORGANISATION_2026-10-21.md) and [`docs/PATH_MAP.md`](../../docs/PATH_MAP.md).
