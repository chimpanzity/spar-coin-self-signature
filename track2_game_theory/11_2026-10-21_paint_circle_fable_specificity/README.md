# 11 · Fable specificity follow-up: is the predictability drop about "yourself"? (2026-10-21)

| | |
|---|---|
| Track | 2 — game theory (complementary to track 1) |
| Run IDs | Batch `fable-specificity-20261021` (with `analysis/`); re-analysis `analysis-20261021/` (119 sessions) |
| Game and models | Paint-and-circle, 200 rounds, W = 50, same prompts as folder 10 (`paint_circle-v1.0`). Fable (`anthropic/claude-fable-5.1`, effort low, no temperature) vs Fable |
| Size and cost | 17 new games, pooled with earlier Fable games to 6 complete games per cell; $68.02 (cap $70, raised to $80 at Chris's request during the run) |
| Previous / next | [← Paint-and-circle self-play](../10_2026-10-20_paint_circle_selfplay/) · [Fable perspective-taking →](../12_2026-10-21_paint_circle_fable_perspective/) |

## What was done

**Starting point.** In folder 10, telling Fable in seat A that the other player was "another instance of yourself" cut its predictability (PI) from 0.22 to 0.03. Fable's controls there were incomplete, so this follow-up tests whether the effect is specific to the self label.

**Prespecified analysis.** The following were written into `plan.json` before any game ran:
- **Cells.** Seat A told nothing / agent (existence sentence only) / other (the *false* label "a different language model") / self. Seat B is told nothing.
- **Pooling.** Earlier Fable–Fable games with the same prompts are pooled in: the baseline from pilot s0 and main s1–s3, and A-self from main s1–s3. This gives 6 complete games per cell.
- **Primary outcome.** Seat-A PI, one value per game.
- **Primary contrasts.** Self vs agent, and self vs other. Each uses a two-sided Welch t test, Holm-adjusted across the two contrasts.

**Run notes.**
- One game crashed when the provider returned no usage data. The runner was fixed, and the game was resumed and completed.
- `analysis-20261021/` re-runs the general analysis over all 119 complete paint-and-circle sessions (folder 10's 102 plus these 17). It also adds two exploitation indices: efficiency and conditional exploitation.

## Questions

- Is Fable's drop in predictability specific to being told the opponent is itself?
- Or does it also follow from being told only that an opponent exists, or that the opponent is a different language model?

## Results

| Seat A told | n | Mean PI | Session PIs | Win | Opponent lag-1 coef. | Self-reference |
|---|---|---|---|---|---|---|
| nothing | 6 | .249 | .17–.33 | .457 | 1.75 | 0% |
| agent (exists) | 6 | .181 | .09–.29 | .494 | 1.87 | 0% |
| other (false) | 6 | .088 | .03–.16 | .505 | 1.13 | 0% |
| self | 6 | .050 | −.00–.11 | .478 | 0.88 | 38% |

- **Self vs agent: −.131, Holm p = .008.** Saying only that another decision-maker exists does little.
- **Self vs other: −.038, Holm p = .19.** This difference is not significant.
- **Against baseline** (unadjusted), self lowers PI by .199 and other by .161 (both p < .001). Both also reduce reliance on the opponent's last move, with no loss of games.
- **The effect is not self-specific.** Describing the opponent as *a language model*, whether "yourself" or "a different language model", produces most of the shift.
- **Fable talks about shared identity only under the self label** (38% of responses), yet its play shifts nearly as much under "other". The verbal self-reasoning carries no distinct behavioural effect at this sample size.
- **Exploitation indices.**
  - Efficiency is undefined in every Fable–Fable game, because the opponent is never exploitable enough (shadow benchmark .51–.54).
  - Conditional exploitation does not differ between conditions (all |Δ| ≤ .07, p > .18).
  - The effect is on the protection side only.

## Open questions

- These conditions have not been tested for Fable: a *true* "different language model" (Fable against another model), and labels for non-language-model opponents (salmon, program).
- What is the mechanism? Does "the opponent is a language model" make Fable reason about the opponent's reasoning, and so drop its default chasing of the last move?

## What it led to

A perspective-taking feasibility run ([12](../12_2026-10-21_paint_circle_fable_perspective/)). It asks whether explicitly telling Fable to simulate the other player produces the same change, and whether that depends on the self label.

## Files

- Main report: [`docs/reports/SPAR_RESULTS_STATIC_AND_SELFPLAY_2026-10-21.md`](../../docs/reports/SPAR_RESULTS_STATIC_AND_SELFPLAY_2026-10-21.md), the "Update" section and Part III
- Batch: [`fable-specificity-20261021/`](fable-specificity-20261021/)
  - `plan.json`, with the prompts, the `prespecified` block and the cap history
  - `progress.log`, `status.json`
  - one folder per session
  - [`analysis/`](fable-specificity-20261021/analysis/): `fable_specificity.json`, `fable_seatA_sessions.csv`
- 119-session re-analysis: [`analysis-20261021/`](analysis-20261021/): `cell_summary.csv`, `contrasts_vs_baseline.csv`, `seat_sessions.csv`, `analysis.json`, `pi_vs_win.png`
- [`results_summary/`](results_summary/): copies of `fable_specificity.json` and `fable_seatA_sessions.csv`, plus `plan_and_prespecified_analysis.json`
- Code: [`src/paint_circle/fable_specificity.py`](../../src/paint_circle/fable_specificity.py), on top of [`src/paint_circle/`](../../src/paint_circle/)
- Tests: [`tests/test_paint_circle.py`](../../tests/test_paint_circle.py)

## Re-running

Run these from the repo root:

```
PYTHONPATH=src python -m paint_circle.fable_specificity --out <out_dir>          # prespecified analysis; no API calls
PYTHONPATH=src python -m paint_circle.analysis \
    track2_game_theory/10_2026-10-20_paint_circle_selfplay/pilot-20261020 \
    track2_game_theory/10_2026-10-20_paint_circle_selfplay/main-20261020 \
    track2_game_theory/10_2026-10-20_paint_circle_selfplay/makeups-20261020 \
    track2_game_theory/11_2026-10-21_paint_circle_fable_specificity/fable-specificity-20261021 --out <out_dir>
PYTHONPATH=src python -m paint_circle.run track2_game_theory/11_2026-10-21_paint_circle_fable_specificity/fable-specificity-20261021   # resumes; live
```

- **Batch locations.** `fable_specificity.py` finds the pilot, main and specificity batches through `src/repo_paths.py`.
- **Live runs** need `OPENROUTER_API_KEY`. They stop at the `cost_cap_usd` in `plan.json`. There is no `APPROVAL.md` gate and no code-hash check.
- **Paths.** See [`docs/REORGANISATION_2026-10-21.md`](../../docs/REORGANISATION_2026-10-21.md) and [`docs/PATH_MAP.md`](../../docs/PATH_MAP.md).
