"""Analysis for FCE1 — sections 16-20.

Primary outputs:
  trial_level.csv
  compliance_summary.csv
  accuracy_by_judge_target_frame.csv
  named_judge_target_matrix.csv
  producer_observer_contrasts.csv
  self_wording_contrasts.csv
  observer_role_summary.csv
  target_complementarity.csv
  baseline_predictions.csv
  baseline_summary.csv
  bootstrap_intervals.csv
"""

import csv, json, math, os, random, statistics
from collections import Counter, defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import config as F
from .pairs import Trial


# ---------------------------------------------------------------------------
# Join trial manifest with outcomes
# ---------------------------------------------------------------------------

def join_trials_outcomes(trials: List[Trial], outcomes: Dict[str, Dict]) -> List[Dict]:
    out = []
    for t in trials:
        o = outcomes.get(t.trial_id, {})
        out.append({
            **{k: getattr(t, k) for k in (
                "trial_id","pair_id","triplet_id","split",
                "target_item_id","target_label","distractor_label",
                "wording_condition","judge_label","judge_role",
                "source_pair_type","source_label_A","source_label_B",
                "sequence_A_id","sequence_B_id","correct_answer",
            )},
            "status": o.get("status", "pending"),
            "visible_answer": o.get("visible_answer"),
            "correct": o.get("correct"),
            "first_attempt_valid": o.get("first_attempt_valid"),
            "attempts": o.get("attempts", 0),
            "total_cost_usd": o.get("total_cost_usd", 0.0),
            "returned_model_id": o.get("returned_model_id", ""),
            "provider": o.get("provider", ""),
            "reasoning_tokens_total": o.get("reasoning_tokens_total", 0),
            "completion_tokens_total": o.get("completion_tokens_total", 0),
        })
    return out


def write_trial_level(path: str, rows: List[Dict]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8") as f: f.write("")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows: w.writerow(r)


# ---------------------------------------------------------------------------
# Compliance summary (section 13)
# ---------------------------------------------------------------------------

def compliance_summary(rows: List[Dict]) -> List[Dict]:
    out = []
    for judge in F.JUDGE_LABELS:
        for wording in ("NAMED", "SELF"):
            subset = [r for r in rows if r["judge_label"] == judge
                      and r["wording_condition"] == wording]
            if not subset:
                continue
            n = len(subset)
            n_ok = sum(1 for r in subset if r["status"] == "ok")
            n_first_valid = sum(1 for r in subset if r.get("first_attempt_valid"))
            n_abandoned = sum(1 for r in subset if r["status"] == "abandoned")
            out.append({
                "judge": judge, "wording": wording, "n": n,
                "n_valid_eventually": n_ok, "n_first_attempt_valid": n_first_valid,
                "n_abandoned": n_abandoned,
                "pct_valid_eventually": round(n_ok / n, 4),
                "pct_first_attempt_valid": round(n_first_valid / n, 4),
            })
    return out


# ---------------------------------------------------------------------------
# Accuracy tables
# ---------------------------------------------------------------------------

def _acc(subset: List[Dict]) -> Tuple[Optional[float], int, int]:
    done = [r for r in subset if r["status"] == "ok" and r["correct"] is not None]
    if not done: return (None, 0, len(subset))
    n_correct = sum(1 for r in done if r["correct"])
    return (n_correct / len(done), len(done), len(subset))


def accuracy_by_judge_target_frame(rows: List[Dict]) -> List[Dict]:
    """One row per (split, judge, target, wording). Also an A-position bias row."""
    out = []
    for split in ("development", "holdout"):
        for judge in F.JUDGE_LABELS:
            for target in F.JUDGE_LABELS:
                for wording in ("NAMED", "SELF"):
                    if wording == "SELF" and judge != target:
                        continue
                    subset = [r for r in rows if r["split"] == split
                              and r["judge_label"] == judge
                              and r["target_label"] == target
                              and r["wording_condition"] == wording]
                    acc, n_scored, n_total = _acc(subset)
                    a_rate_subset = [r for r in subset
                                     if r["status"] == "ok" and r["visible_answer"] in ("A", "B")]
                    a_rate = (sum(1 for r in a_rate_subset if r["visible_answer"] == "A")
                              / len(a_rate_subset)) if a_rate_subset else None
                    out.append({
                        "split": split, "judge": judge, "target": target,
                        "wording": wording,
                        "n_scored": n_scored, "n_planned": n_total,
                        "accuracy": None if acc is None else round(acc, 4),
                        "a_response_rate": None if a_rate is None else round(a_rate, 4),
                    })
    return out


def named_judge_target_matrix(rows: List[Dict]) -> List[Dict]:
    out = []
    for split in ("development", "holdout"):
        for judge in F.JUDGE_LABELS:
            for target in F.JUDGE_LABELS:
                subset = [r for r in rows if r["split"] == split
                          and r["wording_condition"] == "NAMED"
                          and r["judge_label"] == judge
                          and r["target_label"] == target]
                acc, n_scored, n_total = _acc(subset)
                out.append({
                    "split": split, "judge": judge, "target": target,
                    "n_scored": n_scored, "n_planned": n_total,
                    "accuracy": None if acc is None else round(acc, 4),
                })
    return out


# ---------------------------------------------------------------------------
# Section 16: S_M, O_M, F_M on matched items
# ---------------------------------------------------------------------------

def _match_items(rows: List[Dict], split: str, target: str) -> List[str]:
    """Return the complete set of (pair_id, target_item_id) items usable for a
    matched comparison for this target in this split. Only items where all four
    required judgments (SELF + 3 NAMED including the target_producer) are valid."""
    # Group by target_item_id
    by_item: Dict[str, Dict[str, Dict]] = defaultdict(dict)
    for r in rows:
        if r["split"] != split or r["target_label"] != target: continue
        if r["status"] != "ok" or r["correct"] is None: continue
        key = f"{r['wording_condition']}|{r['judge_label']}"
        by_item[r["target_item_id"]][key] = r
    want_keys = {
        f"SELF|{target}",
        f"NAMED|{target}",
    } | {f"NAMED|{j}" for j in F.JUDGE_LABELS if j != target}
    return [item for item, got in by_item.items() if want_keys <= set(got.keys())]


def _contrast_target(rows: List[Dict], split: str, target: str) -> Dict:
    items = _match_items(rows, split, target)
    if not items:
        return {"split": split, "target": target, "n_items": 0,
                "SELF": None, "NAMED": None, "OBS": None,
                "S": None, "O": None, "F": None}
    def _acc_from(items_subset: List[str], wording: str, judge: str) -> Optional[float]:
        correct = 0; tot = 0
        for r in rows:
            if r["target_item_id"] in set(items_subset) \
                    and r["wording_condition"] == wording \
                    and r["judge_label"] == judge \
                    and r["target_label"] == target \
                    and r["split"] == split \
                    and r["status"] == "ok":
                tot += 1
                if r["correct"]: correct += 1
        return correct / tot if tot else None
    SELF = _acc_from(items, "SELF", target)
    NAMED = _acc_from(items, "NAMED", target)
    OBSs = [_acc_from(items, "NAMED", j) for j in F.JUDGE_LABELS if j != target]
    OBS = sum(OBSs) / len(OBSs) if all(x is not None for x in OBSs) else None
    S = (SELF - OBS) if (SELF is not None and OBS is not None) else None
    O = (NAMED - OBS) if (NAMED is not None and OBS is not None) else None
    F_eff = (SELF - NAMED) if (SELF is not None and NAMED is not None) else None
    return {"split": split, "target": target, "n_items": len(items),
            "SELF": None if SELF is None else round(SELF, 4),
            "NAMED": None if NAMED is None else round(NAMED, 4),
            "OBS": None if OBS is None else round(OBS, 4),
            "S": None if S is None else round(S, 4),
            "O": None if O is None else round(O, 4),
            "F": None if F_eff is None else round(F_eff, 4)}


def producer_observer_contrasts(rows: List[Dict]) -> List[Dict]:
    out = []
    for split in ("development", "holdout"):
        for target in F.JUDGE_LABELS:
            out.append(_contrast_target(rows, split, target))
    return out


def self_wording_contrasts(rows: List[Dict]) -> List[Dict]:
    # Same as producer_observer_contrasts but foregrounds F_M; kept as a
    # separate CSV per section 23. Reuse _contrast_target output.
    return producer_observer_contrasts(rows)


# ---------------------------------------------------------------------------
# Section 17: observer roles
# ---------------------------------------------------------------------------

def observer_role_summary(rows: List[Dict]) -> List[Dict]:
    """Per split: accuracy of distractor_producer vs uninvolved_observer when the
    wording is NAMED and the judge is NOT the target."""
    out = []
    for split in ("development", "holdout"):
        for role in ("distractor_producer", "uninvolved_observer"):
            subset = [r for r in rows if r["split"] == split
                      and r["wording_condition"] == "NAMED"
                      and r["judge_role"] == role
                      and r["status"] == "ok" and r["correct"] is not None]
            n = len(subset)
            acc = (sum(1 for r in subset if r["correct"]) / n) if n else None
            out.append({"split": split, "role": role, "n": n,
                        "accuracy": None if acc is None else round(acc, 4)})
    return out


# ---------------------------------------------------------------------------
# Section 17: target complementarity
# ---------------------------------------------------------------------------

def target_complementarity(rows: List[Dict]) -> List[Dict]:
    """Within a pair, if the judge answers consistently for the two target versions,
    the correct answer under target_A and target_B should DISAGREE (one correct_answer
    is A, the other B). Measure the fraction of (judge, pair) where the judge's
    visible answers are different letters."""
    out = []
    by = defaultdict(dict)
    for r in rows:
        if r["wording_condition"] != "NAMED": continue
        if r["status"] != "ok": continue
        if r["visible_answer"] not in ("A", "B"): continue
        by[(r["split"], r["judge_label"], r["pair_id"])][r["target_label"]] = r["visible_answer"]
    for split in ("development", "holdout"):
        for judge in F.JUDGE_LABELS:
            pairs = [(k, v) for k, v in by.items()
                     if k[0] == split and k[1] == judge and len(v) == 2]
            if not pairs:
                out.append({"split": split, "judge": judge,
                            "n_pairs_complete": 0, "pct_complementary": None})
                continue
            comp = sum(1 for (_, v) in pairs if len(set(v.values())) == 2)
            out.append({"split": split, "judge": judge,
                        "n_pairs_complete": len(pairs),
                        "pct_complementary": round(comp / len(pairs), 4)})
    return out


# ---------------------------------------------------------------------------
# Section 19: statistical classifier baselines
# ---------------------------------------------------------------------------

def _features(seq: str, include_full: bool) -> List[float]:
    n = len(seq); n_h = seq.count("H")
    p_h = n_h / n if n else 0.0
    switches = sum(1 for i in range(1, n) if seq[i] != seq[i-1])
    switch_rate = switches / (n - 1) if n > 1 else 0.0
    n_t = n - n_h
    if n_h > 0 and n_t > 0:
        mu = 2 * n_h * n_t / n + 1
        var = 2 * n_h * n_t * (2 * n_h * n_t - n) / (n * n * (n - 1))
        runs = 1 + switches
        runs_z = (runs - mu) / math.sqrt(var) if var > 0 else float("nan")
    else:
        runs_z = float("nan")
    longest = cur = 1
    for i in range(1, n):
        if seq[i] == seq[i-1]:
            cur += 1; longest = max(longest, cur)
        else: cur = 1
    if include_full:
        return [p_h, switch_rate, runs_z, float(longest)]
    return [p_h]


def _standardize(train_feats: List[List[float]]) -> Tuple[List[float], List[float], List[int]]:
    """Return (means, stds, flags) with median-imputation for undefined, applied column-wise.
    Flags[j] = 1 if column j had any undefined values in train (train-only imputation)."""
    n_cols = len(train_feats[0]) if train_feats else 0
    means, stds, flags = [], [], []
    for j in range(n_cols):
        col = [row[j] for row in train_feats]
        defined = [x for x in col if x == x]  # not NaN
        if not defined:
            med = 0.0; flag = 1
        elif len(defined) < len(col):
            med = statistics.median(defined); flag = 1
        else:
            med = statistics.median(defined); flag = 0
        imputed = [x if x == x else med for x in col]
        mu = sum(imputed) / len(imputed)
        sd = math.sqrt(sum((x - mu) ** 2 for x in imputed) / len(imputed)) if len(imputed) > 1 else 1.0
        if sd == 0: sd = 1.0
        means.append(mu); stds.append(sd); flags.append(flag)
    return means, stds, flags


def _apply_standardize(x: List[float], means: List[float], stds: List[float]) -> List[float]:
    return [((xi if xi == xi else means[j]) - means[j]) / stds[j] for j, xi in enumerate(x)]


def _centroid(points: List[List[float]]) -> List[float]:
    if not points: return []
    n_cols = len(points[0])
    return [sum(p[j] for p in points) / len(points) for j in range(n_cols)]


def _sq_distance(a: List[float], b: List[float]) -> float:
    return sum((ai - bi) ** 2 for ai, bi in zip(a, b))


def _fit_baseline(train_rows: List[Dict], feature_set: str):
    """Train centroid-per-model + scalers. Returns a predict(a_seq, b_seq, target, distractor) callable."""
    include_full = (feature_set == "full")
    train_feats = []
    train_labels = []
    for r in train_rows:
        f = _features(r["sequence"], include_full)
        train_feats.append(f); train_labels.append(r["model"])
    means, stds, _ = _standardize(train_feats)
    scaled = [_apply_standardize(f, means, stds) for f in train_feats]
    centroids: Dict[str, List[float]] = {}
    for model in F.JUDGE_LABELS:
        pts = [x for x, lab in zip(scaled, train_labels) if lab == model]
        if pts:
            centroids[model] = _centroid(pts)
    def predict(seq_a: str, seq_b: str, target: str, distractor: str) -> str:
        fa = _apply_standardize(_features(seq_a, include_full), means, stds)
        fb = _apply_standardize(_features(seq_b, include_full), means, stds)
        cost_a = _sq_distance(fa, centroids[target]) + _sq_distance(fb, centroids[distractor])
        cost_b = _sq_distance(fb, centroids[target]) + _sq_distance(fa, centroids[distractor])
        if cost_a < cost_b: return "A"
        if cost_b < cost_a: return "B"
        return "TIE"
    return predict


def baseline_predictions_and_summary(trials: List[Trial], corpus_rows: List[Dict]
                                     ) -> Tuple[List[Dict], List[Dict]]:
    """
    corpus_rows: filtered to history_conditioned trajectories (with model + split + sequence).
    Produces:
      baseline_predictions.csv rows: per-trial per-baseline prediction + correctness.
      baseline_summary.csv rows: aggregate accuracy per split per baseline.

    Holdout: train once on all 30 development trajectories (per baseline).
    Development: leave-one-triplet-out — refit preprocessing + centroids excluding
    the evaluated triplet.
    """
    pred_rows: List[Dict] = []
    summary_rows: List[Dict] = []

    for baseline in ("marginal", "full"):
        # ---- Holdout: trained on all dev ----
        dev = [r for r in corpus_rows if r["split"] == "development"]
        predict = _fit_baseline(dev, baseline)
        hold_pair_items = [t for t in trials if t.split == "holdout"
                           and t.wording_condition == "NAMED"
                           and t.judge_label == t.target_label]  # one row per (pair, target)
        # Deduplicate by (pair_id, target_label)
        seen = set()
        for t in hold_pair_items:
            key = (t.pair_id, t.target_label)
            if key in seen: continue
            seen.add(key)
            pred = predict(t.sequence_A, t.sequence_B, t.target_label, t.distractor_label)
            correct = (pred == t.correct_answer)
            pred_rows.append({
                "split": "holdout", "baseline": baseline,
                "pair_id": t.pair_id, "triplet_id": t.triplet_id,
                "target_label": t.target_label, "distractor_label": t.distractor_label,
                "prediction": pred, "correct_answer": t.correct_answer,
                "correct": None if pred == "TIE" else correct,
                "tie": (pred == "TIE"),
            })

        # ---- Development: leave-one-triplet-out ----
        triplets_dev = sorted({t.triplet_id for t in trials if t.split == "development"})
        for triplet_id in triplets_dev:
            train_rows = [r for r in dev if r["triplet_id"] != triplet_id] if False else \
                         [r for r in dev
                          if not any(t.triplet_id == triplet_id and t.sequence_A_id == r["trajectory_id"]
                                     for t in trials)
                          and not any(t.triplet_id == triplet_id and t.sequence_B_id == r["trajectory_id"]
                                     for t in trials)]
            if not train_rows:
                continue
            fold_predict = _fit_baseline(train_rows, baseline)
            fold_items = [t for t in trials if t.split == "development"
                          and t.triplet_id == triplet_id
                          and t.wording_condition == "NAMED"
                          and t.judge_label == t.target_label]
            seen_f = set()
            for t in fold_items:
                key = (t.pair_id, t.target_label)
                if key in seen_f: continue
                seen_f.add(key)
                pred = fold_predict(t.sequence_A, t.sequence_B, t.target_label, t.distractor_label)
                correct = (pred == t.correct_answer)
                pred_rows.append({
                    "split": "development", "baseline": baseline,
                    "pair_id": t.pair_id, "triplet_id": t.triplet_id,
                    "target_label": t.target_label, "distractor_label": t.distractor_label,
                    "prediction": pred, "correct_answer": t.correct_answer,
                    "correct": None if pred == "TIE" else correct,
                    "tie": (pred == "TIE"),
                })

    # Summary
    for split in ("development", "holdout"):
        for baseline in ("marginal", "full"):
            subset = [p for p in pred_rows if p["split"] == split and p["baseline"] == baseline]
            scored = [p for p in subset if not p["tie"]]
            ties = [p for p in subset if p["tie"]]
            acc = (sum(1 for p in scored if p["correct"]) / len(scored)) if scored else None
            summary_rows.append({
                "split": split, "baseline": baseline,
                "n_scored": len(scored), "n_ties": len(ties), "n_total": len(subset),
                "accuracy": None if acc is None else round(acc, 4),
                "tie_rate": round(len(ties) / len(subset), 4) if subset else None,
            })
    return pred_rows, summary_rows


# ---------------------------------------------------------------------------
# Section 18: triplet bootstrap
# ---------------------------------------------------------------------------

def _acc_from_items(rows_scope: List[Dict], item_ids: set, wording: str, judge: str,
                     target: str) -> Optional[float]:
    tot = 0; correct = 0
    for r in rows_scope:
        if r["target_item_id"] in item_ids \
                and r["wording_condition"] == wording \
                and r["judge_label"] == judge \
                and r["target_label"] == target \
                and r["status"] == "ok":
            tot += 1
            if r["correct"]: correct += 1
    return correct / tot if tot else None


def _bootstrap_split(rows: List[Dict], split: str,
                     reps: int, seed: int) -> Dict[str, Dict]:
    """Return { target_label -> {S:[...], O:[...], F:[...]} resampled triplet distributions }."""
    rng = random.Random(seed)
    # triplets in this split
    triplets = sorted({r["triplet_id"] for r in rows if r["split"] == split})
    # per-triplet target_item_ids
    items_by_triplet: Dict[str, List[str]] = defaultdict(list)
    for r in rows:
        if r["split"] != split: continue
        if r["target_item_id"] not in items_by_triplet[r["triplet_id"]]:
            items_by_triplet[r["triplet_id"]].append(r["target_item_id"])
    rows_scope = [r for r in rows if r["split"] == split]

    boot: Dict[str, Dict[str, List[float]]] = {t: {"S": [], "O": [], "F": []} for t in F.JUDGE_LABELS}
    for _ in range(reps):
        resample = [rng.choice(triplets) for _ in triplets]
        items = set()
        for t in resample:
            items.update(items_by_triplet[t])
        for target in F.JUDGE_LABELS:
            # restrict to items where target_label == target
            tgt_items = {it for it in items if it.endswith(f":{target}")}
            if not tgt_items: continue
            SELF = _acc_from_items(rows_scope, tgt_items, "SELF", target, target)
            NAMED = _acc_from_items(rows_scope, tgt_items, "NAMED", target, target)
            OBSs = [_acc_from_items(rows_scope, tgt_items, "NAMED", j, target)
                    for j in F.JUDGE_LABELS if j != target]
            OBSs = [o for o in OBSs if o is not None]
            OBS = sum(OBSs) / len(OBSs) if OBSs else None
            if SELF is not None and OBS is not None:
                boot[target]["S"].append(SELF - OBS)
            if NAMED is not None and OBS is not None:
                boot[target]["O"].append(NAMED - OBS)
            if SELF is not None and NAMED is not None:
                boot[target]["F"].append(SELF - NAMED)
    return boot


def _pct(dist: List[float], p: float) -> Optional[float]:
    if not dist: return None
    s = sorted(dist)
    k = (len(s) - 1) * p
    f = int(k); c = min(f + 1, len(s) - 1)
    if f == c: return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def bootstrap_intervals(rows: List[Dict], reps: int = F.BOOTSTRAP_REPLICATES,
                        seed: int = F.BOOTSTRAP_SEED) -> List[Dict]:
    out: List[Dict] = []
    for split in ("development", "holdout"):
        boot = _bootstrap_split(rows, split, reps, seed=(seed + hash(split) % 1000))
        for target in F.JUDGE_LABELS:
            for stat in ("S", "O", "F"):
                dist = boot[target][stat]
                out.append({
                    "split": split, "target": target, "stat": stat,
                    "n_replicates": len(dist),
                    "mean": None if not dist else round(sum(dist)/len(dist), 4),
                    "ci_lo": None if not dist else round(_pct(dist, 0.025), 4),
                    "ci_hi": None if not dist else round(_pct(dist, 0.975), 4),
                })
    return out


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def _write_rows(path: str, rows: List[Dict]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8") as f: f.write("")
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows: w.writerow(r)


def write_all_analysis_csvs(out_dir: str, trials: List[Trial],
                            outcomes: Dict[str, Dict], corpus_rows: List[Dict]):
    joined = join_trials_outcomes(trials, outcomes)
    write_trial_level(os.path.join(out_dir, "trial_level.csv"), joined)
    _write_rows(os.path.join(out_dir, "compliance_summary.csv"), compliance_summary(joined))
    _write_rows(os.path.join(out_dir, "accuracy_by_judge_target_frame.csv"),
                accuracy_by_judge_target_frame(joined))
    _write_rows(os.path.join(out_dir, "named_judge_target_matrix.csv"),
                named_judge_target_matrix(joined))
    poc = producer_observer_contrasts(joined)
    _write_rows(os.path.join(out_dir, "producer_observer_contrasts.csv"), poc)
    _write_rows(os.path.join(out_dir, "self_wording_contrasts.csv"),
                self_wording_contrasts(joined))
    _write_rows(os.path.join(out_dir, "observer_role_summary.csv"),
                observer_role_summary(joined))
    _write_rows(os.path.join(out_dir, "target_complementarity.csv"),
                target_complementarity(joined))
    pred, summ = baseline_predictions_and_summary(trials, corpus_rows)
    _write_rows(os.path.join(out_dir, "baseline_predictions.csv"), pred)
    _write_rows(os.path.join(out_dir, "baseline_summary.csv"), summ)
    _write_rows(os.path.join(out_dir, "bootstrap_intervals.csv"), bootstrap_intervals(joined))
    return joined
