# SPAR_CROSSED_GUIDED_SELFPRED_v1.0: frozen protocol

Design source: GPT_SPAR_Experiment_27_Crossed_Qwen_Mistral_Guided_Self_Prediction_Claude_Code_Handoff.md (2026-10-30). Exploratory, staged study. Experiments 01-26 are read, never written.

## Models and serving (one model loaded at a time, one A100-SXM4-80GB)
| | Qwen | Mistral |
|---|---|---|
| Weights | `Qwen/Qwen3-32B` @ `9216db5781bf21249d130ec9da846c4624c16137` | `mistralai/Mistral-Small-3.2-24B-Instruct-2506` @ `95a6d26c4bfb886c58daf9d3f7332c857cb27b43` |
| Identity evidence | Experiments 21/26 commit | OpenRouter's `hugging_face_id` for `mistralai/mistral-small-3.2-24b-instruct` (Experiment 22's model) is this repo |
| Class | `AutoModelForCausalLM` via Experiment 21's `Qwen` class, unchanged | `Mistral3ForConditionalGeneration`, text path only (input_ids, no pixel_values) |
| Tokenizer / template | Qwen2 BPE via transformers; Qwen3 chat template, enable_thinking=False | mistral_common tekken v11 (tekken.json at the pinned revision); one user message, no system prompt |
| Face tokens | ids [16, 17, 18, 19, 20, 21]; digit, space, digit | ids [1049, 1050, 1051, 1052, 1053, 1054]; digit, space, digit |
| Precision | bf16 weights/activations, separate fp32 copy of lm_head, fp32 logits | same |

Both: batch 1, prompt prefilled once, then one token at a time through the KV cache (generation and primary scoring use the same
arithmetic), exact full-vocabulary log-softmax at every step, deterministic flags as in Experiment 21, max 128 new tokens.
Greedy = argmax. Sampling = softmax(fp32 logits / 0.7), top_p 1.0, no top_k, `torch.multinomial` with a CUDA generator
seeded per call from the seed table (feasibility 27000000+, reference 27100000+, target
27200000+; Mistral offset +50000). Mistral is served without its optional
SYSTEM_PROMPT.txt (one user message, as in Experiment 22's API calls). Experiment 22 used DeepInfra's hosted copy; its
precision there is unknown, so Experiment 22 responses are not reused as observations.

## Stages and stop rules
1. Preflight, per model: G x3, F x3, Fanon x1 (Experiment 21's prompts), Qwen also Experiment 26's twelve prompts; four
   feasibility samples (discarded); three crossed prompts as a format check; matched-prefix G|G, F|G, F|F, Fanon|G.
   Gates (all must pass; otherwise STOP): serving identity; template (Qwen empty think block and no system turn; Mistral
   rendered G exactly `<s>[INST]<instruction>[/INST]`); face tokens; finite face log-probs and raw six-face mass >= 0.5;
   scorer reproduces generation within 0.0001 nats; G/F repeats bit-identical; greedy G is ten valid integers;
   numerical floor (incremental vs full pass) <= 0.25. Qwen only: G/F equal Experiment 21 and every six-face vector
   within 0.01; Experiment 26's twelve free outputs identical and teacher-forced vectors within 0.01;
   this package's engine bit-identical to Experiment 21's class. No accuracy gate.
2. Corpus, per model: 8 reference then 24 target sequences under Experiment 21's G prompt at T=0.7,
   seeds in table order; invalid draws are kept and skipped; STOP if more than 2N draws are needed. Duplicates
   are kept and reported. The corpus is written and hashed before any prediction prompt is built. N=24 per generator is
   final for this run (no expansion).
3. Trials: built mechanically from the frozen templates and both corpora; trial file hashed; integrity table written.
4. Predict, per model: every trial with that predictor, seeded shuffle; then policy scoring (G, F, Fanon) of all items.
5. Main checks before analysis: completeness, prompt hashes, forced faces equal targets, finite log-probs, scorer = generation
   (subset), oracle = sampling distribution, per-model floor <= 0.25.

## Target items
- Tier A (2, descriptive bridge): Qwen's greedy G `5 2 6 3 1 4 6 2 5 3` and Mistral's greedy G (preflight).
- Tier B (primary): 24 sampled sequences per generator.
- Each item's D evidence: the generator's reference sequence number (i mod 8) + 1 (Tier A: number 1); never a scored target.

## Trials (5400 = 2 predictors x 50 items x 6 conditions x 9 arms)
Conditions (scored original positions; revealed prefix): k0 (1-3; 1-0), k3 (4-6; 1-3), k6 (7-9; 1-6), k8 (9-10; 1-8), m0 (7-9; 1-0), m3 (7-9; 1-3).
Suites: bridge to Experiment 26 = ('k0', 'k3', 'k6'); fixed position 7 with growing partial history = ('m0', 'm3', 'k6'); immediate next = ('k3', 'k6', 'k8').
Arms: framing A/T/R x evidence H/I/D (`prompts_frozen.md`). R is "your own model" on the diagonal and "a different model, not your
own model" off it, so the relational claim is true in every cell; T always names the true target generator.

## Measurements
- Teacher-forced six-face distribution p at every scored position, with the true target window as the assistant history
  (incremental arithmetic; primary). Free greedy output with its digit-step vectors (secondary).
- Target distribution q_j: the generator's six-face distribution under the G prompt given the item's true rolls 1..j-1
  (assistant history). The prediction prompt puts the revealed rolls in the user text instead; these are different computations.
- Native policy n_j: the predictor's own G distribution at the same history.
- Full-pass rescoring of all Tier A trials and a seeded 5% of Tier B trials, and of all policy rows: per-model floor.

## Estimands (Tier B; resampling unit = distinct target string within generator; 10000 cluster-bootstrap draws, seed 20261051)
Per (predictor, item), a metric is averaged with equal weight over the selected conditions, arms and positions.
- E1 (primary, RQ2): self-advantage interaction on JS(p, q) in bits, arm AH, all conditions and positions:
  S_Qwen = mean over Qwen items of JS(Mistral) - JS(Qwen); S_Mistral = mean over Mistral items of JS(Qwen) - JS(Mistral);
  interaction = (S_Qwen + S_Mistral) / 2. Positive = predictors are closer to their own model. Also KL(q||p), TV, -log2 p(true roll), all arms.
- E2 (RQ4): the same interaction for the native policies n (no prediction wrapper), and prediction minus native per cell.
- E3 (RQ3 identity): change T-A and R-A per cell (paired on item, condition, evidence) and the difference-in-differences
  diagonal minus off-diagonal. Negative DiD = the identity cue helps a predictor more on its own model.
- E4 (RQ3 guidance): D-H, I-H, D-I per cell under framing A.
- E5: E1 within the fixed-position suite (position 7), the immediate-next suite (first window position) and the bridge suite.
- E6: E1 against the target distribution tempered to T=0.7 (sensitivity).
- RQ1: G vs F (and Fanon) matched-prefix distributions per model on its own greedy G (Tier A, descriptive), and k0 arms vs q.
Secondary: p(true roll), rank, top-1 = true roll, top-1 = target's top, free-output exact match, six-face mass, free vs forced.
Tier A is reported per cell as a case study, never pooled with Tier B. Interpretation rules: a diagonal advantage on AH that is
matched by the native-policy advantage (E2) is shared procedural tendency, not identity knowledge; only a negative DiD (E3)
beyond the floor would point to identity-sensitive prediction, and even that is not evidence of introspective access.

## Budget
GPU cap $15, warn at $10; estimate printed by `dryrun` and recomputed from preflight timings before predict.
The instance is destroyed at the end, also after a failure.
