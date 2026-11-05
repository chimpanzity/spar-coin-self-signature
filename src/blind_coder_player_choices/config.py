"""First-level Blind Coder (track 2, folder 22): can Astra and Fable each write a program that predicts its own actual
matching-pennies choices better than a program written by the other model? Frozen config.

Handoff: SPAR_First_Level_Blind_Coder_Player_Choices_Handoff.md (2026-11-04). 40 fresh author calls (2 authors x 2 named
targets x 10 blocks); programs frozen and scored offline against the archived player choices of Study 1 / Experiment 1
condition 00. No observer, no new games. Reuses folder 21's sandbox, parser and approval gate (imported, not modified).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import repo_paths
from blind_twin_forecast_prediction import config as C21

PROTOCOL = "FirstLevelBlindCoder_v1"
PKG = Path(__file__).resolve().parent
REPO = repo_paths.REPO
RD = repo_paths.T2_EXP["blind_coder"]
GAME_LOG = repo_paths.T2 / "05_2026-10-10_study1_exp1_disclosure" / "mp3m-p2-20261010" / "with_makeups" / "game_logs.jsonl"

AUTHORS = ("astra", "fable")
TARGETS = ("astra", "fable")
OPPONENTS = ("astra", "fable", "qwen")
MODELS = C21.MODELS                                   # archived slugs, display names, pinned providers
REASONING = dict(C21.REASONING)                       # {"effort": "low", "exclude": True}
MAX_TOKENS = 4000
CELLS = tuple((a, j) for a in AUTHORS for j in TARGETS)
N_BLOCKS = 10
SCHEDULE_SEED = 20261105
MIN_COMPLETE_BLOCKS = 8                               # fewer: the planned comparison is labelled incomplete

# Archive selection (handoff section 1)
CONDITION = "00"
N_ROUNDS = 20
SEATS = ("p1", "p2")
ROLE = {"p1": "Matcher", "p2": "Mismatcher"}
HISTORY_KEYS = ("round", "p1", "p2", "result")
EXPECTED = dict(games=18, contributing_games=16, decisions=480, per_target=240, per_target_seat=120, after_opening=228)
# Handoff section 4C reference counts (kept out of every prompt): switches / opportunities
EXPECTED_SWITCH = {("astra", "win"): (71, 109), ("astra", "loss"): (49, 119), ("fable", "win"): (68, 118), ("fable", "loss"): (59, 110)}

CAP_USD = 10.0
MAX_TRANSIENT_RETRIES = 3
SANDBOX_TIMEOUT_S = 120
SANDBOX_CALL_LIMIT_S = 2.0
SANDBOX_MEMORY_MB = 512
CONTRACT_SEED = 20261106
N_CONTRACT_RANDOM = 40
HISTORY_RULE_P = 0.75


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


canonical_sha = C21.canonical_sha
