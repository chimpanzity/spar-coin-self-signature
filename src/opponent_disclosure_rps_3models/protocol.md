# RPS opponent identity disclosure, three-model factorial pilot (RPSDisclosure3M_v1_pilot2)

Implements `RPS_Opponent_Disclosure_Three_Model_Claude_Handoff_2026-10-09.md` without redesign, except for the
prospective two-game-per-cell amendment (`SPAR_Study1_Experiment1_Pilot_2_Games_Per_Cell_Claude_Handoff_2026-10-10.md`).
The earlier eight-game cohort `rps3m-20261009T1240Z` was frozen but never approved or executed (0 calls); it is
superseded, not resized. This is a new cohort with its own protocol id, seeds and schedule.

- **Models (verified from OpenRouter endpoint metadata):** `openai/gpt-6-astra` (OpenAI), `anthropic/claude-fable-5.1`
  (Anthropic), `qwen/qwen3.8-27b` (Alibaba) — the same checkpoint and route as Blind Twin RPS runs
  rps-qf-20261009T1045Z and rps-qa-20261009T1124Z. Names in prompts: "GPT-6 Astra", "Claude Fable 5.1",
  "Qwen3.8 27B". Fallbacks off; temperature/top_p/seed omitted for all; reasoning effort=low, exclude=true;
  max_tokens 4000; one user message per call, no system message.
- **Design:** 9 ordered (Player 1, Player 2) pairings x 4 truthful disclosure assignments (00, 10, 01, 11) x 2
  games x 20 rounds = 72 games, 1,440 rounds, 2,880 planned player calls. No false labels.
- **Prompts:** verbatim game template; `Your model identity is {OWN_MODEL_NAME}.` in every prompt; the opponent
  sentence is the only disclosure-dependent text. History: `None. This is the first round.` or the table
  `Round | Player 1 | Player 2 | Result` with rows `t | move | move | Player 1|Player 2|Tie`.
- **Schedule:** SHA-256-derived; replicate wave k contains all 36 cells in a seeded order; up to 16 games
  concurrently (<= 32 calls in flight). Manifest + hashes frozen before the first scientific call.
- **Parser (rps3m_v1_last_line_exact):** last nonempty line, whitespace trimmed and case ignored, must equal
  ROCK, PAPER or SCISSORS; otherwise invalid (no fallback to explanatory text; `**ROCK**` is invalid).
  Truncated responses are invalid. An invalid complete response consumes its slot; the game is marked
  interrupted at that round and not refilled. Transport errors retry the identical payload at most 3 times.
- **Scoring:** round payoff 1 / 0.5 / 0 (win / tie / loss). V_ij(c) = mean Player 1 payoff over COMPLETE games.
  U1, U2, U, factorial seat effects, interaction, S_i, O_i, D_i and D exactly as in handoff Section 6.
- **Uncertainty:** 5,000 game-level bootstrap replicates stratified by the 36 cells (analysis seed 20261013);
  every contrast recomputed from the same draw; percentile 95% intervals; undefined fractions reported.
- **Descriptive:** move distribution, switch rate, 3x3 transitions, longest run, win-stay / lose-shift /
  tie-shift, entropy; prospective history-only predictors (uniform, expanding frequency, repeat last,
  smoothed one-step Markov, counter opponent's last move), fit only to past rounds.
- **Budget:** hard cap $60 for this cohort (proposed; below the $200 RPS cap) including smoke and retries; per-call worst-case reservation
  (max_tokens x output price + input) is checked against spent + in-flight before every dispatch.
- **Approval:** live calls are impossible unless `APPROVAL.md` contains `LIVE RUN APPROVED BY CHRIS: yes`.
