#!/usr/bin/env bash
# GPU host driver for SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0. Run from the deployed repo root (/root/spar), after
# src/spar_dynamic/dice_logprob_crossmodel/remote_setup.sh (Experiment 28's pins, unchanged). The deployed tree must hold
# src/, Experiment 28's main/ records and Experiment 30's frozen files (verify_frozen runs before every stage).
# usage: run_stage.sh <model...>       each model runs `chain`: preflight -> gate -> calibration -> gate -> main -> checks
set -u
cd /root/spar
export PYTHONPATH=src SPAR_CODE_COMMIT=$(cat CODE_COMMIT) SPAR_HOURLY_USD=${SPAR_HOURLY_USD:-unknown}
for m in "$@"; do
  python -m spar_dynamic.dice_six_roll_recognition.gpu chain --model $m > chain_$m.log 2>&1
  echo "chain $m exit $?" >> stage_status.txt
done
echo "ALL_DONE" >> stage_status.txt
