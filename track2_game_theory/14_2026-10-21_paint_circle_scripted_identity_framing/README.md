# 14 · Identity framing against a fixed scripted opponent (2026-10-21)

| | |
|---|---|
| Track | 2: game theory (complementary to track 1) |
| Tag | `SCRIPTED_IDENTITY_FRAMING` |
| Run ID | `identity-framing-20261021` |
| Game and models | Paint-and-circle matching pennies. A = Fable (`anthropic/claude-fable-5.1`, effort low). B = a local script playing the double-alternation S S T T … (no model, no API calls). |
| Size and cost | 6 conditions × 3 sessions × 100 rounds = 1,800 Fable calls, 0 rejected answers, $12.13 (cap $16) |
| Previous / next | [← 13 Scripted-opponent pilot](../13_2026-10-21_paint_circle_scripted_opponent_pilot/) · [15 Identity framing vs random opponent →](../15_2026-10-21_paint_circle_iid_identity_framing/) |

## What was done

The opponent's behaviour was held perfectly constant, and only what Fable was told about the source of that behaviour changed.

- **The opponent:** in every session, the circle followed the same scripted double-alternation. Two of the three sessions per condition started S S T T and one started T T S S.
- **The wording:** Fable received the usual 5 verbal rows and a 50-round grid. The disclosure wording is identical to the earlier paint-and-circle experiments (folders 10–12); only the identity sentence differs.

| Condition | What Fable was told about the circle-placer |
|---|---|
| nothing | (no statement) |
| agent | "Another decision-maker decides where the blue circle lands." |
| self | … "The other decision-maker is another instance of yourself, the same language model." |
| other | … "The other decision-maker is a different language model." |
| salmon | … "The other decision-maker is a dead salmon." |
| program | … "The other decision-maker is a random computer program." |

- **Every identity statement is false:** the opponent is a script.
- **Salmon and program are framing controls,** and implausible ones: a dead salmon can't decide, and a "random" program contradicts an obvious pattern.
- **Session 1 of each condition** served as the feasibility screen.
- **Fixed in [`plan.json`](identity-framing-20261021/plan.json) before any call:** the conditions, measures and descriptive analysis.

## Questions

- Does believing a language model (or itself) generates the circle make Fable give up, or delay, exploiting a pattern it can see?
- If any label disrupts exploitation, is the disruption specific to "self"?

## Results

Means of 3 sessions per condition, from [`identity-framing-20261021/analysis/scripted_pilot_sessions.csv`](identity-framing-20261021/analysis/scripted_pilot_sessions.csv):

| Fable told | Win, rounds 1–100 | Win, rounds 51–100 | Rounds lost per session | Last loss (each session) | PI_A, rounds 51–100 | Tokens per answer |
|---|---|---|---|---|---|---|
| nothing | .960 | .993 | 4, 3, 5 | 7, 7, 58 | .95 | 52 |
| agent | .963 | 1.000 | 4, 3, 4 | 7, 5, 7 | 1.00 | 62 |
| self | .957 | .980 | 5, 5, 3 | 74, 88, 86 | .91 | 63 |
| other | .960 | .987 | 3, 4, 5 | 48, 7, 55 | .92 | 62 |
| salmon | .943 | .980 | 6, 6, 5 | 58, 54, 82 | .89 | 63 |
| program | .940 | .973 | 9, 4, 5 | 86, 76, 8 | .86 | 62 |

- **The pattern wins over the framing in every condition.** Fable won 94–96% of all rounds and 97–100% of rounds 51–100 under every label. It learned the pattern within the first 7 or so rounds in all 18 sessions.
- **No label made Fable abandon exploitation.** The disclosure statements cost at most about 1–2 extra lost rounds per session.
- **The small differences are not specific to "self".** Under the identity labels (self, other, salmon, program), sessions more often lost one or two rounds late in the game, after round 40. Their late predictability was a little lower (PI_A .86–.92, vs .95–1.00 for nothing and agent). But "self" was no different from "other", and the implausible labels (salmon, program) did as much or more.
- **The late losses are phase-counting slips, not strategic departures.** Fable states the correct S S T T pattern and then misplaces its position within the pair, for example "most recent is T (second T in pair)" when it was the first T. The same slip happens twice when Fable is told nothing. None of the late-loss responses mention the opponent's identity.
- **The labels are rarely discussed.** Responses mention the stated identity in 4–12% of rounds (salmon most often; e.g. "The dead salmon isn't making decisions, so … random"). Any disclosure lengthens answers by about 10 tokens.
- **The shadow predicts the script perfectly after round 50** (shadow win 1.00), so EI_A ≈ win rate here (.95–1.00). The ceiling issue noted in folder 13 applies.

**Interpretation, using the outcomes listed in the proposal:** this is "Fable continues winning nearly 100%". Observable regularities dominate identity framing. The residual effects are small, appear for every identity label including the implausible ones, and look like increased phase-tracking errors rather than a strategic shift towards unpredictability. There is no evidence of a self-specific strategic expectation.

## Open questions

- **Noisier opponents:** with a pattern this easy, any belief effect has little room to show. A noisy or adaptive scripted opponent (e.g. 80% double-alternation) would test whether framing changes how much Fable trusts an imperfect pattern.
- **Phase slips:** do the identity labels increase phase-counting slips reliably? With 3 sessions per condition and 1–2 slips per session, this is only suggestive.

## Files

- [`identity-framing-20261021/plan.json`](identity-framing-20261021/plan.json): 18 sessions; Fable's exact prompt for each condition with SHA-256 hashes; caps; cost estimate; the analysis fixed in advance.
- `identity-framing-20261021/fable-vs-script__A-<condition>__<script>__s<k>/rounds.jsonl`: every round, with Fable's full response.
- [`identity-framing-20261021/analysis/`](identity-framing-20261021/analysis/):
  - `scripted_pilot_sessions.csv`: per session, full and late windows, including learning onset.
  - `scripted_pilot.json`: the same numbers.
  - `win_rate_bins.png`: win rate in 10-round bins.
- Code (same as folder 13):
  - `src/paint_circle/scripted.py`, `src/paint_circle/run.py`
  - `src/paint_circle/scripted_pilot.py`, which adds the learning-onset measures
- Tests: `tests/test_paint_circle.py`.

## Re-running

```bash
PYTHONPATH=src python -m paint_circle.scripted_pilot track2_game_theory/14_2026-10-21_paint_circle_scripted_identity_framing/identity-framing-20261021
```
