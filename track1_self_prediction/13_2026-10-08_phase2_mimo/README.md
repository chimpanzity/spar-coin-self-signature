# 13 · Phase 2 coin-flip pilot (v7.1), run 2 with MiMo (2026-10-08)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | `p2-mimo-20261008` (MiMo smoke test in [`../12_.../phase2/_preflight/`](../12_2026-10-07_phase2_qwen/phase2/_preflight/)) |
| Models | Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), MiMo-V2.6-Pro (`xiaomi/mimo-v2.6-pro`, first-party Xiaomi endpoint, reasoning disabled for generation); historical check GPT-3.5-turbo-0613 |
| Size and cost | 2,802 calls, $8.94 (Phase 2 total $17.34) |
| Previous / next | [← 12 Phase 2, run 1 (Qwen3-8B)](../12_2026-10-07_phase2_qwen/) · [14 Dice v3.1 →](../14_2026-10-15_dice_v31/) |

## What was done
The same v7.1 protocol as [run 1](../12_2026-10-07_phase2_qwen/), with MiMo replacing Qwen3-8B as the
third model and fresh development and test data for all three models (nothing pooled with run 1).
Generation parser `gen_v3`; judging greedy (t = 0) for MiMo. MiMo's "fair" validity (10/24 test) was
enough for both prompts to have pair blocks, so all primary panels were estimable.

## Questions
- With all panels estimable, is there any own-model advantage in completion forecasting (H4),
  anonymous SAME/DIFFERENT recognition (R) or named attribution?

## Results
From [`PHASE2_MIMO_RUN_RESULTS_2026-10-08.md`](PHASE2_MIMO_RUN_RESULTS_2026-10-08.md) and [`CORE_REPORT.md`](phase2/p2-mimo-20261008/CORE_REPORT.md):
- **H4 = −0.0004 [−0.0010, +0.0002]**: unresolved, inside the ±0.02 margin.
- Astra and MiMo returned 0.5 at every position for **100%** of completion calls; Fable in 48–81%.
  The pre-registered headroom review was triggered (every I[g] below 0.02).
- Anonymous recognition R = −0.019 [−0.074, +0.034], labelled unstable (1.1% undefined bootstrap
  replicates). MiMo answered exactly 0.5 on 100% of pairs, Astra on 99%. The prefix observer reached 0.78 (plain) and 0.84 (fair).
- Named attribution R = −0.059 [−0.150, +0.039]. Fable chose itself on 35 of 36 sequences whatever the true source:
  a self-labelling default, not discrimination.
- Run 1's plain-prompt R (+0.076) did not replicate.

## Open questions
- How do you elicit an informative answer instead of a flat 0.5 (forced choice, scoring feedback, a best
  guess alongside the probability)? The independent review recommended an elicitation check and a v8 design; neither was run.

## What it led to
The coin-flip track was parked on 2026-10-08. Work moved to strategic games (track 2,
[`../../track2_game_theory/`](../../track2_game_theory/), 10-09 to 10-11), where every round forces a committed
choice. Track 1 resumed on 2026-10-15 with Binder-style hypothetical self-prediction:
[14 Dice v3.1](../14_2026-10-15_dice_v31/).

## Files
- Summary: [`PHASE2_MIMO_RUN_RESULTS_2026-10-08.md`](PHASE2_MIMO_RUN_RESULTS_2026-10-08.md).
- Run folder [`phase2/p2-mimo-20261008/`](phase2/p2-mimo-20261008/): `CORE_REPORT.md`, `RETAINED_ARMS_REPORT.md`,
  `STAGE1_REPORT.md`, `STAGE2_REPORT.md`, `DECISION_MEMO.md`, `amendments.jsonl`, `calls.jsonl` and the other run records.
- Background and the parking decision: [week handoff 10-05 to 10-11, §2 and §6](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md).
- Code: [`src/spar_dynamic/phase2/`](../../src/spar_dynamic/phase2/).
- Tests: [`tests/test_phase2.py`](../../tests/test_phase2.py).

## Re-running
As for [run 1](../12_2026-10-07_phase2_qwen/#re-running), with MiMo selected as the third model
(needs `OPENROUTER_API_KEY`):

```
PHASE2_THIRD_MODEL=mimo PYTHONPATH=src python -m spar_dynamic.phase2 init --run <run id>
```

followed by the same `generate`, `stage1`, `freeze`, `stage2`, `retained`, `analyze` stages, each with `PHASE2_THIRD_MODEL=mimo` set.
