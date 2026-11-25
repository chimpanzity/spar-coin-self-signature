"""Post-run additions, not frozen: greedy-token counts and a relabelled copy of the primary figure. Reads raw/ and results/ only."""
import collections, csv, json
from pathlib import Path

E = Path(__file__).resolve().parents[1]
out = []
for m in ("qwen", "mistral"):
    for ph in ("core", "extensions"):
        rows = [json.loads(l) for l in open(E / f"raw/{m}/forecasts_{ph}.jsonl", encoding="utf-8")]
        for (tok, n) in collections.Counter(r["argmax_token"] for r in rows).most_common(8):
            out.append((m, ph, len(rows), repr(tok), n))
with open(E / "posthoc/greedy_tokens.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["checkpoint", "phase", "n_rows", "greedy_token", "count"])
    w.writerows(out)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
P = json.load(open(E / "results/summary.json", encoding="utf-8"))["core"]["primary"]
R = list(csv.DictReader(open(E / "results/core_pairs_primary.csv", encoding="utf-8")))
COL, LAB = {"qwen": "#2a6fb0", "mistral": "#c4562b", "joint": "0.2"}, {"qwen": "Qwen3-32B", "mistral": "Mistral Small 3.2"}
fig, ax = plt.subplots(1, 3, figsize=(13, 4), gridspec_kw=dict(width_ratios=[1, 1.5, 1.3]))
for x, n in enumerate(("qwen", "mistral", "joint")):
    for dx, e, mk in ((-.12, "T", "o"), (.12, "O", "s")):
        s = P[f"{n}_{e}"]
        ax[0].plot([x + dx] * 2, s["ci95"], color=COL[n], lw=1.2)
        ax[0].plot(x + dx, s["mean"], mk, color=COL[n], mfc="white" if e == "O" else COL[n], ms=7)
ax[0].axhline(0, color="0.6", lw=.8); ax[0].set_xticks(range(3), ["Qwen", "Mistral", "joint"]); ax[0].set_ylabel("bits (JS)")
ax[0].set_title("A. Association test (filled),\nown improvement (open); 95% CI", loc="left", fontsize=9)
for dx, m in ((-.17, "qwen"), (.17, "mistral")):
    rr = [r for r in R if r["checkpoint"] == m]
    ax[1].bar([i + dx for i in range(6)], [float(r["directional_test"]) for r in rr], .3, color=COL[m], label=LAB[m])
    ax[1].plot([i + dx for i in range(6)], [float(r["own_improvement"]) for r in rr], "s", mfc="white", mec="k", ms=4)
    ax[2].plot([float(r["a"]) for r in rr], [float(r["S_left_minus_S_right"]) for r in rr], "o", color=COL[m], label=LAB[m])
    if m == "qwen":
        ax[1].set_xticks(range(6), [f"{r['left']}/{r['right']}" for r in rr], rotation=30, ha="right")
ax[1].axhline(0, color="0.6", lw=.8); ax[1].legend(frameon=False, fontsize=8)
ax[1].set_title("B. By pair: association test (bars),\nown improvement (squares)", loc="left", fontsize=9)
ax[2].axhline(0, color="0.6", lw=.8); ax[2].axvline(0, color="0.6", lw=.8); ax[2].legend(frameon=False, fontsize=8)
ax[2].set_xlabel("association contrast A(left) - A(right), nats"); ax[2].set_ylabel("S(left) - S(right), bits")
ax[2].set_title("C. Association vs selectivity\n(predicted: lower left to upper right)", loc="left", fontsize=9)
fig.tight_layout(); fig.savefig(E / "posthoc/fig33_primary_relabelled.png", dpi=160)
