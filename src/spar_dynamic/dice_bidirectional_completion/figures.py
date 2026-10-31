"""Figures for SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1 (PNG + PDF), from analysis.analyse() results.

Colours: categorical slots 1-2 of the reference data-viz palette (forward blue, backward orange; or revealed/true), neutral
grey for missing/other; heatmaps use the single-hue blue ramp. Predictor is encoded by marker and line style, never colour alone.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from spar_dynamic.dice_bidirectional_completion import config as C  # noqa: E402
from spar_dynamic.dice_logprob_crossmodel.figures import BLUE, GREY, GRID, INK, INK2, MUTED, ORANGE, RAMP, _grid, _save  # noqa: E402

NAME = {"qwen": "Qwen", "mistral": "Mistral"}
ABBR = {"forward": "fwd", "backward": "bwd"}
PSTYLE = {"qwen": dict(marker="o", ls="-"), "mistral": dict(marker="s", ls="--")}
LN6 = math.log(6)


def _cells(res, **kw):
    return [c for c in res["cells"] if all(c.get(k) == v for k, v in kw.items())]


def fig1_design(res, out: Path):
    rows = [("forward", k) for k in C.KS] + [("backward", k) for k in C.KS] + [("middle", None)]
    fig, (ax, axt) = plt.subplots(1, 2, figsize=(11, 5.6), gridspec_kw=dict(width_ratios=[1, 1.15]))
    from spar_dynamic.dice_bidirectional_completion.prompts import split
    for i, (d, k) in enumerate(rows):
        rev, miss = split(d, k)
        for p in range(1, 11):
            if p in rev:
                ax.add_patch(plt.Rectangle((p - 0.45, i - 0.4), 0.9, 0.8, color=GREY, lw=0))
            else:
                ax.add_patch(plt.Rectangle((p - 0.45, i - 0.4), 0.9, 0.8, color=BLUE if d == "forward" else ORANGE if d == "backward" else "#1baf7a", lw=0))
                ax.text(p, i, str(miss.index(p) + 1), ha="center", va="center", fontsize=6.5, color="white")
    ax.set_xlim(0.4, 10.6)
    ax.set_ylim(len(rows) - 0.4, -0.6)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f"{ABBR[d]} k={k}" if k else "middle 3-8" for d, k in rows], fontsize=7.5)
    ax.set_xticks(range(1, 11))
    ax.set_xlabel("original position (grey = revealed; coloured = asked for, number = output order)")
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("19 reveal patterns x 2 instructions x 2 sources x 2 predictors = 152 cells", fontsize=9, loc="left", color=INK)
    axt.axis("off")
    ex = [("Forward k=3 (Qwen G)", "reveal 5 2 6 (pos 1-3)", "target 3 1 4 6 2 5 3 (pos 4-10)"),
          ("Backward k=3 (Qwen G)", "reveal 2 5 3 (pos 8-10)", "target 5 2 6 3 1 4 6 (pos 1-7)"),
          ("Middle (Qwen G)", "reveal 6 3 1 4 6 2 (pos 3-8)", "target 5 2 | 5 3 (pos 1, 2, 9, 10)")]
    y = 0.95
    axt.text(0, y, "Examples (source model never named; both predictors get identical bytes)", fontsize=9, color=INK, va="top")
    for t, a, b in ex:
        y -= 0.12
        axt.text(0, y, t, fontsize=8.5, color=INK, va="top", fontweight="bold")
        axt.text(0.02, y - 0.045, f"{a}  ->  {b}", fontsize=8, color=INK2, va="top", family="monospace")
    axt.text(0, y - 0.15, "Wrapper: 'A language-model instance received the following instruction: <G or F, verbatim> ...\n"
             "Its response consisted of 10 integers from 1 to 6. <REVEALED> ... Predict the missing integers ...'",
             fontsize=7.5, color=INK2, va="top", wrap=True)
    _save(fig, out, "fig1_design")


def _kcurves(res, out: Path, metric, ylabel, name, title):
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.4), sharex=True, sharey=True)
    for r, i in enumerate(C.INSTRUCTIONS):
        for c, s in enumerate(C.MODELS):
            ax = axes[r, c]
            _grid(ax)
            ax.axhline(LN6, color=MUTED, lw=1, ls=":")
            for d, col in (("forward", BLUE), ("backward", ORANGE)):
                for p in C.MODELS:
                    cs = sorted(_cells(res, source=s, source_instruction=i, direction=d, predictor=p), key=lambda x: x["k"])
                    ax.plot([x["k"] for x in cs], [x[metric] for x in cs], color=col, lw=2 if p == s else 1.4, ms=5,
                            mfc=col if p == s else "white", **PSTYLE[p])
            ax.set_title(f"{i} ground truth from {NAME[s]}", fontsize=9, loc="left", color=INK)
            if r == 1:
                ax.set_xlabel("revealed count k")
            if c == 0:
                ax.set_ylabel(ylabel)
            ax.set_xticks(C.KS)
    handles = [Line2D([], [], color=BLUE, lw=2, label="forward"), Line2D([], [], color=ORANGE, lw=2, label="backward"),
               Line2D([], [], color=INK2, marker="o", ls="-", label="Qwen predicts"), Line2D([], [], color=INK2, marker="s", ls="--", label="Mistral predicts"),
               Line2D([], [], color=MUTED, ls=":", label="uniform (ln 6)")]
    fig.legend(handles=handles, frameon=False, ncol=5, fontsize=8, loc="lower center", bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(title + "  (filled markers = self cells)", fontsize=9.5, x=0.06, ha="left", color=INK)
    fig.subplots_adjust(bottom=0.13)
    _save(fig, out, name)


def fig3_crossed(res, out: Path):
    order = {("G", "forward"): 0, ("G", "backward"): 1, ("F", "forward"): 2, ("F", "backward"): 3}
    sets = sorted(((r["source_instruction"], r["direction"], r) for r in res["crossed_avg_mean"]), key=lambda x: order[x[:2]])
    mids = {(m["part"], m["source_instruction"]): m for m in res["middle"]["contrasts"]}
    fig, axes = plt.subplots(1, len(sets), figsize=(12, 3.4))
    vmax = max(v for _, _, r in sets for v in r["matrix"].values())
    for ax, (i, d, r) in zip(axes, sets):
        mat = [[r["matrix"][f"{p}<-{s}"] for s in C.MODELS] for p in C.MODELS]
        ax.imshow(mat, cmap=RAMP, vmin=0, vmax=vmax)
        for a in range(2):
            for b in range(2):
                ax.text(b, a, f"{mat[a][b]:.2f}", ha="center", va="center", fontsize=9, color="white" if mat[a][b] > 0.6 * vmax else INK,
                        fontweight="bold" if a == b else None)
        ax.set_xticks([0, 1])
        ax.set_xticklabels([f"{NAME[s]} source" for s in C.MODELS], fontsize=8)
        ax.set_yticks([0, 1])
        ax.set_yticklabels([f"{NAME[p]} predicts" for p in C.MODELS] if ax is axes[0] else ["", ""], fontsize=8)
        ax.set_title(f"{i}, {d}: self adv. {r['self_advantage']:+.3f}", fontsize=8.5, loc="left", color=INK)
        ax.tick_params(length=0)
    fig.suptitle("Mean span conditional log loss (nats), averaged over k = 1..9; bold = self (diagonal). Positive self advantage = diagonal lower",
                 fontsize=9, x=0.02, ha="left", color=INK)
    _save(fig, out, "fig3_crossed_heatmaps")


def fig5_diagnostics(res, out: Path):
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.2))
    rows = [(s, i, d) for s in C.MODELS for i in C.INSTRUCTIONS for d in C.DIRECTIONS]
    for c, p in enumerate(C.MODELS):
        for r, (metric, lab) in enumerate((("valid_frac", "strict free-output validity"),
                                           ("mean_raw_mass", "teacher-forced raw face mass"))):
            ax = axes[r, c]
            mat = []
            for s, i, d in rows:
                cs = {x["k"]: x for x in _cells(res, predictor=p, source=s, source_instruction=i, direction=d)}
                mat.append([(int(cs[k]["free_valid"].split("/")[0]) / int(cs[k]["free_valid"].split("/")[1])) if metric == "valid_frac"
                            else cs[k]["mean_raw_mass"] for k in C.KS])
            im = ax.imshow(mat, cmap=RAMP, vmin=0, vmax=1, aspect="auto")
            for a, row in enumerate(mat):
                for b, v in enumerate(row):
                    ax.text(b, a, f"{v:.2f}", ha="center", va="center",
                            fontsize=6, color="white" if v > 0.6 else INK)
            ax.set_xticks(range(9))
            ax.set_xticklabels(C.KS, fontsize=7)
            ax.set_yticks(range(len(rows)))
            ax.set_yticklabels([f"{NAME[s]} {i} {ABBR[d]}" for s, i, d in rows] if c == 0 else [""] * len(rows), fontsize=7)
            if c == 0:
                ax.set_ylabel("ground truth (source, instruction, direction)", fontsize=7.5)
            ax.set_title(f"{NAME[p]} predicts: {lab}", fontsize=8.5, loc="left", color=INK)
            ax.tick_params(length=0)
            if r == 1:
                ax.set_xlabel("revealed count k")
    fig.colorbar(im, ax=axes, shrink=0.6)
    _save(fig, out, "fig5_validity_mass")


def fig6_examples(res, out: Path):
    pos = {(x["cell_id"], x["output_step"]): x for x in res["positions"]}
    prim = [c for c in res["cells"] if c["task_type"] == "primary"]
    picks = []
    for p in C.MODELS:
        mine = sorted([c for c in prim if c["predictor"] == p], key=lambda c: c["first_loss"])
        picks += [(mine[0], "lowest first-position loss"), (mine[-1], "highest first-position loss")]
    fig, axes = plt.subplots(1, 4, figsize=(12, 2.9), sharey=True)
    for ax, (c, why) in zip(axes, picks):
        x = pos[(c["cell_id"], 1)]
        cols = [BLUE if f == x["true_face"] else GREY for f in C.FACES]
        ax.bar(C.FACES, x["p6"], color=cols, width=0.7)
        _grid(ax)
        ax.set_ylim(0, 1)
        ax.set_xticks(C.FACES)
        ax.set_title(f"{c['cell_id']}\n{why}; true {x['true_face']} at pos {x['original_position']}", fontsize=7.5, loc="left", color=INK)
        ax.text(0.98, 0.95, f"loss {x['cond_loss']:.2f}\nmass {x['raw_mass']:.2f}\nfree: {c['free_output'][:14]!r}", transform=ax.transAxes,
                ha="right", va="top", fontsize=7, color=INK2)
    axes[0].set_ylabel("six-face p (first missing)")
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=BLUE, label="true face"), Patch(color=GREY, label="other faces")], frameon=False, ncol=2,
               fontsize=8, loc="lower center", bbox_to_anchor=(0.5, -0.08))
    _save(fig, out, "fig6_example_distributions")


def fig7_middle(res, out: Path):
    tab = res["middle"]["table"]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 3.6), gridspec_kw=dict(width_ratios=[1.6, 1]))
    keys = [(p, s, i) for i in C.INSTRUCTIONS for s in C.MODELS for p in C.MODELS]
    for j, (part, col) in enumerate((("early_1_2", BLUE), ("late_9_10", ORANGE))):
        vals = [next(t["mean_cond_loss"] for t in tab if t["part"] == part and (t["predictor"], t["source"], t["source_instruction"]) == key)
                for key in keys]
        ax.bar([x + (j - 0.5) * 0.38 for x in range(len(keys))], vals, width=0.36, color=col,
               label="early pair (positions 1, 2)" if j == 0 else "late pair (positions 9, 10)")
    _grid(ax)
    ax.axhline(LN6, color=MUTED, ls=":", lw=1)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([f"{NAME[p][0]}<-{NAME[s][0]} {i}" + ("\nself" if p == s else "") for p, s, i in keys], fontsize=7.5)
    ax.set_ylabel("mean conditional log loss (nats)")
    ax.set_xlabel("predictor <- source, instruction (Q = Qwen, M = Mistral)")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Supplementary middle-anchored arm (reveal 3-8); not part of the primary results", fontsize=8.5, loc="left", color=INK)
    rows = [m for m in res["middle"]["contrasts"]]
    ax2.axis("off")
    ax2.text(0, 1, "Balanced self advantage (nats; + = self lower)", fontsize=8.5, color=INK, va="top")
    for n, m in enumerate(rows):
        ax2.text(0, 0.86 - n * 0.13, f"{m['part']:<10} {m['source_instruction']}:  {m['self_advantage']:+.3f}   "
                 f"(Q self-other {m['qwen_self_minus_other']:+.2f}, M {m['mistral_self_minus_other']:+.2f})",
                 fontsize=7.5, color=INK2, va="top", family="monospace")
    _save(fig, out, "fig7_middle_anchored")


def all_figures(res: dict, out: Path):
    out = Path(out)
    fig1_design(res, out)
    _kcurves(res, out, "mean_loss", "mean span loss (nats)", "fig2_forward_backward_by_k", "Mean conditional log loss over the missing span")
    fig3_crossed(res, out)
    _kcurves(res, out, "first_loss", "first missing position loss (nats)", "fig4_first_missing_by_k",
             "First missing output position: forward = roll k+1 (boundary), backward = roll 1")
    fig5_diagnostics(res, out)
    fig6_examples(res, out)
    fig7_middle(res, out)
