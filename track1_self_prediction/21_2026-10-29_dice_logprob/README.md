# 21 · Dice self-prediction on log-probabilities: preflight (2026-10-29)

| | |
|---|---|
| Track | 1: static self-prediction |
| Tag | `DICE_LOGPROB_v1.0` |
| Handoff | `GPT_SPAR_Qwen3_32B_Dice_Logprob_Claude_Code_Handoff_v1.0` (2026-10-29), from the 2026-10-25 meeting with Christopher Ackerman |
| Model and serving | Qwen3-32B (`qwen/qwen3-32b`) on OpenRouter, SiliconFlow pinned, no fallback, temperature 0, `reasoning.enabled=false`, `logprobs=true`, `top_logprobs=20`, no tools, no system message, max_tokens 128 |
| Status | SiliconFlow preflight **FAILED** (no logprobs; not deterministic). Amended, with Chris's approval, to open weights on a rented A100; that preflight **PASSED** every gate (see [below](#amendment-open-weights-on-a-rented-gpu-2026-10-29)). **Main collection complete** (150/150 valid; approved by Chris); results in [`main-qwen3-32b-a100/REPORT.md`](main-qwen3-32b-a100/REPORT.md). Total GPU cost about $1.60. |
| Previous | [← 20 Static self-prediction replication](../20_2026-10-20_static_selfpred_replication/) |

## Question

When Qwen3-32B predicts what another instance of itself would output in a 10-roll dice task (prompt F), are the probabilities it assigns to the six faces at each position close to those during direct generation (prompt G)? A close result would mean the two differ only where near-tied faces swap ("noisy recomputation"). A far result would mean F follows a distinct conditional predictive policy.

Secondary questions use single-position (S1–S10) and window (W1–5, W3–8, W5–10) predictions to test reconstruction coherence. That makes 15 conditions; the prompts are frozen in [`preflight-20261029T180505Z/prompts_frozen.md`](preflight-20261029T180505Z/prompts_frozen.md).

## What was built

All code is in `src/spar_dynamic/dice_logprob/`, and 28 offline tests in `tests/test_dice_logprob.py` pass.

| File | What it does |
|---|---|
| `prompts.py` | The 15 frozen prompts, byte-exact to the handoff, with SHA-256 hashes |
| `client.py` | One call per record; archives the full raw response; retries transport errors with backoff, never retries invalid answers |
| `extract.py` | Strict numeric-only parsing; token-to-face alignment that fails closed; six-face vectors with both raw mass and the distribution normalized over the six faces; a face missing from `top_logprobs` stays missing, never zero; JS divergence in bits; ranks |
| `preflight.py` | Stages A–C and the go/no-go gates |

## Preflight result

Run: [`preflight-20261029T180505Z/`](preflight-20261029T180505Z/). Contents:
- [`preflight_report.md`](preflight-20261029T180505Z/preflight_report.md)
- `raw_attempts.jsonl` (every request and full raw response)
- `manifest.json`, `preflight_summary.json`

| Gate (handoff 4.5) | Result | Evidence |
|---|---|---|
| Frozen configuration accepted with SiliconFlow pinned | **FAIL** | Both stage A requests (G, F) were refused by OpenRouter before reaching any provider: HTTP 404, "No endpoints found that can handle the requested parameters", `failed_routing_step: Filter by Parameters`. OpenRouter's endpoint listing for Qwen3-32B shows neither provider (SiliconFlow, DeepInfra) supports `logprobs`/`top_logprobs`. |
| Parameters not silently ignored | **FAIL** | Diagnostic stage B dropped `require_parameters`, still pinned to SiliconFlow. The 24 requests that reached it all came back with `logprobs: null`. SiliconFlow silently drops the logprob request. |
| Complete six-face vectors at all 10 positions of G and F | **FAIL** | No logprobs of any kind, so not even the selected token's probability. |
| References repeatable (≥ 9/10 identical) | **FAIL** | At temperature 0, G produced 3 distinct sequences in 10 calls (modal `5 2 6 3 1 4 2 5 3 6` 4 times); F produced 3 distinct (modal `1 3 5 2 6 4 2 5 3 6` 5 times). Positions 1–4 of G split 6/4 between two openings. This is serving nondeterminism at temperature 0, measured under the diagnostic configuration. |
| Non-thinking | PASS | `reasoning_tokens = 0` reported on all 24 responses; no reasoning fields; no `<think>` text. |
| Valid numeric-only output for G, F, S, W | PASS | 24 of 24 valid, exactly in the frozen format. |

**Two independent blockers.**
1. No logprobs are available for Qwen3-32B anywhere on OpenRouter.
2. The SiliconFlow endpoint is not deterministic at temperature 0.

So even a logprob-capable route through the same serving would not give the single reference sequence the design assumes. Under handoff 4.4, that alone requires a redesign with distributional references.

The stage B/C sequences are diagnostics under a non-frozen configuration and are **not** references. In particular, G and F differ already at position 1 (G: 5 or 3; F: 1 in all 10).

## Options (need investigator approval; any one is a new configuration with its own reference baseline)

1. **Rented GPU, open weights (recommended).** Qwen3-32B in bf16 (about 65 GB) on one 80 GB A100/H100, via `transformers` or vLLM.
   - **Exact logits** for all six faces at every position, so no top-20 truncation.
   - **Deterministic** greedy decoding, which fixes the reproducibility blocker.
   - **Teacher-forced matched-prefix scoring** (handoff 6.4) becomes possible.
   - Non-thinking via the chat template's `enable_thinking=False`.
   - Cost: well under an hour of GPU time for 150 short completions plus prefix scoring, a few dollars. FP8 weights could be used to stay closer to SiliconFlow's fp8 serving.
   - Needs a rental account (e.g. RunPod, Lambda, Modal) and about a day of setup and validation.
2. **This PC.** It has an RTX 4070 SUPER with 12 GB, too small for Qwen3-32B even at 4-bit (about 19 GB) without CPU offload.
   - A llama.cpp GGUF Q4 with partial offload would run slowly but can return per-token probabilities.
   - 4-bit quantization is a further departure from the served model. Useful only as a cheap feasibility check.
3. **Another hosted API outside OpenRouter** that exposes `top_logprobs` for Qwen3-32B with thinking disabled. Not verified; it needs a new account and key.
   - It must pass this same preflight, including the determinism gate, which hosted batch serving may fail as SiliconFlow did.
   - DeepInfra's native API is a candidate only if `enable_thinking=false` actually works there; through OpenRouter it ignored reasoning-off (folder 20).
4. **Do not** degrade to a token-only accuracy study on SiliconFlow without approval (handoff 4.5 and 10.5). The logprob comparison is the point of the study.

## Decision memo

- **Main collection:** not run, blocked.
- **Recommended next step:** option 1. It removes both blockers and also enables the matched-prefix diagnostic Ackerman's question needs. With natural trajectories, G and F diverge at position 1, so every later comparison mixes the framing effect with different histories.
- **Generic-model control, recognition task, reasoning-on arm:** still deferred, as the handoff specifies.

## Amendment: open weights on a rented GPU (2026-10-29)

Chris approved option 1. This is a **new configuration with its own reference baseline**; nothing from the SiliconFlow diagnostics is reused.

| | |
|---|---|
| Serving | `Qwen/Qwen3-32B` at commit `9216db57…`, Hugging Face `transformers` 5.22.0, torch 2.11.0 (CUDA 12.8), bf16 weights and activations with the output layer and logits in fp32, batch size 1 |
| Hardware | One NVIDIA A100-SXM4-80GB rented on Vast.ai (SPAR team account), North Carolina host, $1.93/h. The instance was destroyed after the run. |
| Decoding | Greedy (argmax of the full next-token distribution), no sampling and no logit processors, max 128 new tokens, stop at end of turn |
| Non-thinking | Qwen3's documented switch: chat template with `enable_thinking=False` (the assistant turn starts with an empty think block). One user message, no system message, no tools. |
| Probabilities | Exact log-softmax over the full vocabulary at every step: all six faces, with no top-20 truncation. Raw face mass and the six-face distribution are both kept. |
| Matched-prefix scoring (handoff 6.4) | Teacher-forced: the history is fed through the cache token by token, the same arithmetic as generation. Instruction ∈ {G, F} × history ∈ {modal G, modal F}. |
| Code | `src/spar_dynamic/dice_logprob/gpu_runner.py` (runs on the GPU) and `gpu_eval.py` (gates, offline). The pipeline was first tested end to end on Qwen3-0.6B on the local RTX 4070 SUPER. |

**Preflight run:** [`preflight-qwen3-32b-a100/`](preflight-qwen3-32b-a100/). Report: [`preflight_report.md`](preflight-qwen3-32b-a100/preflight_report.md). It contains 33 generations: 10 G, 10 F and each S and W condition once, in seeded shuffled order, plus matched-prefix scoring.

| Gate | Result |
|---|---|
| Serving recorded (model commit, GPU, versions) | PASS |
| Non-thinking (empty think block; no think text in outputs) | PASS |
| Valid numeric-only outputs, all 15 conditions | PASS (33/33) |
| Complete six-face vectors at all 10 positions of G and F | PASS. The six faces hold ≥ 99.8% of next-token mass at every position, with no tokenization ambiguity. |
| References repeatable | PASS. G = `5 2 6 3 1 4 6 2 5 3` and F = `3 1 4 6 2 5 3 2 6 4`, each 10/10, with bit-identical log-probabilities across repeats. |
| Matched-prefix scoring reproduces generation | PASS (difference 0 when scoring each condition's own output) |

**Numerical precision floor.** The same scores computed in one forward pass instead of token by token differ by up to 0.03 (G) and 0.09 (F) in six-face probability, and flip F's top face at one position. These differences come only from bf16 arithmetic order. So where two faces are within a few hundredths of each other, which one "wins" is not a robust property of the model. The main analysis should treat such near-ties as ties.

**What the preflight data already show (descriptive; the main run will repeat these deterministic outputs):**
- **G and F disagree at 9 of 10 positions** (they agree only at position 8).
- **Position 1 is the clean comparison** (no prior output in either). G picks 5 (p = .54 among faces); F picks 3 (p = .39).
  - G's choice is unlikely under F (p = .02, rank 5).
  - F's choice is a real competitor under G (p = .23, rank 3).
  - JS divergence is 0.52 bits.
- **Later positions are confounded with history.** In the natural trajectories JS reaches 1 bit at positions 4–6, but each condition is continuing a different sequence.
- **Matched prefix points to a cascade.** Given G's own history, the F instruction reproduces G's faces at every position from 2 to 10; only position 1 differs. The reverse is not symmetric: the G instruction given F's history does not reproduce F. This is the early-deviation cascade Ackerman raised; it needs the main-run analysis before any claim.
- **Single-position and window predictions match neither reference.** S(k) answers 4 or 5 at every k, and W1–5 = `4 2 6 3 5`.

## Main collection results (2026-10-29)

Run [`main-qwen3-32b-a100/`](main-qwen3-32b-a100/): 15 conditions × 10 replicates = 150 fresh generations, plus matched-prefix scoring. It used the same machine and model commit as the preflight. The full write-up, with observations, interpretations, limitations and next decisions, is in [**`REPORT.md`**](main-qwen3-32b-a100/REPORT.md).

- **Reliability:** 150/150 valid. Every condition is identical across its 10 replicates, with identical probabilities; the main run reproduces the preflight exactly.
- **G vs F:** G = `5 2 6 3 1 4 6 2 5 3`, F = `3 1 4 6 2 5 3 2 6 4`. They differ at 9 of 10 positions, but **F's positions 1–7 are G's positions 4–10**: the same run of faces, reached after different openings.
- **Position 1** (same empty history) differs substantially: JS 0.52 bits.
  - G's choice (5) has probability .02 under F.
  - F's choice (3) has .23 under G.
  - F's own top face is a near-tie (3 at .39 vs 2 at .31).
- **Matched prefix:** given G's history, the F instruction picks G's face at every position from 2 to 10 (JS ≤ 0.09 bits). Most of the later divergence is a cascade from the different opening. Given F's history, the G instruction departs at positions 2, 3, 7 and 8.
- **Single positions and windows** reconstruct neither reference (6 of 27 reports match G, 3 match F; about 4.5 expected by chance). Different scopes rarely agree on the same position (6 of 52 pairs). Single-position answers are 4 or 5 at every position.
- **Open question:** whether the opening shift is specific to the self framing. A non-self wrapper control is the obvious next step.

Figures are in [`main-qwen3-32b-a100/analysis/figures/`](main-qwen3-32b-a100/analysis/figures/).

## Re-running

```bash
PYTHONPATH=src python -m pytest tests/test_dice_logprob.py          # offline
PYTHONPATH=src python -m spar_dynamic.dice_logprob.preflight         # ~$0.001, capped at $1

# open-weight preflight (on a GPU with >= 80 GB; Qwen3-0.6B works on a 12 GB card for plumbing tests)
PYTHONPATH=src python -m spar_dynamic.dice_logprob.gpu_runner preflight --model Qwen/Qwen3-32B --out <dir>
PYTHONPATH=src python -m spar_dynamic.dice_logprob.gpu_eval <dir>                    # offline gate report
```
