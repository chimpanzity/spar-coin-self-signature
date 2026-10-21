# 02 · Blind Twin v2: self-prediction in matching pennies with a final-line parser (2026-10-09)

| | |
|---|---|
| Track | 2 — game theory (complementary to track 1) |
| Run IDs | `bt2-20261009T0957Z` |
| Game and models | Matching pennies (MP), 20 rounds. Players and judges: Astra (`openai/gpt-6-astra`) and Fable (`anthropic/claude-fable-5.1`), reasoning effort low, no temperature control |
| Size and cost | 12 games (4 ordered matchups × 3); 480 player calls + 1,440 judge calls; $15.17 including $0.90 smoke (cap $25) |
| Previous / next | [← Blind Twin v1](../01_2026-10-09_blind_twin_v1_mp/) · [Blind Twin RPS →](../03_2026-10-09_blind_twin_rps/) |

## What was done

This run repeats the v1 design ([01](../01_2026-10-09_blind_twin_v1_mp/)) as a new run, with one protocol change.

**The change.** In v1, Fable's habit of writing a sentence of reasoning before its move broke the strict parser. Players are now told: "You may briefly think through your choice. End your response with the chosen shape (STAR or TRIANGLE) alone on the final line." The parser (`bt_v2_final_line`) accepts an answer if its last non-empty line is exactly one shape.

**Unchanged from v1:**
- judges, labels (TRUE / FALSE / ANONYMOUS) and indices;
- 3 games per matchup, 20 rounds each.

## Questions

- With complete games, does a TRUE identity label help a judge predict its own model more than it helps the other judge (S)?
- Does a FALSE label cost more on the judge's own model (S_false)?

## Results

- **Completion:** all 12 games were complete, and all 480 player answers were valid. Of the 1,440 judge predictions, 1,439 were valid.
- **S = +4.2 [+0.4, +8.5]; S_false = +4.4 [+1.7, +7.1].** This is the opposite sign to v1's S (−2.2). The intervals come from a game-level bootstrap with 3 games per matchup, so they reflect game-to-game variation only.
- **Fable's self cells were positive:** T[fable,fable] = +3.3 [+1.2, +5.4] and F[fable,fable] = +3.3 [+0.4, +6.7]. Astra's were T[astra,astra] = +3.3 [−1.3, +8.8] and F[astra,astra] = +1.2 [−2.1, +4.2].
- **Label sensitivity:** judges changed their prediction between labels on about 5–28% of paired items. Fable changed most when predicting the Mismatcher.
- **Accuracy (equal-weight, chance 50%):** 55.7–62.8% across the judge × player × label cells.

## Open questions

- Is the positive S specific to matching pennies, or does it hold in a game with three moves and a lower chance rate?
- Is the effect carried by one model? Fable's self cells were the more consistent ones here.
- How much of it is noise? Twelve games and single sampled predictions per item do not settle that.

## What it led to

The same harness was ported to rock-paper-scissors and run three times with different model pairs ([03](../03_2026-10-09_blind_twin_rps/)). The per-call costs from these runs set the budgets of every later track-2 run.

## Files

- Run folder: [`bt2-20261009T0957Z/`](bt2-20261009T0957Z/)
  - [`report.md`](bt2-20261009T0957Z/report.md): main report
  - `predictions.csv`, `by_game.csv`, `breakdown.csv`, `responsiveness.csv`, `baseline_scores.csv`, `player_behaviour.csv`, `results.json`, `figures/`
  - raw `calls.jsonl` and `game_logs.jsonl`
  - `config.json` and `freeze.json`: the frozen configuration and code hash
  - `approvals.jsonl`
- Code: [`src/blind_twin/`](../../src/blind_twin/), including `protocol.md` and `templates/`
- Tests: [`tests/test_blind_twin.py`](../../tests/test_blind_twin.py)
- Background: [`docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md`](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md), sections 1 and 3.1

## Re-running

Run these from the repo root. The package defaults to v2, and runs are written to this folder.

```
PYTHONPATH=src python -m blind_twin analyze --run bt2-20261009T0957Z   # re-score from logged calls (rewrites report.md and CSVs); no API calls
PYTHONPATH=src python -m blind_twin fake    --run <new-id>             # offline end-to-end, fake client
PYTHONPATH=src python -m blind_twin smoke   --run <new-id> --live      # 4 technical calls
PYTHONPATH=src python -m blind_twin run     --run <new-id> --live      # games -> freeze -> judges -> analysis
PYTHONPATH=src python -m pytest -q tests/test_blind_twin.py
```

- **Live runs** need `OPENROUTER_API_KEY`.
- **Approval.** There is no `APPROVAL.md` gate. The dollar cap is in `config.py`, and its provenance is in `approvals.jsonl`.
- **Code hash.** `analyze` does not check the code hash. `run` refuses to resume a run whose stored code hash differs from the current code. The 2026-10-21 path edits changed that hash, so this run cannot be resumed. See [`docs/REORGANISATION_2026-10-21.md`](../../docs/REORGANISATION_2026-10-21.md) and [`docs/PATH_MAP.md`](../../docs/PATH_MAP.md).
