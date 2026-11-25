"""Figure for Experiment 37, drawn from results/paired_changes.csv (added after the run; no model calls)."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

E = Path(__file__).resolve().parent
R = list(csv.DictReader(open(E / "results" / "paired_changes.csv", encoding="utf-8")))
ARM = {"A": "#2a78d6", "B": "#c8571b", "neutral": "#7a7a7a"}
RO = (("agent_agent_probe_change", "Frozen forecast probe"), ("agent_raw_output_change", "Raw forecast log odds"), ("agent_direct_probe_change", "Frozen generation-state probe"))
fig, ax = plt.subplots(3, 3, figsize=(9.6, 8.6), sharex=True)
for i, (a, c) in enumerate(ARM.items()):
    q = [r for r in R if r["arm"] == a]
    for j, (k, lab) in enumerate(RO):
        x = ax[i][j]
        x.scatter([float(r["actual_change"]) for r in q], [float(r[k]) for r in q], s=7, color=c, alpha=0.55, linewidths=0)
        x.axhline(0, color="#bbbbbb", lw=0.8)
        x.axvline(0, color="#bbbbbb", lw=0.8)
        lim = {0: 32, 1: 8, 2: 8}[j]
        x.set_ylim(-lim, lim)
        x.plot([-8, 8], [-8, 8], color="#444444", lw=0.9, ls="--")
        x.set_title(f"{lab}; {'arm ' + a if a != 'neutral' else 'neutral'}", fontsize=9, loc="left")
        for s in ("top", "right"):
            x.spines[s].set_visible(False)
        if i == 2:
            x.set_xlabel("Actual change in direct log odds", fontsize=8.5)
        if j == 0:
            x.set_ylabel("Readout change", fontsize=8.5)
fig.text(0.5, 0.004, "Each point is an unused-face pair on a held-out prefix (agent prompt). Dashed: readout change = actual change. Note the different vertical scale in the left column.", ha="center", fontsize=8, color="#555555")
fig.tight_layout(rect=(0, 0.02, 1, 1))
(E / "figures").mkdir(exist_ok=True)
fig.savefig(E / "figures" / "fig37_changes.png", dpi=170)
