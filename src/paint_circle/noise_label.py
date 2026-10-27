"""Experiment 19 analysis: NOISE_LABEL_PREDICTABILITY_PILOT (handoff 2026-10-27).

Fable paints against one frozen noisy double-alternation sequence per noise level
(epsilon .10/.15/.20), replayed under three source labels (none / self / other LLM).
Two outcomes per session, on rounds 1-100 and the primary window 51-100:

  Exploitation (entropy_gradient.py, unchanged): A_win, realized latent-phase oracle,
    A - oracle, EI_oracle_realized (NA if oracle <= .55), pattern_following.
  Exploitability: the PROSPECTIVE shadow Proteus forecast logged each round before
    Fable's answer was scored (same last-50 completed rounds Fable saw, A's own
    choices and A-win bits). PI_A = 2 * (mean forecast prob of Fable's actual choice - .5),
    activation, mean log2 loss, and a rolling-marginal (Laplace, same window) baseline.
    Each logged forecast is checked against an offline recomputation.

Writes into <batch_dir>/analysis/: session_summary.csv, round_metrics.csv,
results.json, exploitation_by_noise.png, predictability_by_noise.png,
exploitation_vs_exploitability.png. Descriptive only: one session per cell.

Usage: python -m paint_circle.noise_label <batch_dir>
"""

from __future__ import annotations

import collections
import csv
import json
import math
import os
import sys

import numpy as np

from paint_circle import entropy_gradient, scripted, shadow

WINDOWS = {"full": (1, 100), "late": (51, 100)}
LABELS = ["none", "self", "other"]


def _clip(p):
    return min(max(p, 1e-3), 1 - 1e-3)


def round_rows(s: dict, rs: list) -> list:
    paint = "".join(r["paint"] for r in rs)
    circle = "".join(r["circle"] for r in rs)
    phase, eps, seed = scripted.nda_parse(s["script_B"])
    latent = scripted.nda_latent(phase)
    a_w = shadow.wins_string(paint, circle, matcher=True)
    out = []
    for t, r in enumerate(rs):
        f = r["shadow_forecast_A"]
        off = shadow.forecast(paint[:t], a_w[:t], s["window"])            # audit: offline recomputation
        assert abs(off.p_triangle - f["p_triangle"]) < 1e-12 and off.active == f["active"], \
            f"{s['session_id']} round {t+1}: logged forecast differs from recomputation"
        p_actual = f["p_triangle"] if r["paint"] == "T" else 1 - f["p_triangle"]
        past = paint[max(0, t - s["window"]):t]
        pm = (past.count(r["paint"]) + 1) / (len(past) + 2)
        out.append(dict(session_id=s["session_id"], epsilon=eps, label=s["label"], phase=phase, seed=seed,
                        round=t + 1, paint=r["paint"], circle=r["circle"], latent=latent[t],
                        script_flipped=int(r["circle"] != latent[t]), a_win=int(r["a_wins"]),
                        history_window_sha=f["window_sha"], window_rounds=f["window_rounds"],
                        shadow_p_triangle=round(f["p_triangle"], 6), shadow_active=int(f["active"]),
                        shadow_n_active=f["n_active"], shadow_channel=f["channel"],
                        p_actual=round(p_actual, 6), logloss_bits=round(-math.log2(_clip(p_actual)), 6),
                        marginal_p_actual=round(pm, 6), logloss_marginal_bits=round(-math.log2(pm), 6),
                        cost_usd=r["round_cost_usd"]))
    return out


def main(batch_dir: str):
    plan = json.load(open(os.path.join(batch_dir, "plan.json"), encoding="utf-8"))
    all_rounds, summary = [], []
    for s in plan["sessions"]:
        p = os.path.join(batch_dir, s["session_id"], "rounds.jsonl")
        if not os.path.exists(p):
            continue
        rs = [json.loads(l) for l in open(p, encoding="utf-8")]
        complete = len(rs) == s["rounds"]
        phase, eps, seed = scripted.nda_parse(s["script_B"])
        paint = "".join(r["paint"] for r in rs)
        circle = "".join(r["circle"] for r in rs)
        assert circle == scripted.nda_sequence(phase, eps, seed)[:len(rs)], "B deviated from its frozen script"
        rows = round_rows(s, rs)
        all_rounds += rows
        rej = os.path.join(batch_dir, s["session_id"], "rejected_attempts.jsonl")
        rej_rows = [json.loads(l) for l in open(rej, encoding="utf-8")] if os.path.exists(rej) else []
        g = entropy_gradient.gradient_metrics(paint, circle, scripted.nda_latent(phase)[:len(rs)])
        for win, (lo, hi) in WINDOWS.items():
            if hi > len(rs):
                continue
            w = rows[lo - 1:hi]
            pa = float(np.mean([x["p_actual"] for x in w]))
            m = g[win]
            summary.append(dict(
                tag=plan["tag"], session_id=s["session_id"], epsilon=eps, label=s["label"], phase=phase, seed=seed,
                window=win, complete=complete, rounds=len(rs),
                calls_valid=len(rs), calls_rejected=len(rej_rows),
                rejected_rate_limit=sum(1 for x in rej_rows if "429" in str(x.get("error", ""))),
                cost_usd=round(sum(r["round_cost_usd"] for r in rs) + sum(x.get("cost_usd", 0) for x in rej_rows), 4),
                A_win=m["A_win"], oracle_win_realized=m["oracle_win_realized"], A_minus_oracle=m["A_minus_oracle"],
                EI_oracle_realized=m["EI_oracle_realized"], pattern_following=m["pattern_following"],
                PI_A_prospective=2 * (pa - 0.5), shadow_mean_p_actual=pa,
                shadow_activation=float(np.mean([x["shadow_active"] for x in w])),
                logloss_shadow_bits=float(np.mean([x["logloss_bits"] for x in w])),
                logloss_marginal_bits=float(np.mean([x["logloss_marginal_bits"] for x in w])),
                PI_B=m["PI_B"], A_p_triangle=m["A_p_triangle"], A_switch_rate=m["A_switch_rate"], A_runs_z=m["A_runs_z"],
                A_win_stay=m["A_win_stay"], A_lose_shift=m["A_lose_shift"], A_follows_last_circle=m["A_follows_last_circle"],
                br_own1=m["br_own1"], br_opp1=m["br_opp1"],
                losses=m["losses"], losses_flip_induced=m["losses_flip_induced"], losses_A_deviation=m["losses_A_deviation"]))
    out = os.path.join(batch_dir, "analysis")
    os.makedirs(out, exist_ok=True)
    _csv(os.path.join(out, "round_metrics.csv"), all_rounds)
    _csv(os.path.join(out, "session_summary.csv"), sorted(summary, key=lambda r: (r["window"], r["epsilon"], LABELS.index(r["label"]))))
    # self - other descriptive contrasts (and each label vs none)
    idx = {(r["epsilon"], r["label"], r["window"]): r for r in summary}
    contrasts = []
    for (eps, lab, win), r in sorted(idx.items()):
        if lab != "self":
            continue
        o, n = idx.get((eps, "other", win)), idx.get((eps, "none", win))
        for metric in ("A_win", "A_minus_oracle", "pattern_following", "PI_A_prospective", "shadow_activation"):
            contrasts.append(dict(epsilon=eps, window=win, metric=metric,
                                  self_minus_other=(r[metric] - o[metric]) if o else None,
                                  self_minus_none=(r[metric] - n[metric]) if n else None,
                                  other_minus_none=(o[metric] - n[metric]) if (o and n) else None))
    full = [r for r in summary if r["window"] == "full"]
    results = dict(tag=plan["tag"], windows=WINDOWS, sessions_complete=sum(r["complete"] for r in full),
                   sessions_planned=len(plan["sessions"]), total_cost_usd=round(sum(r["cost_usd"] for r in full), 4),
                   calls_valid=sum(r["calls_valid"] for r in full), calls_rejected=sum(r["calls_rejected"] for r in full),
                   forecast_audit="every logged prospective forecast equals its offline recomputation",
                   summary=summary, contrasts=contrasts)
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    _plots(summary, out)
    return results


def _csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: ("NA" if v is None else (round(v, 4) if isinstance(v, float) else v)) for k, v in r.items()})


def _plots(summary, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = {"none": "#555555", "self": "#d1495b", "other": "#00798c"}
    eps_all = sorted({r["epsilon"] for r in summary})
    late = [r for r in summary if r["window"] == "late"]

    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for lab in LABELS:
        rs = sorted([r for r in late if r["label"] == lab], key=lambda r: r["epsilon"])
        ax.plot([r["epsilon"] for r in rs], [r["A_win"] for r in rs], "o-", color=colors[lab], label=f"Fable win, label: {lab}")
    orc = {r["epsilon"]: r["oracle_win_realized"] for r in late}
    ax.plot(eps_all, [orc[e] for e in eps_all], "s--", color="k", label="latent-phase oracle (realized)")
    ax.axhline(0.5, color="grey", ls=":", lw=0.8)
    ax.set_xlabel("noise epsilon"); ax.set_ylabel("win rate, rounds 51-100"); ax.set_ylim(0.3, 1.0)
    ax.set_title("Exploitation by noise and source label"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(out, "exploitation_by_noise.png"), dpi=150); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for lab in LABELS:
        rs = sorted([r for r in late if r["label"] == lab], key=lambda r: r["epsilon"])
        e = [r["epsilon"] for r in rs]
        axes[0].plot(e, [r["PI_A_prospective"] for r in rs], "o-", color=colors[lab], label=lab)
        axes[1].plot(e, [r["shadow_activation"] for r in rs], "o-", color=colors[lab], label=lab)
    axes[0].set_title("PI_A (prospective shadow Proteus), rounds 51-100"); axes[0].axhline(0, color="grey", ls=":", lw=0.8)
    axes[1].set_title("shadow activation rate, rounds 51-100")
    for a in axes:
        a.set_xlabel("noise epsilon"); a.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(out, "predictability_by_noise.png"), dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5))
    markers = {0.1: "o", 0.15: "s", 0.2: "^"}
    for r in late:
        ax.scatter(r["A_minus_oracle"], r["PI_A_prospective"], color=colors[r["label"]], marker=markers.get(r["epsilon"], "o"), s=70)
        ax.annotate(f"{r['label']} e{r['epsilon']:.2f}", (r["A_minus_oracle"], r["PI_A_prospective"]), fontsize=7,
                    xytext=(4, 3), textcoords="offset points")
    ax.axvline(0, color="grey", ls=":", lw=0.8); ax.axhline(0, color="grey", ls=":", lw=0.8)
    ax.set_xlabel("exploitation: Fable win - realized oracle (rounds 51-100)")
    ax.set_ylabel("exploitability: PI_A prospective (rounds 51-100)")
    ax.set_title("Exploitation vs exploitability, 9 sessions")
    fig.tight_layout(); fig.savefig(os.path.join(out, "exploitation_vs_exploitability.png"), dpi=150); plt.close(fig)


if __name__ == "__main__":
    r = main(sys.argv[1])
    print(json.dumps({k: r[k] for k in ("sessions_complete", "sessions_planned", "total_cost_usd", "calls_valid", "calls_rejected")}))
