# Matching-pennies opponent identity disclosure, three-model factorial pilot (MPDisclosure3M_v1_pilot2)

Implements Section B of `SPAR_Study1_Experiment1_Pilot_2_Games_Per_Cell_Claude_Handoff_2026-10-10.md`. A separately
versioned cohort built from the audited RPS three-model infrastructure (`opponent_disclosure_rps_3models`); it does not
reuse, edit or pool with the RPS cohort or the Astra-only MP pilot `od-20261009T1200Z`.

- **Models:** identical to the RPS cohort: `openai/gpt-6-astra` (OpenAI), `anthropic/claude-fable-5.1` (Anthropic),
  `qwen/qwen3.8-27b` (Alibaba); prompt names "GPT-6 Astra", "Claude Fable 5.1", "Qwen3.8 27B". Fallbacks off;
  temperature/top_p/seed omitted; reasoning effort=low, exclude=true; max_tokens 4000; one user message per call.
- **Design:** 9 ordered (Player 1, Player 2) pairings x 4 truthful disclosure assignments (00, 10, 01, 11) x 2 games x
  20 rounds = 72 games, 1,440 rounds, 2,880 planned player calls. Player 1 is always the MATCHER, Player 2 always the
  MISMATCHER. No false labels.
- **Prompt:** the handoff's exact template; `You are {SEAT}, the {ROLE}.` and `Your model identity is {OWN_MODEL_NAME}.`
  in every prompt; the opponent-identity line is the only disclosure-dependent text. History: `None. This is the first
  round.` or `Round | Matcher (Player 1) | Mismatcher (Player 2) | Winner` with rows `t | shape | shape | Matcher|Mismatcher`.
- **Execution:** both prompts rendered from the same completed-round history, dispatched separately, both actions
  committed before scoring. Seeded SHA-256 schedule; each replicate wave contains all 36 cells in seeded order; up to 16
  games concurrently. Manifest and hashes frozen before the first scientific call.
- **Parser (mp3m_v1_last_line_exact):** last nonempty line, whitespace trimmed, case ignored, must equal STAR or
  TRIANGLE; anything else (including `**STAR**`, truncation) is invalid. An invalid complete response consumes its slot
  and interrupts the game (not refilled). Transport errors retry the identical payload at most 3 times, idempotent by
  slot id.
- **Scoring:** Matcher wins iff shapes are equal; payoff 1/0; Mismatcher payoff = 1 - V. V_ij(c) = mean Matcher (P1)
  payoff over complete games. U1, U2, U, S_i, O_i, D_i, D_MP exactly as in the handoff; D_MP is the single primary
  contrast for this game. D_RPS - D_MP is descriptive only.
- **Uncertainty:** 5,000 whole-game bootstrap replicates stratified by the 36 cells (analysis seed 20261015); every
  contrast from the same draws; percentile 95% intervals; undefined fractions reported.
- **Descriptive:** shape marginals, switch rate, 2x2 transitions, longest run, win-stay / lose-shift, entropy, win rate,
  by model x role x informed x same/other opponent; prospective history-only predictors (uniform, expanding frequency,
  repeat last, smoothed Markov-1, role-aware best response to opponent's last, win-stay-lose-shift); pooled
  conditional-choice table with game-clustered bootstrap (Brown-Rosenthal-style, descriptive; no per-game multi-lag
  regression, which 19 transitions cannot identify).
- **Budget:** hard cap $60 for this cohort including smoke and retries (proposed; requires Chris's approval); per-call
  worst-case reservation checked against spent + in-flight before every dispatch.
- **Approval:** live calls are impossible unless `APPROVAL.md` contains `LIVE RUN APPROVED BY CHRIS: yes`.
