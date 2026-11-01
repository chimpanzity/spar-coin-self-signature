# Experiment 30: six-roll self-recognition by minimal-pair discrimination (2026-11-01)

`SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0`. Each judge (Qwen3-32B, Mistral Small 3.2 24B; open weights, one A100) chooses between
two versions of a six-roll sequence:

- the authentic first six rolls of one of Experiment 28's four ten-roll outputs;
- a minimal foil: rolls 5 and 6 swapped (primary) or roll 6 repeating roll 5 (secondary).

Each pair is shown in both orders, under a self frame and a neutral frame. Each source model's own two-step likelihood of the
endings is the benchmark.

**Result:** no self-specific recognition. The swap D is −0.28 (G) and −0.03 (F) log-odds, and every swap pair is
order-inconsistent under a large A bias. The generative policies favour the authentic endings, but generically. Qwen shows a
shared no-repeat preference. Both judges passed every gate. $2.09.

| File | Content |
|---|---|
| [REPORT.md](REPORT.md) | Full results, figures, limitations, run record |
| [DECISION_MEMO.md](DECISION_MEMO.md) | One-page outcome and next steps |
| [PROTOCOL_FROZEN.md](PROTOCOL_FROZEN.md), [prompts_frozen.md](prompts_frozen.md), [conditions.csv](conditions.csv), [calibration_items.csv](calibration_items.csv), [DATA_DICTIONARY.md](DATA_DICTIONARY.md), [inputs_sha256.json](inputs_sha256.json) | Frozen before any GPU call (`d9d8f6b`) |
| [APPROVALS.md](APPROVALS.md) | Investigator decisions |
| `preflight/`, `calibration/`, `main/` (`<judge>/presentations.jsonl`, `env_*.json`, gate JSON and Markdown) | Raw calls and gates |
| `policy_benchmark/<scorer>/policy_teacher_forced.jsonl` | Teacher-forced six-roll histories |
| `analysis/` | CSV tables, `summary.json`, `calibration_gate.json`, `figures/` (PNG and PDF) |
| `host_logs/` | Setup and chain logs from the GPU host |
| [manifest.json](manifest.json) | Commits, instance, cost, environments, file hashes |

Code: `src/spar_dynamic/dice_six_roll_recognition/`. Tests: `tests/test_dice_six_roll_recognition.py`.
