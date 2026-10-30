# Loula dice self-recognition v2: elicitation validation (2026-10-29)

**Tag:** `LOULA_DICE_RECOGNITION_v2.0`. **Handoff:** `GPT_SPAR_Loula_Dice_Recognition_Redesign_Claude_Code_Handoff_v2.0`.
**Models (OpenRouter, pinned, no fallbacks):** Qwen3-32B on SiliconFlow (reasoning off) and Mistral Small 3.2 24B on DeepInfra, as in Experiment 22.
**Outcome:** stopped at the Stage A gate, as prespecified. **Neither judge passed calibration in either response format**, so no identity judgments were run.
**Spend:** $0.0074 of the $5 cap, 300 calls. No GPU.

## 1. What ran

| Stage | Status | Calls |
|---|---|---|
| Dry run (protocol freeze, cost estimate: at most 2,028 calls, about $0.21 worst case) | done | 0 |
| API preflight | **PASS.** Providers pinned, Qwen reasoning tokens 0, valid generations, multi-turn works, and both judges answered an easy "more 6s" item correctly in both orders and both formats. | 12 |
| A. Calibration (12 synthetic items × 3 tasks × 2 orders × 2 judges × 2 formats) | **FAIL for all four judge × format cells** | 288 |
| B. Elicitation screen | `NOT_RUN`: the Stage A stop rule | 0 |
| C. Fresh corpus, evidence dose, named control | `NOT_RUN`: the Stage A stop rule | 0 |
| D. Familiarization (D1, D2) | `NOT_RUN`: the Stage A stop rule | 0 |

Nothing changed after the freeze: no prompt, threshold, item or parser was altered, and no failing cell was rerun.

## 2. Stage A results

Gates: MORE_SIXES ≥ 20/24 correct and ≥ 10/12 consistent pairs; MORE_REPEATS ≥ 20/24 and ≥ 10/12; GEN_RULE ≥ 18/24 and ≥ 9/12; validity ≥ 95% of 72 calls. A cell passes only if every criterion holds.
- **Correct** = presentations answered correctly, out of 24.
- **Consistent** = item pairs where the judge chose the same candidate in both A/B orders, out of 12.
- **A-rate** = share of valid answers that were "A". With balanced orders, a content-reading judge sits near 0.50.

| Judge | Format | More 6s: correct / consistent / A-rate | More adjacent repeats | Generator R vs S | Validity | Cell |
|---|---|---|---|---|---|---|
| Qwen3-32B | bare | 16 / 4 / .83 ✗ | 12 / 0 / **1.00** ✗ | 19 / 7 / .71 ✗ | 72/72 | **FAIL** |
| Qwen3-32B | brief | **23 / 11** / .52 ✓ | 19 / 9 / .54 ✗ (one short on both) | **24 / 12** / .50 ✓ | 71/72 | **FAIL** |
| Mistral Small 3.2 | bare | 20 / 8 / .67 ✗ | 11 / 0 / **1.00** ✗ | **24 / 12** / .50 ✓ | 70/72 | **FAIL** |
| Mistral Small 3.2 | brief | 21 / 9 / .61 ✗ | 19 / 7 / .71 ✗ | **23 / 11** / .54 ✓ | 71/72 | **FAIL** |

Figure: [`analysis/figures/1_calibration.png`](../analysis/figures/1_calibration.png). Full table: [`calibration/gate_table.csv`](../calibration/gate_table.csv).

**What the pattern shows:**
1. **Bare A/B answers are not reliably content-driven.** On "which has more adjacent repeats?", both judges answer "A" on all 24 presentations (consistency 0/12). This is the same position default seen in Experiment 22. On "more 6s", Qwen's bare answers are "A" 83% of the time.
2. **A short written observation helps a lot, but not enough.**
   - With the brief format, A-rates move to about 0.5 and accuracy rises: Qwen gets 23/24 on 6s and 19/24 on repeats.
   - Qwen brief misses the gate by one presentation and one consistent pair, on repeats only.
   - The handoff rules forbid rescuing near-misses, so it is reported as a fail.
3. **A gross source rule is easy; fine counting is not.**
   - Every format except Qwen bare passes the explicit generator task. That task has a large difference: 70% vs 5% repeats.
   - The count tasks differ by only 1–3 occurrences, and they fail.
   - So the judges can map an obvious behavioural tendency onto a source, but cannot count small differences reliably.
4. **Written observations are often wrong even when the answer is right.**
   - In an audit of 4 automatically flagged Qwen "repeats" explanations, all 4 misdescribe the sequences, for example by claiming a "6-6-6" run that does not exist.
   - 3 of those 4 still end in the correct answer.
   - The automated count-claim matcher is crude (it sometimes reads a face value as a count), so its tallies in `analysis/summary.json` are indicative only.
   - Every brief response cites a sequence feature. Fluent explanations are not proof of accurate reading.
5. **Invalid answers (4 of 288).**
   - Two brief replies ended "ANSWER: Neither" after the judge wrongly concluded the counts were tied.
   - Two Mistral bare replies began an explanation and hit the 8-token limit.

## 3. Interpretation

Stage A was designed as a **necessary condition**: can these judges, in this format, make content-dependent A/B choices on ten-roll sequences? For neither model and neither format did the full battery pass. The handoff's prespecified consequence is a **methodological stop**, and no self-recognition claim of any kind follows.

The failure is informative about the Experiment 22 null. The actual Qwen-vs-Mistral phenotype difference is modest:
- an external classifier reached about 0.72–0.76 AUC;
- the differences are in which faces appear and where, not in repeat rate, since both models almost never repeat.

That difference is far subtler than the 1–3-count differences these judges already fail to read reliably. Read as an A/B task over a few ten-roll lines, the source-recognition question is beyond the measurement resolution these judges showed here. That holds before any question of self-knowledge arises.

Constructs, kept separate:
- **Reading / counting:** partial (brief only); fails the gate.
- **Rule-based source inference:** present for an obvious rule.
- **Authorship recognition, typicality, generic named-source identification, own-source advantage, familiarization:** not measured (`NOT_RUN`). They are not estimable, not zero.

## 4. Limitations

- 12 items per task. The gates were deliberately strict, and the brief cells missed by one or two units.
- One fixed wording per task, at temperature 0. Another wording might pass, but searching for one would be the prompt-optimization the handoff rules out within this protocol.
- Stage A items are 10 rolls (10–20 for the generator task). Real Stage C samples would have been 30–50 numbers, which might be harder still to count across.

## 5. What would be needed next (proposed only; each needs separate approval)

See [`DECISION_MEMO.md`](DECISION_MEMO.md). In short:
- **Score the choice instead of sampling it.** Read P(A) vs P(B) on open weights, averaged over both orders (the Experiment 21 A100 pipeline). This sidesteps the answer default and gives graded evidence.
- Or **pre-specify a different calibration-passing elicitation**, such as structured per-sample tallies before the answer, and run Stage A again as a new versioned protocol.

## 6. Files

| Path | Contents |
|---|---|
| `PROTOCOL_FROZEN.md`, `manifest.json` | Templates and hashes, rendered examples, seeds, gates, call allocation, cost estimate |
| `api_preflight/` | 12 raw calls, `preflight_summary.json` |
| `calibration/items.csv`, `generator_rules.json` | The 36 synthetic items, with content-recomputed answers, and the R/S generator definitions |
| `calibration/raw_attempts.jsonl`, `trials.csv`, `responses.csv` | All 288 calibration calls, with full requests and raw replies |
| `calibration/gate.json`, `gate_table.csv`, `run.log` | Gate verdicts per judge × format |
| `elicitation_screen/format_freeze.json` | Primary-format freeze (empty: no judge qualified) |
| `analysis/summary.json`, `analysis/figures/1_calibration.png` | Analysis output; stages B–D labelled `NOT_RUN` |
| `cost_ledger.json` | Spend by stage |
| Code and tests | `src/spar_dynamic/dice_recognition_v2/`; `tests/test_dice_recognition_v2.py` (37 offline tests) |
