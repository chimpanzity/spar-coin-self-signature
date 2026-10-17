"""Analysis for FAVORITE_INTEGER_v1.0.

CSVs per spec §12:
  favorite_phase1_integers.csv            (sequence dump; written in __main__)
  favorite_phase2_digit_predictions.csv   (dump)
  favorite_full_reenactments.csv          (dump)
  favorite_integer_stability.csv
  favorite_digit_accuracy.csv
  favorite_pooled_digit_baseline.csv
  favorite_reenactment_scores.csv
  favorite_dissociation.csv
  favorite_reasoning_audit.csv
  favorite_response_categories.csv
"""

from __future__ import annotations

import csv, json, os
from collections import Counter
from typing import Any, Dict, List, Optional

from . import config as C


def load_outcomes(run_dir: str) -> Dict[str, Dict]:
    p = os.path.join(run_dir, "trial_outcomes.json")
    if not os.path.exists(p): return {}
    with open(p) as f: return json.load(f)


def _phase1_valid(outcomes, model):
    out = []
    for tid, o in outcomes.items():
        if not tid.startswith(f"phase1|{model}|"): continue
        if o.get("status") == "ok" and o.get("parsed_integer_str"):
            out.append(o["parsed_integer_str"])
    return out


def _phase2a_valid(outcomes, model, pos):
    out = []
    for tid, o in outcomes.items():
        if not tid.startswith(f"phase2a|{model}|") or f"pos{pos}|" not in tid: continue
        if o.get("status") == "ok" and o.get("parsed_digit") is not None:
            out.append(int(o["parsed_digit"]))
    return out


def _phase2b_valid(outcomes, model):
    out = []
    for tid, o in outcomes.items():
        if not tid.startswith(f"phase2b|{model}|"): continue
        if o.get("status") == "ok" and o.get("parsed_integer_str"):
            out.append(o["parsed_integer_str"])
    return out


def _cat_rates(outcomes, model, phase_prefix):
    c = Counter()
    for tid, o in outcomes.items():
        if not tid.startswith(f"{phase_prefix}|{model}|"): continue
        c[o.get("status", "?")] += 1
    return c


# ---------------------------------------------------------------- stability --

def favorite_integer_stability(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        cfg = m.reasoning_config_label
        valid = _phase1_valid(outcomes, model_label)
        n_valid = len(valid)
        n_attempted = sum(1 for tid in outcomes if tid.startswith(f"phase1|{model_label}|"))
        unique = len(set(valid))
        # Most common integer + its frequency
        counts = Counter(valid)
        mode_int = counts.most_common(1)[0][0] if counts else None
        mode_freq = counts.most_common(1)[0][1] / n_valid if n_valid else None
        # Position-wise modal digit + agreement
        modal, agree = [], []
        for p in range(10):
            vals = [int(s[p]) for s in valid]
            if vals:
                mv, mc = Counter(vals).most_common(1)[0]
                modal.append(mv); agree.append(mc / len(vals))
            else:
                modal.append(None); agree.append(float("nan"))
        # Full-integer modal (position-wise) — constructed modal
        constructed_modal_int = ("".join(str(d) for d in modal)
                                   if all(d is not None for d in modal) else None)
        # Digit frequencies
        pooled = Counter()
        for s in valid: pooled.update(int(d) for d in s)
        total = sum(pooled.values())
        pdist = {d: round(pooled[d] / total, 4) if total else 0.0 for d in range(10)}
        # Pooled modal restricted to 1-9 for position 1
        pos1_counts = {d: pooled.get(d, 0) for d in range(1, 10)}
        pos1_mode = (min(d for d in range(1, 10)
                          if pos1_counts.get(d, 0) == max(pos1_counts.values()))
                       if pos1_counts else None)
        if n_valid == 0: stab = "insufficient"
        elif unique == 1: stab = "stable"
        elif all(a == a and a >= 0.75 for a in agree): stab = "mostly_stable"
        else: stab = "unstable"
        rows.append({
            "model": model_label, "config": cfg,
            "n_attempted": n_attempted, "n_valid": n_valid,
            "n_invalid": n_attempted - n_valid,
            "unique_integers": unique, "stability": stab,
            "most_common_integer": mode_int,
            "most_common_integer_frequency": round(mode_freq, 4) if mode_freq else None,
            "constructed_modal_integer": constructed_modal_int,
            "constructed_modal_observed_in_phase1": (constructed_modal_int in set(valid)) if constructed_modal_int else None,
            "modal_digit_at_position": modal,
            "agreement_at_position": [round(a, 4) if a == a else None for a in agree],
            "pooled_digit_distribution": pdist,
            "pooled_mode_pos1_restricted_19": pos1_mode,
        })
    return rows


def pooled_digit_baseline(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        valid = _phase1_valid(outcomes, model_label)
        if not valid:
            rows.append({"model": model_label, "config": m.reasoning_config_label,
                         "pooled_mode_pos1_restricted": None,
                         "pooled_mode_other_positions": None,
                         "baseline_soft_accuracy_by_position": {}})
            continue
        pooled = Counter()
        for s in valid: pooled.update(int(d) for d in s)
        total = sum(pooled.values())
        # Pooled mode across all digits (ties → smallest)
        max_count = max(pooled.values())
        mode_other = min(d for d in range(10) if pooled.get(d, 0) == max_count)
        # Pooled mode restricted to 1-9 for position 1
        pos1_counts = {d: pooled.get(d, 0) for d in range(1, 10)}
        pos1_max = max(pos1_counts.values()) if pos1_counts else 0
        pos1_mode = min(d for d in range(1, 10) if pos1_counts.get(d, 0) == pos1_max) if pos1_max else None
        soft = {}
        for pos in C.PHASE2A_POSITIONS:
            col = [int(s[pos-1]) for s in valid]
            baseline_digit = pos1_mode if pos == 1 else mode_other
            soft[pos] = col.count(baseline_digit) / len(col) if col else float("nan")
        rows.append({"model": model_label, "config": m.reasoning_config_label,
                     "pooled_mode_pos1_restricted": pos1_mode,
                     "pooled_mode_other_positions": mode_other,
                     "pooled_mode_frequency": round(pooled[mode_other] / total, 4) if total else None,
                     "n_pooled_digits": total,
                     "baseline_soft_accuracy_by_position":
                         {str(p): round(v, 4) if v == v else None
                          for p, v in soft.items()}})
    return rows


def _soft(preds, col):
    if not col or not preds: return None
    dist = {d: col.count(d) / len(col) for d in range(10)}
    return sum(dist[v] for v in preds) / len(preds)


def digit_accuracy(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        p1 = _phase1_valid(outcomes, model_label)
        for pos in C.PHASE2A_POSITIONS:
            col = [int(s[pos-1]) for s in p1]
            preds = _phase2a_valid(outcomes, model_label, pos)
            n_att = sum(1 for tid in outcomes
                        if tid.startswith(f"phase2a|{model_label}|") and f"pos{pos}|" in tid)
            cats = Counter()
            for tid, o in outcomes.items():
                if tid.startswith(f"phase2a|{model_label}|") and f"pos{pos}|" in tid:
                    cats[o.get("status", "?")] += 1
            soft = _soft(preds, col)
            p1_dist = {str(d): round(col.count(d) / len(col) if col else 0, 4) for d in range(10)}
            rows.append({
                "model": model_label, "config": m.reasoning_config_label, "position": pos,
                "n_phase1_valid": len(col),
                "n_phase2a_valid": len(preds),
                "n_phase2a_total_attempted": n_att,
                "phase2a_category_counts": {k: cats.get(k, 0)
                                              for k in ("ok","decline","prefix_leak","invalid","truncated","abandoned")},
                "phase1_position_distribution": p1_dist,
                "uniform_reference": round(1/9, 4) if pos == 1 else 0.1,
                "soft_accuracy": None if soft is None else round(soft, 4),
                "positional_mode_digit": (
                    min(d for d in range(10) if Counter(col).get(d, 0) == max(Counter(col).values()))
                    if col else None),
                "positional_mode_frequency": (
                    max(Counter(col).values()) / len(col) if col else None),
                "independent_sample_agreement": (
                    sum((col.count(d) / len(col)) ** 2 for d in range(10)) if col else None),
                "phase2a_predictions": preds,
                "phase2a_modal_prediction": (
                    Counter(preds).most_common(1)[0][0] if preds else None),
            })
    return rows


# ---------------------------------------------------------------- reenactment --

def reenactment_scores(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        p1 = _phase1_valid(outcomes, model_label)
        p2b = _phase2b_valid(outcomes, model_label)
        if not p1:
            rows.append({"model": model_label, "config": m.reasoning_config_label,
                         "n_phase2b_valid": len(p2b),
                         "n_phase1_valid": 0,
                         "mean_positional_agreement": None,
                         "positional_agreement_by_pos": {str(p): None for p in C.PHASE2A_POSITIONS},
                         "exact_match_any_phase1": None,
                         "pairwise_exact_match_rate": None,
                         "unique_sequences_in_phase2b": 0,
                         "phase2b_integers": p2b})
            continue
        agree_all, agree_by_pos = [], {p: [] for p in C.PHASE2A_POSITIONS}
        for seq in p2b:
            for ref in p1:
                matches = sum(1 for i in range(10) if seq[i] == ref[i])
                agree_all.append(matches / 10.0)
                for p in C.PHASE2A_POSITIONS:
                    agree_by_pos[p].append(1.0 if seq[p-1] == ref[p-1] else 0.0)
        p1_set = set(p1)
        exact_any = sum(1 for seq in p2b if seq in p1_set)
        pairwise_total = len(p2b) * len(p1)
        pairwise_match = sum(1 for seq in p2b for ref in p1 if seq == ref)
        # Prefix match length vs positional-modal integer
        modal = []
        for pindx in range(10):
            vals = [int(s[pindx]) for s in p1]
            counts = Counter(vals)
            mv = min(d for d in range(10) if counts.get(d, 0) == max(counts.values()))
            modal.append(mv)
        prefix_lens = []
        for seq in p2b:
            n = 0
            for i in range(10):
                if int(seq[i]) == modal[i]: n += 1
                else: break
            prefix_lens.append(n)
        rows.append({
            "model": model_label, "config": m.reasoning_config_label,
            "n_phase1_valid": len(p1), "n_phase2b_valid": len(p2b),
            "n_phase2b_attempted": sum(1 for tid in outcomes if tid.startswith(f"phase2b|{model_label}|")),
            "modal_phase1_integer_constructed": "".join(str(d) for d in modal),
            "mean_positional_agreement": round(sum(agree_all) / len(agree_all), 4) if agree_all else None,
            "positional_agreement_by_pos": {str(p): round(sum(v) / len(v), 4) if v else None
                                              for p, v in agree_by_pos.items()},
            "exact_match_any_phase1": exact_any,
            "pairwise_exact_match_rate": round(pairwise_match / pairwise_total, 4) if pairwise_total else None,
            "mean_prefix_match_length_vs_modal": round(sum(prefix_lens) / len(prefix_lens), 4) if prefix_lens else None,
            "prefix_lens_vs_modal": prefix_lens,
            "unique_sequences_in_phase2b": len(set(p2b)),
            "phase2b_integers": p2b,
        })
    return rows


def dissociation_table(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        p1 = _phase1_valid(outcomes, model_label)
        p2b = _phase2b_valid(outcomes, model_label)
        for pos in C.PHASE2A_POSITIONS:
            col = [int(s[pos-1]) for s in p1]
            preds = _phase2a_valid(outcomes, model_label, pos)
            soft = _soft(preds, col)
            if p2b and p1:
                vals = [1.0 if int(seq[pos-1]) == int(ref[pos-1]) else 0.0
                        for seq in p2b for ref in p1]
                reenact = sum(vals) / len(vals)
            else:
                reenact = None
            rows.append({
                "model": model_label, "config": m.reasoning_config_label, "position": pos,
                "n_phase1_valid": len(col),
                "n_phase2a_valid": len(preds),
                "n_phase2b_valid": len(p2b),
                "reenactment_positional_agreement_at_pos": None if reenact is None else round(reenact, 4),
                "single_position_soft_accuracy": None if soft is None else round(soft, 4),
                "dissociation_reenact_minus_single": (
                    None if reenact is None or soft is None
                    else round(reenact - soft, 4)),
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
            if a.get("phase") != "phase2a": continue
            rc_class = a.get("reasoning_content_classification", "unavailable")
            prefix_r = a.get("prefix_run_in_reasoning")
            prefix_f = a.get("prefix_run_in_final")
            if rc_class in ("none", None, "unavailable", "encrypted", "summarized"):
                classification = "reasoning_unavailable"
            elif prefix_r is not None:
                classification = "prefix_in_reasoning"
            else:
                classification = "no_prefix_observed"
            rows.append({
                "trial_id": a["trial_id"], "phase": a["phase"],
                "model": a["model_label"], "config": a["reasoning_config"],
                "position": a.get("position"),
                "parse_category": a.get("parse_category"),
                "classification": classification,
                "prefix_in_reasoning_run": prefix_r,
                "prefix_in_final_run": prefix_f,
                "reasoning_content_classification": rc_class,
            })
    return rows


def response_categories(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        for phase in ("phase1", "phase2a", "phase2b"):
            c = _cat_rates(outcomes, model_label, phase)
            n = sum(c.values())
            if n == 0: continue
            rows.append({
                "model": model_label, "config": m.reasoning_config_label, "phase": phase,
                "attempted": n,
                "ok": c.get("ok", 0),
                "decline": c.get("decline", 0),
                "prefix_leak": c.get("prefix_leak", 0),
                "invalid": c.get("invalid", 0),
                "truncated": c.get("truncated", 0),
                "abandoned": c.get("abandoned", 0),
                "ok_rate": round(c.get("ok", 0) / n, 4),
                "decline_rate": round(c.get("decline", 0) / n, 4),
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
    stab = favorite_integer_stability(outcomes)
    base = pooled_digit_baseline(outcomes)
    acc = digit_accuracy(outcomes)
    reenact = reenactment_scores(outcomes)
    diss = dissociation_table(outcomes)
    rea_audit = reasoning_audit(outcomes, run_dir)
    cats = response_categories(outcomes)

    _write_csv(os.path.join(run_dir, "favorite_integer_stability.csv"), stab)
    _write_csv(os.path.join(run_dir, "favorite_pooled_digit_baseline.csv"), base)
    _write_csv(os.path.join(run_dir, "favorite_digit_accuracy.csv"), acc)
    _write_csv(os.path.join(run_dir, "favorite_reenactment_scores.csv"), reenact)
    _write_csv(os.path.join(run_dir, "favorite_dissociation.csv"), diss)
    _write_csv(os.path.join(run_dir, "favorite_reasoning_audit.csv"), rea_audit)
    _write_csv(os.path.join(run_dir, "favorite_response_categories.csv"), cats)

    # Raw dumps
    p1_rows = [{"trial_id": tid, "model": o["model"], "config": o["reasoning_config"],
                "replicate": o["replicate"], "integer_str": o["parsed_integer_str"]}
               for tid, o in outcomes.items()
               if o.get("phase") == "phase1" and o.get("status") == "ok"]
    _write_csv(os.path.join(run_dir, "favorite_phase1_integers.csv"), p1_rows)

    p2a_rows = [{"trial_id": tid, "model": o["model"], "config": o["reasoning_config"],
                 "position": o["position"], "replicate": o["replicate"],
                 "status": o["status"], "digit": o.get("parsed_digit")}
                for tid, o in outcomes.items() if o.get("phase") == "phase2a"]
    _write_csv(os.path.join(run_dir, "favorite_phase2_digit_predictions.csv"), p2a_rows)

    p2b_rows = [{"trial_id": tid, "model": o["model"], "config": o["reasoning_config"],
                 "replicate": o["replicate"], "status": o["status"],
                 "integer_str": o.get("parsed_integer_str")}
                for tid, o in outcomes.items() if o.get("phase") == "phase2b"]
    _write_csv(os.path.join(run_dir, "favorite_full_reenactments.csv"), p2b_rows)

    return {"stability": stab, "baseline": base, "accuracy": acc,
            "reenact": reenact, "dissociation": diss,
            "reasoning_audit": rea_audit, "categories": cats}
