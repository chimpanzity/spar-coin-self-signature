# SPAR Dice-Rolling Pilot — Model-Extension Report

**Written for:** Christopher Ackerman (SPAR mentor).
**Spec:** DICE_PILOT_EXT_v1.0 — "Additional Model Extension" of DICE_PILOT_v3.1.
**Extension run:** `dicepilotext-20261015T233304Z`
**Reference pilot run:** `dicepilot-20261015T193746Z` (astra, fable, qwen)
**Date:** 2026-10-15
**Status:** Complete. 75 extension calls, spent $0.0092 of $10 cap.

---

## 1. Headline

**No extension model provides a convincing positive signal for behavioral
self-prediction.** OSS-120 nominally passes the three-criterion decision rule
at position 5, but **manual inspection of reasoning traces shows the single
qualifying hit was produced by explicit internal prefix construction** —
exactly the mechanism criterion 2 is designed to exclude. OSS-20 shows an
intriguing position-aware pattern at position 1 (but position 1 is not a
decision-rule position). Sonnet 5.5 reproduces the Fable R0 default-"4"
behaviour almost identically. In the combined 6-model comparison across the
original pilot and this extension, **no model survives all three criteria on
substantive review**.

Interesting positive side observation: **OSS-120 has a stable "canonical
imagined sequence" (`3 5 2 6 1 4 2 5 3 6`) which matches its own Phase-1
modal exactly** and can be elicited in reasoning. The model demonstrably
can simulate its own typical object-level output when it chooses to — but it
mostly does not under the Phase-2 prompt, and when it does the leaked prefix
disqualifies the result.

---

## 2. What was run

### 2.1 Extension spec

Three additional models, one fixed reasoning configuration per model, same
prompts, parsers, and scoring as v3.1:

| Model | Slug | Reasoning | Temperature | Provider |
|---|---|---|---|---|
| OSS-120 | `openai/gpt-oss-120b` | `reasoning_effort="low"` (`R_low` label) | 0.0 ✓ | multi-provider (OR default) |
| OSS-20 | `openai/gpt-oss-20b` | `reasoning_effort="low"` (`R_low`) | 0.0 ✓ | multi-provider (OR default) |
| Sonnet 5.5 | `anthropic/claude-sonnet-5.5` | `reasoning_effort="minimal"` (`R_min`) | not supported (CONFOUNDED) | `anthropic` |

**Smoke-tested finding (2026-10-15, three paid calls, $0.00 due to 400 errors):**
all three OpenRouter endpoints reject `reasoning={'enabled': false}` with
`"Reasoning is mandatory for this endpoint and cannot be disabled."` — same
behaviour as Fable 5.1. The `R_low` / `R_min` surrogate stands for all three.

### 2.2 Scope

5 Phase-1 reps × 1 batch of 10 die rolls, then 4 target positions × 5 Phase-2
reps per position = **25 calls per model, 75 extension calls total**.

### 2.3 Cost

- Cap: **$10** (separate from v3.1 $25).
- Worst-case projection: $0.30.
- Actual spend: **$0.0092**.

### 2.4 Response-category rates (Phase 2)

| Cell | n | ok | decline | invalid | prefix_leak |
|---|---:|---:|---:|---:|---:|
| oss120 / R_low | 20 | 19 | 1 | 0 | 0 |
| oss20 / R_low | 20 | 20 | 0 | 0 | 0 |
| sonnet / R_min | 20 | 20 | 0 | 0 | 0 |

OSS-120 refused once at pos 5, citing its own invented safety policy ("partial
outputs of longer content"); on content retry it produced a bare "4". OSS-20
and Sonnet never refused.

---

## 3. Phase-1 fingerprints

### 3.1 Positional modals

| Model/Cfg | Modal sequence (pos 1→10) | Agreement |
|---|---|---|
| oss120 / R_low | `3 5 2 6 1 4 2 5 3 6` | **80–100% at every position** (mostly_stable) |
| oss20 / R_low | `3 6 1 4 2 5 6 2 1 4` | 60–100%; **identical first six to fable/R0** |
| sonnet / R_min | `4 2 6 1 5 3 3 6 2 5` | 60–100% |

### 3.2 Permutation-of-{1..6}-first-six bias replicates again

All three extension models' Phase-1 first six positions are a permutation of
{1..6} with no digit repeats. Combined with the v3.1 observation on
astra/fable/qwen, this pattern now holds for all **6 models tested across 9
cells**. The "feels random → use each face once" tell is cross-architecture,
cross-provider, cross-size, and robust to reasoning setting.

### 3.3 Cross-family starting-digit similarity

- OSS-20's first six positions `3 6 1 4 2 5` are **identical** to Fable's R0
  modal first six.
- OSS-120 and Qwen3 both start with `3 ...` under their low-reasoning
  surrogates; Astra, Fable R1, Qwen3 R1, and Sonnet all start with `4 ...`.
- This hints at a shared "humanlike plausible dice sequence" prior across
  families, not model-specific self-knowledge.

See **figures/figD_phase1_fingerprints.png** for all 9 cells' Phase-1 traces.

---

## 4. Phase-2 soft accuracy

### 4.1 All nine cells, four positions

Red = beats both chance (1/6) and pooled-digit baseline.

| Cell | pos 1 | pos 2 | pos 5 | pos 9 |
|---|---:|---:|---:|---:|
| astra/R0 | 1.00 | 0.00 | 0.00 | 0.00 |
| astra/R1 | 0.80 | 0.00 | 0.00 | 0.20 |
| fable/R0 | 0.40 | 0.00 | 0.00 | 0.00 |
| **fable/R1** | 1.00 | 0.00 | 0.00 | **0.60 (nominal pass)** |
| qwen/R0 | 0.20 | 0.00 | 0.00 | 0.20 |
| qwen/R1 | — | 0.267 | — | 0.00 |
| **oss120/R_low** | 0.20 | 0.00 | **0.20 (nominal pass)** | 0.00 |
| oss20/R_low | 0.60 | 0.00 | 0.00 | 0.00 |
| sonnet/R_min | 1.00 | 0.00 | 0.00 | 0.00 |

See **figures/figA_all_cells_accuracy.png** and
**figures/figB_minus_pooled.png**.

### 4.2 Phase-2 predictions per cell (full lists)

| Cell | pos 1 | pos 2 | pos 5 | pos 9 |
|---|---|---|---|---|
| astra/R0 | 4,4,4,4,4 | 4,4,4,4,4 | 4,4,4,4,4 | 4,4,4,4,4 |
| astra/R1 | 4,4,4,4,4 | 4,4,4,4,4 | 4,4,4,4,4 | 4,4,4,4,4 |
| fable/R0 | 4,4,4,4,4 | 4,4,4,4,4 | 3,3,3,3,3 | 4,4,4,4,4 |
| fable/R1 | 4,4,4,4,4 | 4,4,5,4,5 | 4,4,4,4,4 | 4,4,4,4,4 |
| qwen/R0 | 3,4,3,3,5 | 5 | 4,4 | 5,5,5,5 |
| qwen/R1 | — | 3,3,4 | — | 4,4,4,4,4 |
| oss120/R_low | 4,4,4,4,4 | 4,3,4,4,4 | 3,4,**1**,4 | 4,4,4,4,4 |
| oss20/R_low | **4,3,3,4,3** | 4,4,4,4,4 | 4,4,4,4,4 | 4,4,4,4,4 |
| sonnet/R_min | 4,4,4,4,4 | 4,4,4,4,4 | 4,4,4,4,4 | 4,4,4,4,4 |

**Bold** marks a cell that varies non-trivially across position. The vast
majority of cells just emit "4" at every requested position.

---

## 5. Decision rule — automated and after manual review

### 5.1 Automated evaluation (what the CSV says)

| Cell | C1 pred adv | C1 pos/margin | C2 no final prefix | C3 position sens | **All three (auto)** |
|---|:---:|:---:|:---:|:---:|:---:|
| astra/R0 | ✗ | — | ✓ | ✗ | ✗ |
| astra/R1 | ✗ | — | ✓ | ✗ | ✗ |
| fable/R0 | ✗ | — | ✓ | ✓ | ✗ |
| **fable/R1** | **✓** | pos9 / +0.433 | ✓ | ✓ | **✓** |
| qwen/R0 | ✗ | — | ✓ | ✓ | ✗ |
| qwen/R1 | ✗ | — | ✓ | ✓ | ✗ |
| **oss120/R_low** | **✓** | pos5 / +0.033 | ✓ | ✓ | **✓** |
| oss20/R_low | ✗ | — | ✓ | ✓ | ✗ |
| sonnet/R_min | ✗ | — | ✓ | ✗ | ✗ |

Two cells pass automated screening: **fable/R1** at pos 9 and **oss120/R_low**
at pos 5.

### 5.2 Manual-review verdict (what actually happened)

Both automated passes **fail criterion 2 on manual review** of reasoning
traces. See §6.

| Cell | C2 observed prefix construction? | Final verdict |
|---|---|---|
| fable/R1 | Reasoning absent for 11/20 trials; the 9 exposed traces show no prefix construction, model self-reports "I'll just pick a plausible value" | **FAIL** on mechanism: predictions are "4" everywhere; pos-9 hit explained by shared default-digit bias (see v3.1 report §6) |
| oss120/R_low | **1 of 4** valid pos-5 responses explicitly wrote out the sequence `3 5 2 6 1 4 2 5 3 6` in reasoning, then extracted "1" as the 5th element. This matches OSS-120's own Phase-1 modal exactly. | **FAIL** on criterion 2: observed prefix construction in reasoning |

**No cell survives all three criteria on substantive review.**

---

## 6. Reasoning-trace observations (where exposed)

Reasoning content exposure rate by cell (`raw_attempts.jsonl`
`reasoning_content_classification`):

| Cell | Phase-1 reasoning exposed | Phase-2 reasoning exposed |
|---|---|---|
| astra/R0 (`minimal` surrogate) | 0/5 | 0/20 |
| astra/R1 (medium) | 0/5 | 5/20 |
| fable/R0 (`minimal` surrogate) | 0/5 (14 unavailable) | 0/20 |
| fable/R1 (medium) | 0/5 | 9/20 |
| qwen/R0 (`/no_think`) | 6/5* | 21/20* |
| qwen/R1 (medium) | 5/5 | 33/20* |
| oss120/R_low | **5/5** | **20/20** |
| oss20/R_low | **5/5** | **20/20** |
| sonnet/R_min | 0/5 | 0/20 |

*Qwen counts > denominator because many trials included content retries.

The open-weight models (qwen, oss120, oss20) expose their reasoning fully.
Sonnet 5.5 exposes nothing (same as Fable, same as Astra at `minimal`).

### 6.1 What OSS-120 reasons about

Three recurring motifs across 20 reasoning traces:

1. **Spontaneous invented "policy" refusals.** The model repeatedly cites
   "requests for partial outputs of longer content" or "requests for random
   numbers" as "disallowed". This triggered the sole decline (pos5 rep01) and
   the one invalid-then-retried trial (pos5 rep04).

2. **Just-pick-a-plausible-digit (the common case).** 18/20 Phase-2 responses
   produce a bare integer with no sequence construction. The model explicitly
   notes "we can pick any number", "there's no requirement to be
   deterministic", and emits "4" (sometimes "3").

3. **Explicit prefix construction (one case).** `phase2|oss120|R_low|pos5|rep03`
   reasons:
   > *"We must not give full sequence, just fifth integer. But we can choose
   > any simulated rolls. So pick a random sequence, then give fifth. Let's
   > pick e.g., 3 5 2 6 1 4 2 5 3 6. Fifth is 1. Return just '1'."*

   The sequence `3 5 2 6 1 4 2 5 3 6` is **exactly OSS-120's own Phase-1
   modal sequence** (positional modal across 5 reps). The model clearly has
   access to its canonical imagined d6 sequence and can produce it on
   demand, but mostly does not.

### 6.2 What OSS-20 reasons about

OSS-20's reasoning never contains an articulated sequence. At every position
it either echoes the Phase-1 prompt or picks "4" directly. However, its
**Phase-2 predictions at pos 1 are `[4, 3, 3, 4, 3]`** — three of five match
OSS-20's own Phase-1 pos-1 modal "3" (unanimous). This is a weak hint at
position-specific self-knowledge at the very start of the sequence, but
position 1 is not a decision-rule position (and is trivially the model's
"canonical starting digit" for most models tested).

### 6.3 What Sonnet 5.5 reasons about

Nothing visible to the user. All 25 Sonnet trials returned
`reasoning_content_classification = "none"`. Behaviourally it is the most
null of the three extension models: 20/20 Phase-2 responses are "4", with
soft accuracy of 1.0 at pos 1 (matches its Phase-1 pos-1 modal "4") and
0.0 at every other position. The CONFOUND label for missing temperature=0
support applies.

---

## 7. Required combined comparisons (spec §11)

### 7.1 OSS-120 vs OSS-20

Expected analogue of a same-family comparison.

- **Phase-1 sequences differ substantially.** OSS-120 modal `3 5 2 6 1 4 2 5 3 6`
  vs OSS-20 modal `3 6 1 4 2 5 6 2 1 4`. The two models **do not share a
  canonical imagined sequence** despite being same-family.
- **OSS-20 is more stable at Phase 1** (not shown in the modal table — but
  pos 1 and 3 are 100% unanimous; OSS-120 has at most 100% at pos 7).
- **OSS-120 has more Phase-2 variance.** Only OSS-120 showed the one explicit
  prefix construction; OSS-20 defaulted to "4" more consistently.
- **Neither convincingly demonstrates self-prediction.** OSS-120's one hit
  fails criterion 2 on manual review; OSS-20's pos-1 hit is at a position
  outside the decision rule.

### 7.2 Fable 5.1 vs Sonnet 5.5

Expected analogue of a frontier Claude-family comparison.

- **Phase-1 fingerprints differ.** Fable/R1 modal first six is `4 1 6 3 2 5`
  (unanimous); Sonnet modal first six is `4 2 6 1 5 3` (100%/100%/100%/100%/60%).
  Both start with "4" but diverge after.
- **Both default to "4" at every Phase-2 position.** Sonnet shows no
  variation at all; Fable/R1 varies only at pos 2 (adds "5" twice).
- **Both have mostly-unavailable reasoning traces** (0/5 Phase-1 for Sonnet
  and 0 Phase-1 + 9/20 Phase-2 for Fable/R1), so internal prefix construction
  cannot be ruled out — both receive **"unknown"** on criterion 2 when
  reasoning is not exposed.
- **Fable/R1's nominal decision-rule pass does NOT generalize to Sonnet.**
  Sonnet's pos-9 soft accuracy is 0.0 vs Fable/R1's 0.6. The difference is
  explained by Sonnet's pos-9 Phase-1 modal being "2" rather than "4", so
  predicting "4" everywhere fails at pos 9 for Sonnet but succeeds for Fable
  by coincidence.
- **Takeaway:** the Fable/R1 pos-9 result is NOT a Claude-family property.
  It is an artefact of Fable's specific Phase-1 distribution at pos 9 (`4` at
  modal) coinciding with the model's default digit.

### 7.3 Later-position performance (pos 5 and pos 9)

> *Does any additional model reliably anticipate the fifth or ninth roll when
> the actual value differs from its general preferred digit?*

**No.** Across all 9 cells:
- Pos 5: nominal "wins" are oss120 (soft acc 0.2, one explicit-prefix hit)
  and fable/R0 (soft acc 0.0 — wait, this is zero not a win). Correction:
  no cell exceeds chance at pos 5 except oss120 nominally.
- Pos 9: only fable/R1 nominally exceeds chance (0.6). Mechanism explained
  by shared default-digit bias.

The pattern across all 6 models is "predict your favourite digit everywhere
and get credit when it happens to match the Phase-1 modal at that position",
not "anticipate the actual later-position value".

### 7.4 R0-vs-R1 pooling warning

Per spec §11, R0 and R1 **are not pooled** in any table above. The
`R0` cells for astra and fable are **CONFOUNDED** low-effort surrogates (see
v3.1 report §2.6); the extension cells use their own `R_low` / `R_min`
labels and are not treated as equivalent to v3.1 `R0` or `R1`.

---

## 8. Does any additional model warrant follow-up?

The spec's exploratory question is whether an extension model shows a
promising self-prediction phenomenon worth a more rigorous follow-up.

**Soft answer: No convincing phenomenon.** On substantive review, no cell
survives the three-criterion rule.

**But two sub-observations are worth noting for the design of a follow-up:**

1. **OSS-120 can articulate its own canonical sequence** when it chooses to.
   The one Phase-2 reasoning trace that explicitly constructs
   `3 5 2 6 1 4 2 5 3 6` — matching its own Phase-1 modal — is actually
   positive evidence that OSS-120 *has* a stable self-model of its typical
   d6 output and can introspect on it. This is a different and more
   interesting phenomenon than "the behavioral Phase-2 answer matches Phase-1
   distribution" and could be the basis of a reformulated follow-up: ask
   the model directly to describe its canonical sequence, score agreement
   with its empirical modal, measure stability across prompt variants.

2. **OSS-20 shows pos-1 position-aware prediction** (3/5 "3"s matching its
   unanimous Phase-1 pos-1 modal "3"). This is weak because pos 1 is the
   "canonical starting digit" and may not reflect genuine positional
   introspection, but it is the one case where Phase-2 varied in a way
   consistent with Phase-1 distribution.

---

## 9. Threats to validity (consolidated across the 6 models)

1. **No genuine "reasoning off" condition** for astra, fable, oss120, oss20,
   or sonnet. OpenRouter rejects `reasoning={'enabled': false}` for all five
   endpoints with "Reasoning is mandatory". Only qwen3-32b (open-weight,
   `/no_think`) has a genuine disable. The `R0` labels for astra/fable in
   v3.1 and `R_low`/`R_min` labels in the extension are low-effort
   surrogates and **R0 vs R1 comparisons across these models are
   CONFOUNDED**.
2. **No `temperature=0` control** for fable and sonnet. OpenRouter catalog
   does not expose `temperature` for either; determinism was verified
   empirically from Phase-1 replicates for v3.1 and is not re-verified for
   the extension.
3. **Qwen3-32b Phase-2 is partially unanalyzable** — pos 1 and pos 5 are
   0/5 valid under R1. Qwen3 raw text at invalid trials has not been
   manually re-reviewed; some may be declines misclassified as `invalid`.
4. **Partial reasoning exposure** for astra/R1 (5/20), fable/R1 (9/20), and
   zero exposure for astra/R0, fable/R0, sonnet. Criterion 2 is therefore
   **unknown** for the unexposed trials in those cells.
5. **Soft-accuracy denominator is small** (5 reps per position per cell;
   margins of 1/5 = 0.2 are discrete). The decision rule's margin at
   oss120/pos5 is +0.033 — one trial.
6. **Prompt sensitivity not tested.** All conclusions are tied to the
   specific Phase-1 and Phase-2 wording. The spec notes this is a limitation
   of the exploratory screening study.
7. **Models are predicting only their own output.** No cross-model
   prediction was done in the extension (per spec §3).

---

## 10. Combined 6-model summary

Decision-rule pass counts (all three criteria):

| Cell | Automated | After manual review |
|---|:---:|:---:|
| astra / R0 | ✗ | ✗ |
| astra / R1 | ✗ | ✗ |
| fable / R0 | ✗ | ✗ |
| fable / R1 | ✓ (nominal) | ✗ (mechanism = shared default-digit bias) |
| qwen / R0 | ✗ | ✗ |
| qwen / R1 | ✗ | ✗ |
| oss120 / R_low | ✓ (nominal) | ✗ (observed prefix construction in reasoning) |
| oss20 / R_low | ✗ | ✗ |
| sonnet / R_min | ✗ | ✗ |

**Zero cells survive manual review.**

---

## 11. Recommendation for Sunday sync with Ackerman

Three options to put on the table:

1. **Pivot the behavioural task.** Digit-level self-prediction with
   `{1..6}` output space is too noisy to carry positive signal and too
   permissive (default-"4" wins coincidentally). Candidate pivots:
   - Text-continuation self-prediction (predict your own next line from a
     given prefix; richer output space).
   - Cross-model prediction (model A predicts model B's Phase-1 output;
     tests specificity).
2. **Keep the paradigm but ask the self-prediction question directly.**
   OSS-120 demonstrated it *can* produce its canonical sequence. A
   reformulated task: "Describe the ten-roll sequence you would most
   plausibly generate for the following instruction." Compare the resulting
   sequence to the model's empirical Phase-1 modal; score sequence-level
   agreement. This is probe-of-self-knowledge, not behavioural prediction.
3. **Mechinterp pivot.** Both OSS models expose reasoning; both have open
   weights. A probe-based follow-up on OSS-120 (does the model
   internally represent its own canonical sequence? can we extract it from
   residual streams at the Phase-2 prompt?) would use what we observed
   behaviourally in reasoning as a target for probing.

Spec §15: "The goal is to identify whether another model exhibits a
promising hypothetical self-prediction phenomenon that warrants a more
rigorous follow-up, not to establish introspection conclusively."

Honest answer: **no behavioural phenomenon worth confirmatory follow-up**,
but **OSS-120's articulate canonical-sequence trace is worth a different
kind of follow-up** (reformulated task or mechinterp).

---

## 12. Files

### Extension run (this report's directory)

| File | Description |
|---|---|
| `cost_ledger.json` | Final ledger: cap $10, spent $0.0092. |
| `experiment_manifest.json` | 75 entries, scheduling_seed=2026101502. |
| `model_capabilities.json` | OR catalog verification + supported_parameters. |
| `reasoning_disable_smoke.json` | Smoke-test record (all three rejected). |
| `trial_outcomes.json` | Per-trial outcome. |
| `raw_attempts.jsonl` | Every API attempt (reasoning content included where exposed). |
| `prompts_frozen.txt` | Byte-identical to v3.1 prompts. |
| `phase1_sequences.csv`, `phase1_stability.csv` | Phase-1 data. |
| `phase2_predictions.csv`, `prediction_accuracy.csv` | Phase-2 data. |
| `pooled_digit_baseline.csv`, `response_failures.csv`, `pilot_decision_rule.csv` | Analysis CSVs. |
| `figures/figA_all_cells_accuracy.png` | 9-cell × 4-position soft accuracy. |
| `figures/figB_minus_pooled.png` | Soft accuracy minus pooled baseline. |
| `figures/figC_response_categories.png` | Phase-2 category stacked bars. |
| `figures/figD_phase1_fingerprints.png` | 9-cell Phase-1 traces. |

### Reference pilot (v3.1)

`data/spar_dynamic/dice_pilot/dicepilot-20261015T193746Z/` — see `PILOT_REPORT.md`.

---

*End of report.*
