# 18 · Entropy-gradient replication at ε = .10 and .20 (2026-10-22)

| | |
|---|---|
| Track | 2: game theory (complementary to track 1) |
| Tag | `ENTROPY_GRADIENT_REPLICATION` |
| Run ID | `entropy-gradient-rep-20261022` |
| Game and models | As folder 17. A = Fable (`anthropic/claude-fable-5.1`, effort low), with the minimal paint prompt byte-identical to folders 13 and 17 and no labels. B = a scripted noisy double-alternation; no model, no API calls. |
| Size and cost | 4 sessions × 100 rounds = 400 Fable calls, 0 rejected answers, $3.14 (caps: $5 and 450 calls) |
| Previous / next | [← 17 Entropy-gradient pilot](../17_2026-10-22_paint_circle_entropy_gradient/) · [19 Source labels × noise →](../19_2026-10-27_paint_circle_noise_label_predictability/) |

## What was done

Folder 17 found that between ε = .10 and .20 Fable stops exploiting the noisy pattern. This is the targeted replication that folder 17 recommended, and Chris approved it:

- **Noise levels:** ε = .10 and .20 only.
- **Phase:** the starting phase is reversed relative to folder 17. ε = .10 now starts S S T T, and ε = .20 starts T T S S.
- **Seeds:** two fresh seeds per level (`2026102300 + 100·ε + 1000·k`, k = 1, 2), none used before.

All four sequences were generated and checksummed in [`plan.json`](entropy-gradient-rep-20261022/plan.json) before any call. The analysis code (`src/paint_circle/entropy_gradient.py`) is unchanged from folder 17. Realized flips were 14 and 13 at ε = .10, and 22 and 21 at ε = .20.

## Results

Rounds 51–100, with rounds 1–100 in brackets. Folder 17's sessions are shown for comparison:

| ε | Session | Phase | Fable win | Oracle (realized) | Fable − oracle | EI_oracle | Follows latent pattern | Follows last landing | Win-stay | PI_A |
|---|---|---|---|---|---|---|---|---|---|---|
| .10 | folder 17 | T | .70 (.69) | .84 (.89) | −.14 (−.20) | .59 | .82 | .56 | .49 | .27 |
| .10 | rep 1 | S | .76 (.74) | .80 (.86) | −.04 (−.12) | .87 | .76 | .58 | .55 | .40 |
| .10 | rep 2 | S | .80 (.79) | .86 (.87) | −.06 (−.08) | .83 | .86 | .58 | .55 | .59 |
| .20 | folder 17 | S | .52 (.52) | .76 | −.24 | .08 | .44 | .70 | 1.00 | .31 |
| .20 | rep 1 | T | .54 (.48) | .76 (.78) | −.22 (−.30) | .15 | .46 | .66 | .93 | .41 |
| .20 | rep 2 | T | .42 (.48) | .80 (.79) | −.38 (−.31) | −.27 | .42 | .64 | .85 | .13 |

**Losses over rounds 1–100, by cause:**

| Session | Losses | Flip-induced (Fable followed the pattern, the script flipped) | Fable deviations (Fable left the pattern, the script didn't flip) |
|---|---|---|---|
| ε .10, rep 1 | 26 | 9 | 17 |
| ε .10, rep 2 | 21 | 9 | 12 |
| ε .20, rep 1 | 52 | 11 | 41 |
| ε .20, rep 2 | 52 | 10 | 42 |

**At ε = .20, abandonment of the pattern replicates** in both new sessions, and with the opposite starting phase. So in 3 of 3 sessions, Fable at 20% noise:
- **wins about chance:** .42–.54 late and .48–.52 overall, although .76–.80 was available;
- **follows the latent pattern only about half the time:** .42–.46;
- **falls back on a reactive heuristic instead:** painting where the circle last landed (.64–.70) and staying after wins (.85–1.00).

About 80% of its losses are its own departures from the pattern, not the script's flips.

**At ε = .10, Fable mostly exploits the pattern.** The two new sessions capture most of the available advantage (EI_oracle .83–.87; within 4–6 points of the oracle in rounds 51–100). Folder 17's session (EI_oracle .59) was the weaker case. Even so, most losses at ε = .10 are still Fable's own phase slips rather than flips (17 of 26 and 12 of 21).

**Together:** across 3 sessions per level, the drop-off sits between 10% and 20% noise and is sharp:

| ε | EI_oracle, late (3 sessions) |
|---|---|
| .10 | .59 / .83 / .87 |
| .20 | .15 / .08 / −.27 |

Fable's own predictability (PI_A, .13–.59) varies widely between sessions at both levels. In these noisy conditions it is not a stable signature of the noise level, consistent with folder 17's reading that PI_A tracks the strategy Fable happens to adopt.

## Caveats

- **Still small:** 3 sessions per level in total.
- **Phase and seed are confounded within this replication.** The new sessions used the reversed phase, so the better ε = .10 performance could reflect phase, seed or chance.
- **The shadow benchmark is uninformative here.** It sees essentially no pattern at ε = .20 (PI_B ≈ 0), so EI_shadow is undefined. Realized-oracle EI is the exploitation measure to use.

## Files

- [`entropy-gradient-rep-20261022/plan.json`](entropy-gradient-rep-20261022/plan.json): the 4 sessions, their sequences and SHA-256 checksums, seeds, phases, realized flips and oracle wins, the prompt hash (identical to folder 17's), caps, the launch-order seed and the analysis definition.
- `entropy-gradient-rep-20261022/fable-vs-script__NDA_<phase>_e<ε>_<seed>/rounds.jsonl`: every round, with Fable's full response.
- [`entropy-gradient-rep-20261022/analysis/`](entropy-gradient-rep-20261022/analysis/): `entropy_gradient_sessions.csv`, `entropy_gradient.json` and `entropy_gradient.png`.
- Code (unchanged from folder 17): `src/paint_circle/entropy_gradient.py`, `src/paint_circle/scripted.py`, `src/paint_circle/run.py`.

## Re-running

```bash
PYTHONPATH=src python -m paint_circle.entropy_gradient track2_game_theory/18_2026-10-22_paint_circle_entropy_gradient_replication/entropy-gradient-rep-20261022
```
