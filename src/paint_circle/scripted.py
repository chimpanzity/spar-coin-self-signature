"""Scripted circle players for the SCRIPTED_OPPONENT_PILOT (2026-10-21).

A deterministic seat-B adapter: B's placement at round t depends only on the
precommitted sequence and t, never on A's current or past choices, and is
never shown to A before A commits. No API calls.
"""

from __future__ import annotations

from typing import Optional

SEQUENCES = {
    "ALT_S":    "ST",     # STAR, TRIANGLE, STAR, ...
    "ALT_T":    "TS",     # TRIANGLE, STAR, ...
    "DOUBLE_S": "SSTT",   # STAR, STAR, TRIANGLE, TRIANGLE, ...
    "DOUBLE_T": "TTSS",
}


def move(script: str, round_no: int) -> str:
    """B's placement on 1-based round `round_no`."""
    cycle = SEQUENCES[script]
    return cycle[(round_no - 1) % len(cycle)]


def oracle_prediction(prior: str) -> Optional[str]:
    """Ideal periodic oracle: infer period 2 or 4 and phase from the last 4 B moves.

    Returns the predicted next B move, or None when the last 4 moves fit
    neither pattern (or fewer than 4 moves exist).
    """
    if len(prior) < 4:
        return None
    a, b, c, d = prior[-4:]
    if a != b and b != c and c != d:                 # alternating
        return "T" if d == "S" else "S"
    if a == b and c == d and b != c:                  # xxyy -> next starts a new pair: x
        return a
    if b == c and a != b and c != d:                  # xyyx -> next is x (pair completes)
        return d
    return None
