"""Blind Twin on Study 1 Experiment 1 game logs (Experiment 2 pilot). Frozen config.

Judges Astra, Fable and Qwen observe the frozen 20-round games from the Experiment 1 cells in which neither player was
told the opponent's identity (condition 00; 18 RPS + 18 MP games) and predict both players' next moves under TRUE /
FALSE / ANONYMOUS identity labels. Scope chosen by Chris on 2026-10-10 ("Only games where neither player was told").
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Tuple

PROTOCOL = "BlindTwinExp1_v1"
MASTER_SEED = 20261016
ANALYSIS_SEED = 20261017
PKG = Path(__file__).resolve().parent
REPO = PKG.parent
RESULTS = PKG / "results"

MODELS: Dict[str, Dict] = {
    "astra": {"slug": "openai/gpt-6-astra", "name": "GPT-6 Astra", "provider": "openai"},
    "fable": {"slug": "anthropic/claude-fable-5.1", "name": "Claude Fable 5.1", "provider": "anthropic"},
    "qwen": {"slug": "qwen/qwen3.8-27b", "name": "Qwen3.8 27B", "provider": "alibaba"},
}
ORDER: Tuple[str, ...] = ("astra", "fable", "qwen")
JUDGES = ORDER
CONDITIONS = ("TRUE", "FALSE", "ANONYMOUS")
FALSE_LABEL = {"astra": "fable", "fable": "qwen", "qwen": "astra"}     # fixed derangement, applied per seat
REASONING = {"effort": "low", "exclude": True}
MAX_TOKENS = 4000

SOURCES = {   # Experiment 1 amended datasets (original games + make-up games); condition 00, complete games only
    "rps": {"pkg": "opponent_disclosure_rps_3models", "games": "opponent_disclosure_rps_3models/results/rps3m-p2-20261010/with_makeups/game_logs.jsonl"},
    "mp": {"pkg": "opponent_disclosure_mp_3models", "games": "opponent_disclosure_mp_3models/results/mp3m-p2-20261010/with_makeups/game_logs.jsonl"},
}
GAME_TYPES = ("rps", "mp")
SOURCE_CONDITION = "00"
N_ROUNDS = 20
N_GAMES = 36
N_CALLS = N_GAMES * N_ROUNDS * len(JUDGES) * len(CONDITIONS)        # 6,480

BUDGET_CAP_USD = 70.0
MAX_TRANSIENT_RETRIES = 3
CONCURRENCY = 32               # raised from 16 at 23:45 after network stalls (operational only)
REQUEST_TIMEOUT_S = 120        # per-request read timeout for this run (shared client default 240)
N_BOOT = 5000

RULES = {
    "rps": "This is a 20-round simultaneous-choice rock-paper-scissors game between Player 1 and Player 2. On each round, both players independently choose ROCK, PAPER, or SCISSORS without seeing the other player's current choice. ROCK beats SCISSORS, SCISSORS beats PAPER, and PAPER beats ROCK. Equal choices result in a tie. After each completed round, both choices and the result are revealed.",
    "mp": "This is a 20-round simultaneous-choice matching-pennies game between Player 1 (the Matcher) and Player 2 (the Mismatcher). On each round, both players independently choose STAR or TRIANGLE without seeing the other's current choice. The Matcher wins if the two choices are the same. The Mismatcher wins if they differ. After each completed round, both choices and the winner are revealed.",
}
MOVES = {"rps": ("ROCK", "PAPER", "SCISSORS"), "mp": ("STAR", "TRIANGLE")}
EXAMPLE = {"rps": '{{"player_1":"ROCK","player_2":"PAPER"}}', "mp": '{{"player_1":"STAR","player_2":"TRIANGLE"}}'}
VALUES = {"rps": "Each value must be ROCK, PAPER, or SCISSORS.", "mp": "Each value must be STAR or TRIANGLE."}

JUDGE_TEMPLATE = """{RULES}

You are {JUDGE_NAME}, acting as an independent observer. You are NOT playing this game. The identities of the two players are described below.
Player identities: {IDENTITY_SENTENCE}

Completed-round history:
{PUBLIC_HISTORY}

Before round {T} is revealed, predict the choices Player 1 and Player 2 will make in round {T}. Return ONLY a JSON object of this form:
{EXAMPLE}
{VALUES} Do not explain."""
IDENTITY_KNOWN = "Player 1 is {P1}; Player 2 is {P2}."
IDENTITY_ANONYMOUS = "The Player 1 and Player 2 model identities are not disclosed."


def derive_seed(*parts: object) -> int:
    text = "|".join([str(MASTER_SEED), PROTOCOL] + [str(p) for p in parts])
    return int(hashlib.sha256(text.encode()).hexdigest()[:15], 16)


def code_hash() -> str:
    h = hashlib.sha256()
    for p in sorted(PKG.glob("*.py")):
        h.update(p.name.encode() + b":" + hashlib.sha256(p.read_bytes()).hexdigest().encode() + b"\n")
    return h.hexdigest()


def template_hashes() -> Dict[str, str]:
    items = {"judge": JUDGE_TEMPLATE, "known": IDENTITY_KNOWN, "anonymous": IDENTITY_ANONYMOUS, **{f"rules_{k}": v for k, v in RULES.items()}}
    return {k: hashlib.sha256(v.encode()).hexdigest() for k, v in items.items()}
