# 19 · Source labels × noise: exploitation and exploitability (2026-10-27)

| | |
|---|---|
| Track | 2: game theory (complementary to track 1) |
| Tag | `NOISE_LABEL_PREDICTABILITY_PILOT` |
| Run ID | `noise-label-20261027` |
| Game and models | Paint-and-circle matching pennies. A = Fable (`anthropic/claude-fable-5.1`, Anthropic provider, effort low, no temperature setting, no tools). B = a scripted noisy double-alternation; no model, no API calls. |
| Size and cost | 3 noise levels × 3 source labels = 9 sessions × 100 rounds. 900 valid Fable answers, 1 re-request (a provider content-filter stop with an empty answer, round 62, ε = .10 self). $8.03 (caps: $10 and 1,000 calls). All 9 sessions complete. |
| Previous | [← 18 Entropy-gradient replication](../18_2026-10-22_paint_circle_entropy_gradient_replication/) |

## Question

Does believing the other player is *oneself* change how Fable exploits uncertain structure in that player's moves, and how predictable Fable's own moves become, compared with believing it is a different language model or being told nothing?

## What was done

| | |
|---|---|
| Design | 3 × 3. Noise ε = .10, .15, .20 × source label: none / self ("…another instance of yourself, the same language model") / other ("…a different language model"). The wording is identical to folders 10–15. All labels are cover stories; the opponent is a script. |
| Opponent | **One frozen sequence per noise level, replayed under all three labels.** Each is a noisy double-alternation, with phases alternating T, S, T across levels and new seeds `2026102700 + 100·ε`. Sequences, latent patterns, flips and checksums are in [`plan.json`](noise-label-20261027/plan.json). |
| Exploitability | **A prospective shadow Proteus** (the PACA nine-channel algorithm, unchanged). Each round, before Fable's answer was scored, it forecast Fable's choice from the same last-50 completed rounds Fable was shown, using Fable's own choices and win bits. Every logged forecast was audited against an offline recomputation, and all 900 match. It has no effect on play. |
| Prompts | Byte-identical to earlier experiments. Prompt hashes: none `6afb6a52…` (= folders 13, 17, 18), self `491ae49a…`, other `06e5697c…`. |

**Realized noise.** The ε = .15 sequence came out noisier than designed (21 flips, realized oracle .79). That is almost the same as the ε = .20 sequence (22 flips, .78). The plan was frozen when the sequences were generated, so they were kept. **The two higher levels are effectively one noise level in this pilot.**

## Results

Rounds 51–100, the primary window. "Oracle" is the realized win rate of always following the latent pattern on that sequence. EI_oracle is NA if the oracle is .55 or below.

| ε | Label | Fable win | Oracle | Fable − oracle | EI_oracle | Follows pattern | PI_A (prospective) | Shadow active |
|---|---|---|---|---|---|---|---|---|
| .10 | none | .72 | .86 | −.14 | .61 | .82 | .27 | .54 |
| .10 | self | .52 | .86 | −.34 | .06 | .54 | .02 | .18 |
| .10 | other | .60 | .86 | −.26 | .28 | .66 | .12 | .36 |
| .15 | none | .52 | .80 | −.28 | .07 | .60 | −.02 | .72 |
| .15 | self | .46 | .80 | −.34 | −.13 | .46 | .09 | .96 |
| .15 | other | .48 | .80 | −.32 | −.07 | .44 | −.02 | .60 |
| .20 | none | .54 | .74 | −.20 | .17 | .60 | .09 | .44 |
| .20 | self | .46 | .74 | −.28 | −.17 | .64 | .00 | .04 |
| .20 | other | .60 | .74 | −.14 | .42 | .66 | .04 | .18 |

**Self − other, rounds 51–100** (descriptive; one session per cell):

| ε | Fable win | Follows pattern | PI_A | Shadow activation |
|---|---|---|---|---|
| .10 | −.08 | −.12 | −.11 | −.18 |
| .15 | −.02 | +.02 | +.10 | +.36 |
| .20 | −.14 | −.02 | −.04 | −.14 |

All metrics for both windows, every round's forecast, and the label contrasts are in [`analysis/`](noise-label-20261027/analysis/):
- `session_summary.csv`, `round_metrics.csv`, `results.json`
- figures: [`exploitation_by_noise.png`](noise-label-20261027/analysis/exploitation_by_noise.png), [`predictability_by_noise.png`](noise-label-20261027/analysis/predictability_by_noise.png), [`exploitation_vs_exploitability.png`](noise-label-20261027/analysis/exploitation_vs_exploitability.png)

### What it shows

- **Noise response replicates.** With no label, Fable partly exploits the pattern at ε = .10 (EI_oracle .61, in the range of folders 17–18, .59–.87). At the two higher noise levels it is near chance (.07 and .17), as in folders 17–18.
- **At ε = .10, both identity labels reduced exploitation, and "self" reduced it most.**
  - Fable's win rate: none .72 > other .60 > self .52.
  - Pattern-following: .82 > .66 > .54.
  - The no-label value sits inside folders 17–18's unlabelled range. Both labelled values are below that range, self far below it.
- **At ε = .15 and .20, label effects can't be read.** Fable has already largely abandoned the pattern without any label (a floor), and the label ordering is inconsistent: at .20, "other" exploits *more* than "none".
- **Exploitability moves with exploitation at ε = .10.** PI_A follows the same order (none .27 > other .12 > self .02), as does shadow activation. Labels that pushed Fable off the pattern also made it less predictable. Across all nine sessions, in rounds 51–100, exploitation and exploitability are positively related:
  - r = .57 between Fable − oracle and PI_A;
  - r = .68 between pattern-following and PI_A.

  But this relationship is not stable: over rounds 1–100 it reverses (r = −.13 and −.37), driven by streaky early play in the ε = .15 sessions. With a non-reactive opponent, Fable has no reason to hide, so lower PI_A here means it stopped tracking the pattern, not that it evaded.
- **The shadow's forecasts are poorly calibrated.** Its mean log2 loss (1.00–2.03 bits) is at or above the rolling-marginal baseline (0.91–1.40) in every cell, so its forecasts are overconfident when they fire. PI_A is accuracy-based and remains interpretable. Read it as predictability *to this particular Proteus*, not as general randomness (see the discussion of the index's limits in folders 17–18).

### Is there a replication-worthy self-vs-other interaction?

**Possibly at ε = .10 only, and it needs replication before any claim.**

- **The evidence for:** self < other < none on exploitation, pattern-following and exploitability.
- **Why it is weak:**
  - It is one session per cell.
  - The self–other gap (win −.08; EI_oracle .06 vs .28) is within the session-to-session spread seen without labels in folders 17–18 (EI_oracle .59–.87).
  - Folder 11's prespecified test found Fable's self and other labels indistinguishable, and folders 14–16 found label effects that track expected structure, not self.
- **The more robust-looking result here is that *any* language-model label reduced exploitation at ε = .10**, compared with no label. That fits folder 16: labels that imply structure prompt Fable to reason more about the opponent.
- **A useful follow-up:** at ε = .10, run 4–5 sessions per label (none / self / other), with fresh sequences and both phases. That would be roughly 12–15 sessions, about $11–14, and would test both the "any label" effect and the self-vs-other gap. Not run; it needs approval.

## Caveats

- **Descriptive only:** one session per cell; no significance tests.
- **Noise and sequence are confounded:** with one sequence per level, the noise comparison is confounded with phase and sequence. Realized noise at ε = .15 and .20 is nearly equal.
- **Histories diverge after round 1:** the label is the initial intervention, but Fable's own choices then make the histories, and so the later prompts, differ between labels.
- **A label effect is not self-knowledge:** a self-label effect would not show accurate self-modelling; it could reflect a prior about the category of source.

## Files

- [`noise-label-20261027/plan.json`](noise-label-20261027/plan.json): the 9 sessions; the 3 sequences (latent, realized, flips, SHA-256, expected and realized oracle); the prompts and their hashes; caps; the launch-order seed; the test-file hash; the analysis fixed before the run.
- `noise-label-20261027/fable-vs-script__NDA_<phase>_e<ε>_<seed>__label-<label>/rounds.jsonl`: every round with Fable's full response, the cost, and the frozen `shadow_forecast_A` (probability, activity, channel, window size, window hash, timestamp). The `rejected_attempts.jsonl` files hold re-requests.
- [`noise-label-20261027/analysis/`](noise-label-20261027/analysis/): the tables and figures listed above.
- Code:
  - `src/paint_circle/run.py`: the prospective shadow (`prospective_shadow: true`).
  - `src/paint_circle/noise_label.py`: the analysis and forecast audit.
  - `src/paint_circle/entropy_gradient.py`, `src/paint_circle/scripted.py`, `src/paint_circle/shadow.py`: unchanged.
- Tests: `tests/test_paint_circle.py` checks that:
  - the circle sequence is identical across labels;
  - only the disclosure paragraph differs;
  - every forecast is limited to the last 50 completed rounds, uses A's own win bits, and matches the offline recomputation;
  - the audit refuses a tampered forecast.

## Re-running

```bash
PYTHONPATH=src python -m paint_circle.noise_label track2_game_theory/19_2026-10-27_paint_circle_noise_label_predictability/noise-label-20261027
```
