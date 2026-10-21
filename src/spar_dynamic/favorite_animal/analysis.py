"""Analysis for FAVORITE_ANIMAL_v1.0.

CSVs per spec §12:
  favorite_animal_phase1.csv              dump
  favorite_animal_letter_predictions.csv  dump
  favorite_animal_reenactments.csv        dump
  animal_name_stability.csv
  letter_prediction_accuracy.csv
  pooled_letter_baseline.csv
  animal_reenactment_scores.csv
  generation_anticipation_dissociation.csv
  reasoning_candidate_audit.csv
  response_categories.csv
"""

from __future__ import annotations

import csv, json, os
from collections import Counter
from typing import Any, Dict, List, Optional

from . import config as C
from .parsers import letter_at
from .candidate_detector import classify as classify_reasoning


def load_outcomes(run_dir: str) -> Dict[str, Dict]:
    p = os.path.join(run_dir, "trial_outcomes.json")
    if not os.path.exists(p): return {}
    with open(p) as f: return json.load(f)


def _p1_valid(outcomes, model):
    """List of (normalized_name, scoring_string) for valid Phase 1 entries."""
    out = []
    for tid, o in outcomes.items():
        if not tid.startswith(f"phase1|{model}|"): continue
        if o.get("status") == "ok" and o.get("parsed_scoring_string"):
            out.append((o["parsed_normalized_name"], o["parsed_scoring_string"]))
    return out


def _p2a_valid(outcomes, model, position):
    out = []
    for tid, o in outcomes.items():
        if not tid.startswith(f"phase2a|{model}|") or f"pos{position}|" not in tid: continue
        if o.get("status") == "ok" and o.get("parsed_letter"):
            out.append(o["parsed_letter"])
    return out


def _p2b_valid(outcomes, model):
    out = []
    for tid, o in outcomes.items():
        if not tid.startswith(f"phase2b|{model}|"): continue
        if o.get("status") == "ok" and o.get("parsed_scoring_string"):
            out.append((o["parsed_normalized_name"], o["parsed_scoring_string"]))
    return out


def _cat_rates(outcomes, model, phase_prefix):
    c = Counter()
    for tid, o in outcomes.items():
        if not tid.startswith(f"{phase_prefix}|{model}|"): continue
        c[o.get("status", "?")] += 1
    return c


# ---------------------------------------------------------------- stability --

def animal_name_stability(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        cfg = m.reasoning_config_label
        valid = _p1_valid(outcomes, model_label)
        n_valid = len(valid)
        n_attempted = sum(1 for tid in outcomes if tid.startswith(f"phase1|{model_label}|"))
        names = [n for n, _ in valid]
        scoring = [s for _, s in valid]
        name_counts = Counter(names)
        mode_name = name_counts.most_common(1)[0][0] if name_counts else None
        mode_freq = (name_counts.most_common(1)[0][1] / n_valid) if n_valid else None
        unique = len(set(names))
        # Position-specific agreement
        agree_pos = {}
        letters_pos = {}
        for pos in C.PHASE2A_POSITIONS:
            letters = [letter_at(s, pos) for s in scoring]
            letters = [l for l in letters if l is not None]
            letters_pos[pos] = letters
            if letters:
                mc = Counter(letters).most_common(1)[0][1]
                agree_pos[pos] = mc / len(letters)
            else:
                agree_pos[pos] = None
        # Length distribution
        lengths = [len(s) for s in scoring]
        length_dist = dict(Counter(lengths))
        if n_valid == 0: stab = "insufficient"
        elif unique == 1: stab = "stable"
        elif all((a is not None and a >= 0.75) for a in agree_pos.values()): stab = "mostly_stable"
        else: stab = "unstable"
        rows.append({
            "model": model_label, "config": cfg,
            "n_attempted": n_attempted, "n_valid": n_valid,
            "n_invalid": n_attempted - n_valid,
            "unique_names": unique, "stability": stab,
            "most_common_name": mode_name,
            "most_common_name_frequency": round(mode_freq, 4) if mode_freq is not None else None,
            "all_phase1_names": names,
            "scoring_strings": scoring,
            "length_distribution": length_dist,
            "agreement_at_position": {pos: (round(agree_pos[pos], 4) if agree_pos[pos] is not None else None)
                                       for pos in C.PHASE2A_POSITIONS},
            "letters_at_position": letters_pos,
        })
    return rows


# ---------------------------------------------------------------- baselines --

def pooled_letter_baseline(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        valid = _p1_valid(outcomes, model_label)
        if not valid:
            rows.append({"model": model_label, "config": m.reasoning_config_label,
                         "pooled_mode_letter": None, "pooled_mode_frequency": None,
                         "baseline_soft_accuracy_by_position": {}})
            continue
        pooled = Counter()
        for _, s in valid: pooled.update(s)
        total = sum(pooled.values())
        max_count = max(pooled.values())
        # Alphabetical tie-break
        mode = min(l for l in pooled if pooled[l] == max_count)
        mode_freq = pooled[mode] / total
        soft = {}
        for pos in C.PHASE2A_POSITIONS:
            col = [letter_at(s, pos) for _, s in valid]
            col = [l for l in col if l is not None]
            soft[pos] = col.count(mode) / len(col) if col else None
        rows.append({"model": model_label, "config": m.reasoning_config_label,
                     "pooled_mode_letter": mode,
                     "pooled_mode_frequency": round(mode_freq, 4),
                     "n_pooled_letters": total,
                     "pooled_distribution_top10": dict(pooled.most_common(10)),
                     "baseline_soft_accuracy_by_position":
                         {pos: round(v, 4) if v is not None else None
                          for pos, v in soft.items()}})
    return rows


def _soft(preds, col):
    if not col or not preds: return None
    counts = Counter(col)
    dist = {l: counts[l] / len(col) for l in counts}
    return sum(dist.get(v, 0) for v in preds) / len(preds)


def letter_prediction_accuracy(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        p1 = _p1_valid(outcomes, model_label)
        for pos in C.PHASE2A_POSITIONS:
            col = [letter_at(s, pos) for _, s in p1]
            col = [l for l in col if l is not None]
            preds = _p2a_valid(outcomes, model_label, pos)
            n_att = sum(1 for tid in outcomes
                        if tid.startswith(f"phase2a|{model_label}|") and f"pos{pos}|" in tid)
            cats = Counter()
            for tid, o in outcomes.items():
                if tid.startswith(f"phase2a|{model_label}|") and f"pos{pos}|" in tid:
                    cats[o.get("status", "?")] += 1
            soft = _soft(preds, col)
            counts = Counter(col) if col else Counter()
            dist = {l: round(counts[l] / len(col), 4) for l in counts} if col else {}
            mode_letter = min(counts, key=lambda l: (-counts[l], l)) if counts else None
            mode_freq = (counts[mode_letter] / len(col)) if (counts and len(col)) else None
            indep = sum((counts[l] / len(col)) ** 2 for l in counts) if (counts and len(col)) else None
            rows.append({
                "model": model_label, "config": m.reasoning_config_label, "position": pos,
                "n_phase1_valid": len(col),
                "n_phase2a_valid": len(preds),
                "n_phase2a_total_attempted": n_att,
                "phase2a_category_counts": {k: cats.get(k, 0)
                                              for k in ("ok","decline","prefix_leak","invalid","truncated","abandoned")},
                "phase1_position_distribution": dist,
                "uniform_reference": round(1/26, 4),
                "soft_accuracy": None if soft is None else round(soft, 4),
                "positional_mode_letter": mode_letter,
                "positional_mode_frequency": round(mode_freq, 4) if mode_freq is not None else None,
                "independent_sample_agreement": round(indep, 4) if indep is not None else None,
                "phase2a_predictions": preds,
                "phase2a_modal_prediction": (
                    Counter(preds).most_common(1)[0][0] if preds else None),
            })
    return rows


# ---------------------------------------------------------------- reenactment --

def animal_reenactment_scores(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        p1 = _p1_valid(outcomes, model_label)
        p2b = _p2b_valid(outcomes, model_label)
        if not p1 or not p2b:
            rows.append({"model": model_label, "config": m.reasoning_config_label,
                         "n_phase1_valid": len(p1), "n_phase2b_valid": len(p2b),
                         "mean_positional_agreement_by_pos": None,
                         "exact_name_match_any_phase1": None,
                         "pairwise_exact_match_rate": None,
                         "unique_reenacted_names": len({n for n, _ in p2b}),
                         "phase2b_names": [n for n, _ in p2b]})
            continue
        agree_by_pos = {pos: [] for pos in C.PHASE2A_POSITIONS}
        for _, s2b in p2b:
            for _, s1 in p1:
                for pos in C.PHASE2A_POSITIONS:
                    l2 = letter_at(s2b, pos); l1 = letter_at(s1, pos)
                    if l2 is None or l1 is None: continue
                    agree_by_pos[pos].append(1.0 if l2 == l1 else 0.0)
        p1_names = {n for n, _ in p1}
        exact_any = sum(1 for n, _ in p2b if n in p1_names)
        pairwise_total = len(p2b) * len(p1)
        pairwise_match = sum(1 for n2, _ in p2b for n1, _ in p1 if n2 == n1)
        # Agreement with the modal Phase 1 name
        name_counts = Counter(n for n, _ in p1)
        modal_name = name_counts.most_common(1)[0][0] if name_counts else None
        agree_with_modal = (sum(1 for n, _ in p2b if n == modal_name) / len(p2b)
                              if (modal_name and p2b) else None)
        rows.append({
            "model": model_label, "config": m.reasoning_config_label,
            "n_phase1_valid": len(p1), "n_phase2b_valid": len(p2b),
            "n_phase2b_attempted": sum(1 for tid in outcomes if tid.startswith(f"phase2b|{model_label}|")),
            "phase1_modal_name": modal_name,
            "mean_positional_agreement_by_pos":
                {pos: (round(sum(v) / len(v), 4) if v else None)
                 for pos, v in agree_by_pos.items()},
            "exact_name_match_any_phase1": exact_any,
            "pairwise_exact_match_rate": round(pairwise_match / pairwise_total, 4) if pairwise_total else None,
            "agreement_with_phase1_modal_name": round(agree_with_modal, 4) if agree_with_modal is not None else None,
            "unique_reenacted_names": len({n for n, _ in p2b}),
            "phase2b_names": [n for n, _ in p2b],
        })
    return rows


def dissociation_table(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        p1 = _p1_valid(outcomes, model_label)
        p2b = _p2b_valid(outcomes, model_label)
        for pos in C.PHASE2A_POSITIONS:
            col = [letter_at(s, pos) for _, s in p1]
            col = [l for l in col if l is not None]
            preds = _p2a_valid(outcomes, model_label, pos)
            soft = _soft(preds, col)
            if p2b and p1:
                vals = []
                for _, s2b in p2b:
                    l2 = letter_at(s2b, pos)
                    if l2 is None: continue
                    for _, s1 in p1:
                        l1 = letter_at(s1, pos)
                        if l1 is None: continue
                        vals.append(1.0 if l2 == l1 else 0.0)
                reenact = (sum(vals) / len(vals)) if vals else None
            else:
                reenact = None
            rows.append({
                "model": model_label, "config": m.reasoning_config_label, "position": pos,
                "n_phase1_valid": len(col),
                "n_phase2a_valid": len(preds),
                "n_phase2b_valid": len(p2b),
                "reenactment_positional_agreement_at_pos": None if reenact is None else round(reenact, 4),
                "single_letter_soft_accuracy": None if soft is None else round(soft, 4),
                "dissociation_reenact_minus_single": (
                    None if reenact is None or soft is None
                    else round(reenact - soft, 4)),
            })
    return rows


# ---------------------------------------------------------------- reasoning audit --

def reasoning_candidate_audit(outcomes: Dict[str, Dict], run_dir: str) -> List[Dict]:
    """Walk raw_attempts.jsonl, classify each Phase 2A trial's reasoning."""
    # Per-model Phase 1 modal name
    modal_by_model = {}
    for model_label in C.EXECUTION_ORDER:
        p1 = _p1_valid(outcomes, model_label)
        names = Counter(n for n, _ in p1)
        modal_by_model[model_label] = names.most_common(1)[0][0] if names else None
    path = os.path.join(run_dir, "raw_attempts.jsonl")
    rows = []
    if not os.path.exists(path): return rows
    with open(path) as f:
        for line in f:
            if not line.strip(): continue
            a = json.loads(line)
            if a.get("phase") != "phase2a": continue
            rc = a.get("reasoning_content") or ""
            rc_class = a.get("reasoning_content_classification", "unavailable")
            modal_name = modal_by_model.get(a["model_label"])
            classification, info = classify_reasoning(rc, rc_class, modal_name)
            rows.append({
                "trial_id": a["trial_id"], "phase": a["phase"],
                "model": a["model_label"], "config": a["reasoning_config"],
                "position": a.get("position"),
                "parse_category": a.get("parse_category"),
                "classification": classification,
                "candidates_found": info.get("candidates"),
                "modal_mentioned": info.get("modal_mentioned"),
                "phase1_modal_name": info.get("phase1_modal_name"),
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
                "ok": c.get("ok", 0), "decline": c.get("decline", 0),
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
    stab = animal_name_stability(outcomes)
    base = pooled_letter_baseline(outcomes)
    acc = letter_prediction_accuracy(outcomes)
    reenact = animal_reenactment_scores(outcomes)
    diss = dissociation_table(outcomes)
    rea_audit = reasoning_candidate_audit(outcomes, run_dir)
    cats = response_categories(outcomes)

    _write_csv(os.path.join(run_dir, "animal_name_stability.csv"), stab)
    _write_csv(os.path.join(run_dir, "pooled_letter_baseline.csv"), base)
    _write_csv(os.path.join(run_dir, "letter_prediction_accuracy.csv"), acc)
    _write_csv(os.path.join(run_dir, "animal_reenactment_scores.csv"), reenact)
    _write_csv(os.path.join(run_dir, "generation_anticipation_dissociation.csv"), diss)
    _write_csv(os.path.join(run_dir, "reasoning_candidate_audit.csv"), rea_audit)
    _write_csv(os.path.join(run_dir, "response_categories.csv"), cats)

    p1_rows = [{"trial_id": tid, "model": o["model"], "config": o["reasoning_config"],
                "replicate": o["replicate"],
                "normalized_name": o["parsed_normalized_name"],
                "scoring_string": o["parsed_scoring_string"]}
               for tid, o in outcomes.items()
               if o.get("phase") == "phase1" and o.get("status") == "ok"]
    _write_csv(os.path.join(run_dir, "favorite_animal_phase1.csv"), p1_rows)

    p2a_rows = [{"trial_id": tid, "model": o["model"], "config": o["reasoning_config"],
                 "position": o["position"], "replicate": o["replicate"],
                 "status": o["status"], "letter": o.get("parsed_letter")}
                for tid, o in outcomes.items() if o.get("phase") == "phase2a"]
    _write_csv(os.path.join(run_dir, "favorite_animal_letter_predictions.csv"), p2a_rows)

    p2b_rows = [{"trial_id": tid, "model": o["model"], "config": o["reasoning_config"],
                 "replicate": o["replicate"], "status": o["status"],
                 "normalized_name": o.get("parsed_normalized_name"),
                 "scoring_string": o.get("parsed_scoring_string")}
                for tid, o in outcomes.items() if o.get("phase") == "phase2b"]
    _write_csv(os.path.join(run_dir, "favorite_animal_reenactments.csv"), p2b_rows)

    return {"stability": stab, "baseline": base, "accuracy": acc,
            "reenact": reenact, "dissociation": diss,
            "reasoning_audit": rea_audit, "categories": cats}
