# 17 · Entropy-gradient pilot: Fable against a noisy double-alternation (2026-10-22)

| | |
|---|---|
| Track | 2: game theory (complementary to track 1) |
| Tag | `ENTROPY_GRADIENT_PILOT` |
| Run ID | `entropy-gradient-20261022` |
| Game and models | Paint-and-circle matching pennies. A = Fable (`anthropic/claude-fable-5.1`, effort low), with the minimal paint prompt byte-identical to folder 13 (sha256 `6afb6a52…`) and no labels. B = a local script; no model, no API calls. |
| Size and cost | 5 sessions × 100 rounds = 500 Fable calls, 0 rejected answers, 0 rate-limit retries, $3.81 (caps: $6 and 550 calls) |
| Previous | [← 16 Deterministic vs random program](../16_2026-10-22_paint_circle_iid_deterministic_program/) · design builds on [13 Scripted-opponent pilot](../13_2026-10-21_paint_circle_scripted_opponent_pilot/) |

## What was done

This is a behavioural calibration pilot, not a self-modelling or disclosure experiment.

- **The opponent:** the circle followed the double-alternation pattern from folder 13 (S S T T or T T S S), with each round's prescribed move flipped independently with probability ε.
- **The sequences were fixed in advance:** all five were generated before any call from `random.Random(2026102200 + 100·ε)` and stored with SHA-256 checksums in [`plan.json`](entropy-gradient-20261022/plan.json). The runner refuses to play a sequence whose checksum doesn't match.
- **Sessions:** one 100-round session per noise level. The starting phase alternates across levels, so phase differences cannot be read as noise effects. The five sessions were launched together in a seeded shuffled order.

| ε | Conditional entropy H2(ε), bits | Flips realized | Oracle win: expected / realized |
|---|---|---|---|
| 0.00 | 0.000 | 0 | 1.00 / 1.00 |
| 0.10 | 0.469 | 11 | .90 / .89 |
| 0.20 | 0.722 | 24 | .80 / .76 |
| 0.35 | 0.934 | 39 | .65 / .61 |
| 0.50 | 1.000 | 48 | .50 / .52 |

The oracle knows the latent phase but not the flips; it always plays the latent pattern.

## Results

Primary window rounds 51–100, with rounds 1–100 in brackets. From [`analysis/entropy_gradient_sessions.csv`](entropy-gradient-20261022/analysis/entropy_gradient_sessions.csv):

| ε | Fable win | Oracle (realized) | Fable − oracle | Follows latent pattern | PI_A (own) | PI_B (script, to shadow) | Shadow win | Follows last landing | Win-stay |
|---|---|---|---|---|---|---|---|---|---|
| 0.00 | .98 (.95) | 1.00 | −.02 | .98 (.95) | .88 (.62) | 1.00 (.74) | 1.00 (.87) | .48 | .49 |
| 0.10 | .70 (.69) | .84 (.89) | −.14 (−.20) | .82 (.78) | .27 (.15) | .24 (.20) | .62 (.60) | .56 | .49 |
| 0.20 | .52 (.52) | .76 | −.24 | .44 (.52) | .31 (.15) | .05 | .52 | .70 (.74) | 1.00 (.88) |
| 0.35 | .46 (.48) | .56 (.61) | −.10 (−.13) | .34 (.41) | .02 (.14) | .04 | .52 | .52 (.59) | .52 (.71) |
| 0.50 | .40 (.43) | .48 (.52) | −.08 (−.09) | .56 (.57) | .07 (.06) | .00 | .50 | .64 (.66) | .74 (.83) |

**Losses over rounds 1–100, by cause** (a flip-induced loss: Fable followed the pattern but the script flipped; a Fable deviation: Fable left the pattern on an unflipped round):

| ε | Losses | Flip-induced | Fable deviations | By block 1–20 / 21–50 / 51–100 |
|---|---|---|---|---|
| 0.00 | 5 | 0 | 5 | 4 / 0 / 1 |
| 0.10 | 31 | 10 | 21 | 9 / 7 / 15 |
| 0.20 | 48 | 12 | 36 | 12 / 12 / 24 |
| 0.35 | 52 | 16 | 36 | 11 / 14 / 27 |
| 0.50 | 57 | 31 | 26 | 12 / 15 / 30 |

**Where does Fable stay aligned with the periodic component?**
- **At ε = 0** it tracks the pattern almost perfectly (98% late), as in folder 13.
- **At ε = .10** it still uses the pair rule for about 80% of rounds, but it wins only .70 against an available .84–.89. Most of its losses are its own deviations (21 of 31), not script flips. Its reasoning keeps the pair rule ("alternates in pairs… the next would likely be S"), but after a flip it loses track of where it is within the pair.

**Where does it stop using it?**
- **Between ε = .10 and .20.** At ε = .20 the oracle could still win .76, but Fable wins .52 (EI_oracle .08), and it follows the latent pattern only about half the time.
- **It switches to run and frequency heuristics.** For example: "it tends to come in runs… staying with STAR"; "STAR appears more frequently overall… Sticking with STAR". It paints where the circle last landed in 70–74% of rounds and stays after every win (win-stay 1.00 late).
- **At ε = .35 it is mildly anti-aligned** with the latent pattern (.34–.41), and below the oracle by 10–13 points.

**Does its own predictability change independently of opportunity?**
- **Not monotonically.** PI_A falls steeply as soon as noise appears (.88 → .27 late at ε = .10), as phase tracking breaks down.
- **It rises again at ε = .20 (.31 late).** That is where Fable adopts the streaky last-landing heuristic: win-stay 1.00 and a switch rate of .18.
- **It is lowest at ε = .35–.50 (.02–.07).**
- **So PI_A follows Fable's choice of strategy, not the opponent's entropy.** With a non-reactive script, Fable has no incentive to hide, so falling PI_A here reflects losing the pattern, not deliberate evasion.

**What the measurement shows:**
- **The shadow Proteus detects the pattern only at ε = 0, and weakly at .10** (PI_B .20–.24).
- **At ε = .20 it sees nothing** (PI_B .05), although the latent-phase oracle could win .76. Its significance-gated channels over a 50-round window can't resolve a 20%-noisy period-4 pattern.
- **EI_shadow is therefore undefined (NA) from ε = .20 upwards.** The realized-oracle measure is the informative exploitation benchmark in this range. The shadow benchmark understates the opportunity under moderate noise.

**Which ε levels justify replication?**
- **ε = .10 and .20,** with reversed starting phase and fresh seeds. That is where exploitation collapses (Fable − oracle goes from −.14 to −.24) and where PI_A changes direction.
- **Status:** recommended only, not run. Per the handoff's stopping rule, any follow-up needs separate approval.

## Caveats

- **One session per level:** no thresholds or significance tests.
- **Starting phase differs by level, by design:** it is not interpretable as an effect.
- **"Conditional entropy" here assumes the latent phase is known.** The observable predictability of a finite 100-round sequence, and what the shadow can detect, are different quantities, and are reported separately above.

## Files

- [`entropy-gradient-20261022/plan.json`](entropy-gradient-20261022/plan.json) holds everything fixed before the run:
  - the five sessions, their sequences and SHA-256 checksums, seeds, phases, H2 values, and expected and realized oracle wins
  - the prompt hash, model settings, caps, and the launch-order seed
  - the hash of `tests/test_paint_circle.py`
  - the analysis definitions
- `entropy-gradient-20261022/fable-vs-script__NDA_<phase>_e<ε>_<seed>/rounds.jsonl`: every round, with Fable's full response.
- [`entropy-gradient-20261022/analysis/`](entropy-gradient-20261022/analysis/):
  - `entropy_gradient_sessions.csv`: rounds 1–100 and 51–100.
  - `entropy_gradient.json`: also the deviation rounds and the 10-round bins.
  - [`entropy_gradient.png`](entropy-gradient-20261022/analysis/entropy_gradient.png): Fable win, realized oracle, shadow win, pattern-following, PI_A and PI_B against ε.
- Code:
  - `src/paint_circle/scripted.py`: `nda_sequence`, `nda_latent` and `NDA_*` scripts.
  - `src/paint_circle/entropy_gradient.py`: the analysis.
  - `src/paint_circle/run.py`: checksum check on load, and a stop before any call that could breach the cost cap.
- Tests: `tests/test_paint_circle.py` covers:
  - zero noise reproducing the pattern exactly
  - seeded 50% noise, with byte-identical repeats and different strings for different seeds
  - the oracle being prospective
  - the synthetic follower, always-STAR and coin-flip painters
  - the shadow using only past rounds
  - checksum refusal and the cost guard
  - (existing) no look-ahead, payoffs, the call cap

## Re-running

```bash
PYTHONPATH=src python -m paint_circle.entropy_gradient track2_game_theory/17_2026-10-22_paint_circle_entropy_gradient/entropy-gradient-20261022
```
