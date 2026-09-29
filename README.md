# SPAR Dynamic Behavioral Self-Signature Pilot

A small descriptive pilot testing whether LLM self-signatures in a fair-coin
simulation task are more detectable when behavior unfolds dynamically
(one call at a time, with the model shown its accumulated history) than when
the same nominal task is done as one static batch generation.

**Status**: descriptive pilot (n=6 trials/cell). Do not infer self-awareness,
introspection, or self-recognition from these results.

---

## Design

Three models, each serving as both source and judge:

| label | model_id | role |
|---|---|---|
| astra | `openai/gpt-6-astra` | source + judge |
| fable | `anthropic/claude-fable-5.1` | source + judge |
| qwen | `qwen/qwen3.8-27b` | source + judge |

Two source architectures produce 50-flip H/T sequences:

- **batch**: one API call → complete 50-flip string in a single completion
- **online**: 50 sequential API calls, each shown the entire accumulated
  history so far, one flip returned per call

Source pool: 10 valid trajectories × 3 models × 2 architectures = **60 sequences**.

Each judge sees anonymous string pairs from the same architecture and
labels them SAME (same source model) or DIFFERENT. Four analytical cells:

- **A** own+own → SAME
- **B** own+other → DIFFERENT
- **C** same-other+same-other → SAME
- **D** other₁+other₂ → DIFFERENT

24 trials per (judge × architecture), 48 per judge, **144 judgments** total.

Primary self-signature measures (per judge × architecture):

- `self_advantage = own_accuracy − other_accuracy`
- Central architecture contrast:
  `dynamic_self_signature_gain = self_advantage_online − self_advantage_batch`

## Layout

```
spar_dynamic/         Python package
  config.py            frozen prompts, models, retry policy, budget
  api.py               OpenRouter client wrapper + cost accountant
  source.py            batch + online source generation (resume-safe)
  trials.py            A/B/C/D trial construction with balancing
  judgment.py          judgment calls (JSON schema + text fallback)
  analyze.py           source features, LOO classifier, self-advantage, feature-distance baseline
  orchestrator.py      end-to-end resume-safe runner with cost guard
  state.py             on-disk state helpers

tests/
  test_spar_dynamic.py 31 local tests (no API calls)

data/spar_dynamic/spar-dynamic-run-20260929T081814Z/
  the completed pilot's raw data + derived summaries + FINAL_OVERNIGHT_REPORT.md
```

## Running the pilot

```
pip install -r requirements.txt
export OPENROUTER_API_KEY=sk-or-v1-...
python -m spar_dynamic.orchestrator --live --yes --run-id <your-run-id>
```

Every phase writes to disk incrementally and re-invocation with the same
`--run-id` is idempotent (resume-safe). Add `--skip-smoke` if a smoke run
already occurred.

Budget cap is hard-coded at `$25 USD` in `config.py`; the run halts if the
projected total would exceed it.

## Results from this run

Full report:
[FINAL_OVERNIGHT_REPORT.md](data/spar_dynamic/spar-dynamic-run-20260929T081814Z/results/FINAL_OVERNIGHT_REPORT.md).

Summary:

- **Total spend**: $1.43 / $25 cap
- **Source-model identifiability** (leave-one-out nearest centroid on visible
  features): batch 0.70, online 0.93. Online exposes model-specific phenotypes
  that batch generation hides.
- **Pooled self-advantage**: batch +0.056, online +0.028. **Dynamic
  self-signature gain is essentially zero pooled** and negative for the
  fable judge (−0.333).
- **Feature-distance baseline** (median-threshold classifier, no judge
  identity): batch 0.556, online 0.944. The online baseline matches the
  astra/fable judges' online accuracy — most of the judge accuracy under
  online is explainable by visible surface statistics, not by any
  own-model-specific sensitivity.
- Per-model phenotypes under online diverge sharply: qwen produces 94% H
  with mean longest-run of 27 consecutive H's in a 50-flip trajectory
  (near-collapse to a "one" mode); fable drifts to 60% H with switch rate
  0.75; astra remains near 50% but shifts more in switching (0.63 → 0.69).

## Deviations from the frozen design

**qwen batch temperature**. The spec required `temperature=0.0` globally.
At temperature 0.0, the qwen model produced 51-character strings on all 40
attempts (one character too many under the strict `^[HT]{50}$` parser).
With explicit authorization, the qwen batch cell was rerun at
`temperature=0.3` (all other cells stayed at 0.0). See
`spar_dynamic/config.py` `TEMPERATURE_OVERRIDES`. At temp 0.3 the model
produced 10 valid 50-character trajectories out of 96 attempts (10.4%
success rate). This is a deliberate documented deviation; other model
substitutions were considered but showed the same or worse behavior in
smoke-testing.

## Interpretation framework (predefined in spec)

Following the spec's outcome hierarchy, this run maps most closely to:

- **Pattern 2**: online source identity ≫ batch source identity (+0.23 gain
  on the model classifier). Dynamic recurrence exposes model-specific
  phenotypes.
- **Pattern 6**: apparent own-model advantage largely disappears once the
  visible-feature baseline is compared. Interpret as low-level phenotype
  discrimination, not privileged self-related sensitivity.

**Pattern 5** (self-advantage substantially larger online — the main
positive SPAR pattern) is **not** observed in the pooled data.

## Caveats

- One session per (judge × architecture × cell) block; accuracy granularity
  is 1/6 = 0.167.
- 100 flips within a single online trajectory are not independent
  replicates of the manipulation.
- The 3-source-model design deliberately shares each proposition across
  judges but does not calibrate baseline model discriminability across
  content domains beyond this one task.
- The qwen batch deviation weakens direct comparability of qwen batch
  cells to astra/fable batch cells.
