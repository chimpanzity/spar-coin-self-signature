"""Contract validation on synthetic histories only, then execution of the frozen programs on the archived inputs.

Contract (handoff section 3): the source parses, defines predict(history), imports at most math; on every synthetic history
(empty, the longest legal prefix of 19 rounds, constant and alternating histories, seeded random legal histories) it returns a
pair of finite numbers in [0, 1]; outputs are identical when the same histories are evaluated twice in one process and again,
in reverse order, in a second process (determinism, no persistent state).
"""
from __future__ import annotations

import random
from typing import Dict, List, Tuple

from blind_twin_forecast_prediction import config as C
from blind_twin_forecast_prediction import sandbox

MOVES = ("STAR", "TRIANGLE")


def _rows(moves: List[Tuple[str, str]]) -> List[dict]:
    return [{"round": i + 1, "p1": a, "p2": b, "result": "Matcher" if a == b else "Mismatcher"} for i, (a, b) in enumerate(moves)]


def synthetic_histories() -> List[List[dict]]:
    rng = random.Random(C.CONTRACT_SEED)
    hs = [[], _rows([("STAR", "STAR")] * 19), _rows([("TRIANGLE", "TRIANGLE")] * 19),
          _rows([(MOVES[i % 2], MOVES[(i + 1) % 2]) for i in range(19)]), _rows([("STAR", "TRIANGLE")])]
    for _ in range(C.N_CONTRACT_RANDOM):
        n = rng.randint(1, 19)
        hs.append(_rows([(rng.choice(MOVES), rng.choice(MOVES)) for _ in range(n)]))
    hs.append(_rows([(rng.choice(MOVES), rng.choice(MOVES)) for _ in range(19)]))     # another longest legal prefix
    return hs


def deterministic_run(source: str, histories: List[list]) -> dict:
    """Two passes in one process, then a reversed pass in a fresh process; all three must agree exactly."""
    n = len(histories)
    a = sandbox.run(source, histories + histories)
    if not a["ok"]:
        return dict(ok=False, error=a["error"])
    b = sandbox.run(source, list(reversed(histories)))
    if not b["ok"]:
        return dict(ok=False, error=b["error"])
    first, second, rev = a["outputs"][:n], a["outputs"][n:], list(reversed(b["outputs"]))
    if first != second or first != rev:
        bad = next(i for i in range(n) if not (first[i] == second[i] == rev[i]))
        return dict(ok=False, error=f"non-deterministic output on history {bad}: {first[bad]} / {second[bad]} / {rev[bad]}")
    return dict(ok=True, outputs=first, static=a["static"])


def validate(source: str) -> dict:
    hs = synthetic_histories()
    r = deterministic_run(source, hs)
    out = dict(ok=r["ok"], n_synthetic=len(hs), lengths=sorted({len(h) for h in hs}), error=r.get("error"))
    if r["ok"]:
        out.update(imports=r["static"]["imports"], empty_history_output=r["outputs"][0], longest_prefix_output=r["outputs"][1],
                   distinct_outputs=len({tuple(o) for o in r["outputs"]}))
    return out


def execute(source: str, inputs: Dict[Tuple[str, int], list]) -> dict:
    keys = sorted(inputs)
    r = deterministic_run(source, [inputs[k] for k in keys])
    if not r["ok"]:
        return dict(ok=False, error=r["error"])
    return dict(ok=True, table={k: tuple(o) for k, o in zip(keys, r["outputs"])})
