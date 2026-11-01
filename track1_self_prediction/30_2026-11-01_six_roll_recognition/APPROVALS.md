# Investigator decisions (SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0)

Recorded 2026-11-01. The choices in item 1 were approved before the freeze; this record is committed after the freeze
(commit `d9d8f6b`) and before any GPU work.

1. **Choices where the handoff left details open: accepted as drafted and frozen.**
   - Calibration: 18 synthetic items, each shown in both orders. Two task types are gated: `last_digit` and `all_faces`. The third,
     `order56`, is reported only.
   - "Correct sign" is read as S > ε, and "correct in both orders" as s1 > ε and s2 > ε.
   - Label mass: every technical-preflight P(A)+P(B) must be ≥ 0.5, and so must the median over calibration.
   - ε = max(0.05, 2 × the prefill-vs-tokenwise gap). A judge fails if ε ≥ 1.0.
   - The neutral frame runs on all 32 presentations.
   - Main makes 3 identical calls per presentation.
   - Cross-model policy scoring runs for both models.
   - The investigator was told that Experiment 24's Qwen A/B instrument failed a both-orders gate of this kind.
2. **GPU: one vast.ai A100-80GB rental. Each judge (Qwen, then Mistral) runs `chain`**: preflight → gate → calibration → gate
   → main → checks, stopping at its first FAIL.
   - Gating is per judge: a failing judge is reported NOT RUN, and the other continues.
   - This is the explicit approval for main collection that the protocol requires, conditional on PASS.
   - Hard cap $15. Destroy the instance at the end or on failure.
