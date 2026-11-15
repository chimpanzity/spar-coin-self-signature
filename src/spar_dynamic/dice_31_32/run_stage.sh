#!/usr/bin/env bash
# GPU host driver for Experiments 31 and 32. Run from the deployed repo root (/root/spar) after
# src/spar_dynamic/dice_logprob_crossmodel/remote_setup.sh (Experiment 28's pins, unchanged). The deployed tree must hold src/,
# Experiment 28's main/ records, Experiment 30's policy_benchmark/ and the frozen files of Experiments 31 and 32.
# usage: run_stage.sh <model...>     each model: validate -> preflight (archival check) -> Exp 31 -> Exp 32, stopping on failure
set -u
cd /root/spar
export PYTHONPATH=src SPAR_CODE_COMMIT=$(cat CODE_COMMIT) SPAR_HOURLY_USD=${SPAR_HOURLY_USD:-unknown}
python -m spar_dynamic.dice_31_32 validate > validate.log 2>&1 || { echo "validate FAIL" >> stage_status.txt; echo "ALL_DONE" >> stage_status.txt; exit 1; }
for m in "$@"; do
  python -m spar_dynamic.dice_31_32.gpu run --model $m > run_$m.log 2>&1
  echo "run $m exit $?" >> stage_status.txt
done
echo "ALL_DONE" >> stage_status.txt
