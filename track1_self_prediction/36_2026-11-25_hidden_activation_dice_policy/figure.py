"""Figure for Experiment 36, drawn from results/losses.csv (added after the run; no model calls)."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

E = Path(__file__).resolve().parent
L = {(r["target"], r["model"]): float(r["loss"]) for r in csv.DictReader(open(E / "results" / "losses.csv", encoding="utf-8"))}
ROWS = [("Face bias", "face bias", None), ("History only", "history", None), ("History + output (Qwen)", "history+output qwen", None),
        ("  + Qwen forecast activations", "history+output+act qwen b75", "q"), ("History + output (Mistral)", "history+output mistral", None),
        ("  + Mistral forecast activations", "history+output+act mistral b75", "m"), ("Qwen forecast activations only", "act only qwen agent b75", "q"),
        ("Mistral forecast activations only", "act only mistral agent b75", "m"), ("Qwen direct activations only", "act only qwen direct b75", "q"),
        ("Mistral direct activations only", "act only mistral direct b75", "m")]
COL = {None: "#9a9a9a", "q": "#2a78d6", "m": "#c8571b"}
fig, ax = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
for a, t in zip(ax, ("qwen", "mistral")):
    for n, (lab, k, c) in enumerate(ROWS):
        v = L[t, k]
        a.barh(n, v, 0.62, color=COL[c])
        a.text(v, n, f" {v:.2f}", va="center", fontsize=8.5, color="#222222")
    a.axvline(L[t, "history"], color="#555555", lw=1, ls="--")
    a.set_title(f"Target: {t.capitalize()}'s direct policy (equal odds: {L[t, 'equal odds']:.2f})", fontsize=10, loc="left")
    a.set_yticks(range(len(ROWS)), [r[0] for r in ROWS], fontsize=9)
    a.set_xlim(0, L[t, "face bias"] * 1.14)
    a.set_xlabel("Held-out squared error, pairwise log odds (lower is better)", fontsize=9)
    for s in ("top", "right"):
        a.spines[s].set_visible(False)
ax[0].invert_yaxis()
fig.text(0.5, 0.005, "Dashed: history only. Blue: Qwen activations; orange: Mistral activations (75% depth). 432 prefixes, 18 held-out families.", ha="center", fontsize=8, color="#555555")
fig.tight_layout(rect=(0, 0.03, 1, 1))
(E / "figures").mkdir(exist_ok=True)
fig.savefig(E / "figures" / "fig36_losses.png", dpi=170)
