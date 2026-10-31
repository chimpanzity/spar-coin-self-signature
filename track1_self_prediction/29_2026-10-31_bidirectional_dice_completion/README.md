# 29 · Bidirectional cross-model dice completion (2026-10-31)

| | |
|---|---|
| Track | 1: static self-prediction |
| Tag | `SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1` |
| Design source | `SPAR_Experiment_29_Handoff_v1_1.md` (2026-10-31); direct sequel to [28](../28_2026-10-31_dice_logprob_crossmodel/) |
| Status | **Planned: frozen, no GPU data.** Protocol, 152 cells, prompts, code and data dictionary frozen. Preflight and main need investigator authorisation (one A100, $15 cap). |
| Models | Qwen3-32B and Mistral Small 3.2 24B open weights, Experiment 28's engine and pins, unchanged |

## Question

Each model reconstructs missing rolls of Experiment 28's four greedy ground-truth sequences (Qwen/Mistral x G/F):
- forward: given rolls 1..k, predict k+1..10;
- backward: given rolls 11-k..10, predict 1..10-k, in left-to-right order;
- supplementary: given rolls 3-8, predict 1, 2, 9, 10.

The prompt never names the source model, so both predictors receive identical bytes. The question is whether
reconstruction is better on the predictor's own checkpoint's sequences (predictor x source interaction), and how amount and
direction of revealed history matter. Scored by teacher-forced conditional log loss on the true missing digits, plus free
completions.

| File | Contents |
|---|---|
| [`PROTOCOL_FROZEN.md`](PROTOCOL_FROZEN.md) | Hypotheses, design, gates, measurements, analysis plan, stop rules, and the 74-vs-76 prompt count note |
| [`prompts_frozen.md`](prompts_frozen.md), [`conditions.csv`](conditions.csv) | The 76 prompt slots byte-exact; the 152 cells |
| [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md), `manifest_template.json`, `inputs_sha256.json` | Fields, expected counts, frozen hashes (LF-normalised) |

## Re-running

```bash
PYTHONPATH=src python -m pytest tests/test_dice_bidirectional_completion.py      # offline, fake engine
PYTHONPATH=src python -m spar_dynamic.dice_bidirectional_completion dryrun       # counts, example prompts, cost estimate
# GPU host (repo root), after src/spar_dynamic/dice_logprob_crossmodel/remote_setup.sh:
bash src/spar_dynamic/dice_bidirectional_completion/run_stage.sh preflight qwen mistral
PYTHONPATH=src python -m spar_dynamic.dice_bidirectional_completion gate_preflight <model>     # locally
bash src/spar_dynamic/dice_bidirectional_completion/run_stage.sh main qwen mistral             # after approval
PYTHONPATH=src python -m spar_dynamic.dice_bidirectional_completion gate_main <model>
PYTHONPATH=src python -m spar_dynamic.dice_bidirectional_completion analyse
```
