# Study 1, Experiment 1: budget and approval (2026-10-10)

## Account (verified via OpenRouter API, 2026-10-10)

- Account credits: $900 purchased, $577.18 used, so **$322.82 available**. Chris's estimate was about $320.
- API key: $500 limit, $178.40 used, so $321.60 remaining on the key.
- Earlier the same day the account showed $600 purchased (only $22.82 available); Chris topped it up.

## Estimates (per-call costs from 1,440 earlier calls on the same endpoints and settings)

| cohort | calls | expected | pessimistic (p95 per call + 3% retries + smoke) | proposed hard cap |
|---|---:|---:|---:|---:|
| RPS `rps3m-p2-20261010` | 2,880 | $21.39 | $38.03 | $60 |
| MP `mp3m-p2-20261010` | 2,880 | $21.39 | $38.03 | $60 |
| **Total** | 5,760 | **$42.78** | **$76.06** | **$120** |

The MP estimate reuses RPS per-call costs: MP prompts are about the same length. The Astra-only MP pilot's $0.0052/call
is consistent with this. Fable is about two thirds of the cost.

## Capacity

Spendable = min(available $322.82 - $25 contingency reserve, cap): RPS $60, MP $60. Both caps fit with large headroom.
Each runner reserves the worst-case cost of every call (max_tokens x output price + input) against spent + in-flight
before dispatch and stops cleanly at its cap. Partial games are preserved and reported, not refilled.

## Approval gates (approved by Chris in chat 2026-10-10)

- [x] RPS: hard cap $60, live run of `rps3m-p2-20261010`. Supersedes the never-executed $200 eight-game approval request.
- [x] MP: hard cap $60, live run of `mp3m-p2-20261010`.
- [x] Contingency reserve: $25.

Claude writes `LIVE RUN APPROVED BY CHRIS: yes` into a run's APPROVAL.md only after Chris approves that run in chat.

## Actual spend (2026-10-10)

- RPS $22.32, MP $20.28, total $42.60 logged. Account usage rose $577.18 -> $619.79 (+$42.61). About $280 remains.
- Make-up games (Chris's instruction, within the same caps): RPS +$0.29, MP +$7.09. Experiment 1 total $49.97.
