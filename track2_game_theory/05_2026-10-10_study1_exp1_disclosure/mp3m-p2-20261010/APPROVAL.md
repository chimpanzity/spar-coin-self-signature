# APPROVAL

Run `mp3m-p2-20261010`. Protocol MPDisclosure3M_v1_pilot2. Hard cap $60.00 for this experiment (smoke + retries included).

## Cost estimate (from prior per-call costs on the same endpoints)

| model | planned calls | mean $/call | p95 $/call | expected $ | pessimistic $ |
|---|---:|---:|---:|---:|---:|
| astra | 960 | 0.00510 | 0.00848 | 4.90 | 8.14 |
| fable | 960 | 0.01490 | 0.02403 | 14.31 | 23.07 |
| qwen | 960 | 0.00228 | 0.00414 | 2.18 | 3.97 |

- Expected total: $21.39; pessimistic (every call at p95): $35.18; with 3% retry allowance and $1.79 smoke: $38.03.
- Maximum in-flight worst-case reservation: $7.68 (enforced against the cap before every dispatch).

## Status

LIVE RUN APPROVED BY CHRIS: yes

Live calls are blocked until the line above reads exactly `LIVE RUN APPROVED BY CHRIS: yes`, which Claude writes only after Chris's explicit approval in chat.
Approved by Chris in chat 2026-10-10 ("run em both"): hard cap $60, contingency reserve $25. Re-frozen after the price-lookup fix; approval carried over (no scientific change).
