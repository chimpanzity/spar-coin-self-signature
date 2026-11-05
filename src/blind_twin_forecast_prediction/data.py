"""Frozen evaluation set (handoff section 1): archived Astra and Fable observer forecasts on the six condition-00
matching-pennies self-play games, paired on (gid, round, seat), with the public history each judge saw.

The target is the judge's reported forecast (`predicted`), never the player's move. The CSV `model` column is the player in
the seat and is not used as an identity. Predictor inputs are built only from the game log: rounds[:t-1] projected to
round, p1, p2, result.
"""
from __future__ import annotations

import csv
from typing import Dict, List, Tuple

from blind_twin_forecast_prediction import config as C

Key = Tuple[str, int, str]          # (gid, round, seat)


def read_forecasts(path) -> Dict[Tuple[str, str, int, str], str]:
    """{(judge, gid, round, seat): STAR|TRIANGLE} for valid filtered rows; game_condition kept as a string."""
    out = {}
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if not (r["game_type"] == C.GAME_TYPE and r["game_condition"] == C.GAME_CONDITION and r["label"] == C.LABEL
                    and r["judge"] in C.TARGETS and r["valid"] == "True"):
                continue
            k = (r["judge"], r["gid"], int(r["round"]), r["seat"])
            if k in out:
                raise ValueError(f"duplicate forecast {k} in {path}")
            pred = r["predicted"].strip().upper()
            if pred not in ("STAR", "TRIANGLE"):
                raise ValueError(f"bad forecast {pred!r} at {k}")
            out[k] = pred
    return out


def paired(forecasts) -> Dict[Key, Dict[str, str]]:
    """Items where both judges gave a valid forecast: {(gid, round, seat): {"astra": .., "fable": ..}}."""
    keys = {k[1:] for k in forecasts}
    return {k: {j: forecasts[(j,) + k] for j in C.TARGETS} for k in sorted(keys) if all((j,) + k in forecasts for j in C.TARGETS)}


def games() -> Dict[str, dict]:
    from blind_twin_selfself.judge import load_games
    out = {g["gid"]: g for g in load_games() if g["gid"] in C.GAMES}
    assert sorted(out) == sorted(C.GAMES), sorted(out)
    for g in out.values():
        assert g["game_type"] == C.GAME_TYPE and g["condition"] == C.GAME_CONDITION and len(g["rounds"]) == C.N_ROUNDS
    return out


def history(game: dict, t: int) -> List[dict]:
    """Exactly game["rounds"][:t-1], each row projected to round, p1, p2, result (empty at round 1)."""
    rows = game["rounds"][: t - 1]
    assert len(rows) == t - 1
    return [{k: r[k] for k in C.HISTORY_KEYS} for r in rows]


def pairing(gid: str) -> str:
    return gid.split(":")[1][:2]


def evaluation_set() -> dict:
    """Items (both seats of every round of the six games), original and retest labels, the 42 stable disagreements."""
    orig, rt = paired(read_forecasts(C.ORIGINAL_CSV)), paired(read_forecasts(C.RETEST_CSV))
    gs = games()
    items = []
    for gid in C.GAMES:
        for t in range(1, C.N_ROUNDS + 1):
            for seat in C.SEATS:
                k = (gid, t, seat)
                if k not in orig:
                    raise ValueError(f"missing paired original forecast {k}")
                g = gs[gid]["rounds"][t - 1]
                items.append(dict(gid=gid, round=t, seat=seat, pairing=pairing(gid), retested=gid in C.RETESTED,
                                  y_astra=orig[k]["astra"], y_fable=orig[k]["fable"],
                                  retest_astra=rt.get(k, {}).get("astra"), retest_fable=rt.get(k, {}).get("fable"),
                                  actual_move=g[seat]))
    for it in items:
        k = (it["gid"], it["round"], it["seat"])
        it["stable_disagreement"] = k in rt and it["y_astra"] != it["y_fable"] and \
            rt[k]["astra"] == it["y_astra"] and rt[k]["fable"] == it["y_fable"]
    inputs = {(gid, t): history(gs[gid], t) for gid in C.GAMES for t in range(1, C.N_ROUNDS + 1)}
    return dict(items=items, inputs=inputs, n_original=len(orig), n_retest=len(rt))


def acceptance(ev: dict) -> dict:
    """Handoff offline acceptance checks; all must hold before any paid call."""
    items = ev["items"]
    stable = [i for i in items if i["stable_disagreement"]]
    by = {p: sum(i["pairing"] == p for i in stable) for p in C.PAIRING}
    retest = [i for i in items if i["retest_astra"] and i["retest_fable"]]
    checks = dict(items=len(items) == C.EXPECTED["items"] == ev["n_original"],
                  retest_items=len(retest) == C.EXPECTED["retest_items"] == ev["n_retest"],
                  retest_games=sorted({i["gid"] for i in retest}) == sorted(C.RETESTED),
                  stable=len(stable) == C.EXPECTED["stable_disagreements"], stable_by_pairing=by == C.EXPECTED["stable_by_pairing"],
                  inputs=len(ev["inputs"]) == 120 and all(len(h) == t - 1 for (_, t), h in ev["inputs"].items()))
    return dict(ok=all(checks.values()), checks=checks, n_items=len(items), n_retest=len(retest), n_stable=len(stable),
                stable_by_pairing=by)
