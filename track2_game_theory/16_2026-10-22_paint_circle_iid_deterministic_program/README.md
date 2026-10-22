# 16 · "Deterministic" vs "random" computer program against a fixed random opponent (2026-10-22)

| | |
|---|---|
| Track | 2: game theory (complementary to track 1) |
| Tag | `IID_DETERMINISTIC_PROGRAM` |
| Run ID | `iid-deterministic-20261022` |
| Game and models | Paint-and-circle matching pennies. A = Fable (`anthropic/claude-fable-5.1`, effort low). B = the same three seeded random (IID) strings as folder 15; no model, no API calls. |
| Size and cost | 2 labels × 3 sessions × 100 rounds = 600 Fable calls, $6.70 (cap $7) |
| Previous / next | [← 15 Identity framing vs random opponent](../15_2026-10-21_paint_circle_iid_identity_framing/) · [17 Entropy-gradient pilot →](../17_2026-10-22_paint_circle_entropy_gradient/) |

## What was done

This is a control for folder 15. There, the mindless labels ("a dead salmon", "a random computer program") made Fable streaky and predictable, while agent labels made it less predictable. "Random computer program" is both mindless *and* random, so this experiment adds a label that is mindless but not random:

- **New:** "The other decision-maker is a deterministic computer program." This is one word changed from the random-program wording, and the disclosure is otherwise identical.
- **Same-day re-run:** "The other decision-maker is a random computer program."

Both labels faced the same three random strings as folder 15 (string *k* in session *k*). The question and both possible outcomes were written into [`plan.json`](iid-deterministic-20261022/plan.json) before any call:
- **If mindlessness drives the effect,** the deterministic label should look like the random-program label: high PI_A.
- **If "random" drives it,** the deterministic label should be lower, nearer the agent labels.

**Note on the run:** it was interrupted when the controlling session ended. Two deterministic-label sessions stopped at rounds 86 and 76, and were resumed from their last logged round. Rounds still waiting on a response when the run was interrupted were re-requested, so no round is missing or duplicated.

## Results

All 100 rounds, mean of 3 sessions. Folder 15 rows are from the previous day, for comparison.

| Fable told | PI_A (own predictability) | PI_A by string 1 / 2 / 3 | Switch rate | Win-stay | Lose-shift | Tokens per answer | Says "pattern" |
|---|---|---|---|---|---|---|---|
| **deterministic computer program** | **.33** | .31 / .61 / .06 | .30 | .81 | .42 | 216 | 63% |
| random computer program (re-run) | .57 | .58 / .71 / .41 | .12 | .95 | .20 | 78 | 18% |
| *folder 15: random computer program* | *.54* | *.62 / .73 / .29* | *.15* | *.94* | *.25* | | |
| *folder 15: nothing* | *.43* | *.40 / .69 / .21* | *.21* | *.91* | *.33* | | |
| *folder 15: agent / self / other* | *.26–.32* | | *.27–.30* | *.82–.86* | *.43–.44* | | |
| *folder 15: dead salmon* | *.62* | *.61 / .76 / .48* | *.12* | *.96* | *.21* | | |

- **The random-program effect replicates.** The same-day re-run gives PI_A .57, against .54 in folder 15. It stays high on every string.
- **"Deterministic" makes Fable play like it does against an agent.** PI_A is .33, alongside the agent labels (.26–.32) and below "nothing" (.43), not with "random program" (.54–.57) or "dead salmon" (.62). Switching and lose-shift match the agent labels too. The ordering holds within each string.
- **Fable treats a deterministic program as something to decode.** It says "pattern" in 63% of answers, against 18% for the random program, and its answers are almost three times as long (216 vs 78 tokens).

**Interpretation:** folder 15's split is not agent vs non-agent; it tracks whether Fable expects the source to have *structure worth modelling*.
- **Sources described as having a policy:** another decision-maker, another instance of itself, a different language model, a deterministic program. Fable searches for rules, shifts after losses, and is harder to predict.
- **Sources described as random or mindless:** a random computer program, a dead salmon. Fable settles into streaks.
- **The actual opponent sequence is identical in every case.** As in folders 11, 14 and 15, "self" is just one of the structure-implying labels.

## Open questions

- **Rule-hunting payoff:** against an opponent that *does* have learnable structure but is noisy (e.g. 80% double-alternation), does the "deterministic" belief help, by making Fable look for rules, or hurt, by making it chase noise?
- **Other models:** does the same belief effect appear for Astra or Qwen?

## Files

- [`iid-deterministic-20261022/plan.json`](iid-deterministic-20261022/plan.json): the 6 sessions, the strings, both prompts with SHA-256 hashes, caps, and the predictions recorded before the run.
- `iid-deterministic-20261022/fable-vs-script__A-<label>__IID_<seed>__s<k>/rounds.jsonl`: every round, with Fable's full response.
- [`iid-deterministic-20261022/analysis/`](iid-deterministic-20261022/analysis/): per-session tables (`scripted_pilot_sessions.csv`, `scripted_pilot.json`) and `win_rate_bins.png`.
- Code:
  - `src/paint_circle/game.py`: new `deterministic` identity sentence.
  - `src/paint_circle/scripted.py`, `src/paint_circle/scripted_pilot.py`, `src/paint_circle/run.py`.
- Tests: `tests/test_paint_circle.py` checks that the deterministic prompt differs from the random-program prompt by exactly one word.

## Re-running

```bash
PYTHONPATH=src python -m paint_circle.scripted_pilot track2_game_theory/16_2026-10-22_paint_circle_iid_deterministic_program/iid-deterministic-20261022
```
