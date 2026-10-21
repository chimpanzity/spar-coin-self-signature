# Blind Twin self-self 00-vs-11 pilot (BlindTwinSelfSelf_v1)

Authorised by Chris on 2026-10-11 ("run it"), after reviewing the extension proposal and its critique. Exploratory
pipeline pilot for a powered self-self study; not a test of privileged access. Fixed before any paid call.

- **Question:** does truthful identity information help an observer more when the observed players were themselves
  told their opponent's identity? Does that help differ when the observer is the same model as the players?
- **Games:** all complete Experiment 1 self-self games (Astra-Astra, Fable-Fable, Qwen-Qwen) from conditions 00
  (neither player told) and 11 (both told), RPS and MP, from each run's `with_makeups/` dataset. That gives 2 games
  per cell, 24 games, selected by rule; no game is selected on its results. The game logs are hashed in
  `manifest.json`.
- **Judges and labels:** Astra, Fable and Qwen; TRUE, FALSE (fixed rotation Astra->Fable->Qwen->Astra) and ANONYMOUS.
  24 games x 20 rounds x 3 x 3 = 4,320 calls, seeded shuffled order, 32 concurrent, 120 s request timeout.
- **Prompt:** BlindTwinExp1_v1 judge prompt plus one line after the identities:
  - 00: "Player information: Neither player was told its opponent's model identity."
  - 11: "Player information: Before the game, each player was told the true model identity of its opponent."

  The wording names no model, so it does not reveal identities under ANONYMOUS or contradict FALSE. Because the prompt
  differs from BlindTwinExp1_v1, the 12 condition-00 games are re-judged here; the earlier run is not pooled.
- **Parser:** as BlindTwinExp1_v1. The paired set is the items valid under all three labels.
- **Scoring:** Acc[game type, condition, judge, model, label], with equal weight over the two seats, then games, then
  rounds. T = TRUE - ANONYMOUS. Delta[j,m] = T_11 - T_00. Delta_self = mean over m of Delta[m,m]. Delta_other = mean
  over m of the mean over j != m of Delta[j,m]. **The primary result, per game type, is Delta_selfspec = Delta_self -
  Delta_other.** DeltaF uses F = TRUE - FALSE. Pooled values (the mean of the two game types) are secondary. Also
  reported: S within each condition, and the external history-only classifiers on the same games for 00 vs 11.
- **Uncertainty:** 5,000 bootstrap resamples of whole games within game type x model x condition (seed 20261019).
- **Budget:** hard cap $40 with worst-case reservation. Live calls need `LIVE RUN APPROVED BY CHRIS: yes`. The machine
  is kept awake with `caffeinate` for the life of the run.
