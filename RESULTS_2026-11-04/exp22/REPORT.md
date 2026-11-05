# First-level Blind Coder: can a model write a better predictor of its own game choices?

Track 2, folder 22 · 2026-11-04 · protocol `FirstLevelBlindCoder_v1` · plan `plan/run_plan.json` (sha256 `9becd791…`,
frozen at `27e2cbe`; approval [APPROVAL.md](../../track2_game_theory/22_2026-11-04_first_level_blind_coder/APPROVAL.md))

## Answers

- **Who wrote the better predictor of Astra?** Astra. Mean Brier 0.226 for Astra's programs against 0.273 for Fable's: better
  by **0.046**, in 9 of 10 blocks.
- **Who wrote the better predictor of Fable?** Also Astra. Astra's programs score 0.214 against 0.256 for Fable's own. The
  registered Fable own-author advantage is therefore **−0.041**, negative in all 10 blocks.
  - So there is no reciprocal own-model advantage in any block. The balanced self advantage is +0.003. The pattern is a
    general author advantage: Astra writes better predictors of both players.
  - Only Astra's programs beat a constant 0.5 (Brier 0.25), in all 20 of its generations. Fable's beat 0.5 in 5 of 20.
- **Did telling an author which player to simulate help?** No.
  - Scoring each author's two programs on the swapped player changes loss by −0.005 (Astra) and +0.002 (Fable). Positive in
    4 and 5 of 10 blocks.
  - The name in the prompt made no useful difference to either author's predictions.
- **Did the code capture how each player responds to wins and losses?** No.
  - Astra switches more after *winning* (65% vs 41% after losing, gap +0.24). Fable barely differs (58% vs 54%, gap +0.04).
  - Astra's programs predict almost no gap (+0.004 for Astra, −0.036 for Fable).
  - Fable's programs predict the opposite sign, more switching after losses (−0.14 for Astra, −0.13 for Fable). They also
    predict a high switch rate overall (0.55–0.72).
  - Neither author recovered either player's gap. The observed gaps helped motivate the pilot and were kept out of the
    prompts, so this is a known-answer check, not a discovery.

This is a descriptive pilot. Its evidence is 16 contributing games and one archive. The 10 program draws per cell and the 20
rounds per game are not independent games.

## A. Primary 2 × 2 (Brier; lower is better)

Each program's loss is averaged within each seat-game over rounds, then over games within each seat × opponent stratum, then
equally over the six strata. These programs' losses are then averaged over the 10 complete blocks. Each target's two authors
are scored on identical items.

| Author ↓ / intended target → | GPT-6 Astra | Claude Fable 5.1 |
|---|---|---|
| GPT-6 Astra | **0.226** (sd 0.017; 0.198–0.247) | **0.214** (sd 0.010; 0.200–0.231) |
| Claude Fable 5.1 | 0.273 (sd 0.033; 0.217–0.329) | 0.256 (sd 0.013; 0.234–0.277) |

Reference predictors, with the same weighting:

| Reference | Astra | Fable |
|---|---|---|
| constant 0.5 | 0.250 | 0.250 |
| repeat last (0.75 on previous shape) | 0.322 | 0.337 |
| switch last (0.75 on the other shape) | 0.297 | 0.282 |
| learned from the other replicate wave (switch rate after wins and after losses; an outside observer given past examples) | 0.249 | 0.250 |

Generation-level losses (blocks 1–10):

| Cell | Losses | Below 0.25 |
|---|---|---|
| Astra → Astra | 0.247 0.230 0.218 0.233 0.231 0.214 0.198 0.246 0.204 0.242 | 10/10 |
| Astra → Fable | 0.208 0.212 0.200 0.231 0.214 0.213 0.221 0.201 0.217 0.225 | 10/10 |
| Fable → Astra | 0.263 0.262 0.269 0.247 0.260 0.286 0.317 0.217 0.277 0.329 | 2/10 |
| Fable → Fable | 0.263 0.250 0.261 0.234 0.236 0.258 0.257 0.263 0.254 0.277 | 3/10 |

| Contrast (positive favours the same-model author) | Mean | Block sd | Block range | Blocks > 0 | Leave-one-game-out range | Wave 1 / wave 2 | Excl. round 1 |
|---|---|---|---|---|---|---|---|
| Fable own-author advantage L(A→F) − L(F→F) | −0.041 | 0.019 | −0.063 to −0.003 | 0/10 | −0.046 to −0.037 | −0.049 / −0.034 | −0.040 |
| Astra own-author advantage L(F→A) − L(A→A) | +0.046 | 0.043 | −0.029 to +0.118 | 9/10 | +0.042 to +0.051 | +0.042 / +0.050 | +0.047 |
| Balanced self advantage | +0.003 | 0.024 | −0.046 to +0.041 | 6/10 | +0.000 to +0.005 | −0.003 / +0.008 | +0.004 |

Both target-specific contrasts keep their sign:
- whichever single contributing game is dropped (both seats together);
- in either replicate wave;
- without round 1.

The balanced value is close to zero, because the two contrasts mostly cancel.

The archive balances seats and opponents, but each target's histories come from different games. A difference between the
two columns therefore mixes predictability with predictor quality. Only comparisons within a column are matched.

## B. Did naming the target help?

| Author | Intended assignment | Swapped assignment | Swapped − intended (mean; block range; blocks > 0) |
|---|---|---|---|
| Astra | 0.220 | 0.216 | −0.005 (−0.016 to +0.003; 4/10) |
| Fable | 0.264 | 0.266 | +0.002 (−0.016 to +0.024; 5/10) |

Neither author's programs for the two names are usefully different, so the general advantage does not come from targeting.

**Resemblance diagnostic (separate):** this ignores the name in the prompt and asks which actual player each author's 20
programs fit better.

| Author's 20 programs scored on | Astra's choices | Fable's choices |
|---|---|---|
| Astra-authored | 0.213 | 0.223 |
| Fable-authored | 0.274 | 0.256 |

- Each author fits its own model's choices better: author × player self-resemblance +0.014.
- Most of the difference is author quality (0.05 between rows), not resemblance.
- The two columns use different histories, so a single row's comparison mixes fit with difficulty. The interaction does not.

So there are three distinct results:
1. a large **general author advantage** for Astra;
2. **no useful targeting** by either author;
3. a small **passive self-resemblance**.

## C. Response to wins and losses (rounds 2–20, probabilities)

p_switch = 1 − p(STAR) if the player last chose STAR, else p(STAR). The previous winner is relative to the scored seat.

| | After a win | After a loss | Gap (win − loss) |
|---|---|---|---|
| **Astra, observed** | 0.651 (71/109) | 0.412 (49/119) | **+0.240** |
| Astra → Astra programs (mean; range of 10) | 0.505 (0.477–0.548) | 0.501 (0.465–0.533) | +0.004 (−0.036 to +0.049) |
| Fable → Astra programs | 0.548 (0.365–0.729) | 0.691 (0.526–0.823) | −0.143 (−0.429 to +0.006) |
| **Fable, observed** | 0.576 (68/118) | 0.536 (59/110) | **+0.040** |
| Astra → Fable programs | 0.501 (0.476–0.553) | 0.537 (0.501–0.574) | −0.036 (−0.091 to −0.006) |
| Fable → Fable programs | 0.586 (0.457–0.699) | 0.717 (0.571–0.789) | −0.130 (−0.258 to +0.009) |

- No program family reproduces Astra's win-switch tendency.
- Fable's programs apply win-stay/lose-shift. That is the wrong sign for Astra, and too strong and too switch-prone for Fable.

## What the programs used (inspected after the numbers were frozen at `eed899b`)

**Fable-authored programs (20/20) code an explicit win-stay/lose-shift rule.** Most add streak avoidance (19/20) and an
opening STAR lean (14/20). Examples from block 2 (`b02_fable_for_fable.py`):

```python
# Win-stay / lose-shift assumption about opponent
pred += 0.45 * (opp_last if opp_won_last else -opp_last)
...
# Own streak avoidance
if mstreak >= 2:
    desire -= 0.25 * my_last * min(mstreak - 1, 3)
```

The programs push these heuristics to confident probabilities: mean |p − 0.5| = 0.15–0.17. That confidence is what makes
them worse than a coin flip on these players.

**Astra-authored programs** estimate the following from the supplied history and blend them:
- frequencies;
- transition and pattern statistics, in 20/20 programs;
- responses to the opponent's last move.

They temper the result explicitly. For example, `b01_astra_for_astra.py`:

> These are uncertain behavioral hypotheses, not access to the target model's internal probabilities.
> Temper evidence because the hypotheses are approximate.

Their predictions stay near 0.5 (mean |p − 0.5| = 0.05 for Astra, 0.10 for Fable). That keeps their loss below 0.25, but it
cannot capture a +0.24 switch gap. Astra's "for Fable" programs are somewhat bolder and score best of all four cells
(0.214).

**Openings:** at round 1, every program gives Player 1 a STAR lean (0.50–0.66). Player 2 usually gets 0.35–0.50, but some
Fable programs give 0.55–0.60.

The recurring rule is the *author's* style, not the named player's: within each author, the programs for the two names look
alike. Any own-model advantage here would be evidence about predicting behaviour under these prompts. The four cells cannot
show how an author obtained that information, and here the advantage is general, not own-model.

## Run record

- **Answer key:** `track2_game_theory/05_2026-10-10_study1_exp1_disclosure/mp3m-p2-20261010/with_makeups/game_logs.jsonl`,
  read in full (113 records). It holds 18 complete condition-00 games, one per ordered pairing and replicate, including the
  make-up games AQ_00_2_MU1, QA_00_1_MU1, QF_00_1_MU1 and QQ_00_1_MU2.
  - 16 games contribute: 480 decisions (240 Astra, 240 Fable; 120 per seat; 228 after the opening).
  - Qwen's moves appear only as opponent history.
  - Every acceptance count and the four switch counts reproduce the handoff exactly.
- **Prompts:**
  - The two seat templates are the original `GAME_TEMPLATE` (condition 00, uninformed opponent, target's display name). Only
    the history and round number are neutral slots; the history slot documents the original rendering.
  - Substituting real histories reproduces `game.player_prompt()` byte for byte (tested).
  - For each target the message is byte-identical across authors and blocks (sha256 Astra `6e8ff82a…`, Fable `94ae8d4a…`).
- **Calls:** 40 = 10 blocks × 4 cells, shuffled within blocks (seed 20261105), dispatched one at a time on 2026-11-04.
  - `openai/gpt-6-astra` was pinned to `openai` and returned by OpenAI (20); `anthropic/claude-fable-5.1` was pinned to
    `anthropic` and returned by Anthropic (20).
  - Settings: no fallbacks, effort low (reasoning excluded), max_tokens 4000, no temperature, top_p, seed or tools, and no
    cache directives. Usage shows 0 cached prompt tokens.
  - All 40 finished with `stop`, with no transport retries. Response ids are in `responses/calls.jsonl`.
  - **Billed $3.141** (Astra $1.115, Fable $2.027). Hard cap $10; worst-case reservation $8.44.
- **Version limit:** the OpenRouter slugs are not dated snapshots. Pinned providers and prices match the archive, but
  identical weights to the October 2026 players cannot be verified.
- **Programs:** Fable's 20 replies were one Python fence each and Astra's 20 were bare source. All 40 are distinct and were
  frozen and committed (`c4fe5f7`) before validation.
  - **40/40 passed the contract:**
    - round 1 in both seats and 19-round histories;
    - 92 synthetic calls per program;
    - two passes in one process plus a reversed pass in a second process, all identical;
    - a numeric non-bool result, finite and in [0, 1].
  - All 40 ran on the same 480 inputs. Failures: none. Incomplete blocks: none.
- **Isolation:** the same as folder 21 (imported):
  - a base-interpreter `python -I -S` worker with no environment variables except SYSTEMROOT (no credentials), in a fresh
    empty temporary folder;
  - a Windows Job Object (512 MB, one process);
  - an audit hook refusing file opens, sockets, subprocesses, ctypes and non-`math` imports;
  - per-call and per-process time limits.

  No container runtime exists here, so network access was blocked in-process, not by the OS.
- **Deviations:**
  1. The isolation method above.
  2. A schedule-numbering bug (the same `order` value within each block) was fixed before the plan was committed or approved.
     The dispatch order was unaffected.
- No new games, judge calls, ground truth or GPU.

## Reproduce with zero API calls

```bash
PYTHONPATH=src python -m blind_coder_player_choices validate   # contract on synthetic histories
PYTHONPATH=src python -m blind_coder_player_choices score      # 40 hash-checked programs x 480 decisions -> scoring/
pytest tests/test_blind_coder_player_choices.py
```
