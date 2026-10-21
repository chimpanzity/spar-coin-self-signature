"""Prespecified MP analysis (handoff 2026-10-10, Scoring). Unit = complete 20-round game; P1 = Matcher."""
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
# Behaviour and prospective baselines (no ties in MP)
# ---------------------------------------------------------------------------

ROLE_OF = {"p1": "Matcher", "p2": "Mismatcher"}


def _credit(pred, actual):
    s = set(C.MOVES) if pred is None else (set(pred) if isinstance(pred, tuple) else {pred})
    return (1 / len(s)) if actual in s else 0.0


def _argmax(d):
    m = max(d.values())
    top = tuple(sorted(k for k, v in d.items() if v == m))
    return top[0] if len(top) == 1 else top


def seat_rows(g, key):
    other = "p2" if key == "p1" else "p1"
    return [r[key] for r in g["rounds"]], [r[other] for r in g["rounds"]], [r["result"] for r in g["rounds"]], ROLE_OF[key]


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

    def cond_rate(win):
        idx = [t for t in range(n - 1) if (res[t] == me) == win]
        if not idx:
            return None
        same = sum(own[t + 1] == own[t] for t in idx)
        return 100 * (same if win else len(idx) - same) / len(idx)
    ent = -sum((v / n) * math.log2(v / n) for v in cnt.values())
    d = {f"pct_{m.lower()}": 100 * cnt[m] / n for m in C.MOVES}
    d.update({"switch_rate": 100 * sum(a != b for a, b in zip(own, own[1:])) / (n - 1), "longest_run": max(runs),
              "win_stay": cond_rate(True), "lose_shift": cond_rate(False), "entropy_bits": ent,
              "win_rate": 100 * sum(x == me for x in res) / n})
    for a in C.MOVES:
        for b in C.MOVES:
            d[f"T_{a[0]}{b[0]}"] = trans[(a, b)]
    return d


BASELINES = ("uniform", "expanding_frequency", "repeat_last", "markov1_smoothed", "best_response_opponent_last",
             "win_stay_lose_shift")


def baseline_scores(g, key) -> Dict[str, float]:
    """Percent of a player's choices predicted by history-only rules using rounds < t (chance = 50)."""
    own, opp, res, me = seat_rows(g, key)
    acc = {b: [] for b in BASELINES}
    for t in range(len(own)):
        a = own[t]
        acc["uniform"].append(0.5)
        if t == 0:
            for b in BASELINES[1:]:
                acc[b].append(0.5)
            continue
        past = own[:t]
        acc["expanding_frequency"].append(_credit(_argmax({m: past.count(m) for m in C.MOVES}), a))
        acc["repeat_last"].append(_credit(past[-1], a))
        nxt = [y for x, y in zip(past, past[1:]) if x == past[-1]]
        acc["markov1_smoothed"].append(_credit(_argmax({m: nxt.count(m) + 1 for m in C.MOVES}), a))
        # Matcher's best response to "opponent repeats" is to copy it; Mismatcher's is the other shape
        acc["best_response_opponent_last"].append(_credit(opp[t - 1] if me == "Matcher" else C.OTHER[opp[t - 1]], a))
        acc["win_stay_lose_shift"].append(_credit(past[-1] if res[t - 1] == me else C.OTHER[past[-1]], a))
    return {b: 100 * sum(v) / len(v) for b, v in acc.items()}


def conditional_choice(games, n_boot=1000, seed=C.ANALYSIS_SEED + 1):
    """Pooled Brown-Rosenthal-style conditional choice: P(repeat own last shape | won / lost last round), by model x
    role x informed, pooled over complete games with a game-clustered bootstrap. A per-game multi-lag regression is not
    identified on 19 transitions and is not fitted."""
    cells = defaultdict(list)          # (model, role, informed) -> per game [(won_last, repeated)]
    for g in games:
        if g["status"] != "complete":
            continue
        for key, model, inf in (("p1", g["p1_model"], g["p1_informed"]), ("p2", g["p2_model"], g["p2_informed"])):
            own, opp, res, me = seat_rows(g, key)
            cells[(model, me, inf)].append([(res[t] == me, own[t + 1] == own[t]) for t in range(len(own) - 1)])
    rng = random.Random(seed)
    out = []
    for (m, role, inf), gl in sorted(cells.items()):
        def rates(sample):
            w = [r for gg in sample for won, r in gg if won]
            l = [r for gg in sample for won, r in gg if not won]
            return (100 * sum(w) / len(w) if w else None, 100 * sum(l) / len(l) if l else None)
        est = rates(gl)
        bs = [rates([gl[rng.randrange(len(gl))] for _ in gl]) for _ in range(n_boot)]
        row = {"model": m, "role": role, "informed": inf, "n_games": len(gl),
               "n_after_win": sum(won for gg in gl for won, _ in gg), "n_after_loss": sum(not won for gg in gl for won, _ in gg),
               "p_repeat_after_win": est[0], "p_repeat_after_loss": est[1]}
        for k, nm in ((0, "after_win"), (1, "after_loss")):
            v = sorted(b[k] for b in bs if b[k] is not None)
            row[f"lo_{nm}"], row[f"hi_{nm}"] = (v[int(0.025 * (len(v) - 1))], v[int(0.975 * (len(v) - 1))]) if v else (None, None)
        out.append(row)
    return out


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


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def analyze(rd: Path) -> Dict[str, Any]:
    games = [json.loads(l) for l in (rd / "game_logs.jsonl").read_text().splitlines() if l.strip()]
    calls = [json.loads(l) for l in (rd / "calls.jsonl").read_text().splitlines() if l.strip()]
    grows, rrows, brows, hrows = [], [], [], []
    for g in games:
        comp = g["status"] == "complete"
        grows.append({"game_id": g["game_id"], "pairing": f"{g['p1_model']}-{g['p2_model']}", "matcher_model": g["p1_model"],
                      "mismatcher_model": g["p2_model"], "p1_model": g["p1_model"], "p2_model": g["p2_model"],
                      "condition": g["condition"], "replicate": g["replicate"], "status": g["status"],
                      "n_valid_rounds": g["n_valid_rounds"], "note": g["note"],
                      "p1_payoff": game_p1_payoff(g) if g["rounds"] else None,
                      "matcher_wins": sum(r["result"] == "Matcher" for r in g["rounds"]),
                      "mismatcher_wins": sum(r["result"] == "Mismatcher" for r in g["rounds"])})
        for r in g["rounds"]:
            rrows.append({"game_id": g["game_id"], "p1_model": g["p1_model"], "p2_model": g["p2_model"], "condition": g["condition"],
                          "complete_game": comp, **r, "p1_payoff": payoff_p1(r["result"])})
        if g["rounds"]:
            for key, model, informed, opp in (("p1", g["p1_model"], g["p1_informed"], g["p2_model"]),
                                              ("p2", g["p2_model"], g["p2_informed"], g["p1_model"])):
                base = {"game_id": g["game_id"], "seat": "Player 1" if key == "p1" else "Player 2", "role": ROLE_OF[key],
                        "model": model, "opponent": opp, "same_model": model == opp, "informed": informed,
                        "condition": g["condition"], "complete_game": comp, "n_rounds": g["n_valid_rounds"]}
                if g["n_valid_rounds"] >= 2:
                    brows.append({**base, **behaviour(g, key)})
                hrows.append({**base, **baseline_scores(g, key)})
    _w(rd / "games.csv", grows); _w(rd / "rounds.csv", rrows); _w(rd / "behavioral_metrics.csv", brows)
    _w(rd / "baseline_predictions.csv", hrows)
    cc = conditional_choice(games)
    _w(rd / "conditional_choice.csv", cc)
    V = cell_means(games)
    counts = Counter((g["p1_model"], g["p2_model"], g["condition"]) for g in games if g["status"] == "complete")
    planned = Counter((g["p1_model"], g["p2_model"], g["condition"]) for g in games)
    _w(rd / "cell_means.csv", [{"p1_model": i, "p2_model": j, "condition": c, "planned_games": planned[(i, j, c)],
                                "complete_games": counts[(i, j, c)], "V_matcher_payoff": V[(i, j, c)],
                                "mismatcher_payoff": None if V[(i, j, c)] is None else 1 - V[(i, j, c)]}
                               for i, j in C.PAIRINGS for c in C.COND_ORDER])
    ct = contrasts(V)
    ci = bootstrap(games)
    _w(rd / "primary_contrasts.csv", [{"contrast": k, "estimate": v, "ci_lo": ci[k]["lo"], "ci_hi": ci[k]["hi"],
                                       "undefined_boot_frac": ci[k]["undefined_frac"]} for k, v in ct.items()])
    _w(rd / "bootstrap_intervals.csv", [{"contrast": k, "n_boot": C.N_BOOT, "seed": C.ANALYSIS_SEED, **ci[k]} for k in ci])
    invalid = [{"slot_id": r["slot_id"], "model": r["model"], "status": r["status"], "reason": (r.get("parse") or {}).get("reason"),
                "text_tail": ((r.get("response") or {}).get("text") or "")[-300:]} for r in calls if not (r.get("parse") or {}).get("valid")]
    _w(rd / "invalids.csv", invalid)
    from .rescore import rescore
    rs = rescore(rd)
    out = {"V": {f"{i}|{j}|{c}": v for (i, j, c), v in V.items()}, "contrasts": ct, "ci": ci, "rescore": rs}
    (rd / "results.json").write_text(json.dumps(out, indent=1))
    write_report(rd, games, calls, V, counts, planned, ct, ci, brows, hrows, cc, rs)
    files = sorted(p for p in rd.iterdir() if p.is_file() and p.name != "checksums.sha256")
    (rd / "checksums.sha256").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files))
    return out


def write_report(rd, games, calls, V, counts, planned, ct, ci, brows, hrows, cc, rs):
    cost = sum(float(r.get("cost_usd") or 0) for r in calls)
    sp = rd / "smoke_calls.jsonl"
    scost = sum(float(json.loads(l).get("cost_usd") or 0) for l in sp.read_text().splitlines() if l.strip()) if sp.exists() else 0.0
    prov = Counter((r["model"], r.get("returned_provider")) for r in calls if r["status"] == "completed")
    L = ["# Matching-pennies opponent identity disclosure: three-model factorial pilot", "",
         f"Run `{rd.name}`. Protocol {C.PROTOCOL}. Exploratory pilot ({C.REPLICATES} games per cell); Player 1 = Matcher, "
         "Player 2 = Mismatcher; unit of analysis = complete 20-round game. Not pooled with RPS or the Astra-only MP pilot.", "",
         "## Completion, cost and endpoint fidelity", "",
         f"- Games complete: {sum(1 for g in games if g['status'] == 'complete')} / {len(games)} planned ({C.N_GAMES}).",
         f"- Player calls recorded: {len(calls)} (planned {C.N_CALLS}); valid: {sum(1 for r in calls if (r.get('parse') or {}).get('valid'))}.",
         f"- Charged cost: ${cost:.2f} scientific + ${scost:.2f} smoke = ${cost + scost:.2f} (hard cap ${C.BUDGET_CAP_USD:.0f}).",
         f"- Returned providers: {dict(prov)}.", "",
         "| Matcher (P1) vs Mismatcher (P2) | condition | complete / planned | V = Matcher payoff |", "|---|---|---:|---:|"]
    for i, j in C.PAIRINGS:
        for c in C.COND_ORDER:
            L.append(f"| {i} vs {j} | {c} | {counts[(i, j, c)]}/{planned[(i, j, c)]} | {fmt(V[(i, j, c)])} |")

    def row(k, lab):
        c = ci[k]
        tag = " (unstable)" if c["undefined_frac"] > 0.01 else ""
        return f"| {lab} | {fmt(ct[k], 3, True)} | [{fmt(c['lo'], 3, True)}, {fmt(c['hi'], 3, True)}]{tag} |"
    L += ["", "## Primary: self-specific opponent-disclosure contrast D (payoff units; 1 = win, 0 = loss)", "",
          "| quantity | estimate | 95% game-level bootstrap interval |", "|---|---:|---|",
          row("D", "**D = mean(D_Astra, D_Fable, D_Qwen)**")]
    for i in J:
        L += [row(f"D[{i}]", f"D[{i}] = S - O"), row(f"S[{i}]", f"S[{i}] (same-model unilateral disclosure benefit)"),
              row(f"O[{i}]", f"O[{i}] (other-model unilateral disclosure benefit)")]
    L += ["", "Positive D: being told the opponent's true identity helps more when the opponent is the same model. "
          "U1 is a Matcher-seat effect and U2 a Mismatcher-seat effect, so S and O each average both roles.", "",
          "## Unilateral and factorial components by ordered pairing", "",
          "| Matcher vs Mismatcher | U1 | U2 | U | Matcher information effect | Mismatcher information effect | interaction (Matcher scale) |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    for i, j in C.PAIRINGS:
        L.append(f"| {i} vs {j} | " + " | ".join(f"{fmt(ct[f'{k}[{i},{j}]'], 3, True)} [{fmt(ci[f'{k}[{i},{j}]']['lo'], 2, True)}, {fmt(ci[f'{k}[{i},{j}]']['hi'], 2, True)}]"
                                                    for k in ("U1", "U2", "U", "F1", "F2", "INT")) + " |")
    L += ["", "## Behaviour by model x role (complete games; informed vs uninformed, same/other-model opponent)", "",
          "| model | role | opponent | informed | n seats | win % | %STAR | switch % | win-stay % | lose-shift % | longest run | entropy (bits) |",
          "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for m in J:
        for role in ("Matcher", "Mismatcher"):
            for same in (True, False):
                for inf in (False, True):
                    xs = [b for b in brows if b["model"] == m and b["role"] == role and b["same_model"] == same and b["informed"] == inf and b["complete_game"]]
                    if xs:
                        L.append(f"| {m} | {role} | {'same' if same else 'other'} | {inf} | {len(xs)} | " + " | ".join(
                            fmt(_mean([b[k] for b in xs]), 1) for k in ("win_rate", "pct_star", "switch_rate", "win_stay", "lose_shift", "longest_run", "entropy_bits")) + " |")
    L += ["", "## Prospective history-only predictability / exploitability (percent of choices; chance = 50)", "",
          "| model | role | informed | " + " | ".join(BASELINES) + " |", "|---|---|---|" + "---:|" * len(BASELINES)]
    for m in J:
        for role in ("Matcher", "Mismatcher"):
            for inf in (False, True):
                xs = [h for h in hrows if h["model"] == m and h["role"] == role and h["informed"] == inf and h["complete_game"]]
                if xs:
                    L.append(f"| {m} | {role} | {inf} | " + " | ".join(fmt(_mean([h[b] for h in xs]), 1) for b in BASELINES) + " |")
    L += ["", "## Conditional choice (pooled, game-clustered bootstrap; Brown-Rosenthal-style, descriptive)", "",
          "A per-game multi-lag regression is not identified on 19 transitions per player; this pools transitions within "
          "model x role x informed and resamples whole games. Cells with few games or few post-loss rounds are unstable.", "",
          "| model | role | informed | games | P(repeat after win) % | P(repeat after loss) % |", "|---|---|---|---:|---:|---:|"]
    for r in cc:
        L.append(f"| {r['model']} | {r['role']} | {r['informed']} | {r['n_games']} | {fmt(r['p_repeat_after_win'], 1)} "
                 f"[{fmt(r['lo_after_win'], 0)}, {fmt(r['hi_after_win'], 0)}] (n={r['n_after_win']}) | {fmt(r['p_repeat_after_loss'], 1)} "
                 f"[{fmt(r['lo_after_loss'], 0)}, {fmt(r['hi_after_loss'], 0)}] (n={r['n_after_loss']}) |")
    L += ["", "## Independent rescore", "", f"`rescore.py` recomputed V and D from `rounds.csv` without the game-result routine: {json.dumps(rs)}", "",
          "## Interpretation boundaries", "",
          f"- Feasibility pilot: {C.REPLICATES} games per cell; intervals reflect game-to-game variation within cells, are often "
          "unstable, and are neither confirmation nor evidence of absence. No multiplicity correction across 36 cells.",
          "- Disclosure is always truthful. A self-specific effect is functional use of self-related information, not privileged "
          "introspection; model-name priors and skill differences remain alternatives.",
          "- 'Same model' means another independently queried instance with the same name and settings.", ""]
    (rd / "REPORT.md").write_text("\n".join(L) + "\n")
