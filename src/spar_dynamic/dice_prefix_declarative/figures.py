"""Figures for SPAR_DICE_PREFIX_DECLARATIVE_v1.0 (handoff section 8). Measured values only; probabilities on axes."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from spar_dynamic.dice_prefix_declarative import config as C  # noqa: E402
from spar_dynamic.dice_recognition_logprob.analysis import INK, INK2, GRID, BAND  # noqa: E402

ARM_COL = {"H": "#2a78d6", "N": "#eb6834", "S": "#1baa7a", "O": "#8a5cd6"}
REF_COL = {"G": INK, "F": "#a3a29d"}
ARM_NAME = {"H": "H: prefix only", "N": "N: unspecified model", "S": "S: your own model", "O": "O: different model"}
FACES = C.FACES


def _style():
    plt.rcParams.update({"axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                         "font.size": 8, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                         "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True, "legend.frameon": False})


def _bars(ax, series: list, title: str):
    w = 0.8 / len(series)
    x = np.arange(len(FACES))
    for i, (name, col, p) in enumerate(series):
        ax.bar(x - 0.4 + w * (i + 0.5), p, w - 0.03, color=col, label=name, edgecolor="white", linewidth=0.5)
    ax.set_xticks(x, [str(f) for f in FACES])
    ax.set_ylim(0, 1)
    ax.set_xlabel("die face")
    ax.set_title(title, fontsize=8.5, color=INK, loc="left")
    ax.grid(axis="x", visible=False)


def fig_position1(t: dict, out: Path):
    fig, ax = plt.subplots(figsize=(5.2, 2.8))
    p = t["position1"]
    _bars(ax, [("G: direct generation", REF_COL["G"], p["G"]), ("F: full 10-roll self-prediction", REF_COL["F"], p["F_at_G"]),
               ("H(0): predict rolls 1-3, nothing revealed", ARM_COL["H"], p["H0"])],
          "Roll 1: six-face probability under three different task wrappers")
    ax.set_ylabel("probability")
    ax.legend(loc="upper right", fontsize=7)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def fig_k3(t: dict, out: Path):
    fig, axes = plt.subplots(1, 4, figsize=(9.6, 2.6), sharey=True)
    G4 = t["G"][4]
    for ax, a in zip(axes, C.ARMS):
        r = next(r for r in t["rows"] if r["arm"] == a and r["k"] == 3 and r["position"] == 4)
        p = [r[f"p{f}"] for f in FACES]
        _bars(ax, [("G position 4", REF_COL["G"], G4), (ARM_NAME[a], ARM_COL[a], p)], f"{ARM_NAME[a]}\nP(3) = {p[2]:.2f} (G {G4[2]:.2f})")
    axes[0].set_ylabel("probability")
    axes[0].legend(handles=axes[0].patches[:1], labels=["G, position 4"], loc="upper left", fontsize=7)
    fig.suptitle("k = 3 (\"5 2 6\" revealed): next-roll distribution, true roll is 3 (conditional, teacher-forced)",
                 fontsize=8.5, x=0.01, ha="left", color=INK)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def fig_ptrue(t: dict, out: Path):
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    off = {"H": -0.24, "N": -0.08, "S": 0.08, "O": 0.24}
    for a in C.ARMS:
        rs = [r for r in t["rows"] if r["arm"] == a]
        ax.scatter([r["position"] + off[a] for r in rs], [r["p_true"] for r in rs], s=30, color=ARM_COL[a],
                   edgecolor="white", linewidth=1, label=ARM_NAME[a], zorder=3)
    js = [j for j in sorted(t["G"]) if j <= 9]
    ax.scatter(js, [t["G"][j][C.G_REF[j - 1] - 1] for j in js], marker="_", s=220, color=INK, linewidth=2,
               label="G (direct generation)", zorder=4)
    for b in (3.5, 6.5):
        ax.axvline(b, color=INK2, lw=0.6)
    for k in C.KS:
        ax.text(k + 2, 1.04, f"k = {k}", ha="center", fontsize=7.5, color=INK2, transform=ax.get_xaxis_transform())
    ax.set_xticks(range(1, 10), [f"{j}\n({C.G_REF[j - 1]})" for j in range(1, 10)])
    ax.set_xlim(0.5, 9.5)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("original position (true G roll); positions are dependent, k changes which roll is predicted")
    ax.set_ylabel("P(true roll)")
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=7)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def fig_contrasts(t: dict, out: Path):
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 2.9))
    col = {"N-H": ARM_COL["N"], "S-H": ARM_COL["S"], "S-N": INK, "O-H": ARM_COL["O"], "S-O": "#a3a29d"}
    off = {"N-H": -0.24, "S-H": -0.12, "S-N": 0, "O-H": 0.12, "S-O": 0.24}
    for ax, key, lab in ((axes[0], "d_p_true", "difference in P(true roll)"), (axes[1], "d_js_bits", "difference in JS divergence from G (bits)")):
        for c in col:
            rs = [r for r in t["contrasts"] if r["contrast"] == c]
            ax.scatter([r["position"] + off[c] for r in rs], [r[key] for r in rs], s=24, color=col[c], edgecolor="white",
                       linewidth=0.8, label=c, zorder=3)
        if key == "d_p_true":
            ax.axhspan(-t["floor"], t["floor"], color=BAND, zorder=0)
        ax.axhline(0, color=INK2, lw=0.7)
        for b in (3.5, 6.5):
            ax.axvline(b, color=GRID, lw=0.8)
        ax.set_xticks(range(1, 10))
        ax.set_xlabel("original position")
        ax.set_ylabel(lab)
    axes[0].set_title(f"Higher = first arm puts more on the true roll (band: ±{t['floor']:.2f} floor)", fontsize=8, loc="left", color=INK)
    axes[1].set_title("Lower = first arm closer to direct generation", fontsize=8, loc="left", color=INK)
    axes[1].legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=7)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def fig_free(t: dict, out: Path):
    rows = sorted(t["free"], key=lambda r: (r["k"], C.ARMS.index(r["arm"])))
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.grid(False)
    for i, r in enumerate(rows):
        pred = r["output"].split(" ")
        tgt = r["target"].split(" ")
        tf = [x for x in t["rows"] if x["condition"] == r["condition"]]
        tf = sorted(tf, key=lambda x: x["position"])
        for j in range(3):
            ok = j < len(pred) and pred[j] == tgt[j]
            ax.add_patch(plt.Rectangle((j, i), 0.96, 0.9, color="#d9efe6" if ok else "#f7e1d7"))
            ax.text(j + 0.14, i + 0.45, f"{pred[j] if j < len(pred) else '?'}", ha="center", va="center", fontsize=9, color=INK, weight="bold")
            ax.text(j + 0.9, i + 0.45, f"free P(true) {r.get(f'free_p_true_{j + 1}', float('nan')):.2f}\nforced P(true) {tf[j]['p_true']:.2f}",
                    ha="right", va="center", fontsize=5.2, color=INK2)
        ax.text(-0.1, i + 0.45, f"{r['condition']}  (true {r['target']})", ha="right", va="center", fontsize=7, color=INK)
    ax.set_xlim(-1.6, 3)
    ax.set_ylim(len(rows), -0.2)
    ax.set_xticks([0.48, 1.48, 2.48], ["1st predicted", "2nd", "3rd"])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Free greedy prediction (bold; green = matches G) vs teacher-forced P(true roll)", fontsize=8, loc="left", color=INK)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def all_figures(t: dict, d: Path):
    _style()
    d.mkdir(parents=True, exist_ok=True)
    fig_position1(t, d / "fig1_position1_G_F_H0.png")
    fig_k3(t, d / "fig2_k3_position4.png")
    fig_ptrue(t, d / "fig3_p_true_by_position.png")
    fig_contrasts(t, d / "fig4_paired_contrasts.png")
    fig_free(t, d / "fig5_free_vs_teacher_forced.png")
