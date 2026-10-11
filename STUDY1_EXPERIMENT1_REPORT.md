# Study 1, Experiment 1: opponent-identity disclosure in RPS and matching pennies (two-game pilot)

October 10, 2026. Feasibility pilot under `SPAR_Study1_Experiment1_Pilot_2_Games_Per_Cell_Claude_Handoff_2026-10-10.md`.
Rock-paper-scissors (RPS) and matching pennies (MP) are separate games under one research question; they are not pooled.
No Blind Twin observer analysis has been run on these game logs.

## Design

Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`) and Qwen (`qwen/qwen3.8-27b`) played all 9 ordered
pairings x 4 truthful disclosure conditions (00 neither told, 10 only Player 1, 01 only Player 2, 11 both) x 2 games x
20 rounds, in each game. The only treatment text is one line: either the opponent's true model name or "not disclosed".
In MP, Player 1 is always the Matcher. The unit is a complete 20-round game. The primary contrast per game is
D = mean over models of S_i - O_i: how much more a player gains from learning its opponent's identity when that opponent
is the same model than when it is a different one (payoff units; positive = disclosure helps more against self).

## Completion and cost

| | RPS `rps3m-p2-20261010` | MP `mp3m-p2-20261010` |
|---|---|---|
| Games complete / planned | **71 / 72** | **54 / 72** |
| Cells with 0 / 1 / 2 complete games | 0 / 1 / 35 | 2 / 14 / 20 |
| Player calls (valid / recorded) | 2,865 / 2,866 | 2,558 / 2,576 |
| Invalid answers | 1 (Qwen) | 18 (all Qwen) |
| Cost (hard cap $60 each) | $22.32 | $20.28 |

Account usage rose by $42.61 over both runs, matching the $42.60 logged. **Every interrupted game was caused by Qwen**
ending its answer with markdown bold (`**PAPER**`, `**STAR**`). The frozen parser rejects this, so the game stopped
and was not refilled. Qwen's per-call invalid rate was 0.1% in RPS but 2.4% in MP. Astra and Fable never gave an
invalid answer. MP attrition is concentrated in Qwen pairings: Astra-Qwen 5/8 games lost, Qwen-Astra 5/8, Qwen-Fable
3/8, Qwen-Qwen 3/8, Fable-Qwen 2/8. Both empty MP cells are condition 11 (Astra-Qwen, Qwen-Astra), so this attrition
is a selection risk: surviving Qwen games are the ones where Qwen happened not to bold its answer.

## Primary results

| | D (frozen package analysis) | D (handoff definition) | 95% whole-game bootstrap | Partial-game sensitivity |
|---|---|---|---|---|
| **RPS** | +0.011 | +0.011 | [-0.030, +0.052] | +0.011 [-0.027, +0.052] |
| **MP** | not estimable | **-0.044** | [-0.071, -0.017] | -0.094 [-0.159, -0.031] |

| Model | RPS D_i | MP D_i |
|---|---|---|
| Astra | -0.022 [-0.084, +0.038] | -0.019 [-0.075, +0.037] |
| Fable | +0.097 [+0.047, +0.150] | -0.006 [-0.069, +0.056] |
| Qwen | -0.041 [-0.138, +0.056] | -0.106 [-0.138, -0.075] |

- **RPS:** no overall self-specific disclosure effect. Fable's D is positive. Its same-model disclosure benefit
  (S = +0.044) exceeds its other-model one (O = -0.053), and the interval excludes zero. Astra and Qwen are near zero.
- **MP:** D is slightly negative, driven almost entirely by Qwen (S = -0.013, O = +0.094). Fable's positive RPS
  pattern does not replicate in MP (D = -0.006).
- **Between games (descriptive only):** D_RPS - D_MP = +0.055. The two games disagree in sign for Fable and agree in
  sign for Astra and Qwen. With two games per cell this is not evidence either way.
- **Why the intervals cannot be trusted:** with 2 games per cell the bootstrap can produce only three possible means
  per cell, and a cell with 1 game cannot vary at all. 1 RPS cell and 14 MP cells have a single game, including many of
  the Qwen cells behind MP's D_Qwen. So the MP interval in particular is much too narrow. As the handoff warns, no
  interval here is confirmation, and none is evidence of absence.

**Analysis deviation, reported not repaired:** the frozen contrast code (inherited from the RPS package) computes U1 and
U2 for a pairing only when all four cells, 00/10/01/11, have data. The handoff's U1, U2, S, O and D use only 00, 10 and
01. In MP the only empty cells are 11 cells, so the frozen output reports D as NA although the handoff's D is defined.
`experiment1_derived.py` applies the handoff rule with the package's own bootstrap and seeds; its D_MP = -0.044 matches
the independent `rescore.py` exactly. The frozen outputs are left unchanged. RPS is unaffected (every cell has data).

## Behaviour (key points; full tables in each REPORT.md)

- **Predictability:** in MP, prospective history-only rules predict the models' choices mostly near or below chance (about
  36-58%, chance 50). The models are not trivially exploitable by simple rules in either role.
- **Disclosure has no consistent effect** on switch rates or win-stay/lose-shift by model and role at this sample size.

## Data quality and process notes

- **First launch failed** before any request (0 calls, $0). The live price lookup could not read the plan-time
  snapshot format. This was fixed, and both cohorts were re-frozen with identical schedules.
- **MP crashed after 65/72 games** on an `http.client.IncompleteRead`, which the shared client did not treat as a
  transient network error. The fix (retry with identical payload) is in `spar_dynamic/phase2/client.py`. The run
  resumed without reissuing any logged call. No unlogged charges appear in account usage.
- **The eight-game RPS cohort `rps3m-20261009T1240Z`** was never executed. It is marked superseded, not resized.

## Recommendations

1. **Qwen output formatting is the binding constraint for MP.** Before any scale-up, choose and pre-register one of:
   (a) a parser that accepts one layer of markdown emphasis around the exact token, applied to all models; (b) a
   different Qwen route; or (c) accept attrition and over-allocate Qwen cells. Any of these defines a new cohort,
   not a top-up of this one.
2. **Fix the estimability rule** in both packages to match the handoff (U1 needs 00/10, U2 needs 00/01) before the next
   freeze.
3. **Readiness for Experiment 2:** RPS gives 71 complete, clean 20-round histories, usable for the Blind Twin observer.
   MP gives 54, with Qwen under-represented and possibly selected by the formatting failures. Use MP logs for
   Experiment 2 only with that caveat, or after a clean MP cohort.

## Amendment: make-up games (added 2026-10-10 20:45; details in EXPERIMENT1_MAKEUP_GAMES.md)

On Chris's instruction, every Qwen-interrupted game was replaced with fresh games in the same cell, under the frozen
protocol, until one completed. Rules were fixed before the first make-up call. Original raw files are unchanged; the
amended analysis is in each run's `with_makeups/` folder. This is a post-hoc deviation from the pilot protocol,
triggered by formatting failures, never by outcomes. All 19 targets were filled (RPS 1 attempt, MP 41 attempts).
Make-ups cost $7.38; Experiment 1 total is $49.97. Both games now have 2 complete games in all 36 cells.

| | D (amended, 72 complete games each) | D_Astra | D_Fable | D_Qwen |
|---|---|---|---|---|
| RPS | +0.011 [-0.027, +0.052] | -0.022 | +0.113 | -0.056 |
| MP | -0.060 [-0.100, -0.023] | -0.012 | -0.012 | -0.156 |

**New caveat:** Qwen's invalid-answer rate in MP depends on disclosure: 3.6% of calls when told the opponent's identity
versus 1.8% when not (30/825 vs 11/627). Informed-cell Qwen games are therefore more selected, which can bias D_Qwen and
D_MP. The conclusions above stand: no self-specific disclosure effect overall in RPS; a Fable-specific positive D in RPS
that does not appear in MP; and a negative MP D driven by Qwen and now also subject to condition-dependent selection.
Recommendation 1 (resolve Qwen formatting before any scale-up) is strengthened. MP game logs are now balanced for
Experiment 2, but the Qwen selection caveat applies.

## Files

RPS: `opponent_disclosure_rps_3models/results/rps3m-p2-20261010/` (REPORT.md, calls.jsonl, game_logs.jsonl,
cell_means.csv, primary_contrasts.csv, bootstrap.csv, derived_contrasts.csv, checksums.sha256).
MP: `opponent_disclosure_mp_3models/results/mp3m-p2-20261010/` (REPORT.md, calls.jsonl, game_logs.jsonl, games.csv,
rounds.csv, invalids.csv, cell_means.csv, primary_contrasts.csv, behavioral_metrics.csv, baseline_predictions.csv,
bootstrap_intervals.csv, conditional_choice.csv, derived_contrasts.csv, checksums.sha256).
Derived analysis: `experiment1_derived.py` (handoff-definition D and partial-game sensitivity; reads game logs only).
