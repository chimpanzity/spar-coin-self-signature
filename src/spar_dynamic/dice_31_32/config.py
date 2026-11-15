"""Frozen constants for SPAR Track 1 Experiments 31 and 32 (handoff dated 2026-11-15).

Experiment 31 (SPAR_EXP31_CROSS_MODEL_TEACHER_FORCING_v1.0): fully crossed one-step teacher-forced six-face probabilities.
Experiment 32 (SPAR_EXP32_ROLL7_INTERMEDIATE_CONTEXT_v1.0): roll-7 prediction with a generated, absent or supplied sixth roll.

The two experiments share one GPU rental, the Experiment 27-30 engine and these scoring utilities, but have separate folders,
manifests, raw records, analyses, figures and reports.
"""

from __future__ import annotations

from repo_paths import T1
from spar_dynamic.dice_bidirectional_completion import config as C29
from spar_dynamic.dice_logprob_crossmodel import config as C28

TAG31 = "SPAR_EXP31_CROSS_MODEL_TEACHER_FORCING_v1.0"
TAG32 = "SPAR_EXP32_ROLL7_INTERMEDIATE_CONTEXT_v1.0"
DESIGN_SOURCE = "GPT_SPAR_Experiments_31_32_Revised_Claude_Code_Handoff.md (2026-11-15, frozen-design implementation request)"

EXP31 = T1 / "31_2026-11-15_cross_model_teacher_forcing"
EXP32 = T1 / "32_2026-11-15_roll7_intermediate_context"
EXP28 = C28.EXP
EXP28_MAIN = C28.MAIN                     # 28_.../main/{qwen,mistral}: ground truth, archival generations, matched-prefix rows
EXP30_POLICY = T1 / "30_2026-11-01_six_roll_recognition" / "policy_benchmark"
LAST_FROZEN_INDEX = 30                    # experiment folders 01-30 are read, never written

# Models and serving: Experiment 27-30 pins and engine, unchanged.
MODELS = C28.MODELS                       # ("qwen", "mistral")
MODEL = C28.MODEL
FACES = C28.FACES
SEPARATOR_ID = C28.SEPARATOR_ID           # the single-space token between faces (qwen 220, mistral 1032)
MAX_NEW_TOKENS = C28.MAX_NEW_TOKENS       # 128: archival G/F regeneration and every Experiment 32 free generation
TOP_N = 10

# Immutable ground truth: Experiment 28 main greedy outputs (re-read from the raw records at freeze and in every gate).
REFERENCES = C29.REFERENCES
INSTRUCTIONS = ("G", "F")
SEQ_LEN = 10

# Experiment 31 design
POSITIONS = tuple(range(1, 11))
CONTINUATION_POSITIONS = tuple(range(2, 11))
EXPECTED31 = dict(labeled_rows=160, cross_model_rows=80, streams=16, streams_per_scorer=8)
# Remaining-face heuristic (handoff 31.3 D): positions 2-6 use {1..6} minus rolls 1..j-1. Positions 7-10 use a clearly labelled
# six-position reset at roll 7 ({1..6} minus rolls 7..j-1), applied only when rolls 1-6 are six distinct faces (a complete
# permutation segment); otherwise the diagnostic is omitted (ambiguous). Position 1 and 7 are unconstrained (6 remaining).
RESET_POSITION = 7

# Experiment 32 design
SOURCES32 = (("qwen", "G"), ("mistral", "G"))
CONDITIONS32 = ("A", "B", "C")            # A pair-generated, B direct-seven, C authentic sixth supplied
N_PREFIX32 = 5
EXPECTED32 = dict(cells=12, unique_prompts=6)

# Determinism: every scored context is computed twice (incremental replicate 1 and 2) and must be bit-identical.
N_REPLICATES = 2
ARCHIVAL_REPEATS = 2

# Gates (Experiment 28-30 values)
SCORER_TOL_LOGP = C28.SCORER_TOL_LOGP     # 1e-4 nats: own-output rescoring vs generation
REPRO_TOL_P = C28.REPRO_TOL_P             # 0.01: archival regression, six-face |dp|
MIN_FACE_MASS_G = C28.MIN_FACE_MASS_G     # 0.5 at every archival G digit step
FLOOR_STOP_P = C28.FLOOR_STOP_P           # 0.25: incremental vs full pass stop
ARCHIVE_EQUIV_TOL_LOGP = 1e-4             # an Experiment 28 / 30 row counts as an equivalent archival record within this
NEAR_TIE_P = 0.02                         # top-face margin below this (normalised p) is flagged as a near-tie
JS_TOL = 1e-9

ORDER_SEED = {"qwen": 20261115, "mistral": 20261116}   # recorded job order; greedy decoding makes order irrelevant

GPU_CAP_USD = 10.0
