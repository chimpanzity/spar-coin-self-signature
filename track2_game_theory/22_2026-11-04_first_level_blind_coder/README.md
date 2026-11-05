# 22: First-level Blind Coder (2026-11-04)

Can Astra and Fable each write a program that predicts its **own actual matching-pennies choices** better than a program
written by the other model?

Method:
- 40 fresh author calls: 2 authors × 2 named players × 10 blocks, costing $3.14.
- The 40 programs were frozen, hashed and run in a sandbox on all 480 archived Astra and Fable decisions from the Study 1
  condition-00 games.

**Result:** Astra's code predicted *both* players better, so there was no reciprocal own-model advantage. Naming the target
did not help. No program captured how the players react to wins and losses. See [REPORT.md](REPORT.md).

| Path | Content |
|---|---|
| [REPORT.md](REPORT.md) | Answers, 2 × 2 table, references, block contrasts, sensitivity, targeting, win/loss switching, program review, run record |
| `plan/` | Frozen author messages, `schedule.json` (seed 20261105), endpoint and price snapshot, `run_plan.json` (inputs, code, test and message hashes; worst-case costs) |
| [APPROVAL.md](APPROVAL.md) | Live approval for this plan's hash only |
| `responses/calls.jsonl`, `run.log` | The 40 raw author responses (request, response id, returned model and provider, usage, cost) and the run log |
| `programs/` | The 40 frozen programs and `sources_sha256.json` |
| `validation/contract.json` | Contract results on synthetic histories |
| `scoring/` | `item_predictions.csv` (480 decisions × 40 programs and 4 references), `generation_scores.csv`, `results.json` |
| `dry_run/` | The same pipeline with fake programs, made before any paid call |
| [manifest.json](manifest.json) | Commits, provider metadata, cost, counts, deviations, file hashes |

Code: `src/blind_coder_player_choices/`. Tests: `tests/test_blind_coder_player_choices.py`.

Reproduce with zero API calls:

```bash
PYTHONPATH=src python -m blind_coder_player_choices validate
PYTHONPATH=src python -m blind_coder_player_choices score
```
