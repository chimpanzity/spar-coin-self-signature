# 07 · Self-self judging pilot and judge test-retest (2026-10-11)

| | |
|---|---|
| Track | 2 — game theory (complementary to track 1) |
| Run IDs | `btss-20261011` (self-self pilot), `btss-retest-20261011` (test-retest) |
| Game and models | The 24 Study 1 self-self games (Astra–Astra, Fable–Fable, Qwen–Qwen; conditions 00 and 11; RPS and MP; 2 per cell). Judges: Astra, Fable, Qwen (`qwen/qwen3.8-27b`); reasoning effort low, no temperature control |
| Size and cost | Self-self: 4,320 judge calls, $23.40 (cap $40). Retest: 1,080 calls, $5.77 (cap $10) |
| Previous / next | [← Experiment 2: Blind Twin judges](../06_2026-10-10_exp2_blind_twin_judges/) · [Post-hoc analyses →](../08_2026-10-11_post_hoc_analyses/) |

## What was done

**Self-self pilot (`btss-20261011`).**

*Hypothesis.* A player that has been told it faces a copy of itself (condition 11) may play in a way that a same-model observer can read more easily than an uninformed player (condition 00).

*Design.*
- The three judges predicted both players in all 24 self-self games under TRUE, FALSE and ANONYMOUS labels.
- Each prompt gained one line saying what the players had been told, without naming a model. The 00 games were re-judged under this new prompt.
- Primary index, per game type: Δ self-specific = (T₁₁ − T₀₀ for the self-judge) − (the same quantity for the other judges), where T = TRUE − ANONYMOUS accuracy.

**Test-retest (`btss-retest-20261011`).**
- Six games were chosen by rule: the first condition-00 self-self game for each game type × model.
- These were re-judged with prompts byte-identical to `btss` (1,080 calls), and compared item by item with `btss` and with the earlier `btx1` run.
- This measures how much of any label effect is simply the judges' sampling noise.

## Questions

- Is an informed twin easier for a same-model observer to read than an uninformed one?
- How reproducible is a single judge prediction? How large a difference between two cells is noise?

## Results

**Self-self pilot**
- **Δ self-specific:** RPS −4.8 [−9.6, 0.0]; MP 0.0 [−7.3, +7.5]; pooled −2.4 [−6.9, +2.1].
- **No support for the hypothesis.** In RPS the truthful label became *more* useful to the *other* judges in the 11 games: Δ other = +3.2 [+0.8, +5.5].
- **Per-model intervals are too narrow.** Some are as narrow as ±2.5 pp. This is an artefact of 2 games per cell; the retest below shows why.

**Test-retest**
- **Identical prompts gave the identical prediction 80.1% of the time:** Astra 84.9%, Fable 88.1%, Qwen 67.4%.
- **Cell-level noise.** A 40-prediction cell's accuracy moved 4.7 pp on average between runs (maximum 15.0). A TRUE − ANON difference moved 6.9 pp.
- **The player-information line made no measurable difference.** Runs with and without it differ by 5.2 pp per cell (7.2 pp in T), about the same as two identical runs.
- **This is the measurement floor** for every per-cell number in folders 01–07. Per-cell effects below about 7 pp cannot be read.

## Open questions

- Would probability elicitation (scored by log loss), instead of one sampled hard prediction per item, reduce the 20% flip noise enough to resolve small effects?
- Are self-self games the right test at all? Every judge predicts self-self games worst (see [08](../08_2026-10-11_post_hoc_analyses/)).

## What it led to

- **The noise floor** changed how every earlier interval in this track is read.
- **A decision** (10-11): no further gameplay collection until the instrument is redesigned.
- **The proposed redesign**, in the week record, section 7:
  - probability elicitation;
  - seeded game starts;
  - scripted opponents;
  - outsiders given k games of the target's history.
- **Offline analyses** ([08](../08_2026-10-11_post_hoc_analyses/)) were run instead of new calls.

## Files

- Self-self run: [`btss-20261011/`](btss-20261011/)
  - [`REPORT.md`](btss-20261011/REPORT.md): main report
  - `protocol.md`, `manifest.json`, `schedule.json`, `APPROVAL.md`, `VALIDATION_REPORT.md`
  - `predictions.csv`, `accuracy.csv`, `indices.csv`, `baseline_scores.csv`, `results.json`
- Retest run: [`btss-retest-20261011/`](btss-retest-20261011/)
  - [`REPORT.md`](btss-retest-20261011/REPORT.md): main report
  - `predictions.csv`, `schedule.json`, `manifest.json`, `APPROVAL.md`
- Code: [`src/blind_twin_selfself/`](../../src/blind_twin_selfself/), [`src/blind_twin_retest.py`](../../src/blind_twin_retest.py)
- Tests: [`tests/test_blind_twin_selfself.py`](../../tests/test_blind_twin_selfself.py)
- Background: [`docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md`](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md), sections 3.6–3.7 and 5–7

## Re-running

Run these from the repo root:

```
PYTHONPATH=src python -m blind_twin_selfself analyze --run btss-20261011   # no API calls; rewrites REPORT.md
PYTHONPATH=src python src/blind_twin_retest.py analyze                     # recompare btx1 / btss / retest; no API calls
PYTHONPATH=src python -m blind_twin_selfself validate --run <new-id>       # unit tests + offline fake run
PYTHONPATH=src python -m pytest -q tests/test_blind_twin_selfself.py
```

- **Subcommands.** `blind_twin_selfself` has `plan`, `validate`, `run` and `analyze`. `blind_twin_retest.py` has `plan`, `run` and `analyze`.
- **Live runs** need `OPENROUTER_API_KEY` and an approval line in `APPROVAL.md`.
- **Hash checks.** Both scripts check frozen hashes. The self-self `run` checks the code hash, game-log hash and schedule hash. The retest asserts that the prompt templates match `btss`. The 2026-10-21 path edits changed the code hash, so the frozen runs cannot be resumed as they stand. See [`docs/REORGANISATION_2026-10-21.md`](../../docs/REORGANISATION_2026-10-21.md) and [`docs/PATH_MAP.md`](../../docs/PATH_MAP.md).
