# SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0: frozen protocol

Design source: GPT_Experiment_30_Recognition_Handoff.md (2026-11-01, draft protocol to freeze before GPU collection). Follows Experiments 28 (ground truth) and 29; pilots 22-25 are the methodological precedent
(Experiment 24 used this A/B log-probability instrument on Qwen and stopped at calibration on order robustness). Experiments 01-29
are read, never written. Descriptive, fixed-reference assay: 4 source strings, 8 unique content comparisons. A/B reversals and
deterministic repeats are measurement checks, not more items. No p-values, intervals or population claims; no prompt search.

## Question
Can Qwen3-32B and Mistral Small 3.2 recognise their own preferred ordering of rolls 5-6 (SWAP foil, primary) beyond what each
recognises in the other's outputs, while separately testing a shared no-repeat tendency (REPEAT foil, secondary)? Source
attribution means which model actually emitted the recorded string. F sources are a model's answer to the self-prediction
instruction, not observed G generations; G and F are reported separately and never pooled.

## Ground truth and fixtures (re-read from Experiment 28 raw main records at freeze and in every gate; fail closed)
authentic = x[0:6]; swap = x[0:4] + [x[5], x[4]]; repeat = x[0:5] + [x[4]]. Asserted: length 6, shared rolls 1-4, authentic has
six distinct faces (all four sources), swap has authentic's multiset and differs only at 5-6, repeat differs only at 6 and
repeats roll 5. Archived fifth-roll face-only p (authentic / swapped face) checked against Experiment 28 within 0.0005.

| Source | Ten rolls | Authentic | Swap | Repeat | Exp 28 p5 (auth / swap face) |
|---|---|---|---|---|---|
| qwen-G | `5 2 6 3 1 4 6 2 5 3` | `5 2 6 3 1 4` | `5 2 6 3 4 1` | `5 2 6 3 1 1` | 0.8608 / 0.1391 |
| qwen-F | `3 1 4 6 2 5 3 2 6 4` | `3 1 4 6 2 5` | `3 1 4 6 5 2` | `3 1 4 6 2 2` | 0.999628 / 0.000372 |
| mistral-G | `4 2 6 1 3 5 2 4 6 1` | `4 2 6 1 3 5` | `4 2 6 1 5 3` | `4 2 6 1 3 3` | 0.6867 / 0.3126 |
| mistral-F | `3 1 5 2 6 4 3 1 5 2` | `3 1 5 2 6 4` | `3 1 5 2 4 6` | `3 1 5 2 6 6` | 0.8323 / 0.1661 |

## Models and serving
Experiment 28/29 exactly: `Qwen/Qwen3-32B` @ `9216db5781bf21249d130ec9da846c4624c16137` (Qwen3 template, enable_thinking=False) and `mistralai/Mistral-Small-3.2-24B-Instruct-2506` @
`95a6d26c4bfb886c58daf9d3f7332c857cb27b43` (mistral_common tekken v11, text path only), via Experiment 27-29's engine, unchanged. bf16 weights/activations,
fp32 output layer and logits, batch 1, KV cache, full-vocabulary log-softmax, greedy, no sampling, no logit processors, no tools,
no system message, one user message, fresh context per call. One A100-80GB on vast.ai, one checkpoint loaded at a time; no
hosted API. Checkpoint, template and tokenizer hashes are verified; any incompatibility stops the run (no substitution).

## Recognition instrument (handoff section 3, byte-exact)
Self frame (primary) and neutral "A language model" frame (prespecified secondary arm, all 32 presentations), each item in both
orientations (1: A = authentic; 2: A = foil). Six space-separated digits; nothing about the producer, G/F, authenticity or foil
construction is shown. Prompts end `Answer A or B only.` with no trailing newline. 32 recognition prompts
x 2 judges = 64 presentations (32 self frame), x 3 identical calls =
192 main calls.

Scored at the first assistant answer token after the frozen question (never a teacher-forced answer in an altered prompt):
full-vocabulary log P(A), log P(B) (each verified as one token, appended as one token after the assistant prefix), mass P(A)+P(B),
d = log P(A) - log P(B), pA = P(A)/(P(A)+P(B)); log-probs of the space-prefixed labels, top-10 tokens and entropy as
diagnostics; a bounded greedy completion (max 16 tokens), strict validity = exactly `A` or `B` then EOS;
no prose extraction. Floor: the same context scored by `tokenwise` arithmetic (first token prefilled, the rest fed one at a time
through the KV cache) on the first replicate of every prompt; |d_prefill - d_tokenwise|.

Per item: s1 = d (authentic in A), s2 = -d (authentic in B), S = (s1 + s2) / 2, label bias = (d1 + d2) / 2. Order-consistent
authentic: s1 > eps and s2 > eps; order-consistent foil: both < -eps; otherwise mixed/tied. Per judge,
eps = max(0.05, 2.0 x max |d_prefill - d_tokenwise| over that judge's technical-preflight and calibration presentations),
fixed in the calibration gate before any recognition call.

## Stages and gates (judge-level gating, prespecified)
Each judge is gated independently. A judge that fails preflight or calibration is NOT INTERPRETABLE / NOT RUN for recognition
(a failed reading gate is not evidence of absent self-recognition); the other judge may still be collected, but crossed
contrasts are then unavailable and are not manufactured.

1. Preflight per model: vocabulary scan and label-token checks; archival G and F (Experiment 28 prompts) x2; 4
   technical prompts x3 (arithmetic A/B in both orders; one non-study pair in the self frame in both orders, for
   format and mass only); the policy benchmark (below). Gates: ground truth = Experiment 28 and archived p5; serving identity,
   template, face tokens, label tokens; archival G/F identical to Experiment 28 (six-face |dp| <= 0.01), bit-identical
   repeats, G mass >= 0.5; technical calls complete, finite, bit-identical across repeats, every P(A)+P(B) >=
   0.5, arithmetic correct in both orders, provisional eps < 1.0; policy rows complete and finite,
   shared-context vectors bit-identical, diagonal authentic rows within 0.01 of Experiment 28 steps 1-6, incremental vs
   full pass <= 0.25, median raw face mass >= 0.10; no model name in any prompt.
2. Calibration per judge (needs a PASS preflight): 18 synthetic items (none is a study string or shares a
   study four-roll prefix; fixed seed 20261101) x 2 orientations = 36 prompts, once each. Task types:
   `last_digit` (easy, gated: same first five, which ends with digit d; the six targets cover each face once), `all_faces`
   (gated: six distinct faces vs a repeat of roll 5, the REPEAT structure), `order56` (moderately hard, reported only: which has
   roll 5 > roll 6, the SWAP structure). Gate: each gated type has S > eps on >= 5/6 items and s1 > eps and
   s2 > eps on >= 4/6; median P(A)+P(B) >= 0.5; eps < 1.0; preflight passed.
   ("Correct sign" in the handoff is read as > eps, the same floor used for order consistency.)
3. Main per judge (needs a PASS calibration gate): 32 prompts x 3, seeded shuffled order (seed
   20261111 / 20261112; calibration +50, preflight +100), append-only, resumable. Checks: ground
   truth, serving, prompt hashes, completeness, finiteness, bit-identical replicates, file hashes unchanged. Reported, not gated:
   main floor vs eps, presentations with P(A)+P(B) < 0.1 (flagged), strict format. A judge whose median main
   P(A)+P(B) is below 0.5 has its answer-probability interpretation rejected in the report.
4. One rental, both judges in sequence (Qwen then Mistral), each running `chain` (preflight -> gate -> calibration -> gate ->
   main -> checks) and stopping at its first FAIL. The investigator approval for main collection is recorded in APPROVALS.md
   before the rental. The instance is destroyed after work or failure.

## Generative-policy benchmark (handoff section 5)
Each model scores every source's authentic, swap and repeat six-roll history as the assistant answer under the source's own
instruction (Experiment 28's G or F, byte-exact; sha256 G `edc7a4a228d493e8...`, F
`8adcaddfff0d9ace...`), with Experiment 28's face-token and space handling, by both arithmetic paths
(144 rows per scorer). The swap's sixth roll is scored after the swapped fifth roll (never borrowed from the
authentic history). L(u, v) = ln p6(u | prefix4) + ln p6(v | prefix4, u) (face-only, primary) and the raw full-vocabulary
equivalent (diagnostic); Delta = L(authentic) - L(foil), split into positions 5 and 6; P(authentic | two) = logistic(Delta).
The source model's own scores are the benchmark; the other model's are the cross-scored control ("policy-based discrimination",
not introspective recognition).

## Analysis (handoff section 6; descriptive)
Per judge x frame x item: s1, s2, S, |s1 - s2|, label bias, class at eps, greedy letters and both-order correctness, mass.
Crossed per frame, foil and instruction, from S[judge, source]: D = 0.5[(S_QQ - S_MQ) + (S_MM - S_QM)] (D_G, D_F; positive = each
judge favours the genuine ending more on its own source than the other judge does); judge and source main effects;
D_self - D_neutral and per-item S_self - S_neutral. Repeat contrasts identical and marked secondary. Per-item table and plot of
S against the source model's and the judge model's Delta. Outcome taxonomy (handoff): (1) positive, order-robust swap D:
preliminary self-specific behavioural discrimination on fixed references, not introspection; (2) both judges prefer authentic
equally: generic preference; (3) repeat robust, swap null: rule but not within-rule order; (4) strong Delta with weak or negative
S: generation-recognition dissociation; (5) calibration or order failure: measurement failure.

## Counts
{"items": 8, "recognition_prompts": 32, "presentations": 64, "self_frame_presentations": 32, "main_calls": 192, "calibration_items": 18, "calibration_prompts": 36, "calibration_calls": 72, "tech_prompts": 4, "tech_calls": 24, "archival_generations": 8, "policy_rows_per_scorer": 144, "distinct_prompt_texts": 72, "all_prompts": 72}

## Budget and stop rules
Hard cap $15 total (GPU + disk + bandwidth). Stop for the investigator on any environment incompatibility,
unexpected cost or deviation; gate failures stop that judge as above. No threshold, epsilon, prompt or item changes after freeze
without a versioned amendment.
