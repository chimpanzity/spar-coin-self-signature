"""Analyses and figures (handoff sections 8 and 10).

Judgment accuracy is averaged first over the two orientations within a pair, then over the 20 pairs; invalid
answers are excluded from their pair's average (counts reported). Uncertainty: bootstrap over pairs, resampling
every judge, condition and orientation of a pair jointly. The 40 orientation presentations are never treated
as independent trials.
"""

from __future__ import annotations

import collections
import json
import os

import numpy as np

from spar_dynamic.dice_recognition import config as C, prompts as P

COL = {"qwen": "#2a78d6", "mistral": "#eb6834"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                         "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})
    return plt


# ---------------------------------------------------------------------------------------------- corpus --
def corpus_figures(stim, feats, cls, y_dev, fig_dir):
    plt = _plt()
    os.makedirs(fig_dir, exist_ok=True)
    disp = {k: C.MODELS[k]["display"] for k in C.SOURCES}
    # face histogram with per-sequence variability
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    for j, m in enumerate(C.SOURCES):
        P_ = np.array([[f[f"p{x}"] for x in range(1, 7)] for f, s in zip(feats, stim) if s["source"] == m])
        mu, sd = P_.mean(0), P_.std(0)
        ax.bar(np.arange(1, 7) - 0.2 + 0.4 * j, mu, width=0.38, color=COL[m], label=f"{disp[m]} (n={len(P_)})")
        ax.errorbar(np.arange(1, 7) - 0.2 + 0.4 * j, mu, yerr=sd, fmt="none", ecolor=INK2, lw=1, capsize=2)
    ax.axhline(1 / 6, color=INK2, ls=":", lw=1)
    ax.set_xlabel("face"); ax.set_ylabel("proportion within sequence (mean ± SD)")
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)
    ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(os.path.join(fig_dir, "face_histogram.png"), dpi=160); plt.close(fig)
    # per-position face frequencies
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2), sharey=True)
    for ax, m in zip(axes, C.SOURCES):
        S = np.array([[int(s[f"f{k}"]) for k in range(1, 11)] for s in stim if s["source"] == m])
        M = np.array([[np.mean(S[:, k] == f) for k in range(10)] for f in range(1, 7)])
        im = ax.imshow(M, cmap="Blues", vmin=0, vmax=max(0.5, M.max()), aspect="auto", origin="lower",
                       extent=(0.5, 10.5, 0.5, 6.5))
        for f in range(6):
            for k in range(10):
                ax.text(k + 1, f + 1, f"{M[f, k]:.2f}".lstrip("0"), ha="center", va="center", fontsize=6.5,
                        color="white" if M[f, k] > 0.3 else INK)
        ax.set_title(disp[m], fontsize=9, color=INK); ax.set_xlabel("position"); ax.set_xticks(range(1, 11))
    axes[0].set_ylabel("face")
    fig.colorbar(im, ax=axes, fraction=0.025, label="share of sequences")
    fig.savefig(os.path.join(fig_dir, "position_face_frequencies.png"), dpi=160, bbox_inches="tight"); plt.close(fig)
    # switch rate, max run, distinct faces
    fig, axes = plt.subplots(1, 3, figsize=(10, 3))
    for ax, key, bins in zip(axes, ("switch_frac", "max_run", "n_distinct"),
                             (np.linspace(0, 1, 11), np.arange(0.5, 6.5), np.arange(0.5, 7.5))):
        for m in C.SOURCES:
            v = [f[key] for f, s in zip(feats, stim) if s["source"] == m]
            ax.hist(v, bins=bins, alpha=0.55, color=COL[m], label=disp[m], edgecolor="white")
        ax.set_xlabel(key.replace("_", " ")); ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
    axes[0].set_ylabel("sequences"); axes[0].legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(fig_dir, "sequence_statistics.png"), dpi=160); plt.close(fig)
    # ROC of development CV
    from sklearn.metrics import roc_curve
    fpr, tpr, _ = roc_curve(y_dev, cls["oof_scores"])
    fig, ax = plt.subplots(figsize=(3.8, 3.6))
    ax.plot(fpr, tpr, color=INK, lw=2, label=f"grouped 5-fold CV, AUC {cls['cv_auc']:.2f}")
    ax.plot([0, 1], [0, 1], ":", color=INK2, lw=1)
    ax.set_xlabel("false positive rate (Mistral called Qwen)"); ax.set_ylabel("true positive rate (Qwen)")
    ax.set_title(f"Development classifier (gate {C.AUC_GATE})", fontsize=9, color=INK); ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout(); fig.savefig(os.path.join(fig_dir, "classifier_roc.png"), dpi=160); plt.close(fig)


# ------------------------------------------------------------------------------------------ judgments --
def pair_table(responses):
    """(judge, condition, pair) -> dict(acc over valid orientations, n_valid, chose_same_sequence, A choices)."""
    d = collections.defaultdict(list)
    for r in responses:
        d[(r["judge"], r["condition"], r["pair_id"])].append(r)
    out = {}
    for k, rs in d.items():
        v = [r for r in rs if r["valid"]]
        chosen = {r["orientation"]: (r["A_source"] if r["choice"] == "A" else r["B_source"]) for r in v}
        out[k] = dict(acc=float(np.mean([r["is_correct"] for r in v])) if v else None, n_valid=len(v),
                      consistent=(chosen.get("QA") == chosen.get("MA")) if len(chosen) == 2 else None,
                      n_A=sum(r["choice"] == "A" for r in v))
    return out


def summarise_judgments(responses, pairs, cls_pair_correct):
    pt = pair_table(responses)
    pids = [p["pair_id"] for p in pairs]

    def acc(judge, cond, sel=None):
        v = [pt[(judge, cond, p)]["acc"] for p in (sel or pids) if pt.get((judge, cond, p)) and pt[(judge, cond, p)]["acc"] is not None]
        return float(np.mean(v)) if v else float("nan")

    def stats(sel=None):
        s = {f"{j}|{c}": acc(j, c, sel) for j in C.SOURCES for c in P.CONDITIONS}
        s["own_model_advantage_named"] = 0.5 * ((s["qwen|named_qwen"] - s["mistral|named_qwen"])
                                                + (s["mistral|named_mistral"] - s["qwen|named_mistral"]))
        s["qwen_self_minus_named_own"] = s["qwen|self"] - s["qwen|named_qwen"]
        s["mistral_self_minus_named_own"] = s["mistral|self"] - s["mistral|named_mistral"]
        sel_ = sel or pids
        s["classifier_pair_accuracy"] = float(np.mean([cls_pair_correct[p] for p in sel_]))
        return s

    point = stats()
    rng = np.random.default_rng(C.BOOTSTRAP_SEED)
    boots = collections.defaultdict(list)
    for _ in range(C.N_BOOTSTRAP):
        sel = list(rng.choice(pids, size=len(pids), replace=True))
        for k, v in stats(sel).items():
            boots[k].append(v)
    ci = {k: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))] for k, v in boots.items()}
    per_cell = {}
    for j in C.SOURCES:
        for c in P.CONDITIONS:
            rs = [r for r in responses if r["judge"] == j and r["condition"] == c]
            v = [r for r in rs if r["valid"]]
            cons = [pt[(j, c, p)]["consistent"] for p in pids if pt[(j, c, p)]["consistent"] is not None]
            per_cell[f"{j}|{c}"] = dict(n_calls=len(rs), n_valid=len(v), A_rate=float(np.mean([r["choice"] == "A" for r in v])) if v else None,
                                       orientation_consistency=float(np.mean(cons)) if cons else None,
                                       raw_accuracy_all_presentations=float(np.mean([r["is_correct"] for r in v])) if v else None,
                                       confusion_truth_by_choice=_confusion(v))
    return dict(point=point, ci95_pair_bootstrap=ci, per_cell=per_cell, pair_table={"|".join(k): v for k, v in pt.items()})


def _confusion(v):
    c = collections.Counter((r["correct"], r["choice"]) for r in v)
    return {f"truth_{t}_chose_{ch}": c[(t, ch)] for t in "AB" for ch in "AB"}


def judgment_figures(summ, fig_dir):
    plt = _plt()
    os.makedirs(fig_dir, exist_ok=True)
    pt, ci = summ["point"], summ["ci95_pair_bootstrap"]
    labels = {"self": "self (own model)", "named_qwen": "named: Qwen3-32B", "named_mistral": "named: Mistral"}
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for j_i, j in enumerate(C.SOURCES):
        xs = np.arange(3) + (j_i - 0.5) * 0.36
        v = [pt[f"{j}|{c}"] for c in P.CONDITIONS]
        lo = [v[i] - ci[f"{j}|{c}"][0] for i, c in enumerate(P.CONDITIONS)]
        hi = [ci[f"{j}|{c}"][1] - v[i] for i, c in enumerate(P.CONDITIONS)]
        ax.bar(xs, v, width=0.34, color=COL[j], label=f"judge: {C.MODELS[j]['display']}")
        ax.errorbar(xs, v, yerr=[lo, hi], fmt="none", ecolor=INK2, lw=1, capsize=3)
    ax.axhline(0.5, color=INK2, ls=":", lw=1)
    ax.axhline(pt["classifier_pair_accuracy"], color=INK, ls="--", lw=1, label=f"external classifier ({pt['classifier_pair_accuracy']:.2f})")
    ax.set_xticks(range(3), [labels[c] for c in P.CONDITIONS]); ax.set_ylim(0, 1.05)
    ax.set_ylabel("pair-averaged accuracy (95% pair bootstrap)"); ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(os.path.join(fig_dir, "recognition_accuracy.png"), dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    for j_i, j in enumerate(C.SOURCES):
        v = [summ["per_cell"][f"{j}|{c}"]["orientation_consistency"] or 0 for c in P.CONDITIONS]
        ax.bar(np.arange(3) + (j_i - 0.5) * 0.36, v, width=0.34, color=COL[j], label=C.MODELS[j]["display"])
    ax.set_xticks(range(3), ["self", "named Qwen", "named Mistral"]); ax.set_ylim(0, 1.05)
    ax.set_ylabel("same sequence chosen in both orders"); ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(os.path.join(fig_dir, "orientation_consistency.png"), dpi=160); plt.close(fig)
