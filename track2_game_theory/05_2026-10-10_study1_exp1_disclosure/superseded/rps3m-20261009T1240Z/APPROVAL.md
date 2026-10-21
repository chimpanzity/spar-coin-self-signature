# APPROVAL

Run `rps3m-20261009T1240Z`. Protocol RPSDisclosure3M_v1. Hard cap $200.00 for this experiment (smoke + retries included).

## Cost estimate (from prior RPS per-call costs)

| model | planned calls | mean $/call | p95 $/call | expected $ | pessimistic $ |
|---|---:|---:|---:|---:|---:|
| astra | 3840 | 0.00510 | 0.00848 | 19.58 | 32.56 |
| fable | 3840 | 0.01490 | 0.02403 | 57.23 | 92.28 |
| qwen | 3840 | 0.00228 | 0.00414 | 8.74 | 15.90 |

- Expected total: $85.55; pessimistic (every call at p95): $140.74; with 3% retry allowance and $1.79 smoke: $146.75.
- Maximum in-flight worst-case reservation: $7.68 (enforced against the cap before every dispatch).

## Status

LIVE RUN APPROVED BY CHRIS: no

Live calls are blocked until the line above reads exactly `LIVE RUN APPROVED BY CHRIS: yes`, which Claude writes only after Chris's explicit approval in chat.
