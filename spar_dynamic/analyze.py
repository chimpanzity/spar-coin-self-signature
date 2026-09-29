"""Analysis: source phenotypes, model-identifiability classifier, judgment
self-advantage summaries, feature-distance baselines, and reports.
"""

import csv, json, math, os
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

import numpy as np

from . import config as C


# ---- pilot-2 helpers -----------------------------------------------------

def _phi_inv(p: float) -> float:
    """Inverse standard-normal CDF via math.erfinv-free approximation.
    Uses Acklam-style Beasley-Springer-Moro. Accurate to ~7 decimals.
    Returns +/- 5.0 for tail extremes.
    """
    if p <= 0.0 or p >= 1.0:
        # caller should have applied a log-linear correction first
        return -5.0 if p <= 0.0 else 5.0
    # rational approximation
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow = 0.02425
    phigh = 1 - plow
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        x = (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
            ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
        return x
    if p <= phigh:
        q = p - 0.5
        r = q * q
        x = (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5]) * q / \
            (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1)
        return x
    q = math.sqrt(-2 * math.log(1 - p))
    x = -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
        ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    return x


def dprime_criterion(n_hit: int, n_target: int, n_fa: int, n_lure: int) -> Tuple[float, float]:
    """Return (d', criterion c) with a log-linear (Snodgrass-Corwin) correction.

    Correction: add 0.5 to counts, add 1 to N, so hit/false-alarm rates are
    always strictly in (0, 1).
    """
    hr = (n_hit + 0.5) / (n_target + 1.0)
    fr = (n_fa + 0.5) / (n_lure + 1.0)
    zH = _phi_inv(hr)
    zF = _phi_inv(fr)
    d = zH - zF
    c = -0.5 * (zH + zF)
    return (d, c)


def summarize_self_other(records: List[Dict]) -> Dict:
    """records: list of SelfOtherJudgmentRecord as dicts.
    Returns per-(judge, arch) accuracy, balanced accuracy, SELF hit, OTHER CR,
    SELF response rate, d', criterion, plus per-OTHER-source-model breakdown.
    """
    per_ja: Dict[Tuple[str, str], Dict] = {}
    per_other_source_rows: List[Dict] = []
    by_key: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
    for r in records:
        by_key[(r["judge_label"], r["architecture"])].append(r)

    for (judge, arch), lst in by_key.items():
        n_planned = len(lst)
        valid = [r for r in lst if r.get("valid")]
        abandoned = [r for r in lst if r.get("trial_status") == "abandoned" or not r.get("valid")]
        n_valid = len(valid)
        n_abandoned = len(abandoned)
        # SELF trials
        self_trials = [r for r in valid if r["correct_answer"] == "SELF"]
        other_trials = [r for r in valid if r["correct_answer"] == "OTHER"]
        n_self = len(self_trials); n_other = len(other_trials)
        self_hits = sum(1 for r in self_trials if r["parsed_judgment"] == "SELF")
        other_cr = sum(1 for r in other_trials if r["parsed_judgment"] == "OTHER")
        false_alarms = sum(1 for r in other_trials if r["parsed_judgment"] == "SELF")

        self_hit_rate = self_hits / n_self if n_self else float("nan")
        other_cr_rate = other_cr / n_other if n_other else float("nan")
        overall_correct = self_hits + other_cr
        overall_n = n_valid
        acc = overall_correct / overall_n if overall_n else float("nan")
        # balanced accuracy (avg of hit and CR rates)
        if n_self > 0 and n_other > 0:
            ba = (self_hit_rate + other_cr_rate) / 2.0
        else:
            ba = float("nan")
        # SELF response rate across valid trials
        self_response_rate = sum(1 for r in valid if r["parsed_judgment"] == "SELF") / n_valid \
                             if n_valid else float("nan")
        # d' and criterion (SELF = target, OTHER = lure)
        if n_self > 0 and n_other > 0:
            d, c = dprime_criterion(self_hits, n_self, false_alarms, n_other)
        else:
            d, c = float("nan"), float("nan")

        per_ja[(judge, arch)] = {
            "judge": judge, "architecture": arch,
            "n_planned": n_planned, "n_valid": n_valid, "n_abandoned": n_abandoned,
            "n_self": n_self, "n_other": n_other,
            "self_hits": self_hits, "other_cr": other_cr, "false_alarms": false_alarms,
            "self_hit_rate": self_hit_rate,
            "other_cr_rate": other_cr_rate,
            "accuracy": acc,
            "balanced_accuracy": ba,
            "self_response_rate": self_response_rate,
            "d_prime": d, "criterion": c,
        }

        # per-OTHER-source breakdown
        by_other = defaultdict(list)
        for r in other_trials:
            by_other[r["source_model_label"]].append(r)
        for src, sub in by_other.items():
            n_sub = len(sub)
            n_correct_sub = sum(1 for r in sub if r["parsed_judgment"] == "OTHER")
            per_other_source_rows.append({
                "judge": judge, "architecture": arch,
                "other_source_model": src,
                "n": n_sub, "n_correct_other": n_correct_sub,
                "other_cr_rate": n_correct_sub / n_sub if n_sub else float("nan"),
            })

    return {"per_ja": per_ja,
            "per_other_source": per_other_source_rows}


def self_other_dynamic_gain(per_ja: Dict[Tuple[str, str], Dict]) -> List[Dict]:
    """For each judge, compute BA and d' online-batch gains."""
    out = []
    for judge in C.MODEL_LABELS:
        b = per_ja.get((judge, "batch")); o = per_ja.get((judge, "online"))
        if not b or not o:
            continue
        out.append({"judge": judge,
                    "balanced_accuracy_batch": b["balanced_accuracy"],
                    "balanced_accuracy_online": o["balanced_accuracy"],
                    "dynamic_gain_balanced_accuracy": o["balanced_accuracy"] - b["balanced_accuracy"],
                    "d_prime_batch": b["d_prime"],
                    "d_prime_online": o["d_prime"],
                    "dynamic_gain_d_prime": o["d_prime"] - b["d_prime"]})
    return out


def self_other_feature_distance(records: List[Dict],
                                features_by_traj_id: Dict[str, Dict[str, float]],
                                source_by_arch_model: Dict[Tuple[str, str], List[Dict[str, float]]]) -> Dict:
    """For each judgment trial, compute the standardized-feature distance from
    the shown trajectory to the JUDGE'S OWN source-model centroid within the
    same architecture. Then test whether SELF responses correlate with proximity.
    """
    per_arch_stats: Dict[str, Dict] = {}
    trial_rows: List[Dict] = []
    for arch in C.ARCHITECTURES:
        # collect all source-feature vectors for this arch across models to standardize
        all_pts = []
        for ml in C.MODEL_LABELS:
            for f in source_by_arch_model.get((arch, ml), []):
                all_pts.append([f[k] for k in FEATURE_NAMES])
        if not all_pts:
            continue
        X = np.asarray(all_pts, dtype=float)
        mu = np.nanmean(X, axis=0); sd = np.nanstd(X, axis=0); sd[sd == 0] = 1.0
        # per-model centroids in standardized space
        centroids = {}
        for ml in C.MODEL_LABELS:
            vecs = np.asarray([[f[k] for k in FEATURE_NAMES]
                               for f in source_by_arch_model.get((arch, ml), [])], dtype=float)
            if len(vecs) == 0:
                continue
            centroids[ml] = ((vecs - mu) / sd).mean(axis=0)
        for r in records:
            if r["architecture"] != arch or not r.get("valid"):
                continue
            tid = r["source_trajectory_id"]
            f = features_by_traj_id.get(tid)
            if f is None:
                continue
            v = (np.array([f[k] for k in FEATURE_NAMES]) - mu) / sd
            judge = r["judge_label"]
            if judge not in centroids:
                continue
            d_self = float(np.linalg.norm(v - centroids[judge]))
            # min distance to any other centroid
            others = [np.linalg.norm(v - centroids[ml]) for ml in C.MODEL_LABELS if ml != judge and ml in centroids]
            d_min_other = float(min(others)) if others else float("nan")
            trial_rows.append({
                "trial_id": r["trial_id"], "judge": judge, "architecture": arch,
                "correct_answer": r["correct_answer"],
                "parsed_judgment": r["parsed_judgment"],
                "source_model": r["source_model_label"],
                "dist_to_self_centroid": d_self,
                "dist_to_nearest_other_centroid": d_min_other,
                "closer_to_self": d_self < d_min_other,
                "closest_by_features_pred": "SELF" if d_self < d_min_other else "OTHER",
            })
        # per-arch summary: agreement between judge's response and centroid-nearest rule
        sub = [x for x in trial_rows if x["architecture"] == arch]
        if sub:
            agree = sum(1 for x in sub if x["parsed_judgment"] == x["closest_by_features_pred"])
            per_arch_stats[arch] = {"n": len(sub),
                                    "judge_agrees_with_nearest_centroid": agree,
                                    "agreement_rate": agree / len(sub),
                                    # rule accuracy vs ground truth
                                    "nearest_centroid_rule_accuracy":
                                        sum(1 for x in sub
                                            if x["closest_by_features_pred"] == x["correct_answer"]) / len(sub)}
    return {"per_arch": per_arch_stats, "trial_rows": trial_rows}


# ---- pilot 3 (provenance) analysis --------------------------------------

def summarize_provenance(records: List[Dict]) -> Dict:
    """Cell-level summaries for the 2x2x2 (judge x source_identity x actual_arch x stated_arch)
    grid, plus congruence contrasts and paired-within-trajectory provenance deltas.

    Returns:
      cell_rows: list of {judge, true_source_identity, actual_architecture,
                          stated_architecture, n, n_correct, self_response_rate,
                          accuracy}
      congruence_rows: per judge x source_identity:
        {congruent_accuracy, incongruent_accuracy, congruence_advantage}
      self_specific_provenance_effect: per judge:
        {congruence_advantage_SELF, congruence_advantage_OTHER, self_specific}
      arch_conditional_self_rows: per judge x actual_arch:
        {p_self_told_batch, p_self_told_online, delta_told_online_minus_batch}
        computed within true SELF trajectories only
      paired_delta_rows: per judge x source_identity x actual_arch:
        distribution of delta (self_response_told_online - self_response_told_batch)
        across trajectories (paired within the same source_trajectory_id)
    """
    valid = [r for r in records if r.get("valid")]
    # cells
    cells: Dict[Tuple[str, str, str, str], List[Dict]] = defaultdict(list)
    for r in valid:
        cells[(r["judge_label"], r["true_source_identity"],
               r["actual_architecture"], r["stated_architecture"])].append(r)
    cell_rows = []
    for (judge, src, actual, stated), lst in sorted(cells.items()):
        n = len(lst)
        n_correct = sum(1 for r in lst if r.get("correct"))
        n_self = sum(1 for r in lst if r["parsed_judgment"] == "SELF")
        cell_rows.append({
            "judge": judge, "true_source_identity": src,
            "actual_architecture": actual, "stated_architecture": stated,
            "n": n, "n_correct": n_correct,
            "accuracy": n_correct / n if n else float("nan"),
            "self_response_rate": n_self / n if n else float("nan"),
        })

    # congruence contrasts (per judge x source_identity)
    congruence_rows = []
    for judge in C.MODEL_LABELS:
        for src in ("SELF", "OTHER"):
            cong = [r for r in valid if r["judge_label"] == judge
                    and r["true_source_identity"] == src and r["provenance_congruent"]]
            incong = [r for r in valid if r["judge_label"] == judge
                      and r["true_source_identity"] == src and not r["provenance_congruent"]]
            acc_c = sum(1 for r in cong if r.get("correct")) / len(cong) if cong else float("nan")
            acc_i = sum(1 for r in incong if r.get("correct")) / len(incong) if incong else float("nan")
            congruence_rows.append({
                "judge": judge, "true_source_identity": src,
                "n_congruent": len(cong), "n_incongruent": len(incong),
                "congruent_accuracy": acc_c, "incongruent_accuracy": acc_i,
                "congruence_advantage": (acc_c - acc_i) if not (math.isnan(acc_c) or math.isnan(acc_i)) else float("nan"),
            })

    # Self-specific provenance effect per judge
    self_specific_rows = []
    for judge in C.MODEL_LABELS:
        cs = [r for r in congruence_rows if r["judge"] == judge and r["true_source_identity"] == "SELF"]
        co = [r for r in congruence_rows if r["judge"] == judge and r["true_source_identity"] == "OTHER"]
        if cs and co:
            self_specific_rows.append({
                "judge": judge,
                "congruence_advantage_SELF": cs[0]["congruence_advantage"],
                "congruence_advantage_OTHER": co[0]["congruence_advantage"],
                "self_specific_provenance_effect":
                    (cs[0]["congruence_advantage"] - co[0]["congruence_advantage"])
                    if not (math.isnan(cs[0]["congruence_advantage"])
                            or math.isnan(co[0]["congruence_advantage"])) else float("nan"),
            })

    # Architecture-conditional SELF response (for true SELF trajectories only)
    arch_conditional_self_rows = []
    for judge in C.MODEL_LABELS:
        for actual_arch in C.ARCHITECTURES:
            told_batch = [r for r in valid
                          if r["judge_label"] == judge
                          and r["true_source_identity"] == "SELF"
                          and r["actual_architecture"] == actual_arch
                          and r["stated_architecture"] == "batch"]
            told_online = [r for r in valid
                           if r["judge_label"] == judge
                           and r["true_source_identity"] == "SELF"
                           and r["actual_architecture"] == actual_arch
                           and r["stated_architecture"] == "online"]
            p_batch = (sum(1 for r in told_batch if r["parsed_judgment"] == "SELF") / len(told_batch)
                       if told_batch else float("nan"))
            p_online = (sum(1 for r in told_online if r["parsed_judgment"] == "SELF") / len(told_online)
                        if told_online else float("nan"))
            arch_conditional_self_rows.append({
                "judge": judge, "actual_architecture": actual_arch,
                "n_told_batch": len(told_batch), "n_told_online": len(told_online),
                "p_self_told_batch": p_batch, "p_self_told_online": p_online,
                "delta_told_online_minus_batch":
                    (p_online - p_batch) if not (math.isnan(p_batch) or math.isnan(p_online)) else float("nan"),
            })

    # Paired within-trajectory delta (self_response_told_online - self_response_told_batch)
    # for each (judge, pair_key) that has both versions
    by_pair: Dict[Tuple[str, str], Dict[str, Dict]] = defaultdict(dict)
    for r in valid:
        by_pair[(r["judge_label"], r["pair_key"])][r["stated_architecture"]] = r
    paired_records = []
    for (judge, pk), both in by_pair.items():
        if "batch" not in both or "online" not in both:
            continue
        rb = both["batch"]; ro = both["online"]
        delta = (ro["self_response"] if ro["self_response"] is not None else 0) \
              - (rb["self_response"] if rb["self_response"] is not None else 0)
        paired_records.append({
            "judge": judge, "pair_key": pk,
            "true_source_identity": rb["true_source_identity"],
            "actual_architecture": rb["actual_architecture"],
            "self_response_told_batch": rb["self_response"],
            "self_response_told_online": ro["self_response"],
            "delta_told_online_minus_batch": delta,
        })
    paired_summary = []
    for judge in C.MODEL_LABELS:
        for src in ("SELF", "OTHER"):
            for actual_arch in C.ARCHITECTURES:
                deltas = [r["delta_told_online_minus_batch"] for r in paired_records
                          if r["judge"] == judge and r["true_source_identity"] == src
                          and r["actual_architecture"] == actual_arch]
                if not deltas:
                    continue
                n = len(deltas)
                mean_delta = sum(deltas) / n
                paired_summary.append({
                    "judge": judge, "true_source_identity": src,
                    "actual_architecture": actual_arch, "n_pairs": n,
                    "mean_delta_told_online_minus_batch": mean_delta,
                    "n_delta_positive": sum(1 for d in deltas if d > 0),
                    "n_delta_negative": sum(1 for d in deltas if d < 0),
                    "n_delta_zero": sum(1 for d in deltas if d == 0),
                })

    # Signal detection per (judge, actual_arch, stated_arch)
    sdt_rows = []
    for judge in C.MODEL_LABELS:
        for actual in C.ARCHITECTURES:
            for stated in ("batch", "online"):
                sub = [r for r in valid
                       if r["judge_label"] == judge
                       and r["actual_architecture"] == actual
                       and r["stated_architecture"] == stated]
                # SELF hits = SELF response on true SELF trials
                selfs = [r for r in sub if r["true_source_identity"] == "SELF"]
                others = [r for r in sub if r["true_source_identity"] == "OTHER"]
                n_hit = sum(1 for r in selfs if r["parsed_judgment"] == "SELF")
                n_fa = sum(1 for r in others if r["parsed_judgment"] == "SELF")
                n_target = len(selfs); n_lure = len(others)
                if n_target and n_lure:
                    d, c = dprime_criterion(n_hit, n_target, n_fa, n_lure)
                else:
                    d, c = float("nan"), float("nan")
                sdt_rows.append({
                    "judge": judge, "actual_architecture": actual, "stated_architecture": stated,
                    "n_target": n_target, "n_lure": n_lure,
                    "self_hits": n_hit, "false_alarms": n_fa,
                    "hit_rate": n_hit / n_target if n_target else float("nan"),
                    "false_alarm_rate": n_fa / n_lure if n_lure else float("nan"),
                    "d_prime": d, "criterion": c,
                })

    return {"cells": cell_rows, "congruence": congruence_rows,
            "self_specific_provenance_effect": self_specific_rows,
            "arch_conditional_self": arch_conditional_self_rows,
            "paired_delta_per_pair": paired_records,
            "paired_delta_summary": paired_summary,
            "signal_detection": sdt_rows}


def arch_conditioned_feature_baseline(records: List[Dict],
                                       features_by_traj_id: Dict[str, Dict[str, float]],
                                       source_by_arch_model: Dict[Tuple[str, str], List[Dict[str, float]]]) -> Dict:
    """For each judgment trial, compute the standardized-feature distance from
    the shown trajectory to the JUDGE'S own centroid under the STATED architecture.
    Ask: does that distance predict SELF response? Purely a computational
    analogue of the stated-provenance manipulation."""
    per_arch_stats: Dict[str, Dict] = {}
    trial_rows: List[Dict] = []
    for arch in C.ARCHITECTURES:
        all_pts = []
        for ml in C.MODEL_LABELS:
            for f in source_by_arch_model.get((arch, ml), []):
                all_pts.append([f[k] for k in FEATURE_NAMES])
        if not all_pts:
            continue
        X = np.asarray(all_pts, dtype=float)
        mu = np.nanmean(X, axis=0); sd = np.nanstd(X, axis=0); sd[sd == 0] = 1.0
        centroids: Dict[str, np.ndarray] = {}
        for ml in C.MODEL_LABELS:
            vecs = np.asarray([[f[k] for k in FEATURE_NAMES]
                               for f in source_by_arch_model.get((arch, ml), [])], dtype=float)
            if len(vecs):
                centroids[ml] = ((vecs - mu) / sd).mean(axis=0)
        # for each record whose STATED arch matches this arch (this is the
        # architecture the judge was told), compute distance to the judge's
        # centroid under that stated arch.
        for r in records:
            if not r.get("valid"):
                continue
            if r["stated_architecture"] != arch:
                continue
            f = features_by_traj_id.get(r["source_trajectory_id"])
            if f is None:
                continue
            judge = r["judge_label"]
            if judge not in centroids:
                continue
            v = (np.array([f[k] for k in FEATURE_NAMES]) - mu) / sd
            d_self = float(np.linalg.norm(v - centroids[judge]))
            others = [np.linalg.norm(v - centroids[ml]) for ml in C.MODEL_LABELS
                      if ml != judge and ml in centroids]
            d_min_other = float(min(others)) if others else float("nan")
            predicted = "SELF" if d_self < d_min_other else "OTHER"
            trial_rows.append({
                "trial_id": r["trial_id"], "judge": judge,
                "stated_architecture": arch,
                "true_source_identity": r["true_source_identity"],
                "actual_architecture": r["actual_architecture"],
                "provenance_congruent": r["provenance_congruent"],
                "parsed_judgment": r["parsed_judgment"],
                "dist_to_self_centroid_under_stated_arch": d_self,
                "dist_to_nearest_other_centroid_under_stated_arch": d_min_other,
                "feature_rule_prediction": predicted,
                "feature_rule_correct": (predicted == r["true_source_identity"]),
                "judge_agrees_with_feature_rule": (r["parsed_judgment"] == predicted),
            })
        sub = [x for x in trial_rows if x["stated_architecture"] == arch]
        if sub:
            per_arch_stats[arch] = {
                "n": len(sub),
                "feature_rule_accuracy": sum(1 for x in sub if x["feature_rule_correct"]) / len(sub),
                "judge_agrees_with_feature_rule_rate":
                    sum(1 for x in sub if x["judge_agrees_with_feature_rule"]) / len(sub),
            }
    return {"per_stated_arch": per_arch_stats, "trial_rows": trial_rows}


# ---- pilot 4 (Astra provenance replication) analysis --------------------

def summarize_astra_followup(records: List[Dict]) -> Dict:
    """Cell-level SELF response rates, primary selective-online effect,
    no-provenance baseline contrasts, paired within-trajectory switches.

    Returns dict with:
      cells: list of (identity, actual_arch, stated_condition, n, self_rate, accuracy)
      primary: {astra_online_shift, astra_batch_shift (unused label), other_online_shift,
                selective_online_self_effect}
      baseline_vs_none: shifts of told-batch and told-online relative to no-provenance,
                        separately for SELF and OTHER
      paired_switches: batch->online transition per trajectory
      mcnemar: McNemar test for told-batch vs told-online within SELF trajectories, and OTHER
      source_breakdown: OTHER split by source model (fable vs qwen)
    """
    valid = [r for r in records if r.get("valid")]
    from collections import defaultdict, Counter

    # cells
    cells = []
    by_cell: Dict[Tuple[str, str, str], List[Dict]] = defaultdict(list)
    for r in valid:
        by_cell[(r["true_source_identity"], r["actual_architecture"],
                 r["stated_condition"])].append(r)
    for (identity, actual, stated), lst in sorted(by_cell.items()):
        n = len(lst)
        n_self = sum(1 for r in lst if r["parsed_judgment"] == "SELF")
        n_correct = sum(1 for r in lst if r.get("correct"))
        cells.append({
            "true_source_identity": identity, "actual_architecture": actual,
            "stated_condition": stated, "n": n,
            "self_responses": n_self,
            "self_rate": n_self / n if n else float("nan"),
            "accuracy": n_correct / n if n else float("nan"),
        })

    def _rate(pred_identity, stated):
        sub = [r for r in valid
               if r["true_source_identity"] == pred_identity
               and r["stated_condition"] == stated]
        if not sub:
            return float("nan")
        return sum(1 for r in sub if r["parsed_judgment"] == "SELF") / len(sub)

    astra_batch = _rate("SELF", "told_batch")
    astra_online = _rate("SELF", "told_online")
    astra_none = _rate("SELF", "no_provenance")
    other_batch = _rate("OTHER", "told_batch")
    other_online = _rate("OTHER", "told_online")
    other_none = _rate("OTHER", "no_provenance")

    self_online_shift = astra_online - astra_batch
    other_online_shift = other_online - other_batch
    selective = self_online_shift - other_online_shift

    primary = {
        "astra_told_batch_self_rate": astra_batch,
        "astra_told_online_self_rate": astra_online,
        "astra_no_provenance_self_rate": astra_none,
        "other_told_batch_self_rate": other_batch,
        "other_told_online_self_rate": other_online,
        "other_no_provenance_self_rate": other_none,
        "self_online_shift": self_online_shift,
        "other_online_shift": other_online_shift,
        "selective_online_self_effect": selective,
    }

    baseline_vs_none = {
        "self_online_vs_none": astra_online - astra_none,
        "self_batch_vs_none": astra_batch - astra_none,
        "other_online_vs_none": other_online - other_none,
        "other_batch_vs_none": other_batch - other_none,
    }

    # Paired switches (told_batch vs told_online only) per trajectory
    by_pair: Dict[str, Dict[str, Dict]] = defaultdict(dict)
    for r in valid:
        by_pair[r["pair_key"]][r["stated_condition"]] = r
    paired_switches = []
    for pk, both in by_pair.items():
        if "told_batch" not in both or "told_online" not in both:
            continue
        rb = both["told_batch"]; ro = both["told_online"]
        pb = rb["parsed_judgment"]; po = ro["parsed_judgment"]
        transition = "no_change"
        if pb == "OTHER" and po == "SELF":
            transition = "OTHER_to_SELF"
        elif pb == "SELF" and po == "OTHER":
            transition = "SELF_to_OTHER"
        paired_switches.append({
            "pair_key": pk,
            "true_source_identity": rb["true_source_identity"],
            "actual_architecture": rb["actual_architecture"],
            "source_model_label": rb["source_model_label"],
            "told_batch_response": pb,
            "told_online_response": po,
            "transition": transition,
        })

    # Aggregate switch counts + net shift per identity
    switch_table = []
    for identity in ("SELF", "OTHER"):
        sub = [x for x in paired_switches if x["true_source_identity"] == identity]
        c = Counter(x["transition"] for x in sub)
        switch_table.append({
            "true_source_identity": identity,
            "n_pairs": len(sub),
            "OTHER_to_SELF": c.get("OTHER_to_SELF", 0),
            "SELF_to_OTHER": c.get("SELF_to_OTHER", 0),
            "no_change": c.get("no_change", 0),
            "net_online_shift": c.get("OTHER_to_SELF", 0) - c.get("SELF_to_OTHER", 0),
        })

    # McNemar test per identity (told_batch vs told_online paired)
    def _mcnemar(b_to_o: int, o_to_b: int) -> Dict:
        """b_to_o = pairs that were OTHER when told_batch and SELF when told_online.
           o_to_b = the reverse.
           Exact binomial (mid-p) two-sided test on discordant pairs."""
        n_dis = b_to_o + o_to_b
        if n_dis == 0:
            return {"n_discordant": 0, "chi_square": float("nan"), "p_value": float("nan")}
        # continuity-corrected chi-square
        chi = (abs(b_to_o - o_to_b) - 1) ** 2 / n_dis if n_dis > 0 else float("nan")
        # exact binomial p (two-sided)
        # under H0 both cells equally likely -> binomial(n_dis, 0.5)
        from math import comb
        k = min(b_to_o, o_to_b)
        p_one_tail = sum(comb(n_dis, i) for i in range(k + 1)) / (2 ** n_dis)
        p_two = min(1.0, 2 * p_one_tail)
        return {"n_discordant": n_dis, "chi_square": chi,
                "p_value_two_sided_exact_binomial": p_two,
                "b_to_o": b_to_o, "o_to_b": o_to_b}

    mcnemar_rows = []
    for identity in ("SELF", "OTHER"):
        sub = [x for x in paired_switches if x["true_source_identity"] == identity]
        b_to_o = sum(1 for x in sub if x["transition"] == "OTHER_to_SELF")
        o_to_b = sum(1 for x in sub if x["transition"] == "SELF_to_OTHER")
        mcnemar_rows.append({
            "true_source_identity": identity,
            **_mcnemar(b_to_o, o_to_b),
        })

    # Source-model breakdown of OTHER trajectories
    source_breakdown = []
    for source in ("fable", "qwen"):
        for stated in C.STATED_CONDITIONS:
            sub = [r for r in valid
                   if r["true_source_identity"] == "OTHER"
                   and r["source_model_label"] == source
                   and r["stated_condition"] == stated]
            n = len(sub)
            n_self = sum(1 for r in sub if r["parsed_judgment"] == "SELF")
            n_correct = sum(1 for r in sub if r.get("correct"))
            source_breakdown.append({
                "source_model_label": source, "stated_condition": stated,
                "n": n, "self_rate": n_self / n if n else float("nan"),
                "other_cr_rate": (n - n_self) / n if n else float("nan"),
                "accuracy": n_correct / n if n else float("nan"),
            })

    # Actual-architecture breakdown for SELF trajectories
    actual_arch_rows = []
    for actual in C.ARCHITECTURES:
        for stated in C.STATED_CONDITIONS:
            sub = [r for r in valid if r["true_source_identity"] == "SELF"
                   and r["actual_architecture"] == actual
                   and r["stated_condition"] == stated]
            n = len(sub)
            n_self = sum(1 for r in sub if r["parsed_judgment"] == "SELF")
            actual_arch_rows.append({
                "true_source_identity": "SELF",
                "actual_architecture": actual, "stated_condition": stated,
                "n": n, "self_rate": n_self / n if n else float("nan"),
            })
        for stated in C.STATED_CONDITIONS:
            sub = [r for r in valid if r["true_source_identity"] == "OTHER"
                   and r["actual_architecture"] == actual
                   and r["stated_condition"] == stated]
            n = len(sub)
            n_self = sum(1 for r in sub if r["parsed_judgment"] == "SELF")
            actual_arch_rows.append({
                "true_source_identity": "OTHER",
                "actual_architecture": actual, "stated_condition": stated,
                "n": n, "self_rate": n_self / n if n else float("nan"),
            })

    return {"cells": cells, "primary": primary,
            "baseline_vs_none": baseline_vs_none,
            "paired_switches": paired_switches,
            "switch_table": switch_table,
            "mcnemar": mcnemar_rows,
            "source_breakdown": source_breakdown,
            "actual_arch_rows": actual_arch_rows}


def distance_to_astra_per_trial(records: List[Dict],
                                 features_by_traj_id: Dict[str, Dict[str, float]],
                                 source_by_arch_model: Dict[Tuple[str, str], List[Dict[str, float]]]) -> List[Dict]:
    """For every judgment trial in pilot 4, compute standardized-feature distance
    from the shown trajectory to the Astra batch centroid AND the Astra online centroid,
    using only the pilot-4 source data. Purely exploratory."""
    rows = []
    for arch in C.ARCHITECTURES:
        all_pts = []
        for ml in C.MODEL_LABELS:
            for f in source_by_arch_model.get((arch, ml), []):
                all_pts.append([f[k] for k in FEATURE_NAMES])
        if not all_pts:
            continue
        X = np.asarray(all_pts, dtype=float)
        mu = np.nanmean(X, axis=0); sd = np.nanstd(X, axis=0); sd[sd == 0] = 1.0
        astra_pts = np.asarray([[f[k] for k in FEATURE_NAMES]
                                for f in source_by_arch_model.get((arch, "astra"), [])],
                               dtype=float)
        if len(astra_pts) == 0:
            continue
        astra_centroid = ((astra_pts - mu) / sd).mean(axis=0)
        for r in records:
            if not r.get("valid"):
                continue
            f = features_by_traj_id.get(r["source_trajectory_id"])
            if f is None:
                continue
            v = (np.array([f[k] for k in FEATURE_NAMES]) - mu) / sd
            d_astra = float(np.linalg.norm(v - astra_centroid))
            rows.append({
                "trial_id": r["trial_id"],
                "true_source_identity": r["true_source_identity"],
                "actual_architecture": r["actual_architecture"],
                "stated_condition": r["stated_condition"],
                "source_model_label": r["source_model_label"],
                "parsed_judgment": r["parsed_judgment"],
                "arch_centroid_used": arch,
                "distance_to_astra_centroid": d_astra,
            })
    return rows


def self_other_loo_classifier(source_by_arch_model: Dict[Tuple[str, str], List[Dict[str, float]]]) -> Dict:
    """For each judge model x architecture, build a leave-one-out nearest-centroid
    SELF/OTHER classifier on source trajectories (SELF = judge's model, OTHER =
    all other models pooled). Reports its balanced accuracy — a purely feature-
    based upper-bound baseline for what the LLM judge could achieve without
    privileged self access.
    """
    out = []
    for judge in C.MODEL_LABELS:
        for arch in C.ARCHITECTURES:
            self_pool = source_by_arch_model.get((arch, judge), [])
            other_pool = []
            for ml in C.MODEL_LABELS:
                if ml != judge:
                    other_pool += source_by_arch_model.get((arch, ml), [])
            if len(self_pool) < 2 or len(other_pool) < 2:
                continue
            all_vecs = [[f[k] for k in FEATURE_NAMES] for f in self_pool + other_pool]
            X = np.asarray(all_vecs, dtype=float)
            y = np.array(["SELF"] * len(self_pool) + ["OTHER"] * len(other_pool))
            mu = np.nanmean(X, axis=0); sd = np.nanstd(X, axis=0); sd[sd == 0] = 1.0
            Xn = (X - mu) / sd
            preds = []
            for i in range(len(y)):
                keep = np.ones(len(y), dtype=bool); keep[i] = False
                # centroids from remaining
                cent = {}
                for lab in ("SELF", "OTHER"):
                    m = keep & (y == lab)
                    if m.sum() > 0:
                        cent[lab] = Xn[m].mean(axis=0)
                if not cent:
                    preds.append("?"); continue
                pred = min(cent, key=lambda L: float(np.linalg.norm(Xn[i] - cent[L])))
                preds.append(pred)
            hits = sum(1 for i in range(len(y)) if preds[i] == "SELF" and y[i] == "SELF")
            crs  = sum(1 for i in range(len(y)) if preds[i] == "OTHER" and y[i] == "OTHER")
            n_self = int((y == "SELF").sum()); n_other = int((y == "OTHER").sum())
            self_rate = hits / n_self if n_self else float("nan")
            other_rate = crs / n_other if n_other else float("nan")
            ba = (self_rate + other_rate) / 2 if n_self and n_other else float("nan")
            out.append({"judge": judge, "architecture": arch,
                        "n_self": n_self, "n_other": n_other,
                        "self_hit_rate": self_rate, "other_cr_rate": other_rate,
                        "balanced_accuracy": ba})
    return {"rows": out}


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
