"""Blind Twin self-self 00-vs-11 pilot (Experiment 2 extension). Frozen config.

Judges Astra, Fable and Qwen observe the Experiment 1 self-self games (Astra-Astra, Fable-Fable, Qwen-Qwen) from
condition 00 (neither player told) and condition 11 (both told), in RPS and MP: 2 games per cell, 24 games. Each judge
prompt states what the players were told, in model-name-free wording, so ANONYMOUS and FALSE labels stay intact. All
24 games are judged under this one prompt, including the 12 condition-00 games already judged under BlindTwinExp1_v1.
Authorised by Chris on 2026-10-11 ("run it").
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Tuple
import repo_paths  # reorganisation 2026-10-21: see src/repo_paths.py

PROTOCOL = "BlindTwinSelfSelf_v1"
MASTER_SEED = 20261018
ANALYSIS_SEED = 20261019
PKG = Path(__file__).resolve().parent
REPO = repo_paths.REPO   # was PKG.parent
RESULTS = repo_paths.T2_EXP["selfself"]   # was PKG / "results"

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
    "rps": {"pkg": "opponent_disclosure_rps_3models", "games": str(repo_paths.legacy("opponent_disclosure_rps_3models/results/rps3m-p2-20261010/with_makeups/game_logs.jsonl"))},
    "mp": {"pkg": "opponent_disclosure_mp_3models", "games": str(repo_paths.legacy("opponent_disclosure_mp_3models/results/mp3m-p2-20261010/with_makeups/game_logs.jsonl"))},
}
GAME_TYPES = ("rps", "mp")
SOURCE_CONDITIONS = ("00", "11")
N_ROUNDS = 20
N_GAMES = 24                                                        # 2 types x 3 self pairings x 2 conditions x 2
N_CALLS = N_GAMES * N_ROUNDS * len(JUDGES) * len(CONDITIONS)        # 4,320

BUDGET_CAP_USD = 40.0
MAX_TRANSIENT_RETRIES = 3
CONCURRENCY = 32
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
Player information: {INFO_SENTENCE}

Completed-round history:
{PUBLIC_HISTORY}

Before round {T} is revealed, predict the choices Player 1 and Player 2 will make in round {T}. Return ONLY a JSON object of this form:
{EXAMPLE}
{VALUES} Do not explain."""
IDENTITY_KNOWN = "Player 1 is {P1}; Player 2 is {P2}."
IDENTITY_ANONYMOUS = "The Player 1 and Player 2 model identities are not disclosed."
INFO = {"00": "Neither player was told its opponent's model identity.",
        "11": "Before the game, each player was told the true model identity of its opponent."}   # name-free by design


def derive_seed(*parts: object) -> int:
    text = "|".join([str(MASTER_SEED), PROTOCOL] + [str(p) for p in parts])
    return int(hashlib.sha256(text.encode()).hexdigest()[:15], 16)


def code_hash() -> str:
    h = hashlib.sha256()
    for p in sorted(PKG.glob("*.py")):
        h.update(p.name.encode() + b":" + hashlib.sha256(p.read_bytes()).hexdigest().encode() + b"\n")
    return h.hexdigest()


def template_hashes() -> Dict[str, str]:
    items = {"judge": JUDGE_TEMPLATE, "known": IDENTITY_KNOWN, "anonymous": IDENTITY_ANONYMOUS, "info_00": INFO["00"], "info_11": INFO["11"], **{f"rules_{k}": v for k, v in RULES.items()}}
    return {k: hashlib.sha256(v.encode()).hexdigest() for k, v in items.items()}
