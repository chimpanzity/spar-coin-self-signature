"""Frozen constants for SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1 (handoff dated 2026-10-31)."""

from __future__ import annotations

from repo_paths import T1
from spar_dynamic.dice_logprob_crossmodel import config as C28

TAG = "SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1"
DESIGN_SOURCE = "SPAR_Experiment_29_Handoff_v1_1.md (2026-10-31; v1.1 adds the middle-anchored arm before any collection)"

EXP = T1 / "29_2026-10-31_bidirectional_dice_completion"
EXP28 = C28.EXP
EXP28_MAIN = C28.MAIN                     # 28_.../main/{qwen,mistral}
PRE, MAIN, ANALYSIS = (EXP / d for d in ("preflight", "main", "analysis"))
LAST_FROZEN_INDEX = 28                    # experiment folders 01-28 are never written to

MODELS = C28.MODELS                       # ("qwen", "mistral"): predictors and sources
MODEL = C28.MODEL
FACES = C28.FACES
SEPARATOR_ID = C28.SEPARATOR_ID
MAX_NEW_TOKENS = C28.MAX_NEW_TOKENS       # 128

# Immutable ground truth: Experiment 28 main greedy outputs (verified against the raw records at freeze).
REFERENCES = {
    ("qwen", "G"): (5, 2, 6, 3, 1, 4, 6, 2, 5, 3),
    ("qwen", "F"): (3, 1, 4, 6, 2, 5, 3, 2, 6, 4),
    ("mistral", "G"): (4, 2, 6, 1, 3, 5, 2, 4, 6, 1),
    ("mistral", "F"): (3, 1, 5, 2, 6, 4, 3, 1, 5, 2),
}
INSTRUCTIONS = ("G", "F")
DIRECTIONS = ("forward", "backward")
KS = tuple(range(1, 10))
MIDDLE_REVEALED = (3, 4, 5, 6, 7, 8)
MIDDLE_MISSING = (1, 2, 9, 10)

N_REPLICATES = 3                          # deterministic replicas, not independent samples
PREFLIGHT_KS = (1, 5, 9)
ARCHIVAL_REPEATS = 2                      # G and F (Experiment 28 prompts) per model, preflight and main
ORDER_SEED = {"qwen": 20261101, "mistral": 20261102}   # main; preflight uses seed + 100

EXPECTED = dict(cells=152, primary_cells=144, supplementary_cells=8, unique_prompts=76, main_generations=456,
                tf_rows=752, tf_rows_primary=720, tf_rows_supplementary=32)

# Gates (Experiment 28 values)
SCORER_TOL_LOGP = 1e-4
REPRO_TOL_P = 0.01
MIN_FACE_MASS_G = 0.5
FLOOR_STOP_P = 0.25
# Stop-for-review rule for teacher-forced mass (handoff 5: "extremely low"); frozen here before any data.
TF_MASS_REVIEW_MEDIAN = 0.10              # a predictor's median raw six-face mass over its teacher-forced rows below this -> STOP
TF_MASS_REVIEW_CELL = 0.01                # any cell whose every teacher-forced row is below this -> STOP

GPU_CAP_USD = 15.0
