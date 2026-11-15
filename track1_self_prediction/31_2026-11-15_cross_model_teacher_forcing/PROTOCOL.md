# Experiment 31: cross-model teacher-forced continuation probabilities (frozen protocol)

`SPAR_EXP31_CROSS_MODEL_TEACHER_FORCING_v1.0`. Design source: `GPT_SPAR_Experiments_31_32_Revised_Claude_Code_Handoff.md`
(2026-11-15). Written and frozen before any GPU call. Companion: [Experiment 32](../32_2026-11-15_roll7_intermediate_context/PROTOCOL.md)
shares the rental, engine and scoring utilities but has its own folder, manifest, raw records, analysis and report.

## Questions

Holding the exact instruction and the prior authentic rolls fixed:

1. How similarly do Qwen3-32B and Mistral Small 3.2 score the next face?
2. Does switching the scorer's instruction between G and F change its conditional distribution on the same prefix?
3. Does each scorer assign more likelihood to its own model's authentic trajectory than the other scorer does, and does any
   such effect survive under F as well as G?
4. How much of the apparent accuracy is explained by the generic rule "use each of the six faces before repeating"?

## Claims boundary

- Close conditional distributions do not show identical internal computation.
- Model-specific likelihood alignment is not, by itself, privileged access.
- Rescoring a model's own deterministic greedy output under its original prompt (own G-on-G and own F-on-F) is a replay. It
  is expected to fit well, is an engineering check, and is **not** evidence of introspection.
- Four source sequences are fixed examples, not independent replications. No p-values, no intervals, no population claims.

## Ground truth (verified at freeze, and again before every run and in the checks)

The four ten-roll sequences are re-read from Experiment 28's raw main records
(`28_.../main/{qwen,mistral}/raw_attempts.jsonl`). Each has 20 replicates with identical content, the pinned checkpoint and
the archived prompt hash. They agree digit for digit with the handoff's provisional table, including Qwen G, which some
older project notes transcribe differently. No change was needed.

| Source | Instruction | Rolls 1-10 |
|---|---|---|
| Qwen | G | `5 2 6 3 1 4 6 2 5 3` |
| Qwen | F | `3 1 4 6 2 5 3 2 6 4` |
| Mistral | G | `4 2 6 1 3 5 2 4 6 1` |
| Mistral | F | `3 1 5 2 6 4 3 1 5 2` |

## Models and serving (Experiment 28 exactly)

- **Qwen:** `Qwen/Qwen3-32B` @ `9216db5781bf21249d130ec9da846c4624c16137`, Qwen3 chat template (sha `a55ee1b1…`),
  `enable_thinking=False`.
- **Mistral:** `mistralai/Mistral-Small-3.2-24B-Instruct-2506` @ `95a6d26c4bfb886c58daf9d3f7332c857cb27b43`, mistral_common
  tekken v11 (sha `6e250168…`), text path only.
- **Engine:** Experiments 27-30's (`dice_crossed_guidance.models`), unchanged: bf16 weights and activations, fp32 output layer
  and logits, batch 1, KV cache, full-vocabulary log-softmax.
- **Context:** greedy, no sampling, no logit processors, no system message, no tools, one user message, fresh context per
  call.
- **Host:** one A100-80GB on vast.ai, one checkpoint loaded at a time, no hosted API.
- **Package pins:** torch 2.11.0+cu128, transformers 5.22.0, accelerate 1.15.0, huggingface_hub 2.4.0, mistral_common
  1.13.0.

Any incompatibility in checkpoint, template or tokenizer stops the affected model; nothing is substituted.

## Design: 160 labeled rows

Scorer (Qwen, Mistral) × source model (Qwen, Mistral) × source instruction (G, F) × scorer instruction (G, F) × position 1-10
= 160 rows, 80 of them cross-model.

- **User turn:** the scorer's archived G or F instruction, byte-exact (sha `edc7a4a2…` / `8adcaddf…`). It is the only user
  turn.
- **Forced assistant turn:** at position j, the source's authentic rolls 1..j−1, rendered exactly as Experiment 28's output
  (`d d d`, single spaces) and tokenised by the scorer. Both tokenizers give face, space, face, … with single bare-digit
  face tokens; tested on the real tokenizers.
- **Scored boundary:** the six face log-probabilities directly after the forced prefix: after the separator, before roll j.
  Position 1 is scored directly after the assistant prefix (empty history).
- **Teacher forcing:** the stream advances with the source's authentic roll j, never the scorer's preferred face.
- **No identities:** model names appear only in record metadata.

**Computation.** Each of the 16 (scorer, scorer instruction, source trajectory) streams is one teacher-forced pass that yields
positions 1-10.

- Arithmetic: `incremental` is primary (the prompt prefilled once, then one forced token at a time through the KV cache).
  This is the arithmetic of greedy generation and of Experiment 28's matched-prefix scoring.
- Determinism: the incremental pass is computed twice and must be bit-identical.
- Floor: `full_pass` (one forward pass) is the numerical floor only.

**Shared contexts.** The 160 labeled rows map onto 140 unique contexts. All position-1 rows of a scorer and instruction share
the empty prefix, and the two F sources share `3` and `3 1`. Identical contexts must produce identical scores.

**Archival equivalence (handoff 31.2).** All 160 rows are computed fresh on the pinned stack, rather than mixing in archived
values. Two archives hold exactly equivalent records (same pins, rendered prompt, forced history, incremental arithmetic and
bare-digit boundary):

- Experiment 28's within-model matched-prefix rows: 80 rows.
- Experiment 30's authentic policy rows: 24 cross-model rows with scorer instruction = source instruction, positions 1-6.

These 104 equivalents are cross-checked within 1e-4 nats and listed per row as provenance. Experiment 29's completion wrapper
is not eligible. The remaining 56 rows have no archival equivalent.

## Measurements per labeled row

- Six raw face log-probabilities and their token ids.
- Digit mass (raw full-vocabulary mass on the six faces).
- Six-face-normalised p1..p6.
- Scorer top face, top-two margin, and a near-tie flag (margin < 0.02).
- Authentic rank, p(authentic) and log loss −ln p(authentic) in nats. **Log loss is the primary quantity.**
- Diagnostics: the full-vocabulary argmax token, separator log-probability, EOS log-probability, top-10 tokens and entropy.
- Provenance: forced prefix text and ids, prompt and rendered-prompt hashes, model checkpoint.

Raw mass is never treated as a face probability.

## Prespecified comparisons

**A. Crossed own-model likelihood table.**

- For each source trajectory and scorer instruction, both scorers are scored on the same authentic faces at the same
  positions. The table reports mean log loss over positions 2-10 (position 1 separately) and own minus other.
- Reciprocal contrast per (source instruction, scorer instruction): own advantage = mean over the two source models of
  (other scorer − own scorer) log loss. Positive means own-model alignment.
- **Replay cells are marked:** own G-on-G and own F-on-F. The two G/F-mismatched contrasts (own scorer under the other
  instruction) contain no replay cell and are the informative own-model tests.
- The figure shows the 4 × 4 matrix: source path × (scorer, scorer instruction).

**B. Matched-context distributions.**

- JS divergence (bits) and top-face agreement between the two scorers on the same instruction and prefix.
- Within a scorer: JS(G vs F instruction) on the same prefix, with the authentic-rank change.
- Digit mass is reported beside each comparison, never mixed into the distribution comparison.

**C. Opening vs continuation.** Position 1 is reported separately from positions 2-10. Per-position JS and log loss are
plotted rather than only averaged.

**D. Generic remaining-face diagnostic** (no extra GPU calls). This is a diagnostic decomposition, not a claim about the
models' internal rule.

- **Positions 2-6:** remaining = {1..6} minus rolls 1..j−1.
- **Positions 7-10:** a clearly labelled six-position reset heuristic: remaining = {1..6} minus rolls 7..j−1. It is applied
  only when rolls 1-6 are a complete permutation, which holds for all four sources; otherwise it is omitted as ambiguous.
- **Position 1:** an opening with no rule. Position 7 is unconstrained (six remaining).
- **Per row:** the number remaining, the model's normalised mass on the remaining faces, whether the authentic face is among
  them, and p(authentic) renormalised over the remaining set (only when it is in the set and the set is non-empty).
- **Uninformative rows:** when one face remains (always position 6 here), the renormalised probability is 1 by construction.
  These rows are labelled uninformative.
- **Discriminating rows:** 2-5 eligible faces, authentic among them. For these rows the summary compares model log loss with
  the uniform-over-remaining heuristic, ln(n). Comparison A is repeated on discriminating rows only.
- Absolute conditional log loss stays the primary result.

## Checks (`python -m spar_dynamic.dice_31_32 checks`; handoff preflight tests 1-8)

- **Ground truth and serving:** ground truth equals Experiment 28. Serving identity (checkpoint, template and tekken hashes)
  matches. The vocabulary scan finds no whitespace-prefixed or variant face tokens.
- **Archival regeneration:** G and F are regenerated twice per model on the host. Each must be identical to Experiment 28 (six-face |dp|
  <= 0.01, bit-identical repeats, G face mass >= 0.5); this is a stop rule, run before any Experiment 31/32 call.
- **Completeness:** prompt hashes match the frozen ones. All 48 stream records and 160 labeled rows are present (80 cross).
- **Numerical validity:** values are finite and mass is in [0, 1]. Normalised sums are 1, and log-probabilities agree with
  probabilities. JS is zero for identical distributions and stays within [0, 1].
- **Indexing:** position j sees exactly j−1 authentic faces and never the target.
- **Determinism:** identical contexts give identical scores, and replicates are bit-identical.
- **Floor and archive:** the incremental vs full-pass floor is <= 0.25 (larger values are flagged). Archival equivalents
  agree within 1e-4 nats.
- **Files:** raw-file hashes match the env records.

## Stop rules and reporting

- A model that fails the vocabulary scan or the archival check stops before scoring, and its rows are reported as not run.
  Checks that fail after collection are reported, never fixed by changing the design.
- There is no prompt search and no added prefixes. Any extension is a separately labelled experiment, not part of this run.

## Outputs

- `raw/<model>/`:
  - `streams.jsonl`: 16 streams × 3 records, each with every position's full record.
  - `archival.jsonl`.
  - `env.json`: environment, vocabulary scan, archival check and file hashes.
- `results/`: labeled rows CSV, crossed and reciprocal tables, JS tables, heuristic tables, `summary.json`, `checks.json`.
- `figures/`:
  - Experiment 28-style six-face heatmaps on the other model's and on its own G and F paths.
  - The crossed likelihood matrix, with replay cells hatched.
  - Per-position JS.
- `REPORT.md`, plus `run_record.json` with the instance, cost, commits and hashes.
