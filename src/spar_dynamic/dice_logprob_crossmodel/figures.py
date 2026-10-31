"""Figures for SPAR_DICE_LOGPROB_CROSSMODEL_v2.0 (PNG + PDF), all from analysis.analyse_model() results.

Colours: categorical slots 1-3 of the reference data-viz palette (validated all-pairs): G blue, F orange, both aqua;
"neither" is a neutral grey; heatmaps use the single-hue blue ramp. Identity is never colour-only (legends, letters in cells).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from spar_dynamic.dice_logprob_crossmodel import config as C  # noqa: E402

BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#e4e3df"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e9e8e4"
RAMP = LinearSegmentedColormap.from_list("blue", ["#fcfcfb", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
NAME = {m: C.MODEL[m]["name"] for m in C.MODELS}

plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False, "figure.dpi": 150,
                     "savefig.bbox": "tight", "pdf.fonttype": 42, "font.family": "DejaVu Sans"})


def _save(fig, out: Path, name: str):
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(out / f"{name}.{ext}", facecolor="white")
    plt.close(fig)


def _grid(ax, axis="y"):
    ax.grid(True, axis=axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def fig1_design(out: Path):
    rows = ["G", "F"] + [f"S{k}" for k in range(1, 11)] + [f"W{a}-{b}" for a, b in C.WINDOWS]
    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    for i, r in enumerate(rows):
        pos = list(range(1, 11)) if r in ("G", "F") else [int(r[1:])] if r[0] == "S" else list(range(int(r[1:].split("-")[0]), int(r.split("-")[1]) + 1))
        col = BLUE if r == "G" else ORANGE if r == "F" else "#9ec5f4" if r[0] == "S" else "#86b6ef"
        for j, p in enumerate(pos):
            ax.add_patch(plt.Rectangle((p - 0.46, i - 0.42), 0.92, 0.84, color=col, lw=0))
            ax.text(p, i, str(j + 1), ha="center", va="center", fontsize=7, color="white" if r in ("G", "F") else INK)
    ax.set_xlim(0.4, 10.6)
    ax.set_ylim(len(rows) - 0.4, -0.6)
    ax.set_xticks(range(1, 11))
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(["G  generate 10", "F  predict all 10"] + [f"S{k}  predict only {k}" for k in range(1, 11)] +
                       [f"W{a}-{b}  predict {a}..{b}" for a, b in C.WINDOWS])
    ax.set_xlabel("original serial position in the hypothetical 10-roll sequence")
    ax.set_title("15 conditions per model; each row is a separate fresh context.\nNumbers = position within the reported answer",
                 fontsize=9, color=INK, loc="left")
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    _save(fig, out, "fig1_design")


def fig2_gf(res: dict, out: Path):
    fig = plt.figure(figsize=(10, 6.6))
    gs = fig.add_gridspec(3, len(res), height_ratios=[1, 1, 1.25], hspace=0.55, wspace=0.18, right=0.9)
    for c, (m, r) in enumerate(res.items()):
        nat = r["natural"]["rows"]
        for i, key in enumerate(("G", "F")):
            ax = fig.add_subplot(gs[i, c])
            mat = [[row[f"{key}_p"][f - 1] for row in nat] for f in C.FACES]
            im = ax.imshow(mat, cmap=RAMP, vmin=0, vmax=1, aspect="auto", extent=(0.5, 10.5, 6.5, 0.5))
            for row in nat:
                ax.text(row["position"], row[f"{key}_face"], row[f"{key}_face"], ha="center", va="center", fontsize=7,
                        color="white" if row[f"{key}_p"][row[f"{key}_face"] - 1] > 0.55 else INK, fontweight="bold")
            ax.set_yticks(range(1, 7))
            ax.set_xticks(range(1, 11))
            ax.set_ylabel("face")
            ax.set_title(f"{NAME[m]}: {key}, six-face p on its own path", fontsize=8.5, loc="left", color=INK)
            ax.tick_params(length=0)
        ax = fig.add_subplot(gs[2, c])
        _grid(ax)
        ax.axhspan(0, max(r["floor"]["js_bits"], 0.012), color="#c3c2b7", lw=0, label="numerical floor (max JS)")
        mp = r["matched"]["rows"]
        series = [("natural paths (different histories after 1)", [x["js"] for x in nat], INK, "o"),
                  ("matched prefix: G history", [x["js"] for x in mp if x["history"] == "G"], BLUE, "s"),
                  ("matched prefix: F history", [x["js"] for x in mp if x["history"] == "F"], ORANGE, "D")]
        for lab, ys, col, mk in series:
            ax.plot(range(1, 11), ys, color=col, lw=2, marker=mk, ms=5, label=lab)
        ax.set_ylim(0, 1)
        ax.set_xticks(range(1, 11))
        ax.set_xlabel("position")
        ax.set_ylabel("JS(G, F), bits")
        ax.set_title(f"{NAME[m]}: G vs F divergence", fontsize=8.5, loc="left", color=INK)
        if c == 0:
            ax.legend(frameon=False, fontsize=7.5, ncol=4, loc="upper left", bbox_to_anchor=(0, -0.28))
    fig.colorbar(im, cax=fig.add_axes([0.92, 0.47, 0.012, 0.4]), label="six-face probability (bold = chosen face)")
    _save(fig, out, "fig2_G_vs_F")


def fig3_scope(res: dict, out: Path):
    fig = plt.figure(figsize=(10, 6.2))
    gs = fig.add_gridspec(2, len(res), height_ratios=[1.35, 1], hspace=0.45, wspace=0.18)
    for c, (m, r) in enumerate(res.items()):
        nat = {x["position"]: x for x in r["natural"]["rows"]}
        rows = [("G", {k: nat[k]["G_face"] for k in nat}), ("F", {k: nat[k]["F_face"] for k in nat}),
                ("S(k)", {x["position"]: x["S_face"] for x in r["singles"]["rows"] if x["S_face"] is not None})]
        for a, b in C.WINDOWS:
            w = f"W{a}-{b}"
            rows.append((w, {x["position"]: x["W_face"] for x in r["windows"]["rows"] if x["window"] == w and "W_face" in x}))
        ax = fig.add_subplot(gs[0, c])
        for i, (lab, faces) in enumerate(rows):
            span = range(1, 11) if lab in ("G", "F", "S(k)") else range(int(lab[1:].split("-")[0]), int(lab.split("-")[1]) + 1)
            for k in span:
                f = faces.get(k)
                if f is None:
                    col, txt = "white", "×"
                elif lab == "G":
                    col, txt = BLUE, f
                elif lab == "F":
                    col, txt = ORANGE, f
                else:
                    g, ff = f == nat[k]["G_face"], f == nat[k]["F_face"]
                    col, txt = (AQUA if g and ff else BLUE if g else ORANGE if ff else GREY), f
                ax.add_patch(plt.Rectangle((k - 0.45, i - 0.4), 0.9, 0.8, color=col, lw=0, ec=MUTED))
                ax.text(k, i, txt, ha="center", va="center", fontsize=8, color="white" if col in (BLUE, ORANGE) else INK)
        ax.set_xlim(0.4, 10.6)
        ax.set_ylim(len(rows) - 0.4, -0.6)
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels([x[0] for x in rows])
        ax.set_xticks(range(1, 11))
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(f"{NAME[m]}: reported faces at original positions (× = invalid output)", fontsize=8.5, loc="left", color=INK)
        if c == 0:
            ax.legend(handles=[Patch(color=BLUE, label="= G only"), Patch(color=ORANGE, label="= F only"),
                               Patch(color=AQUA, label="= G and F"), Patch(color=GREY, label="neither")],
                      frameon=False, fontsize=7, ncol=4, loc="upper left", bbox_to_anchor=(0, -0.08))
        ax = fig.add_subplot(gs[1, c])
        _grid(ax)
        s = r["singles"]["rows"]
        ax.plot([x["position"] for x in s], [x["vsG_js"] for x in s], color=BLUE, lw=2, marker="s", ms=5, label="S(k) vs G(k)")
        ax.plot([x["position"] for x in s], [x["vsF_js"] for x in s], color=ORANGE, lw=2, marker="D", ms=5, label="S(k) vs F(k)")
        wr = [x for x in r["windows"]["rows"] if "vsG_js" in x]
        ax.scatter([x["position"] for x in wr], [x["vsG_js"] for x in wr], s=26, facecolor="white", edgecolor=BLUE, lw=1.5,
                   marker="o", label="W vs G(k)", zorder=3)
        ax.scatter([x["position"] for x in wr], [x["vsF_js"] for x in wr], s=26, facecolor="white", edgecolor=ORANGE, lw=1.5,
                   marker="^", label="W vs F(k)", zorder=3)
        ax.axhspan(0, r["floor"]["js_bits"], color=GRID, lw=0)
        ax.set_ylim(0, 1)
        ax.set_xticks(range(1, 11))
        ax.set_xlabel("original position")
        ax.set_ylabel("JS, bits (contexts differ)")
        if c == 0:
            ax.legend(frameon=False, fontsize=7.5, ncol=4, loc="upper left", bbox_to_anchor=(0, -0.25))
    _save(fig, out, "fig3_scope_S_W")


def fig4_cross(res: dict, out: Path):
    metrics = [("position 1, natural\n(same empty history)", lambda r: r["natural"]["summary"]["position1"]["js"]),
               ("positions 2-10, natural", lambda r: r["natural"]["summary"]["mean_js_2_10"]),
               ("positions 2-10, matched G history", lambda r: r["matched"]["summary"]["G"]["mean_js_2_10"]),
               ("positions 2-10, matched F history", lambda r: r["matched"]["summary"]["F"]["mean_js_2_10"]),
               ("numerical floor (max JS)", lambda r: r["floor"]["js_bits"])]
    fig, axes = plt.subplots(1, len(res), figsize=(9, 2.9), sharey=True)
    for ax, (m, r) in zip(axes, res.items()):
        vals = [f(r) for _, f in metrics]
        ys = range(len(metrics))
        _grid(ax, "x")
        ax.barh(ys, vals, height=0.55, color=[BLUE] * 4 + [GREY])
        for y, v in zip(ys, vals):
            ax.text(v + 0.01, y, f"{v:.3f}", va="center", fontsize=7.5, color=INK2)
        ax.set_yticks(list(ys))
        ax.set_yticklabels([x[0] for x in metrics])
        if ax is axes[0]:
            ax.invert_yaxis()                     # shared y: invert once
        ax.set_xlim(0, 1)
        ax.set_xlabel("JS(G, F), bits (mean over positions)")
        ax.set_title(NAME[m], fontsize=9, loc="left", color=INK)
    _save(fig, out, "fig4_cross_model")


def all_figures(res: dict, out: Path):
    out = Path(out)
    fig1_design(out)
    fig2_gf(res, out)
    fig3_scope(res, out)
    fig4_cross(res, out)
