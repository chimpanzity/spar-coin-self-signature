# Track 2: game theory (complementary to track 1)

**Question:** does knowing that another player is *the same model* change how a model reads or plays against it? This track runs the self-modelling question inside repeated games, mostly matching pennies (MP) and rock-paper-scissors (RPS).

This track started on Oct 9, after track 1's forecasting design hit a floor. Games force a committed choice every round and add a live opponent. It moved through three phases:

| Phase | Dates | Folders |
|---|---|---|
| A. Observing play | Oct 9–11 | 01–08 |
| B. Framing a generator as self | Oct 11 | 09 |
| C. Closed-loop self-play and scripted opponents | Oct 20–27 | 10–19 |

Each folder has its own README.

---

## Phase A. Observing play: can a model read its own play better when told it is its own? (Oct 9–11)

| # | Folder | What it asked | What we found |
|---|---|---|---|
| 01 | [`01_2026-10-09_blind_twin_v1_mp`](01_2026-10-09_blind_twin_v1_mp/) | "Blind Twin": a judge predicts each player's next move; does a true "this player is you" label help it predict its own model? (MP) | Most games were cut short by a strict answer parser; not interpretable |
| 02 | [`02_2026-10-09_blind_twin_v2_mp`](02_2026-10-09_blind_twin_v2_mp/) | Same, with a fixed parser | A small positive self-label effect (S = +4.2 pp) |
| 03 | [`03_2026-10-09_blind_twin_rps`](03_2026-10-09_blind_twin_rps/) | Same in RPS, three model pairs | A true label helps more than a false one in every run; Fable's self-judgments are the consistent contributor |
| 04 | [`04_2026-10-09_opponent_disclosure_pilot`](04_2026-10-09_opponent_disclosure_pilot/) | Does *telling a player* its opponent is itself change how it plays? (Astra vs Astra) | The told Matcher won about 5 pp more; no response mentions the self |
| 05 | [`05_2026-10-10_study1_exp1_disclosure`](05_2026-10-10_study1_exp1_disclosure/) | Study 1, Experiment 1: disclosure × self/other opponent, three models, RPS and MP | No overall self-specific effect. A Fable effect in RPS; a Qwen-driven negative effect in MP. Make-up games were needed for Qwen formatting failures. |
| 06 | [`06_2026-10-10_exp2_blind_twin_judges`](06_2026-10-10_exp2_blind_twin_judges/) | Experiment 2: Blind Twin judges on the Experiment 1 games | Small label effects, again driven by Fable judging Fable |
| 07 | [`07_2026-10-11_selfself_judges_and_retest`](07_2026-10-11_selfself_judges_and_retest/) | Are informed twins easier for a same-model observer to read? Plus a test-retest of the judges | No. Judges reproduce only 80% of their own predictions on identical prompts, which sets the noise floor for this whole phase. |
| 08 | [`08_2026-10-11_post_hoc_analyses`](08_2026-10-11_post_hoc_analyses/) | Offline: what is Fable's label effect worth, and where does it come from? | Worth about 24–32 of Fable's own games to a simple n-gram observer; it lives in games against *other* models. This is self-knowledge, not privileged access. |

**Where Phase A left us:** label effects exist, but they are small, Fable-specific, close to the judges' own noise floor, and reproducible by an outside observer given enough of the model's past play.

## Phase B. Framing a generator as self (Oct 11)

| # | Folder | What it asked | What we found |
|---|---|---|---|
| 09 | [`09_2026-10-11_paca_believed_self`](09_2026-10-11_paca_believed_self/) | In the PACA forecasting task, does telling a model the sequence comes from "another instance of your model" change its forecasts? | No consistent accuracy effect; small framing effects in opposite directions for Fable and Astra |

## Phase C. Closed-loop self-play: paint-and-circle matching pennies (Oct 20–21)

| # | Folder | What it asked | What we found |
|---|---|---|---|
| 10 | [`10_2026-10-20_paint_circle_selfplay`](10_2026-10-20_paint_circle_selfplay/) | Two copies of a model play 200-round matching pennies; does being told "the other is another instance of yourself" change play? (102 games; Astra, Fable, Qwen3-32B) | Astra and Fable track the opponent, replicating PACA's outward-attention pattern. Told "self", Fable became much less predictable (PI 0.22 → 0.03). No identity-specific effects for Astra or Qwen. |
| 11 | [`11_2026-10-21_paint_circle_fable_specificity`](11_2026-10-21_paint_circle_fable_specificity/) | Prespecified: is Fable's drop specific to "yourself"? | **No.** "A different language model" works almost as well (self vs other p = .19); only "another decision-maker exists" falls short (p = .008). |
| 12 | [`12_2026-10-21_paint_circle_fable_perspective`](12_2026-10-21_paint_circle_fable_perspective/) | Does asking Fable to take the other player's perspective make the self label matter? (feasibility, 2 games per cell) | Guidance makes Fable's play essentially unpredictable under *both* labels; the label adds nothing |
| 13 | [`13_2026-10-21_paint_circle_scripted_opponent_pilot`](13_2026-10-21_paint_circle_scripted_opponent_pilot/) | Pilot to validate the measures: can Fable exploit a scripted circle player that alternates (S T S T) or double-alternates (S S T T)? | Yes, almost immediately: it lost 2–4 rounds per session, all in the first 7. The shadow Proteus detects both patterns but more slowly, so Fable beats it over the full game. Exploiting made Fable perfectly predictable (PI_A = 1). |
| 14 | [`14_2026-10-21_paint_circle_scripted_identity_framing`](14_2026-10-21_paint_circle_scripted_identity_framing/) | Same scripted S S T T opponent in every condition; does telling Fable it is itself, another model, a dead salmon or a random program stop it exploiting the pattern? | No. Fable won 94–96% under every label. The labels add only a few late phase-counting slips, no more for "self" than for "other" or the implausible labels. |
| 15 | [`15_2026-10-21_paint_circle_iid_identity_framing`](15_2026-10-21_paint_circle_iid_identity_framing/) | The same six labels against a fixed random string (nothing to exploit): do they change Fable's own strategy? | Yes, split by agency. Agent labels (decision-maker, self, other model) make Fable less predictable (PI .26–.32 vs .43); mindless labels (salmon, random program) make it streakier (PI .54–.62). "Self" is not special. |
| 16 | [`16_2026-10-22_paint_circle_iid_deterministic_program`](16_2026-10-22_paint_circle_iid_deterministic_program/) | Control for 15: does a "deterministic computer program" label act like the mindless labels? | No. It acts like the agent labels (PI .33). Fable hunts for a rule: it says "pattern" in 63% of answers. The real split is expected structure (agent, self, other model, deterministic program) vs randomness (random program, salmon). |
| 17 | [`17_2026-10-22_paint_circle_entropy_gradient`](17_2026-10-22_paint_circle_entropy_gradient/) | Calibration pilot, no labels: how do Fable's exploitation and own predictability change as noise is added to the S S T T opponent (ε = 0 to .50)? | Fable keeps the pair rule at ε = .10 but loses its place after flips (win .70 vs a possible .84–.89). Between ε = .10 and .20 it abandons the pattern for run/frequency heuristics (win .52 vs .76). The shadow benchmark cannot see the pattern beyond ε = .10. |
| 18 | [`18_2026-10-22_paint_circle_entropy_gradient_replication`](18_2026-10-22_paint_circle_entropy_gradient_replication/) | Replication at ε = .10 and .20 (reversed phase, fresh seeds) | The break replicates: at 20% noise Fable abandons the pattern in all 3 sessions (EI_oracle .15 / .08 / −.27); at 10% it captures most of the available advantage (.59 / .83 / .87). |
| 19 | [`19_2026-10-27_paint_circle_noise_label_predictability`](19_2026-10-27_paint_circle_noise_label_predictability/) | 3 noise levels × 3 labels (none / self / other LLM), the same script under each label, plus a prospective shadow Proteus forecasting Fable: do labels change exploitation and exploitability? | At ε = .10 any LLM label reduced exploitation, self most (wins .72 / .60 / .52), and predictability moved with it. At ε ≥ .15 Fable is near chance regardless. The self–other gap is within session noise: a replication candidate, not a finding. |

## What track 2 shows so far

1. **Identity labels change behaviour, but not because the identity is "self".** In every specificity test (05, 08, 11, 12), effects attributed to "self" also appear for other model labels or general framing.
2. **Fable is the consistently responsive model, as in track 1.** But its responses track how the opponent is described (as a language model) and what it is asked to think about, not whether the opponent really is Fable.
3. **The measurement noise floor matters.** Judge test-retest (07) and per-cell session counts limit what single runs can show.

## How this complements track 1

Track 1 asks whether a model can predict its own outputs in isolation; track 2 asks whether self-identity information is *used* in interaction. Both tracks reach the same conclusion so far: models act on general knowledge about language models and on how a question is framed, with no reliable evidence of self-specific knowledge.

**Open question:** does a true cross-model comparison change this, for example Fable against a different model under a true "different model" label?
