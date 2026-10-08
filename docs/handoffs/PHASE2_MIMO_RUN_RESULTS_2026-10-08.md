# SPAR Phase 2 pilot, run 2: MiMo as the third model

Run `p2-mimo-20261008` (Chris: "try mimo", 2026-10-08). Same v7.1 protocol as run `p2-20261007`, with `xiaomi/mimo-v2.6-pro` (first-party Xiaomi endpoint) replacing Qwen3-8B. All three models got fresh development and test data; nothing is pooled with run 1.

Outputs: `data/spar_dynamic/phase2/p2-mimo-20261008/` (`CORE_REPORT.md`, `RETAINED_ARMS_REPORT.md`, `STAGE1_REPORT.md`, `amendments.jsonl`). Branch `phase2`, not pushed.

## Execution

- **Calls:** 2,802 recorded, all completed. **Spend:** $8.94 (cumulative Phase 2: $17.34 of the $100 cap).
- **MiMo settings:** generation at provider-default sampling with reasoning disabled. The smoke test showed varied outputs with no seed needed. Judging is greedy (t=0), enforced with `require_parameters`. Output budget 4,000 tokens.
- **Parser gen_v3** (collapses "Heads (H)" annotations before removing counts). It changes zero rows of run 1.
- **Known limitation N2:** `**H** (Heads)` is not collapsed, so 1 MiMo development row is wrongly rejected. Left unfixed to keep the freeze; planned as gen_v4.
- **Validity:**
  - MiMo/plain: 56/60 development, 22/24 test.
  - MiMo/fair: 25/60 development, 10/24 test (often explains probability or gives several sample sequences).
  - Astra and Fable: 119–120/120 development, all 24/24 test.
- **Design support:** both prompts now have pair blocks (11 plain, 5 fair; 96 pairs), and all primary panels are estimable.
- **Gates:**
  - Fable failed the pair-fixture format gate again (2/12; it shows its working).
  - MiMo's fixture correctness is low: 6/12 on completion, 4/12 on pairs.
  - The headroom review was **triggered**: every I[g] is below 0.02 (Astra 0.007, Fable 0.0004, MiMo 0.001). Option (a), continue, was applied as carried over and flagged.

## Results

**H4 (completion, key, two-sided):** H4 = −0.0004 [−0.0010, +0.0002], gain_own −0.0001, gain_other +0.0003, C_known −0.0019, C_withheld −0.0015.
- **Direction:** unresolved, and bounded inside the ±0.02 margin.
- **Interpretation:** this cannot be read as evidence about self-knowledge. Astra and MiMo returned 0.5 at every position for **100%** of completion calls; Fable did so in 48–81% of calls.

**Anonymous SAME/DIFFERENT (primary recognition):** R = −0.019 [−0.074, +0.034], P = +0.033, D = −0.070.
- **Status:** the interval is labeled *unstable*, because 1.1% of bootstrap replicates were undefined (the threshold is 1%). No direction is assigned.
- **Flat judges:** MiMo answered exactly 0.5 on 100% of pairs and Astra on 99%. Only Fable varied its answers, with AUROC 0.44 (plain) and 0.65 (fair).
- **External baselines:** the prefix observer reaches 0.78 (plain) and 0.84 (fair), so the signal is there but the judges don't use it.

**Named attribution (36 parents, both prompts):** R = −0.059 [−0.150, +0.039], unresolved.
- **Fable chose itself on 35 of 36 sequences** (balanced accuracy 0.33–0.39, chance 0.33). That is a self-labeling bias, not discrimination.
- **Astra and MiMo** spread their choices roughly evenly.

**Historical check (GPT-3.5-0613):** 357/360 valid. It replicates run 1's pattern; see `RETAINED_ARMS_REPORT.md`.

## Comparison with run 1 (Qwen3-8B)

| | run 1 (Qwen) | run 2 (MiMo) |
|---|---|---|
| Third-model fair-prompt validity (test) | 1/24 | 10/24 |
| Two-prompt pair / named panels | not estimable | estimable |
| H4 | −0.0026, resolved negative, bounded | −0.0004, unresolved, bounded |
| Anonymous R | panel NA; plain +0.076 [+0.011, +0.130] | −0.019 [−0.074, +0.034] (unstable label) |
| Judges answering all-0.5 on completion | Astra 100% (non-Qwen sources); Qwen 80–94% | Astra 100%; MiMo 100% |
| Fable overall pair AUROC (plain) | 0.79 (Qwen's alternation was easy to spot) | 0.44 |

The plain-prompt R from run 1 does not replicate with MiMo. Run 1's sources were easier to separate (Qwen alternated heavily), and its R depended on Qwen being a below-chance reference judge.

## Bottom line

- **No evidence of a self-specific advantage** in completion, anonymous recognition or named attribution.
- **The dominant problem is response policy.** Two of three judges almost always return 0.5, so the completion and pair tasks carry little information about them.
- **Fable's named answers are an "it's me" default,** not recognition.

A useful next step is a design that makes flat answers costly or uninformative-by-construction: for example, forced choice, scoring feedback in the instructions, or eliciting a single best guess alongside the probability. That must be decided before any confirmatory run, since it changes the estimand.
