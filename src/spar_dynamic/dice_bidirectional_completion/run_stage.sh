#!/usr/bin/env bash
# GPU host driver for SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1. Run from the deployed repo root (/root/spar), after
# src/spar_dynamic/dice_logprob_crossmodel/remote_setup.sh (Experiment 28's pins, unchanged).
# usage: run_stage.sh <preflight|main> <model...>     (main needs preflight/<model>/preflight_gates.json uploaded first)
set -u
cd /root/spar
export PYTHONPATH=src SPAR_CODE_COMMIT=$(cat CODE_COMMIT) SPAR_HOURLY_USD=${SPAR_HOURLY_USD:-unknown}
E=track1_self_prediction/29_2026-10-31_bidirectional_dice_completion
stage=$1; shift
for m in "$@"; do
  if [ "$stage" = main ]; then extra="--gate $E/preflight/$m/preflight_gates.json"; else extra=""; fi
  python -m spar_dynamic.dice_bidirectional_completion.gpu $stage --model $m --out $E/$stage/$m $extra > ${stage}_$m.log 2>&1
  echo "$stage $m exit $?" >> stage_status.txt
done
echo "ALL_DONE $stage" >> stage_status.txt
