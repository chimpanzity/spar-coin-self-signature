# 15 · Identity framing against a fixed random opponent (2026-10-21)

| | |
|---|---|
| Track | 2: game theory (complementary to track 1) |
| Tag | `IID_IDENTITY_FRAMING` |
| Run ID | `iid-identity-framing-20261021` |
| Game and models | Paint-and-circle matching pennies. A = Fable (`anthropic/claude-fable-5.1`, effort low). B = a pre-generated random (IID) STAR/TRIANGLE string; no model, no API calls. |
| Size and cost | 6 conditions × 3 sessions × 100 rounds = 1,800 Fable calls, $14.75 (cap $16). 8 calls hit provider rate limits (HTTP 429) and were retried at no cost; Fable gave no unusable answers. |
| Previous | [← 14 Identity framing vs scripted pattern](../14_2026-10-21_paint_circle_scripted_identity_framing/) |

## What was done

This repeats folder 14's design, but the circle now plays a fixed random string instead of a pattern.

- **The opponent:** three random strings were generated from fixed seeds, 100 fair STAR/TRIANGLE draws each:

| Seed | P(TRIANGLE) | Runs z |
|---|---|---|
| 20261021 | .54 | −0.14 |
| 20261022 | .59 | −0.49 |
| 20261023 | .47 | +0.64 |

  Session *k* used string *k* in every condition, so all six conditions faced exactly the same opponent sequences.
- **The conditions:** the same six as folder 14, with the same disclosure wording: told nothing, another decision-maker ("agent"), another instance of yourself ("self"), a different language model ("other"), a dead salmon, a random computer program. All identity statements are false.
- **The measurement:** a random opponent cannot be exploited, so this measures what the labels do to **Fable's own strategy**: its predictability (PI_A), whether it paints where the circle last landed, switching, win-stay/lose-shift, and side bias.
- **Fixed in [`plan.json`](iid-identity-framing-20261021/plan.json) before any call:** the design, the three strings and the measures.

## Results

All 100 rounds, mean of 3 sessions, from [`iid-identity-framing-20261021/analysis/`](iid-identity-framing-20261021/analysis/):

| Fable told | PI_A (own predictability) | Switch rate | Win-stay | Lose-shift | Follows last landing | P(TRIANGLE) | Win | Tokens per answer | Mentions the label |
|---|---|---|---|---|---|---|---|---|---|
| nothing | .43 | .21 | .91 | .33 | .65 | .65 | .54 | 75 | — |
| agent | .32 | .28 | .86 | .44 | .68 | .62 | .54 | 98 | 26% |
| self | .30 | .27 | .85 | .43 | .67 | .61 | .55 | 98 | 42% |
| other | .26 | .30 | .82 | .43 | .65 | .62 | .52 | 100 | 80% |
| salmon | .62 | .12 | .96 | .21 | .61 | .60 | .52 | 85 | 99% |
| program | .54 | .15 | .94 | .25 | .62 | .66 | .53 | 79 | 37% |

**PI_A for each opponent string** (the same string across each row):

| String | nothing | agent | self | other | salmon | program |
|---|---|---|---|---|---|---|
| 1 (seed …21) | .40 | .22 | .15 | .18 | .61 | .62 |
| 2 (seed …22) | .69 | .58 | .58 | .57 | .76 | .73 |
| 3 (seed …23) | .21 | .15 | .15 | .04 | .48 | .29 |

- **The labels split by whether they describe an agent.**
  - **Agent labels** (another decision-maker, self, a different language model) made Fable less predictable than when told nothing (PI_A .26–.32 vs .43). It switched more and shifted more after losses.
  - **Non-agent labels** (dead salmon, random program) made it more predictable (PI_A .54–.62). It stuck with its choices and rarely shifted after a loss: it treated the circle as mechanical.
  - **The ordering holds within every string:** agent labels below "nothing", non-agent labels above. The string itself sets the overall level; string 2, with a long early TRIANGLE streak, gives higher PI everywhere.
- **"Self" is not special.** Self (.30) sits between agent (.32) and other (.26) on every measure, consistent with folders 11 and 14.
- **Unlike against the pattern (folder 14), Fable talks about the label a lot here.** "A different language model" is mentioned in 80% of answers and the dead salmon in 99%. Agent labels lengthen answers by about 25 tokens.
- **Fable's baseline strategy against noise is streaky and biased.** It shows a strong win-stay (.91), a TRIANGLE preference (.60–.66), and paints where the circle last landed about 65% of the time. Win rates of .52–.55 reflect this luck-matching against these particular strings, not exploitation. The shadow benchmark on the strings is .51.

**Interpretation:** when there is no pattern to exploit, what Fable believes about the source changes how it plays. Believing it faces an agent makes it play more like a mixed strategy: less predictable, more shifting. Believing it faces something mindless makes it settle into streaks. This is a belief-about-agency effect, not a self-specific one. It complements folder 14, where a clear pattern overrode every label.

## Open questions

- **How far does the effect extend?** Does the agent/non-agent split hold for other models (Astra, Qwen)? And with an adaptive opponent, where predictability is punished?
- **Is the effect only about agency?** "Random computer program" is both non-agent and explicitly random. A "deterministic computer program" label would separate the two.
- **How reliable is it?** There are 3 sessions per condition and three strings, so this is descriptive only; the within-string consistency is the main reason to take it seriously.

## Files

- [`iid-identity-framing-20261021/plan.json`](iid-identity-framing-20261021/plan.json): 18 sessions, the three strings in full, Fable's exact prompts with SHA-256 hashes, caps, and the analysis fixed in advance.
- `iid-identity-framing-20261021/fable-vs-script__A-<condition>__IID_<seed>__s<k>/rounds.jsonl`: every round, with Fable's full response.
- [`iid-identity-framing-20261021/analysis/`](iid-identity-framing-20261021/analysis/):
  - `scripted_pilot_sessions.csv` and `scripted_pilot.json`: per session, full and late windows, with the strategy measures.
  - `win_rate_bins.png`: one averaged line per condition.
- Code:
  - `src/paint_circle/scripted.py`: `iid_string`, and `move` with `IID_<seed>` scripts.
  - `src/paint_circle/scripted_pilot.py`: strategy measures added.
  - `src/paint_circle/run.py`.
- Tests: `tests/test_paint_circle.py`.

## Re-running

```bash
PYTHONPATH=src python -m paint_circle.scripted_pilot track2_game_theory/15_2026-10-21_paint_circle_iid_identity_framing/iid-identity-framing-20261021
```
