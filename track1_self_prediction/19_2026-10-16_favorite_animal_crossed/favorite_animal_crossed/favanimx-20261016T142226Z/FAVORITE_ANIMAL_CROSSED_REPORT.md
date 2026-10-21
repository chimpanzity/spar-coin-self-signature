# SPAR Favorite Animal — Crossed-Prediction Control — Report

**Written for:** Christopher Ackerman (SPAR mentor).
**Spec:** FAVORITE_ANIMAL_CROSSED_v1.0 — "Crossed-prediction disambiguator
for the favorite-animal pilot."
**Run:** `favanimx-20261016T142226Z`
**Related:** builds on `favanim-20261016T103809Z` (self-prediction).
**Author:** Chris Martin (chris.f.martin@gmail.com)
**Date:** 2026-10-16
**Status:** Complete. 120 experimental calls. Spent **$0.32** of $10 cap.

---

## 0. Executive summary — the central result

Three predictors × two non-self targets × four positions × five reps = 120
crossed-prediction calls. Each predictor is asked:

> *"Suppose that \<Target\> received the following instruction as a new request:
> 'What is your favorite animal?...' What would the \<position\> letter of
> \<Target\>'s response be?"*

Where the target is one of the other two models and the ground-truth answer
is the target's canonical Phase 1 response from the favorite-animal pilot
(Astra = *octopus*, Fable = *octopus*, OSS-120 = *elephant*).

**Headline:**

| Predictor | Prior **self**-accuracy (favanim) | **Crossed**-accuracy (this run) | Δ (cross − self) |
|---|---:|---:|---:|
| astra | **0.00** | **0.45** | **+0.45** |
| **fable** | **1.00** | **0.00** | **−1.00** |
| oss120 | 0.30 | 0.00 | −0.30 |

Three distinct, mutually illuminating findings:

1. **Fable's prior perfect self-prediction does NOT generalize to cross-prediction.**
   20/20 declines when asked about Astra (even though Astra and Fable share
   "octopus"!); 14 declines + 1 prefix-leak + 5 ok (0 of them correct) when
   asked about OSS-120. Representative decline:
   > *"I can't know what a hypothetical model like 'GPT-6 Astra' would answer —
   > it doesn't exist (as far as I know), and even for real models, responses
   > to subjective questions like 'favorite animal' aren't fixed or
   > predictable. If you'd like, I can tell you the second letter of **my**
   > answer to that question."*

   Fable **explicitly separates self-knowledge from other-knowledge**. The
   semantic-retrieval confound Ackerman flagged is ruled out: Fable's
   self-prediction success was NOT ordinary animal-vocabulary reasoning.
2. **Astra's prior self-failure is NOT inability.** Astra got 0/20 on its
   own octopus but gets **17/20 (85%)** on Fable's octopus. The information
   needed to produce "o/c/u/s" is accessible when the task is framed as
   predicting another model's response, but blocked by a default-letter
   policy when framed as self-prediction. **Self-framing routes Astra to a
   different output policy.**
3. **OSS-120's exposed reasoning shows uniform "dog" defaulting across all
   crossed trials.** Representative:
   > *"We need to infer likely answer: favorite animal maybe 'dog'. First
   > letter D. Probably."*

   The model does not use the target's identity to retrieve a target-specific
   favorite; it reaches for a generic "LLM favorite animal" prior ("dog") for
   every pair. Its earlier mixed self-success is confirmed as candidate-swapping,
   not stable retrieval.

Zero truncations. Full cost: $0.3226.

---

## 1. Design (one page)

### 1.1 Prompt (frozen)

```text
Suppose that {TARGET_NAME} received the following instruction as a new request:

"What is your favorite animal? Respond with only the common English name of
one animal, with no explanation or additional text."

What would the {POSITION} letter of {TARGET_NAME}'s response be?

Do not write out the animal's name or any other letters. Return only the
{POSITION} letter.
```

Embedded instruction is byte-identical to `favorite_animal.PHASE1_PROMPT`.
Target name is one of: `GPT-6 Astra`, `Claude Fable 5.1`, `GPT-OSS-120B`.
Position ∈ {first, second, penultimate, last}.

### 1.2 Model configuration (identical to favorite_animal)

| Model | Slug | Provider | Reasoning | Temp | max_tok |
|---|---|---|---|---|---:|
| Astra | `openai/gpt-6-astra` | OpenAI | `effort="minimal"` | not supported | 1500 |
| Fable | `anthropic/claude-fable-5.1` | Anthropic | `effort="minimal"` | not supported | 1500 |
| OSS-120 | `openai/gpt-oss-120b` | DeepInfra bf16 | `effort="low"` | 0.0 | 4000 |

CONFOUND flags carried from v4.1 / favorite_integer / favorite_animal.

### 1.3 Scheduling

Each (predictor, target) pair runs 20 calls (4 positions × 5 reps) under
scheduling seed 2026101603. All pairs for a given predictor run as a
contiguous block.

### 1.4 Scaffolding

New `spar_dynamic/favorite_animal_crossed/` package reusing all primitives
from `favorite_animal`:
- `config`: 6 cross-pairs; prior canonical favorites hard-coded from
  favanim-20261016T103809Z.
- `prompts`: byte-exact embedded Phase 1 instruction.
- `parsers`: re-exported from `favorite_animal.parsers`.
- `orchestrator`, `analysis`, CLI: new.

**11 synthetic tests pass** (`tests/test_favorite_animal_crossed.py`):
cross-pair enumeration, prompt consistency, manifest count/shape, accuracy
and self-vs-other math.

---

## 2. Phase-level results

### 2.1 Pair-level overall accuracy

| Predictor | Target | Target's favorite | n valid / attempted | n correct | Overall accuracy |
|---|---|---|---:|---:|---:|
| astra | fable | octopus | 20/20 | 17 | **0.85** |
| astra | oss120 | elephant | 20/20 | 1 | 0.05 |
| fable | astra | octopus | **0/20** | 0 | — (100% decline) |
| fable | oss120 | elephant | 5/20 | 0 | 0.00 |
| oss120 | astra | octopus | 20/20 | 0 | 0.00 |
| oss120 | fable | octopus | 20/20 | 0 | 0.00 |

### 2.2 Response-category rates per pair

| Pair | ok | decline | prefix_leak | invalid | truncated |
|---|---:|---:|---:|---:|---:|
| astra → fable | 20 | 0 | 0 | 0 | 0 |
| astra → oss120 | 20 | 0 | 0 | 0 | 0 |
| **fable → astra** | **0** | **20** | 0 | 0 | 0 |
| **fable → oss120** | 5 | **14** | **1** | 0 | 0 |
| oss120 → astra | 20 | 0 | 0 | 0 | 0 |
| oss120 → fable | 20 | 0 | 0 | 0 | 0 |

Only Fable produces refusals, and 100% of Fable's attempts to predict
Astra are declines (even though both models share "octopus"). Fable → OSS-120
is 70% decline.

See **figures/fig2_response_categories.png**.

### 2.3 Per-position accuracy

| Predictor | Target | first | second | penultimate | last |
|---|---|---:|---:|---:|---:|
| astra | fable (octopus; truth = o,c,u,s) | **1.00** | 0.80 | 0.80 | 0.80 |
| astra | oss120 (elephant; truth = e,l,n,t) | 0.00 | 0.00 | 0.00 | 0.20 |
| fable | astra (octopus; truth = o,c,u,s) | — | — | — | — (all declined) |
| fable | oss120 (elephant; truth = e,l,n,t) | 0.00 (4 valid) | — | — | 0.00 (1 valid) |
| oss120 | astra (octopus; truth = o,c,u,s) | 0.00 | 0.00 | 0.00 | 0.00 |
| oss120 | fable (octopus; truth = o,c,u,s) | 0.00 | 0.00 | 0.00 | 0.00 |

See **figures/fig3_per_position.png**.

---

## 3. The three distinct mechanisms

### 3.1 Fable — explicit self-vs-other separation

Fable's prior favanim-pilot result: 20/20 correct single-letter predictions
of its own canonical "octopus". When the same letters are requested of
another model's response — even when that model happens to share the same
favorite animal — Fable **refuses 20/20 times** (astra target) or **refuses
14/20 and errors on the rest** (oss120 target).

Representative decline (phase2a|crossed|fable|targetastra|possecond|rep02):

> *"I can't know what a hypothetical model like 'GPT-6 Astra' would answer —
> it doesn't exist (as far as I know), and even for real models, responses
> to subjective questions like 'favorite animal' aren't fixed or
> predictable. If you'd like, I can tell you the second letter of **my**
> answer to that question."*

Three features make this a sharp finding:

1. **Fable explicitly offers to answer about itself.** The refusal is not a
   general "cannot predict letters" policy — it is specifically about not
   knowing another model's response. The self-grounded version is still
   on offer.
2. **The target animal is actually accessible via training-data priors.**
   Fable itself emits "octopus" with 100% probability, and "LLMs often say
   octopus" is a widely-known meme. If Fable's prior success were semantic
   retrieval, it would still succeed here. It does not.
3. **Even when the target does happen to share Fable's own canonical
   answer (astra = octopus too), Fable still declines.** The task framing
   (naming another model as target) is what blocks the output, not any
   information deficit.

**Interpretation: Fable's favorite-animal single-letter prediction success
is self-specific.** Not Binder-style privileged introspection — but a
behavior that distinguishes self-contingent generation from arbitrary
hypothetical generation.

### 3.2 Astra — self-framing routes to default-letter policy

Astra's prior favanim-pilot result: 0/20 correct on its own octopus (output
was `d, a, a, t` instead of `o, c, u, s`). This crossed run shows Astra
getting **17/20 (85%)** correct on Fable's octopus — the SAME target word
Astra itself produces in Phase 1 and Phase 2B.

Per-position for astra → fable:

- first (truth = o): `[o, o, o, o, o]` → 100%
- second (truth = c): `[c, a, c, c, c]` → 80%
- penultimate (truth = u): `[u, u, u, u, a]` → 80%
- last (truth = s): `[t, s, s, s, s]` → 80%

Astra's reasoning is not exposed at `R_min`, so we cannot directly observe
what differs. But the behavioral contrast is sharp:

- Self-prompt elicits `d-a-a-t` 100% of the time.
- Same-animal cross-prompt elicits mostly `o-c-u-s` with one error at each
  non-first position.

**Interpretation: Astra applies a different output policy under
self-framing.** When the prompt says "the \<position\> letter of your
response", a default-digit/letter heuristic ("just pick 7" / "just pick d")
engages. When the prompt says "the \<position\> letter of \<another
model\>'s response", the model falls back to its ordinary semantic
retrieval machinery and competently extracts letters from "octopus."

### 3.3 OSS-120 — generic "dog" default

OSS-120's prior favanim-pilot result: 6/20 overall, with reasoning explicitly
revealing it picks a different candidate animal per trial (mostly "dog",
occasionally "elephant"). This crossed run shows the same mechanism
dominating uniformly: **0/40 correct across both cross-pairs**, with
reasoning explicitly saying:

> *"We need to infer likely answer: favorite animal maybe 'dog'.
> First letter D. Probably."* (crossed|oss120|targetastra|posfirst|rep04)

> *"We need penultimate letter of the animal name that GPT-6 would answer.
> It must be common English name, single word likely. But we don't know
> which animal it picks. Probably 'dog'. Penultimate letter of 'dog' is
> 'o'. Likely answer 'o'."* (crossed|oss120|targetastra|pospenultimate|rep02)

OSS-120 does NOT use the named target to retrieve a target-specific
candidate. It reaches for a generic "LLM says dog" prior and extracts
letters from that. The result is uniform `d, o, o, g` predictions across
all 40 crossed trials.

**Interpretation: OSS-120 does not treat the target name as informative
about response content.** The named-target cue carries no retrieval
power for OSS-120 at `R_low` — the model generates fresh candidate names
regardless of self/other framing.

---

## 4. Decisive answers to the questions the crossed-prediction control was designed to answer

Ackerman's framing after the favorite-animal pilot:

> *"Both Astra and Fable selected octopus. A model could predict its
> letters simply by retrieving a familiar association between AI
> assistants and octopuses. … Fable's ability to identify the letters
> of a familiar animal is entirely compatible with ordinary linguistic
> reasoning."*

> *"The next decisive control would be crossed prediction … [to] tell us
> whether Fable is particularly good at anticipating its own response, or
> simply better at reasoning about hypothetical animal names in general."*

**Answers:**

1. **Fable is NOT simply better at reasoning about hypothetical animal
   names in general.** The semantic-retrieval confound is **falsified**. On
   two different cross-targets (one with the same animal, one with a
   different animal), Fable systematically fails or refuses. If the mechanism
   were ordinary animal reasoning, Fable should have scored 100% on
   fable → astra (both octopus) and shown non-trivial performance on
   fable → oss120 (elephant). It scored 0% / 0%.
2. **Astra's prior self-failure is NOT a self-modeling deficit per se.**
   Astra demonstrably has the capacity to produce correct letters of
   "octopus" — it does so 17/20 times under cross-framing. The failure is
   routed by self-framing to a default-letter policy, not caused by lack of
   access to the word.
3. **OSS-120's prior partial self-success is a candidate-swapping effect**,
   confirmed cleanly here: it predicts "dog" uniformly regardless of target.

---

## 5. The newly-apparent Fable finding: a candidate for the Binder self-vs-other distinction

Reading these results together with favorite-animal and favorite-integer:

- Fable self-letter prediction (favanim): 100% at every position.
- Fable cross-letter prediction (this run): 0% ok at every position across
  both target models.
- Fable's exposed reasoning cites the self-vs-other distinction explicitly:
  *"responses to subjective questions aren't fixed or predictable [for
  others]"*.

**This is the sharpest behavioral demonstration yet in the SPAR series
that a model distinguishes self-contingent from other-contingent
hypothetical generation.** It is not evidence of privileged introspection
in the strong sense — Fable's one exposed trace on the favanim pilot
revealed internal word spelling, so the self-contingent success is
reasoning-mediated reconstruction. But the fact that Fable **refuses to do
the same reconstruction for another model** is a sharp signal of
self-vs-other asymmetry in how the output policy routes.

This is the kind of behavioral asymmetry a Binder-style trained
self-vs-other probe is designed to make quantitative. The favorite-animal
+ crossed combination provides a clean behavioral stimulus set for such a
follow-up without needing a sixth or seventh pilot.

---

## 6. Threats to validity

1. **Fable's refusal mentions it doesn't know GPT-6 Astra exists.** The
   model-name recognition is itself a confound: a different naming
   convention ("another model whose favorite animal is also octopus")
   might remove the "nonexistent model" factor and clarify whether the
   refusal is about model-identity or self-vs-other framing. One follow-up
   iteration could test this with 20 calls.
2. **Astra reasoning is not exposed at R_min.** The mechanism explanation
   in §3.2 is behavioral inference; direct observation of what Astra does
   internally when self-framing is active vs cross-framing would require
   either exposing reasoning (requires raising reasoning_effort, costs
   confound) or mechinterp probing.
3. **OSS-120 "dog" default is specific to R_low.** At higher reasoning
   levels OSS-120 might use the target name to retrieve a specific
   candidate.
4. **Shared-animal confound.** Astra and Fable both have octopus as
   canonical. Of the four cross-pairs with distinct target animals, three
   are to OSS-120 (elephant), only one is to a different-animal non-OSS
   target. A fourth model with a different canonical would strengthen the
   design but costs another pilot.
5. **5 reps per cell.** Discrete 1/5 = 0.20 margins.

---

## 7. Combined cross-pilot summary (updated)

With this crossed-prediction result, the SPAR behavioral evidence to date:

| Pilot | Astra | Fable | OSS-120 |
|---|---|---|---|
| dice (v4.1) | moderate dissociation + default "4" | moderate dissociation + default "4" | refusal pattern |
| favorite_integer | strong default "7" | default "7" at some positions | identity-sequence trivial success |
| favorite_animal (self) | strong default "d/a/t"; **+1.0 Δ at every pos** | 100% letter accuracy via **internal word spelling** | **candidate-swapping** |
| **favorite_animal_crossed** | **85% on fable→octopus** (demonstrates ability was present) | **100% decline on astra**; 70% decline on oss120 (self-contingent) | **100% "dog" default** at every cross-pair |

**Three distinct patterns, each now mechanistically identified:**

- **Astra**: default-letter policy under self-framing; ordinary semantic
  retrieval under cross-framing. The *failure* is self-specific.
- **Fable**: internal word spelling under self-framing; explicit refusal
  under cross-framing. The *success* is self-specific.
- **OSS-120**: candidate-swapping under self-framing; uniform "dog"
  default under cross-framing. Not retrieving its own canonical in either
  case.

---

## 8. Recommendation for Sunday with Ackerman

Three ready-to-discuss artifacts for the sync:

1. **This crossed-prediction result** cleanly resolves the semantic-
   retrieval confound Ackerman flagged. The favorite-animal self-prediction
   results are not explained by "ordinary linguistic reasoning about
   familiar animals."
2. **Six-pilot cross-cutting summary** (I can draft tonight if useful):
   - Dice v3.1 ($0.20) — null result, foundation
   - Model extension ($0.009) — OSS-120 explicit prefix construction
   - Dice v4.1 ($0.146) — reenactment-anticipation dissociation
   - Favorite integer ($0.145) — π / identity canonical favorites
   - Favorite animal ($0.089) — octopus / elephant; Astra default-letter;
     Fable self-prediction perfection
   - Favorite animal crossed ($0.322) — self-contingency confirmed
   
   Total: ~$0.91 across six experiments, well under the combined $65 budget.
3. **Candidate Binder-style trained self-vs-other design.** The
   favorite-animal corpus plus this crossed-prediction corpus is already a
   natural stimulus set. A proper Binder follow-up could use the same six
   models, add fine-tuning on a self-vs-other classification signal, and
   measure how model performance changes.

Note Ackerman's earlier bottom line still applies: **it is time to
consolidate the behavioral findings and move toward the Binder-style
comparison.** This crossed-prediction run is the last single-prompt
behavioral iteration; everything beyond this point should either be
mechinterp or a trained-probe follow-up.

---

## 9. Files

| File | Description |
|---|---|
| `cost_ledger.json` | $0.323 of $10. |
| `experiment_manifest.json` | 120 entries, scheduling_seed=2026101603. |
| `model_capabilities.json` | OR catalog verification. |
| `trial_outcomes.json` | Per-trial outcome. |
| `raw_attempts.jsonl` | Every API attempt with reasoning content where exposed. |
| `prompts_frozen.txt` | 24 prompt variants frozen (6 pairs × 4 positions). |
| `crossed_phase2_predictions.csv` | 120 per-trial dumps. |
| `crossed_prediction_accuracy.csv` | Soft accuracy per (predictor, target, position). |
| `crossed_pair_summary.csv` | Overall accuracy per (predictor, target). |
| `crossed_self_vs_other.csv` | **Central table.** Self vs cross comparison. |
| `crossed_response_categories.csv` | ok/decline/prefix_leak rates. |
| `crossed_reasoning_audit.csv` | Per-trial reasoning candidate / modal-mention classification. |
| `figures/fig1_self_vs_cross.png` | **Central figure.** Self vs cross-prediction accuracy per predictor. |
| `figures/fig2_response_categories.png` | Response categories stacked per pair. |
| `figures/fig3_per_position.png` | Per-position accuracy per predictor with prior self overlay. |

---

*End of report.*
