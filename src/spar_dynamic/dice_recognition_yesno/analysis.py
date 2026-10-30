"""Offline summaries, comparisons and figures for LOULA_DICE_YESNO_LOGPROB v3.0. No GPU or network.

Units are items (calibration) and pair ids (recognition); the four prompts of a unit are never treated as independent
observations. The recognition AUC uses one value per sequence, u = (z_pos - z_neg) / 2, over all 20 x 20 Qwen-Mistral
combinations (descriptive; 40 sequences). Deterministic forward passes are not resampled.
"""

from __future__ import annotations

import collections
import csv
import json

import numpy as np

from spar_dynamic.dice_recognition_logprob import analysis as A24
from spar_dynamic.dice_recognition_v2 import synthetic as S
from spar_dynamic.dice_recognition_yesno import config as C

jsonl, write_csv, fmt_ci, _corr = A24.jsonl, A24.write_csv, A24.fmt_ci, A24._corr
COL, INK, INK2, GRID, BAND = A24.COL, A24.INK, A24.INK2, A24.GRID, A24.BAND
TASK_LABEL = A24.TASK_LABEL
KIND_LABEL = {"AUTH": "AUTH\n(your model?)", "TYP": "TYP\n(typical of you?)"}


def bootstrap_mean(values):
    return A24.bootstrap_mean(values, seed=C.BOOTSTRAP_SEED, n=C.BOOTSTRAP_N)


def describe(rows, eps):
    s = [r["S"] for r in rows]
    return dict(n=len(rows), favors_X=sum(r["outcome"] == "X" for r in rows), favors_Y=sum(r["outcome"] == "Y" for r in rows),
                indeterminate=sum(r["outcome"] == "indeterminate" for r in rows),
                both_polarities_X=sum(r["both_polarities_X"] for r in rows),
                both_polarities_Y=sum(r["both_polarities_Y"] for r in rows),
                polarity_sensitive=sum(r["polarity_sensitive"] for r in rows),
                mean_S=bootstrap_mean(s), median_S=float(np.median(s)), min_S=float(min(s)), max_S=float(max(s)),
                mean_c_pos=float(np.mean([r["c_pos"] for r in rows])), mean_c_neg=float(np.mean([r["c_neg"] for r in rows])),
                mean_yes_bias_pos=float(np.mean([r["yes_bias_pos"] for r in rows])),
                mean_yes_bias_neg=float(np.mean([r["yes_bias_neg"] for r in rows])),
                mean_coherence=float(np.mean([r["coherence"] for r in rows])),
                mass_YN_min=float(min(r["mass_YN_min"] for r in rows)),
                greedy_yes_rate=float(np.mean([r[k] for r in rows for k in ("greedy_yes_X_pos", "greedy_yes_Y_pos",
                                                                              "greedy_yes_X_neg", "greedy_yes_Y_neg")])),
                greedy_separates_pos=sum(r["greedy_yes_X_pos"] and not r["greedy_yes_Y_pos"] for r in rows),
                greedy_separates_neg=sum(r["greedy_yes_Y_neg"] and not r["greedy_yes_X_neg"] for r in rows),
                epsilon=eps)


# ------------------------------------------------------------------------------------- calibration --
def exp24_by_task():
    """Experiment 24 (A/B, both orders) per task, on its own (Experiment 23) items: historical, not paired."""
    g = json.load(open(C.SOURCES["exp24_calibration_gate"], encoding="utf-8"))
    rows = list(csv.DictReader(open(C.SOURCES["exp24_paired_scores"], encoding="utf-8")))
    out = {}
    for t in C.TASKS:
        rs = [r for r in rows if r["kind"] == t]
        out[t] = dict(correct=g["per_task"][t]["correct"], both_orders_correct=g["per_task"][t]["both_orders_correct"],
                      mean_S=float(np.mean([float(r["S_X"]) for r in rs])),
                      mean_B_pair=float(np.mean([float(r["B_pair"]) for r in rs])))
    out["overall"] = dict(correct=g["total_correct"], both_orders_correct=g["both_orders_correct"],
                          mean_S=float(np.mean([float(r["S_X"]) for r in rows])),
                          mean_B_pair=float(np.mean([float(r["B_pair"]) for r in rows])))
    return out


def _by_diff(rows, task):
    f = S.n_sixes if task == "MORE_SIXES" else S.n_repeats
    out = collections.defaultdict(list)
    for r in rows:
        if r["kind"] == task:
            out[f([int(x) for x in r["X"].split()]) - f([int(x) for x in r["Y"].split()])].append(r["S"])
    return {str(d): dict(n=len(s), mean_S=float(np.mean(s)), min_S=float(min(s))) for d, s in sorted(out.items())}


def calibration_summary(rows, gate):
    eps = gate["epsilon"]
    return dict(per_task={t: describe([r for r in rows if r["kind"] == t], eps) for t in C.TASKS},
                overall=describe(rows, eps), gate=gate, exp24=exp24_by_task(),
                S_by_count_difference={t: _by_diff(rows, t) for t in C.TASKS})


# ------------------------------------------------------------------------------------- recognition --
def auc(pos, neg):
    """P(a random Qwen value > a random Mistral value), ties counting one half."""
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    return float(((pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()) / (len(pos) * len(neg)))


def screen_summary(rows, pairs, eps):
    margins = A24.classifier_margins(pairs, C.SOURCES["classifier_gate"])
    out = dict(epsilon=eps, n_pairs=len({r["unit_id"] for r in rows}), per_kind={}, auc={})
    by = {(r["kind"], r["unit_id"]): r for r in rows}
    pids = sorted({r["unit_id"] for r in rows})
    for k in C.FRAMES:
        rs = [r for r in rows if r["kind"] == k]
        out["per_kind"][k] = describe(rs, eps)
        u_q = [0.5 * (r["z_X_pos"] - r["z_X_neg"]) for r in rs]
        u_m = [0.5 * (r["z_Y_pos"] - r["z_Y_neg"]) for r in rs]
        out["auc"][k] = dict(polarity_averaged=auc(u_q, u_m), pos_only=auc([r["z_X_pos"] for r in rs], [r["z_Y_pos"] for r in rs]),
                             neg_only=auc([-r["z_X_neg"] for r in rs], [-r["z_Y_neg"] for r in rs]), n_qwen=len(u_q), n_mistral=len(u_m))
        det = [p for p in pids if abs(by[k, p]["S"]) > eps and margins[p] != 0]
        out["per_kind"][k]["classifier"] = dict(
            n_determinate=len(det), agree_with_classifier_sign=sum((by[k, p]["S"] > 0) == (margins[p] > 0) for p in det),
            corr_S_with_classifier_margin=_corr([by[k, p]["S"] for p in pids], [margins[p] for p in pids]))
    out["AUTH_minus_TYP"] = bootstrap_mean([by["AUTH", p]["S"] - by["TYP", p]["S"] for p in pids])
    out["corr_AUTH_TYP"] = _corr([by["AUTH", p]["S"] for p in pids], [by["TYP", p]["S"] for p in pids])
    out["classifier"] = dict(pairs_classifier_correct=sum(m > 0 for m in margins.values()),
                             pairs_classifier_tied=sum(m == 0 for m in margins.values()), margins=margins)
    out["by_pair"] = {p: dict(AUTH=by["AUTH", p]["S"], TYP=by["TYP", p]["S"], classifier_margin=margins[p]) for p in pids}
    return out


# ----------------------------------------------------------------------------------------- figures --
def fig_strip(rows, kinds, labels, eps, path, title, ylabel):
    A24.fig_strip([dict(r, S_X=r["S"]) for r in rows], kinds, labels, eps, path, title, ylabel)


def fig_polarities(rows, kinds, labels, eps, path, title, xlabel, ylabel):
    """c_pos vs c_neg per unit. Upper right: X preferred under both questions; a constant Yes bias cannot move a point."""
    plt = A24._plt()
    fig, ax = plt.subplots(figsize=(4.8, 4.4))
    lim = max([abs(r[c]) for r in rows for c in ("c_pos", "c_neg")] + [1.0]) * 1.08
    ax.axvspan(-eps, eps, color=BAND, zorder=0)
    ax.axhspan(-eps, eps, color=BAND, zorder=0)
    ax.plot([-lim, lim], [-lim, lim], color=INK2, lw=0.8, ls=":", zorder=1)
    ax.axhline(0, color=INK2, lw=0.6)
    ax.axvline(0, color=INK2, lw=0.6)
    for k in kinds:
        rs = [r for r in rows if r["kind"] == k]
        ax.scatter([r["c_pos"] for r in rs], [r["c_neg"] for r in rs], s=30, color=COL[k], edgecolor="white",
                   linewidth=1.1, label=labels[k].replace("\n", " "), zorder=3)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.text(0.98, 0.98, "X preferred under\nboth questions", transform=ax.transAxes, ha="right", va="top", fontsize=7, color=INK2)
    ax.text(0.02, 0.02, "Y preferred under\nboth questions", transform=ax.transAxes, ha="left", va="bottom", fontsize=7, color=INK2)
    ax.text(0.02, 0.98, "more Yes to Y\nwhatever the question", transform=ax.transAxes, ha="left", va="top", fontsize=7, color=INK2)
    ax.text(0.98, 0.02, "more Yes to X\nwhatever the question", transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color=INK2)
    ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3)
    ax.set_title(title, fontsize=9, color=INK, loc="left")
    A24._save(fig, path)
