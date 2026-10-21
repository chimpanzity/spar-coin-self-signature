# 09 · PACA believed-self pilot: forecasting a sequence said to come from "yourself" (2026-10-11)

This folder is a self-contained package with its own [`README.md`](README.md), which is the original project README. This page summarises it for readers of the track-2 sequence.

| | |
|---|---|
| Track | 2 — game theory (complementary to track 1) |
| Run IDs | `paca_believed_self_pilot_v1`, in [`data/believed_self_pilot/`](data/believed_self_pilot/) |
| Game and models | PACA minimalist forecasting task: predict where the blue circle lands (TRIANGLE / STAR). Hidden generator: Proteus (Lee et al. 2004, Algorithm 2) or an IID fair coin. Models: Fable (`anthropic/claude-fable-5.1`) and Astra (`openai/gpt-6-astra`). Qwen3.8-27B was planned but not run |
| Size and cost | 8 sessions × 200 trials = 1,600 calls; $22.44 including $0.28 preflight |
| Previous / next | [← Post-hoc analyses](../08_2026-10-11_post_hoc_analyses/) · [Paint-and-circle self-play →](../10_2026-10-20_paint_circle_selfplay/) |

## What was done

**Background.** The Blind Twin and disclosure studies (01–08) found no evidence that being told "this is you" changes play in a self-specific way. This pilot moves the manipulation into PACA, an adaptive forecasting task from Chris's earlier work with Bhui.

**The manipulation.** One sentence is prepended to the system prompt. Believed self: "Another instance of your model is generating the sequence of blue circle landings." Believed other: "An instance of a different language model is generating the sequence of blue circle landings."

**The real generator** is either Proteus or a fair coin, hidden in both conditions.

**Design.**
- 2 × 2 within each model: actual generator × believed generator, with one 200-trial session per cell.
- The model sees the last 25 trials; Proteus conditions on the full session.
- Believed-self and believed-other sessions of the same model and generator share an opponent seed. The two coin sessions therefore saw identical sequences.

**Why Qwen was dropped.** At PACA's default reasoning, each Qwen forecast took 28,000–31,000 output tokens (about 10 minutes). Chris decided not to run it rather than change its reasoning setting. The decision is recorded in `data/believed_self_pilot/APPROVAL.md`.

## Questions

- Does believing that the sequence comes from another instance of yourself change how a model uses the history to forecast?
- Does any such change help or hurt against an adaptive opponent (Proteus)?

## Results

All results are descriptive; there is one session per cell.

- **Accuracy:** there was no consistent effect of the believed-self frame. Accuracy ranged from 0.450 to 0.535 across the 8 sessions.
- **Behaviour against the coin:** both models bet against a repeat of the last landing.
- **The frame pushed the two models in opposite directions** on dependence on the last landing (Brown–Rosenthal lag-1 coefficient on the circle, coin sessions):
  - Fable expected *more* switching under the self frame (−0.80 vs −0.39).
  - Astra expected *less* (−0.30 vs −0.63).
- **Status of the result.** Session-to-session variation could produce differences of this size, so this is a candidate effect to replicate, not a finding.
- **Completion:** all 8 sessions were complete. Two attempts failed (content filter) and were re-requested; none was replaced by a coin flip.

## Open questions

- Does the opposite-direction shift replicate with several sessions per cell?
- Does it also appear when the actual generator is the same model?
- Can a frame-induced policy change be separated from ordinary session-to-session drift? Models reproduce only about 80% of their own choices on identical prompts ([07](../07_2026-10-11_selfself_judges_and_retest/)).

## What it led to

- **Proteus reused.** The PACA Proteus implementation in this folder, `task/protean_committed.py`, became the "shadow" predictor used to measure each player's predictability in paint-and-circle self-play ([10](../10_2026-10-20_paint_circle_selfplay/)–[12](../12_2026-10-21_paint_circle_fable_perspective/)).
- **A runtime dependency.** `src/paint_circle/shadow.py` loads this file at run time, so it must stay at this path.
- **The next design.** Paint-and-circle keeps PACA's two-shape frame, but both sides are live models. The identity statement is about the opponent player, not about a sequence generator.

## Files

- Package README: [`README.md`](README.md), covering layout, provenance and how to run
- Main report: [`data/believed_self_pilot/analysis/REPORT.md`](data/believed_self_pilot/analysis/REPORT.md), with `session_measures.csv`, `cross_condition_contrasts.csv`, `trials.csv` and figures
- Run data: [`data/believed_self_pilot/`](data/believed_self_pilot/)
  - `manifest.json`, `APPROVAL.md`, `VALIDATION_REPORT.md`, `preflight_calls.jsonl`
  - per-session raw logs under `astra/` and `fable/`
- Code: [`task/`](task/)
  - written for this pilot: `believed_self.py`, `run_believed_self_pilot.py`, `analyze_believed_self.py`
  - PACA files, vendored unchanged: `protean_committed.py`, `prompts.py`, `prime.py`, `api_client.py`, `analyze_pilot.py`
  - [`code/verify_brown_rosenthal.py`](code/verify_brown_rosenthal.py)
  - This package is not under `src/`.
- Tests: [`tests/test_believed_self.py`](tests/test_believed_self.py), in this folder, not in the repo's `tests/`

## Re-running

These commands run from **this folder**, not the repo root, as the package README describes. The package needs numpy, pandas, scipy, matplotlib and openai.

```
python -m pytest -q tests/test_believed_self.py      # offline
python task/run_believed_self_pilot.py validate      # offline full dry run
python task/analyze_believed_self.py                 # re-analyse from raw logs; rewrites analysis/
python task/run_believed_self_pilot.py run --live    # live; needs OPENROUTER_API_KEY and the APPROVAL.md approval line; resumable
```

- **Not affected by the reorganisation.** This package does not use `src/repo_paths.py`, and the 2026-10-21 reorganisation did not edit its code.
- **Paths.** The folder itself moved from `paca_believed_self/` (see [`docs/PATH_MAP.md`](../../docs/PATH_MAP.md)).
