# 04 · Opponent-disclosure pilot: does telling Astra it faces itself change its play? (2026-10-09)

| | |
|---|---|
| Track | 2 — game theory (complementary to track 1) |
| Run IDs | `od-20261009T1200Z` |
| Game and models | Matching pennies (MP), 20 rounds. Astra (`openai/gpt-6-astra`) vs Astra; reasoning effort low, no temperature control |
| Size and cost | 2×2 conditions × 8 games = 32 games; 1,280 player calls; $7.05 including $0.40 smoke (cap $25) |
| Previous / next | [← Blind Twin RPS](../03_2026-10-09_blind_twin_rps/) · [Study 1, Experiment 1 →](../05_2026-10-10_study1_exp1_disclosure/) |

## What was done

Blind Twin (01–03) asks whether an *observer* reads a player better when told the player is its own model. This pilot asks the other direction: does a *player* play differently when told its opponent is another instance of itself?

**Setup.** Astra played Astra in matching pennies. Each player either received this line or did not:

> "Opponent identity: Your opponent is another independent instance of the same language model as you, Astra."

**Design.** A 2×2 of who is told: 00 neither, 10 Matcher only, 01 Mismatcher only, 11 both. There were 8 games of 20 rounds per cell.

**Outcomes.**
- Primary: Matcher win rate.
- Secondary: switch rates, run lengths, and how well simple history rules predict each player.
- Manipulation check: how often responses mention the shared identity.

## Questions

- Does being told that the opponent is a copy of itself change a player's win rate or its sequential behaviour?
- Do players say anything about the shared identity?

## Results

- **Completion:** all 32 games were complete, and all 1,280 answers were valid.
- **Matcher win rate by condition:** 00 = 53.1%, 10 = 57.5%, 01 = 53.1%, 11 = 58.8%.
- **Telling the Matcher raised its win rate by +5.0 pp [+0.6, +9.7].** Telling the Mismatcher changed little: +0.6 pp [−3.4, +5.3]. The interaction was +1.2 pp [−7.5, +9.4].
- **No response mentioned the self.** None of the 1,280 responses used "same model", "instance", "Astra", "myself" or similar terms. Median answer length rose slightly when informed (for example, Matcher 38 → 43.5 completion tokens).
- **Some behaviour shifted with disclosure, without a clear pattern.** An example is the Matcher's switch rate: +3.6 pp when it was told, −5.6 pp when its opponent was told.

All intervals come from a game-level bootstrap with 8 games per cell and no multiplicity correction. This is an exploratory pilot.

## Open questions

- Is the +5 pp Matcher effect about the self, or would naming *any* opponent do the same? With one model, this pilot cannot tell.
- If the line changes play without ever being mentioned, how does it act?

## What it led to

Study 1, Experiment 1 ([05](../05_2026-10-10_study1_exp1_disclosure/)) scaled this up the next day:
- three models in all nine ordered pairings, so "told it faces itself" can be compared with "told it faces another model";
- both RPS and MP.

## Files

- Run folder: [`od-20261009T1200Z/`](od-20261009T1200Z/)
  - [`report.md`](od-20261009T1200Z/report.md): main report
  - `game_measures.csv`, `manipulation_check.csv`, `summary.csv`, `results.json`
  - raw `calls.jsonl` and `game_logs.jsonl`
  - `config.json` and `freeze.json`: the frozen configuration and code hash
  - `approvals.jsonl`
- Code: [`src/opponent_disclosure/`](../../src/opponent_disclosure/), including `protocol.md`
- Tests: [`tests/test_opponent_disclosure.py`](../../tests/test_opponent_disclosure.py)
- Background: [`docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md`](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md), section 3.1

## Re-running

Run these from the repo root:

```
PYTHONPATH=src python -m opponent_disclosure analyze --run od-20261009T1200Z   # no API calls; rewrites report.md
PYTHONPATH=src python -m opponent_disclosure fake    --run <new-id>            # offline
PYTHONPATH=src python -m opponent_disclosure run     --run <new-id> --live     # live
PYTHONPATH=src python -m pytest -q tests/test_opponent_disclosure.py
```

- **Subcommands:** `fake`, `smoke`, `run` and `analyze`.
- **Live runs** need `OPENROUTER_API_KEY`. There is no `APPROVAL.md` gate; the cap is in `config.py`.
- **Code hash.** `run` and `smoke` refuse a run directory whose stored code hash differs from the current code. The 2026-10-21 path edits changed that hash. See [`docs/REORGANISATION_2026-10-21.md`](../../docs/REORGANISATION_2026-10-21.md) and [`docs/PATH_MAP.md`](../../docs/PATH_MAP.md).
