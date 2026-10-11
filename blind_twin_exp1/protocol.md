# Blind Twin on Study 1 Experiment 1 game logs (BlindTwinExp1_v1)

Experiment 2 pilot, authorised by Chris on 2026-10-10 ("go ahead and run the blind twin"; scope "Only games where
neither player was told"; hard cap $70). Follows Blind Twin v2 (`blind_twin/`, `blind_twin_rps/`) with these
differences, all fixed before the first paid call.

- **Games observed:** the 36 complete Experiment 1 games from condition 00, where neither player was told the
  opponent's identity: 18 RPS and 18 MP, 2 per ordered pairing. They are taken from each run's `with_makeups/`
  dataset; 1 RPS and 4 MP games are make-ups. The game logs are hashed in `manifest.json`; no new games are played.
- **Judges:** Astra, Fable and Qwen, with the same endpoints and settings as Experiment 1. Each judge makes one fresh
  call per (game, round, label), predicting both players' moves for round t from the public history of rounds before t.
  36 games x 20 rounds x 3 judges x 3 labels = 6,480 calls, in a seeded shuffled order, 16 concurrent.
- **Prompt:** the Experiment 1 rules paragraph for the game, without the player-objective sentence. Then the Blind
  Twin v2 observer wording, with "Player 1 / Player 2" and keys `player_1` / `player_2`. The public history uses the
  same format the players saw.
- **Labels:**
  - TRUE: true model names.
  - ANONYMOUS: "The Player 1 and Player 2 model identities are not disclosed."
  - FALSE: each seat's model replaced by a fixed rotation, Astra->Fable, Fable->Qwen, Qwen->Astra. This is a
    derangement; v2's two-model swap is the special case for two models.
- **Parser:** a bare JSON object with exactly `player_1` and `player_2` and legal moves, case-insensitive, or that
  object alone in one code fence. Otherwise there is no prediction. The paired set is the items valid under all
  three labels.
- **Scoring:** Acc[game type, judge, player model, label], with equal weight over the 6 seat x opponent strata, then
  games, then rounds. T = TRUE - ANONYMOUS and F = TRUE - FALSE. S = mean over target models m of
  (T[m,m] - mean_{j!=m} T[j,m]); S_false likewise with F. The **primary result is S per game type.** Pooled S (the mean
  of RPS and MP) is secondary.
- **Uncertainty:** 5,000 bootstrap resamples of whole games within game type x ordered pairing, all judges and labels
  together (seed 20261017); percentile 95% intervals.
- **Budget:** hard cap $70, with worst-case reservation per call. Live calls need `LIVE RUN APPROVED BY CHRIS: yes`.

## Operational amendment (2026-10-10 23:45)

After 2,532 calls, throughput fell to about 8 calls a minute. Read timeouts and dropped connections affected all three
judges, while their median latencies stayed at 2-12 s, so most slots were idle in 240-second timeouts and retry waits.
The run was stopped (SIGINT), concurrency raised from 16 to 32, and the per-request timeout cut to 120 s (the longest
earlier Qwen call took 291 s, but its p90 is 43 s). The run was then re-frozen and resumed. No prompt, label, parser,
schedule, game set or scoring change. Calls already logged are not reissued. Calls in flight at the stop were lost and
may have been billed without a record (at most 16 calls, about $0.10).
