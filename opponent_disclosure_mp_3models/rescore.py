"""Independent rescore from rounds.csv: recomputes MP outcomes from the raw shapes with its own payoff rule
(does not import game.result / payoff_p1), then V and D with separately written formulas. P1 = Matcher."""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

MODELS = ("astra", "fable", "qwen")


def _matcher_payoff(a, b):
    return 1.0 if a == b else 0.0


def rescore(rd: Path):
    games = defaultdict(list)
    meta = {}
    mismatched_results = 0
    with open(rd / "rounds.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["complete_game"] != "True":
                continue
            pay = _matcher_payoff(r["p1"], r["p2"])
            expected = {"Matcher": 1.0, "Mismatcher": 0.0}[r["result"]]
            mismatched_results += pay != expected
            games[r["game_id"]].append(pay)
            meta[r["game_id"]] = (r["p1_model"], r["p2_model"], r["condition"])
    cell = defaultdict(list)
    for gid, pays in games.items():
        cell[meta[gid]].append(sum(pays) / len(pays))
    V = {k: sum(v) / len(v) for k, v in cell.items()}
    try:
        Ds = []
        for i in MODELS:
            j, k = [m for m in MODELS if m != i]
            u1 = lambda a, b: V[(a, b, "10")] - V[(a, b, "00")]
            u2 = lambda a, b: V[(a, b, "00")] - V[(a, b, "01")]
            S = (u1(i, i) + u2(i, i)) / 2
            O = (u1(i, j) + u2(j, i) + u1(i, k) + u2(k, i)) / 4
            Ds.append(S - O)
        D = sum(Ds) / 3
    except KeyError:
        D = None
    return {"D_rescore": D, "n_complete_games": len(games), "round_result_mismatches": int(mismatched_results)}
