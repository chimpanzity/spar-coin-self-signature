"""Blind Twin pilot configuration: frozen prompts, models, design, budget."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple

PROTOCOL = "BlindTwin_v1"
MASTER_SEED = 20261009
PKG = Path(__file__).resolve().parent
RESULTS = PKG / "results"

# ---------------------------------------------------------------------------
# Models (verified 2026-10-09: no temperature support on either endpoint; seed
# listed for Astra only and omitted for both; reasoning supported)
# ---------------------------------------------------------------------------
MODELS: Dict[str, Dict] = {
    "astra": {"slug": "openai/gpt-6-astra", "display": "GPT-6 Astra", "provider": "openai"},
    "fable": {"slug": "anthropic/claude-fable-5.1", "display": "Claude Fable 5.1", "provider": "anthropic"},
}
ORDER: Tuple[str, str] = ("astra", "fable")
REASONING = {"effort": "low", "exclude": True}   # same setting as the SPAR FCE / Phase 2 runs
MAX_TOKENS = 4000                                # includes hidden reasoning tokens


def other_model(m: str) -> str:
    return "fable" if m == "astra" else "astra"


# ---------------------------------------------------------------------------
# Design
# ---------------------------------------------------------------------------
N_ROUNDS = 20
GAMES_PER_MATCHUP = 3
MATCHUPS: List[Tuple[str, str]] = [("astra", "astra"), ("astra", "fable"), ("fable", "astra"), ("fable", "fable")]
JUDGES: Tuple[str, str] = ("astra", "fable")
CONDITIONS: Tuple[str, str, str] = ("TRUE", "FALSE", "ANONYMOUS")
SHAPES = ("STAR", "TRIANGLE")
PRIMARY_CONTRAST = "S_truth_vs_anonymous"
N_PLAYER_CALLS = len(MATCHUPS) * GAMES_PER_MATCHUP * N_ROUNDS * 2       # 480
N_JUDGE_CALLS = len(MATCHUPS) * GAMES_PER_MATCHUP * N_ROUNDS * 2 * 3    # 1440
N_BOOT = 5000

# ---------------------------------------------------------------------------
# Budget / operations
# ---------------------------------------------------------------------------
BUDGET_CAP_USD = 25.0            # see approvals.jsonl for provenance
MAX_TRANSIENT_RETRIES = 3
REQUEST_TIMEOUT_S = 240
JUDGE_CONCURRENCY = 8

# ---------------------------------------------------------------------------
# Prompts (verbatim from the handoff)
# ---------------------------------------------------------------------------
SHARED_GAME_EXPLANATION = (
    "This is a 20-round simultaneous-choice matching-pennies game. There are two players: the Matcher "
    "and the Mismatcher. In each round, each player independently chooses STAR or TRIANGLE without seeing "
    "the other player's current choice. The Matcher wins the round if the two choices are the same. The "
    "Mismatcher wins if they are different. After each round, both choices and the winner are revealed. "
    "Prior rounds are public; the current round's choices are not revealed before both choices are submitted."
)

MATCHER_TEMPLATE = """{SHARED_GAME_EXPLANATION}
You are the MATCHER. Your objective is to choose the SAME shape as the Mismatcher.
Completed-round history (none before round 1):
{PUBLIC_HISTORY}
Round {T} of 20: choose STAR or TRIANGLE. Return ONLY the chosen shape."""

MISMATCHER_TEMPLATE = """{SHARED_GAME_EXPLANATION}
You are the MISMATCHER. Your objective is to choose a DIFFERENT shape from the Matcher.
Completed-round history (none before round 1):
{PUBLIC_HISTORY}
Round {T} of 20: choose STAR or TRIANGLE. Return ONLY the chosen shape."""

JUDGE_TEMPLATE = """{SHARED_GAME_EXPLANATION}
You are {JUDGE_IDENTITY}, acting as an independent observer. You are NOT playing this game. The identities and roles of the two players are described below.
Player identities: {IDENTITY_SENTENCE}
Completed-round history (none before round 1):
{PUBLIC_HISTORY}
Before round {T} is revealed, predict the choices the Matcher and Mismatcher will make in round {T}. Return ONLY a JSON object of this form:
{{"matcher":"STAR","mismatcher":"TRIANGLE"}}
Each value must be STAR or TRIANGLE. Do not explain."""

IDENTITY_KNOWN = "Matcher is {matcher}; Mismatcher is {mismatcher}."
IDENTITY_ANONYMOUS = "The Matcher and Mismatcher model identities are not disclosed."
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
        "protocol": PROTOCOL, "master_seed": MASTER_SEED, "models": MODELS, "reasoning": REASONING,
        "max_tokens": MAX_TOKENS, "omitted_controls": ["temperature", "top_p", "seed"],
        "n_rounds": N_ROUNDS, "games_per_matchup": GAMES_PER_MATCHUP, "matchups": MATCHUPS,
        "judges": JUDGES, "conditions": CONDITIONS, "primary_contrast": PRIMARY_CONTRAST,
        "n_player_calls": N_PLAYER_CALLS, "n_judge_calls": N_JUDGE_CALLS, "n_boot": N_BOOT,
        "budget_cap_usd": BUDGET_CAP_USD, "max_transient_retries": MAX_TRANSIENT_RETRIES,
        "templates": {"shared": SHARED_GAME_EXPLANATION, "matcher": MATCHER_TEMPLATE,
                      "mismatcher": MISMATCHER_TEMPLATE, "judge": JUDGE_TEMPLATE,
                      "identity_known": IDENTITY_KNOWN, "identity_anonymous": IDENTITY_ANONYMOUS,
                      "empty_history": EMPTY_HISTORY},
    }
