# Blocker: Fable explains its move, so 9 of 12 games stopped early

**What happened.** In every game with a Fable seat, Fable eventually answered with one sentence of
reasoning followed by the shape on its own line, e.g.

    Mismatcher has alternated TRIANGLE, STAR, TRIANGLE — pattern suggests STAR next.

    STAR

The prompt says "Return ONLY the chosen shape", and the frozen parser (bt_v1) accepts only a single
shape word. As the handoff requires, each such answer made that round invalid, the game was marked
incomplete, and nothing was resampled or repaired. All 10 invalid player answers (all Fable) have this
exact two-line form.

| matchup | games complete | valid rounds |
|---|---:|---:|
| Astra–Astra | 3/3 | 60/60 |
| Astra–Fable | 0/3 | 18/60 (games ended at rounds 5, 7, 9) |
| Fable–Astra | 0/3 | 9/60 (all ended at round 4) |
| Fable–Fable | 0/3 | 16/60 (ended at rounds 5, 7, 7) |

Judging ran on the 103 valid rounds as frozen (618 calls, all valid). The results in `report.md` are
therefore dominated by Astra–Astra games; every Fable-seat estimate rests on rounds 1–9 only.

**Second issue (independence).** Without temperature control, "independent" games repeat: all three
Fable–Astra games opened STAR-TRIANGLE-STAR / TRIANGLE-STAR-TRIANGLE before stopping at round 4, and the
Astra–Astra games share similar openings. Three replicates per matchup are less than three independent
games.

**Not done (per the handoff: no improvised substitutes).** The parser, prompts, models and sample size
were not changed after these failures.

## Options for Chris (each defines a NEW run; this run stays as is)

1. **Final-line rule (recommended).** Accept a player answer if its last non-empty line, after removing
   cosmetic wrappers, is exactly one shape, and no earlier line is itself a bare shape. This would have
   accepted all 10 failures and changes no prompt text or model setting. Prespecify before the new run.
2. **Prompt change.** Add a stricter format line (e.g. "Do not explain your choice."). Changes the
   protocol text shared by all players.
3. **Allow more hidden reasoning for Fable** (effort above low), hoping the explanation moves into hidden
   reasoning. Changes decoding and cost; not guaranteed.

The independence issue needs its own decision: more replicates, a varied first-round context, or reporting
replicates as dependent.
