# 10 · Paint-and-circle self-play: identity disclosure in a 200-round closed loop (2026-10-20)

| | |
|---|---|
| Track | 2 — game theory (complementary to track 1) |
| Run IDs | Batches `pilot-20261020`, `main-20261020`, `makeups-20261020`; analysis `analysis-20261020/`; window calibration `shadow_calibration.json` |
| Game and models | Paint-and-circle: a matching-pennies variant in PACA's two-shape frame, 200 rounds. Astra (`openai/gpt-6-astra`, effort low, no temperature); Fable (`anthropic/claude-fable-5.1`, effort low, no temperature); Qwen3-32B (`qwen/qwen3-32b` via SiliconFlow, reasoning off, temperature 0) |
| Size and cost | 102 complete sessions; $103.39 (pilot $5.56, main $97.75, make-ups $0.07), within the $125 limit |
| Previous / next | [← PACA believed-self pilot](../09_2026-10-11_paca_believed_self/) · [Fable specificity follow-up →](../11_2026-10-21_paint_circle_fable_specificity/) |

**Which Qwen.** The Qwen here is **Qwen3-32B**, served by SiliconFlow with reasoning off. It is not the Qwen3.8-27B (Alibaba endpoint) used in folders 03–09.

## What was done

**The game.** Player A places yellow paint and wins on a match. Player B places the blue circle and wins on a mismatch. Each round both commit simultaneously, and both see the same truthful history: 5 rows in words plus a grid of the last W = 50 rounds.

**The manipulation.** A disclosure adds one paragraph to a seat's system prompt. It starts with an existence sentence ("Another decision-maker decides where the blue circle lands."), followed by one identity statement:
- self: "another instance of yourself, the same language model"
- other: "a different language model"
- salmon: "a dead salmon"
- program: "a random computer program"

The "agent" control uses the existence sentence alone.

**Primary measure: predictability (PI).** A "shadow" Proteus (PACA's implementation from [09](../09_2026-10-11_paca_believed_self/)) is restricted to the last 50 rounds and forecasts each seat's own choices. PI = 2 × (expected accuracy − 0.5).

**Other measures:**
- win rate;
- Brown–Rosenthal lag regressions, including the coefficient on the opponent's last move;
- run statistics;
- self-reference rate.

**Choosing the window.** W = 50 was chosen offline with `calibrate_shadow.py` on synthetic players. Both candidate windows were unbiased under the null, and W = 50 was more sensitive.

**Sessions.** The 102 complete sessions were:
- Qwen–Qwen: 8 conditions × 5–7 sessions;
- Astra–Astra: 7 conditions × 2–5;
- Fable–Fable: 4 conditions × 2–4;
- Astra-vs-Qwen and Qwen-vs-Astra: 3 conditions × 3 each.

All parts are exploratory, with no correction across contrasts.

## Questions

- **H1:** In the baseline, do players attend outward, conditioning on the opponent's recent moves as in PACA?
- **H2:** Does telling one or both players "the other is yourself" change predictability, dependence on the opponent, or wins?
- **H3:** Is any change identity-specific: larger for "self" than for "other", "agent", "salmon" or "program", and larger when the label is true?
- **H4:** Does disclosure trade predicting the opponent against protecting oneself?

## Results

- **H1, outward attention: yes for Astra and Fable.** In every Astra and Fable baseline session, choices depended on the opponent's recent placements (Brown–Rosenthal p < .05). The painter follows where the circle last landed, and the circle-placer avoids where paint last went. Qwen is streaky, biased toward STAR, and only weakly tied to its opponent.
- **H2, Fable is the clearest case.** Told that seat B is itself, Fable in seat A became much less predictable: PI fell from 0.22 to 0.03, and the session ranges do not overlap (0.17–0.26 vs −0.00–0.07). Its dependence on the opponent's last move roughly halved, and it lost no games. The effect replicated when both seats were told. Fable referred to the shared identity in about 40% of its responses under self-disclosure, and never without it.
- **H2, other models.** Astra showed small, inconsistent shifts and never mentioned identity. Qwen moved a lot under every added sentence, mostly by changing its preference for one shape.
- **H3, nothing was identity-specific.** For Astra, the false "other" label and the bare "agent" sentence moved wins as much as "self" did. For Qwen, "agent", "salmon" and "program" moved it more than "self" did. True and false labels made no consistent difference.
- **H4:** there was no simple trade-off. Only Fable's balance moved, toward protection.
- **Qwen compliance.** In 11 of 52 Qwen–Qwen sessions, Qwen at some point wrote out the history grid instead of a choice. These failures clustered in the salmon (4/7) and agent (3/7) conditions, and never occurred under self-disclosure. Seven sessions were recovered by resuming; replacement games were run for the rest. Analysis uses complete sessions only, so the salmon and agent cells over-represent less streaky games.

## Open questions

- Is Fable's predictability drop caused by the *self* label, or by any statement that the opponent is a language model? Fable's controls here were incomplete.
- Does the change reflect self-simulation, or a general change of strategy?

## What it led to

- A prespecified Fable specificity test with 6 games per cell ([11](../11_2026-10-21_paint_circle_fable_specificity/)).
- A perspective-taking feasibility run ([12](../12_2026-10-21_paint_circle_fable_perspective/)).

## Files

- Main report: [`docs/reports/SPAR_RESULTS_STATIC_AND_SELFPLAY_2026-10-21.md`](../../docs/reports/SPAR_RESULTS_STATIC_AND_SELFPLAY_2026-10-21.md), Part II (Part I is track 1)
- Batches:
  - [`pilot-20261020/`](pilot-20261020/), [`main-20261020/`](main-20261020/), [`makeups-20261020/`](makeups-20261020/)
  - Each contains `plan.json` (prompts, models, cap), `progress.log`, `status.json`, and one folder per session with `rounds.jsonl`.
- 102-session analysis: [`analysis-20261020/`](analysis-20261020/)
  - `cell_summary.csv`, `contrasts_vs_baseline.csv`, `seat_sessions.csv`, `analysis.json`, `pi_vs_win.png`
- [`results_summary/`](results_summary/)
  - Copies of the **119-session** re-analysis of 2026-10-21, which adds the 17 Fable games of folder 11 and the exploitation indices. These are byte-identical to [`../11_2026-10-21_paint_circle_fable_specificity/analysis-20261021/`](../11_2026-10-21_paint_circle_fable_specificity/analysis-20261021/).
  - A copy of `shadow_calibration.json`.
- [`shadow_calibration.json`](shadow_calibration.json): calibration of the W = 50 window
- Code: [`src/paint_circle/`](../../src/paint_circle/): `game.py`, `shadow.py`, `calibrate_shadow.py`, `plan.py`, `run.py`, `analysis.py`
- Tests: [`tests/test_paint_circle.py`](../../tests/test_paint_circle.py)
- Flat exports: [`exports/upload_pack_2026-10-21/`](../../exports/upload_pack_2026-10-21/)

## Re-running

Run these from the repo root:

```
PYTHONPATH=src python -m paint_circle.analysis track2_game_theory/10_2026-10-20_paint_circle_selfplay/pilot-20261020 \
    track2_game_theory/10_2026-10-20_paint_circle_selfplay/main-20261020 \
    track2_game_theory/10_2026-10-20_paint_circle_selfplay/makeups-20261020 --out <out_dir>   # no API calls
PYTHONPATH=src python -m paint_circle.plan main <batch_dir> <cost_cap_usd>                    # writes plan.json
PYTHONPATH=src python -m paint_circle.run <batch_dir> [--concurrency N]                       # live; resumable
PYTHONPATH=src python -m pytest -q tests/test_paint_circle.py
```

- **Live runs** need `OPENROUTER_API_KEY`. There is no `APPROVAL.md` gate: the runner stops at the `cost_cap_usd` in `plan.json`. There is no code-hash check.
- **Proteus dependency.** `shadow.py` loads Proteus from `track2_game_theory/09_2026-10-11_paca_believed_self/task/protean_committed.py`.
- **Calibration:** `PYTHONPATH=src python -m paint_circle.calibrate_shadow 200` regenerates `shadow_calibration.json` in this folder. It makes no API calls. Paths after the reorganisation are explained in [`docs/REORGANISATION_2026-10-21.md`](../../docs/REORGANISATION_2026-10-21.md) and [`docs/PATH_MAP.md`](../../docs/PATH_MAP.md).
