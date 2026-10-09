"""Prespecified analysis (handoff Section 6). Unit = complete 20-round game."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import config as C
from .game import payoff_p1

J = C.ORDER


# ---------------------------------------------------------------------------
# Cell means and contrasts
# ---------------------------------------------------------------------------

def game_p1_payoff(g) -> float:
    return sum(payoff_p1(r["result"]) for r in g["rounds"]) / len(g["rounds"])


def cell_means(games: List[Dict[str, Any]]) -> Dict[Tuple[str, str, str], Optional[float]]:
    by = defaultdict(list)
    for g in games:
        if g["status"] == "complete":
            by[(g["p1_model"], g["p2_model"], g["condition"])].append(game_p1_payoff(g))
    return {(i, j, c): (sum(by[(i, j, c)]) / len(by[(i, j, c)]) if by[(i, j, c)] else None)
            for i, j in C.PAIRINGS for c in C.COND_ORDER}


def contrasts(V: Dict[Tuple[str, str, str], Optional[float]]) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}

    def v(i, j, c):
        return V.get((i, j, c))

    for i, j in C.PAIRINGS:
        vals = [v(i, j, c) for c in C.COND_ORDER]
        ok = all(x is not None for x in vals)
        V00, V10, V01, V11 = vals
        out[f"U1[{i},{j}]"] = V10 - V00 if ok else None
        out[f"U2[{i},{j}]"] = V00 - V01 if ok else None
        out[f"U[{i},{j}]"] = ((V10 - V00) + (V00 - V01)) / 2 if ok else None
        out[f"F1[{i},{j}]"] = ((V10 - V00) + (V11 - V01)) / 2 if ok else None
        out[f"F2[{i},{j}]"] = ((V00 - V01) + (V10 - V11)) / 2 if ok else None
        out[f"INT[{i},{j}]"] = V11 - V10 - V01 + V00 if ok else None
    Ds = []
    for i in J:
        j, k = [m for m in J if m != i]
        need = [out[f"U1[{i},{i}]"], out[f"U2[{i},{i}]"], out[f"U1[{i},{j}]"], out[f"U2[{j},{i}]"], out[f"U1[{i},{k}]"], out[f"U2[{k},{i}]"]]
        if any(x is None for x in need):
            out[f"S[{i}]"] = out[f"O[{i}]"] = out[f"D[{i}]"] = None
            Ds.append(None)
            continue
        S = (out[f"U1[{i},{i}]"] + out[f"U2[{i},{i}]"]) / 2
        O = (out[f"U1[{i},{j}]"] + out[f"U2[{j},{i}]"] + out[f"U1[{i},{k}]"] + out[f"U2[{k},{i}]"]) / 4
        out[f"S[{i}]"], out[f"O[{i}]"], out[f"D[{i}]"] = S, O, S - O
        Ds.append(S - O)
    out["D"] = sum(Ds) / 3 if all(d is not None for d in Ds) else None
    return out


def bootstrap(games, n_boot=C.N_BOOT, seed=C.ANALYSIS_SEED):
    cells = defaultdict(list)
    for g in games:
        if g["status"] == "complete":
            cells[(g["p1_model"], g["p2_model"], g["condition"])].append(game_p1_payoff(g))
    rng = random.Random(seed)
    reps = defaultdict(list)
    undefined = defaultdict(int)
    keys = list(contrasts(cell_means(games)).keys())
    for _ in range(n_boot):
        V = {}
        for i, j in C.PAIRINGS:
            for c in C.COND_ORDER:
                xs = cells.get((i, j, c), [])
                V[(i, j, c)] = (sum(xs[rng.randrange(len(xs))] for _ in xs) / len(xs)) if xs else None
        ct = contrasts(V)
        for k in keys:
            if ct[k] is None:
                undefined[k] += 1
            else:
                reps[k].append(ct[k])
    ci = {}
    for k in keys:
        v = sorted(reps[k])
        ci[k] = {"lo": v[int(0.025 * (len(v) - 1))] if v else None, "hi": v[int(0.975 * (len(v) - 1))] if v else None,
                 "undefined_frac": undefined[k] / n_boot}
    return ci


# ---------------------------------------------------------------------------
# Behaviour and prospective baselines
# ---------------------------------------------------------------------------

def _credit(pred, actual):
    s = set(C.MOVES) if pred is None else (set(pred) if isinstance(pred, tuple) else {pred})
    return (1 / len(s)) if actual in s else 0.0


def _argmax(d):
    m = max(d.values())
    top = tuple(sorted(k for k, v in d.items() if v == m))
    return top[0] if len(top) == 1 else top


def seat_rows(g, key):
    other = "p2" if key == "p1" else "p1"
    me = "Player 1" if key == "p1" else "Player 2"
    return [r[key] for r in g["rounds"]], [r[other] for r in g["rounds"]], [r["result"] for r in g["rounds"]], me


def behaviour(g, key) -> Dict[str, Any]:
    own, opp, res, me = seat_rows(g, key)
    n = len(own)
    cnt = Counter(own)
    trans = Counter(zip(own, own[1:]))
    runs, cur = [], 1
    for a, b in zip(own, own[1:]):
        if a == b:
            cur += 1
        else:
            runs.append(cur); cur = 1
    runs.append(cur)
    def cond_rate(kind):
        idx = [t for t in range(n - 1) if (res[t] == me if kind == "win" else (res[t] == "Tie" if kind == "tie" else res[t] not in (me, "Tie")))]
        if not idx:
            return None
        same = sum(own[t + 1] == own[t] for t in idx)
        return 100 * (same if kind == "win" else len(idx) - same) / len(idx)
    ent = -sum((v / n) * math.log2(v / n) for v in cnt.values())
    d = {f"pct_{m.lower()}": 100 * cnt[m] / n for m in C.MOVES}
    d.update({"switch_rate": 100 * sum(a != b for a, b in zip(own, own[1:])) / (n - 1), "longest_run": max(runs),
              "win_stay": cond_rate("win"), "lose_shift": cond_rate("loss"), "tie_shift": cond_rate("tie"),
              "entropy_bits": ent})
    for a in C.MOVES:
        for b in C.MOVES:
            d[f"T_{a[0]}{b[0]}"] = trans[(a, b)]
    return d


BASELINES = ("uniform", "expanding_frequency", "repeat_last", "markov1_smoothed", "counter_opponent_last")


def baseline_scores(g, key) -> Dict[str, float]:
    own, opp, res, me = seat_rows(g, key)
    acc = {b: [] for b in BASELINES}
    for t in range(len(own)):
        a = own[t]
        acc["uniform"].append(1 / 3)
        if t == 0:
            for b in BASELINES[1:]:
                acc[b].append(1 / 3)
            continue
        past = own[:t]
        acc["expanding_frequency"].append(_credit(_argmax({m: past.count(m) for m in C.MOVES}), a))
        acc["repeat_last"].append(_credit(past[-1], a))
        nxt = [y for x, y in zip(past, past[1:]) if x == past[-1]]
        acc["markov1_smoothed"].append(_credit(_argmax({m: nxt.count(m) + 1 for m in C.MOVES}), a))
        acc["counter_opponent_last"].append(_credit(C.BEATEN_BY[opp[t - 1]], a))
    return {b: 100 * sum(v) / len(v) for b, v in acc.items()}


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

def _w(path, rows):
    if not rows:
        path.write_text(""); return
    keys = list(rows[0].keys())
    for r in rows[1:]:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)


def fmt(x, nd=3, sign=False):
    return "NA" if x is None else (f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}")


def analyze(rd: Path) -> Dict[str, Any]:
    games = [json.loads(l) for l in (rd / "game_logs.jsonl").read_text().splitlines() if l.strip()]
    calls = [json.loads(l) for l in (rd / "calls.jsonl").read_text().splitlines() if l.strip()]
    grows, rrows, brows, hrows = [], [], [], []
    for g in games:
        comp = g["status"] == "complete"
        grows.append({"game_id": g["game_id"], "pairing": f"{g['p1_model']}-{g['p2_model']}", "p1_model": g["p1_model"],
                      "p2_model": g["p2_model"], "condition": g["condition"], "replicate": g["replicate"], "status": g["status"],
                      "n_valid_rounds": g["n_valid_rounds"], "note": g["note"],
                      "p1_payoff": game_p1_payoff(g) if g["rounds"] else None,
                      "p1_wins": sum(r["result"] == "Player 1" for r in g["rounds"]),
                      "p2_wins": sum(r["result"] == "Player 2" for r in g["rounds"]),
                      "ties": sum(r["result"] == "Tie" for r in g["rounds"])})
        for r in g["rounds"]:
            rrows.append({"game_id": g["game_id"], "p1_model": g["p1_model"], "p2_model": g["p2_model"], "condition": g["condition"],
                          "complete_game": comp, **r, "p1_payoff": payoff_p1(r["result"])})
        if g["rounds"]:
            for key, model, informed, opp in (("p1", g["p1_model"], g["p1_informed"], g["p2_model"]),
                                              ("p2", g["p2_model"], g["p2_informed"], g["p1_model"])):
                base = {"game_id": g["game_id"], "seat": "Player 1" if key == "p1" else "Player 2", "model": model,
                        "opponent": opp, "same_model": model == opp, "informed": informed, "condition": g["condition"],
                        "complete_game": comp, "n_rounds": g["n_valid_rounds"]}
                if g["n_valid_rounds"] >= 2:
                    brows.append({**base, **behaviour(g, key)})
                hrows.append({**base, **baseline_scores(g, key)})
    _w(rd / "games.csv", grows); _w(rd / "rounds.csv", rrows); _w(rd / "behavioral_metrics.csv", brows); _w(rd / "history_baselines.csv", hrows)
    V = cell_means(games)
    counts = Counter((g["p1_model"], g["p2_model"], g["condition"]) for g in games if g["status"] == "complete")
    planned = Counter((g["p1_model"], g["p2_model"], g["condition"]) for g in games)
    _w(rd / "cell_means.csv", [{"p1_model": i, "p2_model": j, "condition": c, "planned_games": planned[(i, j, c)],
                                "complete_games": counts[(i, j, c)], "V_p1_payoff": V[(i, j, c)],
                                "p2_payoff": None if V[(i, j, c)] is None else 1 - V[(i, j, c)]}
                               for i, j in C.PAIRINGS for c in C.COND_ORDER])
    ct = contrasts(V)
    ci = bootstrap(games)
    _w(rd / "primary_contrasts.csv", [{"contrast": k, "estimate": v, "ci_lo": ci[k]["lo"], "ci_hi": ci[k]["hi"],
                                       "undefined_boot_frac": ci[k]["undefined_frac"]} for k, v in ct.items()])
    _w(rd / "bootstrap.csv", [{"contrast": k, "n_boot": C.N_BOOT, "seed": C.ANALYSIS_SEED, **ci[k]} for k in ci])
    invalid = [{"slot_id": r["slot_id"], "model": r["model"], "status": r["status"], "reason": (r.get("parse") or {}).get("reason"),
                "text_tail": ((r.get("response") or {}).get("text") or "")[-300:]} for r in calls if not (r.get("parse") or {}).get("valid")]
    _w(rd / "invalids.csv", invalid)
    from .rescore import rescore
    rs = rescore(rd)
    out = {"V": {f"{i}|{j}|{c}": v for (i, j, c), v in V.items()}, "contrasts": ct, "ci": ci, "rescore": rs}
    (rd / "results.json").write_text(json.dumps(out, indent=1))
    write_report(rd, games, calls, V, counts, planned, ct, ci, brows, hrows, rs)
    files = sorted(p for p in rd.iterdir() if p.is_file() and p.name != "checksums.sha256")
    (rd / "checksums.sha256").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files))
    return out


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def write_report(rd, games, calls, V, counts, planned, ct, ci, brows, hrows, rs):
    cost = sum(float(r.get("cost_usd") or 0) for r in calls)
    sp = rd / "smoke_calls.jsonl"
    scost = sum(float(json.loads(l).get("cost_usd") or 0) for l in sp.read_text().splitlines() if l.strip()) if sp.exists() else 0.0
    prov = Counter((r["model"], r.get("returned_provider")) for r in calls if r["status"] == "completed")
    L = ["# RPS opponent identity disclosure: three-model factorial pilot", "",
         f"Run `{rd.name}`. Protocol {C.PROTOCOL}. Exploratory pilot (8 games per cell); unit of analysis = complete 20-round game.", "",
         "## Completion, cost and endpoint fidelity", "",
         f"- Games complete: {sum(1 for g in games if g['status'] == 'complete')} / {len(games)} planned ({C.N_GAMES}).",
         f"- Player calls recorded: {len(calls)} (planned {C.N_CALLS}); valid: {sum(1 for r in calls if (r.get('parse') or {}).get('valid'))}.",
         f"- Charged cost: ${cost:.2f} scientific + ${scost:.2f} smoke = ${cost + scost:.2f} (hard cap ${C.BUDGET_CAP_USD:.0f}).",
         f"- Returned providers: {dict(prov)}.", "",
         "| P1 \\ P2 | condition | complete / planned | V = P1 payoff |", "|---|---|---:|---:|"]
    for i, j in C.PAIRINGS:
        for c in C.COND_ORDER:
            L.append(f"| {i} vs {j} | {c} | {counts[(i, j, c)]}/{planned[(i, j, c)]} | {fmt(V[(i, j, c)])} |")
    def row(k, lab):
        c = ci[k]
        tag = " (unstable)" if c["undefined_frac"] > 0.01 else ""
        return f"| {lab} | {fmt(ct[k], 3, True)} | [{fmt(c['lo'], 3, True)}, {fmt(c['hi'], 3, True)}]{tag} |"
    L += ["", "## Primary: self-specific opponent-disclosure contrast D (payoff units; 1 = win, 0.5 = tie)", "",
          "| quantity | estimate | 95% game-level bootstrap interval |", "|---|---:|---|",
          row("D", "**D = mean(D_Astra, D_Fable, D_Qwen)**")]
    for i in J:
        L += [row(f"D[{i}]", f"D[{i}] = S - O"), row(f"S[{i}]", f"S[{i}] (same-model unilateral disclosure benefit)"),
              row(f"O[{i}]", f"O[{i}] (other-model unilateral disclosure benefit)")]
    L += ["", "Positive D: being told the opponent's true identity helps more when the opponent is the same model. Neither sign shows introspection; model-name priors remain possible explanations.", "",
          "## Unilateral and factorial components by ordered pairing", "",
          "| P1 vs P2 | U1 | U2 | U | P1 information effect | P2 information effect | interaction (P1 scale) |", "|---|---:|---:|---:|---:|---:|---:|"]
    for i, j in C.PAIRINGS:
        L.append(f"| {i} vs {j} | " + " | ".join(f"{fmt(ct[f'{k}[{i},{j}]'], 3, True)} [{fmt(ci[f'{k}[{i},{j}]']['lo'], 2, True)}, {fmt(ci[f'{k}[{i},{j}]']['hi'], 2, True)}]"
                                                    for k in ("U1", "U2", "U", "F1", "F2", "INT")) + " |")
    L += ["", "## Behaviour (means over seats; informed vs uninformed, by same/other-model opponent)", "",
          "| model | opponent | informed | n seats | %ROCK | %PAPER | %SCISSORS | switch % | win-stay % | lose-shift % | tie-shift % | entropy (bits) |",
          "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for m in J:
        for same in (True, False):
            for inf in (False, True):
                xs = [b for b in brows if b["model"] == m and b["same_model"] == same and b["informed"] == inf and b["complete_game"]]
                if not xs:
                    continue
                L.append(f"| {m} | {'same' if same else 'other'} | {inf} | {len(xs)} | " + " | ".join(
                    fmt(_mean([b[k] for b in xs]), 1) for k in ("pct_rock", "pct_paper", "pct_scissors", "switch_rate", "win_stay", "lose_shift", "tie_shift", "entropy_bits")) + " |")
    L += ["", "## Prospective history-only predictability (percent; uniform = 33.3)", "",
          "| model | informed | " + " | ".join(BASELINES) + " |", "|---|---|" + "---:|" * len(BASELINES)]
    for m in J:
        for inf in (False, True):
            xs = [h for h in hrows if h["model"] == m and h["informed"] == inf and h["complete_game"]]
            if xs:
                L.append(f"| {m} | {inf} | " + " | ".join(fmt(_mean([h[b] for h in xs]), 1) for b in BASELINES) + " |")
    L += ["", "## Independent rescore", "", f"`rescore.py` recomputed V and D from `rounds.csv` without the game-result routine: {json.dumps(rs)}", "",
          "## Interpretation boundaries", "",
          "- Exploratory: 8 games per cell; intervals reflect game-to-game variation within cells; no multiplicity correction across 36 cells.",
          "- Disclosure is always truthful. A self-specific effect is functional use of self-related information, not privileged introspection; model-name priors and skill differences remain alternatives.",
          "- 'Same model' means another independently queried instance with the same name and settings.", ""]
    (rd / "REPORT.md").write_text("\n".join(L) + "\n")
