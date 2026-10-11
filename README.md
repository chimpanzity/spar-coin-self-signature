# SPAR: Behavioural Self-Signatures in LLMs

*SPAR Fall 2026 project, mentor Christopher Ackerman. Last updated 2026-10-11.*

> **Reviewing this project (human or LLM)?** Start with [`REVIEW_GUIDE.md`](REVIEW_GUIDE.md). It gives a reading order
> with raw-text links, a claim-to-evidence map, the canonical runs and known caveats.

**The question.** Do LLMs leave a recognisable behavioural signature, and does a model have any privileged access to
its own signature, compared with other models or a simple statistical classifier? The design is adapted from Loula et
al.'s point-light self-recognition paradigm: strip behaviour down to a minimal trace, then ask who produced it.

The project has two parts:

1. **Coin flips (2026-09-21 to 10-08).** Models simulate fair coin flips. Can a model pick out its own sequences, or
   predict their statistics, better than other models can?
2. **Strategic games (2026-10-09 to 10-11).** Models play rock-paper-scissors (RPS) and matching pennies (MP).
   - Does knowing the opponent is "another instance of you" change how a model plays? (Study 1, Experiment 1)
   - Can a model predict its own model's moves better than other models can? (Blind Twin, Experiment 2)

## Bottom line

- **No evidence of privileged self-access in either part.** Every identity effect we found is better explained by
  what a model believes about how LLMs (or particular named models) behave. A model applies those beliefs to itself
  the same way it applies them to others.
- **Fable shows a real self-prediction effect.** Told that a player is Fable, the Fable judge predicts that player
  better. Told the player is Qwen, it predicts worse.
  - The effect appears in both games and replicates across runs.
  - It lives in Fable's games against *other* models, not in Fable-vs-Fable games.
  - It matches a known habit: in RPS, Fable often switches to the move its previous move beats, and a true label nudges
    the Fable judge toward predicting that.
  - A history-only classifier trained on tens of Fable's games does as well. The point estimate is about 25-30
    games, but the plausible range runs from about 12 to more than 47. So this looks like self-*knowledge* of a
    model's habits, not privileged access.
- **The judges are noisy.** Re-asking an identical prompt reproduces only about 80% of predictions. Effects of about
  5 points per cell are within that noise, which matters for every pilot here.

## Part 2: strategic games (2026-10-09 to 10-11)

Models: GPT-6 Astra (`openai/gpt-6-astra`), Claude Fable 5.1 (`anthropic/claude-fable-5.1`) and Qwen3.8 27B
(`qwen/qwen3.8-27b`), via OpenRouter with pinned providers. Astra and Fable do not support temperature, so all runs
use default sampling with low hidden reasoning.

| study | design | headline | where |
|---|---|---|---|
| Blind Twin v1 and v2 (MP) | Astra/Fable play 12 games; both judge every round under TRUE / FALSE / ANONYMOUS identity labels | v1 S = −2.2 [−8.5, +3.5]; v2 (revised prompts) S = +4.2 [+0.4, +8.5] | [`blind_twin/`](blind_twin/) |
| Blind Twin RPS (3 runs) | Same design in RPS: Astra-Fable, Qwen-Fable, Qwen-Astra | S = −2.7, +5.7, +4.4; the false-label cost S_false is positive in all three runs | [`blind_twin_rps/`](blind_twin_rps/) |
| Opponent disclosure pilot (MP) | Astra vs Astra, 2×2 telling the Matcher/Mismatcher "your opponent is another Astra", 32 games | Telling the Matcher raised its win rate +5.0 pp [+0.6, +9.7]; no response mentions self | [`opponent_disclosure/`](opponent_disclosure/) |
| **Study 1, Exp. 1: RPS** | 3 models × 9 ordered pairings × 4 disclosure conditions × 2 games; primary D = self-specific disclosure benefit | **D_RPS = +0.011 [−0.027, +0.052]**. Fable's own D is +0.11, but it does not replicate in MP | [`opponent_disclosure_rps_3models/`](opponent_disclosure_rps_3models/) |
| **Study 1, Exp. 1: MP** | Same design, Matcher = Player 1 | **D_MP = −0.060 [−0.100, −0.023]**, driven by Qwen. 18 games lost to Qwen bold-formatted answers were replaced with make-ups; Qwen's failure rate doubles when told its opponent | [`opponent_disclosure_mp_3models/`](opponent_disclosure_mp_3models/) |
| **Exp. 2: Blind Twin on Exp. 1 logs** | 3 judges × 3 labels on the 36 games where neither player was told (6,480 calls) | S_RPS = +1.8 [−0.7, +4.4], S_MP = +1.5 [−1.0, +4.2]; Fable-on-Fable TRUE > ANON > FALSE in both games | [`blind_twin_exp1/`](blind_twin_exp1/) |
| Exp. 2 self-self pilot | Self-self games, 00 vs 11, judge told what the players knew | Δ self-specific RPS −4.8 [−9.6, 0.0], MP 0.0: no support for "informed twins are easier for a twin to read" | [`blind_twin_selfself/`](blind_twin_selfself/) |
| Judge test-retest | Byte-identical prompts re-judged | 80% of predictions reproduce (Fable 88%, Astra 85%, Qwen 67%); a 40-item cell moves ~5 pp, T = TRUE − ANON ~7 pp | [`blind_twin_selfself/results/btss-retest-20261011/`](blind_twin_selfself/results/btss-retest-20261011/) |
| Post-hoc analyses (offline) | Strategy measures; self-advantage by opponent; round-1 robustness; observation-equivalence calibration | No self-specific strategy change; a general RPS disclosure effect (players counter a *named* opponent ~5.5 pp more); Fable's self-advantage is in cross-model games | [`post_hoc/`](post_hoc/) |

Full write-up for Study 1 Experiment 1 (design, completion, amendments, make-up protocol, budget):
[`docs/study1/`](docs/study1/), starting with [`STUDY1_EXPERIMENT1_REPORT.md`](docs/study1/STUDY1_EXPERIMENT1_REPORT.md).

**Notable behaviour across the 144 Experiment 1 games:**

- **RPS opening:** every model opens PAPER, so 44 of 72 round 1s tie.
- **MP opening:** the Matcher opens STAR and the Mismatcher TRIANGLE, so the Mismatcher wins round 1 in 60 of 72 games.
  Both players are reasoning one step about the obvious opening.
- **Astra is near-deterministic early:** six of eight Astra-Astra MP games share their first five rounds across all
  four disclosure conditions.
- **Fable is the strongest RPS player** (payoff 0.527), despite an exploitable downward-switching habit.
- **MP is a fair game:** all payoffs are 0.49-0.51.

**What we can defend:**
- the null for self-specific disclosure effects (Experiment 1);
- Fable's label-dependent self-prediction (Experiment 2), together with the classifier calibration that bounds it;
- the judge-noise floor;
- Qwen's disclosure-dependent formatting failures.

**What we cannot claim:**
- privileged introspection;
- confirmatory effect sizes, because these are 2-games-per-cell pilots;
- generalisation beyond three models and two games.

## Part 1: coin flips (2026-09-21 to 10-08)

Models: Astra, Fable and MiMo (`xiaomi/mimo-v2.6-pro`). The setup is a frozen corpus of 180 sequences of 100 flips:
3 models × 3 generation procedures × 20. Full write-up: [`docs/COIN_FLIP_STUDY.md`](docs/COIN_FLIP_STUDY.md).

- **Signatures are real but procedure-driven.** A centroid classifier on p(H) alone identifies the source model 97%
  of the time. Under independent calls, Fable produces 98.7% heads.
- **No own-model advantage (FCE1/FCE2):** the mean self-advantage S is about 0.
- **Attribution follows the story, not the trace.** Changing only the stated generation procedure flips Fable's SELF
  answer on 85% of identical items.
- **Judges forecast the same statistics for every model, themselves included.** What looks like a self-model is a
  task-level belief about LLMs.
- **Phase 2 (20-flip strings, completion and same/different):** no self-specific advantage. Most judges answer 0.5
  almost every time, and external observers beat all judges.

## Repository map

```
README.md, REVIEW_GUIDE.md, llms.txt   start here
docs/
  COIN_FLIP_STUDY.md                   Part 1 full write-up (moved from the old README)
  study1/                              Study 1 Exp. 1: report, status, budget/approvals, make-up protocol and log
  handoffs/                            session handoff notes (Part 1 and Phase 2)
  preregistration/, references.md
corpus/, pilots/, data/spar_dynamic/   Part 1 stimulus corpus, archived pilots, raw run data
spar_dynamic/                          Part 1 code (also the shared OpenRouter client, spar_dynamic/phase2/client.py)
blind_twin/, blind_twin_rps/           Blind Twin pilots (players + judges), results/<run>/
opponent_disclosure/                   Astra-Astra MP disclosure pilot
opponent_disclosure_rps_3models/       Study 1 Exp. 1, RPS (run rps3m-p2-20261010; with_makeups/ = amended analysis)
opponent_disclosure_mp_3models/        Study 1 Exp. 1, MP  (run mp3m-p2-20261010; with_makeups/ = amended analysis)
blind_twin_exp1/                       Exp. 2: Blind Twin on Exp. 1 logs (run btx1-20261010)
blind_twin_selfself/                   Exp. 2 extension: self-self 00 vs 11 (btss-20261011) and test-retest
experiment1_makeup.py                  make-up game driver (rules in docs/study1/EXPERIMENT1_MAKEUP_GAMES.md)
experiment1_derived.py                 handoff-definition D and partial-game sensitivity
blind_twin_retest.py                   judge test-retest driver
experiment1_post_hoc_strategy.py       post-hoc strategy measures      -> post_hoc/experiment1_strategy_measures/
experiment2_observation_equivalence.py classifier calibration of judges -> post_hoc/experiment2_observation_equivalence/
post_hoc/experiment2_by_opponent/      self-advantage by opponent; round-1 robustness
tests/                                 unit + fake-transport tests for every package (pytest)
```

Every study package follows the same conventions:
- `config.py` holds the frozen prompts, models and caps; `protocol.md` holds the design decisions.
- A run folder contains `manifest.json` (or `frozen_manifest.json`), `APPROVAL.md`, `PROGRESS.md`, raw `calls.jsonl`,
  `REPORT.md` and `checksums.sha256`.
- Live calls are impossible unless `APPROVAL.md` contains `LIVE RUN APPROVED BY CHRIS: yes`.
- Raw call logs are never edited. Amendments go in new files or folders.

## Running things

```bash
pip install -r requirements.txt
python -m pytest -q                                          # all tests, no network
python -m opponent_disclosure_mp_3models analyze --run mp3m-p2-20261010    # re-analyse from raw logs
python -m blind_twin_exp1 analyze --run btx1-20261010
python experiment1_makeup.py mp --combine-only               # rebuild the amended (make-up) dataset
python experiment1_derived.py                                # handoff-definition D + partial-game sensitivity
```

Live runs need `OPENROUTER_API_KEY` and an approved run folder (`plan` → `validate` → approval → `run --live`).
On a laptop, keep the machine awake (`caffeinate -i`); idle sleep stalled one overnight run.

## Cost

| | spend |
|---|---:|
| Part 1: pilots, corpus, FCE experiments, Phase 2 | ~$55 |
| Blind Twin pilots (MP v1/v2, three RPS runs) | $54.94 |
| Opponent disclosure pilot | $7.05 |
| Study 1 Exp. 1 (RPS $22.61, MP $27.36, incl. make-ups) | $49.97 |
| Exp. 2 Blind Twin on logs / self-self pilot / test-retest | $33.06 / $23.40 / $5.77 |
| **Total** | **~$229** |

## Related work

Martin, C. F. (2026). *Dodging Proteus: Prescribing unexploitable play made language models more exploitable in a
closed-loop matching pennies assay.* Preprint, not peer reviewed.
[doi:10.5281/zenodo.21781962](https://doi.org/10.5281/zenodo.21781962) ·
[code](https://github.com/chimpanzity/dodging-proteus). Key references with notes: [`docs/references.md`](docs/references.md).
