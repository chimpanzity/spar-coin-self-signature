"""Analysis for FAVORITE_ANIMAL_CROSSED_v1.0.

CSVs:
  crossed_phase2_predictions.csv       dump
  crossed_prediction_accuracy.csv      per (predictor, target, position)
  crossed_pair_summary.csv             overall accuracy per (predictor, target)
  crossed_self_vs_other.csv            self-row + cross-row comparison (for critical disambiguator)
  crossed_response_categories.csv      ok/decline/prefix_leak rates
  crossed_reasoning_audit.csv          per-trial reasoning classification
"""

from __future__ import annotations

import csv, json, os
from collections import Counter
from typing import Any, Dict, List

from . import config as C
from .parsers import letter_at
from spar_dynamic.favorite_animal.candidate_detector import classify as classify_reasoning


# Prior pilot data: each model's canonical favorite scoring string.
# Hard-coded from favanim-20261016T103809Z.
PRIOR_SELF_ACCURACY = {
    "astra":  {"first": 0.0, "second": 0.0, "penultimate": 0.0, "last": 0.0},
    "fable":  {"first": 1.0, "second": 1.0, "penultimate": 1.0, "last": 1.0},
    "oss120": {"first": 0.2, "second": 0.0, "penultimate": 1.0, "last": 0.0},
}


def load_outcomes(run_dir: str) -> Dict[str, Dict]:
    p = os.path.join(run_dir, "trial_outcomes.json")
    if not os.path.exists(p): return {}
    with open(p) as f: return json.load(f)


def _crossed_valid(outcomes, predictor, target, position):
    out = []
    for tid, o in outcomes.items():
        if (o.get("predictor_model") == predictor
                and o.get("target_model") == target
                and o.get("position") == position
                and o.get("status") == "ok"
                and o.get("parsed_letter")):
            out.append(o["parsed_letter"])
    return out


def _cat_counts(outcomes, predictor, target):
    c = Counter()
    for tid, o in outcomes.items():
        if (o.get("predictor_model") == predictor
                and o.get("target_model") == target):
            c[o.get("status", "?")] += 1
    return c


def crossed_prediction_accuracy(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for (predictor, target) in C.CROSS_PAIRS:
        target_fav = C.PRIOR_CANONICAL_FAVORITE[target]
        for pos in C.PHASE2_POSITIONS:
            true_letter = letter_at(target_fav, pos)
            preds = _crossed_valid(outcomes, predictor, target, pos)
            n_att = sum(1 for tid, o in outcomes.items()
                        if o.get("predictor_model") == predictor
                        and o.get("target_model") == target
                        and o.get("position") == pos)
            soft = (sum(1 for p in preds if p == true_letter) / len(preds)) if preds else None
            rows.append({
                "predictor": predictor, "target": target,
                "target_favorite": target_fav,
                "position": pos,
                "true_letter": true_letter,
                "n_predictions_attempted": n_att,
                "n_predictions_valid": len(preds),
                "soft_accuracy": None if soft is None else round(soft, 4),
                "predictions": preds,
                "modal_prediction": (Counter(preds).most_common(1)[0][0] if preds else None),
            })
    return rows


def crossed_pair_summary(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for (predictor, target) in C.CROSS_PAIRS:
        target_fav = C.PRIOR_CANONICAL_FAVORITE[target]
        n_att = 0; n_valid = 0; n_correct = 0
        pos_breakdown = {}
        for pos in C.PHASE2_POSITIONS:
            true_letter = letter_at(target_fav, pos)
            preds = _crossed_valid(outcomes, predictor, target, pos)
            attempts = sum(1 for tid, o in outcomes.items()
                            if o.get("predictor_model") == predictor
                            and o.get("target_model") == target
                            and o.get("position") == pos)
            correct = sum(1 for p in preds if p == true_letter)
            n_att += attempts; n_valid += len(preds); n_correct += correct
            pos_breakdown[pos] = {"true": true_letter,
                                     "n_valid": len(preds), "n_correct": correct}
        rows.append({
            "predictor": predictor, "target": target,
            "target_favorite": target_fav,
            "n_predictions_attempted": n_att,
            "n_predictions_valid": n_valid,
            "n_correct": n_correct,
            "overall_accuracy": round(n_correct / n_valid, 4) if n_valid else None,
            "overall_accuracy_against_attempted": round(n_correct / n_att, 4) if n_att else None,
            "pos_breakdown": pos_breakdown,
        })
    return rows


def crossed_self_vs_other(outcomes: Dict[str, Dict]) -> List[Dict]:
    """For each predictor, compare the predictor's own prior self-accuracy
    (from favanim) with its accuracy at predicting the other models'
    favorites. This is the disambiguating analysis."""
    pair_summary = {(r["predictor"], r["target"]): r
                      for r in crossed_pair_summary(outcomes)}
    rows = []
    for predictor in C.EXECUTION_ORDER:
        prior_self = PRIOR_SELF_ACCURACY.get(predictor, {})
        self_overall = sum(prior_self.values()) / len(prior_self) if prior_self else None
        # Average cross-accuracy against targets ≠ self
        cross_rows = [pair_summary.get((predictor, t)) for t in C.EXECUTION_ORDER
                        if t != predictor and pair_summary.get((predictor, t))]
        if not cross_rows: continue
        cross_overall = sum(r["overall_accuracy"] or 0 for r in cross_rows) / len(cross_rows)
        # Per-target overall
        per_target = {r["target"]: r["overall_accuracy"] for r in cross_rows}
        rows.append({
            "predictor": predictor,
            "prior_self_accuracy_mean": round(self_overall, 4) if self_overall is not None else None,
            "prior_self_accuracy_by_position": prior_self,
            "crossed_mean_other": round(cross_overall, 4),
            "crossed_per_target": per_target,
            "delta_cross_minus_self": (
                round(cross_overall - self_overall, 4)
                if self_overall is not None else None),
        })
    return rows


def response_categories(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for (predictor, target) in C.CROSS_PAIRS:
        c = _cat_counts(outcomes, predictor, target)
        n = sum(c.values())
        if n == 0: continue
        rows.append({
            "predictor": predictor, "target": target,
            "attempted": n,
            "ok": c.get("ok", 0), "decline": c.get("decline", 0),
            "prefix_leak": c.get("prefix_leak", 0),
            "invalid": c.get("invalid", 0),
            "truncated": c.get("truncated", 0),
            "abandoned": c.get("abandoned", 0),
            "ok_rate": round(c.get("ok", 0) / n, 4),
            "decline_rate": round(c.get("decline", 0) / n, 4),
        })
    return rows


def reasoning_audit(outcomes: Dict[str, Dict], run_dir: str) -> List[Dict]:
    path = os.path.join(run_dir, "raw_attempts.jsonl")
    rows = []
    if not os.path.exists(path): return rows
    with open(path) as f:
        for line in f:
            if not line.strip(): continue
            a = json.loads(line)
            target_label = a.get("target_model")
            target_fav = C.PRIOR_CANONICAL_FAVORITE.get(target_label)
            rc = a.get("reasoning_content") or ""
            rc_class = a.get("reasoning_content_classification", "unavailable")
            cls, info = classify_reasoning(rc, rc_class, target_fav)
            rows.append({
                "trial_id": a.get("trial_id"),
                "predictor": a.get("predictor_model"),
                "target": target_label,
                "target_favorite": target_fav,
                "position": a.get("position"),
                "parse_category": a.get("parse_category"),
                "classification": cls,
                "candidates_found": info.get("candidates"),
                "target_fav_mentioned_in_reasoning": info.get("modal_mentioned"),
                "reasoning_content_classification": rc_class,
            })
    return rows


# ---------------------------------------------------------------- writers --

def _write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8") as f: f.write(""); return
    def _flat(v):
        if isinstance(v, (dict, list)): return json.dumps(v, sort_keys=True)
        return v
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows: w.writerow({k: _flat(r.get(k)) for k in keys})


def write_all(run_dir: str) -> Dict[str, Any]:
    outcomes = load_outcomes(run_dir)
    acc = crossed_prediction_accuracy(outcomes)
    pair = crossed_pair_summary(outcomes)
    svo = crossed_self_vs_other(outcomes)
    cats = response_categories(outcomes)
    audit = reasoning_audit(outcomes, run_dir)
    _write_csv(os.path.join(run_dir, "crossed_prediction_accuracy.csv"), acc)
    _write_csv(os.path.join(run_dir, "crossed_pair_summary.csv"), pair)
    _write_csv(os.path.join(run_dir, "crossed_self_vs_other.csv"), svo)
    _write_csv(os.path.join(run_dir, "crossed_response_categories.csv"), cats)
    _write_csv(os.path.join(run_dir, "crossed_reasoning_audit.csv"), audit)
    # Dump of all per-trial predictions
    pred_rows = [{"trial_id": tid, "predictor": o.get("predictor_model"),
                   "target": o.get("target_model"),
                   "target_name": o.get("target_name"),
                   "position": o.get("position"),
                   "replicate": o.get("replicate"),
                   "status": o.get("status"),
                   "letter": o.get("parsed_letter")}
                  for tid, o in outcomes.items()]
    _write_csv(os.path.join(run_dir, "crossed_phase2_predictions.csv"), pred_rows)
    return {"accuracy": acc, "pair": pair, "self_vs_other": svo,
            "categories": cats, "audit": audit}
