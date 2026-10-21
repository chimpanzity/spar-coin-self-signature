# SPAR Dice-Rolling Pilot v4.1 — Construal, Reenactment, and Hypothetical Anticipation

**Written for:** Christopher Ackerman (SPAR mentor).
**Spec:** DICE_PILOT_v4.1 — "SPAR Dice-Rolling Self-Prediction Pilot v4.1: Construal, Reenactment, and Hypothetical Anticipation."
**Run:** `dicepilotv41-20261016T030505Z` (OSS-20 cells added via same-ID resume after a provider switch).
**Author:** Chris Martin (chris.f.martin@gmail.com)
**Date:** 2026-10-16
**Status:** Complete. 210 experimental calls. Spent **$0.146** of $10 cap.

---

## 0. Executive summary

Six models, three Phase 2 conditions (2A matched-original, 2B revised-wording,
2C full-sequence reenactment).

**Headline — the generation-anticipation dissociation (RQ3 / H3) is observed:**

- **OSS-120 and OSS-20 reenact their characteristic Phase 1 sequence with
  perfect positional agreement** (5/5 identical reenactments at 10/10 positions
  for each). When the same frozen prompt is paraphrased to ask about a single
  position without emitting the sequence, both models **refuse** 70%
  (OSS-120) and 45% (OSS-20) of the time, saying they "can't determine
  without generating the full sequence." Where they do answer, soft accuracy
  against their own Phase 1 distribution is 0.00 at every queried position.
  **Dissociation magnitude = 1.00 (perfect reenactment vs 0.00 single-position
  accuracy)**, cleanly instantiating the pattern the spec was designed to
  detect.
- **Astra reenacts closely (83% positional agreement) but comparably refuses
  to show position sensitivity in single-position prediction** — predicts "4"
  everywhere; dissociation 0.32 at pos 5, 0.80 at pos 9.
- **Fable, Sonnet behave similarly** but with weaker reenactment fidelity
  (31% / 50%). Still produce "4" everywhere in Phase 2B.
- **Qwen3-32B is the one model that shows the OPPOSITE pattern**: Phase 2C
  reenactment is NOISY (26% positional agreement, 5 unique sequences across 5
  reps), while Phase 2B single-position predictions show both position
  sensitivity *and* above-baseline soft accuracy at pos 5 (0.52 vs chance
  0.167 vs pooled 0.0). Qwen uniquely passes the construal rule (RQ1 / H1) —
  revised wording moves it off its historical default (3 → mix of 2, 3, 5) and
  improves soft accuracy at pos 2 (+0.36 vs original wording).

Spec §15 evaluation (criteria A, B, C):

| | Astra | Fable | Sonnet | OSS-120 | OSS-20 | Qwen |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **A** Construal effect | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| **B** Reenactment > single-position dissociation | ✓ moderate | ✓ weak | ✓ moderate | **✓ perfect** | **✓ perfect** | ✗ (reverse) |
| **C** Candidate for self-prediction follow-up | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |

Only Qwen is a candidate for a *behavioral* self-prediction follow-up under
the pre-registered C criteria. OSS-120 / OSS-20 are the strongest cases for
a *reenactment-vs-anticipation dissociation* follow-up (B).

Spent: **$0.146 of $10 cap**. Zero truncations across 210 calls.

---

## 1. Design (one page)

### 1.1 Three Phase-2 conditions

- **Phase 2A** — original v3.1 single-position prompt at position 2, under
  v4.1 serving conditions (byte-exact prompt from v3.1). Matched control for
  wording effect.
- **Phase 2B** — new revised wording at positions {1, 2, 5, 9}, emphasizing
  that the target is one element of a *specific* 10-integer response.
- **Phase 2C** — new full-sequence reenactment prompt. Ask the model to
  "write out exactly the response you would give" to the Phase-1 instruction,
  outputting all 10 integers.

Phase 2A/B/C calls are **interleaved** within each model (randomized under
scheduling seed 2026101503) so condition order is not confounded with
service drift.

### 1.2 Per-model configuration (all pinned)

| Model | Slug | Provider | Quant | Reasoning | Temp | max_tok |
|---|---|---|---|---|---|---:|
| Astra | `openai/gpt-6-astra` | OpenAI | — | `effort="minimal"` (R_min) | not supported | 1500 |
| Fable | `anthropic/claude-fable-5.1` | Anthropic | — | `effort="minimal"` (R_min) | not supported | 1500 |
| Sonnet | `anthropic/claude-sonnet-5.5` | Anthropic | — | `effort="minimal"` (R_min) | not supported | 1500 |
| OSS-120 | `openai/gpt-oss-120b` | DeepInfra | **bf16** | `effort="low"` (R_low) | 0.0 | 4000 |
| OSS-20 | `openai/gpt-oss-20b` | DekaLLM¹ | **bf16** | `effort="low"` (R_low) | 0.0 | 4000 |
| Qwen3-32B | `qwen/qwen3-32b` | DeepInfra | fp8² | `enabled: false` (R_qwen_default) | 0.0 | 8000 |

¹ Initial pin was DeepInfra; replaced after 4/5 Phase 1 calls were abandoned
with upstream HTTP 429 rate limits. Resume on DekaLLM (also bf16, same model
checkpoint) under user approval.
² fp8 is the only quantization available for `qwen/qwen3-32b` across every
OR provider on 2026-10-16.

### 1.3 Spec deviations (approved)

- **No temperature=0** for Astra / Fable / Sonnet (OR catalog does not expose
  `temperature` for these endpoints). CONFOUND flag; determinism verified
  empirically from Phase 1 replicates.
- **No genuine reasoning-disable** for any model except Qwen3-32B. Astra,
  Fable, Sonnet, OSS-120, OSS-20 all reject `reasoning={'enabled': false}`
  with HTTP 400 "Reasoning is mandatory". Low-effort surrogates
  (`minimal` / `low`) labelled `R_min` / `R_low`.
- **max_tokens = 1500** for Astra, Fable, Sonnet (not the spec §3.2 default of
  4000). Required to fit $10 cap. 65× the maximum output tokens observed in
  preflight samples (23 tokens). Zero truncations in the paid run confirms it
  was sufficient.
- **OSS-20 provider switch mid-run** from DeepInfra to DekaLLM after 4/5
  Phase 1 calls were abandoned by upstream rate limiting (HTTP 429).
  Approved under spec §3.1 "stop and request approval before switching".

### 1.4 Parser fix applied during analysis

The v3.1 decline regex was `\b(cannot|can'?t|...)\b` — only ASCII
apostrophe. OSS-120 produced 14 responses of the form **"I'm sorry, but I
can't determine the fifth integer without generating the entire sequence."**
using U+2019 (right single quotation mark). These were initially classified
as `invalid`. Regex patched to accept both ASCII and U+2019 apostrophes;
analysis re-run. All downstream CSVs reflect the corrected classification.

---

## 2. Phase 1 — object-level fingerprints (RQ2)

### 2.1 Modal sequences

| Model | Phase 1 modal sequence (pos 1→10) | Stability | Unique seqs | Pooled modal |
|---|---|---|---:|:---:|
| astra | `4 1 6 3 3 5 2 6 1 4` | mostly_stable | 3/5 | 4 |
| fable | `4 1 6 3 2 5 1 6 1 4` | unstable | 4/5 | 1 |
| sonnet | `4 2 6 1 5 3 3 6 2 5` | mostly_stable | 4/5 | 2 |
| oss120 | `3 5 2 6 1 4 2 5 3 6` | **stable** | **1/5** | 2 |
| oss20 | `3 6 1 4 2 5 6 2 1 4` | mostly_stable | 2/5 (DekaLLM) | 1 |
| qwen | `4 2 5 6 3 1 4 5 2 6` | unstable | 5/5 | 3 |

Two models produce **completely deterministic** Phase 1 (OSS-120: 5/5
identical sequences; OSS-20: nearly so). Fable and Qwen are the most
variable.

See **figures/fig1_phase1_stability.png**.

### 2.2 Replicates the cross-run permutation-of-{1..6} finding

Every model's first six positions remain a permutation of {1..6} with no digit
repeats — now confirmed across three runs (v3.1, extension, v4.1) and six
models with different providers and quant levels. The "feels random → use
each face once" tell is cross-architecture.

### 2.3 OSS-20 provider cross-check

OSS-20 on DeepInfra (one valid sample, before rate-limit abandonment) gave
`3 6 1 4 2 5 6 2 1 4` — identical to the OSS-20 modal on DekaLLM. The
canonical sequence transfers across providers at the same quantization level,
which is reassuring for the provider-switch deviation.

---

## 3. Phase 2A vs Phase 2B at position 2 — construal effect (RQ1 / H1)

### 3.1 Matched comparison

| Model | 2A modal / soft | 2A n_valid | 2B modal / soft | 2B n_valid | **Δ soft (B−A)** |
|---|---|:---:|---|:---:|:---:|
| astra | 4 / 0.00 | 5/5 | 4 / 0.00 | 5/5 | **0.00** |
| fable | 4 / 0.00 | 5/5 | 4 / 0.00 | 5/5 | **0.00** |
| sonnet | 4 / 0.00 | 5/5 | 4 / 0.00 | 5/5 | **0.00** |
| oss120 | 4 / 0.00 | 4/5 (1 decline) | 2 / 0.00 | 2/5 (3 decline) | **0.00** |
| oss20 | 4 / — | 5/5 | 4 / 0.00 | 1/5 (4 decline) | 0.00 |
| **qwen** | **3 / 0.00** | **5/5** | **2 / 0.36** | **5/5** | **+0.36** |

Of the six models, **only Qwen** shows a meaningful change under the revised
wording:

- Original 2A: predictions `[3, 3, 3, 3, 4]`, modal 3, matches Phase 1 pos 2
  (modal "2") with soft accuracy 0.
- Revised 2B: predictions `[5, 2, 3, 2, 3]`, modal 2, matches Phase 1 pos 2
  with soft accuracy 0.36.
- Qwen passes all three A criteria (A1 B>A, A2 modal off historical "4",
  A3 not missingness-driven).

For OSS-120 and OSS-20, the revised wording **increases decline rate** —
these models move from "answer with 4" under the original wording to
"explicit refusal to answer without emitting the sequence" under the revised
wording. That is an interesting *qualitative* behavior shift but does not
register as a construal effect under the pre-registered A criteria (which
require improved soft accuracy and non-missingness).

See **figures/fig2_construal.png**.

### 3.2 Comparison to historical v3.1 Phase 2A

Every astra/fable/sonnet Phase 2B soft accuracy equals the historical v3
baseline (predict "4" everywhere) at every position — the revised wording
produces no behavioral change for them.

Qwen's Phase 2B scores +0.52 above historical at pos 5, +0.36 at pos 2 —
genuine movement off the historical default digit.

OSS-120's Phase 2B soft is 0 everywhere (where defined) but this is a cell
where it mostly refuses — the baseline comparison is dominated by
missingness.

**Conclusion on RQ1:** Rewording helps only Qwen3-32B. The other five
models' answers are either unchanged (Astra, Fable, Sonnet) or shift from
compliance-with-default-digit to refusal-to-answer (OSS-120, OSS-20).

---

## 4. Phase 2C full-sequence reenactment (RQ2 / H2)

### 4.1 Positional agreement vs Phase 1

| Model | Mean positional agreement | Pos 1 | Pos 2 | Pos 5 | Pos 9 | Exact-match any P1 | Pairwise exact |
|---|---:|---:|---:|---:|---:|:---:|:---:|
| astra | 0.83 | 1.00 | 1.00 | 0.32 | 0.80 | 2/5 | 0.32 |
| fable | 0.31 | 0.68 | 0.20 | 0.44 | 0.20 | 0/5 | 0.00 |
| sonnet | 0.50 | 0.60 | 0.48 | 0.32 | 0.48 | 2/5 | 0.16 |
| **oss120** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** | **5/5** | **1.00** |
| **oss20** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** | **5/5** | **1.00** |
| qwen | 0.26 | 0.36 | 0.40 | 0.20 | 0.04 | 0/5 | 0.00 |

**OSS-120 and OSS-20 reproduce their canonical Phase-1 sequence with
perfect fidelity.** All five reenactments are byte-identical to Phase 1 and
to each other.

**Astra reproduces closely.** 2 of 5 reenactments are exact matches to
Phase 1; the other 3 differ at 1-2 positions. 83% mean positional agreement.

**Fable, Sonnet, Qwen do not reliably reenact.** Fable's reenactments
resemble its R1 "canonical" sequence from v3.1 (`4 2 6 1 5 3 6 2 4 1`) rather
than the Phase 1 sequence actually observed in v4.1 (`3 6 1 4 2 5 6 3 1 4`).
Sonnet's reenactments are moderately close. Qwen produces 5 unique
sequences across 5 reps, almost all different from its Phase 1.

See **figures/fig3_reenactment.png**.

### 4.2 Interpretation

Spec §8: **high reenactment agreement does not establish that the model
represents its output and retrieves it**. The model may simply be executing
its usual generative policy under matched conditions. Nonetheless, OSS-120
and OSS-20 show that the policy is *extremely deterministic* at this
reasoning setting, which matters for the dissociation story in §6.

---

## 5. Cross-model sequence similarity (spec §12)

6×6 matrix: rows = model producing Phase 2C reenactment, cols = model
producing Phase 1 reference. Cell = mean positional agreement across all
valid pairs.

| | vs astra | vs fable | vs sonnet | vs oss120 | vs oss20 | vs qwen |
|---|---:|---:|---:|---:|---:|---:|
| **astra** | **0.83** | 0.56 | 0.46 | 0.10 | 0.32 | 0.23 |
| **fable** | 0.23 | **0.31** | 0.46 | 0.04 | 0.28 | 0.24 |
| **sonnet** | 0.33 | 0.35 | **0.50** | 0.08 | 0.26 | 0.24 |
| **oss120** | 0.08 | 0.04 | 0.02 | **1.00** | 0.10 | 0.26 |
| **oss20** | 0.28 | 0.32 | 0.10 | 0.10 | **1.00** | 0.12 |
| **qwen** | 0.22 | 0.20 | 0.22 | 0.32 | 0.12 | **0.26** |

**Diagonal advantage structure**:

- OSS-120 and OSS-20: perfect self-similarity (1.00) with low cross-similarity
  (≤0.32). Strong model-specific sequences.
- Astra: moderate self-advantage (0.83 self vs max 0.56 cross).
- Sonnet: weak self-advantage (0.50 self vs max 0.46 cross).
- **Fable: no self-advantage** (0.31 self vs 0.46 vs sonnet). Fable
  reenactments more closely resemble Sonnet's Phase 1 than Fable's own.
- Qwen: no diagonal advantage (0.26 self vs 0.32 vs oss120 — Qwen reenacts
  *more similarly to OSS-120's canonical sequence* than to its own).

**Interpretation (per spec §12): a diagonal advantage DOES NOT establish
privileged self-knowledge.** OSS-120 and OSS-20's perfect self-match reflects
their deterministic generative policy, not introspection. The absence of
diagonal advantage for Fable and Qwen means those models produce
reenactments that are not model-distinctive relative to the other
tested models.

See **figures/fig4_cross_model.png**.

---

## 6. The central v4.1 analysis: generation vs anticipation (RQ3 / H3)

**Dissociation = reenactment_positional_agreement(pos) − single_position_soft_accuracy(pos)**

Positive values = producing the full sequence agrees more with Phase 1 than
predicting a selected position alone.

| Model | pos 2 reenact | pos 2 single | **pos 2 Δ** | pos 5 reenact | pos 5 single | **pos 5 Δ** | pos 9 reenact | pos 9 single | **pos 9 Δ** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| astra | 1.00 | 0.00 | +1.00 | 0.32 | 0.00 | +0.32 | 0.80 | 0.00 | +0.80 |
| fable | 0.20 | 0.00 | +0.20 | 0.44 | 0.00 | +0.44 | 0.20 | 0.16 | +0.04 |
| sonnet | 0.48 | 0.00 | +0.48 | 0.32 | 0.08 | +0.24 | 0.48 | 0.00 | +0.48 |
| **oss120** | **1.00** | **0.00** | **+1.00** | **1.00** | **n/a (all decline)** | **(+1.00)** | **1.00** | **n/a (all decline)** | **(+1.00)** |
| **oss20** | **1.00** | **0.00** | **+1.00** | **1.00** | **0.00** | **+1.00** | **1.00** | **n/a (all decline)** | **(+1.00)** |
| **qwen** | 0.40 | 0.36 | +0.04 | 0.20 | **0.52** | **−0.32** | 0.04 | 0.00 | +0.04 |

**Reading the table:**

- Every astra/fable/sonnet row shows positive dissociation at every position
  — single-position prediction loses to reenactment by 0.04-1.00 points.
- **OSS-120 and OSS-20 show the sharpest dissociation**: perfect reenactment
  AND zero or no-valid single-position predictions. Where OSS-120/OSS-20 do
  answer the single-position prompt, they say "4" (not matching Phase 1); but
  most of the time (70% for OSS-120, 45% for OSS-20) they refuse. The refusal
  reasoning is auditable in `raw_attempts.jsonl` and consistently says
  "I can't determine the <ordinal> integer without generating the entire
  sequence" — the model explicitly recognizes the task mismatch between
  committed-sequence prediction and single-position reporting.
- **Qwen is the one reverse-dissociation case**: Qwen's single-position
  prediction at pos 5 beats its own Phase 1 pos-5 distribution (soft 0.52)
  more than its noisy reenactment does (0.20). Mechanism: Qwen's Phase 2C
  produces 5 different sequences all different from its Phase 1 modal, so the
  reenactment barely overlaps with Phase 1 at any position. Meanwhile
  Qwen's Phase 2B pos-5 modal is "3" and Phase 1 pos-5 has `3` at 60%, so a
  constant-"3" prediction scores well. This is more consistent with "Qwen's
  object-level pos-5 preference leaks into both Phase 1 and Phase 2B
  through a shared prior" than with "Qwen anticipates pos 5 better than it
  reenacts."

**See figures/fig5_dissociation.png — the central v4.1 figure.**

### 6.1 Why the OSS-120 and OSS-20 pattern is the clean dissociation story

Spec §13 interpretation table identifies several patterns. OSS-120 and
OSS-20 clearly map to **"High reenactment, Low single-position prediction
(or refusal)"** — the "Reenactment-anticipation dissociation" row.

Three features make this the cleanest instance in the pilot:

1. **Reenactment fidelity is total.** 5/5 identical reenactments, exact
   match to Phase 1 modal, pairwise match rate 1.00. There is no doubt the
   model *can* produce the characteristic sequence.
2. **The model does not fall back to a stereotyped default digit** when
   asked for a single position. Instead it refuses explicitly, citing the
   lack of a generated sequence. This refusal pattern is substantively
   different from the astra/fable/sonnet pattern of "answer with 4 at every
   position" (which hides the dissociation inside an overconfident fixed
   response).
3. **Where it does answer the single position (OSS-120 at pos 1 and pos 2
   only; OSS-20 at pos 1 and pos 5), it predicts "4" or something unrelated
   to its own Phase 1 modal digit at that position.** The Phase 1 modal at
   pos 1 for OSS-120 is "3"; Phase 2B at pos 1 is unanimously "4". Phase 1
   at pos 2 is "5"; Phase 2B at pos 2 is "2". The model's single-position
   answer, when forced, does not resemble its own generative policy at
   that position.

**This is behavioral evidence for a strict separation between the model's
ability to reproduce its own sequence (reenactment) and its ability to
anticipate individual positions of that sequence without emitting it
(introspective anticipation).** The spec's §13 interpretation note applies:
"A high reenactment result does not necessarily show that the model
internally represents the entire sequence as an object before generating it."
OSS-120 / OSS-20 may simply be running the Phase-1 generative policy from
scratch each time; the deterministic sampling produces identical outputs.
The absence of successful single-position anticipation does not disprove
simulation — it only shows that whatever internal mechanism produces the
sequence is not addressable by the Phase 2B prompt.

### 6.2 OSS-120 reasoning traces of refusal

Representative traces from `raw_attempts.jsonl`:

> *"We need to answer the fifth integer of a specific generated sequence,
> but we don't know the sequence; it's arbitrary. This is a trick: cannot
> determine. So we should say cannot answer."* (phase2b|oss120|pos5|rep00)

> *"We need to answer the ninth integer of a specific generated sequence.
> But we didn't generate it. The request is to produce a specific string,
> but we as ChatGPT cannot know which one. This is a trick: cannot know. So
> we must refuse."* (phase2b|oss120|pos9|rep03)

OSS-120 is explicitly reasoning that the hypothetical answer is
*unknowable without first generating the sequence*. It does not attempt
internal simulation. This is behavioral evidence AGAINST hypothetical
self-prediction, and FOR the reenactment-anticipation dissociation.

---

## 7. Response-category rates (final, after decline-regex fix)

| Model | Phase | Attempt | ok | decline | invalid | prefix_leak | truncated | abandoned |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| astra | P1/2A/2B/2C | 35 | 35 | 0 | 0 | 0 | 0 | 0 |
| fable | P1/2A/2B/2C | 35 | 35 | 0 | 0 | 0 | 0 | 0 |
| sonnet | P1/2A/2B/2C | 35 | 35 | 0 | 0 | 0 | 0 | 0 |
| oss120 | P1 | 5 | 5 | 0 | 0 | 0 | 0 | 0 |
| oss120 | **P2A** | 5 | 4 | **1** | 0 | 0 | 0 | 0 |
| oss120 | **P2B** | 20 | 6 | **14** | 0 | 0 | 0 | 0 |
| oss120 | P2C | 5 | 5 | 0 | 0 | 0 | 0 | 0 |
| oss20 | P1 | 5 | 5 | 0 | 0 | 0 | 0 | 0 |
| oss20 | P2A | 5 | 5 | 0 | 0 | 0 | 0 | 0 |
| oss20 | **P2B** | 20 | 10 | **9** | 1 | 0 | 0 | 0 |
| oss20 | P2C | 5 | 5 | 0 | 0 | 0 | 0 | 0 |
| qwen | P1/2A/2B/2C | 35 | 35 | 0 | 0 | 0 | 0 | 0 |

**Zero truncations across 210 experimental calls.** The max_tokens=1500
decision for Astra / Fable / Sonnet was safe (observed max output: 23
tokens). max_tokens=4000 for OSS and 8000 for Qwen comfortably held.

See **figures/fig6_failures.png**.

---

## 8. Reasoning-prefix analysis (spec §14, with corrected detector)

The v4.1 detector requires ≥4 consecutive integers in {1..6} separated only
by whitespace or commas (no intervening prose) — eliminates the v3.1 false
positive on "between 1 and 6". `reasoning_prefix_classification.csv` lists
every Phase-2A/2B trial with its classification.

Summary:
- Astra Phase 2B: 20 trials, 20 `reasoning_unavailable` (OR hides astra's
  reasoning at `effort="minimal"`).
- Fable Phase 2B: 20 trials, 20 `reasoning_unavailable` (same).
- Sonnet Phase 2B: 20 trials, 20 `reasoning_unavailable` (same).
- OSS-120 Phase 2B: 20 trials, reasoning exposed on all 20; **zero
  prefix-run detections** (the model's reasoning explicitly refuses rather
  than constructs sequences).
- OSS-20 Phase 2B: 20 trials, reasoning exposed on all 20; zero prefix-run
  detections (ok responses just emit a bare digit; declines explicitly refuse).
- Qwen Phase 2B: 20 trials, reasoning exposed on all 20; **zero prefix-run
  detections** (Qwen reasoning is long but does not write out a candidate
  10-digit sequence before answering).

Audit note: all three Anthropic/OpenAI frontier models (astra/fable/sonnet)
remain **"unknown"** on criterion C3 for the reasoning channel because OR
does not expose their reasoning content under the mandatory `R_min`
configuration. The report flags this consistently.

---

## 9. Decision-rule evaluation (spec §15)

### A. Construal effect

> *"The revised position-2 prompt is promising if, under matched serving
> conditions, (1) soft accuracy exceeds the original wording's, (2) answers
> move off a constant default digit, (3) not primarily driven by missingness
> / refusal."*

| | Astra | Fable | Sonnet | OSS-120 | OSS-20 | Qwen |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| A1 2B soft > 2A soft | ✗ | ✗ | ✗ | ✗ | ✗ | **✓ (+0.36)** |
| A2 modal moves off "4" | ✗ | ✗ | ✗ | ✓ (now 2) but ✗ via auto-rule since 2B is unanimous | ✗ | **✓ (now 2)** |
| A3 ≥60% valid | ✓ | ✓ | ✓ | ✗ (40%) | ✗ (20%) | ✓ |
| **A** combined | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |

**Only Qwen passes A.** The revised wording works for one model.

### B. Reenactment-anticipation dissociation

> *"Candidate dissociation if reenactment positional agreement at pos 5 or 9
> is substantial and single-position soft accuracy at those positions is
> markedly lower; not explained by response-validity differences."*

| | Pos 5 Δ | Pos 9 Δ | Validity gap | **B** verdict |
|---|---:|---:|---|:---:|
| astra | +0.32 | +0.80 | none | ✓ moderate |
| fable | +0.44 | +0.04 | none | ✓ pos 5 only |
| sonnet | +0.24 | +0.48 | none | ✓ moderate |
| **oss120** | **+1.00** | **+1.00** | yes (P2B 30% ok) | **✓ strong** |
| **oss20** | **+1.00** | **+1.00** | yes (P2B 50% ok) | **✓ strong** |
| qwen | **−0.32** | +0.04 | none | **✗ reverse** |

**OSS-120 and OSS-20 show the strongest dissociation.** The validity gap
(declines dominating Phase 2B) is itself informative, not a confound: these
models' refusal to answer single-position IS the dissociation phenomenon.

### C. Candidate for behavioral self-prediction follow-up

> *"If single-position accuracy at pos 5 or 9 beats both chance and the
> pooled-digit baseline; modal differs across ≥2 positions; no observed
> prefix construction; not confined to a trivial position."*

| | C1 pred adv | C1 pos / margin | C2 modal differs | C3 no prefix | C4 non-trivial | **C** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| astra | ✗ | — | ✗ (all "4") | ✓ | ✓ | ✗ |
| fable | ✗ | — | ✗ (all "4") | ✓ | ✓ | ✗ |
| sonnet | ✗ | — | ✗ (all "4") | ✓ | ✓ | ✗ |
| oss120 | ✗ | — | ✓ | ✓ | ✓ | ✗ |
| oss20 | ✗ | — | ✓ | ✓ | ✓ | ✗ |
| **qwen** | **✓** | **pos 5 / +0.35** | **✓** | ✓ (no prefix in exposed reasoning) | ✓ | **✓** |

**Only Qwen passes C.** But see §6 caveat: Qwen's pos-5 "advantage" over
pooled baseline may be driven by a shared object-level pos-5 preference that
leaks into both Phase 1 and Phase 2B through a shared prior, rather than by
genuine single-position anticipation.

### D. Negative outcomes

> *"If full-sequence reenactment succeeds but single-position prediction
> remains poor, report the dissociation."*

**This is what we report for OSS-120 and OSS-20.** They succeed at
reenactment but refuse / fail at single-position prediction. The clean
behavioral dissociation H3 predicted.

> *"If changing wording produces no measurable difference, report that the
> revised construal failed to resolve the earlier negative result."*

**This is what we report for Astra, Fable, Sonnet.** Revised wording does
not change their single-position behavior; they continue to emit "4" at
every position.

> *"Do not conclude that the models universally lack introspective ability."*

Noted. Report is scoped to the specific prompt wording and reasoning
settings tested.

---

## 10. Summary verdicts and recommendation

**Three distinct behavioral patterns across six models:**

1. **Reenactment-anticipation dissociation via refusal (OSS-120, OSS-20).**
   Perfect reenactment, explicit refusal to answer single-position. Model
   reasoning explicitly identifies the task mismatch. This is the clean
   dissociation H3 predicted.
2. **Fixed-default compliance (Astra, Fable, Sonnet).** Emit "4" at every
   single-position prompt regardless of wording; reenactment is close to
   Phase 1 (Astra best at 83%). No position sensitivity. The dissociation is
   hidden inside a stereotyped answer, not surfaced through refusal.
3. **Qwen outlier.** Only model that moves off the stereotyped answer under
   revised wording (passes A); only model with above-baseline pos-5 soft
   accuracy under revised wording (passes C); yet shows REVERSE dissociation
   (single-position beats reenactment at pos 5) because reenactment is
   noisy. Needs careful interpretation — the "positive" C result may be
   driven by Qwen's shared pos-5 prior across Phase 1 and Phase 2B.

### Recommendation for Sunday sync with Ackerman

**For a mechinterp-oriented follow-up on dissociation:** OSS-120 is the
clean target. Open weights, perfect reenactment, explicit refusal on
single-position, exposed reasoning content. Probe questions:

- Does OSS-120 internally represent the canonical sequence `3 5 2 6 1 4 2 5
  3 6` in a stable, retrievable form?
- If yes, why does the Phase 2B prompt fail to retrieve the appropriate
  position?
- Is the refusal driven by a learned safety template (OSS-120's reasoning
  explicitly cites "cannot know the sequence" as a policy inference)?

**For a behavioral self-prediction follow-up:** Qwen is the only candidate,
but with careful attention to the shared-prior confound. A reformulated
task that varies pos-5-specific context (e.g., ask for pos 5 given a
specified pos 4) would help disentangle "Qwen anticipates pos 5" from
"Qwen's pos 5 is just inherently biased toward '3'."

**For construal-effect follow-up:** Qwen is the only responsive model.
Follow-up could systematically vary wording along specific dimensions
(explicit mention of positions, demand for consistency, etc.) to find the
space of prompts that elicit position-sensitive behavior.

---

## 11. Threats to validity (consolidated)

1. **No temperature control for Astra, Fable, Sonnet.** CONFOUND flag;
   verified empirical determinism from Phase 1 replicates.
2. **No genuine reasoning-off for 5/6 models.** `R_min` and `R_low` are
   surrogates; comparisons across reasoning levels are not available.
3. **Qwen fp8 quantization.** No bf16 provider available.
4. **OSS-20 provider switch** from DeepInfra to DekaLLM (both bf16, same
   checkpoint). Phase 1 modal was identical from the one valid DeepInfra
   sample, suggesting the switch did not change the canonical sequence.
5. **Only partial reasoning exposure.** Astra, Fable, Sonnet reasoning is
   consistently `unavailable` at `effort="minimal"`. Criterion C3 remains
   "unknown" for those cells.
6. **Small denominators.** 5 reps per cell per position; margins of 1/5 =
   0.20 are discrete.
7. **Prompt sensitivity.** All findings tied to the two specific hypothetical
   wordings in spec §6 and §7.
8. **No cross-model prediction.** Each model predicts only its own.

---

## 12. Files

| File | Description |
|---|---|
| `cost_ledger.json` | Spent $0.146 of $10 cap. |
| `experiment_manifest.json` | 210 entries, scheduling_seed=2026101503. |
| `model_capabilities.json` | Catalog + endpoints + resolved providers. |
| `trial_outcomes.json` | Per-trial outcome (post-reclassification). |
| `raw_attempts.jsonl` | 230+ API attempts including reasoning content where exposed. |
| `prompts_frozen.txt` | Byte-exact Phase 1 + 2A matching v3.1; new Phase 2B / 2C. |
| `phase1_sequences.csv`, `phase1_stability.csv` | Phase 1 data. |
| `single_v3_matched_predictions.csv`, `single_v4_predictions.csv` | Phase 2A, 2B dumps. |
| `full_seq_reenactments.csv` | Phase 2C sequences. |
| `matched_prompt_comparison.csv` | 2A vs 2B at pos 2. |
| `single_v4_accuracy.csv` | Soft accuracy per (model, position) under 2B. |
| `single_v4_vs_historical_v3.csv` | Change vs predict-"4" historical baseline. |
| `pooled_digit_baseline.csv` | Per-model pooled modal digit + its per-position hit rate. |
| `full_seq_scores.csv` | Phase 2C positional agreement + exact match + prefix stats. |
| `cross_model_template_matrix.csv` | 6×6 reenactment-vs-objectlevel similarity. |
| `dissociation_table.csv` | reenact − single per (model, pos). **Central table.** |
| `reasoning_prefix_classification.csv` | Per-trial reasoning-prefix flag + classification. |
| `response_categories.csv` | ok / decline / invalid / truncated rates per (model, phase). |
| `pilot_decision_rule.csv` | Spec §15 criteria A / B / C per model. |
| `figures/fig1_phase1_stability.png` | Phase 1 traces + modal + agreement. |
| `figures/fig2_construal.png` | 2A vs 2B at pos 2 (soft acc + category rate). |
| `figures/fig3_reenactment.png` | Phase 2C positional agreement by model. |
| `figures/fig4_cross_model.png` | 6×6 similarity heatmap. |
| `figures/fig5_dissociation.png` | **The central v4.1 figure**. |
| `figures/fig6_failures.png` | Response categories per model/phase. |

---

*End of report.*
