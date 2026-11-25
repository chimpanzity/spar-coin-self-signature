#!/usr/bin/env bash
# GPU host driver for Experiment 33. Run from /root/spar after dice_logprob_crossmodel/remote_setup.sh.
# core (qwen, mistral) -> core checks -> extensions (qwen, mistral); stops at the first failure.
set -u
cd /root/spar
export PYTHONPATH=src SPAR_CODE_COMMIT=$(cat CODE_COMMIT) SPAR_HOURLY_USD=${SPAR_HOURLY_USD:-unknown}
S=stage_status.txt
step() { n=$1; shift; "$@" > "$n.log" 2>&1; rc=$?; echo "$n exit $rc $(date -u +%FT%TZ)" >> $S; [ $rc -eq 0 ] || { echo ALL_DONE_FAIL >> $S; exit 1; }; }
R="python -m spar_dynamic.dice_scaffolding"
step validate $R validate
step core_qwen $R collect --phase core --model qwen
step core_mistral $R collect --phase core --model mistral
step checks_core $R checks --phase core
step ext_qwen $R collect --phase extensions --model qwen
step ext_mistral $R collect --phase extensions --model mistral
echo ALL_DONE >> $S
