# Blind Twin protocol (BlindTwin_v1)

Implements `Blind_Twin_Overnight_Pilot_Handoff.md` (9 October 2026) without design changes.

## Operational decisions not fixed by the handoff
- **Decoding:** neither endpoint supports temperature; temperature, top_p and seed are omitted. Reasoning `effort=low, exclude=true` (same as the SPAR Phase 2 runs); `max_tokens=4000` (includes hidden reasoning). Providers pinned (OpenAI, Anthropic), fallbacks off.
- **Public history rendering:** markdown table `| Round | Matcher | Mismatcher | Winner |`; before round 1 the history slot reads `(no completed rounds)`.
- **Player parser (bt_v1):** exactly one shape word, case-insensitive; cosmetic wrappers (markdown emphasis, quotes, trailing period) allowed and flagged `ok_wrapped`. Anything else is invalid. An invalid choice ends that game at that round (marked incomplete); completed malformed responses are never resampled. Transport errors (429/5xx/timeouts) are retried with the same payload at most 3 times.
- **Judge parser (bt_v1):** bare JSON object with exactly the keys `matcher`, `mismatcher` and values STAR/TRIANGLE (case-insensitive), or that object alone inside one code fence. Invalid responses yield no prediction.
- **Eligibility:** for each judge, the paired set is the (game, round, seat) items with valid predictions in all three label conditions. Acc[j,g,c] averages, with equal weight, the four (seat x opponent-model) strata; within a stratum, games equally; within a game, rounds equally.
- **Baselines (history-only, per seat):** frequency of own prior choices; repeat last; alternate last; win-stay/lose-shift; one-step Markov on own transitions with add-one smoothing. Round 1 and ties receive half credit.
- **Uncertainty:** 5,000 bootstrap resamples of games within each of the four matchups (3 per type), all rounds/judges/labels carried together; intervals with more than 1% undefined replicates are labelled unstable.
- **Execution:** the 12 games run concurrently (time-interleaved); both seats' requests are dispatched from the identical prior history before either answer is committed. After all games, logs and a seeded shuffled judge schedule are hashed and frozen; judge requests run 8 at a time in that order.
- **Budget:** hard ceiling enforced per call with reservation; see `results/<run>/approvals.jsonl`.
