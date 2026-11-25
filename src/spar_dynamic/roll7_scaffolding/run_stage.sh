#!/usr/bin/env bash
# GPU host driver for Experiment 35, run from /root/spar after dice_logprob_crossmodel/remote_setup.sh.
set -u
cd /root/spar
export PYTHONPATH=src SPAR_CODE_COMMIT=$(cat CODE_COMMIT) SPAR_HOURLY_USD=${SPAR_HOURLY_USD:-unknown}
for m in qwen mistral; do
  python -m spar_dynamic.roll7_scaffolding.gpu --model $m > run_$m.log 2>&1
  echo "run $m exit $? $(date -u +%FT%TZ)" >> stage_status.txt
done
echo ALL_DONE >> stage_status.txt
