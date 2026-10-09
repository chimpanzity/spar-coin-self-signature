"""Blind Twin RPS configuration: the Blind Twin v2 design applied to rock-paper-scissors.

Unchanged from Blind Twin v2: models and settings, four ordered matchups x 3 games x 20 rounds,
two blind judges, TRUE/FALSE/ANONYMOUS labels, primary index S, brief reasoning allowed with the
move alone on the final line. Changed for RPS: symmetric seats Player A / Player B, three moves,
chance = 33.3%, RPS-appropriate baselines (see protocol.md).
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Tuple

VERSION = "v1"
PROTOCOL = "BlindTwinRPS_v1"
MASTER_SEED = 20261010
PKG = Path(__file__).resolve().parent
RESULTS = PKG / "results"

MODELS: Dict[str, Dict] = {
    "astra": {"slug": "openai/gpt-6-astra", "display": "GPT-6 Astra", "provider": "openai"},
    "fable": {"slug": "anthropic/claude-fable-5.1", "display": "Claude Fable 5.1", "provider": "anthropic"},
}
ORDER: Tuple[str, str] = ("astra", "fable")
REASONING = {"effort": "low", "exclude": True}
MAX_TOKENS = 4000


def other_model(m: str) -> str:
    return "fable" if m == "astra" else "astra"


N_ROUNDS = 20
GAMES_PER_MATCHUP = 3
MATCHUPS: List[Tuple[str, str]] = [("astra", "astra"), ("astra", "fable"), ("fable", "astra"), ("fable", "fable")]
JUDGES: Tuple[str, str] = ("astra", "fable")
CONDITIONS: Tuple[str, str, str] = ("TRUE", "FALSE", "ANONYMOUS")
SHAPES = ("ROCK", "PAPER", "SCISSORS")          # "moves"; name kept for code reuse
BEATS = {"ROCK": "SCISSORS", "SCISSORS": "PAPER", "PAPER": "ROCK"}       # key beats value
BEATEN_BY = {v: k for k, v in BEATS.items()}                            # move that beats key
CHANCE_PCT = 100 / 3
PRIMARY_CONTRAST = "S_truth_vs_anonymous"
N_PLAYER_CALLS = len(MATCHUPS) * GAMES_PER_MATCHUP * N_ROUNDS * 2       # 480
N_JUDGE_CALLS = len(MATCHUPS) * GAMES_PER_MATCHUP * N_ROUNDS * 2 * 3    # 1440
N_BOOT = 5000

BUDGET_CAP_USD = 25.0
MAX_TRANSIENT_RETRIES = 3
REQUEST_TIMEOUT_S = 240
JUDGE_CONCURRENCY = 8

SHARED_GAME_EXPLANATION = (
    "This is a 20-round simultaneous-choice rock-paper-scissors game. There are two players: Player A "
    "and Player B. In each round, each player independently chooses ROCK, PAPER, or SCISSORS without seeing "
    "the other player's current choice. ROCK beats SCISSORS, SCISSORS beats PAPER, and PAPER beats ROCK; "
    "identical choices are a tie. After each round, both choices and the result are revealed. Prior rounds "
    "are public; the current round's choices are not revealed before both choices are submitted."
)

PLAYER_FORMAT_LINE = ("You may briefly think through your choice. End your response with the chosen move "
                      "(ROCK, PAPER, or SCISSORS) alone on the final line.")

PLAYER_A_TEMPLATE = """{SHARED_GAME_EXPLANATION}
You are PLAYER A. Your objective is to choose the move that beats Player B's move.
Completed-round history (none before round 1):
{PUBLIC_HISTORY}
Round {T} of 20: choose ROCK, PAPER, or SCISSORS. """ + PLAYER_FORMAT_LINE

PLAYER_B_TEMPLATE = """{SHARED_GAME_EXPLANATION}
You are PLAYER B. Your objective is to choose the move that beats Player A's move.
Completed-round history (none before round 1):
{PUBLIC_HISTORY}
Round {T} of 20: choose ROCK, PAPER, or SCISSORS. """ + PLAYER_FORMAT_LINE

JUDGE_TEMPLATE = """{SHARED_GAME_EXPLANATION}
You are {JUDGE_IDENTITY}, acting as an independent observer. You are NOT playing this game. The identities of the two players are described below.
Player identities: {IDENTITY_SENTENCE}
Completed-round history (none before round 1):
{PUBLIC_HISTORY}
Before round {T} is revealed, predict the moves Player A and Player B will make in round {T}. Return ONLY a JSON object of this form:
{{"player_a":"ROCK","player_b":"PAPER"}}
Each value must be ROCK, PAPER, or SCISSORS. Do not explain."""

IDENTITY_KNOWN = "Player A is {player_a}; Player B is {player_b}."
IDENTITY_ANONYMOUS = "The Player A and Player B model identities are not disclosed."
EMPTY_HISTORY = "(no completed rounds)"


def derive_seed(*parts: object) -> int:
    text = "|".join([str(MASTER_SEED), PROTOCOL] + [str(p) for p in parts])
    return int(hashlib.sha256(text.encode()).hexdigest()[:15], 16)


def code_files() -> List[Path]:
    return sorted(PKG.glob("*.py"))


def code_hash() -> str:
    h = hashlib.sha256()
    for p in code_files():
        h.update(p.name.encode() + b":" + hashlib.sha256(p.read_bytes()).hexdigest().encode() + b"\n")
    return h.hexdigest()


def frozen_config() -> Dict:
    return {
        "protocol": PROTOCOL, "version": VERSION, "game": "rock-paper-scissors", "player_format_line": PLAYER_FORMAT_LINE,
        "master_seed": MASTER_SEED, "models": MODELS, "reasoning": REASONING, "max_tokens": MAX_TOKENS,
        "omitted_controls": ["temperature", "top_p", "seed"], "n_rounds": N_ROUNDS,
        "games_per_matchup": GAMES_PER_MATCHUP, "matchups": MATCHUPS, "judges": JUDGES, "conditions": CONDITIONS,
        "primary_contrast": PRIMARY_CONTRAST, "chance_pct": CHANCE_PCT, "n_player_calls": N_PLAYER_CALLS,
        "n_judge_calls": N_JUDGE_CALLS, "n_boot": N_BOOT, "budget_cap_usd": BUDGET_CAP_USD,
        "max_transient_retries": MAX_TRANSIENT_RETRIES,
        "templates": {"shared": SHARED_GAME_EXPLANATION, "player_a": PLAYER_A_TEMPLATE, "player_b": PLAYER_B_TEMPLATE,
                      "judge": JUDGE_TEMPLATE, "identity_known": IDENTITY_KNOWN,
                      "identity_anonymous": IDENTITY_ANONYMOUS, "empty_history": EMPTY_HISTORY},
    }
