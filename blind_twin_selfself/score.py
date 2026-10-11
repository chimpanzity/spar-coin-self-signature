"""Scoring for the Blind Twin self-self 00-vs-11 pilot. Unit of resampling = game (within game type x model x condition).

Acc[gt, cond, j, m, label]: percent of judge j's valid paired predictions of model m's players (self-self games of
model m, game condition cond) that are correct under the label. Equal weight over the two seats, then games, then rounds.
T = TRUE - ANONYMOUS, F = TRUE - FALSE, within a game condition.
Delta[gt, j, m] = T[11] - T[00]: does truthful identity help the observer more when the players themselves knew?
Delta_self = mean_m Delta[m, m]; Delta_other = mean_m mean_{j != m} Delta[j, m]; primary per game type:
Delta_selfspec = Delta_self - Delta_other. Same three with F (DeltaF_*). Pooled (mean of game types) is secondary.
Also S_cond = mean_m (T[m,m] - mean_{j!=m} T[j,m]) within each condition (Blind Twin S restricted to self-self games).
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
CONDS = C.SOURCE_CONDITIONS


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
            out.append({"judge": r["judge"], "gid": r["gid"], "game_type": g["game_type"], "game_condition": g["condition"],
                        "round": r["round"], "label": r["condition"], "seat": s, "model": g["p1_model"],
                        "valid": pred is not None, "predicted": pred[SEAT_KEY[s]] if pred else None, "actual": actual[s],
                        "correct": int(pred is not None and pred[SEAT_KEY[s]] == actual[s])})
    return out


def paired_items(prows):
    by, meta = defaultdict(dict), {}
    for r in prows:
        if r["valid"]:
            k = (r["judge"], r["gid"], r["round"], r["seat"])
            by[k][r["label"]] = r["correct"]
            meta[k] = r
    return {k: v for k, v in by.items() if len(v) == 3}, meta


def acc_table(items, meta, mult: Optional[Dict[str, int]] = None):
    cell = defaultdict(lambda: defaultdict(list))     # (gt, cond, j, m, label, seat) -> gid -> [correct]
    for k, v in items.items():
        j, gid, t, seat = k
        m = meta[k]
        for lab, x in v.items():
            cell[(m["game_type"], m["game_condition"], j, m["model"], lab, seat)][gid].append(x)
    out = {}
    for gt in C.GAME_TYPES:
        for cond in CONDS:
            for j in C.JUDGES:
                for m in C.ORDER:
                    for lab in C.CONDITIONS:
                        strata = []
                        for seat in SEATS:
                            gvals = []
                            for gid, xs in cell.get((gt, cond, j, m, lab, seat), {}).items():
                                w = 1 if mult is None else mult.get(gid, 0)
                                gvals += [sum(xs) / len(xs)] * w
                            if gvals:
                                strata.append(sum(gvals) / len(gvals))
                        out[(gt, cond, j, m, lab)] = 100 * sum(strata) / len(strata) if len(strata) == 2 else None
    return out


def _mean(xs):
    return None if any(x is None for x in xs) else sum(xs) / len(xs)


def indices(acc) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    for gt in C.GAME_TYPES:
        for cond in CONDS:
            for j in C.JUDGES:
                for m in C.ORDER:
                    a, b, f = (acc.get((gt, cond, j, m, lab)) for lab in ("TRUE", "ANONYMOUS", "FALSE"))
                    out[f"{gt}:{cond}:T[{j},{m}]"] = None if None in (a, b) else a - b
                    out[f"{gt}:{cond}:F[{j},{m}]"] = None if None in (a, f) else a - f
            for L, nm in (("T", "S"), ("F", "S_false")):
                out[f"{gt}:{cond}:{nm}"] = _mean([None if out[f"{gt}:{cond}:{L}[{m},{m}]"] is None else
                                                  _sub(out[f"{gt}:{cond}:{L}[{m},{m}]"], _mean([out[f"{gt}:{cond}:{L}[{j},{m}]"] for j in C.JUDGES if j != m]))
                                                  for m in C.ORDER])
        for L, nm in (("T", "Delta"), ("F", "DeltaF")):
            for j in C.JUDGES:
                for m in C.ORDER:
                    out[f"{gt}:{nm}[{j},{m}]"] = _sub(out[f"{gt}:11:{L}[{j},{m}]"], out[f"{gt}:00:{L}[{j},{m}]"])
            self_ = _mean([out[f"{gt}:{nm}[{m},{m}]"] for m in C.ORDER])
            other = _mean([_mean([out[f"{gt}:{nm}[{j},{m}]"] for j in C.JUDGES if j != m]) for m in C.ORDER])
            out[f"{gt}:{nm}_self"], out[f"{gt}:{nm}_other"], out[f"{gt}:{nm}_selfspec"] = self_, other, _sub(self_, other)
    for k in ("Delta_self", "Delta_other", "Delta_selfspec", "DeltaF_self", "DeltaF_other", "DeltaF_selfspec"):
        out[f"pooled:{k}"] = _mean([out[f"{gt}:{k}"] for gt in C.GAME_TYPES])
    return out


def _sub(a, b):
    return None if a is None or b is None else a - b


def bootstrap(items, meta, games, n_boot=C.N_BOOT, seed=C.ANALYSIS_SEED):
    strata = defaultdict(list)
    for g in games:
        strata[(g["game_type"], g["p1_model"], g["condition"])].append(g["gid"])
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
    """External history-only classifiers (Experiment 1 package rules, prior rounds only) on the same games."""
    rows = []
    for g in games:
        A = importlib.import_module(f"{C.SOURCES[g['game_type']]['pkg']}.analysis")
        for s in SEATS:
            sc = A.baseline_scores(g, s)
            rows.append({"gid": g["gid"], "game_type": g["game_type"], "game_condition": g["condition"], "seat": s,
                         "model": g["p1_model"], **sc, "best_rule": max(v for k, v in sc.items() if k != "uniform")})
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
    _w(rd / "accuracy.csv", [{"game_type": k[0], "game_condition": k[1], "judge": k[2], "player_model": k[3], "label": k[4], "acc_pct": v}
                             for k, v in acc.items()])
    _w(rd / "indices.csv", [{"index": k, "estimate": v, "ci_lo": ci[k]["lo"], "ci_hi": ci[k]["hi"],
                             "undefined_boot_frac": ci[k]["undefined_frac"], "n_boot": C.N_BOOT, "seed": C.ANALYSIS_SEED} for k, v in ix.items()])
    _w(rd / "baseline_scores.csv", base)
    _w(rd / "invalids.csv", [{"slot_id": r["slot_id"], "judge": r["judge"], "status": r["status"], "reason": (r.get("parse") or {}).get("reason"),
                              "text_tail": ((r.get("response") or {}).get("text") or "")[-300:]} for r in calls if not (r.get("parse") or {}).get("valid")])
    out = {"indices": ix, "ci": ci, "acc": {"|".join(k): v for k, v in acc.items()},
           "n_paired_items": {j: sum(1 for k in items if k[0] == j) for j in C.JUDGES}}
    (rd / "results.json").write_text(json.dumps(out, indent=1))
    write_report(rd, calls, items, acc, ix, ci, base)
    files = sorted(p for p in rd.iterdir() if p.is_file() and p.name != "checksums.sha256")
    (rd / "checksums.sha256").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files))
    return out


def write_report(rd, calls, items, acc, ix, ci, base):
    cost = sum(float(r.get("cost_usd") or 0) for r in calls)
    valid = sum(1 for r in calls if (r.get("parse") or {}).get("valid"))
    L = ["# Blind Twin self-self pilot: does truthful identity help observers more when the players knew?", "",
         f"Run `{rd.name}`. Protocol {C.PROTOCOL}. Exploratory pilot. Judges Astra, Fable and Qwen predicted both players' "
         "moves in the 24 Experiment 1 self-self games (each model vs itself; condition 00 = neither told, 11 = both told; "
         "RPS and MP; 2 games per cell) under TRUE, FALSE and ANONYMOUS labels. Every prompt states, without naming a model, "
         "what the players were told.", "",
         "## Completion and cost", "",
         f"- Judge calls: {len(calls)} recorded of {C.N_CALLS} planned; valid predictions: {valid}.",
         f"- Paired items (valid under all three labels): {dict((j, sum(1 for k in items if k[0] == j)) for j in C.JUDGES)} "
         f"of {C.N_GAMES * C.N_ROUNDS * 2} per judge.",
         f"- Charged cost: ${cost:.2f} (hard cap ${C.BUDGET_CAP_USD:.0f}).", ""]

    def row(k, lab):
        c = ci[k]
        tag = " (unstable)" if c["undefined_frac"] > 0.01 else ""
        return f"| {lab} | {fmt(ix[k], 1, True)} | [{fmt(c['lo'], 1, True)}, {fmt(c['hi'], 1, True)}]{tag} |"
    L += ["## Interaction indices (percentage points; 5,000 whole-game bootstrap resamples within game type x model x condition)", "",
          "Delta = (TRUE - ANONYMOUS in 11 games) - (TRUE - ANONYMOUS in 00 games). Self: judge predicts its own model. "
          "Other: judges predict a different model. Self-specific = self - other (primary, per game type).", "",
          "| index | estimate | 95% interval |", "|---|---:|---|"]
    for gt, nm in (("rps", "RPS"), ("mp", "MP")):
        L += [row(f"{gt}:Delta_selfspec", f"**{nm} Delta self-specific (primary)**"), row(f"{gt}:Delta_self", f"{nm} Delta self"),
              row(f"{gt}:Delta_other", f"{nm} Delta other"), row(f"{gt}:DeltaF_selfspec", f"{nm} DeltaF self-specific (TRUE vs FALSE)")]
        L += [row(f"{gt}:Delta[{m},{m}]", f"{nm} Delta[{m} judging {m}]") for m in C.ORDER]
        L += [row(f"{gt}:{cond}:S", f"{nm} S within condition {cond}") for cond in CONDS]
    L += [row("pooled:Delta_selfspec", "Pooled Delta self-specific, secondary"), row("pooled:DeltaF_selfspec", "Pooled DeltaF self-specific, secondary"), ""]
    chance = {"rps": 33.3, "mp": 50.0}
    for gt, nm in (("rps", "RPS"), ("mp", "MP")):
        L += [f"## {nm} accuracy (percent; chance = {chance[gt]})", "",
              "| judge | player model | 00 TRUE | 00 FALSE | 00 ANON | 11 TRUE | 11 FALSE | 11 ANON | T00 | T11 | Delta |",
              "|---|---|" + "---:|" * 9]
        for j in C.JUDGES:
            for m in C.ORDER:
                L.append(f"| {j} | {m}{' (self)' if j == m else ''} | " + " | ".join(fmt(acc[(gt, c, j, m, lab)]) for c in CONDS for lab in C.CONDITIONS)
                         + f" | {fmt(ix[f'{gt}:00:T[{j},{m}]'], 1, True)} | {fmt(ix[f'{gt}:11:T[{j},{m}]'], 1, True)} | {fmt(ix[f'{gt}:Delta[{j},{m}]'], 1, True)} |")
        cols = [k for k in next(b for b in base if b["game_type"] == gt) if k not in ("gid", "game_type", "game_condition", "seat", "model")]
        L += ["", f"External history-only classifiers on the same {nm} games (percent of choices predicted; best_rule = best "
              "single rule per player-game, optimistic):", "", "| player model | condition | " + " | ".join(cols) + " |",
              "|---|---|" + "---:|" * len(cols)]
        for m in C.ORDER:
            for cond in CONDS:
                xs = [b for b in base if b["game_type"] == gt and b["model"] == m and b["game_condition"] == cond]
                L.append(f"| {m} | {cond} | " + " | ".join(fmt(sum(b[k] for b in xs) / len(xs)) for k in cols) + " |")
        L.append("")
    L += ["## Interpretation boundaries", "",
          "- Pilot: 2 games per (game type, model, condition); each judge x label x cell has 80 predictions. Delta is a "
          "difference of differences, so intervals are wide. Not a test of privileged access.",
          "- The 00 self-self games were judged before (BlindTwinExp1_v1) without the player-information sentence; they are "
          "re-judged here so both conditions share one prompt. The earlier run is not pooled with this one.",
          "- MP Qwen self-self games include make-ups (QQ_00_1_MU2, QQ_11_1_MU6) with the condition-dependent selection "
          "caveat in EXPERIMENT1_MAKEUP_GAMES.md.",
          "- A positive Delta_self can reflect generic behaviour change under mutual disclosure; Delta_other is the control.", ""]
    (rd / "REPORT.md").write_text("\n".join(L) + "\n")
