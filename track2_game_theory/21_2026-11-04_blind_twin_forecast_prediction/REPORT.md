# Can a model predict its own forecasts? Blind Twin forecast-prediction pilot

Track 2, folder 21 · 2026-11-04 · protocol `BlindTwinForecastPrediction_v1` · plan `plan/run_plan.json`
(sha256 `588d03bb…`, frozen at commit `fbf9fec`; approval in [APPROVAL.md](APPROVAL.md))

## Answer

**Astra's code predicted both judges better.** There is no reciprocal own-model advantage.

- **Predicting Fable's forecasts:**
  - Astra's program: Brier 0.256.
  - Fable's program: 0.288.
  - Astra is better by **0.032** (Fable-target advantage −0.032).
- **Predicting Astra's forecasts:**
  - Astra's program: 0.225.
  - Fable's program: 0.262.
  - Astra is better by **0.037** (Astra-target advantage +0.037).
- **Balanced self advantage:** +0.003, the average of a positive and a negative contrast. This is an author effect, not a
  self effect: Astra wrote the better predictors.
- **Only one of the four programs beats a constant 0.5** (Brier 0.25): Astra's program for Astra.

This is a descriptive pilot: one generated program per cell and six games.

## Four losses, references and variability

Brier loss, averaged within each game over 20 rounds × 2 seats, then equally over the 6 games. Lower is better.

| Author ↓ / target judge → | GPT-6 Astra | Claude Fable 5.1 |
|---|---|---|
| GPT-6 Astra | **0.2254** | 0.2563 |
| Claude Fable 5.1 | 0.2624 | 0.2878 |
| Reference: constant 0.5 | 0.2500 | 0.2500 |
| Reference: repeat previous (0.75 / 0.25) | 0.4031 | 0.4552 |

The repeat reference is much worse than a coin flip. The judges forecast changes of shape far more often than repeats.

| Contrast (positive = same-model author better) | Estimate | 6 game-level values | Leave-one-game-out range |
|---|---|---|---|
| Fable-target advantage B[A,F] − B[F,F] | −0.032 | −0.032, −0.051, −0.031, −0.081, **+0.059**, −0.052 | −0.050 to −0.022 |
| Astra-target advantage B[F,A] − B[A,A] | +0.037 | +0.062, +0.053, +0.066, +0.012, +0.015, +0.014 | +0.031 to +0.042 |
| Balanced self advantage | +0.003 | +0.015, +0.001, +0.018, −0.035, +0.037, −0.019 | −0.004 to +0.010 |

Games in order: AA_00_1, AA_00_2, FF_00_1, FF_00_2, QQ_00_1_MU2, QQ_00_2.

- Astra's program wins on the Astra target in all 6 games and on the Fable target in 5 of 6.
- Dropping any one game never changes the sign of either target contrast.
- The balanced contrast changes sign across games and is unresolved.

## Did the authors use the target identity?

| Author | Different modal calls between its two programs (of 240) | Ties | Mean \|Δp\| | Swapped − intended loss |
|---|---|---|---|---|
| Astra | 19 | 0 | 0.049 | **+0.0015** |
| Fable | 45 | 1 | 0.153 | **−0.0235** |

- **Astra's two programs are near-copies.** They differ in a few modal calls, and swapping their targets changes the loss by
  only 0.0015. Astra's advantage did not come from tailoring each program to its target.
- **Fable's two programs differ more, but in the wrong direction.** Its program written for Astra predicts Fable better than
  Fable's own-target program does (0.206 vs 0.288), so swapping the targets *lowers* Fable's loss.

Every program against both judges:

| Program | vs Astra | vs Fable |
|---|---|---|
| astra_for_astra | 0.2254 | 0.2677 |
| astra_for_fable | 0.2169 | 0.2563 |
| fable_for_astra | 0.2624 | **0.2060** |
| fable_for_fable | 0.2971 | 0.2878 |

**Exploratory and not registered:** each author's two programs both fit its *own model's* judge better than the other judge.

- Averaged over the two programs, the author × judge self-resemblance is +0.037 in Brier.
- It is positive in all six games, from +0.007 to +0.070.
- The registered crossover hides this pattern, because an author's resemblance to its own judge does not depend on which
  target the author was told to write for.
- With one program per cell, this could be a coincidence of two code samples. It would need several generations per cell to
  test.

## Secondary readouts (prespecified)

| Subset | B[A,A] | B[A,F] | B[F,A] | B[F,F] | Fable-target adv. | Astra-target adv. |
|---|---|---|---|---|---|---|
| 3 retested games, original labels | 0.239 | 0.272 | 0.287 | 0.274 | −0.002 | +0.048 |
| 3 retested games, retest labels | 0.227 | 0.274 | 0.272 | 0.291 | −0.017 | +0.045 |
| 3 other games | 0.212 | 0.240 | 0.238 | 0.302 | −0.061 | +0.026 |

**The 42 stable disagreements** (11 Astra–Astra, 14 Fable–Fable, 17 Qwen–Qwen). On each of these, the two judges forecast
opposite shapes and each repeated its forecast on retest. Item-level Brier:

| Program | vs Astra | vs Fable |
|---|---|---|
| astra_for_astra | 0.220 | 0.338 |
| astra_for_fable | 0.215 | 0.327 |
| fable_for_astra | 0.392 | 0.213 |
| fable_for_fable | 0.344 | 0.280 |

On these 42 items, did each author give the higher STAR probability to whichever judge repeatedly forecast STAR?

- **Astra:** 21 right, 21 wrong, 0 ties (chance).
- **Fable:** 16 right, 23 wrong, 3 ties.

Neither author's pair of programs separates the two judges where they reliably disagree.

**Separate descriptive check: actual player moves.** Brier against the actual player moves is 0.260–0.316 for all programs,
no better than a constant 0.5 in this matching-pennies setting. This is not the registered target.

## What the programs used (read after scores were frozen)

All four programs model the **players**, not a particular observer:

- recency-weighted frequencies;
- repeat, alternation and period rules;
- copying or opposing the opponent's last move;
- win-stay/lose-shift with empirical stay rates;
- streak detection.

Each adds a small STAR lean at round 1, citing the example JSON ({"player_1":"STAR",…}).

- **Astra's two programs** differ mainly in how their heuristics are weighted. Both sharpen the result toward a categorical
  forecast.
- **Fable's program for Astra** adds a strategic layer: Player 1 tries to match Player 2's expected move, and Player 2 tries to
  mismatch. That program fits Fable's own forecasts best of all four (0.206).
- **Fable's program for Fable** relies on win-stay/lose-shift and streaks, and is the worst of the four.

Neither author wrote anything specific to the identity of the observer named in the prompt. Both treated "predict this
observer" as "predict what a reasonable observer would expect the players to do".

These programs predict a judge's **public report**, its one-word forecast, from public history. A fit, or a failure to fit,
says nothing about the judge's private reasoning. Agreeing with a forecast is also not the same as reproducing the reasons
for it.

## Run record

- **Inputs:**
  - `btss-20261011/predictions.csv` (primary) and `btss-retest-20261011/predictions.csv`;
  - the Experiment 1 matching-pennies game log via `blind_twin_selfself.judge.load_games()`.
  - Hashes are in `plan/run_plan.json`.
  - Acceptance checks reproduced:
    - 240 paired items and 120 retest items;
    - 42 stable disagreements (11/14/17);
    - no invalid archived forecasts.
- **Author calls:** OpenRouter, one isolated request per cell, 2026-11-04.
  - `openai/gpt-6-astra` was pinned to provider `openai` and returned by OpenAI.
  - `anthropic/claude-fable-5.1` was pinned to `anthropic` and returned by Anthropic.
  - Both had fallbacks off, reasoning effort low (excluded from the response), no temperature, no tools and max_tokens 4000.
  - All four finished with `stop`.
  - **Billed $0.321** (Astra $0.071 + $0.058; Fable $0.074 + $0.118). Hard cap $5; worst-case reservation $0.83.
  - Generation ids are in `responses/calls.jsonl`.
- **Version limit:** the OpenRouter slugs are not dated snapshots. Pinned providers and prices match the 2026-10-11 archive
  snapshot, but identical weights to the archived judges cannot be verified.
- **Parsing:** Astra returned bare source and Fable one enclosing ```python fence; both were accepted by the fixed parser.
  Programs were hashed and committed (`9b42f9d`) before validation or scoring. None was regenerated or edited.
- **Validation:**
  - All four passed the contract on 46 synthetic histories, including empty and 19-round histories.
  - Each check ran two passes in one process and a reversed pass in a second process.
  - Every output was a deterministic pair of finite numbers in [0, 1].
- **Deviations:**
  1. No container runtime exists on this host, so generated code ran in a separate isolated-mode Python process with these
     limits:
     - no environment variables except SYSTEMROOT (no credentials) and a fresh empty working folder;
     - a Windows Job Object (512 MB, no child processes);
     - an in-process audit hook refusing file opens, sockets, subprocesses, ctypes and imports other than `math`;
     - time limits.

     Network access was blocked in-process, not by an OS firewall.
  2. The observer prompt's history and round number are neutral placeholders. The history placeholder spells out the
     original rendering, including "None. This is the first round." (`prompts.py`).
- **Incomplete cells:** none.

## Reproduce with zero API calls

```bash
PYTHONPATH=src python -m blind_twin_forecast_prediction validate   # contract on synthetic histories
PYTHONPATH=src python -m blind_twin_forecast_prediction score      # hash-checked programs x archived labels -> scoring/
pytest tests/test_blind_twin_forecast_prediction.py
```
