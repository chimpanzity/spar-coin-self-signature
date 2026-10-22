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


# Noisy double-alternation (added 2026-10-22 for the entropy-gradient pilot):
# the latent pattern SSTT (or TTSS) with each round's prescribed symbol flipped
# independently with probability epsilon. The whole sequence is fixed in
# advance from random.Random(seed); it never depends on A's choices.
# Script name: NDA_<phase S|T>_e<epsilon x 100, 2 digits>_<seed>.
NDA_LENGTH = 100


def nda_latent(phase: str, length: int = NDA_LENGTH) -> str:
    base = "SSTT" if phase == "S" else "TTSS"
    return "".join(base[i % 4] for i in range(length))


def nda_sequence(phase: str, epsilon: float, seed: int, length: int = NDA_LENGTH) -> str:
    rng = random.Random(seed)
    latent = nda_latent(phase, length)
    flip = {"S": "T", "T": "S"}
    return "".join(flip[c] if rng.random() < epsilon else c for c in latent)


def nda_parse(script: str):
    _, phase, e, seed = script.split("_")
    return phase, int(e[1:]) / 100, int(seed)


def move(script: str, round_no: int) -> str:
    """B's placement on 1-based round `round_no`.

    Periodic scripts are named in SEQUENCES; IID scripts are named
    "IID_<seed>" and play iid_string(seed) once (no wrap-around).
    """
    if script.startswith("NDA_"):
        s = nda_sequence(*nda_parse(script))
        if round_no > len(s):
            raise ValueError(f"{script} has only {len(s)} rounds")
        return s[round_no - 1]
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
