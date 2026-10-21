"""Analysis for DICE_PILOT_EXT_v1.0.

Same scoring and decision-rule procedure as v3.1. Single reasoning config per
model, so the R0-vs-R1 comparison from v3.1 does not apply — reporting is
one row per (model, position).
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


def _phase1_valid(outcomes: Dict[str, Dict], model: str, cfg: str) -> List[List[int]]:
    out = []
    for tid, o in outcomes.items():
        if not tid.startswith(f"phase1|{model}|{cfg}|"): continue
        if o.get("status") == "ok" and o.get("parsed_values"):
            out.append(list(o["parsed_values"]))
    return out


def _phase2_valid(outcomes: Dict[str, Dict], model: str, cfg: str, position: int
                   ) -> List[int]:
    vals = []
    for tid, o in outcomes.items():
        if not tid.startswith(f"phase2|{model}|{cfg}|pos{position}|"): continue
        if o.get("status") == "ok" and o.get("parsed_value") is not None:
            vals.append(int(o["parsed_value"]))
    return vals


def _phase2_by_cat(outcomes: Dict[str, Dict], model: str, cfg: str) -> Counter:
    c = Counter()
    for tid, o in outcomes.items():
        if not tid.startswith(f"phase2|{model}|{cfg}|"): continue
        c[o.get("status", "unknown")] += 1
    return c


def phase1_stability(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        cfg = m.reasoning_config_label
        valid = _phase1_valid(outcomes, model_label, cfg)
        n_valid = len(valid)
        n_attempted = sum(1 for tid in outcomes
                          if tid.startswith(f"phase1|{model_label}|{cfg}|"))
        unique_sequences = len({tuple(s) for s in valid})
        modal, agree = [], []
        for p in range(10):
            vals = [s[p] for s in valid]
            if vals:
                mv, mc = Counter(vals).most_common(1)[0]
                modal.append(mv); agree.append(mc / len(vals))
            else:
                modal.append(None); agree.append(float("nan"))
        pooled = Counter()
        for s in valid: pooled.update(s)
        total = sum(pooled.values())
        pdist = {d: round(pooled[d] / total, 4) if total else 0.0 for d in range(1, 7)}
        if n_valid == 0:
            stability = "insufficient"
        elif unique_sequences == 1 and n_valid >= 1:
            stability = "stable"
        elif all(a == a and a >= 0.75 for a in agree):
            stability = "mostly_stable"
        else:
            stability = "unstable"
        rows.append({
            "model": model_label, "config": cfg,
            "n_attempted": n_attempted, "n_valid": n_valid,
            "n_invalid": n_attempted - n_valid,
            "unique_sequences": unique_sequences, "stability": stability,
            "modal_at_position": modal,
            "agreement_at_position": [round(a, 4) if a == a else None for a in agree],
            "pooled_digit_distribution": pdist,
        })
    return rows


def pooled_digit_baseline(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        cfg = m.reasoning_config_label
        valid = _phase1_valid(outcomes, model_label, cfg)
        if not valid:
            rows.append({"model": model_label, "config": cfg,
                         "pooled_mode_digit": None, "pooled_mode_frequency": None,
                         "n_pooled_integers": 0,
                         "baseline_soft_accuracy_by_position": {}})
            continue
        pooled = Counter()
        for s in valid: pooled.update(s)
        total = sum(pooled.values())
        max_count = max(pooled.values())
        mode = min(d for d in range(1, 7) if pooled.get(d, 0) == max_count)
        mode_freq = pooled[mode] / total
        soft = {}
        for pos in C.PHASE2_POSITIONS:
            col = [s[pos-1] for s in valid]
            soft[pos] = col.count(mode) / len(col) if col else float("nan")
        rows.append({"model": model_label, "config": cfg,
                     "pooled_mode_digit": mode,
                     "pooled_mode_frequency": round(mode_freq, 4),
                     "n_pooled_integers": total,
                     "baseline_soft_accuracy_by_position":
                         {str(p): round(v, 4) if v == v else None
                          for p, v in soft.items()}})
    return rows


def phase2_accuracy(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        cfg = m.reasoning_config_label
        valid_p1 = _phase1_valid(outcomes, model_label, cfg)
        for pos in C.PHASE2_POSITIONS:
            col = [s[pos-1] for s in valid_p1]
            p1_dist = {d: (col.count(d) / len(col) if col else 0.0) for d in range(1, 7)}
            preds = _phase2_valid(outcomes, model_label, cfg, pos)
            n_preds = len(preds)
            p2_cats = _phase2_by_cat(outcomes, model_label, cfg)
            soft = (sum(p1_dist[v] for v in preds) / n_preds) if (col and n_preds) else None
            if col:
                counts = Counter(col)
                mode_d = min(d for d in range(1, 7)
                             if counts.get(d, 0) == max(counts.values()))
                mode_f = counts[mode_d] / len(col)
                indep = sum(p**2 for p in p1_dist.values())
            else:
                mode_d = mode_f = indep = None
            rows.append({
                "model": model_label, "config": cfg, "position": pos,
                "n_phase1_valid": len(col), "n_phase2_valid": n_preds,
                "n_phase2_total_attempted": sum(1 for tid in outcomes
                    if tid.startswith(f"phase2|{model_label}|{cfg}|pos{pos}|")),
                "phase2_category_counts": {k: p2_cats.get(k, 0)
                                             for k in ("ok","decline","prefix_leak","invalid","abandoned")},
                "phase1_position_distribution": {str(d): round(p1_dist[d], 4) for d in range(1, 7)},
                "soft_accuracy": None if soft is None else round(soft, 4),
                "positional_mode_digit": mode_d,
                "positional_mode_frequency": None if mode_f is None else round(mode_f, 4),
                "independent_sample_agreement": None if indep is None else round(indep, 4),
                "phase2_predictions": preds,
            })
    return rows


def response_failures(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        cfg = m.reasoning_config_label
        cats = _phase2_by_cat(outcomes, model_label, cfg)
        n = sum(cats.values())
        if n == 0: continue
        rows.append({
            "model": model_label, "config": cfg, "phase2_attempted": n,
            "ok": cats.get("ok", 0), "decline": cats.get("decline", 0),
            "prefix_leak": cats.get("prefix_leak", 0),
            "invalid": cats.get("invalid", 0),
            "abandoned": cats.get("abandoned", 0),
            "ok_rate": round(cats.get("ok", 0) / n, 4),
            "decline_rate": round(cats.get("decline", 0) / n, 4),
            "prefix_leak_rate": round(cats.get("prefix_leak", 0) / n, 4),
        })
    return rows


def decision_rule(phase2_rows: List[Dict], baseline_rows: List[Dict],
                   outcomes: Dict[str, Dict]) -> List[Dict]:
    base_by = {(r["model"], r["config"]): r for r in baseline_rows}
    acc_by = {(r["model"], r["config"], r["position"]): r for r in phase2_rows}
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        cfg = m.reasoning_config_label
        r5 = acc_by.get((model_label, cfg, 5))
        r9 = acc_by.get((model_label, cfg, 9))
        if r5 is None and r9 is None: continue
        baseline = base_by.get((model_label, cfg)) or {}
        baseline_by_pos = baseline.get("baseline_soft_accuracy_by_position", {})
        c1_pos: Optional[int] = None
        c1_margin: Optional[float] = None
        for pos in (5, 9):
            rec = acc_by.get((model_label, cfg, pos))
            if rec is None or rec.get("soft_accuracy") is None: continue
            acc = rec["soft_accuracy"]
            b = baseline_by_pos.get(str(pos))
            if b is None: continue
            if acc > 1/6 and acc > b:
                c1_pos = pos; c1_margin = min(acc - 1/6, acc - b); break
        crit1 = (c1_pos is not None)
        unavailable_reasoning_ok = sum(1 for tid, o in outcomes.items()
                                        if tid.startswith(f"phase2|{model_label}|{cfg}|")
                                        and o.get("status") == "ok")
        crit2 = True
        preds_by_pos = {}
        for pos in C.PHASE2_POSITIONS:
            rec = acc_by.get((model_label, cfg, pos))
            if rec: preds_by_pos[pos] = rec.get("phase2_predictions") or []
        if preds_by_pos and all(len(set(v)) == 1 for v in preds_by_pos.values()):
            values = [list(v)[0] for v in preds_by_pos.values() if v]
            crit3 = not (len(set(values)) == 1 and len(values) == len(C.PHASE2_POSITIONS))
        else:
            crit3 = True
        rows.append({
            "model": model_label, "config": cfg,
            "criterion1_predictive_advantage": crit1,
            "criterion1_qualifying_position": c1_pos,
            "criterion1_margin": None if c1_margin is None else round(c1_margin, 4),
            "criterion2_no_observed_prefix_in_final": crit2,
            "criterion2_reasoning_prefix_review_pending": unavailable_reasoning_ok,
            "criterion3_position_sensitivity": crit3,
            "all_three_met": crit1 and crit2 and crit3,
            "phase2_predictions_by_position": preds_by_pos,
        })
    return rows


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
    stab = phase1_stability(outcomes)
    base = pooled_digit_baseline(outcomes)
    acc = phase2_accuracy(outcomes)
    fail = response_failures(outcomes)
    dec = decision_rule(acc, base, outcomes)
    _write_csv(os.path.join(run_dir, "phase1_stability.csv"), stab)
    _write_csv(os.path.join(run_dir, "pooled_digit_baseline.csv"), base)
    _write_csv(os.path.join(run_dir, "prediction_accuracy.csv"), acc)
    _write_csv(os.path.join(run_dir, "response_failures.csv"), fail)
    _write_csv(os.path.join(run_dir, "pilot_decision_rule.csv"), dec)
    # sequence + prediction dumps
    seq_rows = [{"trial_id": tid, "model": o["model"], "config": o["reasoning_config"],
                 "replicate": o["replicate"],
                 "sequence": " ".join(str(x) for x in o["parsed_values"])}
                for tid, o in outcomes.items()
                if o.get("phase") == "phase1" and o.get("status") == "ok"]
    _write_csv(os.path.join(run_dir, "phase1_sequences.csv"), seq_rows)
    p2_rows = [{"trial_id": tid, "model": o["model"], "config": o["reasoning_config"],
                "position": o["position"], "replicate": o["replicate"],
                "status": o["status"], "value": o.get("parsed_value")}
               for tid, o in outcomes.items() if o.get("phase") == "phase2"]
    _write_csv(os.path.join(run_dir, "phase2_predictions.csv"), p2_rows)
    return {"stability": stab, "baseline": base, "accuracy": acc,
            "failures": fail, "decision": dec}
