# 13 · Scripted-opponent pilot: can Fable exploit obvious patterns? (2026-10-21)

| | |
|---|---|
| Track | 2: game theory (complementary to track 1) |
| Tag | `SCRIPTED_OPPONENT_PILOT` |
| Run ID | `scripted-pilot-20261021` |
| Game and models | Paint-and-circle matching pennies. A = Fable (`anthropic/claude-fable-5.1`, effort low, unchanged minimal paint prompt). B = a local deterministic script (no model, no API calls). |
| Size and cost | 4 sessions × 100 rounds = 400 Fable calls, 0 rejected answers, $2.39 (estimate $3.18; caps $5 and 400 calls) |
| Previous | [← 12 Fable perspective-taking](../12_2026-10-21_paint_circle_fable_perspective/) |

## What was done

This is a measurement-validation pilot, not a test of self-modelling.

- **Fable's side is unchanged.** It played the painter with the same prompt and history display as in folder 10: 5 verbal rows plus a 50-round grid. It was told nothing about the opponent.
- **B is a script.** The circle player followed a fixed sequence:

| Script | Sequence |
|---|---|
| `ALT_S` | S T S T … (alternating, starting with STAR) |
| `ALT_T` | T S T S … (alternating, starting with TRIANGLE) |
| `DOUBLE_S` | S S T T … (period 4) |
| `DOUBLE_T` | T T S S … (period 4) |

- **No look-ahead.** B's move depends only on the round number. It was fixed before Fable was called, and Fable never saw it before committing.
- **One session per script.** Each ran 100 rounds; the four ran in parallel.
- **Primary window: rounds 51–100.** By then the 50-round history window is full.

## Questions

- Can Fable detect and exploit simple sequential regularities?
- Does the information-matched shadow Proteus detect the same patterns?
- Do the predictability (PI) and exploitation (EI) measures behave sensibly when the answer is known?

## Results

From [`scripted-pilot-20261021/analysis/scripted_pilot_sessions.csv`](scripted-pilot-20261021/analysis/scripted_pilot_sessions.csv):

| Script | Fable win, rounds 1–100 | Fable win, rounds 51–100 | Rounds Fable lost | PI_B (late) | Shadow win, full / late | EI_A, full / late | Gap, full / late | PI_A (late) |
|---|---|---|---|---|---|---|---|---|
| ALT_S | .98 | 1.00 | 1, 2 | 1.00 | .935 / 1.00 | 1.10 / 1.00 | +.045 / 0 | 1.00 |
| ALT_T | .98 | 1.00 | 2, 4 | 1.00 | .935 / 1.00 | 1.10 / 1.00 | +.045 / 0 | 1.00 |
| DOUBLE_S | .96 | 1.00 | 1, 3, 4, 7 | 1.00 | .87 / 1.00 | 1.24 / 1.00 | +.09 / 0 | 1.00 |
| DOUBLE_T | .97 | 1.00 | 3, 4, 5 | 1.00 | .87 / 1.00 | 1.27 / 1.00 | +.10 / 0 | 1.00 |

- **Fable exploits both patterns almost immediately.** It lost only 2–4 rounds per session, all in the first 7, and none after. Its reasoning names the pattern within the first few rounds: "possibly alternating, suggesting T next".
- **Fable matches the periodic oracle.** It agreed with the ideal oracle, which infers period and phase from the last 4 moves, on 99–100% of rounds where the oracle commits.
- **DOUBLE took slightly longer than ALT, for both learners.** Fable lost 3–4 rounds against DOUBLE vs 2 against ALT. The shadow needed more history for DOUBLE too.
- **The shadow detects both patterns.** Each was caught by the expected channel: one-step choice history for ALT, two-step for DOUBLE. Its forecasts were 100% accurate whenever a channel was active, but it needs more rounds than Fable before a channel becomes significant:
  - B-channel activation over the full game: .87 for ALT, .74 for DOUBLE.
  - Over the full game, Fable beat the shadow benchmark by 4.5–10 points (EI_A 1.10–1.27).
  - In the late window both are at ceiling, so EI_A = 1.0 and the gap is 0.
- **Exploiting made Fable perfectly predictable (PI_A = 1.0 late).** It tracked the pattern exactly. This is the predicted tension between chasing an opponent's regularity and staying unpredictable, and it appears in its simplest form.

**Reading against the handoff's decision table:** this is the "Fable wins well above 50%, shadow predicts B well" outcome. Both detect and exploit simple structure, and the indices are usable here.

## Open questions

- **EI at ceiling is uninformative.** In the late window, EI_A is 1.0 only because both learners are perfect. EI discriminates only where the shadow's advantage is partial, so a harder test would use noisy or longer-period scripts (e.g. 80% alternation, period 3, win-stay/lose-shift).
- **Is the shadow benchmark conservative?** Over the full game, Fable learned faster than the shadow's significance-gated channels. Exploitation numbers measured against the shadow could therefore understate a fast learner's early advantage.
- **Other models are untested.** This pilot validates the measures with Fable only.

## Files

- [`scripted-pilot-20261021/plan.json`](scripted-pilot-20261021/plan.json): sessions, scripts, A's exact prompt with its SHA-256, caps, cost estimate and the measures fixed before the run.
- `scripted-pilot-20261021/fable-vs-script__<SCRIPT>/rounds.jsonl`: every round, with Fable's full response.
- [`scripted-pilot-20261021/analysis/`](scripted-pilot-20261021/analysis/):
  - `scripted_pilot_sessions.csv`: full and late windows per session.
  - `scripted_pilot.json`: the same numbers plus 10-round bins.
  - [`win_rate_bins.png`](scripted-pilot-20261021/analysis/win_rate_bins.png): win rate in 10-round bins.
- Code:
  - [`src/paint_circle/scripted.py`](../../src/paint_circle/scripted.py): the scripted circle player and the oracle.
  - [`src/paint_circle/scripted_pilot.py`](../../src/paint_circle/scripted_pilot.py): the analysis.
  - `src/paint_circle/run.py`: runs scripted B sessions and enforces the `call_cap` limit.
- Tests: `tests/test_paint_circle.py` covers the sequences and phases, the oracle, a 100-round fake dry run that checks A never sees the current or a future B move, and the call cap.

## Re-running

From the repository root:

```bash
PYTHONPATH=src python -m paint_circle.scripted_pilot track2_game_theory/13_2026-10-21_paint_circle_scripted_opponent_pilot/scripted-pilot-20261021
PYTHONPATH=src python -m paint_circle.run <new batch dir with a plan.json like this one>   # live; needs OPENROUTER_API_KEY
```
