"""Figures for Experiments 31 and 32 (PNG + PDF), in the Experiment 28-30 house style.

Colours: categorical slots 1-2 of the reference palette for the scoring/predicting model (Qwen blue, Mistral orange); identity
is also carried by marker shape (Qwen circle, Mistral square) and line style for G (solid) vs F (dashed). Sequential blue ramp
for probabilities and log loss; neutral grey for reference lines. Text stays in ink tokens.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from spar_dynamic.dice_31_32 import config as C  # noqa: E402
from spar_dynamic.dice_31_32 import stimuli as S  # noqa: E402
from spar_dynamic.dice_logprob_crossmodel.figures import BLUE, GREY, INK, INK2, MUTED, ORANGE, RAMP, _grid, _save  # noqa: E402

NAME = {"qwen": "Qwen", "mistral": "Mistral"}
COL = {"qwen": BLUE, "mistral": ORANGE}
MK = {"qwen": "o", "mistral": "s"}
LS = {"G": "-", "F": "--"}
SOURCES = [S.source_id(s, i) for s in C.MODELS for i in C.INSTRUCTIONS]
SRC_LABEL = {S.source_id(s, i): f"{NAME[s]} {i}" for s in C.MODELS for i in C.INSTRUCTIONS}
FACES = [str(f) for f in C.FACES]
TICK32 = {"A": "A\npair-generated\nsixth and seventh", "B": "B\ndirect seventh", "C": "C\nauthentic sixth\nsupplied"}


def fig31_heatmaps(res, out: Path, cross=True):
    """Six-face probabilities at every position for each scorer on the other (cross) or its own model's G and F histories."""
    rows = res["rows"]
    combos = [(sc, s, i) for sc in C.MODELS for s in C.MODELS if (s != sc) == cross for i in C.INSTRUCTIONS]
    fig, axes = plt.subplots(len(combos), 2, figsize=(9.6, 2.05 * len(combos)), constrained_layout=True)
    for r_, (sc, s, i) in enumerate(combos):
        x = C.REFERENCES[(s, i)]
        for c_, sm in enumerate(C.INSTRUCTIONS):
            ax = axes[r_, c_]
            sel = sorted([r for r in rows if r["scorer_model"] == sc and r["source_model"] == s and r["source_mode"] == i and r["scorer_mode"] == sm],
                         key=lambda r: r["position"])
            grid = [[r[f"p{f}"] for r in sel] for f in FACES]
            im = ax.imshow(grid, cmap=RAMP, vmin=0, vmax=1, aspect="auto", origin="lower", extent=(0.5, 10.5, 0.5, 6.5))
            for r in sel:
                ax.plot(r["position"], r["authentic_face"], marker="o", ms=11, mfc="none", mec=INK, mew=1.4)
                ax.plot(r["position"], r["top_face"], marker="x", ms=5, color=ORANGE if r["top_face"] != r["authentic_face"] else INK, mew=1.4)
            ll = sum(r["logloss"] for r in sel if r["position"] >= 2) / max(1, sum(r["position"] >= 2 for r in sel))
            ax.set_title(f"{NAME[sc]} scores {NAME[s]} {i} path  |  scorer prompt {sm}  |  log loss 2-10 = {ll:.2f}",
                         fontsize=8, loc="left", color=INK)
            ax.set_xticks(range(1, 11))
            ax.set_xticklabels([f"{j}\n{x[j - 1]}" for j in range(1, 11)], fontsize=6.5)
            ax.set_yticks(range(1, 7))
            ax.set_ylabel("face", fontsize=7.5)
    fig.colorbar(im, ax=axes, shrink=0.5, label="six-face normalised probability")
    fig.suptitle(("Cross-model" if cross else "Own-model") + " teacher forcing: ring = authentic source roll, x = scorer's top face "
                 "(orange if different). Tick: position / authentic roll.", fontsize=9, color=INK2)
    _save(fig, out, "fig31_heatmaps_" + ("cross" if cross else "own"))


def fig31_matrix(res, out: Path):
    """Mean authentic-face log loss (positions 2-10) per source path (rows) x scorer and scorer prompt (columns)."""
    rows = res["rows"]
    cols = [(sc, sm) for sc in C.MODELS for sm in C.INSTRUCTIONS]
    M = [[sum(r["logloss"] for r in rows if r["source_id"] == sid and r["scorer_model"] == sc and r["scorer_mode"] == sm and r["position"] >= 2) / 9
          for sc, sm in cols] for sid in SOURCES]
    fig, ax = plt.subplots(figsize=(7.4, 4.0), constrained_layout=True)
    vmax = max(max(r) for r in M)
    im = ax.imshow(M, cmap=RAMP, vmin=0, vmax=vmax, aspect="auto")
    for a, sid in enumerate(SOURCES):
        s, i = sid.split("-")
        for b, (sc, sm) in enumerate(cols):
            replay = sc == s and sm == i
            ax.text(b, a, f"{M[a][b]:.2f}" + ("\nreplay" if replay else ""), ha="center", va="center", fontsize=8,
                    color="white" if M[a][b] > 0.6 * vmax else INK, fontstyle="italic" if replay else "normal")
            if replay:
                ax.add_patch(plt.Rectangle((b - 0.5, a - 0.5), 1, 1, fill=False, hatch="///", edgecolor=MUTED, lw=0))
    ax.set_xticks(range(4))
    ax.set_xticklabels([f"{NAME[sc]} scorer\n{sm} prompt" for sc, sm in cols], fontsize=8)
    ax.set_yticks(range(4))
    ax.set_yticklabels([f"{SRC_LABEL[s]} path" for s in SOURCES], fontsize=8)
    ax.axvline(1.5, color="white", lw=3)
    ax.axhline(1.5, color="white", lw=3)
    fig.colorbar(im, ax=ax, label="mean -ln p(authentic), nats (lower = better)")
    ax.set_title("Crossed likelihood matrix, rolls 2-10. Hatched 'replay' cells rescore the model's own greedy output under\n"
                 "its original prompt (deterministic, expected; not evidence of self-knowledge).", fontsize=8.5, loc="left", color=INK)
    _save(fig, out, "fig31_crossed_matrix")


def fig31_js(res, out: Path):
    """Per-position JS: between scorers on the same context (top), and within a scorer between G and F prompts (bottom)."""
    fig, axes = plt.subplots(2, 2, figsize=(10.2, 6.4), sharex=True, constrained_layout=True)
    for c_, sm in enumerate(C.INSTRUCTIONS):
        ax = axes[0, c_]
        _grid(ax)
        for sid in SOURCES:
            s, i = sid.split("-")
            xs = sorted([x for x in res["js"]["between"] if x["source_id"] == sid and x["scorer_mode"] == sm], key=lambda x: x["position"])
            ax.plot([x["position"] for x in xs], [x["js_bits"] for x in xs], color=COL[s], ls=LS[i], marker=MK[s], ms=4.5, lw=1.6,
                    label=f"{SRC_LABEL[sid]} path")
        ax.set_ylim(0, 1)
        ax.set_title(f"Qwen vs Mistral, same context, scorer prompt {sm}", fontsize=9, loc="left", color=INK)
        ax.set_ylabel("JS divergence, bits")
    for c_, sc in enumerate(C.MODELS):
        ax = axes[1, c_]
        _grid(ax)
        for sid in SOURCES:
            s, i = sid.split("-")
            xs = sorted([x for x in res["js"]["within"] if x["source_id"] == sid and x["scorer_model"] == sc], key=lambda x: x["position"])
            ax.plot([x["position"] for x in xs], [x["js_bits_G_vs_F"] for x in xs], color=COL[s], ls=LS[i], marker=MK[s], ms=4.5, lw=1.6)
        ax.set_ylim(0, 1)
        ax.set_title(f"{NAME[sc]}: G vs F prompt on the same prefix", fontsize=9, loc="left", color=INK)
        ax.set_ylabel("JS divergence, bits")
        ax.set_xlabel("position (1 = opening, empty prefix)")
    ax.set_xticks(range(1, 11))
    h = [Line2D([], [], color=COL[s], ls=LS[i], marker=MK[s], label=f"{SRC_LABEL[S.source_id(s, i)]} path") for s in C.MODELS for i in C.INSTRUCTIONS]
    axes[0, 1].legend(handles=h, fontsize=7.5, frameon=False, loc="upper right", handlelength=3.2)
    _save(fig, out, "fig31_js_by_position")


def fig32(res, out: Path):
    """p(authentic seventh) under A / B / C, facets by source, one series per predictor (fixed examples, exploratory)."""
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.9), sharey=True, constrained_layout=True)
    for ax, (s, i) in zip(axes, C.SOURCES32):
        sid = S.source_id(s, i)
        _grid(ax)
        a7 = C.REFERENCES[(s, i)][6]
        for k, p in enumerate(C.MODELS):
            cs = {c["condition"]: c for c in res["cells"] if c["predictor"] == p and c["source_id"] == sid}
            if len(cs) < 3:
                continue
            xs = [n + (k - 0.5) * 0.12 for n in range(3)]
            ys = [cs[c]["p_true7"] for c in C.CONDITIONS32]
            ax.plot([x for x, y in zip(xs, ys) if y is not None], [y for y in ys if y is not None], color=COL[p], marker=MK[p], ms=7,
                    lw=1.6, label=f"{NAME[p]} predictor")
            ax.plot(xs[0], cs["A"]["constrained_p_true7"], marker=MK[p], ms=9, mfc="none", mec=COL[p], mew=1.4, ls="none")
            for x, y in zip(xs, ys):
                if y is not None:
                    ax.text(x + 0.05, y, f"{y:.2f}", fontsize=7, color=INK2, va="center")
            six = cs["A"]["generated_sixth"]
            ax.text(xs[0], -0.09 - 0.07 * k, f"{NAME[p]} sixth: {six if six is not None else 'invalid'}", fontsize=7, color=COL[p], ha="center")
        ax.axhline(1 / 6, color=GREY, lw=1)
        ax.set_xticks(range(3))
        ax.set_xticklabels([TICK32[c] for c in C.CONDITIONS32], fontsize=7.5)
        ax.set_ylim(-0.25, 1.05)
        ax.set_title(f"{SRC_LABEL[sid]} path (own source: {NAME[s]})\nrolls 1-5 `{S.seq(C.REFERENCES[(s, i)][:5])}`, "
                     f"true 6th {C.REFERENCES[(s, i)][5]}, true 7th {a7}", fontsize=8.5, loc="left", color=INK)
    axes[0].set_ylabel("p(authentic roll 7), six-face normalised")
    axes[1].legend(fontsize=7.5, frameon=False, loc="upper right")
    fig.suptitle("Exploratory, two fixed examples. Hollow marker at A = constrained-digit readout (top first face + space). "
                 "Grey line = 1/6.", fontsize=8.5, color=INK2)
    _save(fig, out, "fig32_roll7_by_condition")


def all31(res, out):
    fig31_heatmaps(res, out, cross=True)
    fig31_heatmaps(res, out, cross=False)
    fig31_matrix(res, out)
    fig31_js(res, out)


def all32(res, out):
    fig32(res, out)
