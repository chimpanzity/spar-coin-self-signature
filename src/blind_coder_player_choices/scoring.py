"""Scoring (handoff sections 4-5). Pure functions of item lists and per-program prediction tables {item_key: p_STAR}.

Loss for one program on one target's data: Brier (p - y)^2 with STAR = 1, averaged within each seat-game over rounds, then
equally over games within each seat x opponent stratum, then equally over the six strata. Generation-level losses are
averaged across blocks (never probabilities).

  A. Fable own-author advantage = L(astra->fable) - L(fable->fable); Astra own-author advantage = L(fable->astra) - L(astra->astra);
     balanced = mean. Reciprocal only if both > 0. Primary uses complete four-cell blocks.
  B. Per author and block: swapped - intended (each program also scored on the other player's data). Plus a resemblance
     diagnostic: which player each author's programs fit, ignoring the name in the prompt.
  C. Rounds 2-20: p_switch = 1 - p_STAR if the player last chose STAR else p_STAR; mean after wins and after losses, vs observed.
"""
from __future__ import annotations

import statistics
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from blind_coder_player_choices import config as C

Key = Tuple[str, int, str]
Preds = Dict[Key, float]


def key(it) -> Key:
    return it["game_id"], it["round"], it["seat"]


def yv(it) -> int:
    return 1 if it["y"] == "STAR" else 0


def stratified_loss(pred: Preds, items: Sequence[dict], target: str, keep: Optional[Callable[[dict], bool]] = None) -> float:
    sg: Dict[Tuple[str, str, str], List[float]] = {}
    for it in items:
        if it["target"] != target or (keep and not keep(it)):
            continue
        sg.setdefault((it["seat"], it["opponent"], it["game_id"]), []).append((pred[key(it)] - yv(it)) ** 2)
    strata: Dict[Tuple[str, str], List[float]] = {}
    for (seat, opp, _), v in sg.items():
        strata.setdefault((seat, opp), []).append(sum(v) / len(v))
    means = [sum(v) / len(v) for v in strata.values()]
    return sum(means) / len(means)


def item_loss(pred: Preds, items, target) -> float:
    xs = [(pred[key(it)] - yv(it)) ** 2 for it in items if it["target"] == target]
    return sum(xs) / len(xs)


# ---------- programs and blocks ----------

def complete_blocks(programs: List[dict]) -> List[int]:
    return sorted(b for b in {p["block"] for p in programs}
                  if all(any(p["block"] == b and p["author"] == a and p["target"] == j and p["valid"] for p in programs) for a, j in C.CELLS))


def prog(programs, b, a, j) -> Optional[dict]:
    return next((p for p in programs if p["block"] == b and p["author"] == a and p["target"] == j and p["valid"]), None)


def contrasts(L: Dict[Tuple[str, str], float]) -> dict:
    fab = L[("astra", "fable")] - L[("fable", "fable")]
    ast = L[("fable", "astra")] - L[("astra", "astra")]
    return dict(fable_own_author_advantage=fab, astra_own_author_advantage=ast, balanced_self_advantage=(fab + ast) / 2,
                reciprocal=fab > 0 and ast > 0)


def primary(programs, preds: Dict[str, Preds], items, keep=None) -> dict:
    blocks = complete_blocks(programs)
    gen = {(a, j): [stratified_loss(preds[prog(programs, b, a, j)["id"]], items, j, keep) for b in blocks] for a, j in C.CELLS}
    L = {c: sum(v) / len(v) for c, v in gen.items()}
    per_block = []
    for i, b in enumerate(blocks):
        per_block.append(dict(block=b, **{k: v for k, v in contrasts({c: gen[c][i] for c in C.CELLS}).items()}))
    return dict(complete_blocks=blocks, n_complete=len(blocks), planned_comparison_complete=len(blocks) >= C.MIN_COMPLETE_BLOCKS,
                L={f"{a}->{j}": v for (a, j), v in L.items()}, contrasts=contrasts(L), per_block=per_block,
                block_summary={k: _desc([r[k] for r in per_block]) for k in ("fable_own_author_advantage", "astra_own_author_advantage",
                                                                             "balanced_self_advantage")},
                n_blocks_reciprocal=sum(r["reciprocal"] for r in per_block))


def _desc(xs) -> dict:
    return dict(n=len(xs), mean=sum(xs) / len(xs), sd=statistics.stdev(xs) if len(xs) > 1 else 0.0, min=min(xs), max=max(xs),
                n_positive=sum(x > 0 for x in xs)) if xs else dict(n=0)


def generation_table(programs, preds, items) -> List[dict]:
    rows = []
    for p in programs:
        r = dict(program=p["id"], block=p["block"], author=p["author"], intended_target=p["target"], valid=p["valid"], status=p["status"])
        if p["valid"]:
            for j in C.TARGETS:
                r[f"loss_on_{j}"] = stratified_loss(preds[p["id"]], items, j)
            r["loss_intended"] = r[f"loss_on_{p['target']}"]
        rows.append(r)
    return rows


def cell_descriptives(programs, preds, items) -> dict:
    """All valid programs (not only complete blocks): count, mean, sd, min, max of intended-target loss."""
    out = {}
    for a, j in C.CELLS:
        xs = [stratified_loss(preds[p["id"]], items, j) for p in programs if p["author"] == a and p["target"] == j and p["valid"]]
        out[f"{a}->{j}"] = dict(n_valid=len(xs), n_generated=sum(p["author"] == a and p["target"] == j for p in programs), **_desc(xs))
    return out


# ---------- B: targeting and resemblance ----------

def target_swap(programs, preds, items) -> dict:
    blocks = complete_blocks(programs)
    out = {}
    for a in C.AUTHORS:
        rows = []
        for b in blocks:
            pa, pf = prog(programs, b, a, "astra"), prog(programs, b, a, "fable")
            intended = (stratified_loss(preds[pa["id"]], items, "astra") + stratified_loss(preds[pf["id"]], items, "fable")) / 2
            swapped = (stratified_loss(preds[pa["id"]], items, "fable") + stratified_loss(preds[pf["id"]], items, "astra")) / 2
            rows.append(dict(block=b, intended=intended, swapped=swapped, swapped_minus_intended=swapped - intended))
        out[a] = dict(per_block=rows, summary=_desc([r["swapped_minus_intended"] for r in rows]),
                      mean_intended=sum(r["intended"] for r in rows) / len(rows), mean_swapped=sum(r["swapped"] for r in rows) / len(rows))
    return out


def resemblance(programs, preds, items) -> dict:
    """Ignoring the prompt's name: each author's programs (complete blocks, both names pooled) scored on each player's data.
    Across players the data differ, so per-author comparisons mix fit and difficulty; the author x player interaction does not."""
    blocks = complete_blocks(programs)
    M = {}
    for a in C.AUTHORS:
        ps = [p for p in programs if p["author"] == a and p["valid"] and p["block"] in blocks]
        for j in C.TARGETS:
            M[(a, j)] = sum(stratified_loss(preds[p["id"]], items, j) for p in ps) / len(ps)
    inter = ((M[("astra", "fable")] - M[("astra", "astra")]) + (M[("fable", "astra")] - M[("fable", "fable")])) / 2
    return dict(loss={f"{a}_programs_on_{j}": v for (a, j), v in M.items()},
                better_fit={a: min(C.TARGETS, key=lambda j: M[(a, j)]) for a in C.AUTHORS},
                author_x_player_self_resemblance=inter)


# ---------- C: response to wins and losses ----------

def p_switch(p_star: float, prev_own: str) -> float:
    return 1 - p_star if prev_own == "STAR" else p_star


def switch_profile(pred: Preds, items, target) -> dict:
    out = {}
    for k, won in (("win", True), ("loss", False)):
        sub = [it for it in items if it["target"] == target and it["round"] > 1 and it["prev_won"] is won]
        out[k] = sum(p_switch(pred[key(it)], it["prev_own"]) for it in sub) / len(sub)
    out["gap_win_minus_loss"] = out["win"] - out["loss"]
    return out


def observed_switch(items) -> dict:
    out = {}
    for j in C.TARGETS:
        d = {}
        for k, won in (("win", True), ("loss", False)):
            sub = [it for it in items if it["target"] == j and it["round"] > 1 and it["prev_won"] is won]
            d[k] = sum(it["y"] != it["prev_own"] for it in sub) / len(sub) if sub else None
            d[f"n_{k}"] = len(sub)
        d["gap_win_minus_loss"] = d["win"] - d["loss"] if d["win"] is not None and d["loss"] is not None else None
        out[j] = d
    return out


def switch_cells(programs, preds, items) -> dict:
    blocks = complete_blocks(programs)
    out = {}
    for a, j in C.CELLS:
        prof = [switch_profile(preds[prog(programs, b, a, j)["id"]], items, j) for b in blocks]
        out[f"{a}->{j}"] = {k: _desc([p[k] for p in prof]) for k in ("win", "loss", "gap_win_minus_loss")}
    return dict(observed=observed_switch(items), predicted=out)


# ---------- baselines ----------

def constant(items, p=0.5) -> Preds:
    return {key(it): p for it in items}


def history_rule(items, switch: bool, p=C.HISTORY_RULE_P) -> Preds:
    out = {}
    for it in items:
        if it["round"] == 1:
            out[key(it)] = 0.5
        else:
            same = p if not switch else 1 - p
            out[key(it)] = same if it["prev_own"] == "STAR" else 1 - same
    return out


def learned_reference(items) -> Preds:
    """Outside observer given past examples: per target, switch rates after wins and losses from the *other* replicate wave's
    games, add-one smoothed; held-out predictions pooled over both waves; 0.5 at openings."""
    out = {}
    for j in C.TARGETS:
        for w in (1, 2):
            train = [it for it in items if it["target"] == j and it["replicate"] != w and it["round"] > 1]
            rate = {}
            for won in (True, False):
                sub = [it for it in train if it["prev_won"] is won]
                rate[won] = (sum(it["y"] != it["prev_own"] for it in sub) + 1) / (len(sub) + 2)
            for it in items:
                if it["target"] != j or it["replicate"] != w:
                    continue
                if it["round"] == 1:
                    out[key(it)] = 0.5
                else:
                    ps = rate[it["prev_won"]]
                    out[key(it)] = 1 - ps if it["prev_own"] == "STAR" else ps
    return out


def baselines(items) -> dict:
    preds = {"constant_0.5": constant(items), "repeat_last_0.75": history_rule(items, False), "switch_last_0.75": history_rule(items, True),
             "learned_other_wave": learned_reference(items)}
    return {name: {j: stratified_loss(p, items, j) for j in C.TARGETS} for name, p in preds.items()}, preds


# ---------- sensitivity ----------

def sensitivity(programs, preds, items) -> dict:
    games = sorted({it["game_id"] for it in items})
    logo = {g: primary(programs, preds, items, keep=lambda it, g=g: it["game_id"] != g)["contrasts"] for g in games}
    rng = {k: (min(v[k] for v in logo.values()), max(v[k] for v in logo.values()))
           for k in ("fable_own_author_advantage", "astra_own_author_advantage", "balanced_self_advantage")}
    waves = {f"replicate_{w}": primary(programs, preds, items, keep=lambda it, w=w: it["replicate"] == w)["contrasts"] for w in (1, 2)}
    no_open = primary(programs, preds, items, keep=lambda it: it["round"] > 1)
    return dict(leave_one_game_out=logo, leave_one_game_out_range=rng, by_wave=waves,
                excluding_round_1=dict(L=no_open["L"], contrasts=no_open["contrasts"]))


def score_all(programs, preds, items) -> dict:
    base, _ = baselines(items)
    blocks = complete_blocks(programs)
    out = dict(validity=dict(generated=len(programs), valid=sum(p["valid"] for p in programs), complete_blocks=blocks,
                             failures=[dict(program=p["id"], status=p["status"]) for p in programs if not p["valid"]]),
               cell_descriptives=cell_descriptives(programs, preds, items), baselines=base)
    if not blocks:
        out["primary"] = "not computed: no complete four-cell block"
        return out
    out.update(primary=primary(programs, preds, items), target_swap=target_swap(programs, preds, items),
               resemblance=resemblance(programs, preds, items), switching=switch_cells(programs, preds, items),
               sensitivity=sensitivity(programs, preds, items))
    return out
