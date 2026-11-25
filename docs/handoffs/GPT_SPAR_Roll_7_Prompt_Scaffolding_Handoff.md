# SPAR · Can a prompt scaffold help a model skip ahead to roll 7?

Run this small exploratory follow-up to Experiment 32, page 4 of the Nov. 15 SPAR update. Reuse the original open-weight Hugging Face checkpoints and Vast GPU workflow. Experiment 33's adjective cues and Experiment 34's unused-face work are separate. Use a new experiment directory and leave frozen runs unchanged.

## Question and fixed examples

The model sees rolls 1–5 and returns **only** roll 7. Can acknowledging the missing sixth position, imagining its value, or thinking through the continuation improve prediction? In Experiment 32, all four predictor × source combinations returned the authentic sixth face when asked for roll 7. Writing a sixth-roll answer first raised the true-seventh probability in all four combinations, but did not yield a correct seventh-roll top choice.

| Source (metadata only) | Rolls shown | True roll 6 (scoring only) | True roll 7 (scoring only) |
|---|---|---:|---:|
| Qwen direct generation | 5 2 6 3 1 | 4 | 6 |
| Mistral direct generation | 4 2 6 1 3 | 5 | 2 |

Cross both sources with both predictors. Exact weights from Experiment 32:

- `Qwen/Qwen3-32B` at `9216db5781bf21249d130ec9da846c4624c16137`.
- `mistralai/Mistral-Small-3.2-24B-Instruct-2506` at `95a6d26c4bfb886c58daf9d3f7332c857cb27b43`.

Use the same bf16 engine and model-specific chat templates, blank system context (no system message), no tools, and greedy decoding. Reuse `src/spar_dynamic/dice_31_32/` and its scoring utilities where practical. Start with Exp. 32's archival/serving check and reproduce the exact B outputs and face probabilities within its established tolerance before interpreting any differences. Never pass the held-out values, source labels, or any examples containing answers into the experimental inputs.

## Prompt conditions

Each prompt begins with this exact block. Substitute only `{prefix}`. One user message, LF newlines, no trailing newline.

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: {prefix}
```

Append the following endings on a new line. Every ending ends with the same one-integer instruction. No instructions about symmetry, uniformity, or using each face once.

| ID | Exact ending |
|---|---|
| B · baseline | Predict roll 7 of that response. Return exactly one integer, with no other text. |
| GAP · position only | Roll 6 is not shown. Predict roll 7 of that response. Return exactly one integer, with no other text. |
| SLOT · explicit blank | Roll 6: [blank]. Roll 7: [predict this position]. Predict roll 7 of that response. Return exactly one integer, with no other text. |
| THINK · generic deliberation | Think through your prediction carefully before answering. Predict roll 7 of that response. Return exactly one integer, with no other text. |
| INFER · infer 6, use it | First consider what the instance would have produced for roll 6. Use that estimate to predict roll 7 of that response, without outputting your estimate for roll 6. Return exactly one integer, with no other text. |
| IMAGINE · simulate both | Imagine continuing the same simulated die-rolling response for two more rolls, in order. Keep the first imagined roll (roll 6) to yourself. Predict roll 7 of that response using the second imagined roll. Return exactly one integer, with no other text. |

## Reasoning manipulation

- **Both exact checkpoints, standard mode:** run all six endings (24 cells total).
- **Qwen, native thinking enabled:** run the same six endings on both prefixes with `enable_thinking=True` (12 additional cells). Keep greedy decoding so the comparison changes the mode, not sampling. Give the thinking run up to 1,024 generated tokens. Record whether thinking opened and closed, whether the final answer appeared, and any truncation. Score the final answer after the actual thinking block closes, not the first token of the thinking block and not a forced closing marker. Use the normal Qwen template behavior in each mode. If no thinking or final answer is observable, mark that explicitly. Do not silently retry with a changed prompt, forced digit, or different sampler.
- **Mistral Small 3.2:** the original Instruct checkpoint does not have an equivalent native thinking toggle. THINK and IMAGINE still test prompt scaffolding. Do not swap in a reasoning-tuned model and call it a within-checkpoint comparison.
- Expected 36 cells, two fresh greedy replicates (72 calls), plus archival preflight. Store prompt hashes and exact decoded outputs. Use original Exp. 32 A and C scores as descriptive anchors for emitted and supplied roll 6.

## Readouts and report

1. For each predictor × source × condition × mode, record the freely produced final face and classify it as true seventh, true sixth, another face, or invalid. Apply Exp. 32's strict one-digit answer rule to final-answer text, excluding only the native thinking block and template-defined structural tokens. Never extract a digit from prose.
2. Score all six raw face log-probabilities at the first final-answer token. Also store total digit probability, six-face-normalized probabilities, rank of the true seventh, and the margin log P(true 7) minus log P(true 6). Record an unavailable answer boundary as missing, and label any differences in answer-position whitespace handling. For thinking mode this distribution is conditional on the generated thinking prefix, not a marginal probability over all possible thinking paths. A model can shift the digit distribution but still give an invalid answer.
3. Compare each variant against B within the same model, prefix, and mode. Compare Qwen thinking on/off within each identical ending. GAP/SLOT versus INFER/IMAGINE separates making the slot explicit from instructing the model to use a guessed sixth. THINK is the control for generic deliberation. If a rich prompt helps, inspect the simpler variants first and only then consider smaller wording ablations.
4. Report per-cell results, the exact controls, and a short summary of whether gains recur across prompt forms. Treat this as a pilot using two fixed sequences. A correct roll 7 does not show that the no-thinking model represented roll 6 internally, and escaping the roll-6 answer alone is not success. Keep reasoning-enabled results separate from any claim about no-output computation.

## Before reporting completion

Verify both baseline prompt hashes against `prompts_frozen.md`, the 36-cell grid, replicate agreement or any deviations, six-face probability calculations, and mode/answer-boundary handling. Save the frozen prompt manifest, raw records, per-cell CSV, and short report. Report any unrunnable or truncated cells and the actual rental cost, if applicable.
