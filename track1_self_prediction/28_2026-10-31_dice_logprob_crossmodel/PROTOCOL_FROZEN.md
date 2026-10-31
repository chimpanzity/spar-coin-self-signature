# SPAR_DICE_LOGPROB_CROSSMODEL_v2.0: frozen protocol

Design source: Main_Experiment_SPAR_Dice_Logprob_Qwen_Mistral_Claude_Code_Handoff.md (2026-10-31), from the 2026-10-25 discussion with Christopher Ackerman. Experiments 01-27 are read, never
written. Behavioural study on output log-probabilities; no layer-wise or mechanistic analysis.

## Questions
- RQ1 (shared vs distinct policy): are G/F mismatches near-tie swaps or a re-run of one conditional distribution (H1a), or does
  the prediction wrapper induce a different distribution (H1b)? Natural-path and matched-prefix six-face differences.
- RQ2 (scope): do isolated position predictions S1-S10 recover G(k) or F(k)? Systematic bias toward particular faces?
- RQ3 (multi-position coherence): do five-position windows reproduce G or F better than S(k)? Do overlapping windows agree?
- RQ4 (two checkpoints): are the patterns alike for Qwen3-32B and Mistral Small 3.2 24B? Descriptive only.
Prior result incorporated, not rediscovered (Experiment 21, Qwen): natural G/F differ at 9/10 positions; on G's prefix the F
instruction picks G's face at positions 2-10; the generic-model control showed the opening shift is a prediction-wrapper effect,
not specific to self-reference.

## Models and serving (one model loaded at a time, one A100-SXM4-80GB on vast.ai; no hosted inference API)
| | Qwen | Mistral |
|---|---|---|
| Weights | `Qwen/Qwen3-32B` @ `9216db5781bf21249d130ec9da846c4624c16137` | `mistralai/Mistral-Small-3.2-24B-Instruct-2506` @ `95a6d26c4bfb886c58daf9d3f7332c857cb27b43` |
| Class | Experiment 21's `Qwen` class (via Experiment 27's `QwenEngine`), unchanged | Experiment 27's `MistralEngine`: transformers Mistral 3 conditional-generation class, text path only |
| Tokenizer / template | Qwen2 BPE via transformers; Qwen3 chat template, enable_thinking=False | mistral_common tekken v11 (tekken.json at the pinned revision); one user message, no system prompt |
| Face tokens | ids [16, 17, 18, 19, 20, 21]; separator id 220 | ids [1049, 1050, 1051, 1052, 1053, 1054]; separator id 1032 |

Both: bf16 weights/activations, separate fp32 copy of lm_head, fp32 logits, batch 1, prompt prefilled once then one token at a
time through the KV cache, exact full-vocabulary log-softmax at every step, greedy argmax, no sampling, no logit processors, no
tools, no system message, max 128 new tokens, deterministic flags as in Experiment 21. Code: Experiment 27's
`dice_crossed_guidance/models.py`, unchanged. Offline check (2026-10-31, pinned tokenizer files): in both vocabularies each face
1-6 is exactly one token, a digit after a space encodes as separator + bare digit, and no other token's text is a face digit
(with or without whitespace) or a run of ASCII digits. So the six bare ids are the only ways to emit a face; this is re-checked
on the GPU host by a full vocabulary scan (gate `face_tokens`).

## Conditions (15 per model; prompts in `prompts_frozen.md`)
G (generate 10), F (predict all 10 of "another instance of your model"), S1-S10 (only position k), W1-5, W3-7, W6-10 (only those five
positions, original order). G, F, S1-S10 and W1-5 are byte-identical to Experiment 21; W3-7 and W6-10 are new (Experiment 21
used W3-8 and W5-10, which are not reused as this design's windows).

## Collection
1. Preflight per model: G x3, F x3, every S and W once, in seeded shuffled order (seed
   20261131 Qwen / 20261132 Mistral). Every output rescored (incremental and full pass); matched prefix and matched windows
   (below); vocabulary scan; timings.
2. Gates (all must PASS, else STOP and report): serving identity and hashes; template (Qwen empty think block, no system turn;
   Mistral rendered G exactly `<s>[INST]<G>[/INST]`); face tokens (ids, separator alternation, no variant face tokens); finite
   face log-probs; raw six-face mass >= 0.5 at every G-prompt digit step (prediction-prompt mass reported, not gated, as in
   Experiment 27 amendment v1.1); valid numeric-only output for G, F and every S/W condition; incremental rescoring of each
   output reproduces generation within 0.0001 nats; G and F repeats bit-identical; floor (incremental vs full pass)
   <= 0.25; matched rows complete; archival regression (Qwen: G, F, S1-S10, W1-5 outputs identical to Experiment 21 main
   and every six-face vector, including matched prefix, within 0.01; Mistral: G and F identical to Experiment 27's
   Mistral preflight and vectors within 0.01).
3. Main per model (only after its preflight PASS and investigator authorisation): 20 fresh-context greedy calls of
   each of the 15 conditions (300 per model, 600 total), seeded shuffled order (seed
   20261031 Qwen / 20261032 Mistral), append-only and resumable (refuses prompt or model drift). The first
   record of each distinct (condition, output) is rescored by both arithmetic paths (the predefined full-pass subset). Then
   matched prefix and matched windows on the main run's G and F. Raw-file hashes written to the environment record.
4. Main checks (all must PASS before analysis): serving, template, face tokens, completeness (300 records, each
   (condition, replicate) once), finite, G mass, G/F format, scorer, G and F single output equal to preflight, floor, matched
   rows complete, raw files unchanged since collection (SHA-256).

## Matched-prefix design (teacher-forced, incremental = generation arithmetic; full pass = floor only)
- mp: instruction in {G, F} x history in {G_ref, F_ref} (the model's own greedy sequences), six-face vector at every position.
- window: each W(a-b) prompt with G_ref[a..b] or F_ref[a..b] as its assistant history (secondary; compared with G|G and F|F).

## Analysis plan (per model, then side by side; descriptive, no p-values over deterministic replicates)
1. Integrity: valid rate, distinct outputs and max six-face spread across replicates per condition, raw mass, floor
   (max |dp6| and max JS between arithmetic paths), tokenizer diagnostics.
2. G vs F natural: per position six-face vectors, JS (bits), probability and rank of the other's chosen face; exact sequence
   match, aligned matches, shared bigrams, best shift alignment, longest common run. Position 1 (same empty history) reported
   separately.
3. G vs F matched prefix: JS and top-face agreement per position on each history; disagreements at 2-10 with and without near-ties
   (margin below floor); how many natural disagreements at 2-10 disappear under a matched prefix (cascade) and what remains
   (residual framing effect).
4. S(k): first-token six-face vector and answer vs G(k) and F(k) natural (contexts differ; labelled). Counts vs chance 10/6,
   face counts, mean distribution and entropy (generic bias).
5. Windows: each position vs G(k), F(k), S(k) (JS and chosen face); matched windows vs G|G and F|F; overlaps W1-5/W3-7 at 3-5 and
   W3-7/W6-10 at 6-7, each pair reported once.
6. Conditional dynamics: face counts, adjacent repeats, permutation structure, step sizes mod 6, probability given to repeating
   the previous face (vs 1/6).
7. Cross-model table with identical metrics.
Interpretation rules: similarity can come from shared priors or prompt-conditioned computation; dissimilarity does not show
absence of self-modelling; Experiment 21's generic-model control shows part of the G/F difference is a prediction-wrapper effect.
Top-face differences within the floor are ties. Archival Experiment 21 windows are labelled where compared.

## Budget and stop rules
GPU cap $15 (GPU + disk + bandwidth), warn at $10. Stop for the investigator on unexpected cost, checkpoint mismatch,
tokenizer ambiguity, scoring failure, numerical instability or a gate failure. Sample size is not changed without approval. The
instance is destroyed at the end, also after a failure.
