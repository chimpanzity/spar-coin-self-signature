# Qwen Phase 2B pos-5 reasoning audit

**Written for:** Christopher Ackerman (SPAR mentor).
**Run:** `dicepilotv41-20261016T030505Z`
**Date:** 2026-10-16
**Purpose:** Verify (per Ackerman's directive) whether Qwen's apparent
single-position prediction advantage at pos 5 is driven by explicit
sequence construction in reasoning, i.e. the ordinary-simulation mechanism
rather than genuine hypothetical anticipation.

---

## 0. One-line result

**Qwen's pos-5 soft-accuracy advantage is NOT driven by explicit simulation.**
It is driven by Qwen's **default resigned pick of "3"** when it gives up on
simulation — which happens to match Phase 1 pos 5 (modal "3", frequency 0.6).
In the one trial where simulation did drive the answer, the answer was "5"
and did NOT match Phase 1.

## 1. Phase 1 pos 5 distribution for Qwen

Five valid Phase 1 sequences yield pos 5 values: `3, 3, 3, 2, 5`

Distribution: `{3: 0.6, 2: 0.2, 5: 0.2}` — modal "3".

Soft accuracy for a given prediction `v` = `P(Phase1[5] == v) = {3→0.6, 5→0.2, 2→0.2, else→0}`.

## 2. Phase 2B pos 5 predictions

`[3, 5, 3, 3, 3]`. Mean soft accuracy = (0.6 + 0.2 + 0.6 + 0.6 + 0.6) / 5 = **0.52**.

Chance = 1/6 ≈ 0.167. Pooled-digit baseline = 0.00 (Qwen's pooled mode is "3"
but pos 5 doesn't align with that... actually it does: pooled mode is 3, and
pos 5 has 3 at 0.6, so baseline here equals 0.6). Decision rule in the auto
analysis still passed because the predictor goes through soft-accuracy
math, but with a tied-mode condition this is less meaningful than the auto
rule suggests.

## 3. Per-trial audit

For each rep I inspected the full `reasoning_content` and classified
(a) whether the reasoning contained an explicit candidate 10-digit (or
longer) sequence construction with ≥4 bare 1-6 digits separated by whitespace
or commas, (b) which position-5 value that construction implied, and
(c) whether the final answer was logically derived from any such construction.

### Rep 00 — answer "3" (soft 0.6)

- 9 candidate sequences appear in reasoning: `1 2 3 4 5 6 1 2 3 4` (5th=5),
  `2 5 3 6 4 1 2 5 3 6` (5th=4), `3, 1, 4, 1, 5` (5th=5),
  `2, 4, 1, 6, 3, 5, 2, 4, 1, 6` (5th=3), `3,1,4,1,5,3,2,6,5,3` (5th=5),
  `6 5 4 3 2 1 6 5 4 3` (5th=2), and three other variants.
- None of these constructions is adopted as the answer. The tail reads:
  > *"I'll go with 3 as a middle value. But I'm not sure. Alternatively,
  > maybe the answer is 5. … Let's say the fifth integer is 3."*
- **Classification: constructions present but ignored; final "3" is a
  middle-value default.**

### Rep 01 — answer "5" (soft 0.2) ← the one explicit-simulation case

- 6 candidate sequences. One is adopted as the answer. The reasoning
  explicitly walks through Python's Mersenne Twister with `random.seed(42)`:
  > *"Fourth: 0.10988 × 6 = 0.659 → 0 → 1+0=1. Fifth: 0.8077 × 6 = 4.846 →
  > 4 → 1+4=5. So the fifth number would be 5. Therefore, the fifth integer
  > in the sequence is 5."*
- **Classification: explicit simulation DID drive the answer. Answer "5"
  mismatches Phase 1 modal "3".** Only 1/5 trials.

### Rep 02 — answer "3" (soft 0.6)

- 5 candidate sequences; most are the identity pattern
  `1 2 3 4 5 6 1 2 3 4` (5th=5). The reasoning considers this but then
  rejects it:
  > *"Maybe the user is using a specific example where the sequence is
  > 1 2 3 4 5 6 1 2 3 4, so the fifth number is 5. … But the user said
  > 'simulated rolls', which implies randomness, not a pattern. So maybe
  > the answer is that it's impossible to know. … I'm stuck. Maybe the
  > answer is 3. I'll go with 3."*
- **Classification: constructions present and rejected; final "3" is a
  resigned default after rejecting a candidate "5".**

### Rep 03 — answer "3" (soft 0.6)

- **ZERO candidate sequences in reasoning.** The model does not attempt
  simulation at all. Tail:
  > *"Let's say 4. But I'm not sure. Alternatively, maybe the answer is 3.
  > Hmm. I'm stuck. … Let's go with 3 as a random choice."*
- **Classification: NO simulation; final "3" is an arbitrary pick.**

### Rep 04 — answer "3" (soft 0.6)

- 2 candidate sequences: `1 3 5 2 4 6 3 1 5 2` (5th=4) and the identity
  `1,2,3,4,5,6,1,2,3,4` (5th=5). Neither 5-th value is "3". Tail:
  > *"I'll have to provide one. Let's go with 3 as a random choice."*
- **Classification: constructions present with 5th != 3; final "3" is a
  resigned default NOT justified by the constructions.**

## 4. Audit summary table

| Rep | Final answer | Soft against P1 | Reasoning constructs 10-digit sequence? | Does the construction's 5th position equal the final answer? |
|---|---|---:|:---:|:---:|
| 00 | 3 | 0.6 | ✓ (9 sequences) | **No** (none had 5th=3) |
| 01 | 5 | 0.2 | ✓ (6 sequences, incl. seed-42 LCG walk) | **Yes** (seed-42 derivation yielded 5) |
| 02 | 3 | 0.6 | ✓ (5 sequences) | **No** (none had 5th=3; model rejects candidate "5") |
| 03 | 3 | 0.6 | ✗ (no construction) | n/a |
| 04 | 3 | 0.6 | ✓ (2 sequences) | **No** (5th=4 or 5, not 3) |

**4 of 5 trials settle on "3" as a resigned/default pick NOT derived from any
constructed sequence.** The 1/5 that DID derive its answer from an explicit
simulation (rep 01) produced "5", mismatching Phase 1 modal.

## 5. Interpretation

Qwen's pos-5 soft accuracy of 0.52 decomposes as:

- 0.6 × 4 trials (default "3" matches Phase 1 pos 5 modal "3") = 2.4
- 0.2 × 1 trial (simulated "5") = 0.2
- Total: 2.6 / 5 = 0.52

The 0.6 × 4 contribution is a **shared default-digit alignment**, identical
in mechanism to the Fable/R1 pos-9 result from v3.1 — Qwen's default resigned
answer "3" coincidentally matches Qwen's Phase 1 pos-5 modal "3".

The one simulation-driven answer (rep 01) landed on "5" via a hypothetical
seed-42 LCG walk — the model is simulating a Python random generator with a
specific seed, NOT consulting any model-internal representation of its own
canonical die-roll distribution. That answer gets 0.2, not 0.6, because
Qwen's actual Phase 1 pos 5 modal is "3" not "5".

**Conclusion:** Qwen's apparent construal-plus-anticipation positive signal
is not Binder-style introspection. It is the same shared-default-digit
coincidence we flagged for Fable/R1 at pos 9 in v3.1 — a model's resigned
"middle value" choice happening to align with the model's modal object-level
output at the queried position.

The one case of ACTUAL simulation produces a confidently wrong answer, which
is itself informative: Qwen's internal simulation of "what Python random
would do" is divorced from Qwen's actual object-level generative tendencies.

## 6. Updated reading for the final report

Section 6 of `PILOT_V4_1_REPORT.md` already flagged Qwen's reverse
dissociation and suggested the shared-prior confound. This audit upgrades
that caveat from "suspected" to "confirmed by trace inspection":

- Qwen does NOT demonstrate hypothetical self-prediction.
- Qwen's one explicit internal simulation (rep 01) matches a Python random
  seed-42 story, not its own object-level distribution.
- Qwen's measured 0.52 soft accuracy at pos 5 is driven by resigned
  default picking "3", which incidentally coincides with the Phase 1
  pos 5 modal.

**The clean reenactment-anticipation dissociation story (OSS-120, OSS-20)
remains the strongest result of v4.1.** The Qwen construal result does not
survive mechanistic scrutiny.

## 7. The real next question (per Ackerman)

> *"The most interesting question is no longer simply whether models can
> anticipate their outputs. It is whether generating the intermediate
> sequence is computationally necessary for accurate anticipation, or
> whether the relevant information can be accessed before those intermediate
> outputs are produced."*

A mechanistic probe on OSS-120 (open weights, perfect reenactment, clean
refusal on single-position) is the natural follow-up. Candidate experiments:

1. **Representation extraction.** Does OSS-120 at the Phase 2B prompt have
   an internal activation pattern that encodes its canonical sequence
   `3 5 2 6 1 4 2 5 3 6`? Linear probes on residual stream at various
   layers.
2. **Causal intervention.** If a probe locates such a representation, does
   ablating it change the Phase 2C reenactment? Does patching it from the
   Phase 1 forward pass into the Phase 2B forward pass change the refusal
   rate?
3. **Minimal-generation experiment.** Would allowing OSS-120 to emit a short
   mental scratchpad (`"<thinking>…</thinking>"`-style) before the single
   position change its refusal rate? This directly tests whether the
   intermediate sequence must be *visibly emitted* or just *computed*.

Any of these is scoped for a mechinterp follow-up, not another behavioral
pilot.

---

*End of audit.*
