"""Answer key (handoff section 1): actual Astra and Fable choices in the condition-00 matching-pennies games.

Item = (game_id, round, seat) for every seat occupied by Astra or Fable; label = that seat's actual move in that round.
Predictor input = the seat and the preceding completed rounds, rounds[:t-1] projected to round, p1, p2, result. Qwen is an
opponent only: its moves stay in histories, its own choices are never targets.
"""
from __future__ import annotations

import json
from collections import Counter
from typing import Dict, List

from blind_coder_player_choices import config as C


def load_games(path=None) -> List[dict]:
    """The whole log, then complete condition-00 games; one per ordered pairing and replicate (make-up ids respected)."""
    rows = [json.loads(l) for l in open(path or C.GAME_LOG, encoding="utf-8") if l.strip()]
    gs = [g for g in rows if g["status"] == "complete" and str(g["condition"]) == C.CONDITION]
    key = Counter((g["p1_model"], g["p2_model"], g["replicate"]) for g in gs)
    if any(v != 1 for v in key.values()):
        raise ValueError(f"not one complete game per ordered pairing and replicate: {key}")
    for g in gs:
        if len(g["rounds"]) != C.N_ROUNDS or g["p1_informed"] or g["p2_informed"]:
            raise ValueError(f"{g['game_id']}: unexpected rounds or information flags")
    return sorted(gs, key=lambda g: g["game_id"])


def history(game: dict, t: int) -> List[dict]:
    rows = game["rounds"][: t - 1]
    assert len(rows) == t - 1
    return [{k: r[k] for k in C.HISTORY_KEYS} for r in rows]


def items(games=None) -> List[dict]:
    out = []
    for g in games or load_games():
        for seat in C.SEATS:
            target = g[f"{seat}_model"]
            if target not in C.TARGETS:
                continue
            opp = g["p2_model" if seat == "p1" else "p1_model"]
            for t in range(1, C.N_ROUNDS + 1):
                prev = g["rounds"][t - 2] if t > 1 else None
                out.append(dict(game_id=g["game_id"], round=t, seat=seat, target=target, opponent=opp, replicate=g["replicate"],
                                y=g["rounds"][t - 1][seat], prev_own=prev[seat] if prev else None,
                                prev_won=(prev["result"] == C.ROLE[seat]) if prev else None, history=history(g, t)))
    return out


def acceptance(games, its) -> dict:
    by_t = Counter(i["target"] for i in its)
    seat = Counter((i["target"], i["seat"]) for i in its)
    after = Counter(i["target"] for i in its if i["round"] > 1)
    contributing = {i["game_id"] for i in its}
    pairings = Counter((g["p1_model"], g["p2_model"]) for g in games)
    sw = switch_counts(its)
    checks = dict(games=len(games) == C.EXPECTED["games"], pairings=len(pairings) == 9 and set(pairings.values()) == {2},
                  contributing=len(contributing) == C.EXPECTED["contributing_games"], decisions=len(its) == C.EXPECTED["decisions"],
                  per_target=all(by_t[j] == C.EXPECTED["per_target"] for j in C.TARGETS),
                  per_seat=all(seat[(j, s)] == C.EXPECTED["per_target_seat"] for j in C.TARGETS for s in C.SEATS),
                  after_opening=all(after[j] == C.EXPECTED["after_opening"] for j in C.TARGETS),
                  switch_counts=sw == {f"{j}_{k}": list(v) for (j, k), v in C.EXPECTED_SWITCH.items()})
    return dict(ok=all(checks.values()), checks=checks, n_games=len(games), contributing_games=sorted(contributing),
                decisions={j: by_t[j] for j in C.TARGETS}, switch_counts=sw)


def switch_counts(its) -> Dict[str, list]:
    out = {}
    for j in C.TARGETS:
        for k, won in (("win", True), ("loss", False)):
            sub = [i for i in its if i["target"] == j and i["round"] > 1 and i["prev_won"] is won]
            out[f"{j}_{k}"] = [sum(i["y"] != i["prev_own"] for i in sub), len(sub)]
    return out
