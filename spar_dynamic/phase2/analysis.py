"""Core estimators (Sections 6.4, 7.4, 8, 11).

H4 and its companions use fixed two-judge common sets; anonymous P/D/R use
two-judge common pair sets with both orders valid. Common-three versions are
mandatory sensitivities. Bootstraps resample parents (completion, named) or
complete six-parent blocks (pairs) and re-apply the fixed masks.
"""
from __future__ import annotations

import math
import random
from itertools import combinations
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from . import config as C

J = C.CORE_ORDER
PAIRS = list(combinations(J, 2))       # unordered judge pairs (a, b)
CONDS = ("known", "withheld")


def third(a: str, b: str) -> str:
    return [x for x in J if x not in (a, b)][0]


def nanmean(xs: Iterable[Optional[float]]) -> Optional[float]:
    xs = list(xs)
    if not xs or any(x is None or (isinstance(x, float) and math.isnan(x)) for x in xs):
        return None
    return sum(xs) / len(xs)


def pct_ci(vals: List[float]) -> Tuple[Optional[float], Optional[float]]:
    if not vals:
        return None, None
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


# ---------------------------------------------------------------------------
# AUROC with half credit for ties
# ---------------------------------------------------------------------------

def auroc(pos: Sequence[float], neg: Sequence[float]) -> float:
    if not pos or not neg:
        return float("nan")
    p = np.asarray(pos, float)[:, None]
    n = np.asarray(neg, float)[None, :]
    return float(np.mean((p > n) + 0.5 * (p == n)))


# ---------------------------------------------------------------------------
# H4 (Section 6.4)
# ---------------------------------------------------------------------------
# cells[(g, p)] = list of parent dicts {"parent_id", (judge, cond): loss or None}

Cells = Dict[Tuple[str, str], List[Dict[Any, Any]]]


def _crossover(cells: Cells, a: str, b: str, p: str, req: Sequence[str]) -> Optional[Dict[str, float]]:
    L: Dict[Tuple[str, str, str], float] = {}
    n = {}
    for g in (a, b):
        S = [d for d in cells.get((g, p), []) if all(d.get((j, c)) is not None for j in req for c in CONDS)]
        if not S:
            return None
        n[g] = len(S)
        for j in (a, b):
            for c in CONDS:
                L[(j, g, c)] = sum(d[(j, c)] for d in S) / len(S)
    G = {(j, g): L[(j, g, "withheld")] - L[(j, g, "known")] for j in (a, b) for g in (a, b)}
    Cc = {c: 0.5 * (L[(b, a, c)] - L[(a, a, c)] + L[(a, b, c)] - L[(b, b, c)]) for c in CONDS}
    own = 0.5 * (G[(a, a)] + G[(b, b)])
    other = 0.5 * (G[(b, a)] + G[(a, b)])
    return {"gain_own": own, "gain_other": other, "C_known": Cc["known"], "C_withheld": Cc["withheld"],
            "H4": own - other, f"n_{a}": n[a], f"n_{b}": n[b]}


H4_KEYS = ("H4", "gain_own", "gain_other", "C_known", "C_withheld")


def h4_panel(cells: Cells, mask: str = "pairwise") -> Dict[str, Any]:
    """mask='pairwise' (primary) or 'common3' (sensitivity)."""
    out: Dict[str, Any] = {"crossovers": {}, "per_prompt": {}, "estimable": True}
    for p in C.PROMPT_ORDER:
        vals = []
        for a, b in PAIRS:
            req = (a, b) if mask == "pairwise" else J
            t = _crossover(cells, a, b, p, req)
            out["crossovers"][f"{a}-{b}|{p}"] = t
            vals.append(t)
        if any(v is None for v in vals):
            out["per_prompt"][p] = None
            out["estimable"] = False
        else:
            out["per_prompt"][p] = {k: sum(v[k] for v in vals) / 3 for k in H4_KEYS}
    if out["estimable"]:
        out["panel"] = {k: sum(out["per_prompt"][p][k] for p in C.PROMPT_ORDER) / 2 for k in H4_KEYS}
    else:
        out["panel"] = None
    # judge-pair crossovers averaged over prompts (reported individually)
    out["pair_means"] = {}
    for a, b in PAIRS:
        ts = [out["crossovers"][f"{a}-{b}|{p}"] for p in C.PROMPT_ORDER]
        out["pair_means"][f"{a}-{b}"] = ({k: sum(t[k] for t in ts) / 2 for k in H4_KEYS}
                                         if all(t is not None for t in ts) else None)
    return out


def bootstrap_h4(cells: Cells, mask: str, n_boot: int, tag: str) -> Dict[str, Any]:
    rng = random.Random(C.derive_seed("bootstrap", "h4", mask, tag))
    pools = {}
    for key, lst in cells.items():
        pools[key] = [d for d in lst if any(d.get((j, c)) is not None for j in J for c in CONDS)]
    keys = list(H4_KEYS)
    reps = {k: [] for k in keys}
    pair_reps: Dict[str, Dict[str, List[float]]] = {f"{a}-{b}": {k: [] for k in keys} for a, b in PAIRS}
    prompt_reps: Dict[str, Dict[str, List[float]]] = {p: {k: [] for k in keys} for p in C.PROMPT_ORDER}
    undefined = 0
    for _ in range(n_boot):
        bc = {key: [lst[rng.randrange(len(lst))] for _ in range(len(lst))] if lst else [] for key, lst in pools.items()}
        res = h4_panel(bc, mask)
        if res["panel"] is None:
            undefined += 1
        else:
            for k in keys:
                reps[k].append(res["panel"][k])
        for pk, v in res["pair_means"].items():
            if v is not None:
                for k in keys:
                    pair_reps[pk][k].append(v[k])
        for p, v in res["per_prompt"].items():
            if v is not None:
                for k in keys:
                    prompt_reps[p][k].append(v[k])
    return {"n_boot": n_boot, "undefined": undefined, "undefined_frac": undefined / n_boot,
            "ci": {k: pct_ci(reps[k]) for k in keys},
            "pair_ci": {pk: {k: pct_ci(v[k]) for k in keys} for pk, v in pair_reps.items()},
            "prompt_ci": {p: {k: pct_ci(v[k]) for k in keys} for p, v in prompt_reps.items()}}


def available_case_matrix(cells: Cells) -> Dict[str, Optional[float]]:
    out = {}
    for (g, p), lst in cells.items():
        for j in J:
            for c in CONDS:
                v = [d[(j, c)] for d in lst if d.get((j, c)) is not None]
                out[f"{j}|{g}|{c}|{p}"] = sum(v) / len(v) if v else None
                out[f"n:{j}|{g}|{c}|{p}"] = len(v)
    return out


def h4_coefficients() -> Dict[Tuple[str, str, str, str], float]:
    """Complete-data linear weights of each mean loss L[j,g,c,p] in panel H4."""
    w = {}
    for p in C.PROMPT_ORDER:
        for j in J:
            for g in J:
                base = (1 / 3) if j == g else (-0.5 / 3)
                w[(j, g, "withheld", p)] = 0.5 * base
                w[(j, g, "known", p)] = -0.5 * base
    return w


def h4_worst_case(cells: Cells) -> Dict[str, Optional[float]]:
    """Bounds on complete-data panel H4 over all attempted slots, unobserved losses in {0,1}."""
    w = h4_coefficients()
    lo = hi = 0.0
    for (g, p), lst in cells.items():
        n = len(lst)
        if n == 0:
            return {"lower": None, "upper": None}
        for j in J:
            for c in CONDS:
                coef = w[(j, g, c, p)] / n
                for d in lst:
                    v = d.get((j, c))
                    if v is None:
                        lo += coef * (0.0 if coef > 0 else 1.0)
                        hi += coef * (1.0 if coef > 0 else 0.0)
                    else:
                        lo += coef * v
                        hi += coef * v
    return {"lower": lo, "upper": hi}


# ---------------------------------------------------------------------------
# Anonymous P / D / R (Section 7.4)
# ---------------------------------------------------------------------------
# items: list of dicts {pair_id, block_id, prompt, relation, src: (s1, s2), q: {judge: float|None}}


def _A(items: List[Dict[str, Any]], j: str, g: str, r: str, p: str) -> float:
    pos = [it["q"][j] for it in items if it["prompt"] == p and it["relation"] == "SAME" and it["src"][0] == g]
    neg = [it["q"][j] for it in items if it["prompt"] == p and it["relation"] == "DIFFERENT" and set(it["src"]) == {g, r}]
    return auroc(pos, neg)


def _valid_for(items, judges):
    return [it for it in items if all(it["q"].get(j) is not None for j in judges)]


def pdr_crossover(items: List[Dict[str, Any]], a: str, b: str, p: str,
                  A: Callable = _A) -> Dict[str, float]:
    m = third(a, b)
    S = _valid_for(items, (a, b))
    Pc = 0.5 * (A(S, a, a, m, p) - A(S, b, a, m, p) + A(S, b, b, m, p) - A(S, a, b, m, p))
    Dc = 0.5 * (A(S, a, m, a, p) - A(S, b, m, a, p) + A(S, b, m, b, p) - A(S, a, m, b, p))
    return {"P": Pc, "D": Dc, "R": (Pc + Dc) / 2, "n_items": len([s for s in S if s["prompt"] == p])}


def _isnan(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def pdr_panel(items: List[Dict[str, Any]], A: Callable = _A) -> Dict[str, Any]:
    out: Dict[str, Any] = {"crossovers": {}, "per_prompt": {}}
    est = True
    for p in C.PROMPT_ORDER:
        vals = []
        for a, b in PAIRS:
            t = pdr_crossover(items, a, b, p, A)
            out["crossovers"][f"{a}-{b}|{p}"] = t
            vals.append(t)
        if any(_isnan(v[k]) for v in vals for k in ("P", "D")):
            out["per_prompt"][p] = None
            est = False
        else:
            out["per_prompt"][p] = {k: sum(v[k] for v in vals) / 3 for k in ("P", "D", "R")}
    out["panel"] = ({k: sum(out["per_prompt"][p][k] for p in C.PROMPT_ORDER) / 2 for k in ("P", "D", "R")}
                    if est else None)
    out["estimable"] = est
    out["pair_means"] = {}
    for a, b in PAIRS:
        ts = [out["crossovers"][f"{a}-{b}|{p}"] for p in C.PROMPT_ORDER]
        out["pair_means"][f"{a}-{b}"] = ({k: sum(t[k] for t in ts) / 2 for k in ("P", "D", "R")}
                                         if not any(_isnan(t[k]) for t in ts for k in ("P", "D")) else None)
    return out


def pdr_common3(items: List[Dict[str, Any]], A: Callable = _A) -> Dict[str, Any]:
    S = _valid_for(items, J)
    out: Dict[str, Any] = {"per_prompt": {}, "A": {}}
    est = True
    for p in C.PROMPT_ORDER:
        Pv, Dv = [], []
        for g in J:
            for r in J:
                if g == r:
                    continue
                b = third(g, r)
                Ag = A(S, g, g, r, p); Ar = A(S, r, g, r, p); Ab = A(S, b, g, r, p)
                out["A"][f"{g}>{r}|{p}"] = {"focal": Ag, "alternative": Ar, "uninvolved": Ab}
                Pv.append(Ag - Ab); Dv.append(Ar - Ab)
        if any(_isnan(x) for x in Pv + Dv):
            out["per_prompt"][p] = None; est = False
        else:
            P, D = sum(Pv) / 6, sum(Dv) / 6
            out["per_prompt"][p] = {"P": P, "D": D, "R": (P + D) / 2, "D_legacy": P - D / 2}
    out["panel"] = ({k: sum(out["per_prompt"][p][k] for p in C.PROMPT_ORDER) / 2 for k in ("P", "D", "R", "D_legacy")}
                    if est else None)
    out["n_items"] = len(S)
    return out


def bootstrap_pdr(items: List[Dict[str, Any]], n_boot: int, tag: str, A: Callable = _A,
                  unit: str = "block_id") -> Dict[str, Any]:
    rng = random.Random(C.derive_seed("bootstrap", "pdr", tag))
    by_prompt: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for it in items:
        by_prompt.setdefault(it["prompt"], {}).setdefault(it[unit], []).append(it)
    reps = {k: [] for k in ("P", "D", "R")}
    c3 = {k: [] for k in ("P", "D", "R", "D_legacy")}
    pair_reps = {f"{a}-{b}": {k: [] for k in ("P", "D", "R")} for a, b in PAIRS}
    undefined = undefined3 = 0
    for _ in range(n_boot):
        sample = []
        for p, blocks in by_prompt.items():
            keys = list(blocks.keys())
            for _k in range(len(keys)):
                sample.extend(blocks[keys[rng.randrange(len(keys))]])
        res = pdr_panel(sample, A)
        if res["panel"] is None:
            undefined += 1
        else:
            for k in reps:
                reps[k].append(res["panel"][k])
        for pk, v in res["pair_means"].items():
            if v is not None:
                for k in v:
                    pair_reps[pk][k].append(v[k])
        r3 = pdr_common3(sample, A)
        if r3["panel"] is None:
            undefined3 += 1
        else:
            for k in c3:
                c3[k].append(r3["panel"][k])
    return {"n_boot": n_boot, "undefined": undefined, "undefined_frac": undefined / n_boot,
            "ci": {k: pct_ci(v) for k, v in reps.items()},
            "pair_ci": {pk: {k: pct_ci(v[k]) for k in v} for pk, v in pair_reps.items()},
            "common3_ci": {k: pct_ci(v) for k, v in c3.items()},
            "common3_undefined_frac": undefined3 / n_boot}


def pair_bias_table(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for p in C.PROMPT_ORDER:
        for j in J:
            for g in J:
                for r in J:
                    if g == r:
                        continue
                    S = _valid_for(items, (j,))
                    pos = [it["q"][j] for it in S if it["prompt"] == p and it["relation"] == "SAME" and it["src"][0] == g]
                    neg = [it["q"][j] for it in S if it["prompt"] == p and it["relation"] == "DIFFERENT" and set(it["src"]) == {g, r}]
                    if not pos or not neg:
                        continue
                    dec = lambda q: 1.0 if q > 0.5 else (0.5 if q == 0.5 else 0.0)
                    hit = sum(dec(q) for q in pos) / len(pos)
                    fs = sum(dec(q) for q in neg) / len(neg)
                    rows.append({"prompt": p, "judge": j, "focal": g, "alternative": r,
                                 "role": "focal" if j == g else ("alternative" if j == r else "uninvolved"),
                                 "n_pos": len(pos), "n_neg": len(neg), "same_hit_rate": hit,
                                 "false_same_rate": fs, "balanced_accuracy": (hit + 1 - fs) / 2,
                                 "brier": (sum((q - 1) ** 2 for q in pos) + sum(q ** 2 for q in neg)) / (len(pos) + len(neg)),
                                 "auc": auroc(pos, neg)})
    return rows


# ---------------------------------------------------------------------------
# Named roles (Section 8): single-string probabilities
# ---------------------------------------------------------------------------
# named items: {parent_id, prompt, source, prob: {judge: {alias: prob}|None}}


def named_A(items: List[Dict[str, Any]], j: str, g: str, r: str, p: str) -> float:
    pos = [it["prob"][j][g] for it in items if it["prompt"] == p and it["source"] == g]
    neg = [it["prob"][j][g] for it in items if it["prompt"] == p and it["source"] == r]
    return auroc(pos, neg)


def named_panel(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    conv = [{**it, "q": {j: (1.0 if it["prob"].get(j) is not None else None) for j in J}} for it in items]
    # reuse the P/D/R machinery with a named AUC function; masks come from 'q'
    def A(S, j, g, r, p):
        return named_A(S, j, g, r, p)
    return pdr_panel(conv, A)


def named_common3(items):
    conv = [{**it, "q": {j: (1.0 if it["prob"].get(j) is not None else None) for j in J}} for it in items]
    return pdr_common3(conv, lambda S, j, g, r, p: named_A(S, j, g, r, p))


def bootstrap_named(items, n_boot, tag):
    conv = [{**it, "q": {j: (1.0 if it["prob"].get(j) is not None else None) for j in J},
             "unit": it["parent_id"]} for it in items]
    # resample parents within source x prompt: encode cell into prompt-level grouping
    rng = random.Random(C.derive_seed("bootstrap", "named", tag))
    cells: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for it in conv:
        cells.setdefault((it["source"], it["prompt"]), []).append(it)
    reps = {k: [] for k in ("P", "D", "R")}
    und = 0
    A = lambda S, j, g, r, p: named_A(S, j, g, r, p)
    for _ in range(n_boot):
        sample = []
        for key, lst in cells.items():
            sample.extend(lst[rng.randrange(len(lst))] for _ in range(len(lst)))
        res = pdr_panel(sample, A)
        if res["panel"] is None:
            und += 1
        else:
            for k in reps:
                reps[k].append(res["panel"][k])
    return {"n_boot": n_boot, "undefined_frac": und / n_boot, "ci": {k: pct_ci(v) for k, v in reps.items()}}


def named_secondary(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for j in J:
        for p in C.PROMPT_ORDER:
            S = [it for it in items if it["prompt"] == p and it["prob"].get(j) is not None]
            if not S:
                continue
            choice = {g: 0 for g in J}
            correct_by_src = {g: [] for g in J}
            brier_sum = []
            for it in S:
                pr = it["prob"][j]
                top = max(pr, key=pr.get)
                choice[top] += 1
                correct_by_src[it["source"]].append(1.0 if top == it["source"] else 0.0)
                brier_sum.append(sum((pr[g] - (1.0 if g == it["source"] else 0.0)) ** 2 for g in J))
            recalls = [sum(v) / len(v) for v in correct_by_src.values() if v]
            rows.append({"judge": j, "prompt": p, "n": len(S), "choice_counts": choice,
                         "self_choice_rate": choice[j] / len(S),
                         "balanced_accuracy": sum(recalls) / len(recalls) if recalls else None,
                         "multiclass_brier_sum": sum(brier_sum) / len(brier_sum),
                         "recall_by_source": {g: (sum(v) / len(v) if v else None) for g, v in correct_by_src.items()}})
    return rows


# ---------------------------------------------------------------------------
# Resolution vocabulary (Section 11.4)
# ---------------------------------------------------------------------------

def resolution_row(name: str, est: Optional[float], ci: Tuple[Optional[float], Optional[float]],
                   margin: float, undefined_frac: float, support: str, mask: str) -> Dict[str, Any]:
    lo, hi = ci if ci else (None, None)
    row = {"contrast": name, "estimate": est, "ci_lower": lo, "ci_upper": hi, "margin": margin,
           "undefined_bootstrap_fraction": round(undefined_frac, 4), "support": support, "mask": mask}
    if est is None or lo is None or hi is None:
        row.update(status="not_estimable", direction="none", width=None, max_side_distance=None,
                   bounded_small=False, benefit_not_excluded=None, harm_not_excluded=None)
        return row
    stable = undefined_frac <= 0.01
    row["width"] = hi - lo
    row["max_side_distance"] = max(abs(lo), abs(hi))
    if not stable:
        row.update(status="unstable_interval", direction="none", bounded_small=False,
                   benefit_not_excluded=None, harm_not_excluded=None)
        return row
    direction = "resolved_positive" if lo > 0 else ("resolved_negative" if hi < 0 else "unresolved")
    row.update(status="ok", direction=direction,
               bounded_small=(lo >= -margin and hi <= margin),
               benefit_not_excluded=hi >= margin, harm_not_excluded=lo <= -margin)
    return row
