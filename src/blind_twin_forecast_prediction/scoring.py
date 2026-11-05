"""Registered contrast and prespecified readouts (handoff section 4). Pure functions on item lists and prediction tables.

A prediction table maps (gid, round) -> (p_star_player_1, p_star_player_2), one predict() call per history (both seats).
B[a, j] = mean (p_star - y_j)^2: averaged within each game over rounds and both seats, then equally over games. Lower is better.

  Fable-target advantage  = B[astra, fable] - B[fable, fable]
  Astra-target advantage  = B[fable, astra] - B[astra, astra]
  Balanced self advantage = mean of the two (positive = same-model author better). Reciprocal: both target contrasts > 0.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from blind_twin_forecast_prediction import config as C

Table = Dict[Tuple[str, int], Tuple[float, float]]
SEAT_INDEX = {"p1": 0, "p2": 1}


def y(label: Optional[str]) -> Optional[int]:
    return None if label is None else 1 if label == "STAR" else 0


def p_of(table: Table, it: dict) -> float:
    return table[(it["gid"], it["round"])][SEAT_INDEX[it["seat"]]]


def label_key(judge: str, admin: str = "original") -> str:
    return f"y_{judge}" if admin == "original" else f"retest_{judge}"


def game_loss(table: Table, items: Sequence[dict], key: str) -> Dict[str, float]:
    """Per game: mean squared error over its items with a label under `key`."""
    by: Dict[str, List[float]] = {}
    for it in items:
        lab = y(it[key]) if key in it else None
        if lab is None:
            continue
        by.setdefault(it["gid"], []).append((p_of(table, it) - lab) ** 2)
    return {g: sum(v) / len(v) for g, v in by.items()}


def brier(table: Table, items: Sequence[dict], key: str, games: Optional[Sequence[str]] = None) -> float:
    gl = game_loss(table, items, key)
    gs = [g for g in (games or sorted(gl)) if g in gl]
    return sum(gl[g] for g in gs) / len(gs)


def item_brier(table: Table, items: Sequence[dict], key: str) -> float:
    xs = [(p_of(table, it) - y(it[key])) ** 2 for it in items if it.get(key) is not None]
    return sum(xs) / len(xs)


def cells_table(tables: Dict[Tuple[str, str], Table], items, admin="original", games=None) -> Dict[Tuple[str, str], float]:
    return {(a, j): brier(tables[(a, j)], items, label_key(j, admin), games) for a, j in C.CELLS}


def contrasts(B: Dict[Tuple[str, str], float]) -> dict:
    fab = B[("astra", "fable")] - B[("fable", "fable")]
    ast = B[("fable", "astra")] - B[("astra", "astra")]
    return dict(fable_target_advantage=fab, astra_target_advantage=ast, balanced_self_advantage=(fab + ast) / 2,
                reciprocal=fab > 0 and ast > 0)


def primary(tables, items) -> dict:
    B = cells_table(tables, items)
    games = sorted({it["gid"] for it in items})
    per_game = {g: contrasts(cells_table(tables, items, games=[g])) for g in games}
    logo = {g: contrasts(cells_table(tables, items, games=[x for x in games if x != g])) for g in games}
    rng = {k: (min(v[k] for v in logo.values()), max(v[k] for v in logo.values()))
           for k in ("fable_target_advantage", "astra_target_advantage", "balanced_self_advantage")}
    return dict(B={f"{a}->{j}": v for (a, j), v in B.items()}, contrasts=contrasts(B),
                per_game={g: {k: v for k, v in c.items() if k != "reciprocal"} for g, c in per_game.items()},
                logo_range=rng, logo=logo)


# ---------- reference predictors ----------

def constant_table(inputs, p=0.5) -> Table:
    return {k: (p, p) for k in inputs}


def repeat_table(inputs, p=C.REPEAT_P) -> Table:
    """Each observer calls a repeat of that seat's previous move: p on the previous shape, 1 - p on the other; 0.5 at round 1."""
    out = {}
    for k, h in inputs.items():
        if not h:
            out[k] = (0.5, 0.5)
        else:
            last = h[-1]
            out[k] = tuple(p if last[s] == "STAR" else 1 - p for s in ("p1", "p2"))
    return out


def references(inputs, items) -> dict:
    out = {}
    for name, t in (("constant_0.5", constant_table(inputs)), ("repeat_previous_0.75", repeat_table(inputs))):
        out[name] = {j: brier(t, items, label_key(j)) for j in C.TARGETS}
    return out


# ---------- diagnostics ----------

def modal(p: float) -> str:
    return "STAR" if p > 0.5 else "TRIANGLE" if p < 0.5 else "TIE"


def modal_diagnostic(tables, items) -> dict:
    """Per author: on identical inputs, how often its two programs make different modal calls (ties counted separately)."""
    out = {}
    for a in C.AUTHORS:
        ta, tf = tables[(a, "astra")], tables[(a, "fable")]
        n = diff = same = tie = 0
        identical = 0
        for it in items:
            pa, pf = p_of(ta, it), p_of(tf, it)
            n += 1
            identical += pa == pf
            ma, mf = modal(pa), modal(pf)
            if "TIE" in (ma, mf):
                tie += 1
            elif ma != mf:
                diff += 1
            else:
                same += 1
        out[a] = dict(n=n, different_modal_calls=diff, same_modal_calls=same, involving_tie=tie, identical_probabilities=identical,
                      mean_abs_prob_difference=sum(abs(p_of(ta, it) - p_of(tf, it)) for it in items) / n)
    return out


def target_swap(tables, items) -> dict:
    """Per author: loss after swapping its programs' target assignments minus loss with the intended assignments."""
    out = {}
    for a in C.AUTHORS:
        intended = (brier(tables[(a, "astra")], items, "y_astra") + brier(tables[(a, "fable")], items, "y_fable")) / 2
        swapped = (brier(tables[(a, "astra")], items, "y_fable") + brier(tables[(a, "fable")], items, "y_astra")) / 2
        out[a] = dict(intended=intended, swapped=swapped, swapped_minus_intended=swapped - intended)
    return out


def cross_scores(tables, items) -> dict:
    """Every program against both judges (game-averaged)."""
    return {f"{a}_for_{t}": {j: brier(tables[(a, t)], items, label_key(j)) for j in C.TARGETS} for a, t in C.CELLS}


# ---------- secondary readouts ----------

def split_games(tables, items) -> dict:
    out = {}
    for name, sel in (("retested_games", lambda it: it["retested"]), ("other_games", lambda it: not it["retested"])):
        sub = [it for it in items if sel(it)]
        B = cells_table(tables, sub)
        out[name] = dict(games=sorted({it["gid"] for it in sub}), B={f"{a}->{j}": v for (a, j), v in B.items()}, contrasts=contrasts(B))
    return out


def by_administration(tables, items) -> dict:
    """Retested games, the same frozen programs scored against the original and the retest labels separately."""
    sub = [it for it in items if it["retested"] and it["retest_astra"] and it["retest_fable"]]
    out = {}
    for admin in ("original", "retest"):
        B = cells_table(tables, sub, admin)
        out[admin] = dict(n_items=len(sub), B={f"{a}->{j}": v for (a, j), v in B.items()}, contrasts=contrasts(B))
    return out


def stable_disagreements(tables, items) -> dict:
    sub = [it for it in items if it["stable_disagreement"]]
    loss = {f"{a}_for_{t}": {j: item_brier(tables[(a, t)], sub, label_key(j)) for j in C.TARGETS} for a, t in C.CELLS}
    assign = {}
    for a in C.AUTHORS:
        right = wrong = tie = 0
        for it in sub:
            star_judge = "astra" if it["y_astra"] == "STAR" else "fable"
            other = "fable" if star_judge == "astra" else "astra"
            ps, po = p_of(tables[(a, star_judge)], it), p_of(tables[(a, other)], it)
            right += ps > po
            wrong += ps < po
            tie += ps == po
        assign[a] = dict(higher_star_to_star_judge=right, higher_star_to_other_judge=wrong, ties=tie)
    return dict(n=len(sub), by_pairing={p: sum(it["pairing"] == p for it in sub) for p in C.PAIRING}, item_brier=loss,
                star_assignment=assign)


def player_moves(tables, items) -> dict:
    """Separate descriptive check: each program scored against the actual player moves (not the registered target)."""
    return {f"{a}_for_{t}": brier(tables[(a, t)], items, "actual_move") for a, t in C.CELLS}


def item_rows(tables, items) -> List[dict]:
    rows = []
    for it in items:
        r = {k: it[k] for k in ("gid", "round", "seat", "pairing", "retested", "stable_disagreement", "y_astra", "y_fable",
                                "retest_astra", "retest_fable", "actual_move")}
        for a, t in C.CELLS:
            r[f"p_{a}_for_{t}"] = p_of(tables[(a, t)], it)
        rows.append(r)
    return rows


def score_all(tables, ev) -> dict:
    items, inputs = ev["items"], ev["inputs"]
    return dict(primary=primary(tables, items), references=references(inputs, items), cross_scores=cross_scores(tables, items),
                modal=modal_diagnostic(tables, items), target_swap=target_swap(tables, items),
                secondary=dict(split_games=split_games(tables, items), by_administration=by_administration(tables, items),
                               stable_disagreements=stable_disagreements(tables, items)),
                descriptive_player_moves=player_moves(tables, items))
