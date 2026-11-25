# Experiment 35 protocol: can a prompt scaffold help a model skip ahead to roll 7?

Tag `SPAR_EXP35_ROLL7_PROMPT_SCAFFOLDING_v1.0`. Design source: `docs/handoffs/GPT_SPAR_Roll_7_Prompt_Scaffolding_Handoff.md` (exploratory pilot, follow-up to Experiment 32). Frozen before any model call. Where this file is silent, the handoff governs.

## Design

- Two fixed prefixes (Experiment 28 greedy G outputs, rolls 1-5): Qwen `5 2 6 3 1` (true 6th 4, true 7th 6); Mistral `4 2 6 1 3` (5, 2). Targets are used for scoring only.
- Six endings (B, GAP, SLOT, THINK, INFER, IMAGINE), exact text in `prompts_frozen.md`. Both predictors get identical bytes.
- 36 cells: 2 predictors x 2 sources x 6 endings in standard mode (24), and Qwen native thinking x 2 sources x 6 endings (12). Two fresh greedy replicates each (72 calls).
- Same checkpoints, engine, templates and scoring as Experiment 32 (imported, unchanged). No system message, no tools, greedy.

## Stop rules before the grid (per model)

Vocabulary scan finds no variant face tokens; Experiment 28 G and F archival replay passes (identical outputs, six-face |dp| <= 0.01, identical repeats); both Experiment 32 B prompts replay with identical prompt ids, identical output and six-face |dp| <= 0.01. Bit identity is also recorded.

## Readouts

- **Free answer.** Strict rule: the final-answer text must be exactly one digit 1-6 and generation must end by itself. Classified as true seventh, true sixth, another face or invalid. No digit is extracted from prose. Standard-mode budget 128 tokens (Experiment 32).
- **Distribution.** The six bare face log-probabilities at the first final-answer token, digit mass, six-face-normalised probabilities, rank of the true seventh, and log P(true 7) - log P(true 6).
  - *Standard mode:* the first assistant token (for Qwen, after the template's empty think block and its `\n\n`).
  - *Thinking mode:* the first non-whitespace token after the first generated `</think>`. The template's `\n\n` is the only text removed before the strict rule; any other whitespace is labelled. The distribution is conditional on the generated thinking. If there is no boundary, it is missing.
- **Thinking budget:** 1,024 generated tokens (primary, as specified).

## Addition to the handoff

Cells truncated at 1,024 tokens are primary missing/invalid, as specified. After the primary run they are also run once on the same greedy path with a 4,096-token budget: same prompt, sampler and template, no forced tokens. These go to a separate file and table labelled supplementary, never replace the primary cell, and must reproduce its first 1,024 tokens. Reason: the cost is small and a truncated arm would otherwise carry no information.

## Analysis

Descriptive only, replicate 1 (replicates must be bit-identical; any difference is reported). Each variant against B within model, prefix and mode; Qwen thinking against standard within ending; counts of recurrence across the cells. Experiment 32 A and C are anchors. No p-values: two fixed sequences. A correct roll 7 does not show internal representation of roll 6, and leaving the sixth-roll answer is not itself success. No wording ablations are run here.

## Cost

vast.ai A100-SXM4-80GB, estimate $2-4; self-imposed hard cap $10. The instance is destroyed after the raw files are copied and hash-checked.
