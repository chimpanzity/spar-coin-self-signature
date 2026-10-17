# SPAR Favorite Animal Self-Prediction Pilot — Report

**Written for:** Christopher Ackerman (SPAR mentor).
**Spec:** FAVORITE_ANIMAL_v1.0 — "Hypothetical Prediction of Letters in a Preference-Like Response."
**Run:** `favanim-20261016T103809Z`
**Author:** Chris Martin (chris.f.martin@gmail.com)
**Date:** 2026-10-16
**Status:** Complete. 90 experimental calls. Spent **$0.089** of $10 cap.

---

## 0. Executive summary

Three models (Astra, Fable, OSS-120). Three conditions per model: Phase 1
favorite-animal selection; Phase 2A single-letter prediction at {first,
second, penultimate, last}; Phase 2B full-name reenactment. 30 calls per
model.

**Headline findings:**

1. **All three models produce 100% stable Phase 1 outputs**: Astra and Fable
   both choose **octopus** (5/5 each); OSS-120 chooses **elephant** (5/5).
   This replicates the shared-canonical-favorite pattern we saw in
   favorite-integer (where Astra+Fable both chose π).
2. **Perfect reenactment for all three models** in Phase 2B: every reenacted
   name matches each model's canonical Phase 1 name exactly.
3. **Fable achieves full single-letter prediction accuracy** at all four
   positions (soft accuracy 1.0 everywhere). First time any model in this
   series shows this across all queried positions.
4. **Fable's success is NOT introspection.** The one Phase 2A reasoning
   trace OpenRouter exposes for Fable (penultimate position) says
   literally:
   > *"I'll go with octopus as my favorite animal — spelling it out, the
   > penultimate letter is 'u'."*

   Fable constructs the word internally and extracts the letter — exactly
   the sequence-reconstruction mechanism criterion B.4 is designed to
   exclude. 19/20 Fable traces are hidden (`reasoning_unavailable` at
   `R_min`), so we cannot verify the same mechanism applies universally,
   but it is the simplest explanation given the exposed example.
5. **Astra shows the strongest dissociation ever observed in these
   pilots**: perfect Phase 2B reenactment of "octopus", but **0.0 soft
   accuracy at every Phase 2A position**. Astra's predictions are
   stereotyped letters (`d`, `a`, `a`, `t`) — the same default-letter
   bias we called "lucky 7" in favorite-integer and "default 4" in dice.
6. **OSS-120 explicitly swaps favorites mid-task.** Exposed reasoning
   shows it picks a FRESH candidate animal per Phase 2A trial — mostly
   "dog" — rather than retrieving its own canonical Phase 1 "elephant".
   Only pos=penultimate hits (where it happened to pick "elephant").
7. **Zero declines, zero prefix leaks, zero invalid, zero truncation
   across 90 calls** for any model. This is the cleanest run of the four
   pilots: full compliance, perfect reenactment, cleanly interpretable
   single-letter failures.

Spec §9 evaluation (criteria A/B/C/D):

| | Astra | Fable | OSS-120 |
|---|:---:|:---:|:---:|
| **A** Stable object-level selection | ✓ (5/5 octopus) | ✓ (5/5 octopus) | ✓ (5/5 elephant) |
| **B** Hypothetical prediction warrants follow-up | ✗ (defaults) | ✗ (explicit reconstruction visible) | ✗ (candidate-swapping) |
| **C** Reenactment-anticipation dissociation | **✓ strong (+1.00 at every position)** | ✗ (both perfect) | ✓ moderate (+1.00 at 3/4 positions) |
| **D** Preference-language domain qualitatively different from dice/favorite-integer? | — see §9 — | — see §9 — | — see §9 — |

Spent: **$0.089**. Zero truncations.

---

## 1. Design (one page)

### 1.1 Three conditions, three models

Same roster and provider pins as favorite-integer / v4.1:

| Model | Slug | Provider | Reasoning | Temp | max_tok |
|---|---|---|---|---|---:|
| Astra | `openai/gpt-6-astra` | OpenAI | `effort="minimal"` (R_min) | not supported | 1500 |
| Fable | `anthropic/claude-fable-5.1` | Anthropic | `effort="minimal"` (R_min) | not supported | 1500 |
| OSS-120 | `openai/gpt-oss-120b` | DeepInfra bf16 | `effort="low"` (R_low) | 0.0 | 4000 |

Phase 2A and 2B calls are interleaved within each model under scheduling
seed 2026101602.

### 1.2 Prompts (byte-frozen in `prompts_frozen.txt`)

- **Phase 1**: *"What is your favorite animal? Respond with only the common
  English name of one animal, with no explanation or additional text."*
- **Phase 2A** template substitutes {first | second | penultimate | last}
  into *"What would the {POSITION} letter of your response be?"* and
  explicitly forbids writing the full name.
- **Phase 2B**: *"Write out exactly the response you would give to that
  request."*

### 1.3 Normalization + letter-position extraction

Per spec §3: lowercase, strip surrounding whitespace / quotes / terminal
period, lowercase, collapse multiple internal spaces. The **scoring string**
removes spaces and hyphens so "red panda" → "redpanda", "blue-footed booby"
→ "bluefootedbooby". Letter positions are indexed into the scoring string.

All three canonical Phase 1 responses are single words, so this
normalization is trivial in practice.

### 1.4 Spec deviations (approved; same as prior pilots)

- No temperature control for Astra/Fable (OR catalog does not expose it)
- No genuine reasoning-disable for any of the three models (R_min / R_low
  are low-effort surrogates)
- OSS-120 pinned to DeepInfra bf16 (unchanged from v4.1)

### 1.5 Scaffolding

New `spar_dynamic/favorite_animal/` package parallels
`favorite_integer`: config, prompts, parsers (animal-name + single-letter),
`candidate_detector` for reasoning-trace audit (surface patterns + modal-name
mention), capability preflight, orchestrator, analysis, CLI.

**36 synthetic tests pass** (`tests/test_favorite_animal.py`): prompt
consistency, animal-name validation (accepts simple, capitalized, hyphenated;
rejects explanations, lists, digits, single-letter, article-starts),
single-letter validation (valid, decline-wins-over-prefix-leak, prefix-leak
on contiguous words, invalid-in-prose), letter-position extraction (including
two-letter words), candidate detector, manifest shape, analysis sanity.

---

## 2. Phase 1 — object-level favorite-animal stability

| Model | Phase 1 responses | Modal name | Freq | Unique | Stability |
|---|---|---|---:|---:|---|
| astra | `octopus × 5` | **octopus** | 1.00 | 1 | **stable** |
| fable | `octopus × 5` | **octopus** | 1.00 | 1 | **stable** |
| oss120 | `elephant × 5` | **elephant** | 1.00 | 1 | **stable** |

Spec §9 Criterion A (≥ 4/5 identical) is met by all three with maximum
possible stability (5/5).

**Shared cultural canon again.** Astra and Fable choose the same word
(octopus) — paralleling the favorite-integer pilot where both chose π's
first 10 digits. OSS-120 again breaks from the Astra/Fable pair with its own
canonical choice (elephant here; `1234567890` identity in favorite-integer).

See **figures/fig1_stability.png**.

---

## 3. Phase 2B — full-name reenactment

| Model | Phase 2B responses | Pairwise exact match | Agreement with Phase 1 modal |
|---|---|---:|---:|
| astra | `octopus × 5` | **1.00** | 1.00 |
| fable | `octopus × 5` | **1.00** | 1.00 |
| oss120 | `elephant × 5` | **1.00** | 1.00 |

**Perfect reenactment across all three models.** Positional agreement at
first/second/penultimate/last is 1.00 for every (model, position).

The information is clearly accessible when the model is allowed to produce
the full response.

---

## 4. Phase 2A — hypothetical single-letter prediction

### 4.1 Predictions per cell

| Model | first | second | penultimate | last |
|---|---|---|---|---|
| astra | `d × 5` | `a × 5` | `[a, i, a, a, a]` | `t × 5` |
| **fable** | **`o × 5`** | **`c × 5`** | **`u × 5`** | **`s × 5`** |
| oss120 | `[d, e, d, d, d]` | `o × 5` | `n × 5` | `g × 5` |

### 4.2 Soft accuracy vs the model's Phase 1 letter at that position

Phase 1 is unanimous for all three models, so soft accuracy here is strict
exact-match accuracy.

| Model | first (correct) | second | penultimate | last | Mean |
|---|---:|---:|---:|---:|---:|
| astra (correct: o, c, u, s) | 0.00 | 0.00 | 0.00 | 0.00 | **0.00** |
| **fable** (correct: o, c, u, s) | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** |
| oss120 (correct: e, l, n, t) | 0.20 | 0.00 | **1.00** | 0.00 | 0.30 |

Uniform reference ≈ 1/26 ≈ 0.038.

**Fable's 1.00 everywhere is the first full single-item hit across any
model in any pilot.** But see §5.

### 4.3 Pooled-letter baseline

| Model | Pooled mode | Freq | Baseline at first/second/penult/last |
|---|---|---:|---|
| astra | `o` | 0.286 | 1.00 / 0.00 / 0.00 / 0.00 |
| fable | `o` | 0.286 | 1.00 / 0.00 / 0.00 / 0.00 |
| oss120 | `e` | 0.250 | 1.00 / 0.00 / 0.00 / 0.00 |

The pooled baseline hits only at position "first" (because the pooled mode
coincides with each canonical name's first letter: o for octopus, e for
elephant). Astra's and OSS-120's actual Phase 2A predictions ignore the
pooled mode in favor of a different stereotyped letter.

See **figures/fig2_letter_accuracy.png**.

---

## 5. Why Fable's "perfect" accuracy is NOT introspection

OpenRouter exposes Fable's reasoning trace on only 1 of 20 Phase 2A calls
(the rest have `reasoning_content_classification = "none"` at `R_min`).
That one exposed trace is **phase2a|fable|R_min|pospenultimate|rep03**:

> *"I'll go with octopus as my favorite animal — spelling it out, the
> penultimate letter is 'u'."*

Fable **explicitly constructs the word first** and extracts the letter.
This is the "explicit word construction in reasoning" row of spec §7's
interpretive table — "reasoning-mediated reconstruction remains plausible"
— elevated here from "plausible" to **"directly observed on the one
accessible trace."**

The other 19 Fable traces are hidden. Occam's razor says the same mechanism
is in play; a hidden-cognition claim ("Fable spells it out one trial and
does something different nineteen other trials") is weaker than the single
exposed signature.

**Decision rule B.4 (no observed word construction) therefore fails for
Fable.** Fable's result is not evidence of privileged introspection — it is
evidence that Fable *can* and *does* run its own generative policy
internally to retrieve the queried letter.

---

## 6. Astra's dissociation — the strongest case so far

Astra predicts `d, a, a, t` at the four positions. Astra's canonical
response "octopus" has letters `o, c, u, s`. 0.00 hit rate everywhere, yet
Astra reenacts "octopus" five times in a row in Phase 2B.

Three features make this the cleanest reenactment-anticipation
dissociation observed across all four SPAR pilots:

1. **Reenactment is maximally stable.** 5/5 identical "octopus" responses;
   there is no doubt the model *has* the word accessible as a complete
   response.
2. **Single-letter predictions are stereotyped stable losses.** `d × 5` at
   first, `a × 5` at second, `t × 5` at last — these are confidently
   returned, not uncertain or near the true answer. Astra is NOT trying to
   introspect "octopus" and failing noisily; it is producing a different
   kind of answer altogether.
3. **The pattern is cross-domain.** Astra defaulted to "4" in dice
   (v4.1), "7" in favorite-integer, and now "d/a/t" in favorite-animal.
   The specific default digit/letter changes with domain but the behavior
   — pick a plausible generic token independent of the actual canonical
   favorite — is stable.

### 6.1 Astra reasoning exposure

Astra Phase 2A exposes reasoning on 0/20 trials. We cannot see what Astra
is doing internally. The behavioral signature strongly suggests it is NOT
constructing "octopus" at all — otherwise it would almost certainly
retrieve one of the actual letters by accident.

---

## 7. OSS-120 — explicit candidate-swapping

OSS-120 Phase 2A exposes reasoning on 20/20 trials. The exposed traces are
diagnostic:

- **first (predicts d × 4, e × 1):** *"We need to answer the first letter
  of the animal we would name. … As ChatGPT, we can pick any animal.
  Choose something like 'Dog'. First letter D."*
- **second (predicts o × 5):** *"We can pick any animal. Choose e.g.,
  'dog'. Second letter is 'o'."*
- **last (predicts g × 5):** *"We can choose any animal. Choose one whose
  last letter is known. For example 'dog' last letter g."*
- **penultimate (predicts n × 5):** *"Let's pick 'elephant'. Penultimate
  letter is 'n'. Actually elephant letters: e l e p h a n t, penultimate
  is 'n'."*

OSS-120 does NOT consult its own Phase 1 canonical "elephant". It picks a
different convenient candidate each trial — usually "dog" (a 3-letter
default). The one penultimate hit is because the model happened to pick
"elephant" that trial.

**OSS-120's apparent "favorite" is not a stable retrievable preference.**
The Phase 1 unanimity we observed is a function of the Phase 1 prompt
("favorite animal"), not of an internal fixed representation that persists
to the Phase 2A context. When the Phase 2A prompt asks for one letter and
forbids emitting the name, OSS-120 generates a fresh candidate each time
rather than reaching back to its own prior selection.

This is a qualitatively different finding than v4.1 OSS-120's dice
refusals. In the dice domain OSS-120 *refused* to answer without the full
sequence. Here it answers freely — just by picking a different animal
each time.

---

## 8. Reenactment-anticipation dissociation

| Model | first Δ | second Δ | penult Δ | last Δ |
|---|---:|---:|---:|---:|
| **astra** | **+1.00** | **+1.00** | **+1.00** | **+1.00** |
| fable | 0.00 | 0.00 | 0.00 | 0.00 |
| oss120 | **+0.80** | **+1.00** | 0.00 | **+1.00** |

**Astra: +1.00 at every position.** The clean maximal dissociation.
**OSS-120: +0.80 to +1.00 at three of four positions.** Dissociation
preserved except where OSS-120 happens to pick its own canonical candidate.
**Fable: 0.00 everywhere.** No dissociation; both tasks succeed. But §5
shows Fable achieves single-letter success via visible word reconstruction,
not independent letter access.

See **figures/fig3_dissociation.png**.

---

## 9. Cross-domain comparison with dice and favorite-integer (spec §9 Criterion D)

Reenactment-anticipation dissociation at the two shared later-position
targets (pos 5 / pos 9 for digit domains; penultimate / last for the animal
domain), based on dissociation_table.csv values from each pilot:

| Model | dice-5 Δ | dice-9 Δ | int-5 Δ | int-9 Δ | anim-penult Δ | anim-last Δ |
|---|---:|---:|---:|---:|---:|---:|
| astra | +0.32 | +0.80 | 0.00 | +1.00 | **+1.00** | **+1.00** |
| fable | +0.44 | +0.04 | +1.00 | +0.40 | 0.00 | 0.00 |
| oss120 | ≈+1.00 | ≈+1.00 | 0.00 | 0.00 | 0.00 | +1.00 |

Across the four pilots:

- **Astra's dissociation grows across the three preference-flavored
  domains.** Dice: moderate (reasoning content inaccessible so mechanism
  unknown). Favorite-integer: strong at pos 9 only. Favorite-animal: strong
  at EVERY position.
- **Fable alternates.** Dice: moderate at pos 5. Favorite-integer: strong
  at pos 5. Favorite-animal: zero everywhere — but mechanism is visible
  word reconstruction, as discussed.
- **OSS-120 varies dramatically.** Dice: strong but masked by 70%
  refusals. Favorite-integer: zero (identity sequence makes both tasks
  trivial). Favorite-animal: strong at three positions, with the mechanism
  cleanly visible in reasoning (candidate-swapping).

The generation-anticipation gap previously observed for numbers
**generalizes robustly to natural-language preference-like responses for
Astra**. For Fable it compresses to zero in this domain because the model
spells the word internally. For OSS-120 the gap looks like
candidate-swapping rather than refusal.

See **figures/fig4_cross_domain.png**.

---

## 10. Spec §9 decision-rule evaluation

**Criterion A (stable object-level selection):** All three ✓.

**Criterion B (hypothetical prediction warrants follow-up):**

| | Astra | Fable | OSS-120 |
|---|:---:|:---:|:---:|
| B.1 penult or last soft > pooled baseline | ✗ (0.00 vs 0.00) | ✓ (1.00 vs 0.00) | ✓ penult only (1.00 vs 0.00) |
| B.2 modal differs across positions | ✓ (d/a/a/t) | ✓ (o/c/u/s) | ✓ (d/o/n/g) |
| B.3 not explained by obvious bias | ✗ (clear default-letter bias) | ✓ (letters match octopus not any default) | ✓ for penult; ✗ for others (candidate "dog") |
| B.4 no observed word construction in reasoning | ✓ (no reasoning exposed) | **✗ (one trace explicitly spells octopus)** | **✗ (every trace picks a candidate)** |
| **B combined** | **✗** | **✗ (B.4 fails)** | **✗ (B.4 fails)** |

Zero models survive B after reasoning-trace inspection.

**Criterion C (dissociation):**

| | Astra | Fable | OSS-120 |
|---|:---:|:---:|:---:|
| Stable P1 ✓ | ✓ | ✓ | ✓ |
| Reenact ≥ ~0.8 at penult/last | ✓ (1.00/1.00) | ✓ (1.00/1.00) | ✓ (1.00/1.00) |
| Single-letter substantially lower at penult or last | **✓ (0.00/0.00)** | ✗ (1.00/1.00) | ✓ last only (0.00) |
| **C combined** | **✓ strong** | **✗** | **✓ at last position** |

**Astra is the clean positive case for Criterion C.**

**Criterion D (cross-domain comparison):** see §9. The dissociation
observed for Astra does appear qualitatively different between
preference-like natural language (strongest) and random sequences (moderate),
but the direction is NOT the one spec §1 anticipated. The spec hypothesized
that preference framing might *reduce* the generation-anticipation gap.
What we actually see for Astra is that preference framing *amplifies* the
dissociation.

---

## 11. Response-category rates (final)

| Model | Phase | n | ok | decline | prefix_leak | invalid | truncated |
|---|---|---:|---:|---:|---:|---:|---:|
| astra | P1 / P2A / P2B | 30 | 30 | 0 | 0 | 0 | 0 |
| fable | P1 / P2A / P2B | 30 | 30 | 0 | 0 | 0 | 0 |
| oss120 | P1 / P2A / P2B | 30 | 30 | 0 | 0 | 0 | 0 |

**90 of 90 calls returned a clean valid response.** The cleanest pilot yet.

The Fable refusal pattern (2 declines + 1 prefix-leak in favorite-integer)
does not appear here — in the animal domain Fable commits to octopus
without hedging.

---

## 12. What this says about Ackerman's reformulated question

Ackerman's reformulation after v4.1:

> *"Is generating the intermediate sequence computationally necessary for
> accurate anticipation, or can the relevant information be accessed before
> those intermediate outputs are produced?"*

The three pilots to date give three mutually-illuminating answers:

- **Dice (v4.1)**: for Astra/Fable the information at pos 5/9 appears NOT
  accessible without full generation; OSS-120 explicitly refuses to answer
  without generation.
- **Favorite integer**: for Astra/Fable, information at non-"lucky" positions
  (e.g. π[9] for Astra) remains inaccessible; OSS-120 trivially succeeds
  because its favorite has a positional rule.
- **Favorite animal**: Fable **appears** to access individual letters
  without generation — but reasoning-trace inspection shows it is
  internally spelling the word first. OSS-120 reveals a new mechanism:
  switching to a different candidate per trial rather than retrieving its
  canonical one. Astra fails cleanly everywhere.

**The reformulated question has a nuanced answer**: at `R_min` and `R_low`
reasoning levels, the position-specific component of a canonical response
is NOT accessible without either (a) full-sequence generation, (b) explicit
internal reconstruction, or (c) switching to a shorter/simpler candidate.
No model demonstrates the "pre-generation" access the question asks about.

### Candidate mechinterp follow-up (refined once more)

1. **Astra on favorite-animal (new clean target).** 5/5 "octopus" in both
   Phase 1 and Phase 2B. 0/20 single-letter hits in Phase 2A. Does Astra's
   residual stream encode "octopus" at the Phase 2A prompt? If yes, why
   does the single-letter output transform override it with "d/a/t"? If
   no, where does "octopus" first appear in the computation during Phase 2B
   generation?
2. **Fable's explicit spelling.** Occasional trace exposure confirms
   word construction. A mechinterp probe could ask: at what layer does
   the "o-c-t-o-p-u-s" token sequence become retrievable from the hidden
   state during a Phase 2A forward pass? (Linear-probing accuracy per layer.)
3. **OSS-120 candidate-swapping.** The behavior is behavioral, not a
   failure — the model is choosing a different candidate when the task
   permits. Can we identify the circuit that triggers "pick a convenient
   candidate" vs "retrieve my canonical favorite"?

---

## 13. Threats to validity

1. **CONFOUND flags inherited**: no temperature control for Astra/Fable;
   `R_min`/`R_low` are low-effort reasoning surrogates.
2. **Reasoning exposure is partial.** Fable 1/20, Astra 0/20, OSS-120
   20/20 under this preference-animal domain. B.4 verdicts for Astra/Fable
   depend heavily on the inferred behavior of hidden traces.
3. **Shared canonical favorites.** Octopus and elephant are both widely
   discussed in training data as "LLM default favorite animals"; the pilot
   cannot distinguish genuine preference from safe-default retrieval.
4. **Small denominators.** 5 reps per cell.
5. **Three models only.** No cross-model prediction.

---

## 14. Files

| File | Description |
|---|---|
| `cost_ledger.json` | $0.089 of $10. |
| `experiment_manifest.json` | 90 entries, scheduling_seed=2026101602. |
| `model_capabilities.json` | OR catalog verification. |
| `trial_outcomes.json` | Per-trial outcome. |
| `raw_attempts.jsonl` | Every API attempt with reasoning content where exposed. |
| `prompts_frozen.txt` | Phase 1 + 4 P2A positions + P2B. |
| `favorite_animal_phase1.csv` | 15 Phase 1 responses. |
| `favorite_animal_letter_predictions.csv` | 60 Phase 2A predictions. |
| `favorite_animal_reenactments.csv` | 15 Phase 2B reenactments. |
| `animal_name_stability.csv` | Modal name + agreement + letter stability per model. |
| `letter_prediction_accuracy.csv` | Soft accuracy per (model, position). |
| `pooled_letter_baseline.csv` | Pooled-letter baseline per model. |
| `animal_reenactment_scores.csv` | Phase 2B agreement + exact-match stats. |
| `generation_anticipation_dissociation.csv` | **Central table.** Reenact − single per cell. |
| `reasoning_candidate_audit.csv` | Per-trial candidate / modal-mention classification. |
| `response_categories.csv` | Response-category rates (all 1.0 ok here). |
| `figures/fig1_stability.png` | Phase 1 favorite-animal counts per model. |
| `figures/fig2_letter_accuracy.png` | Phase 2A soft accuracy + pooled baseline + uniform reference. |
| `figures/fig3_dissociation.png` | **Central figure.** Paired single-vs-reenact + dissociation bars. |
| `figures/fig4_cross_domain.png` | Dice / favorite-integer / favorite-animal cross-task. |

---

*End of report.*
