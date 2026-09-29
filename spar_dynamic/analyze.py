"""Analysis: source phenotypes, model-identifiability classifier, judgment
self-advantage summaries, feature-distance baselines, and reports.
"""

import csv, json, math, os
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

import numpy as np

from . import config as C


# -------------------- source-level features --------------------------------
FEATURE_NAMES = ["prop_H", "switch_rate", "runs_Z", "longest_run",
                 "HH", "HT", "TH", "TT"]


def sequence_features(seq: str) -> Dict[str, float]:
    n = len(seq)
    n_h = seq.count("H")
    prop_h = n_h / n
    switches = sum(1 for i in range(1, n) if seq[i] != seq[i-1])
    switch_rate = switches / (n - 1)
    # W-W runs Z
    runs = 1 + switches
    n_t = n - n_h
    if n_h > 0 and n_t > 0:
        mu = 2 * n_h * n_t / n + 1
        var = 2 * n_h * n_t * (2 * n_h * n_t - n) / (n * n * (n - 1))
        runs_z = (runs - mu) / math.sqrt(var) if var > 0 else float("nan")
    else:
        runs_z = float("nan")
    # longest run
    longest = cur = 1
    for i in range(1, n):
        if seq[i] == seq[i-1]:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 1
    if n == 0:
        longest = 0
    # bigram counts (of the n-1 bigrams)
    denom = n - 1
    hh = sum(1 for i in range(denom) if seq[i]=="H" and seq[i+1]=="H") / denom
    ht = sum(1 for i in range(denom) if seq[i]=="H" and seq[i+1]=="T") / denom
    th = sum(1 for i in range(denom) if seq[i]=="T" and seq[i+1]=="H") / denom
    tt = sum(1 for i in range(denom) if seq[i]=="T" and seq[i+1]=="T") / denom
    return {"prop_H": prop_h, "switch_rate": switch_rate, "runs_Z": runs_z,
            "longest_run": float(longest),
            "HH": hh, "HT": ht, "TH": th, "TT": tt,
            "lag1_rep": 1.0 - switch_rate,
            "first_H": 1.0 if seq[0] == "H" else 0.0,
            "entropy_binary": _binary_entropy(prop_h)}


def _binary_entropy(p: float) -> float:
    if p <= 0 or p >= 1:
        return 0.0
    return -(p * math.log2(p) + (1-p) * math.log2(1-p))


# -------------------- classifier baseline -----------------------------------

def nearest_centroid_loo(feats_by_model: Dict[str, List[Dict[str, float]]]) -> Dict:
    """Leave-one-out nearest-centroid model classification.
    feats_by_model: model_label -> list of feature dicts (one per trajectory).
    Returns accuracy, per-class accuracy, and confusion matrix (indexed by label order).
    """
    labels = sorted(feats_by_model.keys())
    all_pts = []
    all_labels = []
    for lab in labels:
        for f in feats_by_model[lab]:
            all_pts.append([f[k] for k in FEATURE_NAMES])
            all_labels.append(lab)
    X = np.asarray(all_pts, dtype=float)
    # z-score standardize each feature globally
    means = np.nanmean(X, axis=0)
    stds = np.nanstd(X, axis=0)
    stds[stds == 0] = 1.0
    Xn = (X - means) / stds
    y = np.asarray(all_labels)

    n_correct = 0
    confusion: Dict[Tuple[str, str], int] = defaultdict(int)
    predictions = []
    for i in range(len(y)):
        keep = np.ones(len(y), dtype=bool); keep[i] = False
        # class centroids from the remaining points
        centroids = {}
        for lab in labels:
            m = keep & (y == lab)
            if m.sum() > 0:
                centroids[lab] = Xn[m].mean(axis=0)
        # nearest centroid
        best_lab = min(centroids,
                       key=lambda L: float(np.linalg.norm(Xn[i] - centroids[L])))
        predictions.append(best_lab)
        confusion[(y[i], best_lab)] += 1
        if best_lab == y[i]:
            n_correct += 1
    return {
        "labels": labels,
        "accuracy": n_correct / len(y) if len(y) else float("nan"),
        "n": len(y),
        "confusion": {f"{a}->{b}": v for (a, b), v in confusion.items()},
        "predictions": predictions,
        "y": list(y),
    }


# -------------------- judgment summaries ------------------------------------

def summarize_judgment(records: List[Dict]) -> Dict:
    """Per-(judge, architecture) cell accuracies, self-advantage, dynamic gain.
    Also totals across judges and confusion by SAME/DIFFERENT."""
    by_key: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
    for r in records:
        by_key[(r["judge_label"], r["architecture"])].append(r)

    per_cell = []          # rows: judge, arch, cell, n, n_correct, accuracy
    per_ja = {}            # (judge, arch) -> {"accuracy_A": ..., ..., own, other, self_advantage, same_rate}
    per_judge_arch = []    # detail rows

    for (judge, arch), lst in by_key.items():
        by_cell: Dict[str, List[Dict]] = defaultdict(list)
        for r in lst:
            by_cell[r["cell"]].append(r)
        accs = {}
        for cell in C.JUDGMENT_CELLS:
            trials = by_cell.get(cell, [])
            n = len(trials)
            n_correct = sum(1 for t in trials if t.get("correct"))
            per_cell.append({"judge": judge, "architecture": arch,
                             "cell": cell, "n": n, "n_correct": n_correct,
                             "accuracy": n_correct / n if n else float("nan")})
            accs[f"accuracy_{cell}"] = n_correct / n if n else float("nan")
        # own vs other
        own = [t for t in lst if t["cell"] in ("A", "B")]
        other = [t for t in lst if t["cell"] in ("C", "D")]
        own_acc = sum(1 for t in own if t.get("correct")) / len(own) if own else float("nan")
        other_acc = sum(1 for t in other if t.get("correct")) / len(other) if other else float("nan")
        # SAME response rate (parsed_judgment == "SAME")
        parsed = [t.get("parsed_judgment", "") for t in lst]
        same_rate = sum(1 for p in parsed if p == "SAME") / len(parsed) if parsed else float("nan")
        # confusion: predicted x correct
        conf = Counter((t.get("parsed_judgment", "MISSING"), t.get("correct_answer"))
                       for t in lst)
        total_correct = sum(1 for t in lst if t.get("correct"))
        total_n = len(lst)
        per_ja[(judge, arch)] = {
            **accs,
            "n": total_n, "n_correct": total_correct,
            "total_accuracy": total_correct / total_n if total_n else float("nan"),
            "own_accuracy": own_acc, "other_accuracy": other_acc,
            "self_advantage": own_acc - other_acc if not (math.isnan(own_acc) or math.isnan(other_acc)) else float("nan"),
            "A_minus_C": (accs["accuracy_A"] - accs["accuracy_C"])
                         if not (math.isnan(accs["accuracy_A"]) or math.isnan(accs["accuracy_C"])) else float("nan"),
            "B_minus_D": (accs["accuracy_B"] - accs["accuracy_D"])
                         if not (math.isnan(accs["accuracy_B"]) or math.isnan(accs["accuracy_D"])) else float("nan"),
            "same_response_rate": same_rate,
            "confusion_pred_vs_correct": {f"pred={p}|correct={c}": n_ for (p, c), n_ in conf.items()},
        }
        per_judge_arch.append({"judge": judge, "architecture": arch, **per_ja[(judge, arch)]})

    # Central dynamic self-signature gain per judge
    dynamic = []
    for judge in C.MODEL_LABELS:
        b_key = (judge, "batch"); o_key = (judge, "online")
        if b_key in per_ja and o_key in per_ja:
            sb = per_ja[b_key]["self_advantage"]
            so = per_ja[o_key]["self_advantage"]
            gain = (so - sb) if not (math.isnan(sb) or math.isnan(so)) else float("nan")
            dynamic.append({"judge": judge,
                            "self_advantage_batch": sb,
                            "self_advantage_online": so,
                            "dynamic_self_signature_gain": gain})

    # Pooled across judges
    def _pool(arch):
        rows = [per_ja[(j, arch)] for j in C.MODEL_LABELS if (j, arch) in per_ja]
        if not rows:
            return {}
        # weighted by n
        total_n = sum(r["n"] for r in rows)
        pooled_own_correct = sum(r["own_accuracy"] * (r["n"] // 2) for r in rows
                                 if not math.isnan(r["own_accuracy"]))
        pooled_other_correct = sum(r["other_accuracy"] * (r["n"] // 2) for r in rows
                                   if not math.isnan(r["other_accuracy"]))
        pooled_own = pooled_own_correct / (total_n / 2)
        pooled_other = pooled_other_correct / (total_n / 2)
        return {"total_n": total_n,
                "own_accuracy": pooled_own,
                "other_accuracy": pooled_other,
                "self_advantage": pooled_own - pooled_other}
    pooled = {arch: _pool(arch) for arch in C.ARCHITECTURES}

    return {"per_cell": per_cell,
            "per_judge_arch": per_judge_arch,
            "dynamic_gain": dynamic,
            "pooled_by_architecture": pooled}


# -------------------- feature-distance baseline -----------------------------

def feature_distance_baseline(records: List[Dict],
                              features_by_traj_id: Dict[str, Dict[str, float]]) -> Dict:
    """For each judgment trial, compute standardized-feature distance between
    string 1 and string 2. Then evaluate a distance-threshold SAME/DIFFERENT
    baseline by architecture: threshold chosen at the median distance so that
    below-median = predict SAME, above-median = predict DIFFERENT.
    Also report cell-level mean distance."""
    rows = []
    for r in records:
        f1 = features_by_traj_id.get(r["trajectory_id_1"])
        f2 = features_by_traj_id.get(r["trajectory_id_2"])
        if f1 is None or f2 is None:
            continue
        v1 = np.array([f1[k] for k in FEATURE_NAMES])
        v2 = np.array([f2[k] for k in FEATURE_NAMES])
        rows.append({"architecture": r["architecture"], "cell": r["cell"],
                     "correct_answer": r["correct_answer"],
                     "v1": v1, "v2": v2, "trial_id": r["trial_id"]})
    # standardize per architecture using all v1/v2 involved
    by_arch: Dict[str, List[Dict]] = defaultdict(list)
    for x in rows:
        by_arch[x["architecture"]].append(x)
    out = {"per_arch": {}, "per_cell": []}
    for arch, xs in by_arch.items():
        pts = np.vstack([x["v1"] for x in xs] + [x["v2"] for x in xs])
        mu = np.nanmean(pts, axis=0)
        sd = np.nanstd(pts, axis=0); sd[sd == 0] = 1.0
        # distances
        dists = []
        for x in xs:
            d = float(np.linalg.norm(((x["v1"] - mu)/sd) - ((x["v2"] - mu)/sd)))
            dists.append(d); x["dist"] = d
        # median-threshold classifier (baseline; no supervision)
        median_d = float(np.median(dists))
        n_correct = 0
        for x in xs:
            pred = "SAME" if x["dist"] <= median_d else "DIFFERENT"
            if pred == x["correct_answer"]:
                n_correct += 1
        acc = n_correct / len(xs) if xs else float("nan")
        # per-cell means
        by_cell_dist: Dict[str, List[float]] = defaultdict(list)
        for x in xs:
            by_cell_dist[x["cell"]].append(x["dist"])
        out["per_arch"][arch] = {"n": len(xs), "median_distance": median_d,
                                  "median_threshold_accuracy": acc}
        for cell in C.JUDGMENT_CELLS:
            ds = by_cell_dist.get(cell, [])
            out["per_cell"].append({"architecture": arch, "cell": cell,
                                    "n": len(ds),
                                    "mean_distance": float(np.mean(ds)) if ds else float("nan"),
                                    "sd_distance": float(np.std(ds)) if ds else float("nan")})
    return out
