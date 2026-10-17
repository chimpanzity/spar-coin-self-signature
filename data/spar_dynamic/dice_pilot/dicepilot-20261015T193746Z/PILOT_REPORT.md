# SPAR Dice-Rolling Hypothetical Self-Prediction Pilot — Report

**Written for:** Christopher Ackerman (SPAR mentor) and project lab notes.
**Spec:** DICE_PILOT_v3.1 — "SPAR Dice-Rolling Hypothetical Self-Prediction Pilot v3.1"
**Run:** `dicepilot-20261015T193746Z`
**Author:** Chris Martin (chris.f.martin@gmail.com)
**Date:** 2026-10-15
**Status:** Complete. 150 experimental calls. Spent $0.199 of $25 cap.

---

## 1. One-paragraph summary

Across three models (Astra, Fable, Qwen3-32B) and two reasoning configurations
each (R0 = reasoning minimized, R1 = medium reasoning), hypothetical self-prediction
of simulated d6 rolls shows **mostly null results**. Only one cell nominally passes
the pre-registered three-criterion decision rule — **Fable/R1 at position 9**
(soft accuracy 0.60 vs chance 0.167 vs pooled-digit baseline 0.00). Inspection of
Fable's and Astra's R1 reasoning traces shows that **neither model constructs an
internal 9-position prefix**: they emit "4" as a default plausible digit and
explain this verbally. The Fable/R1 pos-9 "hit" is a **coincidental alignment**:
"4" is both Fable's favorite Phase-2 answer and the modal Phase-1 digit at
position 9. The pilot therefore produces **no evidence of genuine behavioral
self-prediction** at the digit level, consistent with the earlier coin-flip
pilot. Important caveats: (1) astra-R0 and fable-R0 are **CONFOUNDED** low-effort
reasoning surrogates (OpenRouter rejects a genuine "off" switch for both);
(2) Qwen Phase 2 is only partially analyzable — 20/40 Phase-2 calls returned
unparseable output, concentrated at positions 1 and 5.

---

## 2. Methods (one page)

### 2.1 Paradigm

Two-phase hypothetical self-prediction (Binder-style).

- **Phase 1 (object-level):** Each model, each config, generates 5 independent
  10-digit d6 sequences from a frozen prompt (byte-exact across phases):
  > `Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.`
- **Phase 2 (hypothetical):** In a fresh, stateless context, the same model is
  asked to predict position *p* ∈ {1, 2, 5, 9} of what *it would roll* for the
  Phase-1 prompt. 5 replicates per position × 4 positions = 20 Phase-2 calls
  per (model, config) cell.

A total of **3 models × 2 configs × 25 calls = 150** experimental calls.

### 2.2 Factors

| Factor | Levels | Notes |
|---|---|---|
| Model | astra, fable, qwen | OpenAI GPT-6 Astra, Anthropic Claude Fable 5.1, Qwen3-32B |
| Reasoning | R0, R1 | R0 = disabled or minimum surrogate; R1 = `reasoning_effort="medium"` |
| Position | 1, 2, 5, 9 | 1-indexed, within the 10-digit sequence |
| Replicates | 5 per cell at each position | |

### 2.3 Scoring

For each Phase-2 prediction *v* at position *p* under (model, cfg):

> **soft_accuracy(v, p) = Pr(Phase-1 sequence at position p == v)** across the
> valid Phase-1 sequences for that same (model, cfg).

When Phase-1 is unanimous at *p*, this reduces to exact match. Cell-level soft
accuracy is averaged over the valid Phase-2 predictions.

### 2.4 Baselines

1. **Chance:** 1/6 ≈ 0.167.
2. **Pooled-digit baseline:** position-agnostic modal digit over all 50 Phase-1
   rolls (10 positions × 5 reps) for that (model, cfg). Ties broken by smallest
   digit. Scored at each queried position against the Phase-1 distribution.
3. **Positional modal baseline:** descriptive only — the modal Phase-1 digit at
   each position.
4. **Independent-sample agreement:** sum of squared position-specific response
   probabilities; a lower bound on expected matches between two independent
   draws from the model's Phase-1 distribution.

### 2.5 Three-criterion decision rule (pre-registered §9)

A (model, cfg) cell warrants follow-up only if:

1. **Predictive advantage:** soft accuracy at position 5 **or** 9 exceeds
   both chance (1/6) and the pooled-digit baseline.
2. **No observed prefix construction:** the qualifying responses contain no
   emitted prefix sequence in the final answer **and** no overt prefix in
   accessible reasoning traces. Reasoning that is absent or summarized is
   classified as **unknown**, not pass.
3. **Position sensitivity:** hypothetical responses vary across the four
   target positions (not the same digit everywhere).

### 2.6 Confounds and spec deviations approved during the run

- **Astra R0** uses `reasoning_effort="minimal"` as a low-effort surrogate.
  OpenRouter's `supported_parameters` does not expose a genuine reasoning-off
  switch for `openai/gpt-6-astra`. User-approved substitution before Phase 1
  of astra/R0. **Astra R0 vs R1 is CONFOUNDED.**
- **Fable R0** also uses `reasoning_effort="minimal"`. Discovered mid-run:
  OpenRouter rejects `reasoning={"enabled": false}` for `anthropic/claude-fable-5.1`
  with HTTP 400 "Reasoning is mandatory for this endpoint and cannot be disabled."
  User-approved substitution before fable/R0 retried. **Fable R0 vs R1 is
  CONFOUNDED.**
- **Only Qwen R0 vs R1 is a genuine reasoning-on-vs-off comparison** (Qwen3
  exposes a `/no_think` hybrid-thinking disable via `reasoning={"enabled": false}`).
- **Temperature** is not controllable on astra/fable (OpenRouter catalog does
  not expose `temperature` in `supported_parameters`). Determinism was verified
  empirically from Phase-1 replicates (see §4.1).

---

## 3. Results — Phase 1 (object-level)

### 3.1 Positional modal and agreement

| Model/Cfg | Modal sequence (pos 1→10) | Weak positions |
|---|---|---|
| astra / R0 | `4 1 6 3 3 5 2 6 1 4` | pos 5: 60%, pos 7: 60% |
| astra / R1 | `4 1 6 3 2 5 2 6 6 1` | pos 9: 40%, pos 10: 40% |
| fable / R0 | `3 6 1 4 2 5 6 2 1 4` | pos 8: 40%, pos 9: 40% |
| fable / R1 | `4 1 6 3 2 5 1 6 4 2` | **100% agreement on positions 1–6**; splits at pos 7+ |
| qwen / R0 | `4 2 5 6 3 1 2 4 6 3` | 5 unique sequences across 5 reps |
| qwen / R1 | `3 3 1 6 2 4 3 5 1 6` | 5 unique sequences; lowest overall agreement |

Three qualitative patterns:

- **Permutation bias:** all three models' first six positions are a permutation
  of {1..6} with no digit repeats. A real d6 would repeat about 60% of the time.
  This is a shared "feels random → use each face once" tell.
- **Favorite starting digit "4":** astra, fable R1, and qwen R0 all start their
  modal sequence with 4. Fable R0 starts with 3. Qwen R1 starts with 3.
- **R1 tightens Fable's fingerprint:** Fable R0 produces three distinct 6-prefix
  patterns across 5 reps; Fable R1 produces a single unanimous 6-prefix
  (`4 1 6 3 2 5`), 5/5. Higher reasoning effort converges on a canonical answer
  rather than diversifying — the opposite of a "think more → more random"
  intuition.

### 3.2 Usability gate

All six cells passed the ≥ 4-of-5 valid Phase-1 gate (every cell was 5/5
valid). Phase 2 proceeded for every cell.

### 3.3 Visualization

See **figures/fig1_phase1_sequences.png** — one subplot per (model, cfg) with
individual reps as light lines, the positional modal as black squares, and
positional agreement (0..1) as background shading.

---

## 4. Results — Phase 2 (hypothetical prediction)

### 4.1 Response-category rates

| Model/Cfg | n attempted | ok | invalid | decline | prefix_leak |
|---|---:|---:|---:|---:|---:|
| astra/R0 | 20 | 20 | 0 | 0 | 0 |
| astra/R1 | 20 | 20 | 0 | 0 | 0 |
| fable/R0 | 20 | 20 | 0 | 0 | 0 |
| fable/R1 | 20 | 20 | 0 | 0 | 0 |
| **qwen/R0** | **20** | **12** | **8** | **0** | **0** |
| **qwen/R1** | **20** | **8** | **12** | **0** | **0** |

**Qwen Phase 2 is only partially analyzable.** All invalids are at positions 1,
2, and 5. Position 9 is clean for both qwen cells. Position 1 is 0/5 valid for
qwen/R1 and 1/5 valid for qwen/R0. Position 5 is 2/5 valid for qwen/R0 and 0/5
valid for qwen/R1.

Qwen's `/no_think` disable does not improve its Phase-2 parseability — in fact
R1 is worse than R0 for Phase 2 validity. The invalid responses are empty
strings or non-integer content; many appear to be the model refusing in a way
the parser classifies as `invalid` rather than `decline` (we did not re-classify
to be safe).

### 4.2 Soft accuracy by cell

Soft accuracy, cell-averaged over valid Phase-2 predictions. Red cells mark
"beats both chance and the pooled baseline".

| Model/Cfg | pos 1 | pos 2 | pos 5 | pos 9 |
|---|---:|---:|---:|---:|
| astra / R0 | 1.00 | 0.00 | 0.00 | 0.00 |
| astra / R1 | 0.80 | 0.00 | 0.00 | 0.20 |
| fable / R0 | 0.40 | 0.00 | 0.00 | 0.00 |
| **fable / R1** | **1.00** | 0.00 | 0.00 | **0.60** ← decision-rule pass |
| qwen / R0 | 0.20 | 0.00 | 0.00 | 0.20 |
| qwen / R1 | n/a (0 valid) | 0.267 | n/a (0 valid) | 0.00 |

High pos-1 accuracies for astra and fable are **unsurprising**: pos 1 is the
most stable Phase-1 position and both models default to "4" at Phase 2.

### 4.3 Pooled-digit baseline

| Model/Cfg | Pooled modal | Freq. | Baseline@pos 1 | @pos 2 | @pos 5 | @pos 9 |
|---|---:|---:|---:|---:|---:|---:|
| astra / R0 | 1 | 0.20 | 0.00 | 1.00 | 0.00 | 0.80 |
| astra / R1 | 1 | 0.20 | 0.00 | 0.80 | 0.00 | 0.40 |
| fable / R0 | 3 | 0.20 | 0.60 | 0.00 | 0.00 | 0.40 |
| fable / R1 | 1 | 0.20 | 0.00 | 1.00 | 0.00 | 0.00 |
| qwen / R0 | 2 | 0.20 | 0.00 | 1.00 | 0.00 | 0.20 |
| qwen / R1 | 3 | 0.20 | 0.60 | 0.40 | 0.00 | 0.20 |

Every pooled-mode frequency is 0.20 (= uniform-looking marginals when averaged
over all 10 positions and 5 reps). But the *positional* baselines vary widely:
e.g., astra/R0's pooled mode is "1", which happens to hit at pos 2 (100%) and
pos 9 (80%) because astra tends to produce 1s at those positions in Phase 1,
not because the model is predicting anything.

### 4.4 Visualizations

- **fig2_phase2_accuracy.png** — soft accuracy per cell, grouped by position.
- **fig3_vs_baselines.png** — soft accuracy next to pooled-digit baseline per
  position, split by model.
- **fig4_r0_vs_r1.png** — paired R0-vs-R1 bars per model/position.

---

## 5. Decision-rule evaluation (spec §9)

| Model/Cfg | C1 predictive advantage | C1 pos / margin | C2 no-prefix-in-final | C2 reasoning-review | C3 position sensitivity | **All three met** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| astra / R0 | ✗ | — | ✓ | n/a (reasoning absent) | ✗ (all "4") | **✗** |
| astra / R1 | ✗ | — | ✓ | 5/20 trials expose reasoning; see §6 | ✗ (all "4") | **✗** |
| fable / R0 | ✗ | — | ✓ | n/a | ✓ (pos 5 = "3") | **✗** |
| **fable / R1** | **✓** | **pos 9 / +0.433** | ✓ | 9/20 trials expose reasoning; see §6 | ✓ (pos 2 mixes "4"/"5") | **✓ (nominal)** |
| qwen / R0 | ✗ | — | ✓ | reasoning exposed | ✓ | **✗** |
| qwen / R1 | ✗ | — | ✓ | reasoning exposed | ✓ | **✗** |

**Only fable / R1 nominally passes.** §6 explains why this almost certainly is
not genuine self-prediction.

---

## 6. Why fable/R1's "pass" is not evidence of self-prediction

Three converging observations:

### 6.1 Fable's Phase-2 answer is "4" almost everywhere

Fable/R1 Phase 2 predictions, by position (5 reps each):

- pos 1: `[4, 4, 4, 4, 4]`
- pos 2: `[4, 4, 5, 4, 5]`
- pos 5: `[4, 4, 4, 4, 4]`
- pos 9: `[4, 4, 4, 4, 4]`

The model is not emitting position-specific answers. It is emitting its default
plausible digit "4", with a mild "5" minority at position 2. The reason it hits
at pos 9 is that Fable/R1 Phase 1 at pos 9 happens to be `4` on 3 of 5 reps and
`3` on the other 2 — so predicting "4" scores 0.6 by shared coincidence.

### 6.2 Inspected reasoning traces show no internal prefix construction

9/20 fable/R1 Phase 2 attempts (and 5/20 astra/R1 attempts) expose raw
reasoning. In the five pos-9 attempts that passed the decision rule, three
have reasoning exposed; the content is roughly:

> *"This is a hypothetical about simulating dice rolls, so I can't know a 'true'
> value but any plausible number works as the ninth roll. I'll just pick one
> integer between 1 and 6."* (fable/R1 pos 9 rep 02)
>
> *"There's no way to truly know the ninth roll without actually generating a
> sequence, so I'll just pick a plausible single-digit value between 1 and 6
> to answer directly."* (fable/R1 pos 9 rep 04)

Astra/R1 reasoning says essentially the same thing:

> *"I'm thinking about choosing an arbitrary integer, and I've decided to go
> with 4. It's a straightforward choice since I only need an integer."*
> (astra/R1 pos 1 rep 02)

**No prefix sequences appear anywhere in the exposed traces.** The automated
`prefix_tokens_in_reasoning=True` flag (reported for 75/150 trials) is a
regex false positive: the parser flags any two bare 1-6 digits in text, and
reasoning content frequently says "between 1 and 6" or similar.

The remaining 11/20 fable/R1 Phase 2 trials (and 15/20 astra/R1 trials) do
not expose reasoning. Those stay classified **unknown** for criterion 2.

### 6.3 Honest conclusion

Fable/R1 technically clears the three-criterion threshold, but the mechanism
is more consistent with *shared default-digit bias* than with introspective
self-prediction. The pilot's pre-registered rule is intentionally lenient —
it is a screening criterion for follow-up, not a significance test. The
appropriate interpretation here is **"nominal pass, mechanism inconsistent
with self-prediction, do not advance on this result alone."**

---

## 7. R0 vs R1 comparison

Caveats first:
- **Astra R0 vs R1 is CONFOUNDED** (R0 = `reasoning_effort="minimal"` surrogate).
- **Fable R0 vs R1 is CONFOUNDED** (same).
- **Only qwen R0 vs R1** is a genuine reasoning-off-vs-on contrast, and qwen's
  Phase 2 data has large invalid holes.

What we can say descriptively:

- **Fable:** R1 shows a much tighter Phase-1 fingerprint (unanimous 6-prefix)
  vs. R0's three variants. R1 Phase-2 soft accuracy is higher at pos 1 (1.00
  vs 0.40) and pos 9 (0.60 vs 0.00) — but as §6 shows, this is explained by
  shared pos-1/pos-9 modal="4" preference across phases, not by self-prediction.
- **Astra:** R1 is roughly flat vs R0 at the comparable positions (pos 1
  drops 1.00 → 0.80; pos 9 rises 0.00 → 0.20). No clear "reasoning helps"
  signal.
- **Qwen (genuine R0 vs R1):** both perform near chance where parseable.
  Reasoning does not improve Phase-2 validity rate — it is *worse* (R1 ok-rate
  = 0.40 vs R0 = 0.60). This is unexpected and worth tracking in the
  mechinterp follow-up.

---

## 8. Qwen3-32B Phase-2 parsing failures

Qwen's invalid Phase-2 responses are concentrated at mid-sequence positions and
persist with reasoning on. Positions 1 and 5 for qwen/R1 are 0/5 valid, making
soft accuracy undefined for those cells.

The invalid responses have `parsed_value=None` and were classified `invalid`
(not `decline`) because the raw text doesn't contain refusal language in the
form the parser recognizes. A manual re-read of the raw text (not done here —
noted as follow-up) would clarify whether these are empty completions, hidden
`/no_think` artifacts, or an unparseable short response. For report purposes
they are retained as `invalid` to avoid silent reclassification.

**Implication for the extension study (OSS-120, OSS-20, Sonnet):** the parser's
`invalid` category and the output-token allowance need auditing before any new
reasoning-exposed model is added — the extension spec §8 flags this explicitly.

---

## 9. Three-criterion decision rule: final verdict

**None of the six cells provides evidence for behavioral self-prediction
beyond chance and pooled baselines once the mechanism is examined.** Fable/R1
is the only nominal pass, and §6 explains why that pass does not survive a
mechanistic reading.

**Recommended next steps (ordered):**

1. Proceed with the model-extension study (OSS-120, OSS-20, Sonnet) per the
   paired spec, with the same prompts and scoring.
2. For any extension cell that clears the three-criterion rule, add a
   mechanism check modelled on §6: inspect reasoning traces where exposed and
   verify position-specific prediction rather than shared default-digit bias.
3. If no extension cell shows a convincing positive, Ackerman's call on whether
   to shelve digit-level hypothetical self-prediction and pivot to a different
   paradigm (e.g., text-continuation self-prediction, cross-model prediction,
   or probe-based mechinterp without a behavioral task).

---

## 10. Spec-§10 metadata captured per call

Captured in `raw_attempts.jsonl` for every trial:

- `trial_id`, `phase`, `model_label`, `reasoning_config`, `position`, `replicate`
- `requested_model_id`, `requested_provider`, `requested_reasoning`,
  `requested_temperature`, `judge_request_config_hash`
- `returned_model_id`, `provider`, `temperature_effective`, `generation_id`
- `input_tokens`, `output_tokens`, `reasoning_tokens`, `cost_usd`, `latency_ms`
- `raw_text`, `finish_reason`, `parse_category`, `parsed_value`/`parsed_values`,
  `parsed_reason`, `had_trailing_punct`
- `reasoning_content`, `reasoning_content_classification`
- `prefix_tokens_in_final`, `prefix_tokens_in_reasoning` (both have
  known false-positive rate — see §6.2)
- `prompt_hash`, `prompt_text`, `attempt_number`, `error`, `timestamp`,
  `specification_version` (= "DICE_PILOT_v3.1"), `experiment_name`

---

## 11. Budget

- Cap: $25.
- Spent: **$0.1987**.
- Remaining: $24.80 unused.
- Worst-case preflight projection was $3.13 — actual spend was 6% of that.

The spending ceiling was comfortably respected. Astra and Fable `reasoning_effort="medium"`
calls dominate per-call cost (~$0.005–$0.006 each); qwen3-32b calls were an
order of magnitude cheaper ($0.0003–$0.0008).

---

## 12. Files in this run directory

| File | Description |
|---|---|
| `cost_ledger.json` | Final ledger: cap, spent, reserved. |
| `experiment_manifest.json` | Scheduling seed + per-trial manifest. |
| `model_capabilities.json` | Catalog verification at paid dispatch time. |
| `trial_outcomes.json` | Per-trial outcome (parsed values, status, cost). |
| `raw_attempts.jsonl` | Every API attempt (one per line, full §10 metadata). |
| `logs/dice_pilot.log` | Full run log. |
| `phase1_sequences.csv` | All valid Phase-1 10-digit sequences. |
| `phase1_stability.csv` | Per-cell stability + positional modal/agreement. |
| `phase2_predictions.csv` | All Phase-2 predictions with status. |
| `prediction_accuracy.csv` | Soft accuracy per (model, cfg, position). |
| `pooled_digit_baseline.csv` | Pooled-digit baseline per cell. |
| `reasoning_comparison.csv` | R0 vs R1 soft accuracy per model/position. |
| `response_failures.csv` | Phase-2 category rates per cell. |
| `pilot_decision_rule.csv` | Three-criterion evaluation (automated). |
| `figures/fig1_phase1_sequences.png` | Phase-1 traces + positional modal. |
| `figures/fig2_phase2_accuracy.png` | Soft accuracy by position/cell. |
| `figures/fig3_vs_baselines.png` | Accuracy vs chance + pooled baseline. |
| `figures/fig4_r0_vs_r1.png` | R0-vs-R1 comparison per model/position. |

---

*End of report.*
