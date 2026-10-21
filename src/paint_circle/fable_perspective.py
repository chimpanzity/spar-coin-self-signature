"""2x2 summary for the Fable perspective-taking feasibility batch
(paint_circle/results/fable-perspective-20261021, plan.json "prespecified").

Cells (seat A only; B uninformed): self / other (false label) x guidance / none.
Per game, seat A: win, PI, shadow replay win (bench), exploitation gap
(win - bench), Brown-Rosenthal lag-1 coefficients, switch rate, P(TRIANGLE),
mean written tokens, cost. Contrasts: self_sim - other_sim, and the
interaction (self_sim - self_plain) - (other_sim - other_plain), with
session-level percentile bootstrap intervals (4,000 resamples, seed 20261021).
With 2 games per cell these are descriptive feasibility numbers only.

The older plain games from fable-specificity-20261021 (and earlier Fable
batches) are reported alongside as a separate cohort, never pooled.

Usage: python -m paint_circle.fable_perspective --out <dir>
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np

from paint_circle import analysis
import repo_paths  # reorganisation 2026-10-21: see src/repo_paths.py

BATCH = str(repo_paths.legacy("paint_circle/results/fable-perspective-20261021"))
HISTORIC = [str(repo_paths.legacy(b)) for b in [
    "paint_circle/results/pilot-20261020", "paint_circle/results/main-20261020",
    "paint_circle/results/fable-specificity-20261021"]]
CELLS = ["self+sim", "other+sim", "self", "other"]
METRICS = ["win", "pi", "bench", "gap", "br_opp1", "br_own1", "alt", "p_T", "tokens", "cost"]
N_BOOT, SEED = 4000, 20261021


def seat_a_rows(batches, cohort):
    rows = []
    for s in analysis.load_sessions(batches):
        if s["model_A"] != "fable" or s["model_B"] != "fable" or s["disclosure_B"] is not None:
            continue
        r = [x for x in analysis.session_rows(s) if x["seat"] == "A"][0]
        r["gap"] = r["win"] - r["bench"]
        r["cohort"] = cohort
        rpath = os.path.join(BATCH if cohort == "new" else _batch_dir(s), s["session_id"], "rounds.jsonl")
        toks = [json.loads(l)["response_A"]["completion_tokens"] for l in open(rpath, encoding="utf-8")]
        r["tokens"] = float(np.mean(toks))
        r["cost"] = s["cost"]
        rows.append(r)
    return rows


def _batch_dir(s):
    return str(repo_paths.legacy(os.path.join("paint_circle", "results", s["batch"])))


def boot(fn, groups, rng):
    vals = []
    for _ in range(N_BOOT):
        res = [g[rng.integers(0, len(g), len(g))] for g in groups]
        vals.append(fn(*res))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(SEED)

    new = seat_a_rows([BATCH], "new")
    old = [r for r in seat_a_rows(HISTORIC, "historic") if r["disclosure"] in ("self", "other")]
    by = {c: [r for r in new if r["disclosure"] == c] for c in CELLS}

    cells = {}
    for c in CELLS:
        cells[c] = dict(n=len(by[c]), sessions=[r["session_id"] for r in by[c]],
                        **{m: [round(r[m], 4) for r in by[c]] for m in METRICS},
                        **{f"{m}_mean": float(np.mean([r[m] for r in by[c]])) for m in METRICS})
    historic = {c: dict(n=len(rs), **{f"{m}_mean": float(np.mean([r[m] for r in rs])) for m in METRICS})
                for c in ("self", "other") for rs in [[r for r in old if r["disclosure"] == c]]}

    contrasts = []
    for m in ("win", "pi", "gap", "br_opp1", "tokens"):
        g = {c: np.array([r[m] for r in by[c]]) for c in CELLS}
        d1 = g["self+sim"].mean() - g["other+sim"].mean()
        contrasts.append(dict(metric=m, contrast="self_sim - other_sim", estimate=float(d1),
                              ci95=boot(lambda s, o: s.mean() - o.mean(), [g["self+sim"], g["other+sim"]], rng)))
        f = lambda ss, op, sp, oth: (ss.mean() - sp.mean()) - (op.mean() - oth.mean())
        args = [g["self+sim"], g["other+sim"], g["self"], g["other"]]
        contrasts.append(dict(metric=m, contrast="(self_sim - self_plain) - (other_sim - other_plain)",
                              estimate=float(f(*args)), ci95=boot(f, args, rng)))

    out = dict(status="feasibility, 2 games per cell; descriptive", cells=cells,
               historic_plain_cohort=historic, contrasts=contrasts)
    with open(os.path.join(a.out, "fable_perspective_2x2.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    analysis.write_csv(os.path.join(a.out, "fable_perspective_seatA_games.csv"), new + old)

    print(f"{'cell':10}{'n':>3}{'win':>7}{'PI':>7}{'bench':>7}{'gap':>7}{'opp1':>7}{'tokens':>8}{'cost':>7}")
    for c in CELLS:
        x = cells[c]
        print(f"{c:10}{x['n']:>3}{x['win_mean']:7.3f}{x['pi_mean']:7.3f}{x['bench_mean']:7.3f}{x['gap_mean']:7.3f}"
              f"{x['br_opp1_mean']:7.2f}{x['tokens_mean']:8.0f}{x['cost_mean']:7.2f}")
    for c, x in historic.items():
        print(f"{c + ' (old)':10}{x['n']:>3}{x['win_mean']:7.3f}{x['pi_mean']:7.3f}{x['bench_mean']:7.3f}{x['gap_mean']:7.3f}"
              f"{x['br_opp1_mean']:7.2f}{x['tokens_mean']:8.0f}{x['cost_mean']:7.2f}")
    for k in contrasts:
        print(f"{k['metric']:8}{k['contrast']:52}{k['estimate']:+8.3f}  [{k['ci95'][0]:+.3f}, {k['ci95'][1]:+.3f}]")


if __name__ == "__main__":
    main()
