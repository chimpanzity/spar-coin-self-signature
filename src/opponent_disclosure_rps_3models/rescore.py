"""Independent rescore from rounds.csv: recomputes RPS outcomes from the raw moves with its own payoff
table (does not import game.result / payoff_p1), then V and D with separately written formulas."""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

WIN = {("ROCK", "SCISSORS"), ("SCISSORS", "PAPER"), ("PAPER", "ROCK")}
MODELS = ("astra", "fable", "qwen")


def _p1(a, b):
    return 0.5 if a == b else (1.0 if (a, b) in WIN else 0.0)


def rescore(rd: Path):
    games = defaultdict(list)
    meta = {}
    mismatched_results = 0
    with open(rd / "rounds.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["complete_game"] != "True":
                continue
            pay = _p1(r["p1"], r["p2"])
            expected = {"Player 1": 1.0, "Player 2": 0.0, "Tie": 0.5}[r["result"]]
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
