#!/usr/bin/env bash
# GPU host driver for Experiment 38. Run from the deployed repo root (/root/spar) after
# src/spar_dynamic/dice_logprob_crossmodel/remote_setup.sh (Experiment 28's pins, unchanged). The deployed tree must hold src/, the
# frozen files of Experiment 38 and the archived inputs listed in its inputs_sha256.json.
# usage: run_stage.sh <model...>     each model: validate -> preflight -> policy -> prompts, stopping on failure
set -u
cd /root/spar
export PYTHONPATH=src SPAR_CODE_COMMIT=$(cat CODE_COMMIT) SPAR_HOURLY_USD=${SPAR_HOURLY_USD:-unknown}
python -m spar_dynamic.slot_skip_ahead validate > validate.log 2>&1 || { echo "validate FAIL" >> stage_status.txt; echo "ALL_DONE" >> stage_status.txt; exit 1; }
for m in "$@"; do
  python -m spar_dynamic.slot_skip_ahead.gpu --model $m > run_$m.log 2>&1
  echo "run $m exit $? $(date -u +%FT%TZ)" >> stage_status.txt
done
echo "ALL_DONE" >> stage_status.txt
