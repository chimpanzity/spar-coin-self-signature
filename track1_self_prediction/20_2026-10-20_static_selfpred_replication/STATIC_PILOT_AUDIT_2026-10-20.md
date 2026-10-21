# Static self-prediction pilots: audit against logs

**Date:** 2026-10-20
**Audits:** Part I §2 ("Aim and current observations") of the 2026-10-20 combined handoff, *SPAR Research Handoff: Static Self-Prediction and Strategic Self-Play*.
**Sources:** Run directories under `data/spar_dynamic/`:

| Pilot | Run | Models | Calls per cell |
|---|---|---|---|
| Dice v3.1 | `dice_pilot/dicepilot-20261015T193746Z` | Astra, Fable, Qwen3-32B | 10 sequences; 10 hypotheticals per position per config |
| Dice ext | `dice_pilot_ext/dicepilotext-20261015T233304Z` | OSS-120, OSS-20, Sonnet 5.5 | 5; 5 |
| Dice v4.1 | `dice_pilot_v41/dicepilotv41-20261016T030505Z` | all six | 5; 5 |
| Favorite integer | `favorite_integer/favint-20261016T054030Z` | Astra, Fable, OSS-120 | 5; 5 |
| Favorite animal | `favorite_animal/favanim-20261016T103809Z` | Astra, Fable, OSS-120 | 5; 5 |
| Favorite animal, crossed | `favorite_animal_crossed/favanimx-20261016T142226Z` | Astra, Fable, OSS-120 | 5 per target per position |

All counts below are recomputed from the CSVs in those directories, not taken from the pilot reports.

## 1. Corrections to the handoff

### 1.1 Dice: no "7" appears; the default is 4

The handoff says hypothetical dice requests "often collapsed onto repeated defaults (described as `4` or `7`)". None of the 255 parsed dice hypotheticals is a 7. Every value is an integer from 1 to 6.

The "7" comes from the **favorite-integer** pilot. There, Astra predicted 7 as the first digit of its favorite integer in 5 of 5 calls, but its actual answer was always `3141592653`. The report calls this the "lucky 7" default. The dice wording in the handoff mixes the two tasks.

### 1.2 Animal: Astra fails, Fable succeeds

The handoff reports only Astra. The full result is:

| Model | Object level (5 calls) | Hypothetical letters, 5 calls each (first / second / penultimate / last) | Correct |
|---|---|---|---|
| Astra | octopus ×5 | d×5 / a×5 / a×4, i×1 / t×5 | 0/20 |
| Fable | octopus ×5 | o×5 / c×5 / u×5 / s×5 | 20/20 |
| OSS-120 | elephant ×5 | mostly "dog"-consistent letters (exposed reasoning) | 6/20 |

All three models reproduced their animal perfectly when asked to write out the full hypothetical response.

The crossed pilot shows the reverse pattern. Asked about another named model, Astra got 17/20 letters of Fable's "octopus" right. Fable declined 20/20 times when asked about Astra.

This is a **two-model dissociation**, not a general failure of hypothetical self-prediction. One caveat: the only Fable reasoning trace that OpenRouter exposed (1 of 20; the rest were hidden at `R_min`) spells out "octopus" before extracting the letter. Fable's success may therefore come from reconstructing the word internally, not from predicting a property directly.

## 2. Findings the handoff does not mention

### 2.1 The dice "default" is position-invariant and coincides with the true first roll

For Astra, Fable and Sonnet, the hypothetical answer is mostly 4, regardless of which position (1, 2, 5, 9) is asked about. Per run, 4 makes up 33/40 (Fable, v3.1) to 40/40 (Astra, v3.1) of parsed answers. Their object-level sequences usually **start** with 4 (Astra 14/15 across v3.1 and v4.1; Sonnet 10/10). Astra and Sonnet rarely have a 4 at positions 2, 5 or 9. Fable has a 4 at position 9 in 4 of 15 sequences.

So position-1 "accuracy" for these models is the default answer landing on the truth. Position-1 accuracy should not be read as evidence of self-prediction unless it beats a position-invariant default baseline. The generic comparator and single-roll controls in the frozen protocol are designed to estimate that baseline.

### 2.2 The object-level distributions are very peaked

Within a run, the same position often has the same value in every call. For example, Astra's position 2 was 1 in 9/10 v3.1 sequences and 5/5 v4.1 sequences. Astra and Fable don't accept a temperature setting on OpenRouter (the catalogue excludes it), so these calls used provider-default sampling with `reasoning.effort = minimal`.

Separate calls are therefore not guaranteed to give independent draws from a broad distribution. With 100 calls per cell, most cells will probably be nearly constant. Divergence and calibration analyses need to handle near-zero-entropy distributions, for example with Jeffreys-smoothed total variation and exact or bootstrap uncertainty.

### 2.3 Parse compliance depends on the prompt wording

| Model | Dice v3.1 wording ("What would the *k*th integer in your response be?") | Dice v4.1 wording ("Your response … would be one specific string … What is the *k*th integer?") |
|---|---|---|
| OSS-120 | 19/20 ok, 1 decline | 6/20 ok, **14 declines** |
| OSS-20 | 20/20 ok | 10/20 ok, 9 declines, 1 invalid |
| Qwen3-32B | **20/40 invalid** (R0/R1 configs) | 20/20 ok (`R_qwen_default`, reasoning disabled) |

Astra, Fable and Sonnet parsed 100% under both wordings. For the open-weight model, the parse-compliance gate in the handoff has to be checked against the exact frozen wording, not carried over from an earlier pilot.

### 2.3a The pilots' Qwen "reasoning off" runs were not reasoning-free

The config label `R_qwen_default` reflected the fact that disabling was never verified. Tested on 2026-10-20, Qwen3-32B on DeepInfra (the pilots' provider) produced about 1,200 reasoning tokens per call despite `reasoning.enabled = false`. `effort = "none"` and `chat_template_kwargs.enable_thinking = false` made no difference. SiliconFlow and Tenstorrent returned 0 reasoning tokens with `enabled = false`.

The replication runs Qwen on SiliconFlow at temperature 0, with reasoning off and with reasoning effort high. Both settings passed the parse check on the draft prompts (`data/spar_dynamic/static_selfpred/parsecheck-qwen-20261021T000345Z`): 140/140 and 137/140 usable, no tool calls, no truncation. Of the 3 unusable high-reasoning answers, two said the value can't be determined and one wrote Python code for a die roll as text. The dice parser classes all three as `prefix_leak` because they contain several digits.

### 2.4 The handoff's dice positions differ from the pilots

The handoff suggests positions 2, 6, 7 and 10. All pilots used 1, 2, 5 and 9. Switching loses comparability with the pilots, and position 1 is the most informative position for separating a default answer from self-prediction (§2.1). The frozen draft keeps 1, 2, 5 and 9. This is an open decision.

### 2.5 The crossed pilot does not settle the generic-retrieval question

The crossed report says Fable's declines rule out "semantic retrieval". But a refusal to predict another model is not evidence against generic retrieval. It is missing data. The handoff's generic comparator ("a typical language model") could hit the same refusal in Fable, so the frozen draft records declines as their own category and adds a name-elicitation version of the comparator, which is less likely to be refused.

## 3. What stands

- Astra and Fable both give a stable "octopus" (5/5 each). OSS-120 gives "elephant" (5/5).
- All three models reproduce their full name or sequence perfectly in the reenactment condition.
- Astra's hypothetical single-property answers are stereotyped and wrong for the animal task, and position-invariant for the dice task.
- Qwen's parse failures are real and depend on the configuration.

These are pilot observations with 5–10 calls per cell. None are replication findings.
