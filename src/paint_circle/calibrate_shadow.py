"""Calibrate the windowed shadow Proteus on synthetic players (handoff §9).

Each synthetic focal player plays 200 rounds as matcher against an IID 50/50
opponent; the shadow forecasts the focal player's choices. Reported for
W in {25, 50, full}: activation, expected accuracy (p_shadow), PI, log loss
vs a marginal-only baseline. No API calls.

Usage: python -m paint_circle.calibrate_shadow [n_sessions]
"""

from __future__ import annotations

import json
import os
import random
import statistics as st
import sys

from paint_circle import shadow
import repo_paths  # reorganisation 2026-10-21: see src/repo_paths.py

ROUNDS = 200
WINDOWS = {"W25": 25, "W50": 50, "full": None}
SEED = 20261021


def _flip(c):
    return "S" if c == "T" else "T"


def policy(name, rng, own, opp, wins):
    if not own:
        return rng.choice("TS")
    last, won = own[-1], wins[-1] == "1"
    if name == "iid50":
        return rng.choice("TS")
    if name == "bias60":
        return "T" if rng.random() < 0.60 else "S"
    if name == "bias70":
        return "T" if rng.random() < 0.70 else "S"
    if name.startswith("alt"):
        p = int(name[3:]) / 100
        return _flip(last) if rng.random() < p else last
    if name == "wsls80":
        stay = rng.random() < 0.8
        return (last if stay else _flip(last)) if won else (_flip(last) if stay else last)
    if name == "copyopp80":
        return opp[-1] if rng.random() < 0.8 else _flip(opp[-1])
    raise ValueError(name)


POLICIES = ["iid50", "bias60", "bias70", "alt65", "alt80", "alt100", "wsls80", "copyopp80"]


def simulate(name, rng):
    own, opp, wins = "", "", ""
    for _ in range(ROUNDS):
        a = policy(name, rng, own, opp, wins)
        b = rng.choice("TS")
        own, opp, wins = own + a, opp + b, wins + ("1" if a == b else "0")
    return own, wins


def main(n_sessions: int = 200):
    rng = random.Random(SEED)
    out = {}
    for name in POLICIES:
        sessions = [simulate(name, rng) for _ in range(n_sessions)]
        out[name] = {}
        for wlabel, w in WINDOWS.items():
            res = [shadow.predictability(c, wn, w) for c, wn in sessions]
            out[name][wlabel] = dict(
                p_shadow=round(st.mean(r.p_shadow for r in res), 4),
                p_shadow_sd=round(st.stdev(r.p_shadow for r in res), 4),
                pi=round(st.mean(r.pi for r in res), 4),
                activation=round(st.mean(r.activation for r in res), 4),
                logloss_gain_bits=round(st.mean(r.logloss_marginal - r.logloss for r in res), 4),
            )
        print(name, json.dumps(out[name]), flush=True)
    path = repo_paths.legacy("paint_circle/results/shadow_calibration.json")
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict(rounds=ROUNDS, n_sessions=n_sessions, seed=SEED, results=out), f, indent=2)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
