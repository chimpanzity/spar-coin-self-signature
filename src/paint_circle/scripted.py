"""Scripted circle players for the SCRIPTED_OPPONENT_PILOT (2026-10-21).

A deterministic seat-B adapter: B's placement at round t depends only on the
precommitted sequence and t, never on A's current or past choices, and is
never shown to A before A commits. No API calls.
"""

from __future__ import annotations

import random
from typing import Optional

SEQUENCES = {
    "ALT_S":    "ST",     # STAR, TRIANGLE, STAR, ...
    "ALT_T":    "TS",     # TRIANGLE, STAR, ...
    "DOUBLE_S": "SSTT",   # STAR, STAR, TRIANGLE, TRIANGLE, ...
    "DOUBLE_T": "TTSS",
}


# Pre-generated IID strings (added 2026-10-21 for the IID identity-framing
# experiment): 100 independent fair STAR/TRIANGLE draws from a fixed seed.
IID_LENGTH = 100


def iid_string(seed: int, length: int = IID_LENGTH) -> str:
    rng = random.Random(seed)
    return "".join(rng.choice("TS") for _ in range(length))


def move(script: str, round_no: int) -> str:
    """B's placement on 1-based round `round_no`.

    Periodic scripts are named in SEQUENCES; IID scripts are named
    "IID_<seed>" and play iid_string(seed) once (no wrap-around).
    """
    if script.startswith("IID_"):
        s = iid_string(int(script.split("_", 1)[1]))
        if round_no > len(s):
            raise ValueError(f"{script} has only {len(s)} rounds")
        return s[round_no - 1]
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
