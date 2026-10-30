# 24 · Loula dice recognition v2.1: does scoring P(A) vs P(B) on open weights get past the "A" default? (2026-10-30)

| | |
|---|---|
| Track | 1: static self-prediction |
| Status | **Incomplete, failed:** stopped at the Stage A calibration gate; the recognition screen was never run |
| Tag | `LOULA_DICE_AB_LOGPROB_v2.1` (v2.1 methodology pilot) |
| Handoff | `GPT_SPAR_Loula_v2_1_OpenWeight_AB_Logprob_Claude_Code_Handoff` (protocol dated 2026-10-29) |
| Judge | Qwen3-32B open weights, Experiment 21 configuration (commit `9216db57…`, bf16 with fp32 output layer, thinking off) |
| Size and cost | 5 preflight + 72 calibration scored prompts; one A100-SXM4-80GB for 13.9 min, **about $0.28** of the $8 cap |
| Previous | [← 23 Loula recognition redesign v2](../23_2026-10-29_loula_recognition_redesign/) |
| Full report | [**REPORT.md**](REPORT.md) · [decision memo](DECISION_MEMO.md) |

## Question

In Experiments 22–23, judges asked "A or B?" about dice sequences mostly answered by position. This pilot reads the model's **probabilities** instead of its answer. It takes log P(A) − log P(B) at the first answer token, in both orders, and averages them to cancel a constant A/B bias. It then checks this score on Experiment 23's 36 reading-check items before any recognition question.

## What was done

- **Inputs were validated against content:** the 36 Experiment 23 items and the 20 Experiment 22 pairs.
- **The protocol was frozen** ([`PROTOCOL_FROZEN.md`](PROTOCOL_FROZEN.md)), and the pipeline was tested on Qwen3-0.6B locally.
- **One A100 was rented** for the 32B runs.
- **Technical preflight: PASS.**
  - Labels are single tokens and greedy replies start with the letter.
  - Repeats are bit-identical.
  - The numerical floor is 0.029, so ε = 0.058 log-odds.
- **Stage A calibration** scored all 72 orientations.

## Results

**Stage A failed one of five criteria, so the recognition screen was not run, as prespecified.**

| Task | correct after averaging the two orders (gate) | correct in both orders | mean label bias toward A |
|---|---|---|---|
| More 6s | 12/12 (≥ 9) | 4/12 | +4.1 |
| More adjacent repeats | 12/12 (≥ 8) | 5/12 | +0.8 |
| Generator R vs S | 12/12 (≥ 10) | 11/12 | +3.1 |
| **All** | **36/36 (≥ 29) ✓** | **20/36 (≥ 24) ✗** | +2.7 |

- **The probabilities do read content.** Once the A/B bias is averaged out, the correct sample is favoured on every item. The emitted "A" answers in Experiments 22–23 hid this.
- **But the "A" bias often outweighs it.** When the correct sample is shown as B, the model still prefers A on 16 of 36 items.
- **The adjacent-repeats signal is weak** (mean S +0.7, about the size of the bias) and does not grow with the size of the count difference.
- **The greedy letters from these local weights reproduce Experiment 23's bare-format results** (6s: 16/24 correct, 4/12 consistent). The position default belongs to the model, not the provider.

![Preference for the correct sample in each order](analysis/figures/calibration_order_bias.png)

## What it led to

Decision: **stop; no recognition scoring and no confirmatory study.** Proposed, not run (see the [decision memo](DECISION_MEMO.md)):
1. A new protocol that adopts the order-averaged score, with an order-by-content check, validated on new and subtler calibration items.
2. Or remove the label bias by design: neutral counterbalanced labels, or a separate yes/no question per sample.
3. Or park the recognition line and report 22–24 together.

## Re-running

```bash
PYTHONPATH=src python -m pytest tests/test_dice_recognition_logprob.py                 # 20 offline tests
PYTHONPATH=src python -m spar_dynamic.dice_recognition_logprob freeze                   # refuses if the frozen protocol would change
PYTHONPATH=src python -m spar_dynamic.dice_recognition_logprob preflight_eval           # offline, from the archived records
PYTHONPATH=src python -m spar_dynamic.dice_recognition_logprob calibration_eval
PYTHONPATH=src python -m spar_dynamic.dice_recognition_logprob analyse
```

The GPU module is `python -m spar_dynamic.dice_recognition_logprob.gpu {preflight,calibration,screen} --trials trials/<stage>.json --out <dir> [--gate <json>]`. Calibration refuses to start without a passed preflight gate, and the screen without a passed calibration gate, so with this archive the screen refuses.
