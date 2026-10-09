# Blind Twin RPS protocol (BlindTwinRPS_v1)

The Blind Twin v2 design (matching pennies, run `bt2-20261009T0957Z`) applied to rock-paper-scissors at
Chris's request ("try it again with rock paper scissors", 2026-10-09). Everything not listed here is
identical to Blind Twin v2 (see `blind_twin/protocol.md`).

## Changes required by the game
- **Seats:** symmetric Player A / Player B (RPS has no matcher/mismatcher). Each player's objective is to
  choose the move that beats the other's. Matchups are ordered (seat A model, seat B model):
  Astra-Astra, Astra-Fable, Fable-Astra, Fable-Fable; 3 games each, 20 rounds.
- **Moves:** ROCK, PAPER, SCISSORS. History table `| Round | Player A | Player B | Result |` with results
  "Player A wins", "Player B wins" or "Tie".
- **Player format line:** "You may briefly think through your choice. End your response with the chosen
  move (ROCK, PAPER, or SCISSORS) alone on the final line." (v2 wording with "move" for "shape").
- **Judge answer:** `{"player_a": ..., "player_b": ...}`; identity line "Player A is X; Player B is Y." FALSE
  swaps Astra and Fable separately for each seat, exactly as in v2.
- **Chance:** 33.3% per seat prediction.
- **Baselines (prior history only):** frequency of own moves; repeat own last; cycle up (R->P->S->R) and
  cycle down from own last; counter the opponent's last move; win-stay/lose-shift (after a loss or tie,
  play the move that beats the opponent's last move); one-step Markov on own transitions with add-one
  smoothing. Tied predictions get fractional credit (1/|tied set| if correct); round 1 gets 1/3.
- **Parser (btrps_v1_final_line):** v2 final-line rule for three moves.
- **Seeds:** master seed 20261010 (distinct from v2's schedule).
