"""Study 1 Experiment 1: partial-game sensitivity (handoff 2026-10-10, Scoring). Derived analysis, not primary.

(1) Handoff-definition D on complete games: the frozen package contrasts() requires all four conditions (00/10/01/11)
for a pairing before computing U1/U2, but the handoff's U1, U2, S, O and D use only 00, 10 and 01. When an 11 cell is
empty this makes the frozen D NA although the handoff's D is defined. `handoff_contrasts` applies the handoff rule; the
bootstrap procedure, seed and resampling are the package's own.
(2) Partial-game sensitivity: recomputes V/U/S/O/D for each game type with every game that has >= 1 valid round, scoring an interrupted game by its
mean Player 1 payoff over the rounds it completed. Uses the same package contrast and bootstrap code (same seeds) as the
primary analysis. Reads game_logs.jsonl only; writes derived_contrasts.json/.csv next to it. Raw files untouched.

    python experiment1_sensitivity.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from opponent_disclosure_mp_3models import analysis as MP
from opponent_disclosure_rps_3models import analysis as RPS

RUNS = {"RPS": (RPS, Path("opponent_disclosure_rps_3models/results/rps3m-p2-20261010")),
        "MP": (MP, Path("opponent_disclosure_mp_3models/results/mp3m-p2-20261010"))}


def handoff_contrasts(A):
    def f(V):
        out = {}
        for i, j in A.C.PAIRINGS:
            V00, V10, V01 = (V.get((i, j, c)) for c in ("00", "10", "01"))
            out[f"U1[{i},{j}]"] = V10 - V00 if None not in (V10, V00) else None
            out[f"U2[{i},{j}]"] = V00 - V01 if None not in (V00, V01) else None
        Ds = []
        for i in A.J:
            j, k = [m for m in A.J if m != i]
            need = [out[f"U1[{i},{i}]"], out[f"U2[{i},{i}]"], out[f"U1[{i},{j}]"], out[f"U2[{j},{i}]"], out[f"U1[{i},{k}]"], out[f"U2[{k},{i}]"]]
            if None in need:
                out[f"S[{i}]"] = out[f"O[{i}]"] = out[f"D[{i}]"] = None; Ds.append(None); continue
            out[f"S[{i}]"] = (need[0] + need[1]) / 2
            out[f"O[{i}]"] = sum(need[2:]) / 4
            out[f"D[{i}]"] = out[f"S[{i}]"] - out[f"O[{i}]"]; Ds.append(out[f"D[{i}]"])
        out["D"] = sum(Ds) / 3 if None not in Ds else None
        return out
    return f


def _estimate(A, games, contrast_fn):
    orig = A.contrasts
    A.contrasts = contrast_fn                       # A.bootstrap looks up the module-level name
    try:
        ct, ci = contrast_fn(A.cell_means(games)), A.bootstrap(games)
    finally:
        A.contrasts = orig
    return ct, ci


def run(name):
    A, rd = RUNS[name]
    games = [json.loads(l) for l in (rd / "game_logs.jsonl").read_text().splitlines() if l.strip()]
    partial = [{**g, "status": "complete"} for g in games if g["n_valid_rounds"] >= 1]
    keys = ["D"] + [f"{q}[{m}]" for m in A.J for q in ("D", "S", "O")]
    rows = []
    for analysis, gs in (("handoff_D_complete_games", games), ("partial_games_handoff_D", partial)):
        ct, ci = _estimate(A, gs, handoff_contrasts(A))
        rows += [{"game": name, "analysis": analysis, "contrast": k, "estimate": ct[k], "ci_lo": ci[k]["lo"],
                  "ci_hi": ci[k]["hi"], "undefined_boot_frac": ci[k]["undefined_frac"]} for k in keys]
    out = {"game": name, "n_games_used": len(partial), "n_interrupted_included": sum(g["status"] != "complete" for g in games if g["n_valid_rounds"] >= 1),
           "n_games_total": len(games), "rows": rows}
    (rd / "derived_contrasts.json").write_text(json.dumps(out, indent=1))
    with open(rd / "derived_contrasts.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return out


if __name__ == "__main__":
    for n in RUNS:
        if (RUNS[n][1] / "game_logs.jsonl").exists():
            o = run(n)
            print(n, o["n_games_used"], "games used,", o["n_interrupted_included"], "interrupted included")
            for r in o["rows"]:
                f = lambda x: "NA" if x is None else f"{x:+.3f}"
                print(f"  {r['analysis']:<26} {r['contrast']:<9} {f(r['estimate'])} [{f(r['ci_lo'])}, {f(r['ci_hi'])}] undef {r['undefined_boot_frac']:.3f}")
