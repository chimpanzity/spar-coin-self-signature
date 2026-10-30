"""v2 measurement diagnostics, estimands and figures (handoff section 8).

Unit = calibration item (Stage A), Experiment 22 pair (Stage B) or pair family (Stages C-D). Accuracy is averaged
over a unit's valid orientations first, then over units; invalid answers are excluded and counted. Orientation
consistency = the same candidate chosen in both orientations (needs both valid). Uncertainty: 10,000 bootstrap
resamples of units, drawn once per stage family set and applied jointly to every cell and contrast, so paired
comparisons keep their pairing. No p-values.
"""

from __future__ import annotations

import collections
import re

import numpy as np

from spar_dynamic.dice_recognition import features as F1
from spar_dynamic.dice_recognition_v2 import config as C

COL = {"qwen": "#2a78d6", "mistral": "#eb6834"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


# --------------------------------------------------------------------------------------- frozen classifier --
def logit_qwen(seq, fm):
    f = F1.features([int(x) for x in seq.split()])
    z = (np.array([f[k] for k in fm["features"]]) - np.array(fm["mean"])) / np.array(fm["scale"])
    return float(z @ np.array(fm["coef"]) + fm["intercept"])


def classifier_pair(qwen_blocks, mistral_blocks, fm):
    """Predeclared K-block rule: sum of per-block Qwen logits; the candidate with the larger sum is called Qwen.
    Returns 1 (correct), 0 (wrong) or 0.5 (tie)."""
    q, m = sum(logit_qwen(s, fm) for s in qwen_blocks), sum(logit_qwen(s, fm) for s in mistral_blocks)
    return 1.0 if q > m else 0.5 if q == m else 0.0


# ------------------------------------------------------------------------------------------ unit tables --
def chosen(r):
    if not r["valid"]:
        return None
    if r["orientation"] in ("XA", "XB"):
        return "X" if (r["orientation"] == "XA") == (r["choice"] == "A") else "Y"
    return r["A_source"] if r["choice"] == "A" else r["B_source"]


def unit_table(resps, key, unit="unit_id"):
    """{cell: {unit: dict(acc, consistent, n, n_valid, n_A)}}; consistency within (cell, unit) across orientations."""
    g = collections.defaultdict(list)
    for r in resps:
        g[(key(r), r[unit])].append(r)
    out = collections.defaultdict(dict)
    for (cell, u), rs in g.items():
        v = [r for r in rs if r["valid"]]
        ch = {r["orientation"]: chosen(r) for r in v}
        out[cell][u] = dict(acc=float(np.mean([r["is_correct"] for r in v])) if v else None, n=len(rs), n_valid=len(v),
                            n_A=sum(r["choice"] == "A" for r in v),
                            consistent=(len(set(ch.values())) == 1) if len(ch) == 2 else None)
    return out


def cell_summary(cells):
    """Pooled descriptives per cell (not bootstrapped)."""
    s = {}
    for cell, units in cells.items():
        n = sum(u["n"] for u in units.values())
        nv = sum(u["n_valid"] for u in units.values())
        cons = [u["consistent"] for u in units.values() if u["consistent"] is not None]
        accs = [u["acc"] for u in units.values() if u["acc"] is not None]
        s[cell] = dict(n_calls=n, n_valid=nv, validity=nv / n if n else None,
                       A_rate=sum(u["n_A"] for u in units.values()) / nv if nv else None,
                       accuracy=float(np.mean(accs)) if accs else None,
                       orientation_consistency=float(np.mean(cons)) if cons else None, n_consistency_units=len(cons))
    return s


def bootstrap(series, units, derived=None, seed=C.SEEDS["bootstrap"], n=C.N_BOOTSTRAP):
    """series: {name: {unit: value or None}}; derived: {name: f(dict name -> array)} evaluated on cell means.
    Returns {name: dict(point, lo, hi)}; all names share one resample matrix."""
    units = list(units)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(units), size=(n, len(units)))
    pts, bs = {}, {}
    for k, d in series.items():
        v = np.array([np.nan if d.get(u) is None else float(d[u]) for u in units])
        pts[k] = np.nanmean(v) if np.isfinite(v).any() else np.nan
        with np.errstate(all="ignore"):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                bs[k] = np.nanmean(v[idx], axis=1)
    for k, f in (derived or {}).items():
        try:
            pts[k] = float(f({kk: np.array([vv]) for kk, vv in pts.items()})[0])
            bs[k] = f(bs)
        except KeyError:
            pts[k], bs[k] = np.nan, np.full(n, np.nan)
    out = {}
    for k in pts:
        b = bs[k][np.isfinite(bs[k])]
        out[k] = dict(point=None if not np.isfinite(pts[k]) else float(pts[k]),
                      lo=float(np.percentile(b, 2.5)) if len(b) else None,
                      hi=float(np.percentile(b, 97.5)) if len(b) else None)
    return out


def series_of(cells, field):
    return {cell: {u: (None if v[field] is None else float(v[field])) for u, v in units.items()} for cell, units in cells.items()}


# ---------------------------------------------------------------------------------------- Stage A gate --
def calibration_gate(resps):
    by = collections.defaultdict(list)
    for r in resps:
        by[(r["judge"], r["fmt"])].append(r)
    gate = {}
    for (j, fmt), rs in sorted(by.items()):
        cells = unit_table(rs, lambda r: r["task"], unit="item_id")
        row = dict(judge=j, fmt=fmt, n_calls=len(rs), n_valid=sum(r["valid"] for r in rs))
        row["validity"] = row["n_valid"] / row["n_calls"]
        ok = row["validity"] >= C.MIN_FORMAT_VALIDITY
        for task in C.CAL_TASKS:
            trs = [r for r in rs if r["task"] == task]
            corr = sum(bool(r["is_correct"]) for r in trs)
            cons = sum(bool(u["consistent"]) for u in cells[task].values())
            g = C.GATES[task]
            p = corr >= g["min_correct"] and cons >= g["min_consistent"]
            row[task] = dict(correct=corr, of=len(trs), consistent_pairs=cons, of_pairs=len(cells[task]),
                             A_rate=float(np.mean([r["choice"] == "A" for r in trs if r["valid"]])) if any(r["valid"] for r in trs) else None,
                             pass_=p)
            ok &= p
        row["PASS"] = bool(ok)
        gate[f"{j}|{fmt}"] = row
    return gate


# ----------------------------------------------------------------------------------- evidence (brief) --
_NUM = r"(\d+|zero|no|one|two|three|four|five|six|seven|eight|nine|ten)"
_WORDNUM = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten".split())}
_WORDNUM["no"] = 0
_CLAIM = re.compile(r"(?:Sample\s+)?\b([AB])\b(?:[^.;\n]{0,30}?)\b" + _NUM +
                    r"\b\s*(?:sixes|6s|6's|occurrences|instances|times|adjacent|repeat|repeats|consecutive|pairs?)", re.I)
_FEATURE = re.compile(r"\b(\d|six|repeat|repeated|consecutive|adjacent|frequen|count|occur|appears?|times|order|"
                      r"pattern|sequence|variety|distribut|start|begin|end|position)\w*", re.I)


def observation(text):
    lines = [l for l in (text or "").strip().splitlines() if l.strip()]
    return "\n".join(lines[:-1])


def evidence_check(r, true_counts=None):
    """Descriptive only. cites_feature: the observation names a number or a sequence feature. For count tasks,
    claimed per-sample counts are compared with the truth: verified / contradicted / unverifiable."""
    obs = observation(r.get("content"))
    out = dict(cites_feature=bool(_FEATURE.search(obs)), claim="unverifiable")
    if true_counts:
        claims = [(m.group(1).upper(), m.group(2).lower()) for m in _CLAIM.finditer(obs)]
        claims = [(s, int(n) if n.isdigit() else _WORDNUM[n]) for s, n in claims]
        if claims:
            out["claim"] = "verified" if all(true_counts[s] == n for s, n in claims) else "contradicted"
    return out


# ---------------------------------------------------------------------------------------- phenotypes --
def phenotype(seqs):
    S = np.array([[int(x) for x in s.split()] for s in seqs])
    reps = [sum(a == b for a, b in zip(r, r[1:])) for r in S]
    big = collections.Counter((a, b) for r in S for a, b in zip(r, r[1:]))
    pos_mode = []
    for k in range(10):
        c = collections.Counter(S[:, k])
        f, n = c.most_common(1)[0]
        pos_mode.append(f"{f} ({n / len(S):.0%})")
    return dict(n=len(S), face_share={f: float(np.mean(S == f)) for f in range(1, 7)},
                mean_adjacent_repeats=float(np.mean(reps)), share_no_repeat=float(np.mean([x == 0 for x in reps])),
                share_all_six_faces=float(np.mean([len(set(r)) == 6 for r in S])),
                modal_face_by_position=pos_mode, top_bigrams=[(f"{a}{b}", n) for (a, b), n in big.most_common(6)],
                unique_strings=len(set(seqs)), modal_string=collections.Counter(seqs).most_common(1)[0])


# -------------------------------------------------------------------------------------------- figures --
def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                         "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})
    return plt


def _finish(fig, ax_list, path):
    for ax in ax_list:
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    import matplotlib.pyplot as plt
    plt.close(fig)


def fig_calibration(gate, path):
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6))
    tasks = list(C.CAL_TASKS)
    for ax, metric, lab in zip(axes, ("acc", "cons"), ("accuracy (of 24 presentations)", "same candidate in both orders (of 12)")):
        k = 0
        for j in C.SOURCES:
            for fmt in C.FORMATS:
                row = gate.get(f"{j}|{fmt}")
                if not row:
                    continue
                v = [row[t]["correct"] / row[t]["of"] if metric == "acc" else row[t]["consistent_pairs"] / row[t]["of_pairs"] for t in tasks]
                xs = np.arange(3) + (k - 1.5) * 0.2
                ax.bar(xs, v, width=0.19, color=COL[j], alpha=1.0 if fmt == "brief" else 0.45,
                       label=f"{C.MODELS[j]['display']}, {fmt}{' (PASS)' if row['PASS'] else ' (FAIL)'}")
                k += 1
        th = [C.GATES[t]["min_correct"] / 24 if metric == "acc" else C.GATES[t]["min_consistent"] / 12 for t in tasks]
        for i, t in enumerate(th):
            ax.hlines(t, i - 0.45, i + 0.45, color=INK, ls="--", lw=1)
        ax.axhline(0.5 if metric == "acc" else 0, color=INK2, ls=":", lw=1)
        ax.set_xticks(range(3), ["more 6s", "more\nadjacent repeats", "which is\nfrom generator R"])
        ax.set_ylim(0, 1.05)
        ax.set_ylabel(lab)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=7, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.06))
    axes[0].set_title("Stage A calibration (dashed = gate threshold)", fontsize=9, color=INK, loc="left")
    _finish(fig, axes, path)


def fig_cells(summ, keys, labels, path, title, ci=None):
    """Three panels: A-choice rate, orientation consistency, accuracy (with CI when given)."""
    plt = _plt()
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    xs = np.arange(len(keys))
    cols = [COL[k.split("|")[0]] for k in keys]
    for ax, f, lab, ref in zip(axes, ("A_rate", "orientation_consistency", "accuracy"),
                               ("share answering A", "same sequence chosen in both orders", "accuracy vs own source"),
                               (0.5, None, 0.5)):
        v = [summ[k][f] if summ.get(k) and summ[k][f] is not None else np.nan for k in keys]
        ax.bar(xs, v, color=cols, width=0.7)
        if f == "accuracy" and ci:
            lo = [v[i] - ci[k]["lo"] if ci.get(k) and ci[k]["lo"] is not None else 0 for i, k in enumerate(keys)]
            hi = [ci[k]["hi"] - v[i] if ci.get(k) and ci[k]["hi"] is not None else 0 for i, k in enumerate(keys)]
            ax.errorbar(xs, v, yerr=[lo, hi], fmt="none", ecolor=INK2, lw=1, capsize=2)
        if ref is not None:
            ax.axhline(ref, color=INK2, ls=":", lw=1)
        ax.set_xticks(xs, labels, rotation=45, ha="right", fontsize=7)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel(lab)
    axes[0].set_title(title, fontsize=9, color=INK, loc="left")
    _finish(fig, axes, path)


def fig_dose(boot, cls_by_k, judges, path):
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    for ax, metric, lab in zip(axes, ("acc", "cons"), ("accuracy vs own source", "same sequence chosen in both orders")):
        for j in judges:
            for frame, ls, mk in (("AUTH", "-", "o"), ("TYP", "--", "s")):
                ks = [f"{metric}|{j}|{frame}|K{K}" for K in C.DOSES]
                if not all(k in boot for k in ks):
                    continue
                y = [boot[k]["point"] for k in ks]
                lo = [y[i] - boot[k]["lo"] for i, k in enumerate(ks)]
                hi = [boot[k]["hi"] - y[i] for i, k in enumerate(ks)]
                off = (0.06 if frame == "TYP" else -0.06) + (0.02 if j == "mistral" else -0.02)
                ax.errorbar(np.array(C.DOSES) + off, y, yerr=[lo, hi], color=COL[j], ls=ls, marker=mk, ms=5, lw=1.6,
                            capsize=2, label=f"{C.MODELS[j]['display']} {frame}")
        if metric == "acc":
            ax.plot(C.DOSES, [cls_by_k[K]["point"] for K in C.DOSES], color=INK, lw=1, ls="-.", marker="^",
                    label="external classifier")
            ax.axhline(0.5, color=INK2, ls=":", lw=1)
        ax.set_xticks(C.DOSES, [f"K={K}\n({10 * K} rolls)" for K in C.DOSES])
        ax.set_ylim(-0.02, 1.05)
        ax.set_ylabel(lab)
    axes[0].legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(1.05, -0.2), ncol=5)
    axes[0].set_title("Stage C: evidence dose (95% family bootstrap)", fontsize=9, color=INK, loc="left")
    _finish(fig, axes, path)


def fig_corpus(phen, cls_by_k, path):
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))
    for j_i, m in enumerate(C.SOURCES):
        v = [phen[m]["face_share"][f] for f in range(1, 7)]
        axes[0].bar(np.arange(1, 7) + (j_i - 0.5) * 0.38, v, width=0.36, color=COL[m],
                    label=f"{C.MODELS[m]['display']} ({phen[m]['unique_strings']} unique / {phen[m]['n']})")
    axes[0].axhline(1 / 6, color=INK2, ls=":", lw=1)
    axes[0].set_xlabel("face")
    axes[0].set_ylabel("share of all rolls")
    axes[0].legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=1)
    y = [cls_by_k[K]["point"] for K in C.DOSES]
    lo = [y[i] - cls_by_k[K]["lo"] for i, K in enumerate(C.DOSES)]
    hi = [cls_by_k[K]["hi"] - y[i] for i, K in enumerate(C.DOSES)]
    axes[1].errorbar(C.DOSES, y, yerr=[lo, hi], color=INK, marker="o", capsize=3)
    axes[1].axhline(0.5, color=INK2, ls=":", lw=1)
    axes[1].set_xticks(C.DOSES, [f"K={K}" for K in C.DOSES])
    axes[1].set_ylim(0, 1.05)
    axes[1].set_ylabel("frozen classifier pair accuracy")
    axes[1].set_title("v1 development classifier on v2 families", fontsize=9, color=INK)
    _finish(fig, axes, path)


def fig_bars(boot, keys, labels, colors, path, title, ref=0.5, ylabel="accuracy (95% family bootstrap)", ylim=(0, 1.05)):
    plt = _plt()
    fig, ax = plt.subplots(figsize=(max(4, 0.7 * len(keys) + 1.5), 3.4))
    xs = np.arange(len(keys))
    y = [boot[k]["point"] if boot.get(k) and boot[k]["point"] is not None else np.nan for k in keys]
    lo = [y[i] - boot[k]["lo"] if boot.get(k) and boot[k]["lo"] is not None else 0 for i, k in enumerate(keys)]
    hi = [boot[k]["hi"] - y[i] if boot.get(k) and boot[k]["hi"] is not None else 0 for i, k in enumerate(keys)]
    ax.bar(xs, y, color=colors, width=0.7)
    ax.errorbar(xs, y, yerr=[lo, hi], fmt="none", ecolor=INK2, lw=1, capsize=2)
    if ref is not None:
        ax.axhline(ref, color=INK2, ls=":", lw=1)
    ax.set_xticks(xs, labels, rotation=35, ha="right", fontsize=7)
    ax.set_ylim(*ylim)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=9, color=INK, loc="left")
    _finish(fig, [ax], path)
