"""Frozen constants for SPAR_DICE_LOGPROB_CROSSMODEL_v2.0 (handoff dated 2026-10-31)."""

from __future__ import annotations

from repo_paths import T1
from spar_dynamic.dice_crossed_guidance import config as XC

TAG = "SPAR_DICE_LOGPROB_CROSSMODEL_v2.0"
DESIGN_SOURCE = "Main_Experiment_SPAR_Dice_Logprob_Qwen_Mistral_Claude_Code_Handoff.md (2026-10-31)"

EXP = T1 / "28_2026-10-31_dice_logprob_crossmodel"
EXP21 = XC.EXP21                          # 21_2026-10-29_dice_logprob/main-qwen3-32b-a100
EXP27_PRE = XC.PRE                        # 27_.../preflight/{qwen,mistral}
PRE, MAIN, ANALYSIS = (EXP / d for d in ("preflight", "main", "analysis"))
LAST_FROZEN_INDEX = 27                    # experiment folders 01-27 are never written to

# Models and serving: Experiment 27's pins and engine, unchanged.
MODELS = XC.MODELS
MODEL = XC.MODEL
FACES = XC.FACES
SEQ_LEN = 10
MAX_NEW_TOKENS = XC.MAX_NEW_TOKENS        # 128

# Design: Experiment 21's prompts with the investigator's windows (Experiment 21 used (1,5), (3,8), (5,10)).
WINDOWS = ((1, 5), (3, 7), (6, 10))
OVERLAPS = (((1, 5), (3, 7), (3, 4, 5)), ((3, 7), (6, 10), (6, 7)))
N_REPLICATES = 20                         # fresh-context greedy calls per condition per model (deterministic replicas)
PREFLIGHT_REPEATS = 3                     # G and F; every S and W condition once
ORDER_SEED = {"qwen": 20261031, "mistral": 20261032}   # random.Random(seed).shuffle(jobs); preflight uses seed + 100

# Archival regression targets (deterministic greedy on the same stack).
QWEN_G_REF, QWEN_F_REF = XC.QWEN_G_REF, XC.QWEN_F_REF
MISTRAL_G_REF = (4, 2, 6, 1, 3, 5, 2, 4, 6, 1)          # Experiment 27 Mistral preflight, same G prompt
MISTRAL_F_REF = (3, 1, 5, 2, 6, 4, 3, 1, 5, 2)          # Experiment 27 Mistral preflight, same F prompt
QWEN_CHAT_TEMPLATE_SHA256 = XC.QWEN_CHAT_TEMPLATE_SHA256
MISTRAL_TEKKEN_SHA256 = "6e2501687ccd0e1f30f36319eaf2b46958b897811e246cd8eb5d385b9e3de7d1"
SEPARATOR_ID = {"qwen": 220, "mistral": 1032}           # the single-space token between faces

# Gates
SCORER_TOL_LOGP = 1e-4                    # incremental rescoring of a model's own output vs its generation, nats
REPRO_TOL_P = 0.01                        # archival regression, six-face |dp|
MIN_FACE_MASS_G = 0.5                     # raw six-face mass at every G-prompt digit step (Exp 27 amendment v1.1 rule)
FLOOR_STOP_P = 0.25                       # numerical instability stop: incremental vs full pass beyond this
VARIANT_FACE_TOKENS_ALLOWED = 0           # vocabulary tokens other than the six bare digits whose text is a face

# Budget (vast.ai A100-SXM4-80GB; Experiment 27 billed GPU + disk + download)
GPU_CAP_USD = 15.0
GPU_WARN_USD = 10.0
