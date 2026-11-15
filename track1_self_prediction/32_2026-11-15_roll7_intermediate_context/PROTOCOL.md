# Experiment 32: seventh-roll prediction with and without the sixth roll (frozen protocol)

`SPAR_EXP32_ROLL7_INTERMEDIATE_CONTEXT_v1.0`. Design source: `GPT_SPAR_Experiments_31_32_Revised_Claude_Code_Handoff.md`
(2026-11-15). Written and frozen before any GPU call. It shares the rental, engine, serving pins, ground truth and archival
preflight with [Experiment 31](../31_2026-11-15_cross_model_teacher_forcing/PROTOCOL.md), whose protocol also lists the
models and serving. It has its own folder, manifest, raw records, analysis and report.

## Question

Given five authentic rolls, how does a predictor's probability for the authentic seventh roll change across three conditions?

- **A:** the predictor first outputs a sixth roll, then the seventh.
- **B:** it forecasts the seventh directly.
- **C:** it is given the authentic sixth roll.

Is any pattern stronger when the predictor is the source's own model? Condition C separates the effect of having the correct
intermediate history from the effect of generating one's own intervening guess. It does not isolate latent simulation,
because wording and context length also differ.

## Claims boundary

- These are two fixed source examples evaluated under tightly controlled contrasts. There is no inferential test and no
  population claim.
- A correct seventh roll does not establish latent self-simulation. Good performance on the predictor's own G sequence under C
  may be ordinary conditional continuation.

## Fixed design: 12 cells

Predictor (Qwen, Mistral) × source (Qwen G, Mistral G) × condition (A, B, C). Both predictors receive byte-identical prompts.
The targets were verified against the Experiment 28 raw records; they agree with the handoff and were not changed.

| Source | Rolls 1-5 | Authentic 6th | Authentic 7th |
|---|---|---:|---:|
| Qwen G | `5 2 6 3 1` | 4 | 6 |
| Mistral G | `4 2 6 1 3` | 5 | 2 |

In both examples rolls 1-5 are five distinct faces, so a generic missing-face rule predicts roll 6. These prefixes stay fixed
regardless, and no alternative examples will be chosen.

## Prompts (byte-exact; see `prompts_frozen.md`)

The wrapper is new and saved verbatim. The archived G instruction is substituted unedited. There is no trailing newline.

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
{G}
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: {prefix}
{ENDING}
```

- **A:** `Predict rolls 6 and 7 of that response. Return exactly two integers separated by a single space, with no other text.`
- **B:** `Predict roll 7 of that response. Return exactly one integer, with no other text.`
- **C:** the prefix line becomes `The first six rolls it produced were: {prefix} {authentic_sixth}`, followed by B's ending.

The true seventh roll never appears in any input. No model names, labels or file names appear in any prompt.

## Scoring

Each cell is a fresh context. Free greedy generation (max 128 new tokens) runs twice per prompt and model, and the two runs
must be bit-identical. Every record stores:

- the raw free text, finish reason and token ids;
- at the scored boundary: the six raw face log-probabilities, digit mass, six-face-normalised p1..p6, top face, rank, p(true)
  and −ln p(true), plus separator and EOS log-probabilities, top-10 tokens and entropy.

**Validity is strict:** A requires exactly `d d` then EOS; B and C require exactly `d` then EOS. Prose is invalid and no digit
is extracted from it.

**Scored boundaries by condition:**

- **B and C:** roll 7 is scored at the first answer token. This is the same distribution greedy generation uses at step 1,
  and it is checked bit-for-bit.
- **A, roll 6:** scored at the first answer token. The record keeps p(true sixth), the generated sixth, and whether it equals
  the authentic sixth.
- **A, roll 7 (free, primary):** scored after the predictor's own generated sixth digit and the exact separator token, never
  after the authentic sixth. This readout exists only when the free output starts with a digit followed by the separator;
  otherwise it is undefined (invalid).
- **A, roll 7 (constrained-digit readout, always computed, labelled separately):** the predictor's highest-probability first
  face and the separator are forced, then roll 7 is scored. When the free readout exists it must equal this readout bit for
  bit. When free output is prose, the constrained readout is reported under its own label and never substituted silently.

**Numerical floor:** the `full_pass` arithmetic for each first boundary and constrained readout.

**Tokenisation:** a one-digit answer is a single bare-digit token whether it starts the response or follows a space. No
whitespace-prefixed face token exists. The vocabulary scan and real-tokenizer tests check this. EOS and separator
log-probabilities at each boundary are recorded so that format handling can be audited.

## Prespecified contrasts (per predictor × source)

All three contrasts use p(authentic seventh), with raw p and log loss alongside. A uses the free readout; the A-constrained
variants are also reported.

- **A − B:** the effect of requesting and outputting an intermediate forecast. It includes the influence of the predictor's
  chosen sixth.
- **C − B:** the effect of receiving the correct intervening history in a slightly modified prompt.
- **C − A:** authentic versus self-generated intervening history. This is not an isolated causal history effect, because the
  prompts and response positions differ.
- **A sixth correctness:** whether A restored the authentic sixth. This is stratified descriptively and never pooled when it
  is wrong.

Both predictors' scores on the identical target are shown before any same-model statement. Digit mass appears in every row:
normalised probabilities are conditional on a face being emitted, and Mistral often answers prediction prompts in prose
(Experiments 27-29).

## Checks (`python -m spar_dynamic.dice_31_32 checks`)

- **Shared preflight:** the archival checks from Experiment 31 pass.
- **Completeness:** prompt hashes match the frozen ones; there are 24 records and 12 cells; both predictors received identical
  stimuli.
- **Prompt content:** no leakage. B shows five rolls and C six (the authentic sixth).
- **A's readouts:** A is scored after the predicted sixth, and the constrained path is present.
- **Determinism and agreement:** replicates are bit-identical. The first boundary equals generation step 1. The constrained
  readout equals the free readout whenever the free one is defined.
- **Numerical:** values are finite, and the full-pass floor is <= 0.25.

## Outputs

- `raw/<model>/cells.jsonl`: 6 prompts × 2 replicates, with full generations and readouts.
- `raw/<model>/env.json`: points at Experiment 31's `archival.jsonl` for this model.
- `results/`: `cells_12.csv`, `contrasts.csv`, `summary.json`, `checks.json`.
- `figures/fig32_roll7_by_condition`: paired/triad p(true 7) by condition, faceted by source, one series per predictor,
  marked exploratory.
- `REPORT.md` and `run_record.json`.

The optional later extension in the handoff (more prefixes chosen before seeing outcomes) is **not** part of this run.
