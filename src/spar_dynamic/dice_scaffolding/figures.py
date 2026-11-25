"""Figures for Experiment 33 (PNG + PDF)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from spar_dynamic.dice_scaffolding import config as C
from spar_dynamic.dice_scaffolding import design as D

LAB = {"qwen": "Qwen3-32B", "mistral": "Mistral Small 3.2"}
COL = {"qwen": "#2a6fb0", "mistral": "#c4562b"}


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
    return plt


def _save(fig, out, name):
    out.mkdir(parents=True, exist_ok=True)
    for e in ("png", "pdf"):
        fig.savefig(out / f"{name}.{e}", dpi=200, bbox_inches="tight")
    _plt().close(fig)


def vectors(data, out):
    """Direct (G) and forecast (F) six-face vectors after 5 2 6 and at roll 7 of each archived greedy path."""
    from spar_dynamic.dice_scaffolding.analysis import CK
    plt = _plt()
    fig, axs = plt.subplots(2, 3, figsize=(11, 5), sharex=True, sharey=True)
    bars = (("direct G", "0.2", None), ("F: a shape", "0.65", C.NEUTRAL), ("F: blue", "#2a6fb0", D.subject_word("blue")), ("F: orange", "#e08a1e", D.subject_word("orange")))
    for i, m in enumerate(C.MODELS):
        for j, h in enumerate(C.WORKED):
            hs, ax = D.seq(h), axs[i, j]
            for k, (lab, col, s) in enumerate(bars):
                v = data.GT[(m, hs)] if s is None else data.F[(m, CK(s), hs)]
                ax.bar(np.arange(1, 7) + (k - 1.5) * 0.2, v, 0.18, color=col, label=lab)
            ax.set_title(f"{LAB[m]}, after {hs} (roll {len(h) + 1})", loc="left", fontsize=8.5)
            ax.set_xticks(range(1, 7))
            if j == 0:
                ax.set_ylabel("probability (six faces)")
            if i == 1:
                ax.set_xlabel("next face")
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    _save(fig, out, "fig33_vectors")


def primary(res, out):
    plt = _plt()
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.8), gridspec_kw=dict(width_ratios=[1, 1.5, 1.3]))
    P = res["core"]["primary"]
    ax = axs[0]
    for x, n in enumerate(("qwen", "mistral", "joint")):
        for dx, e, mk in ((-0.12, "T", "o"), (0.12, "O", "s")):
            s = P[f"{n}_{e}"]
            if "ci95" in s:
                ax.plot([x + dx] * 2, s["ci95"], color=COL.get(n, "0.2"), lw=1.2)
            ax.plot(x + dx, s["mean"], mk, color=COL.get(n, "0.2"), mfc="white" if e == "O" else COL.get(n, "0.2"), ms=7)
    ax.axhline(0, color="0.6", lw=0.8)
    ax.set_xticks(range(3))
    ax.set_xticklabels(["Qwen", "Mistral", "joint"])
    ax.set_ylabel("bits (JS)")
    ax.set_title("A. Primary: association test (filled),\nown improvement (open)", loc="left", fontsize=9)
    ax = axs[1]
    pr = res["core"]["pairs_primary"]
    labs = [f"{l}/{r}" for l, r in C.CONF_PAIRS]
    for dx, m in ((-0.17, "qwen"), (0.17, "mistral")):
        rr = [x for x in pr if x["checkpoint"] == m]
        ax.bar(np.arange(6) + dx, [x["directional_test"] for x in rr], 0.32, color=COL[m], label=LAB[m])
        ax.plot(np.arange(6) + dx, [x["own_improvement"] for x in rr], "s", mfc="white", mec="k", ms=4)
    ax.axhline(0, color="0.6", lw=0.8)
    ax.set_xticks(range(6))
    ax.set_xticklabels(labs, rotation=30, ha="right")
    ax.set_title("B. By confirmatory pair (bars: association test; squares: own improvement)", loc="left", fontsize=9)
    ax.legend(frameon=False, fontsize=7.5)
    ax = axs[2]
    for m in C.MODELS:
        rr = [x for x in pr if x["checkpoint"] == m]
        ax.plot([x["a"] for x in rr], [x["S_left_minus_S_right"] for x in rr], "o", color=COL[m], label=LAB[m])
        for x in rr:
            ax.annotate(x["left"], (x["a"], x["S_left_minus_S_right"]), fontsize=6, xytext=(3, 3), textcoords="offset points")
    ax.axhline(0, color="0.6", lw=0.8)
    ax.axvline(0, color="0.6", lw=0.8)
    ax.set_xlabel("association contrast a = A(left) - A(right), nats")
    ax.set_ylabel("S(left) - S(right), bits")
    ax.set_title("C. Independent association vs held-out selectivity", loc="left", fontsize=9)
    fig.tight_layout()
    _save(fig, out, "fig33_primary")


def rolls(res, out):
    plt = _plt()
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.2))
    for ax, k, t in zip(axs, ("separability_js", "D_own_neutral", "directional_test"),
                        ("A. Direct-policy separability (JS)", "B. Neutral forecast to own policy (JS)", "C. Association test by roll")):
        for m in C.MODELS:
            rr = [x for x in res["core"]["rolls"] if x["checkpoint"] == m]
            ax.plot([x["roll"] for x in rr], [x[k] for x in rr], "o-", color=COL[m], label=LAB[m])
        if k == "directional_test":
            ax.axhline(0, color="0.6", lw=0.8)
        ax.set_title(t, loc="left", fontsize=9)
        ax.set_xlabel("roll scored")
    axs[0].set_ylabel("bits")
    axs[1].legend(frameon=False, fontsize=7.5)
    fig.tight_layout()
    _save(fig, out, "fig33_rolls")


def named(res, out):
    plt = _plt()
    M = {(x["forecaster"], x["named_target"]): x for x in res["core"]["named_matrix"]}
    fig, axs = plt.subplots(1, 2, figsize=(7.5, 3))
    for ax, k, t in zip(axs, ("D_named", "improvement_vs_generic"), ("JS to named target (lower = closer)", "Improvement vs 'a language model'")):
        Z = np.array([[M[(p, q)][k] for q in C.MODELS] for p in C.MODELS])
        ax.imshow(Z, cmap="Blues" if k == "D_named" else "RdBu", vmin=0 if k == "D_named" else -abs(Z).max(), vmax=abs(Z).max())
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{Z[i, j]:+.3f}" if k != "D_named" else f"{Z[i, j]:.3f}", ha="center", va="center",
                        bbox=dict(fc="white", ec="none", alpha=0.8, pad=1.5))
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["named Qwen", "named Mistral"])
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["Qwen forecasts", "Mistral forecasts"])
        ax.set_title(t, fontsize=9, loc="left")
        for s in ax.spines.values():
            s.set_visible(False)
    fig.tight_layout()
    _save(fig, out, "fig33_named_matrix")


def words(res, out):
    plt = _plt()
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.4), sharey=True)
    for ax, m in zip(axs, C.MODELS):
        rr = [x for x in res["core"]["words"] if x["checkpoint"] == m and x["bank"].startswith("confirmatory")]
        x = np.arange(len(rr))
        ax.bar(x - 0.2, [r["own_gain"] for r in rr], 0.38, color=COL[m], label="gain vs own policy")
        ax.bar(x + 0.2, [r["other_gain"] for r in rr], 0.38, color="0.7", label="gain vs other policy")
        ax.axhline(0, color="0.6", lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels([r["word"] for r in rr], rotation=40, ha="right")
        ax.set_title(f"{LAB[m]} forecasts", loc="left", fontsize=9)
        ax.legend(frameon=False, fontsize=7.5)
    axs[0].set_ylabel("gain over 'a shape' (bits)")
    fig.tight_layout()
    _save(fig, out, "fig33_words")


def all(data, res, out):
    out = Path(out)
    vectors(data, out)
    primary(res, out)
    rolls(res, out)
    named(res, out)
    words(res, out)
