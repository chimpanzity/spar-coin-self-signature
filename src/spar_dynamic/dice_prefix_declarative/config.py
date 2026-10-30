"""Frozen constants for SPAR_DICE_PREFIX_DECLARATIVE_v1.0 (handoff dated 2026-10-30)."""

from __future__ import annotations

from repo_paths import T1, T1_EXP

TAG = "SPAR_DICE_PREFIX_DECLARATIVE_v1.0"
DESIGN_SOURCE = "GPT_SPAR_Qwen_Dice_Partial_History_Declarative_Knowledge_Logprob_Handoff_v1.0.md (2026-10-30)"

EXP = T1_EXP["dice_prefix_declarative"]
EXP21 = T1_EXP["dice_logprob"] / "main-qwen3-32b-a100"
EXP22 = T1_EXP["dice_recognition"]
PRE, MAIN, ANALYSIS, REPORTS = EXP / "preflight", EXP / "main", EXP / "analysis", EXP / "reports"
LAST_FROZEN_INDEX = 25                    # experiment folders 01-25 are never written to

MODEL_ID = "Qwen/Qwen3-32B"
REVISION = "9216db5781bf21249d130ec9da846c4624c16137"          # Experiment 21's commit
CHAT_TEMPLATE_SHA256 = "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8"   # Experiment 21 env_main.json
G_PROMPT_SHA256 = "edc7a4a228d493e83a5086181c170aa052e3e7cb8b34b9911ef4dc8147fdb8fe"
F_PROMPT_SHA256 = "8adcaddfff0d9acee6bcc9060917175e7d68167f440c42b00a3800cd32dcef03"
G_RENDERED_SHA256 = "5c5bb4193ac7634b82765c91ef75399166b97edadea66924d56396d4355cc185"

# Experiment 21's greedy references (10/10 identical in its main run)
G_REF = (5, 2, 6, 3, 1, 4, 6, 2, 5, 3)
F_REF = (3, 1, 4, 6, 2, 5, 3, 2, 6, 4)

KS = (0, 3, 6)
WINDOW = 3
ARMS = ("H", "N", "S", "O")
REPEATS = 3
PREFLIGHT_REF_REPEATS = 3
PREFLIGHT_ARMS_K = 3                      # representative H/N/S/O prompts run in preflight
ORDER_SEED = 20261040
FACES = (1, 2, 3, 4, 5, 6)

# Reproduction tolerance (predeclared): G and F greedy sequences identical on every repeat, and the six-face normalised
# distribution at every G and F generation step and every archived matched-prefix position within this of the archive.
REPRO_TOL_P = 0.01
SCORER_TOL_LOGP = 1e-4                    # teacher-forced incremental scoring vs generation on the same context
ARCHIVED_FLOOR_P = 0.09                   # Experiment 21 full-pass vs incremental floor
MIN_FACE_MASS = 0.5                       # minimum full-vocabulary mass on the six faces at a scored digit step

GPU_CAP_USD = 10.0
EST_MINUTES = 25
EST_RATE_USD_H = 1.6

# The O sentence must be true: a real response to the exact G instruction by a different model whose first six
# values use each face once. Experiment 22's corpus has 49/50 such Mistral Small 3.2 24B sequences (temperature 0.7).
O_EVIDENCE_SOURCE = "mistral"
