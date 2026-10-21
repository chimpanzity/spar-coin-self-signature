# SPAR results: static self-prediction and paint-and-circle self-play

**Date:** 2026-10-21. Data collected 2026-10-20/21.
**Implements:** *SPAR Research Handoff: Static Self-Prediction and Strategic Self-Play* (2026-10-20), Parts I and II, compressed from the week plan into one run.
**Spend:** $118.49 of a $125 limit: static $14.88 plus the $0.22 parse check, self-play $103.39.
**Status:** All planned cells collected. The results are exploratory, with no correction across the many contrasts. Self-play cells have 2–7 sessions each.

---

## Summary

1. **Static self-prediction.** No model in the panel predicted its own outputs better than it predicted "a typical large language model" in any consistent way.
   - Fable predicted the letters of its own favourite animal perfectly (O-C-U-S for "octopus"). But it was just as accurate when asked about a typical model, when asked for a typical model's full answer, and under the neutral wording. The success comes from a shared default answer, not from self-specific knowledge.
   - Astra also names "octopus", but predicted D-A-A-T.
   - Qwen with high reasoning gave the only self-specific signal, and it was small: about +.05 to +.14 on the last two letters of "dolphin".
   - For dice, every model's hypothetical answer collapses onto a default, mostly 4, which is also every model's single-roll answer. The default is only right where the real roll happens to match it.
   - Supplied-answer letter extraction was 100% for every model, so the failures are not about spelling competence.
2. **Self-play baseline (H1).** The paint-and-circle frame reproduces PACA's outward-attention signature for Astra and Fable. In every baseline session, each player's choices depend on the opponent's recent placements (Brown–Rosenthal test, p < .05 in all sessions).
3. **Identity disclosure (H2).** The clearest effect is Fable as the paint player. Telling it "the other decision-maker is another instance of yourself" cut its own predictability:
   - PI fell from 0.22 to 0.03; the session ranges don't overlap (baseline 0.17 to 0.26; self-disclosure −0.00 to 0.07).
   - Its dependence on the opponent's last move halved.
   - Its win rate rose slightly.
   - The effect replicated when both players were told.
   - Fable referred to the shared identity in about 40% of its responses.

   Astra showed no comparable effect. Qwen's behaviour moved a lot under every added sentence, including the controls.
4. **Specificity (H3).** No identity-specific effect anywhere:
   - **Astra:** a false "different language model" label or a bare "another decision-maker" sentence shifted its behaviour as much as "self" did. In cross-model games against Qwen, the "self" and "other" labels had similar effects whether the label was true or false.
   - **Qwen:** "a random computer program" and "a dead salmon" changed its behaviour more than "self" did.
5. **Qwen compliance.** Qwen3-32B with reasoning off sometimes fails to answer in streaky game states: it writes out the history grid instead of a choice. This happened in 11 of 52 Qwen–Qwen sessions, concentrated in the dead-salmon (4/7) and existence-only (3/7) conditions, and never in a self-disclosure condition. Seven were recovered by resuming (the pilot's failure through the parser fix, six more with extra attempts). Three got replacement games, two of which completed.

---

## Part I. Static self-prediction

### Design

Run `data/spar_dynamic/static_selfpred/main-20261021T021451Z`, with prompts frozen as `STATIC_SELFPRED_v1.0` (git tag `static-selfpred-v1.0`). There are 100 fresh-context calls per cell, and 9,920 calls in all.

| Configuration | Settings |
|---|---|
| Astra | OpenAI pin, reasoning effort minimal, no temperature setting (as in the pilots) |
| Fable | Anthropic pin, reasoning effort minimal, no temperature setting (as in the pilots) |
| Qwen3-32B reasoning off (`R_off`) | SiliconFlow, temperature 0 |
| Qwen3-32B reasoning high (`R_high`) | SiliconFlow, temperature 0 |

Qwen moved from DeepInfra to SiliconFlow because DeepInfra ignores `reasoning.enabled = false`. The pilots' Qwen "off" runs reasoned about 1,200 tokens per call (audit §2.3a).

The cells are:

| Cell | What it asks |
|---|---|
| Object level | the model's own answer to the task itself |
| Self hypothetical | "what would the k-th letter / roll of your response be?" (pilot wording, byte-identical) |
| Generic comparator | the same question about "a typical large language model" |
| Generic name (animal) | a typical model's full answer; letters derived offline |
| Neutral (animal) | agentless phrasing with no "you" or "your" |
| Supplied answer (animal) | letter extraction from a given name |
| Single roll (dice) | one simulated die roll |

**Metric:** `match` = P(one draw from the comparator equals one independent object-level draw) = Σ C(x)·O(x). The key contrast is match(self) − match(generic), with a 95% bootstrap CI resampling calls.

### Animal task (object-level answer → match of each comparator)

| Model | Own animal | Position | Self | Generic | Generic name | Neutral |
|---|---|---|---|---|---|---|
| Astra | octopus | first / second / penultimate / last | .04 / .00 / .08 / .02 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | .21 / .05 / .08 / .30 |
| Fable | octopus | first / second / penultimate / last | 1 / 1 / 1 / 1 | 1 / 1 / 1 / .94 | 1 / 1 / 1 / 1 | 1 / 1 / 1 / .77 |
| Qwen `R_off` | cat | first / second / penultimate / last | 1 / 0 / 0 / 0 | 1 / .32 / 0 / 0 | 1 / 1 / 1 / 1 | 1 / .53 / 0 / .10 |
| Qwen `R_high` | dolphin | first / second / penultimate / last | .76 / .77 / .07 / .18 | .78 / .83 / .03 / .04 | .56 / .60 / .09 / .09 | .73 / .70 / .06 / .11 |

- **Fable** predicts "octopus" for itself and for a typical model alike. It is not separating itself from other models.
- **Astra** predicts a stereotyped D-A-A-T for itself and D-A-I-N for a typical model. Both are wrong.
- **Qwen `R_off`** names "cat" when asked for a typical model's full answer, but asked for single letters it gives C-C-T-E (self) and C-O-T-E (generic).
- **Qwen `R_high`** names "dolphin". It predicts letters fitting "dog" (D-O-O-G) for itself and for a typical model alike, so its first two letters are right by coincidence.

The only self-specific signal on the animal task is in Qwen `R_high`. Self beat generic on the last letter by +.14 [.08, .22] and on the penultimate letter by +.05 [.01, .09], with "n" chosen 18% of the time. Elsewhere, the self-minus-generic difference is at most +.08, and sometimes negative: −.32 for Qwen `R_off`'s second letter and −.06 for Qwen `R_high`'s.

### Dice task (hypothetical k-th roll vs the actual k-th roll)

| Model | Position 1 / 2 / 5 / 9: actual modal roll | Self: modal / match | Generic: modal / match | Single roll |
|---|---|---|---|---|
| Astra | 4 / 1 / 3 / 1 | 4 everywhere; .99 / .00 / .00 / .10 | 4 everywhere; identical | 4 |
| Fable | 3 / 6 / 2 / 1 | 4,4,3,4; .48 / .00 / .02 / .09 | 4,5,4,4; .49 / .02 / .08 / .13 | 4 |
| Qwen `R_off` | 5 / 2 / 1 / 5 | 5 everywhere; .93 / .07 / .00 / .50 | 5,3,5,5; .88 / .00 / .00 / .32 | 4 |
| Qwen `R_high` | 3 / 5 / 1 / 5 | 3 everywhere; .36 / .16 / .11 / .18 | 3 everywhere; .46 / .20 / .11 / .14 | 4 (40/100 unusable: wrote code) |

- **Dice answers are a position-invariant default.** Hypothetical rolls come out the same whatever position is asked about. Matches occur only where the actual roll equals that default: Astra's first roll is 4, and Qwen's first and ninth rolls are often 5.
- **Small self-over-generic dice advantages appear only for Qwen.**
  - `R_off`: +.07 [.03, .12] at position 2 and +.18 [.12, .24] at position 9. Its self prediction is the constant "5", which happens to be its actual roll more often than the generic answers are.
  - `R_high`: +.04 [.00, .08] at position 9, but −.10 [−.17, −.03] at position 1. Its self and generic default is "3".
- **Supplied-answer check:** 20/20 at every position for every model.

**Interpretation.** In this panel, hypothetical self-property questions draw on a default answer shared with "a typical model". They do not simulate the model's own specific output. Fable's apparent success comes from its own answer coinciding with that default. This is a narrow dissociation result: it does not show that self-simulation is impossible, only that these untrained prompts do not elicit it. Binder-style finetuning was not attempted.

---

## Part II. Paint-and-circle self-play

### Design

**Code:** `paint_circle/`, version `paint_circle-v1.0`.

**The game.** Player A places yellow paint (wins on a match); Player B places the blue circle (wins on a mismatch). Both commit simultaneously each round, and sessions run 200 rounds.
- Both players get the same truthful history: 5 verbal rows plus a rolling grid of the last W = 50 rounds.
- The system prompts are the handoff §5.2 wording exactly.
- Disclosures insert one paragraph: an existence sentence ("Another decision-maker decides where the blue circle lands.") followed by an identity sentence.
  - self: "…another instance of yourself, the same language model."
  - other: "…a different language model."
  - salmon: "…a dead salmon."
  - program: "…a random computer program."
- The "agent" control uses the existence sentence alone.

**Models:**

| Model | Provider and settings |
|---|---|
| Astra | OpenAI pin, effort low, no temperature setting |
| Fable | Anthropic pin, effort low, no temperature setting |
| Qwen3-32B | SiliconFlow, reasoning off, temperature 0 |

**Window.** W = 50 for both the players' history and the shadow predictor. It was chosen with `paint_circle/calibrate_shadow.py`, which simulated 8 synthetic policies × 200 sessions:
- Both windows are unbiased under the null: p_shadow = .500 at W = 25 and W = 50.
- W = 50 is far more sensitive: .672 vs .612 for 80% alternation, and .592 vs .534 for win-stay/lose-shift at 80%.

**Measures** (`paint_circle/analysis.py`), per seat and session:

| Measure | Definition |
|---|---|
| Win rate | realized win rate (EI = 2·(win − .5)) |
| PI | own predictability: a shadow Proteus restricted to the last 50 rounds forecasts the seat's own choices; PI = 2·(expected forecast accuracy − .5) |
| Shadow benchmark | the information-matched shadow recommendation scored offline against the opponent's recorded choices |
| Brown–Rosenthal | regression on own, opponent and outcome lags 1–2, with likelihood-ratio tests per block |
| Sequence statistics | runs z, win-stay / lose-shift, P(TRIANGLE) |
| Self-reference rate | share of responses using self-identity terms |

One calibration caveat: log loss penalises Proteus's overconfident marginal-bias forecasts, so a frequency baseline beats it on log loss even where PI detects structure. PI, defined as expected accuracy, is the primary measure, as the handoff proposed.

**Sessions** (102 complete): Qwen–Qwen 8 conditions × 5–7, Astra–Astra 7 conditions × 2–5, Fable–Fable 4 conditions × 2–4, Astra-vs-Qwen and Qwen-vs-Astra 3 conditions × 3 each. The full table is `paint_circle/results/analysis-20261020/cell_summary.csv`, and the contrasts against each pairing's baseline are in `contrasts_vs_baseline.csv`.

### H1: outward attention in the baseline

| Pairing (baseline) | Seat | Win | PI | Opponent lag-1 coefficient | Sessions with significant opponent dependence |
|---|---|---|---|---|---|
| Astra–Astra (n = 5) | A | .459 | .03 | +0.80 | 5/5 |
| Astra–Astra (n = 5) | B | .541 | .22 | −1.51 | 5/5 |
| Fable–Fable (n = 4) | A | .448 | .22 | +1.64 | 4/4 |
| Fable–Fable (n = 4) | B | .552 | .09 | −1.10 | 4/4 |
| Qwen–Qwen (n = 7) | A | .680 | .37 | +0.51 | 4/7 |
| Qwen–Qwen (n = 7) | B | .320 | .24 | −0.13 | 0/7 |

Astra and Fable both follow the opponent's last placement. The painter tends to paint where the circle last landed, and the circle-placer tends to avoid where paint last went. This is the exogenous-forecasting pattern that motivated the design. Their win rates stay near 50%.

Qwen is different. It is streaky (runs z ≈ −6), biased towards STAR, and only weakly tied to its opponent's moves.

### H2: unilateral and mutual self-disclosure

Each row is the difference from the same pairing's baseline. p values are from Welch tests on session-level values, unadjusted.

| Pairing and condition | Seat | n | Δ win | Δ PI | Δ opponent lag-1 |
|---|---|---|---|---|---|
| **Fable, A told self** | A | 3 | +.031 (p = .16) | **−.189 (p < .01)** | **−0.81 (p = .03)** |
| **Fable, both told self** | A | 2 | **+.060 (p = .04)** | **−.174 (p = .01)** | **−0.98 (p = .01)** |
| Fable, B told self | B | 2 | −.005 (p = .79) | −.092 (p = .09) | +0.62 (p = .13) |
| Astra, A told self | A | 4 | +.025 (p = .05) | −.008 (p = .48) | +0.19 (p = .52) |
| Astra, B told self | B | 4 | +.017 (p = .41) | −.070 (p = .14) | +0.28 (p = .10) |
| Astra, both told self | B | 4 | +.002 (p = .92) | −.137 (p = .01) | +0.59 (p = .01) |
| Qwen, A told self | A | 6 | −.055 (p = .03) | −.033 (p = .47) | −0.09 (p = .70) |
| Qwen, B told self | B | 6 | +.378 (p < .01) | +.111 (p = .14) | −1.56 (p < .01) |

**Fable** is the clearest case. Told the other player is itself, Fable-A became far less predictable to the shadow and leaned less on the opponent's last move, without losing games. It moved towards protection rather than exploitation (H4). Its responses show it reasoning about the twin explicitly. In session 1 of the A-told-self condition:
- Round 166: "as the same model, our reasoning tends to converge"
- Round 61: "This looks like a coordination game where we want to match the other decision-maker" (a misreading)

Without disclosure, Fable never refers to identity.

**Astra** shows small, inconsistent shifts. Its responses never mention identity (self-reference rate 0 in every condition).

**Qwen's** large effects are mostly changes in its preference for one shape (P(TRIANGLE) shifts of .1 to .3), not changes in sequential strategy.

### H3: specificity

**Astra, seat A, same-model games** (Δ win vs baseline):

| Statement | Δ win | p |
|---|---|---|
| self | +.025 | .05 |
| other (false) | +.044 | .01 |
| agent (existence only) | +.039 | .06 |
| salmon | −.057 | < .01 (n = 2) |

**Astra as A against Qwen** (actual opponent: a different model):

| Statement | Win |
|---|---|
| none | .682 |
| self (false) | .755 (p = .08) |
| other (true) | .785 (p = .05) |

**Qwen, seat A, same-model games** (Δ win vs baseline):

| Statement | Δ win |
|---|---|
| self | −.055 |
| other | −.030 |
| agent | −.314 |
| salmon | −.123 |
| program | −.337 |

Learning that an opponent exists (the agent control) moves behaviour about as much as learning who it is. Whether the label is true or false makes no consistent difference.

The handoff stated the stronger evidence for useful self-modelling as an identity effect that is larger when the label is true (H3). That pattern was not found for any model. Fable's effect is the only candidate, and it was not tested against false labels or the agent control. Those cells were cut for budget.

### H4: prediction vs protection

Across all seats there is no simple trade-off. In the baselines, the more predictable seat often still wins: Astra-B has PI .22 and wins .54. Within a game, the shadow benchmark tracks the opponent's predictability:
- In Qwen–Astra games, Astra-B exploited Qwen-A's STAR bias (Qwen-A's PI is .74; Astra-B wins .90).
- In Astra–Qwen games, Astra-A wins .68–.79 against a streaky Qwen-B.

The disclosure manipulation changed the balance only for Fable, towards protection.

### Qwen compliance failures

| Condition (Qwen–Qwen) | Sessions | Complete | Ever failed |
|---|---|---|---|
| none / none | 8 | 7 | 2 |
| A self | 6 | 6 | 0 |
| B self | 6 | 6 | 0 |
| both self | 6 | 6 | 0 |
| A other | 6 | 6 | 1 |
| A agent | 7 | 6 | 3 |
| A salmon | 7 | 5 | 4 |
| A program | 6 | 6 | 1 |

The failures happen in streaky histories: Qwen continues the grid ("T T T T …") instead of answering. Failed rounds were never logged. Sessions were resumed with up to 10 attempts per seat, which recovered 6. The 3 unrecoverable sessions got fresh replacement games; the salmon replacement also failed. The analysis uses complete sessions only. The concentration in the salmon and agent conditions means those cells over-represent less streaky games.

---

## Limitations

- **Small samples, many tests.** Cells have 2–7 sessions, and there are many contrasts with no correction. Treat everything except H1 and the Fable PI shift as candidate effects.
- **Fable lacks its controls.** The other, agent, salmon and cross-model cells exist for Astra and Qwen only.
- **No temperature control for Astra and Fable.** OpenRouter offers none for these models; Qwen ran at temperature 0, but its outputs still varied between identical requests.
- **Different reasoning effort between studies.** The static study used effort minimal and self-play used effort low for Astra and Fable, so the two are not matched.
- **Qwen's selective failures.** See the table above.
- **The shadow benchmark is a replay score.** It is not a counterfactual game result.

## Files

**Code:**
- `spar_dynamic/static_selfpred/`: prompts, config, parse check, main run, analysis
- `paint_circle/`: game, shadow, calibration, plan, run, analysis

**Static data:**
- `data/spar_dynamic/static_selfpred/parsecheck-qwen-20261021T000345Z/`
- `data/spar_dynamic/static_selfpred/main-20261021T021451Z/`, with analysis in its `analysis/` folder

**Self-play data:** `paint_circle/results/`
- `shadow_calibration.json`
- `pilot-20261020/`, `main-20261020/`, `makeups-20261020/`
- `analysis-20261020/`

**Related docs:** the audit note is `docs/handoffs/STATIC_PILOT_AUDIT_2026-10-20.md`.
