# 01 · Blind Twin v1: can a model predict its own play in matching pennies? (2026-10-09)

| | |
|---|---|
| Track | 2 — game theory (complementary to track 1) |
| Run IDs | `bt-20261009T0455Z` |
| Game and models | Matching pennies (MP), 20 rounds. Players and judges: Astra (`openai/gpt-6-astra`) and Fable (`anthropic/claude-fable-5.1`), reasoning effort low, no temperature control |
| Size and cost | 12 games planned (4 ordered matchups × 3); 224 player calls + 618 judge calls = 842 calls; $4.62 (cap $25) |
| Previous / next | (first track-2 run) · [Blind Twin v2 (MP) →](../02_2026-10-09_blind_twin_v2_mp/) |

## What was done

The coin-flip work of track 1 had reached a floor by 2026-10-08: in the Phase 2 runs the judges did not really forecast. Track 2 moved to strategic games, where each choice is a committed action with a payoff.

Blind Twin is the first design. Two models play matching pennies against each other. Fresh judge instances of the same two models then predict both players' next moves from the public history, one round at a time. Each judge sees the same frozen game log under three identity labels:

- TRUE: the real model names;
- FALSE: the names swapped;
- ANONYMOUS: no names.

The primary index S is the self-specific truth benefit. For each judge, take (TRUE − ANONYMOUS) accuracy on players of its own model, subtract the other judge's (TRUE − ANONYMOUS) on that model, and average. S_false is the same index with FALSE in place of ANONYMOUS.

## Questions

- Does telling a judge "this player is your own model" help it predict that player more than it helps the other judge?
- Does the pipeline work end to end (games → freeze → blinded judging → analysis)?

## Results

- **The player parser cut 9 of 12 games short.** In every game with a Fable seat, Fable eventually wrote one sentence of reasoning before the shape. The frozen v1 parser accepted only a bare shape word, so that round was invalid and the game stopped. All 10 invalid answers were Fable's and had this same two-line form. Only the three Astra–Astra games completed. See `BLOCKER.md`.
- Judging ran on the 103 valid rounds as frozen. All 618 judge calls were valid.
- S = −2.2 [−8.5, +3.5]. S_false = +3.5 [−3.1, +9.4]. The estimates are dominated by Astra–Astra games. Every Fable-seat estimate rests on rounds 1–9 only.
- **Shared openings.** Without temperature control, "independent" games repeated: all three Fable–Astra games had the same opening before stopping at round 4. Three replicates per matchup are therefore fewer than three independent games.

## Open questions

- Would a parser that accepts brief reasoning followed by the move on the final line fix completion without changing anything else? `BLOCKER.md` lists this option and two others.
- How should the dependence created by near-identical openings be handled: more replicates, varied starting contexts, or reporting replicates as dependent?

## What it led to

Chris chose the final-line option. Blind Twin v2 ([02](../02_2026-10-09_blind_twin_v2_mp/)) let players reason briefly, required the move alone on the final line, and reran the same design as a new run. This run was left unchanged.

## Files

- Run folder: [`bt-20261009T0455Z/`](bt-20261009T0455Z/)
  - [`report.md`](bt-20261009T0455Z/report.md): completion, accuracy tables, indices, baselines, per-game player behaviour
  - [`BLOCKER.md`](bt-20261009T0455Z/BLOCKER.md): the parser failure and the options offered
  - `predictions.csv`, `by_game.csv`, `summary.csv`, `results.json`, `figures/`
  - `config.json` and `freeze.json`: the frozen configuration and code hash
- Code: [`src/blind_twin/`](../../src/blind_twin/), including `protocol.md` and `templates/`
- Tests: [`tests/test_blind_twin.py`](../../tests/test_blind_twin.py)
- Background: [`docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md`](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md), sections 1 and 3.1

## Re-running

Run these from the repo root:

```
PYTHONPATH=src BLIND_TWIN_VERSION=v1 python -m blind_twin fake --run <new-id>          # offline end-to-end, fake client
PYTHONPATH=src BLIND_TWIN_VERSION=v1 python -m blind_twin run  --run <new-id> --live   # live; needs OPENROUTER_API_KEY
PYTHONPATH=src python -m pytest -q tests/test_blind_twin.py
```

- **Version.** The package defaults to v2. Set `BLIND_TWIN_VERSION=v1` to get this run's prompt and strict parser.
- **Run location.** `--run bt-20261009T0455Z` finds this run in place, because finished runs are located by their ID. New runs are written to folder 02 (`config.RESULTS`). The outputs here are already complete.
- **Approval.** There is no `APPROVAL.md` gate. The $25 ceiling and its provenance are in the run's `approvals.jsonl`.
- **Code hash.** The CLI refuses to resume a run whose stored code hash differs from the current code. The 2026-10-21 path edits changed that hash, so this run cannot be resumed. See [`docs/REORGANISATION_2026-10-21.md`](../../docs/REORGANISATION_2026-10-21.md) and [`docs/PATH_MAP.md`](../../docs/PATH_MAP.md).
