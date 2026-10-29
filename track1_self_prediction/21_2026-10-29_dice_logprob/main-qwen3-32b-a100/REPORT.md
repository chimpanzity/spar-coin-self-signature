# DICE_LOGPROB_v1.0: direct generation vs hypothetical self-prediction in Qwen3-32B output probabilities

**Run:** `main-qwen3-32b-a100`, 2026-10-29. **Model:** Qwen3-32B open weights (commit `9216db57…`), bf16 with fp32 output layer, greedy decoding, non-thinking chat template, one user message, no system message, no tools. **Hardware:** one A100-SXM4-80GB on Vast.ai, the same machine as the passed preflight. **Size:** 15 conditions × 10 fresh-context replicates = 150 generations, plus teacher-forced matched-prefix scoring. **Cost:** about $1.60 of GPU time for preflight and main run together.

Every number below can be recomputed offline from `raw_attempts.jsonl` and `matched_prefix.jsonl` with `python -m spar_dynamic.dice_logprob.analysis --run <this folder>`.

## 1. Technical diagnostics

| Check | Result |
|---|---|
| Valid numeric-only outputs | 150 / 150 |
| Reproducibility | Each of the 15 conditions gave the same output in 10/10 replicates, with **identical** probabilities (maximum spread 0). The replicates are reliability evidence, not independent observations. |
| Six-face coverage | Exact log-softmax over the full vocabulary, so all six faces are scored at every position (no top-k truncation). The faces hold ≥ 99.6% of next-token mass at every scored position; no tokenization ambiguity (digits and spaces are separate tokens). |
| Non-thinking | Template `enable_thinking=False`; no think text in any output |
| Numerical precision floor | Recomputing the same probabilities in one forward pass instead of token by token moves the six-face distribution by up to **0.09**. Faces closer than that are treated as **near-ties**: which one wins is not a robust property of the model. |

## 2. Observations

### 2.1 Reference sequences

| Position | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| **G** (direct generation) | 5 | 2 | 6 | 3 | 1 | 4 | 6 | 2 | 5 | 3 |
| **F** (full self-prediction) | 3 | 1 | 4 | 6 | 2 | 5 | 3 | 2 | 6 | 4 |

- **G and F differ at 9 of 10 positions;** they agree only at position 8.
- **They are one sequence, offset by three positions.** F's positions 1–7 are exactly G's positions 4–10 (`3 1 4 6 2 5 3`). G reaches that run after the opening `5 2 6`; F starts with it. Of G's 9 adjacent pairs, 7 also occur in F.

### 2.2 Position 1: the only position where G and F are compared under the same (empty) history

| Face | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| G: probability among faces | .001 | .004 | .225 | .234 | **.535** | .002 |
| F: probability among faces | .226 | .308 | **.388** | .058 | .021 | .000 |

- **The distributions differ substantially:** Jensen–Shannon divergence is 0.52 bits (the maximum is 1).
- **G's choice is far from F's.** Under F, face 5 has probability .021 (rank 5 of 6).
- **F's choice is a moderate competitor under G.** Face 3 has probability .225 (rank 3).
- **F's own winner is a near-tie:** 3 (.388) vs 2 (.308), a margin of .08, below the .09 precision floor.

### 2.3 Later positions: natural trajectories vs matched prefix

In the natural trajectories, JS divergence stays high after position 1 (0.20–1.00 bits; figure `divergence_and_rank.png`). But each condition is continuing a *different* history, so this mixes the instruction's effect with the history's.

Matched-prefix scoring separates the two. The same assistant prefix is fed under both instructions, token by token through the cache, exactly as in generation:

| History fed as the prefix | Positions where the G and F instructions pick different faces | JS divergence, positions 2–10 |
|---|---|---|
| G's sequence | only position 1 | 0.00–0.09 (same top face at every position) |
| F's sequence | 1, 2, 3, 7, 8 | 0.00–0.32 |

- **Given G's history, the F instruction continues exactly as G does.**
- **Given F's history, the G instruction partly resists.** At positions 2 and 3 it prefers 5 and 6, while F's history has 1 and 4. At positions 7 and 8 it prefers 2 and 6, while F's history has 3 and 2. At positions 4–6, 9 and 10 it follows F's sequence.
- **None of these disagreements is a near-tie under the G instruction.** G's own preference beats F's face by .22–.70.

### 2.4 Single-position and window predictions (RQ2, RQ3)

| Condition | Output (aligned to original positions) | Matches G at | Matches F at |
|---|---|---|---|
| S(1)…S(10) | 4 4 5 5 4 4 4 4 5 4 | 6, 9 | 10 |
| W(1–5) | 4 2 6 3 5 | 2, 3, 4 | none |
| W(3–8) | 4 2 5 3 6 1 (positions 3–8) | 7 | 3 |
| W(5–10) | 3 6 2 5 1 4 (positions 5–10) | none | 10 |

- **Accuracy is low against both references.** Across the 27 position reports, 6 match G and 3 match F. A random face would match 4.5 of 27 by chance, and these deterministic outputs are not independent trials.
- **Asked for a single position, the model answers 4 or 5 whatever the position.** The answers at S3, S4, S5 and S8 are near-ties between the top two faces.
- **Partial reconstructions are inconsistent across scopes.** At the same original position, two prediction contexts report the same face in only 6 of 52 pairwise comparisons.
  - At position 5, five contexts give F 2, S(5) 4, W(1–5) 5, W(3–8) 5 and W(5–10) 3.
- **W(1–5) reproduces G's positions 2–4** (`2 6 3`), not F's.

## 3. Interpretations (what the data support)

1. **RQ1 (close or distant distributions?): neither pure "noisy recomputation" nor a wholly distinct policy.**
   - **The opening is distinct.** At position 1 the self-prediction framing moves probability away from G's choice: 5 drops from .54 to .02. This is not a near-tie crossing.
   - **The continuation is shared.** Once the prefix is fixed, the F instruction reproduces G's choices at every later position, with JS ≤ 0.09 bits. Most of the natural-trajectory divergence after position 1 is a cascade from different openings, as Ackerman suggested.
   - **The two sequences pass through the same run** (`3 1 4 6 2 5 3`), which suggests a strongly preferred continuation that both conditions reach from different starting points.
2. **The asymmetry needs care.** The G instruction resists F's early history at positions 2–3 more than the F instruction resists G's. That is consistent with direct generation having stronger opening preferences, but there are only two histories here, so it is descriptive.
3. **RQ2 and RQ3 (reconstruction):** single-position and window predictions do not reconstruct either reference and depend on the requested scope. They look like a default answer (4 or 5) for single positions and fresh partial generations for windows, not read-outs of a stable predicted sequence.
4. **Nothing here is evidence of privileged self-knowledge.** F's sequence is not G's sequence, and where F matches G after a matched prefix, that reflects shared continuation behaviour given identical context, not prediction.

## 4. Alternative explanations and limitations

- **Prompt wording and length.** F embeds G's instruction inside a longer wrapper. Any wrapper might shift the first-roll distribution. Without a non-self control (for example "another language model" or a neutral paraphrase), the opening shift cannot be attributed to the *self* framing.
- **One trajectory per condition.** Greedy decoding is deterministic, so this describes one path through each condition, not a population of model behaviours. With 10 positions and 2 histories, all comparisons are descriptive.
- **Serving configuration.** These results hold for bf16 open weights with this template and greedy decoding. SiliconFlow's fp8 API produced *different*, non-deterministic sequences in the earlier diagnostic, so precision and serving matter at near-ties.
- **Numerical floor (0.09).** It limits fine-grained claims: F's own position-1 winner and four single-position answers sit within it.
- **Six-face normalisation** is conditional on the die-face subset. Raw face mass is ≥ 99.6% throughout, so the conditioning changes little here.

## 5. Next decisions (proposals, not run)

| Question | Proposed follow-up | Cost |
|---|---|---|
| Is the position-1 shift specific to *self*? | Add non-self wrappers (generic model, neutral paraphrase) with the same structure, and compare first-roll distributions and matched-prefix behaviour | About $1 of GPU time on the existing pipeline |
| Is `3 1 4 6 2 5 3` a general attractor? | Force each possible first one or two faces and score the continuations under G and F | Same pipeline, minutes |
| How robust are near-ties to serving? | Re-score the same prompts in fp8 and/or on different hardware | Small |
| Recognition task / reasoning-on arm | Still deferred per the handoff; each needs its own baseline | — |

## Files

| File | Contents |
|---|---|
| `raw_attempts.jsonl` | Every generation: rendered prompt, token ids, exact face log-probabilities per step, top-20 per step, latency |
| `matched_prefix.jsonl` | Teacher-forced scores (incremental and full pass) |
| `env_main.json`, `manifest.json`, `prompts_frozen.md` | Serving, hardware, versions, hashes and frozen prompts |
| `responses.csv`, `position_probabilities.csv`, `probability_coverage.csv` | Normalized tables |
| `analysis/` | `summary.json`, `reference_sequences.csv`, `divergence.csv`, `condition_by_position.csv`, `cross_window.csv`, `matched_prefix.csv`, and figures `reference_sequences.png`, `g_vs_f_face_distributions.png`, `divergence_and_rank.png`, `serial_window_heatmap.png`, `cross_window_distributions.png` |
