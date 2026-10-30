# 26 · Partial history and declarative descriptions in Qwen3-32B dice self-prediction (2026-10-30)

| | |
|---|---|
| Track | 1: static self-prediction |
| Tag | `SPAR_DICE_PREFIX_DECLARATIVE_v1.0` (exploratory, gated pilot) |
| Status | **Complete.** Preflight PASS (Experiment 21's G and F reproduced bit-for-bit); main checks PASS; 12 conditions × 3 repeats collected and analysed |
| Design source | `GPT_SPAR_Qwen_Dice_Partial_History_Declarative_Knowledge_Logprob_Handoff_v1.0.md`, a follow-up to Experiment 21 |
| Model | Qwen3-32B open weights, Experiment 21's configuration and runner (commit `9216db57…`, bf16 with fp32 output layer, thinking off, greedy) |
| Size and cost | 10 preflight + 36 main generations, 108 teacher-forced positions; one A100-SXM4-80GB for 7.2 min, **about $0.13** of the $10 cap |
| Previous | [← 25 single-sample Yes/No scoring](../25_2026-10-30_loula_yesno_logprob_pilot/) · builds on [21 dice log-probabilities](../21_2026-10-29_dice_logprob/) |
| Full report | [**reports/REPORT.md**](reports/REPORT.md) · [decision memo](reports/DECISION_MEMO.md) |

## Question

When Qwen3-32B predicts "another instance of your model" rolling a die, does its prediction get closer to what it actually generates in two cases?
- when it sees the first k actual rolls (k = 0, 3, 6);
- when it is also told one true fact about them: an earlier response used each face once in its first six rolls.

The fact is given in three versions that differ only in its source: "your own model" (S), "an unspecified model" (N) or "a different model" (O). H gets the revealed rolls only.

## Results

- **Revealed history works where the next rolls are predictable.** After "5 2 6", all four arms answer `3 1 4`, exactly G's continuation. With nothing revealed or with six rolls revealed, no arm gets the next three rolls right.
- **The prediction wrapper moves roll 1 strongly.** Asked for rolls 1–3 with nothing revealed, the model puts .85 on 3 and .01 on 5. Direct generation puts .53 on 5.
- **The fact helps, but not only as information.**
  - It raises the probability of the true roll at several k = 0 and k = 3 positions (by .12–.37).
  - It also shifts k = 6, where it carries no information about rolls 7–9 (P(true 6) rises from .02 to .14–.21).
- **"Your own model" is not special.** S and N are within the numerical floor (0.091) at 7 of 9 positions, and the two exceptions have opposite signs.

![P(true roll) by position](analysis/figures/fig3_p_true_by_position.png)

The reference is one deterministic greedy trajectory, and repeats were bit-identical. Positions are dependent, and k changes which roll is predicted. Treat this as a case study, not a population estimate.

## Re-running

```bash
PYTHONPATH=src python -m pytest tests/test_dice_prefix_declarative.py      # 12 offline tests
PYTHONPATH=src python -m spar_dynamic.dice_prefix_declarative freeze        # refuses if the frozen protocol would change
PYTHONPATH=src python -m spar_dynamic.dice_prefix_declarative dryrun        # prints all prompts and the GPU estimate
PYTHONPATH=src python -m spar_dynamic.dice_prefix_declarative preflight_eval
PYTHONPATH=src python -m spar_dynamic.dice_prefix_declarative analyse
```

GPU module: `python -m spar_dynamic.dice_prefix_declarative.gpu preflight --out <dir>`, then `… main --out <dir> --execute --confirm-preflight-id <id> --gate preflight_gates.json`.
