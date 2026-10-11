"""Scoring for Blind Twin on Experiment 1 logs. Unit of resampling = game (within game type x ordered pairing).

Acc[gt, j, m, c]: percent of judge j's valid paired predictions of players of model m that are correct, under label c,
in game type gt. Equal weight over the 6 (seat x opponent-model) strata, then games, then rounds (Blind Twin v2
weighting extended to three models). T[j,m] = Acc TRUE - Acc ANONYMOUS; F[j,m] = Acc TRUE - Acc FALSE.
S = mean over target models m of ( T[m,m] - mean_{j != m} T[j,m] ): the truth benefit when the judge predicts its own
model, beyond other judges' truth benefit on that same model. With two models this equals Blind Twin v2's S.
S_false likewise with F. Primary: S per game type. Pooled S (mean of the two game types) is secondary.
"""
from __future__ import annotations

import csv
import hashlib
import importlib
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config as C
from .judge import load_games

SEATS = ("p1", "p2")
SEAT_KEY = {"p1": "player_1", "p2": "player_2"}


def prediction_rows(games, calls) -> List[Dict[str, Any]]:
    by = {g["gid"]: g for g in games}
    out = []
    for r in calls:
        if r.get("kind") != "judge":
            continue
        g = by[r["gid"]]
        actual = g["rounds"][r["round"] - 1]
        pred = (r.get("parse") or {}).get("prediction") if r["status"] == "completed" else None
        for s in SEATS:
            model = g[f"{s}_model"]
            out.append({"judge": r["judge"], "gid": r["gid"], "game_type": g["game_type"], "round": r["round"],
                        "condition": r["condition"], "seat": s, "seat_model": model,
                        "opponent_model": g["p2_model" if s == "p1" else "p1_model"],
                        "valid": pred is not None, "predicted": pred[SEAT_KEY[s]] if pred else None,
                        "actual": actual[s], "correct": int(pred is not None and pred[SEAT_KEY[s]] == actual[s])})
    return out


def paired_items(prows):
    by, meta = defaultdict(dict), {}
    for r in prows:
        if r["valid"]:
            k = (r["judge"], r["gid"], r["round"], r["seat"])
            by[k][r["condition"]] = r["correct"]
            meta[k] = r
    return {k: v for k, v in by.items() if len(v) == 3}, meta


def acc_table(items, meta, mult: Optional[Dict[str, int]] = None):
    """mult: game -> resample multiplicity (bootstrap); None = each game once."""
    cell = defaultdict(lambda: defaultdict(list))   # (gt, j, m, c, seat, opp) -> game -> [correct]
    for k, v in items.items():
        j, gid, t, seat = k
        m = meta[k]
        for c, x in v.items():
            cell[(m["game_type"], j, m["seat_model"], c, seat, m["opponent_model"])][gid].append(x)
    out = {}
    for gt in C.GAME_TYPES:
        for j in C.JUDGES:
            for m in C.ORDER:
                for c in C.CONDITIONS:
                    strata = []
                    for seat in SEATS:
                        for opp in C.ORDER:
                            gvals = []
                            for gid, xs in cell.get((gt, j, m, c, seat, opp), {}).items():
                                w = 1 if mult is None else mult.get(gid, 0)
                                gvals += [sum(xs) / len(xs)] * w
                            if gvals:
                                strata.append(sum(gvals) / len(gvals))
                    out[(gt, j, m, c)] = 100 * sum(strata) / len(strata) if len(strata) == 6 else None
    return out


def indices(acc) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    for gt in C.GAME_TYPES:
        for j in C.JUDGES:
            for m in C.ORDER:
                a, b, f = (acc.get((gt, j, m, c)) for c in ("TRUE", "ANONYMOUS", "FALSE"))
                out[f"{gt}:T[{j},{m}]"] = None if None in (a, b) else a - b
                out[f"{gt}:F[{j},{m}]"] = None if None in (a, f) else a - f
        for L, name in (("T", "S"), ("F", "S_false")):
            per = []
            for m in C.ORDER:
                own = out[f"{gt}:{L}[{m},{m}]"]
                oth = [out[f"{gt}:{L}[{j},{m}]"] for j in C.JUDGES if j != m]
                v = None if own is None or None in oth else own - sum(oth) / len(oth)
                out[f"{gt}:{name}[{m}]"] = v
                per.append(v)
            out[f"{gt}:{name}"] = None if None in per else sum(per) / len(per)
    for name in ("S", "S_false"):
        xs = [out[f"{gt}:{name}"] for gt in C.GAME_TYPES]
        out[f"pooled:{name}"] = None if None in xs else sum(xs) / len(xs)
    return out


def bootstrap(items, meta, games, n_boot=C.N_BOOT, seed=C.ANALYSIS_SEED):
    strata = defaultdict(list)
    for g in games:
        strata[(g["game_type"], g["p1_model"], g["p2_model"])].append(g["gid"])
    rng = random.Random(seed)
    reps, undefined, keys = defaultdict(list), defaultdict(int), None
    for _ in range(n_boot):
        mult = defaultdict(int)
        for gids in strata.values():
            for _ in gids:
                mult[gids[rng.randrange(len(gids))]] += 1
        ix = indices(acc_table(items, meta, mult))
        keys = ix.keys()
        for k, v in ix.items():
            if v is None:
                undefined[k] += 1
            else:
                reps[k].append(v)
    ci = {}
    for k in keys:
        v = sorted(reps[k])
        ci[k] = {"lo": v[int(0.025 * (len(v) - 1))] if v else None, "hi": v[int(0.975 * (len(v) - 1))] if v else None,
                 "undefined_frac": undefined[k] / n_boot}
    return ci


def baselines(games) -> List[Dict[str, Any]]:
    """History-only per-seat predictability from the Experiment 1 packages (fitted on prior rounds only)."""
    rows = []
    for g in games:
        A = importlib.import_module(f"{C.SOURCES[g['game_type']]['pkg']}.analysis")
        for s in SEATS:
            rows.append({"gid": g["gid"], "game_type": g["game_type"], "seat": s, "model": g[f"{s}_model"], **A.baseline_scores(g, s)})
    return rows


def _w(path, rows):
    if not rows:
        path.write_text(""); return
    keys = list(rows[0])
    for r in rows[1:]:
        keys += [k for k in r if k not in keys]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)


def fmt(x, nd=1, sign=False):
    return "NA" if x is None else (f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}")


def analyze(rd: Path) -> Dict[str, Any]:
    games = load_games()
    calls = [json.loads(l) for l in (rd / "calls.jsonl").read_text().splitlines() if l.strip()]
    prows = prediction_rows(games, calls)
    items, meta = paired_items(prows)
    acc = acc_table(items, meta)
    ix = indices(acc)
    ci = bootstrap(items, meta, games)
    base = baselines(games)
    _w(rd / "predictions.csv", prows)
    _w(rd / "accuracy.csv", [{"game_type": gt, "judge": j, "player_model": m, "condition": c, "acc_pct": acc[(gt, j, m, c)]}
                             for gt in C.GAME_TYPES for j in C.JUDGES for m in C.ORDER for c in C.CONDITIONS])
    _w(rd / "indices.csv", [{"index": k, "estimate": v, "ci_lo": ci[k]["lo"], "ci_hi": ci[k]["hi"],
                             "undefined_boot_frac": ci[k]["undefined_frac"], "n_boot": C.N_BOOT, "seed": C.ANALYSIS_SEED} for k, v in ix.items()])
    _w(rd / "baseline_scores.csv", base)
    inval = [{"slot_id": r["slot_id"], "judge": r["judge"], "status": r["status"], "reason": (r.get("parse") or {}).get("reason"),
              "text_tail": ((r.get("response") or {}).get("text") or "")[-300:]} for r in calls if not (r.get("parse") or {}).get("valid")]
    _w(rd / "invalids.csv", inval)
    # responsiveness: how often the prediction changes between labels for the same item
    byp = defaultdict(dict)
    for r in prows:
        if r["valid"]:
            byp[(r["judge"], r["gid"], r["round"], r["seat"])][r["condition"]] = r["predicted"]
    resp = []
    for gt in C.GAME_TYPES:
        for j in C.JUDGES:
            for a, b in (("TRUE", "ANONYMOUS"), ("TRUE", "FALSE"), ("FALSE", "ANONYMOUS")):
                ps = [v for k, v in byp.items() if k[0] == j and k[1].startswith(gt + ":") and a in v and b in v]
                resp.append({"game_type": gt, "judge": j, "comparison": f"{a} vs {b}", "n": len(ps),
                             "pct_differ": 100 * sum(p[a] != p[b] for p in ps) / len(ps) if ps else None})
    _w(rd / "responsiveness.csv", resp)
    out = {"indices": ix, "ci": ci, "acc": {"|".join(k): v for k, v in acc.items()},
           "n_paired_items": {j: sum(1 for k in items if k[0] == j) for j in C.JUDGES}}
    (rd / "results.json").write_text(json.dumps(out, indent=1))
    write_report(rd, games, calls, items, acc, ix, ci, base, resp)
    files = sorted(p for p in rd.iterdir() if p.is_file() and p.name != "checksums.sha256")
    (rd / "checksums.sha256").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files))
    return out


def write_report(rd, games, calls, items, acc, ix, ci, base, resp):
    cost = sum(float(r.get("cost_usd") or 0) for r in calls)
    valid = sum(1 for r in calls if (r.get("parse") or {}).get("valid"))
    L = ["# Blind Twin on Experiment 1 game logs (Experiment 2 pilot)", "",
         f"Run `{rd.name}`. Protocol {C.PROTOCOL}. Exploratory pilot. Judges Astra, Fable and Qwen predicted both players' next "
         "moves in the 36 Experiment 1 games where neither player was told its opponent's identity (18 RPS, 18 MP; 2 per ordered "
         "pairing), under TRUE, FALSE (fixed rotation Astra->Fable->Qwen->Astra) and ANONYMOUS identity labels.", "",
         "## Completion and cost", "",
         f"- Judge calls: {len(calls)} recorded of {C.N_CALLS} planned; valid predictions: {valid}.",
         f"- Paired items (valid under all three labels): {dict((j, sum(1 for k in items if k[0] == j)) for j in C.JUDGES)} "
         f"of {C.N_GAMES * C.N_ROUNDS * 2} per judge.",
         f"- Charged cost: ${cost:.2f} (hard cap ${C.BUDGET_CAP_USD:.0f}).", ""]

    def row(k, lab):
        c = ci[k]
        tag = " (unstable)" if c["undefined_frac"] > 0.01 else ""
        return f"| {lab} | {fmt(ix[k], 1, True)} | [{fmt(c['lo'], 1, True)}, {fmt(c['hi'], 1, True)}]{tag} |"
    L += ["## Identity indices (percentage points; 5,000 whole-game bootstrap resamples within game type x ordered pairing)", "",
          "| index | estimate | 95% interval |", "|---|---:|---|"]
    for gt, nm in (("rps", "RPS"), ("mp", "MP")):
        L += [row(f"{gt}:S", f"**{nm} S: self-specific truth benefit (TRUE vs ANONYMOUS), primary**"),
              row(f"{gt}:S_false", f"{nm} S_false: self-specific false-label cost (TRUE vs FALSE)")]
        L += [row(f"{gt}:S[{m}]", f"{nm} S[{m}]") for m in C.ORDER]
    L += [row("pooled:S", "Pooled S (mean of RPS and MP), secondary"), row("pooled:S_false", "Pooled S_false, secondary"), "",
          "Positive S: telling a judge the truth helps it predict players of its own model more than it helps other judges "
          "predict that model. This measures the functional value of identity information, not introspection.", ""]
    chance = {"rps": 33.3, "mp": 50.0}
    for gt, nm in (("rps", "RPS"), ("mp", "MP")):
        L += [f"## {nm} accuracy (percent; chance = {chance[gt]})", "",
              "| judge | predicted player model | TRUE | FALSE | ANONYMOUS | T (truth benefit) | F (false-label cost) |", "|---|---|---:|---:|---:|---:|---:|"]
        for j in C.JUDGES:
            for m in C.ORDER:
                L.append(f"| {j} | {m}{' (self)' if j == m else ''} | " + " | ".join(fmt(acc[(gt, j, m, c)]) for c in C.CONDITIONS)
                         + f" | {fmt(ix[f'{gt}:T[{j},{m}]'], 1, True)} | {fmt(ix[f'{gt}:F[{j},{m}]'], 1, True)} |")
        bl = [b for b in base if b["game_type"] == gt]
        names = [k for k in bl[0] if k not in ("gid", "game_type", "seat", "model")]
        L += ["", f"History-only baselines (percent of players' choices predicted, prior rounds only; {nm}):", "",
              "| player model | " + " | ".join(names) + " |", "|---|" + "---:|" * len(names)]
        for m in C.ORDER:
            xs = [b for b in bl if b["model"] == m]
            L.append(f"| {m} | " + " | ".join(fmt(sum(b[n] for b in xs) / len(xs)) for n in names) + " |")
        L.append("")
    L += ["## Responsiveness (percent of paired predictions that change between labels)", "",
          "| game | judge | TRUE vs ANONYMOUS | TRUE vs FALSE | FALSE vs ANONYMOUS |", "|---|---|---:|---:|---:|"]
    for gt in C.GAME_TYPES:
        for j in C.JUDGES:
            rs = {r["comparison"]: r["pct_differ"] for r in resp if r["game_type"] == gt and r["judge"] == j}
            L.append(f"| {gt} | {j} | {fmt(rs['TRUE vs ANONYMOUS'])} | {fmt(rs['TRUE vs FALSE'])} | {fmt(rs['FALSE vs ANONYMOUS'])} |")
    L += ["", "## Interpretation boundaries", "",
          "- Two games per ordered pairing: intervals reflect game-to-game variation and are wide or unstable; exploratory.",
          "- Game logs come from Experiment 1 (including make-up games for interrupted Qwen games; MP Qwen games carry the "
          "selection caveat in EXPERIMENT1_MAKEUP_GAMES.md, though condition-00 cells were least affected).",
          "- FALSE uses a fixed rotation, so a FALSE label can name the judge's own model for a different player (e.g. an "
          "Astra player labelled Fable for the Fable judge).", ""]
    (rd / "REPORT.md").write_text("\n".join(L) + "\n")
