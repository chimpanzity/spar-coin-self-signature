# SPAR Phase 2 pilot (v7.1): results summary

Run `p2-20261007`, executed overnight 2026-10-07/08 on branch `phase2` (local commits, not pushed).
Full outputs: `data/spar_dynamic/phase2/p2-20261007/`. Start with `CORE_REPORT.md`, then
`RETAINED_ARMS_REPORT.md`, `STAGE1_REPORT.md`, `amendments.jsonl`.

## Execution

- **Models**, all via OpenRouter with pinned providers: Astra (OpenAI), Fable (Anthropic), Qwen3-8B (Alibaba). Historical check: GPT-3.5-turbo-0613 (Azure).
- **Calls:** 2,514 recorded, all completed (planned envelope 3,186). The shortfall is entirely downstream of Qwen's low validity on the "fair" prompt, which reduced the number of test parents, pairs and controls.
- **Spend:** $8.39 against the $100 cap, plus about $0.01 of troubleshooting calls.
- **Gates and approvals:** all of Chris's decisions were recorded before any data existed (`approvals.jsonl`). The freeze was executed before test generation (`freeze.json`).

### Amendments, all recorded in `amendments.jsonl`

| id | when | what |
|---|---|---|
| A1 | Stage 1 smoke, before any judge data | Qwen's endpoint returned identical outputs for identical requests unless a seed was sent. Each Qwen generation call now carries a distinct SHA-derived seed. 10 smoke rows from the old configuration are archived. |
| A2 | Stage 1, before freeze | Generation parser gen_v1 → gen_v2: accepts "·" separators and `**Heads:** 10` counts. All rows re-parsed; 12 Astra rows changed from invalid to valid after manual review. |
| N1 | Stage 1 | Fable failed the pair-fixture valid-response gate (2/12). It printed its working before the number, and the frozen parser does not salvage trailing numbers. On the real pair task it was 11/12 valid. The run continued, per Chris. |
| A3 | After all test calls; reporting only | Per-prompt bootstrap CIs for R/P/D and named R/P/D, plus a table of flat 0.5 forecasts. No endpoint, mask or estimator changed. |

## Corpus

| source | plain valid | fair valid | notes |
|---|---:|---:|---|
| Astra | 60/60 dev, 24/24 test | 60/60, 24/24 | 31–37 distinct strings per 60 |
| Fable | 60/60, 24/24 | 59/60, 24/24 | very concentrated: 16–18 distinct strings per 60; shares top strings with Astra |
| Qwen3-8B | 59/60, 24/24 | **6/60, 1/24** | "Flip 20 fair coins." gets a probability explainer, not flips; "plain" gives heavy alternation (switch rate 0.90; `HTHTHT…` x24 of 59) |

Consequence: the fair prompt has **no pair blocks** and only one Qwen test parent. Under the frozen rules, the two-prompt anonymous and named panels are **not estimable**. Per-prompt (plain) results are reported as secondary.

## Key results

**H4 (completion, key, two-sided):** H4 = −0.0026 [−0.0040, −0.0013], with gain_own −0.0002 [−0.0006, +0.0002], gain_other +0.0024 [+0.0012, +0.0037], C_known −0.014, C_withheld −0.012.
- **Direction:** resolved negative, but bounded well inside the ±0.02 Brier margin. Disclosure helped other-source forecasts slightly, and own forecasts not at all.
- **The judges mostly do not forecast.** Astra returns 0.5 at every position for 100% of Astra- and Fable-source prefixes. Fable does so on 52–62%, and Qwen on 80–94% of all prefixes. They depart from 0.5 mainly for Qwen's alternating sequences, which carry most of the H4 signal.
- **External observers far outperform the judges.** On Fable/plain, the prefix observer scores Brier 0.064 when told the source, against 0.250 for the judges. The fixtures show Astra and Fable *can* use stated rules (12/12 correct), so the flat answers reflect the task framing rather than inability.
- **The fair-prompt crossovers involving Qwen rest on a single parent.**

**Anonymous SAME/DIFFERENT:**
- **Primary two-prompt panel:** not estimable.
- **Plain prompt, secondary:** R = +0.076 [+0.011, +0.130], P = +0.085, D = +0.067.
- **Not consistent across judge pairs:** Astra–Fable R = −0.05, Astra–Qwen +0.10, Fable–Qwen +0.17.
- **Driven by a weak reference judge:** the largest term relies on Qwen, as the uninvolved judge, scoring below chance on Fable-versus-Astra pairs (AUC 0.11). This is the skill-by-difficulty pattern the spec warns about.
- **Astra is nearly flat:** it answers exactly 0.5 on 93% of pairs.
- **Overall SAME-vs-DIFFERENT AUROC:** Fable 0.79, Astra 0.60, Qwen 0.57. External baselines: observer 0.95, L2 pair classifier 0.88.
- **Reading:** some source-relation sensitivity, mainly from Fable. Neither the role pattern nor the comparison with baselines supports an own-model advantage.

**Named attribution (plain only, 18 parents):** R = −0.04 [−0.17, +0.09], unresolved. Fable has balanced accuracy 0.61 (chance 0.33) and picked itself 10 of 18 times. Astra scored 0.28; Qwen spread its choices evenly.

**Historical check (GPT-3.5-0613):** first flip heads 98–100%, matching the paper's Table 2 except fair/t=1.5 (0.98 versus 0.86). Heavy over-alternation (switch rate 0.74–0.88); longest run about 2.

**LASSO (`history7_runs14_v1`):** beats the per-position baseline for Astra/plain, Fable/plain, Qwen/plain and all six GPT-3.5 cells. It is not resolved for Astra/fair or Fable/fair, and Qwen/fair is insufficient. This is predictability, not identity.

## What this pilot does and does not show

- **No evidence of a self-specific forecasting advantage from disclosure** (H4 tiny, negative, bounded), in this configuration and assay.
- **A main obstacle is response policy:** two of three judges largely return uninformative 0.5 forecasts and pair probabilities. A future design should address this before reading anything into H4 or R.
- **Qwen3-8B (non-thinking) is a poor generator for the "fair" prompt.** The two-prompt design needs a different third model or a documented prompt decision before a confirmatory run.

## Code and audit

- **Package:** `spar_dynamic/phase2/`. Tests: `tests/test_phase2.py`; all 150 tests in `tests/` pass.
- **Independent rescore:** `rescore.py` matches the main H4 to 1e-15.
- **Confirmed audit leads from the older code (not reused):**
  - `hash()`-based seeds in `trials.py`, `self_other.py`, `provenance.py` and the FCE bootstrap (`full_corpus_exp1/analysis.py:542`), so those FCE bootstrap intervals are not reproducible across processes.
  - `api.py` always sends temperature and reasoning, even where the endpoint doesn't support them.
