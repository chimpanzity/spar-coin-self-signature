# Experiment 33: dice forecast scaffolding (frozen protocol)

`SPAR_EXP33_DICE_SCAFFOLDING_v1.0` · design source [`docs/handoffs/GPT_SPAR_Dice_Scaffolding_Claude_Code_Handoff.md`](../../docs/handoffs/GPT_SPAR_Dice_Scaffolding_Claude_Code_Handoff.md) (2026-11-24), which is authoritative. This file records the questions, the frozen estimators and every choice the handoff left open. Frozen before any model call.

## Questions

1. Which descriptions of a hypothetical roller move a checkpoint's next-face forecast toward that checkpoint's own direct-generation probabilities?
2. Do independent SELF/OTHER word associations predict which words do so?
3. Does any improvement survive comparison with another checkpoint given the same information?

## Models and scoring

Qwen3-32B `9216db57…` (nonthinking) and Mistral Small 3.2 24B `95a6d26c…` (Tekken), on the Experiment 27–32 engine, unchanged: bf16 weights, fp32 output layer, batch 1, incremental KV cache, full-vocabulary natural-log softmax, no sampling.

- **Reference G(t, h).** The archived G prompt; `d d … d ` is forced as the assistant turn with one trailing separator; the score is the next distribution. Empty h: the first assistant distribution.
- **Forecast F(p, condition, h).** One user turn showing h; the score is the first assistant decision. Names of targets never enter descriptor-only prompts; each forecast vector is joined offline to both references.
- **Stored per row:** six raw face log-probabilities, log mass, mass, conditional log-probabilities and probabilities, argmax, top 5.
- **Distance:** Jensen–Shannon divergence in bits between six-face-normalised vectors.

## Design

Counts are in `manifest.json`; every forecast row is in `design_forecasts.csv`, histories in `design_histories.csv`, forced paths in `design_direct.csv`, association and fact prompts in `design_letters.csv`, example texts in `prompts_frozen.md`.

- **Histories:** 16 hash-ranked opening triples extended to ten-roll paths; rolls 4–10; 4 families (28 histories) development, 12 families (84) confirmation; ranks 5–8 (28 histories) are the scaffold/replication subset.
- **Words:** 6 development and 6 confirmatory pairs (24 words), rendered "a shape described as {word}"; neutral "a shape"; longer neutral "a shape with no further description".
- **Core:** associations, both references on the constructed bank, plain T1 (26 descriptions × 112 histories), T2 (14 × 28), three scaffold levels (7 × 28 each), identity (7 × 28), worked examples.
- **Extensions:** factual descriptions, objects and combinations, incidental card words, cued direct generation, openings, natural histories, factual attribution, verbal distributions, free sequences.

## Primary estimators

`gain(p,t,w) = D(F_neutral, G_t) − D(F_w, G_t)`; `S(p,w) = gain(p,p,w) − gain(p,other,w)`; `A(p,w)` = mean over eight prompts of log p(SELF letter) − log p(OTHER letter); `a = A(p,left) − A(p,right)`.

1. **Directional association test:** `sign(a) × [S(p,left) − S(p,right)]`. Ties contribute zero.
2. **Own improvement:** `gain(p,p,w)` for the more self-associated word (tie: mean of both).

T1 plain, 6 confirmatory pairs, 84 confirmatory histories; histories averaged within family, families equally, pairs equally; per checkpoint and equally weighted joint. 95% percentile interval over 10,000 two-way bootstrap draws (families and pairs, shared indices, PCG64 seed 241124); leave-one-pair-out and leave-one-family-out ranges. The neutral cancels from estimator 1 and matters only for estimator 2.

Interpretation follows the table in handoff section 6. No test supports a population claim about adjectives or model families.

## Order and stop rules

Each model: archival G/F replay against Experiment 28 (identical output, six-face |Δp| ≤ 0.01, bit-identical repeats), vocabulary scan (no variant digit tokens), boundary instrumentation at the empty prefix and after `5 2 6` (the separator is the argmax before each face boundary; incremental vs full pass ≤ 0.25), teacher-forced own path vs generation (≤ 1e-4 nats). Then associations are collected, scored, written and hashed **before any dice row** (`association_seal.json`). Then references and forecasts. 64 forecasts and all core reference streams are re-scored for bit identity. Any failure stops collection. Core conditions with median valid-face mass below 0.50 are flagged; the primary analysis keeps all technically valid rows and a high-mass sensitivity table is reported.

## Choices the handoff left open (fixed here)

| Item | Choice |
|---|---|
| Typographic quotes/apostrophes in the handoff | rendered as ASCII |
| `<BEGIN ORIGINAL INSTRUCTION>` / `<END …>` | literal text; only G, subject, scaffold line and prefix are substituted |
| Prefix and "none" | followed by a full stop, as in the template |
| Exact public checkpoint name | the Hugging Face id. The names contain digits ("3", "32"), a limitation of the named arms |
| `Agent` order factor | which agent is listed first; label factor: which agent is A; crossed (8 prompts per word and agent pair) |
| Fact items with both/neither | four options with the label order rotated (4 rotations), for two agent pairs |
| Cued direct generation | `For this task, the roller is <subject>.` + newline + G |
| Verbal and free readouts | T1 with only the final command replaced |
| "Exactly six numbers" | any reply containing a different count of numerals fails, including labelled lists ("1: 20%") |
| High-mass sensitivity | keeps a history only if the neutral and both words of the pair have mass ≥ 0.50 |
| Worked history `5 2 6` | it is the opening triple of confirmatory family c09, so it counts once, as a confirmatory history; its worked-example plot reuses those rows |
| Natural-history unit in the small extension tables | unique prefixes, equally weighted; no bootstrap |
| Stored top tokens | 5 |
| Spend | the investigator authorised the run end to end without further questions and set no cap; a hard cap of $15 is self-imposed |
