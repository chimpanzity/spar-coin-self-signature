"""Experiment 20 analysis: NOISE_LABEL_REPLICATION_5SOURCES (handoff 2026-10-27).

Five independent noisy double-alternation scripts at epsilon = .10, each replayed
under five source labels (none / self / other / human / salmon): 25 Fable sessions.
Per session, rounds 1-100 and the primary window 51-100, the Experiment 19
measures (exploitation from entropy_gradient.py; prospective shadow-Proteus
exploitability, every logged forecast audited against an offline recomputation
via noise_label.round_rows). The replication unit is the script block: paired
within-block label differences, with mean / median / SD / range over the 5 blocks.

Writes into <batch_dir>/analysis/: session_summary.csv, round_metrics.csv,
paired_block_contrasts.csv, results.json, exploitation_by_label_paired.png,
predictability_by_label_paired.png, exploitation_vs_exploitability.png,
ten_round_trajectories.png. Exploratory: no confirmatory tests at n = 5 blocks.

Usage: python -m paint_circle.noise_label_rep <batch_dir>
"""

from __future__ import annotations

import collections
import csv
import json
import os
import sys

import numpy as np

from paint_circle import entropy_gradient, noise_label, scripted

LABELS = ["none", "self", "other", "human", "salmon"]
WINDOWS = {"full": (1, 100), "late": (51, 100)}
CONTRASTS = [("self", "other"), ("self", "none"), ("other", "none"), ("human", "none"), ("salmon", "none"),
             ("self", "human"), ("self", "salmon"), ("other", "human"), ("other", "salmon")]
METRICS = ["A_win", "A_minus_oracle", "EI_oracle_realized", "pattern_following", "PI_A_prospective", "shadow_activation"]


def summarise(batch_dir: str):
    plan = json.load(open(os.path.join(batch_dir, "plan.json"), encoding="utf-8"))
    rounds_all, summary, bins = [], [], {}
    for s in plan["sessions"]:
        p = os.path.join(batch_dir, s["session_id"], "rounds.jsonl")
        if not os.path.exists(p):
            continue
        rs = [json.loads(l) for l in open(p, encoding="utf-8")]
        phase, eps, seed = scripted.nda_parse(s["script_B"])
        paint = "".join(r["paint"] for r in rs)
        circle = "".join(r["circle"] for r in rs)
        assert circle == scripted.nda_sequence(phase, eps, seed)[:len(rs)], "B deviated from its frozen script"
        rows = noise_label.round_rows(s, rs)                    # includes the forecast audit
        for r in rows:
            r["block"] = s["block"]
        rounds_all += rows
        rej = os.path.join(batch_dir, s["session_id"], "rejected_attempts.jsonl")
        rej_rows = [json.loads(l) for l in open(rej, encoding="utf-8")] if os.path.exists(rej) else []
        g = entropy_gradient.gradient_metrics(paint, circle, scripted.nda_latent(phase)[:len(rs)])
        bins[s["session_id"]] = g["bins_A_win"]
        for win, (lo, hi) in WINDOWS.items():
            if hi > len(rs):
                continue
            w = rows[lo - 1:hi]
            pa = float(np.mean([x["p_actual"] for x in w]))
            m = g[win]
            summary.append(dict(
                tag=plan["tag"], session_id=s["session_id"], block=s["block"], label=s["label"], phase=phase, seed=seed,
                window=win, complete=len(rs) == s["rounds"], rounds=len(rs), calls_valid=len(rs), calls_rejected=len(rej_rows),
                cost_usd=round(sum(r["round_cost_usd"] for r in rs) + sum(x.get("cost_usd", 0) for x in rej_rows), 4),
                A_win=m["A_win"], oracle_win_realized=m["oracle_win_realized"], A_minus_oracle=m["A_minus_oracle"],
                EI_oracle_realized=m["EI_oracle_realized"], pattern_following=m["pattern_following"],
                PI_A_prospective=2 * (pa - 0.5), shadow_activation=float(np.mean([x["shadow_active"] for x in w])),
                logloss_shadow_bits=float(np.mean([x["logloss_bits"] for x in w])),
                logloss_marginal_bits=float(np.mean([x["logloss_marginal_bits"] for x in w])),
                PI_B=m["PI_B"], A_p_triangle=m["A_p_triangle"], A_switch_rate=m["A_switch_rate"], A_runs_z=m["A_runs_z"],
                A_win_stay=m["A_win_stay"], A_lose_shift=m["A_lose_shift"], A_follows_last_circle=m["A_follows_last_circle"],
                br_own1=m["br_own1"], br_opp1=m["br_opp1"],
                losses=m["losses"], losses_flip_induced=m["losses_flip_induced"], losses_A_deviation=m["losses_A_deviation"]))
    return plan, rounds_all, summary, bins


def paired_contrasts(summary, window="late"):
    idx = {(r["block"], r["label"]): r for r in summary if r["window"] == window and r["complete"]}
    blocks = sorted({b for b, _ in idx})
    rows, agg = [], []
    for a, b in CONTRASTS:
        for metric in METRICS:
            diffs = []
            for blk in blocks:
                ra, rb = idx.get((blk, a)), idx.get((blk, b))
                if ra is None or rb is None or ra[metric] is None or rb[metric] is None:
                    continue
                d = ra[metric] - rb[metric]
                diffs.append(d)
                rows.append(dict(window=window, contrast=f"{a} - {b}", metric=metric, block=blk, difference=d))
            if diffs:
                agg.append(dict(window=window, contrast=f"{a} - {b}", metric=metric, n_blocks=len(diffs),
                                mean=float(np.mean(diffs)), median=float(np.median(diffs)),
                                sd=float(np.std(diffs, ddof=1)) if len(diffs) > 1 else None,
                                min=float(min(diffs)), max=float(max(diffs)),
                                n_negative=sum(d < 0 for d in diffs), n_positive=sum(d > 0 for d in diffs),
                                per_block=[round(d, 4) for d in diffs]))
    return rows, agg


def main(batch_dir: str):
    plan, rounds_all, summary, bins = summarise(batch_dir)
    out = os.path.join(batch_dir, "analysis")
    os.makedirs(out, exist_ok=True)
    noise_label._csv(os.path.join(out, "round_metrics.csv"), rounds_all)
    noise_label._csv(os.path.join(out, "session_summary.csv"),
                     sorted(summary, key=lambda r: (r["window"], r["block"], LABELS.index(r["label"]))))
    rows, agg = [], []
    for win in WINDOWS:
        r, a = paired_contrasts(summary, win)
        rows += r
        agg += a
    noise_label._csv(os.path.join(out, "paired_block_contrasts.csv"), rows)
    by_label = {}
    for win in WINDOWS:
        for lab in LABELS:
            rs = [r for r in summary if r["window"] == win and r["label"] == lab and r["complete"]]
            if rs:
                by_label[f"{win}|{lab}"] = {m: dict(mean=float(np.mean([x[m] for x in rs if x[m] is not None])),
                                                    per_block=[round(x[m], 4) if x[m] is not None else None
                                                               for x in sorted(rs, key=lambda x: x["block"])])
                                            for m in METRICS}
    full = [r for r in summary if r["window"] == "full"]
    late = [r for r in summary if r["window"] == "late"]
    xs = np.array([r["A_minus_oracle"] for r in late]); ys = np.array([r["PI_A_prospective"] for r in late])
    results = dict(tag=plan["tag"], sessions_complete=sum(r["complete"] for r in full), sessions_planned=len(plan["sessions"]),
                   total_cost_usd=round(sum(r["cost_usd"] for r in full), 4),
                   calls_valid=sum(r["calls_valid"] for r in full), calls_rejected=sum(r["calls_rejected"] for r in full),
                   forecast_audit="every logged prospective forecast equals its offline recomputation",
                   r_exploitation_exploitability_late=float(np.corrcoef(xs, ys)[0, 1]) if len(late) > 2 else None,
                   by_label=by_label, paired_contrasts=agg, bins_A_win=bins, summary=summary)
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    _plots(summary, bins, out)
    return results


def _plots(summary, bins, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    late = [r for r in summary if r["window"] == "late" and r["complete"]]
    blocks = sorted({r["block"] for r in late})
    colors = {"none": "#555555", "self": "#d1495b", "other": "#00798c", "human": "#edae49", "salmon": "#8d6a9f"}
    xpos = {lab: i for i, lab in enumerate(LABELS)}

    def paired(metric, title, fname, ylabel):
        fig, ax = plt.subplots(figsize=(7, 4.4))
        for blk in blocks:
            pts = sorted([(xpos[r["label"]], r[metric]) for r in late if r["block"] == blk and r[metric] is not None])
            ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", color="#bbbbbb", lw=1)
            for x, y in pts:
                ax.scatter(x, y, color=colors[LABELS[x]], s=40, zorder=3)
            ax.annotate(f"script {blk}", (pts[-1][0], pts[-1][1]), fontsize=7, xytext=(5, 0), textcoords="offset points")
        means = [np.mean([r[metric] for r in late if r["label"] == lab and r[metric] is not None]) for lab in LABELS]
        ax.plot(range(len(LABELS)), means, "k_", ms=28, mew=2.5, label="mean of 5 scripts")
        ax.set_xticks(range(len(LABELS)), LABELS)
        ax.set_ylabel(ylabel); ax.set_title(title); ax.legend(fontsize=8)
        fig.tight_layout(); fig.savefig(os.path.join(out, fname), dpi=150); plt.close(fig)

    paired("A_win", "Fable win rate by source label, paired by script (rounds 51-100)", "exploitation_by_label_paired.png", "win rate")
    paired("PI_A_prospective", "Fable's own predictability (prospective PI_A), paired by script (rounds 51-100)",
           "predictability_by_label_paired.png", "PI_A")

    fig, ax = plt.subplots(figsize=(6, 5))
    for r in late:
        ax.scatter(r["A_minus_oracle"], r["PI_A_prospective"], color=colors[r["label"]], s=45, label=r["label"])
    h, l = ax.get_legend_handles_labels(); uniq = dict(zip(l, h))
    ax.legend(uniq.values(), uniq.keys(), fontsize=8)
    ax.axhline(0, color="grey", ls=":", lw=0.8)
    ax.set_xlabel("exploitation: Fable win - realized oracle (rounds 51-100)")
    ax.set_ylabel("exploitability: PI_A prospective (rounds 51-100)")
    ax.set_title("Exploitation vs exploitability, 25 sessions")
    fig.tight_layout(); fig.savefig(os.path.join(out, "exploitation_vs_exploitability.png"), dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    sid_label = {r["session_id"]: r["label"] for r in summary}
    for lab in LABELS:
        series = [v for k, v in bins.items() if sid_label.get(k) == lab and len(v) == 10]
        if series:
            ax.plot(np.arange(10) * 10 + 5, np.mean(series, axis=0), "o-", color=colors[lab], label=f"{lab} (mean of {len(series)})")
    ax.axhline(0.5, color="grey", ls=":", lw=0.8); ax.axvline(50.5, color="grey", lw=0.8)
    ax.set_xlabel("round (10-round bins)"); ax.set_ylabel("Fable win rate"); ax.set_ylim(0.2, 1.0)
    ax.set_title("10-round win-rate trajectories by source label"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(out, "ten_round_trajectories.png"), dpi=150); plt.close(fig)


if __name__ == "__main__":
    r = main(sys.argv[1])
    print(json.dumps({k: r[k] for k in ("sessions_complete", "sessions_planned", "total_cost_usd", "calls_valid", "calls_rejected",
                                        "r_exploitation_exploitability_late")}))
