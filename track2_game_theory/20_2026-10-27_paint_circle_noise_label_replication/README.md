# 20 · Source-label replication at 10% noise: 5 scripts × 5 labels (2026-10-27)

| | |
|---|---|
| Track | 2: game theory (complementary to track 1) |
| Tag | `NOISE_LABEL_REPLICATION_5SOURCES` |
| Run ID | `noise-label-replication-20261027` |
| Game and models | Paint-and-circle matching pennies. A = Fable (`anthropic/claude-fable-5.1`, Anthropic provider, effort low, no temperature setting, no tools). B = a scripted noisy double-alternation; no model, no API calls. |
| Size and cost | 5 scripts × 5 source labels = 25 sessions × 100 rounds. 2,500 valid Fable answers, 0 re-requests. **$21.94** (caps: $32 and 2,600 calls; estimate $22–26). All 25 sessions complete. |
| Previous | [← 19 Source labels × noise](../19_2026-10-27_paint_circle_noise_label_predictability/) |

## Question

Folder 19 found, at 10% noise and with one session per cell, that Fable exploited the noisy pattern in the order none > other LLM > self (win .72 / .60 / .52), and that its own predictability to a shadow Proteus fell in the same order. This study asks two things:
- **Does that replicate across independent script sequences?**
- **Do two new cover stories, a human and a dead salmon, behave like the language-model labels?**

## What was done

| | |
|---|---|
| Design | ε = .10 only. **Five new frozen scripts** (blocks 1–5): noisy double-alternation, starting phases T, S, T, S, T, seeds 2026102731–35. **Each script is replayed under all five labels**, so a block is a matched set of 5 sessions with the identical circle sequence. |
| Labels | Disclosure paragraph "Another decision-maker decides where the blue circle lands. The other decision-maker is …": **none** (no paragraph) / **self** "another instance of yourself, the same language model" / **other** "a different language model" / **human** "a human" (new) / **salmon** "a dead salmon" (wording from folder 14). none/self/other prompts are byte-identical to folder 19 (hashes `6afb6a52…`, `491ae49a…`, `06e5697c…`); human `cce9557b…`, salmon `ccf1d797…`. |
| Exploitability | As folder 19: a prospective shadow Proteus (PACA nine channels, unchanged, W = 50) forecasts each Fable choice from the same last-50 completed rounds before the call. **All 2,500 logged forecasts match the offline recomputation**, and every session's circle sequence matches its frozen checksum. |
| Run | Plan, prompts, hashes, caps and analysis frozen in [`plan.json`](noise-label-replication-20261027/plan.json) before any call. Sessions launched in a seeded random order interleaving labels and scripts, 13 at a time. |
| Unit of replication | The script block (n = 5). Paired within-block label differences; exploratory, no confirmatory tests. |

**Realized noise varied across scripts** (frozen as generated). Flips in rounds 51–100 were 2, 6, 11, 2 and 6, so the oracle's late win rate is .96, .88, .78, .96 and .88. Blocks 1 and 4 are nearly clean in the late window; block 3 is the noisiest.

## Results

### Per session, rounds 51–100

Fable win rate, with PI_A (prospective) in brackets:

| Block (phase, late oracle) | none | self | other | human | salmon |
|---|---|---|---|---|---|
| 1 (T, .96) | .88 (.80) | .88 (.74) | .88 (.59) | .90 (.66) | .84 (.07) |
| 2 (S, .88) | .88 (.59) | .86 (.47) | .84 (.61) | .82 (.50) | .82 (.24) |
| 3 (T, .78) | .66 (.43) | .52 (.23) | .54 (.27) | .62 (.22) | .58 (.19) |
| 4 (S, .96) | .84 (.71) | .88 (.71) | .84 (.67) | .90 (.79) | .92 (.74) |
| 5 (T, .88) | .74 (.24) | .60 (.06) | .74 (.07) | .72 (.14) | .62 (.04) |
| **Mean** | **.80 (.55)** | **.75 (.44)** | **.77 (.44)** | **.79 (.46)** | **.76 (.26)** |
| Mean EI_oracle | .75 | .59 | .65 | .72 | .62 |
| Mean pattern-following | .87 | .82 | .84 | .84 | .80 |

### Paired contrasts, rounds 51–100

Per-block differences for blocks 1–5:

| Contrast | Win: per block | Win: mean (median) | PI_A: per block | PI_A: mean (median) |
|---|---|---|---|---|
| **self − other** (primary) | 0, +.02, −.02, +.04, −.14 | −.02 (0) | +.14, −.14, −.03, +.04, −.02 | .00 (−.02) |
| self − none | 0, −.02, −.14, +.04, −.14 | −.05 (−.02) | −.06, −.13, −.19, −.01, −.18 | **−.11 (−.13), 5 of 5 negative** |
| other − none | 0, −.04, −.12, 0, 0 | −.03 (0) | −.21, +.01, −.16, −.05, −.16 | −.11 (−.16), 4 of 5 negative |
| human − none | +.02, −.06, −.04, +.06, −.02 | −.01 (−.02) | −.14, −.10, −.21, +.08, −.10 | −.10 (−.10), 4 of 5 negative |
| salmon − none | −.04, −.06, −.08, +.08, −.12 | −.04 (−.06) | −.73, −.35, −.24, +.03, −.20 | −.30 (−.24), 4 of 5 negative |
| self − human | −.02, +.04, −.10, −.02, −.12 | −.04 (−.02) | +.08, −.03, +.02, −.08, −.08 | −.02 (−.03) |
| self − salmon | +.04, +.04, −.06, −.04, −.02 | −.01 (−.02) | +.67, +.23, +.04, −.03, +.02 | +.18 (+.05) |

Over rounds 1–100, PI_A is lower than with no label in 5 of 5 blocks for both self and other (−.07 and −.08 on average); self − other is again about 0 (win −.002, PI_A +.007).

All metrics for both windows, every logged forecast and every per-block difference (including other − human, other − salmon, EI_oracle and pattern-following) are in [`analysis/`](noise-label-replication-20261027/analysis/):
- `session_summary.csv`, `round_metrics.csv`, `paired_block_contrasts.csv`, `results.json`
- figures: [`exploitation_by_label_paired.png`](noise-label-replication-20261027/analysis/exploitation_by_label_paired.png), [`predictability_by_label_paired.png`](noise-label-replication-20261027/analysis/predictability_by_label_paired.png), [`exploitation_vs_exploitability.png`](noise-label-replication-20261027/analysis/exploitation_vs_exploitability.png), [`ten_round_trajectories.png`](noise-label-replication-20261027/analysis/ten_round_trajectories.png)

### What it shows

- **Fable exploits a 10% noisy pattern well with no label.** Late win .80 on average, EI_oracle .75, consistent with folders 17–19 (.59–.87).
- **The self-vs-other gap from folder 19 did not replicate.** Self − other in win rate is 0, +.02, −.02, +.04 and −.14 across blocks (median 0); in PI_A it is centred on zero. Only block 5 repeats folder 19's pattern. On these data, "another instance of yourself" and "a different language model" have the same effect.
- **Label effects on winning are small and concentrated in two scripts.** Every label's mean late win is .75–.79 against .80 with no label. The losses come mostly from blocks 3 and 5, both T-phase scripts and, for block 3, the noisiest late window. In the cleanest scripts (blocks 1 and 4, 2 late flips) every label exploits the pattern about equally. Folder 19's ε = .10 script was also T-phase with a late oracle of .86, which may be why it showed a larger spread. This is a post-hoc reading, not a tested effect.
- **Any label makes Fable less predictable to Proteus, more consistently than it changes winning.** PI_A is lower than with no label in 5/5 blocks for self and 4/5 for other, human and salmon (late), and self, other and human reduce it by about the same amount (−.10 to −.11). This is the most consistent label effect in the study, and it is not specific to self or to language models.
- **Salmon is the outlier, mainly on predictability.**
  - It produced the largest PI_A drop (−.30 on average). It was also the slowest starter: 10-round win rates of .44 and .48 in rounds 1–20, and the lowest full-game exploitation (EI_oracle .43 vs .54–.61).
  - By the late window it exploits about as well as self and other (win .76).
  - In block 1 it shows a dissociation: Fable followed the pattern 88% of the time and won .84, yet PI_A was .07, and the shadow's log loss (1.39 bits) was above the marginal baseline. Its streaky early play still filled the shadow's 50-round window and misled its channels. **A low PI_A here means the shadow was misled, not that Fable's play was unstructured.**
- **Human behaves like the other agent labels, closest to no label on winning.** Human − none is −.01 in win rate (3 of 5 negative), with the same PI_A reduction as self and other.

## Synthesis

**(a) Does the self-versus-other pattern replicate across scripts?** No. Across five independent matched scripts, self − other is centred on zero for exploitation (median 0; 2 blocks negative, 2 positive, 1 tie) and for PI_A. Folder 19's ordering (self < other) reappears in one block of five. Folder 19's single-script result should be treated as an unreplicated signal, as its README anticipated.

**(b) Do human and dead salmon behave like generic labels or meaningful controls?**
- **Human acts like a generic agent label.** It lowers PI_A as much as self and other, with a slightly smaller effect on winning.
- **Salmon is a meaningful contrast, but not in the direction a self story needs.** It disrupts early exploitation and, through the shadow's window, late predictability more than any model label. So an implausible or mindless source description changes play at least as much as "yourself".

Together, the controls make a self-specific account of folder 19 harder to sustain. The consistent effect is that **any source description lowers predictability**, with the size of the change set by the kind of source described (folders 15–16 found the same split between structure-implying and randomness-implying labels).

**(c) How do exploitation and Proteus exploitability covary?** Positively, but much of it is between scripts. Across the 25 sessions, Fable − oracle and PI_A correlate r = .70 in rounds 51–100 (pattern-following and PI_A, r = .70; full game, r = .80). That is driven largely by script difficulty (between-block r = .80 late, .99 full). Within blocks, the correlation is r = .44 late (.46 full; .45 without salmon). So when a label pushes Fable off the pattern it tends also to become less predictable, but the coupling is loose: PI_A can drop without any loss in winning (salmon, block 1; other, block 1). As in folder 19, the opponent is not reactive, so lower predictability is not evasion.

**(d) What, if anything, merits a more rigorous preregistered replication?**
- **Not self vs other** at this noise level; the effect is near zero with a 5-block paired design.
- **Candidate 1: the "any label lowers PI_A" effect,** using a model-agnostic predictor alongside Proteus so the shadow's window artefacts (salmon block 1) cannot drive it. It was in the same direction in 17 of 20 label-versus-none late comparisons (5 of 5 for self).
- **Candidate 2: script dependence.** Labels mattered most in the T-phase and noisier late-window scripts. A preregistered design that crosses phase with late-window noise would test whether framing matters mainly when the evidence is weaker, as folders 15–19 suggest.
- **Either would need more blocks** (≈ 10–15) to detect differences of the size seen here (about .05 in win rate).

## Caveats

- **Exploratory:** n = 5 script blocks; no significance tests. Rounds within a session are not independent replications.
- **Script heterogeneity:** realized late noise ranged from 2 to 11 flips. Phase is confounded with the script draw (T-phase blocks 1, 3, 5 include both the cleanest and the noisiest scripts).
- **Histories diverge after round 1:** matched scripts control the stimulus, not the feedback trajectory.
- **PI_A is relative to one algorithm,** with a 50-round window that carries early play into the late window (see salmon block 1). Its calibration depends on the script. Late-window log loss beats the rolling-marginal baseline in only 12 of 25 sessions: all of block 4, but none of block 3.
- **A label effect is not self-knowledge** (see folder 19).

## Files

- [`noise-label-replication-20261027/plan.json`](noise-label-replication-20261027/plan.json) (sha256 `1e5e666f…`): the 25 sessions in launch order; the 5 blocks (latent pattern, sequence, SHA-256, flips, expected and realized oracle); prompts and hashes; model settings; caps; the launch-order seed; the git head, test-file hash and analysis-code hash at freeze; the prespecified analysis.
- `noise-label-replication-20261027/fable-vs-script__NDA_<phase>_e10_<seed>__label-<label>/rounds.jsonl`: every round, with Fable's full response, cost and the frozen `shadow_forecast_A`.
- `progress.log` and `status.json`: the run log ($21.94 spent).
- [`noise-label-replication-20261027/analysis/`](noise-label-replication-20261027/analysis/): the tables and figures listed above.
- Code:
  - `src/paint_circle/noise_label_rep.py`: the paired-block analysis. It reuses the folder 19 forecast audit (`noise_label.round_rows`) and `entropy_gradient.gradient_metrics`.
  - `src/paint_circle/game.py` gains the `human` identity sentence; nothing else changed.
- Tests: `tests/test_paint_circle.py` checks that:
  - the human and salmon disclosure texts are exact;
  - in a 2-block × 5-label offline dry run, circle sequences are identical within each block;
  - prompts differ only in the disclosure paragraph;
  - the paired contrasts are computed per block.

  The folder 19 tests (strict 50-round forecast window, A's own win bits, audit refusing tampered forecasts, budget guards) still pass: 36 of 36.

## Re-running

```bash
PYTHONPATH=src python -m paint_circle.noise_label_rep track2_game_theory/20_2026-10-27_paint_circle_noise_label_replication/noise-label-replication-20261027
```
