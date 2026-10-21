# 06 · Experiment 2: three Blind Twin judges on the Study 1 games (2026-10-10/11)

| | |
|---|---|
| Track | 2 — game theory (complementary to track 1) |
| Run IDs | `btx1-20261010` |
| Game and models | The 36 condition-00 games from Study 1 Experiment 1 (18 RPS, 18 MP; 2 per ordered pairing). Judges: Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), Qwen (`qwen/qwen3.8-27b`); reasoning effort low, no temperature control |
| Size and cost | 6,480 judge calls, 6,452 valid; $33.06 (cap $70) |
| Previous / next | [← Study 1, Experiment 1](../05_2026-10-10_study1_exp1_disclosure/) · [Self-self judges and retest →](../07_2026-10-11_selfself_judges_and_retest/) |

## What was done

This is the Blind Twin observer design (01–03), applied at larger scale and to games that no judge had played in.

**Stimuli.** The input was the 36 Study 1 games in which neither player had been told its opponent's identity ([05](../05_2026-10-10_study1_exp1_disclosure/)). These include make-up games that replaced interrupted Qwen games.

**Task.** Astra, Fable and Qwen each predicted both players' moves at every round from the public history. One fresh call was made per item, under three labels:
- TRUE;
- ANONYMOUS;
- FALSE, using a fixed rotation Astra → Fable → Qwen → Astra.

**Scoring.**
- Predictions were scored on items valid under all three labels, with equal weight over seat × opponent strata.
- The primary index S (self-specific TRUE vs ANONYMOUS benefit) was computed separately for each game type, with a whole-game bootstrap.
- The headline numbers were recomputed independently from `predictions.csv` on 10-11.

## Questions

- With three judges and games none of them played, does a TRUE label help a judge predict its own model more than it helps other judges (S)?
- Which model, if any, carries the effect?

## Results

| Index | RPS | MP |
|---|---|---|
| **S (TRUE vs ANON), primary** | +1.8 [−0.7, +4.4] | +1.5 [−1.0, +4.2] |
| S_false (TRUE vs FALSE) | +3.9 [+0.6, +7.4] | +3.5 [+0.8, +6.3] |
| S[astra] / S[fable] / S[qwen] | +3.5 / +4.8 / −2.8 | +3.1 / +3.8 / −2.3 |
| Fable judging Fable, TRUE / ANON / FALSE (%) | 53.4 / 45.0 / 38.8 (chance 33.3) | 65.0 / 62.1 / 56.2 (chance 50) |

- **The primary S is small, and its interval includes zero in both games.** S_false is positive in both.
- **Fable is the signal.** Its accuracy on Fable players falls in order TRUE > ANON > FALSE in both games. A wrong label on a Fable player costs Fable 14.5 pp in RPS, while the Fable label on an Astra player gains it nothing (41.6 vs 40.8).
- **Astra is label-sensitive but not self-specific.** In both games, the FALSE label on Astra players beats TRUE.
- **Qwen** changes about 40% of its RPS predictions between labels without gaining accuracy, and its S is negative.
- **Simple rules can beat the judges.** A history-only rule ("counter the opponent's last move") predicts Qwen players at 46.7% in RPS, above every judge.

**Operational issues.**
- Throughput collapsed after 2,532 calls because the laptop went into idle sleep. The run was resumed with higher concurrency and a shorter timeout; this involved no scientific change.
- 44 Qwen calls hit the timeout and were resampled.
- 28 Fable answers were invalid because they wrote reasoning before the JSON.

## Open questions

- Is Fable's labelled advantage privileged self-access, or knowledge of its own conventions that an outsider could learn by watching? Folder [08](../08_2026-10-11_post_hoc_analyses/) addresses this offline.
- Where does the effect sit: which rounds, and which opponents?
- How noisy is a single judge prediction? Folder [07](../07_2026-10-11_selfself_judges_and_retest/) addresses this.

## What it led to

- A self-self judging pilot with a retest of the judges' own noise ([07](../07_2026-10-11_selfself_judges_and_retest/)).
- Offline analyses ([08](../08_2026-10-11_post_hoc_analyses/)). These showed that Fable's self-advantage lives in its games against *other* models, and that its labelled self-prediction is worth about 24–32 of its own logged games to a simple 2-gram predictor.

## Files

- Run folder: [`btx1-20261010/`](btx1-20261010/)
  - [`REPORT.md`](btx1-20261010/REPORT.md): main report
  - `protocol.md`, `manifest.json`, `schedule.json`, `APPROVAL.md`, `VALIDATION_REPORT.md`
  - `predictions.csv`, `accuracy.csv`, `indices.csv`, `responsiveness.csv`, `baseline_scores.csv`, `invalids.csv`, `results.json`
- Code: [`src/blind_twin_exp1/`](../../src/blind_twin_exp1/)
- Tests: [`tests/test_blind_twin_exp1.py`](../../tests/test_blind_twin_exp1.py)
- Background: [`docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md`](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md), sections 3.3–3.5

## Re-running

Run these from the repo root:

```
PYTHONPATH=src python -m blind_twin_exp1 analyze  --run btx1-20261010     # no API calls; rewrites REPORT.md
PYTHONPATH=src python -m blind_twin_exp1 validate --run <new-id>          # unit tests + offline fake run
PYTHONPATH=src python -m blind_twin_exp1 plan     --run <new-id>          # manifest, cost estimate, unapproved APPROVAL.md
PYTHONPATH=src python -m blind_twin_exp1 run      --run <new-id> --live   # needs approval
PYTHONPATH=src python -m pytest -q tests/test_blind_twin_exp1.py
```

- **Live runs** need `OPENROUTER_API_KEY` and an approval line in the run's `APPROVAL.md`.
- **Code hash.** `run` checks the code hash, game-log hash and schedule hash against the frozen manifest. The 2026-10-21 path edits changed the code hash, so `btx1-20261010` cannot be resumed as is. See [`docs/REORGANISATION_2026-10-21.md`](../../docs/REORGANISATION_2026-10-21.md) and [`docs/PATH_MAP.md`](../../docs/PATH_MAP.md).
