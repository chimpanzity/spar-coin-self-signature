# 12 · Fable perspective-taking guidance: does "simulate the other player" act like "it is yourself"? (2026-10-21)

| | |
|---|---|
| Track | 2 — game theory (complementary to track 1) |
| Run IDs | Batch `fable-perspective-20261021` (with `analysis/`); prompts version `paint_circle-fable-perspective-v1.0` (commit `b6f7d87`) |
| Game and models | Paint-and-circle, 200 rounds, W = 50. Fable (`anthropic/claude-fable-5.1`, effort low, no temperature) vs Fable throughout |
| Size and cost | 2×2 design × 2 games = 8 games, all collected fresh; $37.82 (cap $45); about $5.40 per guided game and $4.10 per plain game |
| Previous / next | [← Fable specificity follow-up](../11_2026-10-21_paint_circle_fable_specificity/) · [Scripted-opponent pilot →](../13_2026-10-21_paint_circle_scripted_opponent_pilot/) |

## What was done

**Background.** Folder 11 showed that Fable's predictability drop is not specific to the self label: "a different language model" does nearly as much. This feasibility run, approved by Chris, asks a different question. If Fable is told explicitly to put itself in the other player's position, does its play change in the same way? And does that depend on whether the other player is called "yourself"?

**Design.** A 2×2 for seat A only:
- **Identity label:** self, or other. "Other" is a false label, since the opponent is always Fable.
- **Guidance:** yes or no.

**The guided prompt** adds B's instruction, followed by this sentence:

> "Before choosing your shape, consider what you would choose if you were in the other decision-maker's position, following that instruction and using the available history. Use that prediction to choose the shape where you expect the blue circle to land."

- **Seat B's prompt** is byte-identical to the baseline.
- **Prompts are checked by tests.** Tests confirm that the guided prompts match the handoff text.
- **The plan was prespecified** in `plan.json` before any call.

**A confound.** The guided cells also reveal B's objective. A guidance effect therefore cannot be separated from that task disclosure.

## Questions

- Does perspective-taking guidance change Fable's strategy?
- Does the change differ between the self and other labels? A difference would point to self-specific simulation.

## Results

Seat A, mean of 2 games per cell. These numbers are descriptive only.

| A told | Guidance | Win | PI | Opponent lag-1 coef. | Tokens per answer |
|---|---|---|---|---|---|
| self | yes | .545 | .006 | −0.22 | 238 |
| other | yes | .528 | .008 | −0.07 | 227 |
| self | no | .508 | .036 | +0.81 | 129 |
| other | no | .530 | .055 | +0.98 | 113 |

- **Guidance changes Fable's strategy under both labels.**
  - Play becomes essentially unpredictable to the shadow predictor (PI ≈ .01, against .04–.06 without guidance).
  - Fable stops chasing B's last placement: the opponent lag-1 coefficient moves from about +0.9 to about 0.
  - Answers roughly double in length.
- **The label adds nothing under guidance.** self_sim − other_sim: PI −.002 [−.021, +.017]; win +.017 [−.030, +.065].
- **No interaction.** The label × guidance interaction includes zero for win, PI and exploitation gap (session bootstrap, 4,000 resamples).
- **Wins may rise a few points with guidance,** but not distinguishably from zero at this size.
- **Reproducibility.** The fresh unguided games reproduce folder 11's values for the same cells (PI .04–.06 here vs .05–.09). The earlier games are reported alongside, not pooled.
- **Reading.** By the handoff's decision tree, this is the "both guided cells change" outcome: a general effect of perspective-taking and task disclosure, not self-specific simulation.

## Open questions

The handoff lists the next informative cells:
- task disclosure without guidance;
- a neutral strategic instruction of matched length;
- a real cross-model opponent.

These would separate guidance from task disclosure and from prompt length.

## What it led to

This is the latest track-2 run. Taken together, folders 10–12 show three things:
- Fable's identity-related change in play is real.
- It is general, not tied to the self label.
- Explicit perspective-taking produces it too.

This complements track 1's finding that models show no consistent privileged self-prediction.

## Files

- Main report: [`docs/reports/SPAR_RESULTS_STATIC_AND_SELFPLAY_2026-10-21.md`](../../docs/reports/SPAR_RESULTS_STATIC_AND_SELFPLAY_2026-10-21.md), "Update 2" and Part IV
- Batch: [`fable-perspective-20261021/`](fable-perspective-20261021/)
  - `plan.json`, with the system prompts, their SHA-256 hashes, the git head and the `prespecified` block
  - `progress.log`, `status.json`
  - 8 session folders
  - [`analysis/`](fable-perspective-20261021/analysis/): `fable_perspective_2x2.json`, `fable_perspective_seatA_games.csv`
- [`results_summary/`](results_summary/): copies of the two analysis files, plus `plan_and_prompts.json`
- Code:
  - [`src/paint_circle/fable_perspective.py`](../../src/paint_circle/fable_perspective.py), for the analysis
  - [`src/paint_circle/game.py`](../../src/paint_circle/game.py), which holds the guidance text (`GUIDANCE_VERSION`)
- Tests: [`tests/test_paint_circle.py`](../../tests/test_paint_circle.py), in the perspective-taking section

## Re-running

Run these from the repo root:

```
PYTHONPATH=src python -m paint_circle.fable_perspective --out <out_dir>      # 2x2 summary; no API calls
PYTHONPATH=src python -m paint_circle.run track2_game_theory/12_2026-10-21_paint_circle_fable_perspective/fable-perspective-20261021   # resumes; live
PYTHONPATH=src python -m pytest -q tests/test_paint_circle.py
```

- **Batch locations.** `fable_perspective.py` finds this batch, and the earlier Fable batches it reports alongside, through `src/repo_paths.py`.
- **Live runs** need `OPENROUTER_API_KEY`. They stop at the `cost_cap_usd` in `plan.json`. There is no `APPROVAL.md` gate and no code-hash check.
- **Paths.** See [`docs/REORGANISATION_2026-10-21.md`](../../docs/REORGANISATION_2026-10-21.md) and [`docs/PATH_MAP.md`](../../docs/PATH_MAP.md).
