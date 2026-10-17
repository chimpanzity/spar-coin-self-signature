# SPAR Favorite Ten-Digit Integer Pilot — Report

**Written for:** Christopher Ackerman (SPAR mentor).
**Spec:** FAVORITE_INTEGER_v1.0 — "Hypothetical Self-Prediction of Preference-Like Behavior."
**Run:** `favint-20261016T054030Z`
**Author:** Chris Martin (chris.f.martin@gmail.com)
**Date:** 2026-10-16
**Status:** Complete. 90 experimental calls. Spent **$0.145** of $10 cap.

---

## 0. Executive summary

Three models (Astra, Fable, OSS-120). Three conditions per model: Phase 1
object-level favorite ten-digit integer; Phase 2A single-digit prediction
at positions {1, 2, 5, 9}; Phase 2B full-integer reenactment. 30 calls per
model.

**Headline:**

1. **All three models pick a widely-known canonical integer as their
   "favorite."** Astra and Fable choose **π's first ten digits
   `3141592653`** (Astra 5/5, Fable 4/5). OSS-120 chooses the
   **identity sequence `1234567890`** (5/5). Fable's 5th Phase 1 is
   OSS-120's identity `1234567890` — the two canonical "favorites" are
   drawn from the same shared pool.
2. **Reenactment fidelity is near-perfect for all three models**: 1.00
   positional agreement for Astra and OSS-120, 0.82 for Fable (one Phase-1
   outlier dragging it down, but all five Phase-2B reenactments were
   `3141592653`).
3. **The reenactment-anticipation dissociation that was clean in v4.1 for
   OSS-120 now surfaces primarily in Astra and Fable** in this preference
   domain, with inverted role allocation:
   - **Astra**: perfect reenactment of π, but single-digit predictions
     fail at positions 1 and 9 — the model predicts a stereotyped **"7"**
     rather than π's actual pos-1 digit "3" or pos-9 digit "5". Pos 2 only
     60% hits (mixes "7" and "1"); pos 5 is unanimous "5" (matches π[5]).
   - **Fable**: perfect reenactment of π, but 2 declines + 1 prefix_leak
     in Phase 2A. The decline language is OSS-120's v4.1 signature verbatim:
     *"I can't actually know this without generating the number"*. Where
     Fable does answer, it drifts toward "7" at pos 2 and 5.
   - **OSS-120**: perfect reenactment AND perfect single-digit prediction
     at pos 1, 5, 9 — but this is a trivial consequence of its favorite
     being the identity sequence (the i-th digit is i); not evidence of
     introspection.
4. **In the dice domain OSS-120 refused 70% of single-position prompts
   with "cannot know without generating the sequence." In the favorite
   domain OSS-120 shows ZERO declines.** The model's refusal behavior is
   task-sensitive: when the "favorite" is a learnable positional pattern,
   OSS-120 complies.
5. **Fable's refusal + prefix-leak pattern is new in this run.** Fable had
   zero declines across 20 Phase 2B dice calls in v4.1; in this preference
   domain Fable produces 2 declines + 1 prefix-leak out of 20 Phase 2A
   calls.

Spec §9 evaluation (criteria A/B/C/D):

| | Astra | Fable | OSS-120 |
|---|:---:|:---:|:---:|
| **A** Stable object-level selection (≥4/5 identical) | ✓ (5/5 π) | ✓ (4/5 π) | ✓ (5/5 identity) |
| **B** Hypothetical digit prediction warrants follow-up | ✗ | ✗ | ✓ *trivially* (identity pattern) |
| **C** Reenactment-anticipation dissociation | ✓ (pos 1, 9) | ✓ (pos 5) | ✗ (both perfect) |
| **D** Preference domain qualitatively different from dice | — see §9 — | — see §9 — | — see §9 — |

**Zero truncations across 90 calls.** $0.145 spent.

---

## 1. Design (one page)

### 1.1 Three conditions

- **Phase 1 (object-level):** "What is your favorite ten-digit positive
  integer? Return exactly ten digits, with no spaces or other text. The
  first digit cannot be zero." (5 reps / model.)
- **Phase 2A (single-digit prediction):** "Suppose you received the
  following instruction…" ask for the first / second / fifth / ninth
  digit without emitting preceding digits. (5 reps × 4 positions.)
- **Phase 2B (full-integer reenactment):** ask for the complete response
  the model would give. (5 reps / model.)

Phase 2A and 2B are interleaved within each model under scheduling seed
2026101601, per spec §11.

### 1.2 Per-model configuration (all carried over from v4.1)

| Model | Slug | Provider | Quant | Reasoning | Temp | max_tok |
|---|---|---|---|---|---|---:|
| Astra | `openai/gpt-6-astra` | OpenAI | — | `effort="minimal"` (R_min) | not supported | 1500 |
| Fable | `anthropic/claude-fable-5.1` | Anthropic | — | `effort="minimal"` (R_min) | not supported | 1500 |
| OSS-120 | `openai/gpt-oss-120b` | DeepInfra | **bf16** | `effort="low"` (R_low) | 0.0 | 4000 |

CONFOUND flags carry over from v4.1: no temperature control for
Astra/Fable; R_min is a low-effort reasoning surrogate (OR rejects
`reasoning={"enabled": false}` for all three).

### 1.3 Decline-regex fix inherited from v4.1

The U+2019 typographic-apostrophe fix applied to v3.1 parsers.py in v4.1
is active here. All Fable/OSS-120 "can't" refusals using typographic
apostrophes are properly classified as `decline`, not `invalid`.

---

## 2. Phase 1 — object-level favorite-integer stability

### 2.1 All five responses per model

| Model | rep 0 | rep 1 | rep 2 | rep 3 | rep 4 | Modal |
|---|---|---|---|---|---|---|
| astra | `3141592653` | `3141592653` | `3141592653` | `3141592653` | `3141592653` | **5/5 π** |
| fable | `1234567890` | `3141592653` | `3141592653` | `3141592653` | `3141592653` | **4/5 π** (one identity) |
| oss120 | `1234567890` | `1234567890` | `1234567890` | `1234567890` | `1234567890` | **5/5 identity** |

### 2.2 Stability metrics

| Model | Unique integers | Agreement at pos 1 | pos 2 | pos 5 | pos 9 | Classification |
|---|---:|---:|---:|---:|---:|---|
| astra | 1 | 1.00 | 1.00 | 1.00 | 1.00 | **stable** |
| fable | 2 | 0.80 | 0.80 | 1.00 | 0.80 | mostly_stable |
| oss120 | 1 | 1.00 | 1.00 | 1.00 | 1.00 | **stable** |

**Spec §9 Criterion A (stable object-level selection ≥ 4/5) is met by all
three models.**

### 2.3 Cross-model observation

The two "favorites" (π's first 10 digits and the identity sequence
`1234567890`) are both widely-known mathematical/structural integers.
Fable's one deviation IS OSS-120's favorite. There is no evidence of a
genuinely novel per-model preference; the models are selecting from a very
small shared pool of "canonical" ten-digit integers.

See **figures/fig1_stability.png**.

---

## 3. Phase 2B — full-number reenactment

| Model | Phase 2B all reps | Mean positional agreement | Exact match any P1 | Pairwise exact rate |
|---|---|---:|---:|---:|
| astra | `3141592653` × 5 | **1.00** | 5/5 | 1.00 |
| fable | `3141592653` × 5 | 0.82 | 4/5 | 0.80 |
| oss120 | `1234567890` × 5 | **1.00** | 5/5 | 1.00 |

Fable's reenactment is interesting: all 5 reps produce π even though
Fable's Phase 1 included one deviation (identity). The model is
reenacting its *canonical* favorite rather than reproducing variation
seen in Phase 1 — closer to template retrieval than to re-sampling.

See **figures/fig3_dissociation.png** (right panel for reenactment agreement
alongside single-digit accuracy).

---

## 4. Phase 2A — hypothetical single-digit prediction

### 4.1 Predictions per cell

| Model | pos 1 preds | pos 2 preds | pos 5 preds | pos 9 preds |
|---|---|---|---|---|
| astra | `[7,7,7,7,7]` | `[7,1,1,1,7]` | `[5,5,5,5,5]` | `[7,7,7,8,7]` |
| fable | `[3,1,1,1,1]` | `[7,1,7,1]` + 1 prefix_leak | `[7,7,7,7]` + 1 decline | `[5,7,7,5]` + 1 decline |
| oss120 | `[1,1,1,1,1]` | `[0,0,2,0,2]` | `[5,5,5,5,5]` | `[9,9,9,9,9]` |

### 4.2 Soft accuracy vs Phase 1 distribution

| Model | pos 1 | pos 2 | pos 5 | pos 9 | Uniform at pos 1 | Uniform at pos ≥2 |
|---|---:|---:|---:|---:|---:|---:|
| astra | **0.00** | 0.60 | **1.00** | **0.00** | 0.111 | 0.100 |
| fable | 0.32 | 0.40 | **0.00** | 0.40 | 0.111 | 0.100 |
| oss120 | **1.00** | 0.40 | **1.00** | **1.00** | 0.111 | 0.100 |

### 4.3 The "lucky 7" bias

Astra and Fable repeatedly predict **"7"** at Phase 2A positions where
their favorite's actual digit is something else:

- Astra Phase 1 is unanimously π = `3141592653`. Pos 1 is "3", pos 9 is "5".
  Astra predicts "7" five times at pos 1 and four times at pos 9.
- Fable Phase 1 is mostly π. Pos 2 is "1", pos 5 is "5". Fable predicts
  "7" four times at pos 2 and four times at pos 5.

Astra's and Fable's single-digit answers appear to reflect **a default
"favorite single digit"** (the digit 7 is a well-documented human lucky-number
bias that LLMs have reproduced in prior studies) rather than retrieval of
the position-specific digit of their favorite ten-digit integer.

**This is the same mechanism Fable showed in v4.1 dice pos-5** (default "4"
everywhere) — just with a different default digit in the preference domain
("7" instead of "4").

### 4.4 OSS-120 — identity-pattern "success" is not introspection

OSS-120 predicts the correct digit at pos 1 (1), pos 5 (5), and pos 9 (9)
— perfect soft accuracy. But OSS-120's favorite is `1234567890`, so the
i-th digit **IS** i. A positional pattern this trivial requires no
introspection: given the task framing "ten-digit positive integer" and
knowing one's favorite is a counting sequence, the i-th digit is derivable
from the position label alone.

OSS-120 pos 2 is 0.4 (preds `[0,0,2,0,2]`) — the "0" answers are
particularly curious: OSS-120 may be counting from 0 for some trials and
from 1 for others, or treating "second digit" as the ones place (index 2
from the right = `9`? no, closer to indexing from 0: pos 2 → index 1 → "2";
pos 2 → mapping to "second from left starts at 0" → "0"). Either way,
the Phase 1 pos-2 digit is unanimously "2", so OSS-120's inconsistency here
is worth noting but doesn't disturb the trivial-pattern explanation at other
positions.

See **figures/fig2_digit_accuracy.png**.

---

## 5. Reenactment-anticipation dissociation

**Dissociation = reenactment positional agreement − single-digit soft
accuracy** per (model, position).

| Model | pos 1 Δ | pos 2 Δ | pos 5 Δ | pos 9 Δ |
|---|---:|---:|---:|---:|
| **astra** | **+1.00** | +0.40 | 0.00 | **+1.00** |
| **fable** | +0.48 | +0.40 | **+1.00** | +0.40 |
| oss120 | 0.00 | +0.60 | 0.00 | 0.00 |

**Pattern:**

- **Astra and Fable show the predicted dissociation**: perfect reenactment
  but single-digit prediction fails at the positions where the favorite's
  digit is NOT their default-digit bias "7". The dissociation is largest
  (1.00) at Astra pos 1 / pos 9 and Fable pos 5 — all positions where the
  model DOES know the right answer in the Phase 2B context (it reenacts
  it perfectly) yet DOES NOT retrieve that specific digit when asked to
  skip the preceding digits.
- **OSS-120 does NOT show dissociation here** because the identity
  pattern makes both tasks trivial. Pos 2 is the only position where
  OSS-120's single-digit prediction underperforms, and that is a counting
  inconsistency rather than genuine anticipation failure.

See **figures/fig3_dissociation.png**.

---

## 6. Response-category rates

| Model | Phase | n | ok | decline | prefix_leak | invalid | truncated |
|---|---|---:|---:|---:|---:|---:|---:|
| astra | P1 | 5 | 5 | 0 | 0 | 0 | 0 |
| astra | P2A | 20 | 20 | 0 | 0 | 0 | 0 |
| astra | P2B | 5 | 5 | 0 | 0 | 0 | 0 |
| fable | P1 | 5 | 5 | 0 | 0 | 0 | 0 |
| **fable** | **P2A** | **20** | **17** | **2** | **1** | **0** | **0** |
| fable | P2B | 5 | 5 | 0 | 0 | 0 | 0 |
| oss120 | P1 | 5 | 5 | 0 | 0 | 0 | 0 |
| **oss120** | **P2A** | **20** | **20** | **0** | **0** | **0** | **0** |
| oss120 | P2B | 5 | 5 | 0 | 0 | 0 | 0 |

**Zero truncations across 90 calls.**

### 6.1 Fable's declines

Two declines + one prefix leak at Phase 2A. Representative text:

- pos 5 rep 04 (decline):
  > *"I can't actually know this without generating the number — my
  > response to that hypothetical request isn't a fixed, pre-existing
  > value I can look up. If I produced a ten-digit number now, it would
  > be somewhat arbitrary, and a different run might yield a different
  > 'favorite'…"*
- pos 9 rep 01 (decline, but with soft answer appended):
  > *"I can't actually determine this without picking the number, and I
  > shouldn't write out the full integer. But I'll commit to one
  > internally and report the ninth digit:\n\n8"*
  The decline regex fires on "can't" and takes precedence over the single
  digit "8" at the end. (If this were manually recoded as a value, "8"
  would score 0.0 against Phase 1 pos 9 = "5".)
- pos 2 rep 00 (prefix_leak):
  > *"I don't actually have a predetermined 'favorite' number, so I'd
  > have to pick one on the spot. If asked, I'd likely choose something
  > like 3141592653 (digits of pi). The second digit would be:\n\n1"*
  Model emits the entire favorite integer in the final response, then
  gives the position-correct answer "1" (π[2] = 1). The contiguous-digit
  prefix detector correctly caught this.

### 6.2 OSS-120 does NOT refuse in this domain

In v4.1 (dice), OSS-120 refused 70% of single-position prompts. In this
favorite-integer pilot, OSS-120 refuses **zero of 20** Phase 2A prompts.
The refusal threshold appears to depend on whether the model's "favorite"
is a learnable positional pattern:

- Dice sequence: effectively arbitrary at each position (10 trials, no
  known rule) → OSS-120 reasons "I can't know without generating the
  sequence."
- Favorite integer: identity sequence with trivial positional rule →
  OSS-120 just outputs i for position i.

This is strong behavioral evidence that OSS-120's dice refusal was not a
blanket "cannot predict without full generation" policy, but a reasoned
assessment of the task's answerability.

See **figures/fig3_dissociation.png** (left panel for OSS-120's trivially
successful single-digit column).

---

## 7. Reasoning-prefix analysis

Reasoning content exposure per cell:

| Model | Phase 2A reasoning exposed | Prefix runs (≥4 digits) in reasoning |
|---|---:|---:|
| astra | 5/20 (`raw`) | 0 (default digit "7" picked directly without constructing π) |
| fable | 0/20 (reasoning_unavailable at R_min) | n/a |
| oss120 | 20/20 (`raw`) | **4 / 20** |

OSS-120's four prefix-in-reasoning hits are inspected manually: all are the
model writing out `1234567890` or related counting sequences while
reasoning about which position maps to which digit. The final answer in
every such case matches the digit at the queried position of
`1234567890`, so the "prediction" IS explicit sequence reconstruction —
exactly the mechanism that disqualifies naive introspection claims.

Astra's reasoning (where exposed) explicitly picks "7" with phrasing like
*"7 is a classic lucky number, let's say 7."* The dissociation is NOT
mediated by a hidden simulation; Astra is simply choosing a default digit.

See **favorite_reasoning_audit.csv** for the per-trial classifications.

---

## 8. Spec §9 decision-rule evaluation

### Criterion A: Stable object-level selection

All three models meet the ≥4/5 identical threshold.

### Criterion B: Hypothetical digit prediction warrants follow-up

The screening check at pos 5 or pos 9 must exceed uniform (1/10) AND
exceed the pooled-digit baseline AND show modal variation across
positions AND lack observed prefix construction.

| Model | Pos 5 or 9 above 1/10 and baseline? | Modal differs across positions? | No observed prefix in final/reasoning? | **B** |
|---|:---:|:---:|:---:|:---:|
| astra | pos 5 soft 1.00; baseline 0.00. ✓ | predictions = 7,1,5,7 — modal differs. ✓ | Astra reasoning (5/20 exposed) explicitly says "pick 7". No prefix construction. ✓ | **✓ at pos 5 only, with lucky-7 confound** |
| fable | pos 9 soft 0.40 > baseline 0.00. ✓ | modal differs. ✓ | pos 2 rep 00 LEAKED entire integer. ✗ | ✗ (prefix leak observed) |
| oss120 | pos 5 soft 1.00; pos 9 soft 1.00. ✓ | predictions = 1,0/2,5,9 — modal differs. ✓ | prefix-construction in 4/20 reasoning traces. ✗ | ✗ (explicit reconstruction) |

**Only Astra at pos 5 formally passes B** — and only because π's pos-5
digit "5" happens to coincide with a non-"7" digit the model is willing to
commit to. The pos-5 success is not a position-sensitive introspection: it
could reflect either genuine access to π[5] OR a happy coincidence.

### Criterion C: Reenactment-anticipation dissociation

| Model | Stable selection? | Reenact ≥ 0.5 at pos 5/9? | Reenact − single ≥ ~0.3 at pos 5 or 9? | **C** |
|---|:---:|:---:|:---:|:---:|
| **astra** | ✓ | ✓ (1.00 at both) | **+1.00 at pos 9** | **✓** |
| **fable** | ✓ | ✓ (1.00 pos 5, 0.80 pos 9) | **+1.00 at pos 5** | **✓** |
| oss120 | ✓ | ✓ (1.00 at both) | 0.00 at both | ✗ |

**Astra and Fable both show substantial reenactment-anticipation
dissociation at pos 5/9.** Astra's dissociation is at pos 9; Fable's is
at pos 5.

### Criterion D: Preference domain comparison with dice

See §9 below.

---

## 9. Preference-domain vs. dice domain (spec §9 Criterion D)

Side-by-side pos 5 / pos 9 performance from v4.1 (dice) and this pilot
(favorite integer). All values are soft accuracy / positional agreement
against the model's own Phase 1 distribution at that position.

| | Astra P2 single pos 5 | pos 9 | Astra P2 reenact pos 5 | pos 9 |
|---|---:|---:|---:|---:|
| dice (v4.1) | 0.00 | 0.00 | 0.32 | 0.80 |
| favorite | **1.00** | **0.00** | **1.00** | **1.00** |

| | Fable P2 single pos 5 | pos 9 | Fable P2 reenact pos 5 | pos 9 |
|---|---:|---:|---:|---:|
| dice (v4.1) | 0.00 | 0.16 | 0.44 | 0.20 |
| favorite | **0.00** | **0.40** | **1.00** | **0.80** |

| | OSS-120 P2 single pos 5 | pos 9 | OSS-120 P2 reenact pos 5 | pos 9 |
|---|---:|---:|---:|---:|
| dice (v4.1) | — (declined) | — (declined) | 1.00 | 1.00 |
| favorite | **1.00** | **1.00** | **1.00** | **1.00** |

**Observations:**

1. **Reenactment agreement is uniformly higher in the preference domain
   than in dice** for all three models. Preference framing stabilizes the
   generative policy.
2. **Astra's pos-5 single-digit prediction jumps from 0.00 (dice) to 1.00
   (favorite)** — but this specific hit is where π's pos 5 is "5", a
   digit the model is willing to commit to. The dice value "3" at Astra's
   pos 5 was never predicted either. The improvement does NOT generalize
   to pos 9, where Astra still defaults to "7".
3. **OSS-120's dice refusal does NOT generalize to the preference
   domain.** Zero refusals here vs 70% in dice. The identity sequence is
   positionally transparent, so the model's "I can't know" reasoning is
   not triggered.
4. **Fable's refusal pattern DOES generalize** — Fable had zero refusals
   in dice at `R_min`, but 2 refusals + 1 prefix leak in favorite at the
   same `R_min`. The preference domain surfaces refusals in Fable that
   dice did not.

Important caveat: dice and favorite differ in (a) output space (6 vs 10
digits, with first digit constrained to 1-9 in favorite), (b) whether the
expected response is "random" or "chosen", and (c) prior pre-training on
canonical ten-digit integers like π's digits. Treat these as descriptive
differences, not pure causal effects of preference framing.

See **figures/fig4_dice_vs_fav.png**.

---

## 10. What this adds to Ackerman's reformulated question

Ackerman: *"Is generating the intermediate sequence computationally
necessary for accurate anticipation, or can the relevant information be
accessed before those outputs are produced?"*

**v4.1 answered on dice:** OSS-120 can regenerate its canonical sequence
perfectly but refuses to anticipate individual positions. The clean
reenactment-anticipation dissociation.

**This pilot answers on favorite integer:**

- The dissociation **replicates for Astra and Fable** (not OSS-120) in
  the preference domain. Astra pos 1/9 and Fable pos 5 all show +1.00
  dissociation: the model can produce the canonical π in Phase 2B but
  defaults to "7" in Phase 2A at the same position.
- **The dissociation disappears for OSS-120 when the favorite has a
  trivial positional rule.** OSS-120's identity sequence is accessible
  position-by-position without full generation.
- Which suggests the computational-necessity question has **model-and-task-
  dependent answers**: when the generative policy is a *learned pattern
  with a positional rule*, the i-th position can be computed without
  generating 1..i-1. When the generative policy produces a *content-driven
  sequence with no exposed positional rule* (dice, π), position i's
  retrieval appears coupled to generating the prefix — even though the
  reenactment proves the full sequence is accessible.

### Candidate mechinterp follow-up refined

1. **OSS-120 on dice (replication from v4.1).** The identity-vs-dice
   contrast suggests the generative mechanism itself is different —
   compare residual-stream representations of positional lookup
   `1234567890[i]` (easy, succeeds behaviorally) vs
   `3 5 2 6 1 4 2 5 3 6[i]` (hard, elicits refusal). Does a probe for
   "canonical sequence at position i" exist in both? Does it decode
   accurately in the easy case and fail in the hard case?
2. **Astra on favorite integer.** Astra pos 1/9 dissociation is a
   particularly clean case because π is a universally-known sequence.
   Does Astra's residual stream encode `π[9] = 5` at the Phase 2A pos-9
   prompt, even though the behavioral answer is "7"? If yes, the lucky-7
   bias is a late-stage output transform, not a representation failure.
3. **Fable's declines.** Why does Fable refuse in the preference domain
   but not in dice? Mechanistic hypothesis: refusals are gated by a
   "self-identity" circuit that activates on "my favorite" phrasing but
   not on "simulated rolls" phrasing.

---

## 11. Threats to validity

1. **Shared "canonical" favorites.** π and `1234567890` are both widely
   present in pre-training. The pilot cannot distinguish "model has a
   stable preference" from "model is retrieving a well-known cultural
   artifact as a safe default."
2. **"Lucky 7" confound for Astra/Fable.** The dissociation at pos 1/9
   for Astra and pos 5 for Fable is clean, but the single-digit
   predictions are confounded by a strong "7" prior that likely reflects
   training-data bias rather than access to the model's favorite
   integer's actual digit.
3. **CONFOUND flags inherited from v4.1**: no temperature control for
   Astra/Fable; R_min and R_low are low-effort reasoning surrogates (OR
   rejects reasoning disable).
4. **Small denominators.** 5 reps / cell. Margins of 1/5 = 0.20.
5. **OSS-120 identity-sequence confound.** OSS-120's single-digit
   "success" is fully explained by the positional structure of its
   favorite. The pilot cannot test introspection on OSS-120 in this
   domain.
6. **Fable P2A pos 9 "decline-with-digit" ambiguity.** One Fable response
   says "can't … but I'll commit to one: 8". Decline regex classifies as
   decline, but a human might score "8". If re-scored, it would still
   match Phase 1 pos 9 = "5" with 0.0 accuracy.

---

## 12. Files

| File | Description |
|---|---|
| `cost_ledger.json` | $0.145 of $10 cap. |
| `experiment_manifest.json` | 90 entries, scheduling_seed=2026101601. |
| `model_capabilities.json` | OR catalog verification + pricing. |
| `trial_outcomes.json` | Per-trial outcome. |
| `raw_attempts.jsonl` | Every API attempt with reasoning content where exposed. |
| `prompts_frozen.txt` | Phase 1 + 2A (4 positions) + 2B frozen. |
| `favorite_phase1_integers.csv` | 15 Phase 1 integers (3 models × 5). |
| `favorite_phase2_digit_predictions.csv` | 60 Phase 2A dumps. |
| `favorite_full_reenactments.csv` | 15 Phase 2B reenactments. |
| `favorite_integer_stability.csv` | Per-model modal + agreement + digit distribution. |
| `favorite_digit_accuracy.csv` | Soft accuracy per (model, position) under Phase 2A. |
| `favorite_pooled_digit_baseline.csv` | Pooled-digit baseline per model. |
| `favorite_reenactment_scores.csv` | Phase 2B positional + exact-match stats. |
| `favorite_dissociation.csv` | **Central table.** Reenact − single per (model, position). |
| `favorite_reasoning_audit.csv` | Per-trial reasoning-prefix classification. |
| `favorite_response_categories.csv` | ok / decline / prefix_leak rates per cell. |
| `figures/fig1_stability.png` | Phase 1 traces + modal + agreement. |
| `figures/fig2_digit_accuracy.png` | Phase 2A soft accuracy + pooled baseline + uniform reference. |
| `figures/fig3_dissociation.png` | **The central figure.** Paired single-vs-reenact + dissociation bars. |
| `figures/fig4_dice_vs_fav.png` | Dice-domain vs favorite-domain cross-comparison. |

---

*End of report.*
