# Investigator decisions (SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1)

Recorded 2026-10-31, after the freeze (commit `201ad2b`) and before any GPU work.

1. **Prompt count discrepancy (74 distinct texts over 76 prompt slots): accepted as documented.** Run as frozen; the four
   F forward k = 1, 2 cells are flagged in the report (their diagonal contrast reflects source difficulty only).
2. **GPU: one vast.ai A100-80GB rental, preflight for both predictors, then the full main run in the same rental only if every
   hard preflight gate passes** (including the teacher-forced mass review rule). Hard cap $15; destroy the instance at the end
   or on failure. This is the explicit main-collection approval the protocol requires, conditional on PASS.
