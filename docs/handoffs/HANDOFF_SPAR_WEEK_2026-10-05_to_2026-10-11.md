# SPAR week record: 2026-10-05 to 2026-10-11

Single record of the week for Chris Martin's SPAR project (mentor Christopher Ackerman), covering the close of the
coin-flip work (Part 1, Phase 2) and the start and first results of the strategic-games work (Part 2). Written
2026-10-11 by Claude from the repository `chimpanzity/spar-coin-self-signature` (local copy in
`Py_Projects/spar-coin-self-signature`), the run folders, and this week's review discussions. Every number below is in
a file named in section 9; nothing here is new analysis. The previous record is
`docs/handoffs/HANDOFF_SPAR_WEEK_2026-09-29_to_2026-10-03.md`.

Models, all via OpenRouter with pinned providers: Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`),
and a third model: Qwen3-8B (Phase 2 run 1), MiMo-V2.6-Pro (Phase 2 run 2), Qwen3.8-27B (all strategic-game runs).
Players and judges ran at reasoning effort low, reasoning excluded from the response, 4,000 output tokens, no
temperature control (Astra and Fable endpoints do not accept one).

## 1. Timeline

| date | run | what | calls | cost | headline |
|---|---|---|---:|---:|---|
| 10-07/08 | `p2-20261007` | Phase 2 coin-flip pilot v7.1, third model Qwen3-8B | 2,514 | $8.39 | H4 = -0.0026, bounded; judges answered 0.5 |
| 10-08 | `p2-mimo-20261008` | Same, third model MiMo | 2,802 | $8.94 | H4 = -0.0004; Astra and MiMo at 0.5 on 100% of completions |
| 10-08 | review | Independent rebuild of both Phase 2 runs from raw logs | 0 | $0 | Arithmetic reproduces; the contrasts are at floor because the judges did not forecast |
| 10-09 | `bt-20261009T0455Z` | Blind Twin v1, MP, Astra/Fable, 12 games planned | 842 | $4.62 | 9 of 12 games cut short by the player parser; S = -2.2 [-8.5, +3.5] |
| 10-09 | `bt2-20261009T0957Z` | Blind Twin v2 (revised prompts), MP, 12 games | 1,920 | $15.17 | S = +4.2 [+0.4, +8.5], S_false = +4.4 [+1.7, +7.1] |
| 10-09 | `rps-20261009T1024Z` | Blind Twin RPS, Astra-Fable | 1,920 | $15.64 | S = -2.7 [-4.6, -0.8], S_false = +0.6 |
| 10-09 | `rps-qf-20261009T1045Z` | Blind Twin RPS, Qwen-Fable | 1,920 | $11.82 | S = +5.7 [+1.2, +10.9], S_false = +6.3 [+3.2, +9.8] |
| 10-09 | `rps-qa-20261009T1124Z` | Blind Twin RPS, Qwen-Astra | 1,920 | $7.69 | S = +4.4 [-2.3, +11.7], S_false = +8.1 [+3.5, +13.1] |
| 10-09 | `od-20261009T1200Z` | Opponent disclosure pilot, Astra vs Astra MP, 2x2, 32 games | 1,280 | $7.05 | Informing the Matcher raised its win rate +5.0 pp [+0.6, +9.7] |
| 10-09 | `rps3m-20261009T1240Z` | Eight-game three-model RPS cohort, frozen | 0 | $0 | Never executed; superseded by the two-game design |
| 10-10 | `rps3m-p2-20261010` | Study 1 Exp. 1, RPS, 3 models x 9 pairings x 4 conditions x 2 games | 2,906 | $22.61 | D = +0.011 [-0.027, +0.052] |
| 10-10 | `mp3m-p2-20261010` | Study 1 Exp. 1, MP, same design | 3,746 | $27.36 | D = -0.060 [-0.100, -0.023], driven by Qwen |
| 10-10 | (make-ups) | 19 Qwen-interrupted games replaced under the frozen protocol | in above | $7.38 | 42 attempts; Qwen's invalid rate doubles when told its opponent |
| 10-10/11 | `btx1-20261010` | Exp. 2, Blind Twin judges on the 36 condition-00 games | 6,480 | $33.06 | S_RPS = +1.8 [-0.7, +4.4], S_MP = +1.5 [-1.0, +4.2]; S_false positive in both |
| 10-11 | `btss-20261011` | Self-self games, 00 vs 11, judge told what players knew | 4,320 | $23.40 | Delta self-specific RPS -4.8 [-9.6, 0.0], MP 0.0 [-7.3, +7.5] |
| 10-11 | `btss-retest-20261011` | Byte-identical re-judging of 6 games | 1,080 | $5.77 | 80% of predictions reproduce; a 40-item cell moves ~5 pp |
| 10-11 | `post_hoc/` | Offline analyses (no calls) | 0 | $0 | See sections 3.5 to 3.8 |

Week's spend: about $191 (Phase 2 $17.34; Blind Twin pilots $54.94; disclosure pilot $7.05; Exp. 1 $49.97; Exp. 2
$33.06; self-self $23.40; retest $5.77). Account balance about $210, to be reconciled against OpenRouter usage: calls
that timed out or were in flight at the 10-10 stop may have billed without a record (at most a few dollars).

## 2. Part 1 close-out: Phase 2 coin flips (10-07 to 10-08)

Design (v7.1): three models generate 20-flip strings under "plain" and "fair" prompts; judges forecast continuations
(completion, Brier-scored, key contrast H4 = own-source gain minus other-source gain from source disclosure), judge
anonymous SAME/DIFFERENT pairs (R), and attribute named sources. External observers (prefix lookup, pair classifier,
LASSO) run on the same items. Full outputs under `data/spar_dynamic/phase2/`; summaries in
`docs/handoffs/PHASE2_PILOT_RESULTS_2026-10-08.md` and `PHASE2_MIMO_RUN_RESULTS_2026-10-08.md`.

What happened:

- Run 1 (Qwen3-8B): Qwen produced a usable "fair" sequence in 7 of 84 calls, so the two-prompt panels were not
  estimable. H4 = -0.0026 [-0.0040, -0.0013], inside the +/-0.02 margin. Plain-prompt R = +0.076 [+0.011, +0.130],
  but driven by Qwen scoring below chance as the uninvolved judge.
- Run 2 (MiMo): all panels estimable. H4 = -0.0004 [-0.0010, +0.0002]; R = -0.019 [-0.074, +0.034] (unstable);
  named R = -0.059. Fable chose itself on 35 of 36 named items regardless of the true source.
- Independent review (10-08, project doc `claude/SPAR_Phase2_Run_Review_2026-10-08.md`): every headline number
  rebuilds from `calls.jsonl`. The runs did not measure self-recognition because the judges answered 0.5: Astra at
  every completion position for all Astra and Fable sequences, MiMo on 100% of everything, Fable within 0.05 of 0.5
  on 380 of 382 forecasts. The sequences were predictable (a development-set lookup table scores Brier 0.06 to 0.19
  against the judges' 0.25). Astra departs from 0.5 only when it reasons (60+ reasoning tokens), and Fable writes its
  working into the answer, which the frozen parser rejects. Astra and Fable share whole 20-flip strings.
- Recommended there, not yet run: an elicitation check on development strings (reasoning low vs high, probabilities
  vs best guess), then a v8 with a source-blind gate and the uncued crossover as primary.

Status: parked. The project moved to strategic games on 10-09 because the games force a committed choice each round
(no 0.5 answer is available to a player), the choice histories are a behavioural trace rather than a text artefact,
and the opponent manipulation gives a live arm, which Ackerman had said interests him more than replay.

## 3. Part 2: strategic games (10-09 to 10-11)

### 3.1 Oct 9 pilots

Blind Twin v1/v2 (MP) and three RPS runs: two models play 12 games (3 per matchup); both act as judges on every round
under TRUE, FALSE (swapped) and ANONYMOUS identity labels. S = self-judge's (TRUE - ANON) on its own model minus the
other judge's, averaged. v1's player parser cut 9 of 12 games short; v2 fixed the prompts and all 12 completed.
Results above. Across the five runs S is positive in three and S_false in all five, Fable's self cells being the
consistent positive contributor. The opponent-disclosure pilot (Astra vs Astra MP, 2x2 unilateral disclosure, 8 games
per cell) found +5.0 pp [+0.6, +9.7] Matcher win rate from telling the Matcher; no response mentioned the self.
These pilots set the per-call cost figures used in every later budget.

### 3.2 Study 1, Experiment 1: opponent-identity disclosure (10-10)

Design: Astra, Fable and Qwen in all 9 ordered pairings x 4 truthful disclosure conditions (00 neither told, 10 P1
told, 01 P2 told, 11 both) x 2 games x 20 rounds, separately in RPS and MP (Player 1 = Matcher). Treatment is one
line: the opponent's true model name, or "not disclosed"; players are told their own identity. Primary contrast
D = mean over models of S_i - O_i, where S_i is model i's payoff gain from being told when the opponent is itself and
O_i when it is another model. Approved 10-10 with $60 hard caps per game (`docs/study1/`).

Results (amended analysis, 72 complete games each, `with_makeups/`):

| | D | D_Astra | D_Fable | D_Qwen |
|---|---|---|---|---|
| RPS | +0.011 [-0.027, +0.052] | -0.022 | +0.113 [+0.056, +0.169] | -0.056 |
| MP | -0.060 [-0.100, -0.023] | -0.012 | -0.012 | -0.156 [-0.238, -0.081] |

Calibration (Monte Carlo, random play, same design): the null SD of D is 0.032 (RPS) and 0.040 (MP) against a
bootstrap-implied SD of 0.020 in both; the null 95% bound on a single D_i is 0.128 (RPS) and 0.156 (MP). So MP's D is
1.5 null SDs, Fable's RPS D_i is 1.7 and the most extreme of six, Qwen's MP D_i sits at the single-contrast bound and
carries the selection caveat below. Two structural points for any redesign: for the self-pairing, S_i reduces to
(V1(10) - V1(01))/2, so the 00 cell cancels in S but not in O, and Fable's positive RPS D is mostly its four
negative other-model contrasts (told it faced Astra or Qwen, Fable played worse); and every 00 cell feeds two
models' O with opposite signs, so one Qwen-vs-Fable 00 cell (Fable won ~65% in both games, both game types) pushes
D_Fable up and D_Qwen down at once.

Process: first launch failed at the price lookup (0 calls); MP crashed at 65/72 games on an `IncompleteRead` that the
client did not treat as transient (fixed, resumed without reissuing calls). Qwen ended answers with markdown bold
(`**PAPER**`), which the frozen parser rejects: 1 RPS and 18 MP games interrupted. On Chris's instruction all 19 were
replaced by fresh games in the same cell under the frozen protocol (rules fixed before the first make-up call,
format-triggered, every interrupted game replaced; 42 attempts, $7.38). Qwen's MP invalid rate is 3.6% when told its
opponent's identity against 1.8% when not (30/825 vs 11/627), highest when told it faces a different model, so
complete informed Qwen games are a selected subset. Condition-00 cells were least affected.

### 3.3 Experiment 2: Blind Twin judges on the Experiment 1 logs (10-10/11)

Design: the 36 condition-00 games (18 RPS, 18 MP; 2 per ordered pairing). Astra, Fable and Qwen each predict both
players' round-t moves from the public history under TRUE, ANONYMOUS and FALSE (fixed rotation
Astra->Fable->Qwen->Astra) labels; one fresh call per item; 6,480 calls, 6,452 valid (28 Fable answers that wrote
reasoning before the JSON, 16 of them in one game). Scored on the paired set, equal weight over seat x opponent
strata. Primary S per game type; whole-game bootstrap. Scope "only games where neither player was told", cap $70.
Recomputed independently from `predictions.csv` on 10-11: matches to the decimal.

| index | RPS | MP |
|---|---|---|
| S (TRUE vs ANON, self-specific), primary | +1.8 [-0.7, +4.4] | +1.5 [-1.0, +4.2] |
| S_false (TRUE vs FALSE) | +3.9 [+0.6, +7.4] | +3.5 [+0.8, +6.3] |
| S[astra] / S[fable] / S[qwen] | +3.5 / +4.8 / -2.8 | +3.1 / +3.8 / -2.3 |
| Fable judging Fable, TRUE / ANON / FALSE | 53.4 / 45.0 / 38.8 (chance 33.3) | 65.0 / 62.1 / 56.2 (chance 50) |

Readings: Fable is the signal. Its label-swap control behaves as a self-model should (the self-label on an Astra
player gives nothing, 41.6 vs 40.8; the wrong label on a Fable player costs 14.5 pp in RPS), and under ANONYMOUS it
predicts Fable players 4.4 (RPS) and 6.5 (MP) pp better than the other judges do. Astra is label-sensitive but not
self-specific: FALSE (Astra players labelled Fable) beats TRUE in both games, and in RPS Astra gains more from being
told a player is Fable (+6.3) than from being told it is itself (+3.8). Qwen changes 40% of its predictions between
labels with no accuracy gain, has negative S, and in RPS is predicted at 46.7% by "counter the opponent's last move"
against 37.5% by itself.

Operational: throughput collapsed after 2,532 calls; cause was macOS idle sleep on battery. The run was stopped,
concurrency raised 16->32 and the request timeout cut 240->120 s (no scientific change; up to 16 in-flight calls lost),
resumed under `caffeinate`. 44 Qwen calls hit the 120 s timeout afterwards and were resampled (3% of its remaining
calls), a mild selection on latency.

### 3.4 Where the Fable effect lives (post hoc, `post_hoc/experiment2_by_opponent/`)

Self-judge advantage over the other judges (TRUE label, 80 predictions per cell), Fable players by opponent:
vs Astra +14.6 (RPS) / +16.3 (MP); vs Qwen +9.8 / +13.8; vs Fable +3.1 / +0.7. On the self-self 00 games
Fable-on-Fable is 42.5 (btx1) and 36.2 (btss), not 53.4. The effect is in Fable's games against other models, where
its play is a crisp exploitation policy; Fable-Fable games are the condition every judge predicts worst.

Round 1 (`ROBUSTNESS_round1.md`): openings are near-fixed (RPS PAPER: Astra 46 of 48; 44 of 72 round-1 ties. MP:
Matcher STAR and Mismatcher TRIANGLE in 47 of 48 Astra/Fable games; the Mismatcher wins round 1 in 60 of 72). Dropping
round 1 moves RPS S from +1.8 to +1.0 and S_false from +3.9 to +2.9; MP is unchanged. The RPS self-advantage is an
opening-rounds effect (self 58.3 vs others 37.5 at round 1; 42.6 vs 40.8 by rounds 6-20); the MP one grows late
(58.0 vs 53.0 in rounds 6-20). Round 1 is also the clearest cued-self-knowledge case in the data: judges' default
prior is the folk ROCK, their own opening is PAPER; under ANONYMOUS the Astra judge predicts ROCK 100% of the time and
scores 0% on its own kind; Fable predicts its own opening 100% correct under TRUE, 50% ANONYMOUS, 0% FALSE. Content
of the label effect: Fable plays the "down" move (the one its previous move beats) 48% of the time; the Fable judge
predicts it for Fable players 47% under TRUE, 43% ANONYMOUS, 41% FALSE.

### 3.5 Classifier floor and observation equivalence (post hoc, offline)

A backoff 2-gram predictor (contexts up to the last two own/opponent moves and the last result) trained on ~47 other
games of the target, leave-one-game-out, on the same condition-00 games, stratified as Experiment 2:

| target | RPS: same-model / other-models-only n-gram / best LLM judge | MP: same |
|---|---|---|
| Astra | 55.8 / 50.4 / 43.8 | 68.3 / 60.4 / 58.3 |
| Fable | 55.8 / 55.0 / 53.4 (Fable) | 70.8 / 58.8 / 65.0 (Fable) |
| Qwen | 49.2 / 49.2 / 46.3 | 53.8 / 62.5 / 57.5 |

The same-model predictor beats every judge on every target; the predictor trained only on the other models' games
beats every judge in RPS and all but Fable-on-Fable in MP. In RPS the exploitable structure is largely shared across
models; model-specific structure is clearest for Astra and Fable in MP. Learning curve
(`post_hoc/experiment2_observation_equivalence/`): Fable's labelled self-prediction equals the n-gram trained on about
32 (RPS) and 24 (MP) of Fable's own games, and more than 47 games of other models' play; under ANONYMOUS about 2-3
(RPS) and 16 (MP) games; Astra's self-prediction equals 16 (RPS) and 5 (MP) games; Qwen's a handful. The n-gram is a
weak learner, so these k are upper bounds, and the curves are still rising at 47 games.

### 3.6 Self-self pilot: 00 vs 11 (10-11, `blind_twin_selfself/`)

Design: the 24 complete self-self games (Astra-Astra, Fable-Fable, Qwen-Qwen; conditions 00 and 11; RPS and MP; 2 per
cell), 3 judges x 3 labels, with one added line stating what the players were told ("Neither player was told its
opponent's model identity" / "Before the game, each player was told the true model identity of its opponent"). The
00 games were re-judged under the new prompt. Primary: Delta self-specific = (T_11 - T_00 for the self-judge) minus the
same for other judges. Approved "run it", cap $40; $23.40.

Result: RPS -4.8 [-9.6, 0.0] (Delta_other +3.2 [+0.8, +5.5], Delta_self -1.6), MP 0.0 [-7.3, +7.5], pooled -2.4.
No support for the hypothesis that an informed twin is easier for a same-model observer to read; in RPS truthful
labels became more useful to the other judges. Per-model intervals in the report (as narrow as +/-2.5 pp) are
artefacts of 2 games per cell; see the retest.

### 3.7 Judge test-retest (10-11)

1,080 prompts byte-identical to btss, re-sampled ("yep check it", cap $10; $5.77). Identical predictions 80.1%
(Astra 84.9, Fable 88.1, Qwen 67.4). A 40-prediction cell's accuracy moves 4.7 pp on average between runs (max 15);
T = TRUE - ANON moves 6.9 pp. The run with the player-information line differs from the run without it by 5.2 and
7.2 pp, so the line changed nothing measurable. This is the measurement floor for every per-cell number this week.

### 3.8 Strategy measures (post hoc, `post_hoc/experiment1_strategy_measures/`)

Following the "offensive / defensive self-modelling" proposal: does being told the opponent is a copy make a player
(a) harder for a history-only predictor to predict, or (b) more likely to counter what its own model's predictor says
the opponent will do? Four groups (told x opponent type), contrasts matched on opponent type, self-specific effect =
interaction. All interactions are within +/-8 pp of zero on accuracy and within +/-0.15 nats on log loss, in both
games, with model-specific and identity-blind predictors. What the data show instead is a general disclosure effect
in RPS only: told any opponent's name, players counter that model's tendencies about 5.5 pp more
[+1.4, +9.9], are about 3 pp less predictable (log loss +0.06 to +0.09 nats), and gain 0.04 payoff. Contrasting
told-self against all uninformed games (not matched on opponent) yields a spurious +14.6 pp "self-specific" effect
for Fable; it vanishes against uninformed self-pairings (45.6 -> 46.9). The judge-based "expectation alignment"
figures (75.4% MP, 53.8% RPS for Astra) reproduce but are not self-specific (Astra's forecasts align with Fable
players more than with Astra players in RPS); they measure shared heuristics.

Descriptive facts from the logs worth keeping: Astra plays nearly the same game whatever it is told (6 of 8
Astra-Astra MP games share the first five rounds); Fable repeats a move 22% of the time and plays the down move 49%,
yet has the highest RPS payoff (0.527) and holds its edge in both halves; RPS switch rates are 78% (Fable), 74%
(Astra), 66% (Qwen) against 67% for random play; MP payoffs are within 0.49 to 0.51 for all models.

## 4. What the week established

1. The harnesses work: frozen protocols, approval gates, hashed schedules, resumable runs, worst-case budget
   reservation, independent recomputation of every headline number. About 34,000 paid calls, no unexplained charges.
2. In strategic play, no evidence of privileged self-access. A 2-gram model with logged games beats every LLM judge,
   including each model on itself; a 2-gram model with no data on the target beats them in RPS.
3. Self-knowledge, where present, is cued and belongs to one model. Fable's labelled self-prediction advantage
   appears in both games of Experiment 2 and in the four Oct 9 pilots that include Fable (F[fable,fable] = +2.8,
   +3.3, +4.2, +7.6); it passes the label-swap control; it
   is worth roughly 25-30 games of observation; it lives in opening conventions and in Fable's play against other
   models; the uncued (anonymous) version is 2-3 pp and inside measurement noise. Astra's label effects are not
   self-specific; Qwen's are absent.
4. Telling a model it faces a copy of itself does not detectably change how it plays. Payoff D is null in RPS and
   Qwen-driven and selection-confounded in MP; strategy measures show no self-specific change; there is a small
   general effect of naming any opponent in RPS.
5. The instruments are noisier than the reports' intervals. Single sampled hard predictions reproduce 80% of the
   time; 2 games per cell make the whole-game bootstrap understate uncertainty by about half; per-cell effects
   below 7 pp are unreadable.
6. Phase 2 coin flips are at floor for a different reason: the judges did not forecast at all at low reasoning
   effort with a bare numeric answer.

On Ackerman's criterion (intrinsic, non-cued, accessible self-knowledge): the strategic-play evidence so far is
negative on non-cued, weakly positive on cued functional self-modelling for one model.

## 5. Methodological lessons

- Elicit probabilities (or several samples per item) and score with log loss or Brier; a single argmax wastes most
  of the information and adds 20% flip noise. Blind Twin v2.0 already used P(SWITCH).
- Two games per cell is a pipeline pilot, not a test. Bootstrap over games cannot see within-item sampling noise.
  Calibrate intervals against a null simulation or a retest.
- Shared baseline cells create correlated errors across contrasts; over-allocate control cells.
- Match contrasts on opponent type; pooled baselines manufacture self-specific effects.
- Near-deterministic openings mean n games are fewer than n trajectories. Seed each game with a short random
  pre-history, or report round 1 separately.
- Fix the Qwen parser (accept one layer of markdown emphasis around the exact token, all models) before any run
  that includes Qwen; its failure rate is condition-dependent and selects the surviving games.
- State the players' information condition in judge prompts whenever it varies.
- Keep the machine awake (`caffeinate -i -m -w <pid>`) for long runs; treat `IncompleteRead` as transient.
- In Phase 2, gate on whether judges forecast real items at all before freezing; the fixtures test arithmetic only.

## 6. Decisions taken this week

- 10-08: Phase 2 reviewed; elicitation check recommended; coin-flip track parked.
- 10-09: strategic-games track opened (Blind Twin v1/v2, three RPS runs, disclosure pilot, all exploratory); the
  eight-game three-model RPS cohort frozen then superseded, not resized.
- 10-10: two-games-per-cell Exp. 1 in RPS and MP approved with $60 caps and a $25 contingency reserve; make-up games
  for Qwen-interrupted games ordered ("keep trying until qwen allotment is filled, and keep detailed notes");
  Exp. 2 approved on condition-00 games only, cap $70.
- 10-11: self-self 00-vs-11 pilot approved as a pipeline pilot with the information line and re-judged 00 games, cap
  $40; test-retest approved, cap $10; post-hoc analyses run offline. Current stance from the week's discussion: no
  further gameplay collection until the instrument is redesigned.

## 7. Open questions and the proposed next design (not yet decided)

Confirmatory Blind Twin (Experiment 2 v2):

- Probability elicitation over moves, scored by log loss and Brier; hard-prediction accuracy secondary.
- Pre-registered indices: S, S_false, the anonymous self-advantage, and the self-advantage expressed in games of
  observation (outsider judges given k of the target's past games in context; the k at which they match the
  self-judge is the headline). A fitted history classifier as the dispositional floor, with its learning curve.
- Games against fixed scripted opponents (and cross-model games) rather than self-self games, since the Fable effect
  is in exploitation of a predictable opponent; a short random pre-history per game to break shared openings.
- 6 or more games per cell; 4-5 models including an open-weight one and a second model from one judge's family
  (checkpoint-specific or family-level asymmetry); reasoning low vs high for judges; FALSE label kept.
- Qwen parser fixed first. Budget on the order of $150-300.
- The live arm: the player itself, told it faces a copy, scored on within-game strategy measures with the matched
  2x2 design; and a self-description arm (does another model armed with the target's own stated strategy predict as
  well as the self-judge?), which separates simulation from stored self-knowledge and answers the live-vs-replay point.
- Chimp-opponent logs as the extension nobody else can run.

Unresolved: whether to resume the coin-flip track with the elicitation check; whether the Fable effect is a fact
about Fable's training rather than about LLMs; how much of the RPS "named opponent" effect survives probability
elicitation.

## 8. For Ackerman (draft framing)

> We moved from coin-string self-recognition to prediction of strategic play. Three findings. First, play in these
> games is largely governed by shared conventions and simple history rules: a 2-gram predictor trained on other
> models' games predicts a model's moves better than any LLM judge, including the model itself. Second,
> self-knowledge, where it appears, is cued: told that the player is itself, Fable predicts its own play better than
> other judges do, and better than when the label is withheld; with the label withheld, the self-advantage is within
> measurement noise. The effect is concentrated in opening conventions and in Fable's play against other models, and
> is absent in Fable-versus-Fable games. It is equivalent to roughly 25-30 logged games of observation. Third, telling
> a model it faces a copy of itself does not detectably change how it plays, beyond a small general effect of being
> told any opponent's identity. On your criterion of intrinsic, non-cued self-knowledge, the strategic-play evidence
> so far is negative; on cued, functional self-modelling, it is weakly positive for one model. The next run changes
> the instrument: probability elicitation, seeded game starts, scripted opponents, and outsiders given k games of the
> target's history.

## 9. File index

Repository `spar-coin-self-signature` (entry points `README.md`, `REVIEW_GUIDE.md`, both updated 10-11):

- Phase 2: `data/spar_dynamic/phase2/p2-20261007/`, `p2-mimo-20261008/`;
  `docs/handoffs/PHASE2_PILOT_RESULTS_2026-10-08.md`, `PHASE2_MIMO_RUN_RESULTS_2026-10-08.md`.
- Oct 9 pilots: `blind_twin/results/bt-20261009T0455Z/`, `bt2-20261009T0957Z/`; `blind_twin_rps/results/rps-*/`;
  `opponent_disclosure/results/od-20261009T1200Z/`; each with `protocol.md` and `REPORT.md`.
- Exp. 1: `docs/study1/STUDY1_EXPERIMENT1_REPORT.md`, `EXPERIMENT1_MAKEUP_GAMES.md`, `EXPERIMENT1_BUDGET_AND_APPROVAL.md`,
  `EXPERIMENT1_STATUS.md`; runs `opponent_disclosure_rps_3models/results/rps3m-p2-20261010/` and
  `opponent_disclosure_mp_3models/results/mp3m-p2-20261010/` (`with_makeups/` = amended analysis);
  `experiment1_derived.py`, `experiment1_makeup.py`.
- Exp. 2: `blind_twin_exp1/results/btx1-20261010/` (REPORT.md, predictions.csv, indices.csv, protocol.md).
- Self-self and retest: `blind_twin_selfself/results/btss-20261011/`, `btss-retest-20261011/`; `blind_twin_retest.py`.
- Post hoc: `post_hoc/experiment1_strategy_measures/` (REPORT.md with addendum, group_means.csv, contrasts.csv,
  classifier_floor_condition00.csv, expectation_alignment_condition00.csv), `post_hoc/experiment2_by_opponent/`
  (REPORT.md, ROBUSTNESS_round1.md, self_advantage_by_opponent.csv), `post_hoc/experiment2_observation_equivalence/`
  (REPORT.md, learning_curve.csv); scripts `experiment1_post_hoc_strategy.py`, `experiment2_observation_equivalence.py`.

Project docs (claude.ai Project "SPAR _ Experiments"): `claude/SPAR_Phase2_Run_Review_2026-10-08.md`,
`claude/SPAR_Phase2_Handoff_v6_2026-10-07.md`, `SPAR_Phase2_Claude_Code_Handoff_2026-10-07.md`, and this record.
