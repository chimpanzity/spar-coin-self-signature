# SPAR_DICE_PREFIX_DECLARATIVE_v1.0: frozen protocol

Design source: GPT_SPAR_Qwen_Dice_Partial_History_Declarative_Knowledge_Logprob_Handoff_v1.0.md (2026-10-30). Exploratory, gated pilot; a follow-up to Experiment 21, not to the Loula line.

## Serving (Experiment 21, unchanged)
- `Qwen/Qwen3-32B` at commit `9216db5781bf21249d130ec9da846c4624c16137`; transformers; bf16 weights with an fp32 output layer; Qwen3 chat template with
  `enable_thinking=False` (template sha256 `a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8`); one user message, no system message, no tools;
  greedy, batch 1, no logits processors, 128-token cap. Generation and scoring use Experiment 21's `Qwen` class unchanged.
- Six-face log-probabilities are the exact full-vocabulary log-softmax at the face tokens `1`-`6` (ids 16-21). Digits and the
  space separator are separate tokens.

## Reference
- G: Experiment 21's direct-generation prompt (sha `edc7a4a228d4…`), greedy output `5 2 6 3 1 4 6 2 5 3`.
- F: Experiment 21's full self-prediction prompt (sha `8adcaddfff0d…`), greedy output `3 1 4 6 2 5 3 2 6 4`.
- G_j = six-face distribution of the G prompt at original position j with the true G history (incremental arithmetic).

## Conditions: 3 prefix lengths x 4 arms
k = (0, 3, 6); targets are the next three G rolls (positions k+1..k+3). Arms: H (prefix only), N/S/O (H plus one paragraph
directly before "Predict" reporting a separate earlier response whose first six integers use each face once; source
"an unspecified model" / "your own model" / "a different model"). Exact strings and hashes: `prompts_frozen.md`.

Why this wording (handoff 4.3): the draft neutral sentence described the target itself while the self sentence described a
prior sample, which would make the neutral version more informative. All three versions here describe a *separate earlier
response*, say it is an observation and not a guarantee, and say it does not determine order. Only the source phrase differs;
each paragraph has the same word count. The paragraph contains no digit and no order information.

Truth of each paragraph:
- S and N: Experiment 21's greedy G (`5 2 6 3 1 4 6 2 5 3`) is an earlier response to this exact instruction by Qwen3-32B.
- O: Experiment 22 sampled Mistral Small 3.2 24B on this exact instruction at temperature 0.7; 49 of its valid
  sequences use each face once in their first six integers (e.g. `mistral-01`: `3 1 5 6 2 4 1 3 6 2`).
- No paragraph claims a population propensity; Experiment 22's Qwen and Mistral prevalence is context in the report only.

## Measurements
- Measurement B (primary): teacher-forced six-face distribution at each target position, true G window as assistant history,
  incremental KV-cache arithmetic. Labelled conditional scoring, never "generated".
- Measurement A (supplementary): free greedy three-integer output, with the six-face distribution at each emitted digit.
- Each prompt's own free output is rescored with the teacher-forced scorer (scorer = generator check).
- One full-pass score per condition and for the references: numerical floor.

## Order and repeats
Preflight: G x3, F x3, H3/N3/S3/O3 x1, seeded shuffle (seed 20261041).
Main: 12 conditions x 3 fresh-context repeats, seeded shuffle (seed 20261040). Greedy repeats establish
determinism, not independent observations; analysis uses repeat 1 and reports the spread.

## Preflight gates (all must pass before main)
1. serving: commit, chat-template hash, rendered-G hash and all prompt hashes match.
2. non_thinking: every rendered prompt ends with the empty think block, no system turn, no think text in outputs.
3. face_tokens: face ids 16-21, single tokens; G history tokenises as digit, space, digit, ...
4. face_logprobs: all finite; raw six-face mass >= 0.5 at every scored digit step.
5. scorer_matches_generation: rescoring each output reproduces its generation log-probs within 0.0001.
6. reference_reproduction: G and F greedy outputs identical to Experiment 21 on every repeat, and every six-face distribution
   (generation steps; matched-prefix G|G, F|G, F|F) within max |dp| <= 0.01 of the archive. Otherwise stop and ask
   before establishing a new baseline.
7. determinism: G and F repeats bit-identical.
8. k3_outputs_valid / k3_teacher_forced_complete: H3/N3/S3/O3 each return three integers 1-6; all 12 forced rows present.
Numerical floor: delta = max |dp| incremental vs full pass; near-tie floor = max(0.09, delta).

## Main checks before comparative analysis
The same gates on the main data, completeness (36 records, 108 forced rows), and G_j within 0.01 of the archive.
No accuracy gate: scientific nulls are reported.

## Outcomes (per original position; positions are not pooled as independent)
1. P(true roll), six-face normalised; also raw log P and raw six-face mass.
2. JS divergence (bits) and total variation between the arm and G_j. Primary contrasts at the same k and position:
   N-H, S-H, S-N; framing control O-H, S-O.
3. Rank and top face of the true roll; near-ties flagged by the floor.
4. Teacher-forced window log-likelihood (sum and mean over 3 positions).
Supplementary (free): predicted triple, exact match by position and whole window, k=3 rule adherence (faces in {1,3,4}),
path log-prob. Prefix-length (k) comparisons change the predicted position too; they are descriptive only.

## Budget
GPU cap $10 for preflight plus pilot; estimate 25 min x $1.6/h on one A100 80 GB.
