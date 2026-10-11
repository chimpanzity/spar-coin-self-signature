# Study 1, Experiment 1: make-up games for Qwen-interrupted games

Written 2026-10-10 before any make-up call was dispatched. Sections 1-4 are fixed; Section 5 is appended by
`experiment1_makeup.py` as attempts complete; Section 6 is written after the make-up runs finish.

## 1. Decision and authority

After the two-game pilot, 19 games had stopped early because Qwen ended its answer with markdown bold (`**PAPER**`,
`**STAR**`). The frozen parser rejects this, so each game was interrupted and not refilled:

- RPS `rps3m-p2-20261010`: 1 game (FQ_00_1).
- MP `mp3m-p2-20261010`: 18 games, all in Qwen pairings. Two cells (Astra-Qwen 11 and Qwen-Astra 11) had no complete
  game, and 14 had one.

On 2026-10-10 Chris instructed: "do make-up games to fill in the gaps where qwen failed. keep trying until qwen
allotment is filled, and keep detailed notes on the process and rationale."

This is an amendment made after the pilot data were seen. The handoff forbids "adaptively top[ping] up interesting cells
after viewing outcomes". This amendment differs in what triggers it. The trigger is a **formatting failure** (an
invalid answer), never a game's payoff or any contrast. **Every** interrupted game is replaced, in every cell,
regardless of the cell's results. The decision is Chris's, and it is recorded here as a deviation from the frozen
pilot protocol.

## 2. Rationale

- **Restore balance:** the design needs 2 complete games per cell. Under the frozen estimability rule, MP's D was not
  estimable, and 14 MP cells rested on a single game, whose bootstrap variance is zero.
- **Interruptions are a format failure, not strategic behaviour:** in every one of the 19 cases the move inside the
  bold markers was a legal move.
- **Replacing interruptions differs from refilling invalid answers:** the frozen rule "an invalid answer is not
  refilled" is kept. No answer is reparsed or replaced, and no interrupted game is continued. A make-up is a **new,
  independent game** from round 1.

## 3. Rules (fixed before the first make-up call)

1. **Targets:** each interrupted game in the two run folders above (19 targets). One make-up target per interrupted
   game, in the same cell (same ordered pairing, same condition, same seats, same informed flags).
2. **Unchanged protocol:** the same frozen package, prompts, models, provider pinning, reasoning settings, parser and
   scorer. The driver checks the package code hash and schedule hash against the run's frozen manifest and refuses to
   run on a mismatch. No prompt or parser change.
3. **Attempts:** a make-up attempt is a fresh 20-round game, id `<original>_MU<k>` (k = 1, 2, ...). Slot ids are
   prefixed `makeup:` and cannot collide with original calls. If attempt k is interrupted by an invalid answer, attempt
   k + 1 starts from round 1. **Attempts continue until the target has one complete game**, as Chris instructed.
4. **Fixed outcome:** the first complete make-up attempt fills the target. Later attempts are never run for a filled
   target, and no complete game is ever discarded. Interrupted attempts are kept and reported.
5. **Budget:** spending counts against each run's existing approved $60 hard cap (RPS spent $22.32, MP $20.28 before
   make-ups), using the same worst-case in-flight reservation. If a cap would be exceeded, the driver stops dispatching,
   and Claude asks Chris before going further. The cap is never raised silently.
6. **Transport:** transient network failures retry the identical payload (unchanged rule). A transport failure is not
   counted as an attempt outcome; the attempt resumes idempotently.
7. **Storage:** original raw files (`calls.jsonl`, `game_logs.jsonl`, reports) are never modified. Make-up calls go to
   `makeup_calls.jsonl`, and make-up games to `makeup_game_logs.jsonl`, in the same run folder.
8. **Analysis:** a combined dataset is written to `<run>/with_makeups/` containing:
   - all original games, with interrupted originals kept as interrupted;
   - all make-up attempts, interrupted ones included;
   - concatenated calls.

   The frozen package `analyze()` is then run on it unchanged. The original pilot-only analysis stays primary for the
   pre-registered cohort. The with-make-ups analysis is labelled "amended (make-up) analysis". Both are reported.

## 4. Known consequences

- **Selection:** a complete Qwen game is now, by construction, one in which Qwen never used bold. If bolding
  correlates with Qwen's strategy, its game state or the disclosure condition, the retained Qwen games are a selected
  subset. The report gives the number of attempts per cell, and attempt counts by condition, so this can be checked.
- **Timing:** make-up games are played after the main schedule, not interleaved with it. Any drift in endpoints over
  time is confounded with make-up status. Endpoints and prices are checked at launch.
- **Uncertainty:** with make-ups, each cell has 2 complete games, but the bootstrap still sees only 2 games per cell.

## 5. Attempt log (appended automatically)

Pre-launch validation (fake transport, copy of the MP run folder, 3% simulated invalid rate, so higher than Qwen's
2.4%): 18/18 targets filled in 76 attempts; a rerun added 0 calls (idempotent); the combined analysis had 72/72 complete
games and D matched the independent rescore exactly; the copied calls.jsonl and game_logs.jsonl were byte-identical to
the originals afterwards. The package code hash and schedule hash matched the frozen manifests.

### RPS rps3m-p2-20261010: launch 2026-10-10 19:54:03, 1 targets, spent before make-ups $22.32 of $60

| time | target | attempt | status | valid rounds | note | spent |
|---|---|---:|---|---:|---|---:|
| 19:58:02 | FQ_00_1 | 1 | complete | 20 |  | $22.61 |

MAKEUP end (RPS rps3m-p2-20261010): 1/1 targets filled; attempts 1; spent $22.61

### MP mp3m-p2-20261010: launch 2026-10-10 19:58:03, 18 targets, spent before make-ups $20.28 of $60

| time | target | attempt | status | valid rounds | note | spent |
|---|---|---:|---|---:|---|---:|
| 19:58:27 | FQ_01_2 | 1 | interrupted | 0 | invalid response at round 1: {'p2': 'final_line_not_exact_choice'} | $20.40 |
| 19:59:50 | QF_10_1 | 1 | interrupted | 5 | invalid response at round 6: {'p1': 'final_line_not_exact_choice'} | $20.94 |
| 20:00:51 | AQ_01_2 | 1 | interrupted | 8 | invalid response at round 9: {'p2': 'final_line_not_exact_choice'} | $21.34 |
| 20:01:22 | QQ_00_1 | 1 | interrupted | 10 | invalid response at round 11: {'p1': 'final_line_not_exact_choice'} | $21.51 |
| 20:02:22 | AQ_11_2 | 1 | interrupted | 12 | invalid response at round 13: {'p2': 'final_line_not_exact_choice'} | $21.96 |
| 20:02:37 | QF_01_2 | 1 | interrupted | 16 | invalid response at round 17: {'p1': 'final_line_not_exact_choice'} | $22.02 |
| 20:03:36 | AQ_10_1 | 1 | complete | 20 |  | $22.35 |
| 20:03:37 | QF_10_1 | 2 | interrupted | 7 | invalid response at round 8: {'p1': 'final_line_not_exact_choice'} | $22.37 |
| 20:04:06 | AQ_11_2 | 2 | interrupted | 5 | invalid response at round 6: {'p2': 'final_line_not_exact_choice'} | $22.58 |
| 20:04:16 | FQ_11_2 | 1 | interrupted | 1 | invalid response at round 2: {'p2': 'final_line_not_exact_choice'} | $22.66 |
| 20:04:39 | AQ_11_1 | 1 | complete | 20 |  | $22.81 |
| 20:05:25 | QQ_11_1 | 1 | interrupted | 5 | invalid response at round 6: {'p2': 'final_line_not_exact_choice'} | $23.20 |
| 20:06:04 | QA_00_1 | 1 | complete | 20 |  | $23.45 |
| 20:06:26 | QA_11_1 | 1 | complete | 20 |  | $23.68 |
| 20:06:33 | QA_01_1 | 1 | complete | 20 |  | $23.74 |
| 20:06:39 | QA_10_2 | 1 | complete | 20 |  | $23.75 |
| 20:06:48 | QA_11_2 | 1 | complete | 20 |  | $23.79 |
| 20:06:52 | QF_01_2 | 2 | interrupted | 12 | invalid response at round 13: {'p1': 'final_line_not_exact_choice'} | $23.81 |
| 20:07:10 | AQ_01_2 | 2 | complete | 20 |  | $23.89 |
| 20:07:36 | FQ_01_2 | 2 | complete | 20 |  | $24.03 |
| 20:09:42 | QQ_00_1 | 2 | complete | 20 |  | $24.61 |
| 20:10:03 | QF_01_2 | 3 | interrupted | 10 | invalid response at round 11: {'p1': 'final_line_not_exact_choice'} | $24.72 |
| 20:10:44 | QF_00_1 | 1 | complete | 20 |  | $24.90 |
| 20:11:02 | QQ_11_1 | 2 | interrupted | 10 | invalid response at round 11: {'p1': 'final_line_not_exact_choice'} | $24.94 |
| 20:11:29 | AQ_00_2 | 1 | complete | 20 |  | $25.07 |
| 20:11:34 | AQ_11_2 | 3 | complete | 20 |  | $25.08 |
| 20:11:35 | QQ_10_2 | 1 | complete | 20 |  | $25.09 |
| 20:12:00 | FQ_11_2 | 2 | interrupted | 19 | invalid response at round 20: {'p2': 'final_line_not_exact_choice'} | $25.13 |
| 20:14:04 | QQ_11_1 | 3 | interrupted | 7 | invalid response at round 8: {'p1': 'final_line_not_exact_choice'} | $25.42 |
| 20:14:57 | QF_10_1 | 3 | interrupted | 19 | invalid response at round 20: {'p1': 'truncated_length'} | $25.54 |
| 20:15:53 | QQ_11_1 | 4 | interrupted | 4 | invalid response at round 5: {'p1': 'final_line_not_exact_choice'} | $25.65 |
| 20:16:25 | FQ_11_2 | 3 | interrupted | 10 | invalid response at round 11: {'p2': 'final_line_not_exact_choice'} | $25.74 |
| 20:16:46 | QF_01_2 | 4 | complete | 20 |  | $25.79 |
| 20:16:57 | QQ_11_1 | 5 | interrupted | 2 | invalid response at round 3: {'p2': 'final_line_not_exact_choice'} | $25.80 |
| 20:17:29 | QF_10_1 | 4 | interrupted | 4 | invalid response at round 5: {'p1': 'final_line_not_exact_choice'} | $25.84 |
| 20:20:15 | FQ_11_2 | 4 | interrupted | 11 | invalid response at round 12: {'p2': 'final_line_not_exact_choice'} | $26.12 |
| 20:22:32 | FQ_11_2 | 5 | interrupted | 7 | invalid response at round 8: {'p2': 'final_line_not_exact_choice'} | $26.37 |
| 20:27:06 | QQ_11_1 | 6 | complete | 20 |  | $26.84 |
| 20:29:12 | FQ_11_2 | 6 | complete | 20 |  | $26.94 |
| 20:29:29 | QF_10_1 | 5 | interrupted | 18 | invalid response at round 19: {'p1': 'final_line_not_exact_choice'} | $26.96 |
| 20:42:46 | QF_10_1 | 6 | complete | 20 |  | $27.36 |

MAKEUP end (MP mp3m-p2-20261010): 18/18 targets filled; attempts 41; spent $27.36

## 6. Outcome (written after both make-up runs finished, 2026-10-10 20:45)

### Completion and cost

| | RPS | MP |
|---|---|---|
| Targets filled | 1 / 1 | 18 / 18 |
| Make-up attempts (complete + interrupted) | 1 (1 + 0) | 41 (18 + 23) |
| Make-up calls / cost | 40 / $0.29 | 1,170 / $7.09 |
| Run total incl. make-ups (cap $60) | $22.61 | $27.36 |
| Cells with 2 complete games | 36 / 36 | 36 / 36 |

MP attempts per target: 1 attempt for 11 targets, 2 for 3 (AQ_01_2, FQ_01_2, QQ_00_1), 3 for 1 (AQ_11_2), 4 for 1
(QF_01_2) and 6 for 3 (FQ_11_2, QF_10_1, QQ_11_1). The cap was never approached. The two non-bold invalid MP answers
ended with explanation text on the last line.

### Selection finding: Qwen's invalid rate depends on the disclosure condition

| Qwen MP calls | not told opponent identity | told opponent identity |
|---|---|---|
| Original pilot | 7 / 384 (1.8%) | 11 / 379 (2.9%) |
| Make-up attempts | 4 / 243 (1.6%) | 19 / 446 (4.3%) |
| **All** | **11 / 627 (1.8%)** | **30 / 825 (3.6%)** |

- **Size of the difference:** in MP, Qwen gives an invalid (mostly bold) answer about twice as often when told its
  opponent's identity. A naive two-proportion test gives z of about 2.2, but calls are clustered within games, so treat
  this as suggestive.
- **Which opponents:** the rate is highest when Qwen is told it faces a *different* model (23/583, 3.9%), versus told it
  faces Qwen (7/242, 2.9%).
- **Interrupted attempts by MP condition:** 00: 1/5; 10: 5/9; 01: 5/9; 11: 12/18.
- **RPS:** shows no such pattern (told 0/480, not told 1/493).

Consequence: disclosure changes not only Qwen's play but also whether Qwen completes a game. Complete Qwen games in
informed cells are therefore more strongly selected, being those where Qwen avoided bold for 20 rounds. That is exactly
the selection risk anticipated in Section 4. It now differs by condition, so it can bias U1 and U2 and hence D_Qwen and
D_MP. Qwen's bolding is itself an outcome of disclosure, and is worth reporting in its own right.

### Results with make-ups (amended analysis; frozen package analysis on `with_makeups/`; rescore matches exactly)

| | D | D_Astra | D_Fable | D_Qwen |
|---|---|---|---|---|
| RPS, pilot only (71 games) | +0.011 [-0.030, +0.052] | -0.022 | +0.097 | -0.041 |
| **RPS, with make-up (72)** | **+0.011 [-0.027, +0.052]** | -0.022 [-0.084, +0.038] | +0.113 [+0.056, +0.169] | -0.056 [-0.150, +0.041] |
| MP, pilot only (54; handoff-rule D) | -0.044 [-0.071, -0.017] | -0.019 | -0.006 | -0.106 |
| **MP, with make-ups (72)** | **-0.060 [-0.100, -0.023]** | -0.012 [-0.075, +0.050] | -0.012 [-0.081, +0.056] | -0.156 [-0.238, -0.081] |

- **Frozen analysis now works for MP:** with every cell filled, the frozen package analysis computes D_MP directly, and
  the estimability-rule deviation no longer matters for these data.
- **The make-ups did not change the picture:** RPS D is unchanged, and Fable's positive RPS D is slightly larger. MP D is
  slightly more negative, still driven by Qwen: its same-model disclosure benefit S = -0.050 against other-model
  O = +0.106.
- **How much to trust the intervals:** each cell now has 2 games, so no cell has zero bootstrap variance. The
  intervals are still from a two-game-per-cell pilot, and D_Qwen in MP is subject to the condition-dependent selection
  above. Neither result is confirmatory.

### Files

- Make-up raw data: `makeup_calls.jsonl` and `makeup_game_logs.jsonl` in each run folder.
- Amended analysis: `with_makeups/`, which holds REPORT.md, the CSVs and checksums.
- Driver: `experiment1_makeup.py`.
- Original pilot files are unchanged.
