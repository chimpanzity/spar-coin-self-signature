"""Prespecified Fable specificity analysis (plan.json "prespecified" block of
paint_circle/results/fable-specificity-20261021).

Primary: seat-A PI under self vs agent and self vs other (false label),
Welch t on session-level PI, Holm-adjusted across the two contrasts.
Secondary: each condition vs baseline; win, exploitation indices,
opponent lag-1 coefficient, self-reference rate.

Usage: python -m paint_circle.fable_specificity --out <dir>
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np

from paint_circle import analysis
import repo_paths  # reorganisation 2026-10-21: see src/repo_paths.py

BATCHES = [str(repo_paths.legacy(b)) for b in [
    "paint_circle/results/pilot-20261020", "paint_circle/results/main-20261020",
    "paint_circle/results/fable-specificity-20261021"]]
CONDITIONS = ["none", "self", "agent", "other"]
SECONDARY = ["win", "ei", "eff", "cond", "bench", "alt", "p_T", "br_opp1", "br_own1", "self_ref"]


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, running = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = running
    return adj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    sessions = [s for s in analysis.load_sessions(BATCHES)
                if s["model_A"] == "fable" and s["model_B"] == "fable" and s["disclosure_B"] is None]
    rows = [r for s in sessions for r in analysis.session_rows(s) if r["seat"] == "A"]
    by = {c: [r for r in rows if r["disclosure"] == c] for c in CONDITIONS}

    desc = {}
    for c, rs in by.items():
        desc[c] = dict(n=len(rs), sessions=[r["session_id"] for r in rs],
                       pi=[round(r["pi"], 4) for r in rs])
        for m in ["pi"] + SECONDARY:
            v = np.array([r[m] for r in rs], float)
            desc[c][f"{m}_mean"] = float(np.nanmean(v)) if len(v) else float("nan")
            desc[c][f"{m}_sd"] = float(np.nanstd(v, ddof=1)) if np.sum(~np.isnan(v)) > 1 else float("nan")

    primary = []
    for other in ("agent", "other"):
        d, p = analysis.welch([r["pi"] for r in by["self"]], [r["pi"] for r in by[other]])
        primary.append(dict(contrast=f"PI self - PI {other}", diff=d, p=p))
    for rec, p_adj in zip(primary, holm([r["p"] for r in primary])):
        rec["p_holm"] = p_adj

    secondary = []
    for c in ("self", "agent", "other"):
        for m in ["pi"] + SECONDARY:
            d, p = analysis.welch([r[m] for r in by[c]], [r[m] for r in by["none"]])
            secondary.append(dict(contrast=f"{c} - none", metric=m, diff=d, p=p))
    for other in ("agent", "other"):
        for m in SECONDARY:
            d, p = analysis.welch([r[m] for r in by["self"]], [r[m] for r in by[other]])
            secondary.append(dict(contrast=f"self - {other}", metric=m, diff=d, p=p))

    out = dict(descriptives=desc, primary=primary, secondary=secondary)
    with open(os.path.join(a.out, "fable_specificity.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    analysis.write_csv(os.path.join(a.out, "fable_seatA_sessions.csv"), rows)
    print(json.dumps(dict(n={c: d["n"] for c, d in desc.items()},
                          pi_mean={c: round(d["pi_mean"], 3) for c, d in desc.items()},
                          primary=primary), indent=2))


if __name__ == "__main__":
    main()
