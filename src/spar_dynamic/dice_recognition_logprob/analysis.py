"""Offline summaries, benchmarks and figures for LOULA_DICE_AB_LOGPROB v2.1. No GPU or network.

Units are items (calibration) and pair ids (recognition); the two orientations of a unit are never treated as
independent observations. Deterministic forward passes are not resampled.
"""

from __future__ import annotations

import collections
import csv
import json
import math

import numpy as np

from spar_dynamic.dice_recognition import features as F
from spar_dynamic.dice_recognition_logprob import config as C

COL = {"MORE_SIXES": "#2a78d6", "MORE_REPEATS": "#eb6834", "GEN_RULE": "#1baa7a",
       "AUTH": "#2a78d6", "TYP": "#eb6834", "NAMED_QWEN": "#8a5cd6"}
INK, INK2, GRID, BAND = "#0b0b0b", "#52514e", "#e4e3df", "#efeeea"
TASK_LABEL = {"MORE_SIXES": "more 6s", "MORE_REPEATS": "more adjacent\nrepeats", "GEN_RULE": "which is from\ngenerator R"}
KIND_LABEL = {"AUTH": "AUTH\n(own model)", "TYP": "TYP\n(typical of me)", "NAMED_QWEN": "NAMED\n(Qwen3-32B)"}


def jsonl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def write_csv(path, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def bootstrap_mean(values, seed=C.BOOTSTRAP_SEED, n=C.BOOTSTRAP_N):
    v = np.asarray(values, dtype=float)
    if len(v) == 0:
        return dict(point=None, lo=None, hi=None, n=0)
    idx = np.random.default_rng(seed).integers(0, len(v), size=(n, len(v)))
    bs = v[idx].mean(axis=1)
    return dict(point=float(v.mean()), lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)), n=len(v))


def describe(rows, eps):
    s = [r["S_X"] for r in rows]
    return dict(n=len(rows), favors_X=sum(r["outcome"] == "X" for r in rows), favors_Y=sum(r["outcome"] == "Y" for r in rows),
                indeterminate=sum(r["outcome"] == "indeterminate" for r in rows),
                both_orders_X=sum(r["both_orders_X"] for r in rows), both_orders_Y=sum(r["both_orders_Y"] for r in rows),
                orientation_sensitive=sum(r["orientation_sensitive"] for r in rows),
                mean_S=bootstrap_mean(s), median_S=float(np.median(s)), min_S=float(min(s)), max_S=float(max(s)),
                prop_favors_X=bootstrap_mean([r["outcome"] == "X" for r in rows]),
                mean_B_pair=float(np.mean([r["B_pair"] for r in rows])),
                median_abs_B_pair=float(np.median([abs(r["B_pair"]) for r in rows])),
                max_abs_B_pair=float(max(abs(r["B_pair"]) for r in rows)),
                mass_AB_min=float(min(min(r["mass_AB_XA"], r["mass_AB_XB"]) for r in rows)),
                mass_AB_median=float(np.median([m for r in rows for m in (r["mass_AB_XA"], r["mass_AB_XB"])])),
                greedy_argmax_A_rate=float(np.mean([a == "A" for r in rows for a in (r["argmax_XA"], r["argmax_XB"])])),
                greedy_argmax_correct=sum(r["greedy_picks_X_XA"] + r["greedy_picks_X_XB"] for r in rows),
                greedy_argmax_consistent=sum(r["greedy_picks_X_XA"] == r["greedy_picks_X_XB"] for r in rows),
                epsilon=eps)


# ------------------------------------------------------------------------------- historical benchmarks --
def exp23_qwen_by_item(responses_path=C.SOURCES["exp23_responses"]):
    """Experiment 23's emitted Qwen answers per item and format (historical, different serving)."""
    out = collections.defaultdict(dict)
    for r in csv.DictReader(open(responses_path, encoding="utf-8")):
        if r["judge"] != "qwen":
            continue
        out[r["item_id"]][f"{r['fmt']}_{r['orientation']}"] = r["choice"] if r["valid"] == "True" else "invalid"
    return out


def exp23_gate_table(path=C.SOURCES["exp23_gate_table"]):
    return {f"{r['judge']}|{r['fmt']}": r for r in csv.DictReader(open(path, encoding="utf-8"))}


def classifier_margins(pairs, gate_path=C.SOURCES["classifier_gate"]):
    """Experiment 22 frozen classifier: logit P(qwen | qwen_seq) - logit P(qwen | mistral_seq) per pair."""
    fm = json.load(open(gate_path, encoding="utf-8"))["frozen_model"]

    def logit(seq):
        f = F.features([int(x) for x in seq.split()])
        z = (np.array([f[k] for k in fm["features"]]) - np.array(fm["mean"])) / np.array(fm["scale"])
        return float(z @ np.array(fm["coef"]) + fm["intercept"])
    return {p["pair_id"]: logit(p["qwen_seq"]) - logit(p["mistral_seq"]) for p in pairs}


def exp22_qwen_emitted(path=C.SOURCES["exp22_responses"]):
    out = collections.defaultdict(dict)
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if r["judge"] == "qwen" and r["condition"] in ("self", "named_qwen"):
            out[r["pair_id"]][f"{r['condition']}_{r['orientation']}"] = r["choice"]
    return out


# ------------------------------------------------------------------------------------------ summaries --
def calibration_summary(rows, gate):
    by_item23 = exp23_qwen_by_item()
    gt = exp23_gate_table()
    per = {t: describe([r for r in rows if r["kind"] == t], gate["epsilon"]) for t in C.TASKS}
    hist = {}
    for fmt in ("bare", "brief"):
        g = gt[f"qwen|{fmt}"]
        hist[fmt] = {t: dict(correct_of_24=int(g[f"{t}_correct"]), consistent_of_12=int(g[f"{t}_consistent_pairs"]),
                             A_rate=float(g[f"{t}_A_rate"])) for t in C.TASKS}
    for r in rows:
        e = by_item23.get(r["unit_id"], {})
        for fmt in ("bare", "brief"):
            r[f"exp23_{fmt}_XA"] = e.get(f"{fmt}_XA")
            r[f"exp23_{fmt}_XB"] = e.get(f"{fmt}_XB")
            r[f"exp23_{fmt}_both_correct"] = e.get(f"{fmt}_XA") == "A" and e.get(f"{fmt}_XB") == "B"
    item_cmp = {fmt: dict(scored_correct_and_exp23_both=sum(r["outcome"] == "X" and r[f"exp23_{fmt}_both_correct"] for r in rows),
                          scored_correct_only=sum(r["outcome"] == "X" and not r[f"exp23_{fmt}_both_correct"] for r in rows),
                          exp23_both_only=sum(r["outcome"] != "X" and r[f"exp23_{fmt}_both_correct"] for r in rows),
                          neither=sum(r["outcome"] != "X" and not r[f"exp23_{fmt}_both_correct"] for r in rows))
                for fmt in ("bare", "brief")}
    # does S track the size of the content difference? (descriptive)
    size = {t: [(r_X - r_Y, r["S_X"]) for r in rows if r["kind"] == t for r_X, r_Y in [_counts(r, t)]] for t in C.TASKS}
    return dict(per_task=per, overall=describe(rows, gate["epsilon"]), gate=gate, exp23_qwen_emitted=hist,
                item_level_vs_exp23=item_cmp, S_by_count_difference={t: _by_diff(v) for t, v in size.items()})


def _counts(r, task):
    from spar_dynamic.dice_recognition_v2 import synthetic as S
    f = S.n_sixes if task == "MORE_SIXES" else S.n_repeats
    return f([int(x) for x in r["X"].split()]), f([int(x) for x in r["Y"].split()])


def _by_diff(v):
    out = collections.defaultdict(list)
    for d, s in v:
        out[d].append(s)
    return {str(d): dict(n=len(s), mean_S=float(np.mean(s)), min_S=float(min(s))) for d, s in sorted(out.items())}


def screen_summary(rows, pairs, eps):
    margins = classifier_margins(pairs)
    emitted = exp22_qwen_emitted()
    per_kind = {}
    for k in ("AUTH", "TYP"):
        per_kind[k] = describe([r for r in rows if r["kind"] == k], eps)
    named = [r for r in rows if r["kind"] == "NAMED_QWEN"]
    by_pair = collections.defaultdict(dict)
    for r in rows:
        key = r["kind"] if r["kind"] != "NAMED_QWEN" else f"NAMED_QWEN|{r['name_order']}"
        by_pair[r["unit_id"]][key] = r["S_X"]
    pids = sorted(by_pair)
    out = dict(epsilon=eps, per_kind=per_kind, n_pairs=len(pids))
    if named:
        per_kind["NAMED_QWEN"] = describe(named, eps)
        for no in C.NAME_ORDERS:
            per_kind[f"NAMED_QWEN|{no}"] = describe([r for r in named if r["name_order"] == no], eps)
        nm = {p: 0.5 * (by_pair[p]["NAMED_QWEN|QM"] + by_pair[p]["NAMED_QWEN|MQ"]) for p in pids}
        out["named_pair_mean_S"] = bootstrap_mean([nm[p] for p in pids])
        out["named_name_order_effect_QM_minus_MQ"] = bootstrap_mean([by_pair[p]["NAMED_QWEN|QM"] - by_pair[p]["NAMED_QWEN|MQ"] for p in pids])
        out["AUTH_minus_NAMED"] = bootstrap_mean([by_pair[p]["AUTH"] - nm[p] for p in pids])
        out["corr_AUTH_NAMED"] = _corr([by_pair[p]["AUTH"] for p in pids], [nm[p] for p in pids])
    else:
        out["named_arm"] = "NOT_RUN"
    out["AUTH_minus_TYP"] = bootstrap_mean([by_pair[p]["AUTH"] - by_pair[p]["TYP"] for p in pids])
    out["corr_AUTH_TYP"] = _corr([by_pair[p]["AUTH"] for p in pids], [by_pair[p]["TYP"] for p in pids])
    cls = {}
    for k in [k for k in ("AUTH", "TYP", "NAMED_QWEN") if k in per_kind]:
        s = {p: (by_pair[p][k] if k != "NAMED_QWEN" else 0.5 * (by_pair[p]["NAMED_QWEN|QM"] + by_pair[p]["NAMED_QWEN|MQ"])) for p in pids}
        det = [p for p in pids if abs(s[p]) > eps and margins[p] != 0]      # classifier ties (identical features) excluded
        cls[k] = dict(n_determinate=len(det), agree_with_classifier_sign=sum((s[p] > 0) == (margins[p] > 0) for p in det),
                      corr_S_with_classifier_margin=_corr([s[p] for p in pids], [margins[p] for p in pids]))
    out["classifier"] = dict(pairs_classifier_correct=sum(m > 0 for m in margins.values()),
                             pairs_classifier_tied=sum(m == 0 for m in margins.values()), margins=margins, by_kind=cls)
    out["exp22_emitted_qwen"] = {p: emitted.get(p, {}) for p in pids}
    out["by_pair"] = {p: dict(by_pair[p], classifier_margin=margins[p]) for p in pids}
    return out


def _corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 3 or a.std() == 0 or b.std() == 0:
        return None
    ra, rb = a.argsort().argsort(), b.argsort().argsort()
    return dict(pearson=float(np.corrcoef(a, b)[0, 1]), spearman=float(np.corrcoef(ra, rb)[0, 1]))


# --------------------------------------------------------------------------------------------- figures --
def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                         "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})
    return plt


def _save(fig, path):
    import matplotlib.pyplot as plt
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_strip(rows, kinds, labels, eps, path, title, ylabel):
    """Order-corrected S per unit, one column per task/frame; the gray band is the indeterminate zone."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(1.9 * len(kinds) + 1.6, 3.8))
    rng = np.random.default_rng(0)
    for i, k in enumerate(kinds):
        s = np.array([r["S_X"] for r in rows if r["kind"] == k])
        x = i + rng.uniform(-0.18, 0.18, len(s))
        ax.scatter(x, s, s=34, color=COL[k], edgecolor="white", linewidth=1.2, zorder=3)
        if len(s):
            ax.hlines(np.median(s), i - 0.3, i + 0.3, color=INK, lw=1.6, zorder=4)
            n_pos, n_neg = int((s > eps).sum()), int((s < -eps).sum())
            ax.text(i, 1.0, f"{n_pos} favour X · {n_neg} favour Y · {len(s) - n_pos - n_neg} tie",
                    transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=7, color=INK2)
    ax.axhspan(-eps, eps, color=BAND, zorder=1)
    ax.axhline(0, color=INK2, lw=0.8, zorder=2)
    ax.set_xticks(range(len(kinds)), [labels[k] for k in kinds])
    ax.set_xlim(-0.6, len(kinds) - 0.4)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.set_title(title, fontsize=9, color=INK, loc="left", pad=16)
    _save(fig, path)


def fig_orders(rows, kinds, labels, eps, path, title, xlabel, ylabel):
    """Preference for X when X is shown as A vs when X is shown as B. On the diagonal: no order bias."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(4.8, 4.4))
    v = [abs(r[c]) for r in rows for c in ("pref_X_as_A", "pref_X_as_B")]
    lim = max(v + [1.0]) * 1.08
    ax.axvspan(-eps, eps, color=BAND, zorder=0)
    ax.axhspan(-eps, eps, color=BAND, zorder=0)
    ax.plot([-lim, lim], [-lim, lim], color=INK2, lw=0.8, ls=":", zorder=1)
    ax.axhline(0, color=INK2, lw=0.6)
    ax.axvline(0, color=INK2, lw=0.6)
    for k in kinds:
        rs = [r for r in rows if r["kind"] == k]
        ax.scatter([r["pref_X_as_A"] for r in rs], [r["pref_X_as_B"] for r in rs], s=30, color=COL[k], edgecolor="white",
                   linewidth=1.1, label=labels[k].replace("\n", " "), zorder=3)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.text(0.98, 0.98, "X preferred in\nboth orders", transform=ax.transAxes, ha="right", va="top", fontsize=7, color=INK2)
    ax.text(0.02, 0.02, "Y preferred in\nboth orders", transform=ax.transAxes, ha="left", va="bottom", fontsize=7, color=INK2)
    ax.text(0.02, 0.98, "always B", transform=ax.transAxes, ha="left", va="top", fontsize=7, color=INK2)
    ax.text(0.98, 0.02, "always A", transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color=INK2)
    ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3)
    ax.set_title(title, fontsize=9, color=INK, loc="left")
    _save(fig, path)


def fmt_ci(b, nd=2):
    if b is None or b.get("point") is None:
        return "NA"
    return f"{b['point']:+.{nd}f} [{b['lo']:+.{nd}f}, {b['hi']:+.{nd}f}]"


def is_finite(x):
    return x is not None and not (isinstance(x, float) and math.isnan(x))
