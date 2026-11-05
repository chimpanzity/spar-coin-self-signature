"""Blind Twin forecast prediction (track 2): can a model write code that predicts its own observer forecasts better than code
written by the other model? Zero-example, crossed code-author x forecast-target pilot. Frozen config.

Handoff: SPAR_Blind_Twin_Forecast_Prediction_Handoff.md (2026-11-04). Four fresh author calls (Astra and Fable, each writing
one predictor per target judge); programs frozen and run offline on archived Blind Twin forecasts (run btss-20261011 and its
identical-prompt retest). No new games, player calls or judge forecasts.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import repo_paths
from blind_twin_selfself import config as BT

PROTOCOL = "BlindTwinForecastPrediction_v1"
PKG = Path(__file__).resolve().parent
REPO = repo_paths.REPO
RD = repo_paths.T2_EXP["forecast_prediction"]
ARCHIVE = repo_paths.T2 / "07_2026-10-11_selfself_judges_and_retest"
ORIGINAL_CSV = ARCHIVE / "btss-20261011" / "predictions.csv"
RETEST_CSV = ARCHIVE / "btss-retest-20261011" / "predictions.csv"
ORIGINAL_SNAPSHOT = ARCHIVE / "btss-20261011" / "endpoint_and_price_snapshots.json"

AUTHORS = ("astra", "fable")
TARGETS = ("astra", "fable")
MODELS = {k: BT.MODELS[k] for k in AUTHORS}            # slugs, display names and pinned providers of the archive
REASONING = dict(BT.REASONING)                         # {"effort": "low", "exclude": True}, as the archived judge calls
MAX_TOKENS = BT.MAX_TOKENS                             # 4000, both authors
CELLS = tuple((a, j) for a in AUTHORS for j in TARGETS)
PROGRAM = {(a, j): f"{a}_for_{j}.py" for a, j in CELLS}

# Evaluation set (handoff section 1)
GAME_TYPE, GAME_CONDITION, LABEL = "mp", "00", "ANONYMOUS"
GAMES = ("mp:AA_00_1", "mp:AA_00_2", "mp:FF_00_1", "mp:FF_00_2", "mp:QQ_00_1_MU2", "mp:QQ_00_2")
RETESTED = ("mp:AA_00_1", "mp:FF_00_1", "mp:QQ_00_1_MU2")
PAIRING = {"AA": "Astra-Astra", "FF": "Fable-Fable", "QQ": "Qwen-Qwen"}
SEATS = ("p1", "p2")
N_ROUNDS = BT.N_ROUNDS
EXPECTED = dict(items=240, items_per_judge=240, retest_items=120, stable_disagreements=42,
                stable_by_pairing={"AA": 11, "FF": 14, "QQ": 17})
HISTORY_KEYS = ("round", "p1", "p2", "result")

# Budget (handoff section 3)
CAP_USD = 5.0
MAX_TRANSIENT_RETRIES = 3

# Sandbox (handoff section 3)
SANDBOX_TIMEOUT_S = 60                 # whole worker process, all calls of one program
SANDBOX_CALL_LIMIT_S = 2.0             # any single predict() call
SANDBOX_MEMORY_MB = 512                # Windows Job Object process-memory limit
CONTRACT_SEED = 20261104               # synthetic histories for the contract check
N_CONTRACT_RANDOM = 40

# Reference predictors and modal-call threshold
REPEAT_P = 0.75


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_sha(path) -> str:
    """SHA-256 with CRLF normalised to LF (the committed git blob on this Windows checkout)."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
