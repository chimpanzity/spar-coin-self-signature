"""Experiment 38 figure: distance to the roll-(k+2) target by k, the index score, and p(realised roll k+2)."""

from __future__ import annotations

from spar_dynamic.slot_skip_ahead import design as D


def figure(desc, pri):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ink, mut = "#222222", "#777777"
    col = {"SLOT": "#2a78d6", "B": "#c8571b", "C": "#3a9a5b"}
    fig, axes = plt.subplots(3, 2, figsize=(9.6, 9.4), sharex=True)
    ks = list(D.KS)
    for j, m in enumerate(D.MODELS):
        d = {(r["condition"], r["k"]): r for r in desc if r["predictor"] == m}
        a = axes[0, j]
        for c in ("SLOT", "B"):
            a.plot(ks, [d[(c, k)]["d2_own"] for k in ks], "o-", color=col[c], label=f"{c} forecast")
        a.plot(ks, [d[("C", k)]["dc_own"] for k in ks], "o-", color=col["C"], label="C forecast (roll k+1 shown; conditional target)")
        a.plot(ks, [d[("SLOT", k)]["base_uniform"] for k in ks], ":", color=mut, label="uniform")
        a.plot(ks, [d[("SLOT", k)]["base_rule2"] for k in ks], "--", color=mut, label="two-step exhaustion rule")
        a.plot(ks, [d[("SLOT", k)]["base_T1_own"] for k in ks], "-.", color=ink, lw=1, label="own next-roll policy (mis-index)")
        a.set_title(f"{m.capitalize()}: JS to own roll-(k+2) target", fontsize=9.5, loc="left", color=ink)
        a.set_ylim(0, 1)
        a = axes[1, j]
        for c in ("SLOT", "B"):
            a.plot(ks, [d[(c, k)]["index"] for k in ks], "o-", color=col[c], label=c)
        a.axhline(0, color=mut, lw=0.8)
        a.set_title(f"{m.capitalize()}: index = JS to roll k+1 minus JS to roll k+2", fontsize=9.5, loc="left", color=ink)
        a = axes[2, j]
        for c in ("SLOT", "B", "C"):
            a.plot(ks, [d[(c, k)]["p_true_k2_own"] for k in ks], "o-", color=col[c], label=f"{c}, own sequences")
            a.plot(ks, [d[(c, k)]["p_true_k2_other"] for k in ks], "o--", color=col[c], mfc="white", label=f"{c}, other model's")
        a.set_title(f"{m.capitalize()}: p(realised roll k+2)", fontsize=9.5, loc="left", color=ink)
        a.set_ylim(0, 1)
        a.set_xlabel("rolls shown, k (target is roll k+2)", fontsize=8.5)
        a.set_xticks(ks)
    for a in axes.flat:
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
        a.tick_params(labelsize=8)
    axes[0, 1].legend(fontsize=7, frameon=False, loc="upper right")
    axes[1, 1].legend(fontsize=7, frameon=False)
    axes[2, 1].legend(fontsize=6.5, frameon=False, ncol=2)
    fig.tight_layout()
    (D.EXP / "figures").mkdir(exist_ok=True)
    fig.savefig(D.EXP / "figures" / "fig38_slot_by_k.png", dpi=170)
    fig.savefig(D.EXP / "figures" / "fig38_slot_by_k.pdf")
