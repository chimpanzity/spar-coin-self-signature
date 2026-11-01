"""Frozen constants for SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0 (handoff dated 2026-11-01)."""

from __future__ import annotations

from repo_paths import T1
from spar_dynamic.dice_bidirectional_completion import config as C29
from spar_dynamic.dice_logprob_crossmodel import config as C28

TAG = "SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0"
DESIGN_SOURCE = "GPT_Experiment_30_Recognition_Handoff.md (2026-11-01, draft protocol to freeze before GPU collection)"

EXP = T1 / "30_2026-11-01_six_roll_recognition"
EXP28 = C28.EXP
EXP28_MAIN = C28.MAIN                     # 28_.../main/{qwen,mistral}: ground truth and archived position-5/6 vectors
PRE, CAL, MAIN, POLICY, ANALYSIS = (EXP / d for d in ("preflight", "calibration", "main", "policy_benchmark", "analysis"))
LAST_FROZEN_INDEX = 29                    # experiment folders 01-29 are never written to

MODELS = C28.MODELS                       # ("qwen", "mistral"): judges, generative scorers and sources
MODEL = C28.MODEL
FACES = C28.FACES
SEPARATOR_ID = C28.SEPARATOR_ID
MAX_NEW_TOKENS = C28.MAX_NEW_TOKENS       # archival G/F regeneration (128)
ANSWER_MAX_NEW_TOKENS = 16                # bounded greedy completion after a recognition / calibration question
LABELS = ("A", "B")
TOP_N = 10

# Immutable ground truth: Experiment 28 main greedy outputs (re-read from the raw records at freeze and in every gate).
REFERENCES = C29.REFERENCES
INSTRUCTIONS = ("G", "F")
FOILS = ("swap", "repeat")                # swap primary (source-specific), repeat secondary (generic rule)
FRAMES = ("self", "neutral")              # neutral companion control: all 32 presentations, prespecified secondary arm
ORIENTATIONS = (1, 2)                     # 1: A = authentic, B = foil; 2: A = foil, B = authentic
N_REPLICATES = 3                          # identical main calls per presentation: determinism check, not replication
PREFLIGHT_REPEATS = 3

# Handoff section 5: archived Experiment 28 fifth-roll face-only probabilities (authentic, swapped), checked programmatically.
ARCHIVED_P5 = {("qwen", "G"): (0.8608, 0.1391), ("qwen", "F"): (0.999628, 0.000372),
               ("mistral", "G"): (0.6867, 0.3126), ("mistral", "F"): (0.8323, 0.1661)}
ARCHIVED_P5_TOL = 0.0005

# Calibration (handoff section 4): 3 task types x 6 items x 2 orientations per judge, generated from a fixed seed at freeze.
CAL_SEED = 20261101
CAL_ITEMS_PER_TYPE = 6
CAL_GATED = ("last_digit", "all_faces")   # gated; "order56" (moderately hard) is reported, not gated
CAL_MIN_S_CORRECT = 5                     # of 6: S > epsilon
CAL_MIN_BOTH_ORDERS = 4                   # of 6: s1 > epsilon and s2 > epsilon

# Numerical floor and label mass
EPS_MIN = 0.05
EPS_MULT = 2.0                            # epsilon = max(EPS_MIN, EPS_MULT * max |d_prefill - d_tokenwise|), preflight + calibration
EPS_STOP = 1.0                            # epsilon >= this: the instrument is too noisy (Experiment 24 rule) -> judge fails
MIN_MASS_TECH = 0.5                       # P(A)+P(B) on every technical preflight call
MIN_MEDIAN_MASS_CAL = 0.5                 # median P(A)+P(B) over a judge's calibration presentations
LOW_MASS_FLAG = 0.10                      # main presentations below this are flagged
MIN_MEDIAN_MASS_MAIN = 0.5                # a judge below this: answer-probability interpretation rejected (reported, not run again)

# Archival / policy gates (Experiment 28/29 values)
SCORER_TOL_LOGP = C28.SCORER_TOL_LOGP
REPRO_TOL_P = C28.REPRO_TOL_P
MIN_FACE_MASS_G = C28.MIN_FACE_MASS_G
FLOOR_STOP_P = C28.FLOOR_STOP_P
ARCHIVAL_REPEATS = 2
ORDER_SEED = {"qwen": 20261111, "mistral": 20261112}   # main; calibration +50, preflight +100

GPU_CAP_USD = 15.0
