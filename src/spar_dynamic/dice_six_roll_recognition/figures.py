"""Figures for SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0 (PNG + PDF), from analysis.analyse() results and the calibration gates.

Colours: categorical slots 1-2 of the reference data-viz palette (Qwen blue, Mistral orange) for the judge or scoring model,
neutral grey for zero lines and epsilon bands. Model identity is also carried by marker shape, never colour alone. Filled
markers are order-averaged S; hollow markers are the single-orientation scores s1 (authentic shown as A) and s2 (as B).
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from spar_dynamic.dice_logprob_crossmodel.figures import BLUE, GREY, INK, INK2, MUTED, ORANGE, _grid, _save  # noqa: E402
from spar_dynamic.dice_six_roll_recognition import config as C  # noqa: E402
from spar_dynamic.dice_six_roll_recognition import stimuli as S  # noqa: E402

NAME = {"qwen": "Qwen", "mistral": "Mistral"}
COL = {"qwen": BLUE, "mistral": ORANGE}
MK = {"qwen": "o", "mistral": "s"}
SOURCES = [S.source_id(s, i) for s in C.MODELS for i in C.INSTRUCTIONS]
SRC_LABEL = {S.source_id(s, i): f"{NAME[s]} {i}" for s in C.MODELS for i in C.INSTRUCTIONS}


def _legend_models(ax, title, loc="best"):
    h = [Line2D([], [], color=COL[m], marker=MK[m], ls="none", label=NAME[m]) for m in C.MODELS]
    ax.legend(handles=h, title=title, fontsize=7.5, title_fontsize=7.5, frameon=False, loc=loc)


def _empty(ax, msg):
    ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=8.5, color=MUTED, transform=ax.transAxes, wrap=True)
    ax.set_xticks([])
    ax.set_yticks([])


def fig1_policy(res, out: Path):
    """Generative-policy benchmark: Delta = L(authentic) - L(foil) under each scoring model and the source's instruction."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=False)
    dl = res["policy"]["deltas"]
    for ax, foil in zip(axes, C.FOILS):
        _grid(ax)
        ax.axhline(0, color=GREY, lw=1)
        for k, m in enumerate(C.MODELS):
            xs = [n + (k - 0.5) * 0.36 for n in range(len(SOURCES))]
            ys = [next((x["delta"] for x in dl if x["scorer"] == m and x["source_id"] == sid and x["foil_type"] == foil), None) for sid in SOURCES]
            for x, y, sid in zip(xs, ys, SOURCES):
                if y is None:
                    continue
                own = sid.startswith(m)
                ax.bar(x, y, width=0.32, color=COL[m], alpha=1.0 if own else 0.45, edgecolor="white", linewidth=1.5)
                ax.text(x, y + (0.15 if y >= 0 else -0.15), f"{y:.1f}", ha="center", va="bottom" if y >= 0 else "top", fontsize=6.5, color=INK2)
        ax.set_xticks(range(len(SOURCES)))
        ax.set_xticklabels([SRC_LABEL[s] for s in SOURCES], fontsize=8)
        ax.set_ylabel("Delta = L(authentic) - L(foil), nats" if foil == "swap" else "")
        ax.set_title(f"{foil.upper()} foil" + (" (primary)" if foil == "swap" else " (secondary)"), fontsize=9.5, loc="left", color=INK)
    h = [plt.Rectangle((0, 0), 1, 1, color=COL[m]) for m in C.MODELS] + [plt.Rectangle((0, 0), 1, 1, color=GREY, alpha=0.45)]
    fig.legend(h, ["Qwen scores", "Mistral scores", "pale = scorer is not the source"], fontsize=7.5, frameon=False, loc="lower center", ncol=3)
    fig.suptitle("Policy benchmark: how much more likely each source's authentic rolls 5-6 are than the foil (face-only, two steps)",
                 fontsize=10, x=0.01, ha="left", color=INK)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    _save(fig, out, "fig1_policy_benchmark")


def _scores_panel(ax, pairs, frame, foil, instr, eps):
    _grid(ax)
    ax.axhline(0, color=GREY, lw=1)
    xs_lab = [m for m in C.MODELS]
    for k, j in enumerate(C.MODELS):
        if j in eps:
            ax.axhspan(-eps[j], eps[j], color=GREY, alpha=0.08, lw=0)
        for n, s in enumerate(xs_lab):
            p = next((p for p in pairs if p["judge"] == j and p["frame"] == frame and p["foil_type"] == foil and
                      p["source_instruction"] == instr and p["source"] == s), None)
            if p is None:
                continue
            x = n + (k - 0.5) * 0.3
            ax.plot([x, x], [p["s1"], p["s2"]], color=COL[j], lw=1, alpha=0.6)
            ax.plot([x - 0.06], [p["s1"]], marker=MK[j], mfc="white", mec=COL[j], ms=5, ls="none")
            ax.plot([x + 0.06], [p["s2"]], marker=MK[j], mfc="white", mec=COL[j], ms=5, ls="none")
            ax.plot([x], [p["S"]], marker=MK[j], color=COL[j], ms=8, ls="none", mec="white", mew=1.2)
    ax.set_xticks(range(len(xs_lab)))
    ax.set_xticklabels([f"{NAME[s]} {instr} source" for s in xs_lab], fontsize=8)
    ax.set_xlim(-0.6, len(xs_lab) - 0.4)


def fig2_swap_scores(res, out: Path, foil="swap", name="fig2_swap_scores"):
    pairs, eps = res["pairs"], res["epsilon"]
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharey=True)
    for r, frame in enumerate(C.FRAMES):
        for c, instr in enumerate(C.INSTRUCTIONS):
            ax = axes[r][c]
            if not pairs:
                _empty(ax, "no analysable judge")
                continue
            _scores_panel(ax, pairs, frame, foil, instr, eps)
            ax.set_title(f"{frame} frame, {instr} sources", fontsize=9, loc="left", color=INK)
            if c == 0:
                ax.set_ylabel("authentic preference (log-odds)")
    if pairs:
        h = [Line2D([], [], color=COL[m], marker=MK[m], ls="none", ms=8, label=f"{NAME[m]} judge: S") for m in C.MODELS] + \
            [Line2D([], [], color=INK2, marker="o", mfc="white", ls="none", ms=5, label="s1 (authentic = A), s2 (authentic = B)"),
             plt.Rectangle((0, 0), 1, 1, color=GREY, alpha=0.2, label="within +/- epsilon")]
        fig.legend(handles=h, fontsize=7.5, frameon=False, loc="lower center", ncol=4)
    fig.suptitle(f"{foil.upper()} foil: each judge's preference for the authentic ending, by source, frame and order "
                 "(positive = authentic)", fontsize=10, x=0.01, ha="left", color=INK)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    _save(fig, out, name)


def fig3_contrasts(res, out: Path):
    fig, ax = plt.subplots(figsize=(9, 4.2))
    _grid(ax)
    ax.axhline(0, color=GREY, lw=1)
    rows = res["crossed"]
    if not rows:
        _empty(ax, "Crossed contrasts unavailable: they need both judges to pass calibration and main checks.")
    else:
        groups = [(foil, i) for foil in C.FOILS for i in C.INSTRUCTIONS]
        frames = [("self", BLUE, 1.0), ("neutral", BLUE, 0.45), ("self_minus_neutral", INK2, 1.0)]
        for g, (foil, i) in enumerate(groups):
            for k, (frame, col, a) in enumerate(frames):
                d = next((r["D"] for r in rows if r["frame"] == frame and r["foil_type"] == foil and r["source_instruction"] == i), None)
                if d is None:
                    continue
                x = g + (k - 1) * 0.26
                ax.bar(x, d, width=0.24, color=col, alpha=a, edgecolor="white", linewidth=1.5)
                ax.text(x, d + (0.03 if d >= 0 else -0.03), f"{d:+.2f}", ha="center", va="bottom" if d >= 0 else "top", fontsize=6.5, color=INK2)
        ax.set_xticks(range(len(groups)))
        ax.set_xticklabels([f"{foil} D_{i}" for foil, i in groups], fontsize=8.5)
        ax.set_ylabel("D (log-odds; positive = own-source advantage)")
        ax.margins(y=0.15)
        h = [plt.Rectangle((0, 0), 1, 1, color=c, alpha=a) for _, c, a in frames]
        ax.legend(h, ["self frame", "neutral frame", "self - neutral"], fontsize=7.5, frameon=False)
    ax.set_title("Crossed diagonal advantage D = 0.5[(S_QQ - S_MQ) + (S_MM - S_QM)]; descriptive, one string per source",
                 fontsize=9.5, loc="left", color=INK)
    fig.tight_layout()
    _save(fig, out, "fig3_crossed_contrasts")


def fig4_calibration(cal: dict, out: Path):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, j in zip(axes, C.MODELS):
        g = cal.get(j)
        if g is None:
            _empty(ax, f"{NAME[j]}: calibration not run")
            continue
        _grid(ax)
        eps = g["epsilon"]
        ax.axhline(0, color=GREY, lw=1)
        ax.axhspan(-eps, eps, color=GREY, alpha=0.12, lw=0)
        items = [(t, k, v) for t in ("last_digit", "all_faces", "order56") for k, v in g["info"]["tasks"].get(t, {}).get("items", {}).items()]
        for n, (t, k, v) in enumerate(items):
            ax.plot([n, n], [v["s1"], v["s2"]], color=COL[j], lw=1, alpha=0.6)
            ax.plot([n], [v["s1"]], marker=MK[j], mfc="white", mec=COL[j], ms=5, ls="none")
            ax.plot([n], [v["s2"]], marker=MK[j], mfc="white", mec=COL[j], ms=5, ls="none")
            ax.plot([n], [v["S"]], marker=MK[j], color=COL[j], ms=7, ls="none", mec="white")
        for b in (5.5, 11.5):
            ax.axvline(b, color=GREY, lw=0.8, ls=":")
        for c, t in zip((2.5, 8.5, 14.5), ("last digit (gated)", "all six faces (gated)", "roll 5 > roll 6 (reported)")):
            ax.text(c, 1.02, t, ha="center", va="bottom", fontsize=7.5, color=INK2, transform=ax.get_xaxis_transform())
        ax.set_xticks([])
        ax.set_title(f"{NAME[j]}: {g['overall']} (epsilon {eps:.3f})", fontsize=9, loc="left", color=INK, pad=16)
        ax.set_ylabel("correct-answer preference (log-odds)" if j == "qwen" else "")
    fig.suptitle("Calibration: filled = S, hollow = each orientation; correct needs > epsilon", fontsize=10, x=0.01, ha="left", color=INK)
    fig.tight_layout()
    _save(fig, out, "fig4_calibration")


def fig5_policy_vs_recognition(res, out: Path):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    for ax, frame in zip(axes, C.FRAMES):
        ps = [p for p in res["pairs"] if p["frame"] == frame]
        if not ps:
            _empty(ax, "no analysable judge")
            continue
        _grid(ax)
        ax.axhline(0, color=GREY, lw=1)
        ax.axvline(0, color=GREY, lw=1)
        for p in ps:
            ax.plot(p["source_model_delta"], p["S"], marker=MK[p["judge"]], ls="none", ms=7,
                    color=COL[p["judge"]] if p["foil_type"] == "swap" else "white", mec=COL[p["judge"]])
            ax.annotate(SRC_LABEL[f"{p['source']}-{p['source_instruction']}"].replace(" ", "-"), (p["source_model_delta"], p["S"]),
                        fontsize=5.5, color=MUTED, xytext=(3, 3), textcoords="offset points")
        ax.set_xlabel("source model's own Delta (nats)")
        ax.set_title(f"{frame} frame", fontsize=9, loc="left", color=INK)
    axes[0].set_ylabel("judge's S (log-odds)")
    h = [Line2D([], [], color=COL[m], marker=MK[m], ls="none", label=f"{NAME[m]} judge") for m in C.MODELS] + \
        [Line2D([], [], color=INK2, marker="o", ls="none", label="filled = swap"), Line2D([], [], color=INK2, marker="o", mfc="white", ls="none", label="hollow = repeat")]
    axes[1].legend(handles=h, fontsize=7, frameon=False, loc="best")
    fig.suptitle("Generation vs recognition per item (8 items x 2 judges; descriptive, too few points for a correlation)",
                 fontsize=10, x=0.01, ha="left", color=INK)
    fig.tight_layout()
    _save(fig, out, "fig5_policy_vs_recognition")


def all_figures(res, out: Path, root=None):
    out.mkdir(parents=True, exist_ok=True)
    cal = {}
    for j in C.MODELS:
        p = Path(root or C.EXP) / "calibration" / j / "calibration_gate.json"
        if p.exists():
            cal[j] = json.load(open(p, encoding="utf-8"))
    fig1_policy(res, out)
    fig2_swap_scores(res, out)
    fig2_swap_scores(res, out, foil="repeat", name="fig2b_repeat_scores")
    fig3_contrasts(res, out)
    fig4_calibration(cal, out)
    fig5_policy_vs_recognition(res, out)
