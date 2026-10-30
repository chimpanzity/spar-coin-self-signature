"""Frozen configuration for LOULA_DICE_RECOGNITION v2.0 (handoff 2026-10-29, Experiment 23).

Models, providers, generation settings and the v1 frozen classifier are reused from Experiment 22 unchanged.
Changing any value here after `dryrun` writes PROTOCOL_FROZEN.md is a versioned amendment needing approval.
"""

from __future__ import annotations

from spar_dynamic.dice_recognition import config as V1

TAG = "LOULA_DICE_RECOGNITION_v2.0"

MODELS = V1.MODELS                                   # same slugs, pinned providers, reasoning-off for Qwen
SOURCES = V1.SOURCES
OTHER = {"qwen": "mistral", "mistral": "qwen"}

GENERATION = dict(V1.GENERATION)                     # temperature 0.7, top_p 1, max_tokens 64
JUDGMENT = {"bare": dict(temperature=0.0, top_p=1.0, max_tokens=8),
            "brief": dict(temperature=0.0, top_p=1.0, max_tokens=160)}
FORMATS = ("bare", "brief")

# Stage A (calibration)
N_CAL_ITEMS = 12
CAL_TASKS = ("MORE_SIXES", "MORE_REPEATS", "GEN_RULE")
GATES = {"MORE_SIXES": dict(min_correct=20, min_consistent=10),
         "MORE_REPEATS": dict(min_correct=20, min_consistent=10),
         "GEN_RULE": dict(min_correct=18, min_consistent=9)}
MIN_FORMAT_VALIDITY = 0.95
RULE_R_REPEAT, RULE_S_REPEAT = 0.70, 0.05            # generator definitions, A2
RULE_LEN = (10, 20)                                  # inclusive range of rolls per item (same length within a pair)

# Stage C corpus
N_EVAL_PER_SOURCE = 100                              # 20 families x 5 blocks
N_FAMILIAR_PER_SOURCE = 10
N_VALID_PER_SOURCE = N_EVAL_PER_SOURCE + N_FAMILIAR_PER_SOURCE
MAX_ATTEMPTS_PER_SOURCE = 160
N_FAMILIES, BLOCKS_PER_FAMILY = 20, 5
DOSES = (1, 3, 5)
N_EXPOSURE_EXAMPLES = 5
N_LIVE_FAMILIES = 8                                  # D2, per judge
N_LIVE_GEN_TURNS = 3

# Validity stop for live judgment stages: stop a stage if a judge's invalid share exceeds this after MIN_N calls.
STAGE_MAX_INVALID_SHARE, STAGE_MIN_N = 0.10, 40

COST_CAP_USD = 5.00
MAX_CALL_COST_PRIOR_USD = 0.002
MAX_TRANSPORT_RETRIES = 4
CONCURRENCY = 4                                      # bounded; dispatch order is recorded

SEEDS = dict(calibration_items=2026102911, calibration_order=2026102912, screen_order=2026102913,
             gen_schedule=2026102914, partition=2026102915, dose_order=2026102916, named_order=2026102917,
             exposure_select=2026102918, exposure_order=2026102919, live_order=2026102920, bootstrap=2026102921)
N_BOOTSTRAP = 10000

V1_EXP_KEY = "dice_recognition"                      # Experiment 22 folder (read-only)
