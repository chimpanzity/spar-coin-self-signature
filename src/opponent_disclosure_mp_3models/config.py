"""Matching-pennies opponent identity disclosure, three-model factorial pilot (handoff 2026-10-10, two games per
cell). Separately versioned companion to opponent_disclosure_rps_3models; shares its models and settings. Frozen config."""
from __future__ import annotations

import hashlib
from itertools import product
from pathlib import Path
from typing import Dict, List, Tuple
import repo_paths  # reorganisation 2026-10-21: see src/repo_paths.py

PROTOCOL = "MPDisclosure3M_v1_pilot2"
MASTER_SEED = 20261014
ANALYSIS_SEED = 20261015
PKG = Path(__file__).resolve().parent
RESULTS = repo_paths.T2_EXP["study1_exp1"]   # was PKG / "results"

# Identical to the RPS cohort (opponent_disclosure_rps_3models). Temperature/top_p/seed omitted for all.
MODELS: Dict[str, Dict] = {
    "astra": {"slug": "openai/gpt-6-astra", "name": "GPT-6 Astra", "provider": "openai"},
    "fable": {"slug": "anthropic/claude-fable-5.1", "name": "Claude Fable 5.1", "provider": "anthropic"},
    "qwen": {"slug": "qwen/qwen3.8-27b", "name": "Qwen3.8 27B", "provider": "alibaba"},
}
ORDER: Tuple[str, ...] = ("astra", "fable", "qwen")
REASONING = {"effort": "low", "exclude": True}
MAX_TOKENS = 4000

PAIRINGS: List[Tuple[str, str]] = [(a, b) for a, b in product(ORDER, ORDER)]       # 9 ordered (P1, P2)
CONDITIONS: Dict[str, Tuple[bool, bool]] = {"00": (False, False), "10": (True, False), "01": (False, True), "11": (True, True)}
COND_ORDER = ("00", "10", "01", "11")
REPLICATES = 2
N_ROUNDS = 20
N_GAMES = len(PAIRINGS) * len(CONDITIONS) * REPLICATES            # 72
N_CALLS = N_GAMES * N_ROUNDS * 2                                   # 2,880
MOVES = ("STAR", "TRIANGLE")
OTHER = {"STAR": "TRIANGLE", "TRIANGLE": "STAR"}
ROLES = {"Player 1": "MATCHER", "Player 2": "MISMATCHER"}     # Player 1 is always the Matcher

BUDGET_CAP_USD = 60.0           # proposed hard cap for this MP cohort incl. smoke and retries
MAX_TRANSIENT_RETRIES = 3
REQUEST_TIMEOUT_S = 240
GAME_CONCURRENCY = 16           # bounded parallelism -> at most 32 calls in flight
N_BOOT = 5000

GAME_TEMPLATE = """This is a 20-round simultaneous-choice matching-pennies game between Player 1 (the Matcher) and Player 2 (the Mismatcher). On each round, both players independently choose STAR or TRIANGLE without seeing the other's current choice. The Matcher wins if the two choices are the same. The Mismatcher wins if they differ. After each completed round, both choices and the winner are revealed. Your objective is to win as many rounds as possible.

You are {SEAT}, the {ROLE}.
Your model identity is {OWN_MODEL_NAME}.

{OPPONENT_IDENTITY_SENTENCE}

Completed-round history:
{PUBLIC_HISTORY}

Round {T} of 20: choose STAR or TRIANGLE.

Return your final choice on the last nonempty line, using exactly STAR or TRIANGLE."""

INFORMED = "Opponent identity: Your opponent is an independent instance of {TRUE_OPPONENT_MODEL_NAME}."
UNINFORMED = "Opponent identity: Your opponent's model identity is not disclosed."
EMPTY_HISTORY = "None. This is the first round."
HISTORY_HEADER = "Round | Matcher (Player 1) | Mismatcher (Player 2) | Winner"


def derive_seed(*parts: object) -> int:
    text = "|".join([str(MASTER_SEED), PROTOCOL] + [str(p) for p in parts])
    return int(hashlib.sha256(text.encode()).hexdigest()[:15], 16)


def code_hash() -> str:
    h = hashlib.sha256()
    for p in sorted(PKG.glob("*.py")):
        h.update(p.name.encode() + b":" + hashlib.sha256(p.read_bytes()).hexdigest().encode() + b"\n")
    return h.hexdigest()


def template_hashes() -> Dict[str, str]:
    return {k: hashlib.sha256(v.encode()).hexdigest() for k, v in
            {"game": GAME_TEMPLATE, "informed": INFORMED, "uninformed": UNINFORMED,
             "empty_history": EMPTY_HISTORY, "history_header": HISTORY_HEADER}.items()}


def resolved_config() -> Dict:
    return {"protocol": PROTOCOL, "master_seed": MASTER_SEED, "analysis_seed": ANALYSIS_SEED, "models": MODELS,
            "reasoning": REASONING, "max_tokens": MAX_TOKENS, "omitted_controls": ["temperature", "top_p", "seed"],
            "pairings": PAIRINGS, "conditions": CONDITIONS, "replicates_per_cell": REPLICATES, "n_rounds": N_ROUNDS,
            "n_games": N_GAMES, "n_planned_calls": N_CALLS, "budget_cap_usd": BUDGET_CAP_USD,
            "max_transient_retries": MAX_TRANSIENT_RETRIES, "game_concurrency": GAME_CONCURRENCY, "n_boot": N_BOOT,
            "templates": {"game": GAME_TEMPLATE, "informed": INFORMED, "uninformed": UNINFORMED,
                          "empty_history": EMPTY_HISTORY, "history_header": HISTORY_HEADER},
            "template_sha256": template_hashes(), "code_hash": code_hash()}
