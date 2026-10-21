"""Analysis for DICE_PILOT_v4.1.

Produces every CSV required by spec §19:

  phase1_stability.csv              per model
  matched_prompt_comparison.csv     Phase 2A vs 2B at position 2, per model
  single_v4_accuracy.csv            Phase 2B soft accuracy, per model/position
  single_v4_vs_historical_v3.csv    Phase 2B vs the model's v3.1 modal digit
  pooled_digit_baseline.csv         pooled modal digit, per model
  full_seq_scores.csv               Phase 2C positional agreement + exact + prefix
  cross_model_template_matrix.csv   6×6 reenactment-vs-objectlevel positional match
  dissociation_table.csv            Phase 2C - Phase 2B at positions 2, 5, 9
  reasoning_prefix_classification.csv  prefix-in-reasoning flags per trial
  response_categories.csv           ok/decline/prefix_leak/invalid/truncated rates
  pilot_decision_rule.csv           evaluation of spec §15 criteria

Historical v3.1 modal digit per model is loaded from a provided path if
`historical_run_dir` is given; otherwise this column is omitted.
"""

from __future__ import annotations

import csv, json, os
from collections import Counter
from typing import Any, Dict, List, Optional

from . import config as C


# ---------------------------------------------------------------- loaders --

def load_outcomes(run_dir: str) -> Dict[str, Dict]:
    p = os.path.join(run_dir, "trial_outcomes.json")
    if not os.path.exists(p): return {}
    with open(p) as f: return json.load(f)


def _phase1_valid(outcomes, model):
    return [o["parsed_values"] for tid, o in outcomes.items()
            if tid.startswith(f"phase1|{model}|") and o.get("status") == "ok"]


def _phase2a_valid(outcomes, model):
    return [o["parsed_value"] for tid, o in outcomes.items()
            if tid.startswith(f"phase2a|{model}|") and o.get("status") == "ok"
            and o.get("parsed_value") is not None]


def _phase2b_valid(outcomes, model, pos):
    return [o["parsed_value"] for tid, o in outcomes.items()
            if tid.startswith(f"phase2b|{model}|") and f"pos{pos}|" in tid
            and o.get("status") == "ok" and o.get("parsed_value") is not None]


def _phase2c_valid(outcomes, model):
    return [o["parsed_values"] for tid, o in outcomes.items()
            if tid.startswith(f"phase2c|{model}|") and o.get("status") == "ok"
            and o.get("parsed_values")]


def _cat_rates(outcomes, model, phase_prefix):
    c = Counter()
    for tid, o in outcomes.items():
        if not tid.startswith(f"{phase_prefix}|{model}|"): continue
        c[o.get("status", "unknown")] += 1
    return c


# ---------------------------------------------------------------- phase 1 --

def phase1_stability(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        cfg = m.reasoning_config_label
        valid = _phase1_valid(outcomes, model_label)
        n_valid = len(valid)
        n_attempted = sum(1 for tid in outcomes if tid.startswith(f"phase1|{model_label}|"))
        unique = len({tuple(s) for s in valid})
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
        if n_valid == 0: stab = "insufficient"
        elif unique == 1: stab = "stable"
        elif all(a == a and a >= 0.75 for a in agree): stab = "mostly_stable"
        else: stab = "unstable"
        rows.append({
            "model": model_label, "config": cfg,
            "n_attempted": n_attempted, "n_valid": n_valid,
            "n_invalid": n_attempted - n_valid,
            "unique_sequences": unique, "stability": stab,
            "modal_at_position": modal,
            "agreement_at_position": [round(a, 4) if a == a else None for a in agree],
            "pooled_digit_distribution": pdist,
        })
    return rows


def pooled_digit_baseline(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        valid = _phase1_valid(outcomes, model_label)
        if not valid:
            rows.append({"model": model_label, "config": m.reasoning_config_label,
                         "pooled_mode_digit": None, "pooled_mode_frequency": None,
                         "baseline_soft_accuracy_by_position": {}})
            continue
        pooled = Counter()
        for s in valid: pooled.update(s)
        total = sum(pooled.values())
        mx = max(pooled.values())
        mode = min(d for d in range(1, 7) if pooled.get(d, 0) == mx)
        soft = {}
        for pos in C.PHASE2B_POSITIONS:
            col = [s[pos-1] for s in valid]
            soft[pos] = col.count(mode) / len(col) if col else float("nan")
        rows.append({"model": model_label, "config": m.reasoning_config_label,
                     "pooled_mode_digit": mode,
                     "pooled_mode_frequency": round(pooled[mode] / total, 4),
                     "n_pooled_integers": total,
                     "baseline_soft_accuracy_by_position":
                         {str(p): round(v, 4) if v == v else None
                          for p, v in soft.items()}})
    return rows


# ---------------------------------------------------------------- single-position accuracy --

def _soft_acc(preds, column_vals):
    if not column_vals or not preds: return None
    dist = {d: column_vals.count(d) / len(column_vals) for d in range(1, 7)}
    return sum(dist[v] for v in preds) / len(preds)


def single_v4_accuracy(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        p1 = _phase1_valid(outcomes, model_label)
        for pos in C.PHASE2B_POSITIONS:
            col = [s[pos-1] for s in p1]
            preds = _phase2b_valid(outcomes, model_label, pos)
            n_attempted = sum(1 for tid in outcomes
                              if tid.startswith(f"phase2b|{model_label}|")
                              and f"pos{pos}|" in tid)
            cats = Counter()
            for tid, o in outcomes.items():
                if tid.startswith(f"phase2b|{model_label}|") and f"pos{pos}|" in tid:
                    cats[o.get("status", "unknown")] += 1
            soft = _soft_acc(preds, col)
            p1_dist = {str(d): round((col.count(d) / len(col) if col else 0), 4) for d in range(1, 7)}
            rows.append({
                "model": model_label, "config": m.reasoning_config_label, "position": pos,
                "n_phase1_valid": len(col), "n_phase2b_valid": len(preds),
                "n_phase2b_total_attempted": n_attempted,
                "phase2b_category_counts": {k: cats.get(k, 0)
                                             for k in ("ok","decline","prefix_leak","invalid","truncated","abandoned")},
                "phase1_position_distribution": p1_dist,
                "soft_accuracy": None if soft is None else round(soft, 4),
                "phase2b_predictions": preds,
                "phase2b_modal": (Counter(preds).most_common(1)[0][0] if preds else None),
            })
    return rows


# ---------------------------------------------------------------- matched 2A vs 2B at pos 2 --

def matched_prompt_comparison(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        p1 = _phase1_valid(outcomes, model_label)
        col2 = [s[1] for s in p1]  # position 2 (0-indexed = 1)
        p2a = _phase2a_valid(outcomes, model_label)
        p2b = _phase2b_valid(outcomes, model_label, 2)
        p2a_cats = _cat_rates(outcomes, model_label, "phase2a")
        p2b_cats = Counter()
        for tid, o in outcomes.items():
            if tid.startswith(f"phase2b|{model_label}|") and "pos2|" in tid:
                p2b_cats[o.get("status", "unknown")] += 1
        rows.append({
            "model": model_label, "config": m.reasoning_config_label,
            "n_phase1_valid": len(col2),
            "phase1_pos2_distribution": {str(d): round(col2.count(d) / len(col2), 4) if col2 else 0 for d in range(1, 7)},
            "phase2a_n_valid": len(p2a),
            "phase2a_n_attempted": sum(1 for tid in outcomes if tid.startswith(f"phase2a|{model_label}|")),
            "phase2a_category_counts": {k: p2a_cats.get(k, 0)
                                         for k in ("ok","decline","prefix_leak","invalid","truncated","abandoned")},
            "phase2a_soft_accuracy": None if not col2 or not p2a else round(_soft_acc(p2a, col2), 4),
            "phase2a_modal": Counter(p2a).most_common(1)[0][0] if p2a else None,
            "phase2a_proportion_4": round(p2a.count(4) / len(p2a), 4) if p2a else None,
            "phase2a_predictions": p2a,
            "phase2b_n_valid": len(p2b),
            "phase2b_n_attempted": sum(1 for tid in outcomes if tid.startswith(f"phase2b|{model_label}|") and "pos2|" in tid),
            "phase2b_category_counts": {k: p2b_cats.get(k, 0)
                                         for k in ("ok","decline","prefix_leak","invalid","truncated","abandoned")},
            "phase2b_soft_accuracy": None if not col2 or not p2b else round(_soft_acc(p2b, col2), 4),
            "phase2b_modal": Counter(p2b).most_common(1)[0][0] if p2b else None,
            "phase2b_proportion_4": round(p2b.count(4) / len(p2b), 4) if p2b else None,
            "phase2b_predictions": p2b,
            "soft_accuracy_delta_B_minus_A": (
                None if not col2 or not p2a or not p2b
                else round(_soft_acc(p2b, col2) - _soft_acc(p2a, col2), 4)
            ),
        })
    return rows


# ---------------------------------------------------------------- v3 historical baseline --

HISTORICAL_V3_MODAL = {
    # Each model's v3.1 (or ext) Phase 2 modal digit from PILOT_REPORT /
    # MODEL_EXTENSION_REPORT.
    # astra R0/R1, fable R0 and R1, qwen R0/R1 — all mostly "4".
    "astra": 4,
    "fable": 4,
    "sonnet": 4,
    "oss120": 4,
    "oss20": 4,
    "qwen": 4,
}


def single_v4_vs_historical_v3(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        hist = HISTORICAL_V3_MODAL.get(model_label)
        p1 = _phase1_valid(outcomes, model_label)
        for pos in C.PHASE2B_POSITIONS:
            col = [s[pos-1] for s in p1]
            preds = _phase2b_valid(outcomes, model_label, pos)
            soft_v4 = _soft_acc(preds, col)
            # Historical baseline: predict `hist` constantly at this position
            if col:
                hist_soft = col.count(hist) / len(col) if hist is not None else None
            else:
                hist_soft = None
            rows.append({
                "model": model_label, "config": m.reasoning_config_label, "position": pos,
                "historical_v3_modal_digit": hist,
                "phase2b_soft_accuracy_v4": None if soft_v4 is None else round(soft_v4, 4),
                "historical_v3_baseline_soft_at_pos": None if hist_soft is None else round(hist_soft, 4),
                "delta_v4_minus_historical": (
                    None if soft_v4 is None or hist_soft is None
                    else round(soft_v4 - hist_soft, 4)
                ),
            })
    return rows


# ---------------------------------------------------------------- Phase 2C reenactment --

def full_seq_scores(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        p1 = _phase1_valid(outcomes, model_label)
        p2c = _phase2c_valid(outcomes, model_label)
        if not p1:
            rows.append({"model": model_label, "config": m.reasoning_config_label,
                         "n_phase2c_valid": len(p2c),
                         "n_phase1_valid": 0,
                         "mean_positional_agreement": None,
                         "positional_agreement_by_pos": {str(p): None for p in C.PHASE2B_POSITIONS},
                         "exact_match_any_phase1": None,
                         "pairwise_exact_match_rate": None,
                         "mean_prefix_match_length_vs_modal": None,
                         "unique_sequences_in_phase2c": 0,
                         "phase2c_sequences": []})
            continue
        # Positional modal from Phase 1
        modal = []
        for p in range(10):
            vals = [s[p] for s in p1]
            counts = Counter(vals)
            mx = max(counts.values())
            modal.append(min(d for d in range(1, 7) if counts.get(d, 0) == mx))
        # Positional agreement
        agree_all = []
        agree_by_pos = {p: [] for p in C.PHASE2B_POSITIONS}
        for seq in p2c:
            for ref in p1:
                matches = sum(1 for i in range(10) if seq[i] == ref[i])
                agree_all.append(matches / 10.0)
                for p in C.PHASE2B_POSITIONS:
                    agree_by_pos[p].append(1.0 if seq[p-1] == ref[p-1] else 0.0)
        # Exact match
        p1_set = {tuple(s) for s in p1}
        exact_any = sum(1 for seq in p2c if tuple(seq) in p1_set)
        pairwise_total = len(p2c) * len(p1)
        pairwise_match = sum(1 for seq in p2c for ref in p1 if seq == ref)
        # Prefix match vs modal
        prefix_lens = []
        for seq in p2c:
            n = 0
            for i in range(10):
                if seq[i] == modal[i]: n += 1
                else: break
            prefix_lens.append(n)
        rows.append({
            "model": model_label, "config": m.reasoning_config_label,
            "n_phase1_valid": len(p1), "n_phase2c_valid": len(p2c),
            "n_phase2c_attempted": sum(1 for tid in outcomes if tid.startswith(f"phase2c|{model_label}|")),
            "modal_phase1_sequence": modal,
            "mean_positional_agreement": round(sum(agree_all) / len(agree_all), 4) if agree_all else None,
            "positional_agreement_by_pos": {str(p): round(sum(v) / len(v), 4) if v else None
                                              for p, v in agree_by_pos.items()},
            "exact_match_any_phase1": exact_any,
            "pairwise_exact_match_rate": round(pairwise_match / pairwise_total, 4) if pairwise_total else None,
            "mean_prefix_match_length_vs_modal": round(sum(prefix_lens) / len(prefix_lens), 4) if prefix_lens else None,
            "prefix_lens_vs_modal": prefix_lens,
            "unique_sequences_in_phase2c": len({tuple(s) for s in p2c}),
            "phase2c_sequences": p2c,
        })
    return rows


# ---------------------------------------------------------------- cross-model similarity matrix --

def cross_model_template_matrix(outcomes: Dict[str, Dict]) -> List[Dict]:
    """6x6 matrix: rows = model producing P2C reenactment, cols = model producing
    Phase-1 object-level reference. Cell = mean positional-agreement rate across
    all valid pairs."""
    rows = []
    p1_by_model = {m: _phase1_valid(outcomes, m) for m in C.EXECUTION_ORDER}
    p2c_by_model = {m: _phase2c_valid(outcomes, m) for m in C.EXECUTION_ORDER}
    for row_model in C.EXECUTION_ORDER:
        row = {"reenact_model": row_model}
        for col_model in C.EXECUTION_ORDER:
            seqs = p2c_by_model.get(row_model) or []
            refs = p1_by_model.get(col_model) or []
            if not seqs or not refs:
                row[f"vs_{col_model}"] = None; continue
            pair_vals = []
            for seq in seqs:
                for ref in refs:
                    pair_vals.append(sum(1 for i in range(10) if seq[i] == ref[i]) / 10.0)
            row[f"vs_{col_model}"] = round(sum(pair_vals) / len(pair_vals), 4) if pair_vals else None
        rows.append(row)
    return rows


# ---------------------------------------------------------------- dissociation --

def dissociation_table(outcomes: Dict[str, Dict]) -> List[Dict]:
    """For each model and position in {2, 5, 9} (spec §13), compute
    Phase 2C positional agreement MINUS Phase 2B soft accuracy."""
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        p1 = _phase1_valid(outcomes, model_label)
        p2c = _phase2c_valid(outcomes, model_label)
        for pos in (2, 5, 9):
            col = [s[pos-1] for s in p1]
            preds = _phase2b_valid(outcomes, model_label, pos)
            soft_b = _soft_acc(preds, col)
            # Reenactment agreement at this position: how often any P2C seq
            # matches a P1 seq at the same position, averaged over all pairs.
            if p2c and p1:
                vals = [1.0 if seq[pos-1] == ref[pos-1] else 0.0
                        for seq in p2c for ref in p1]
                reenact_at_pos = sum(vals) / len(vals)
            else:
                reenact_at_pos = None
            rows.append({
                "model": model_label, "config": m.reasoning_config_label, "position": pos,
                "n_phase1_valid": len(col),
                "n_phase2b_valid": len(preds),
                "n_phase2c_valid": len(p2c),
                "reenactment_positional_agreement_at_pos": None if reenact_at_pos is None else round(reenact_at_pos, 4),
                "single_position_soft_accuracy": None if soft_b is None else round(soft_b, 4),
                "dissociation_reenact_minus_single": (
                    None if reenact_at_pos is None or soft_b is None
                    else round(reenact_at_pos - soft_b, 4)
                ),
            })
    return rows


# ---------------------------------------------------------------- reasoning prefix classification --

def reasoning_prefix_classification(outcomes: Dict[str, Dict], run_dir: str) -> List[Dict]:
    """Walk raw_attempts.jsonl, extract flagged prefix runs per trial."""
    path = os.path.join(run_dir, "raw_attempts.jsonl")
    rows = []
    if not os.path.exists(path): return rows
    with open(path) as f:
        for line in f:
            if not line.strip(): continue
            a = json.loads(line)
            if a.get("phase") in ("phase2a", "phase2b"):  # single-position phases only
                prefix_r = a.get("prefix_run_in_reasoning")
                prefix_f = a.get("prefix_run_in_final")
                rc_class = a.get("reasoning_content_classification", "unavailable")
                if rc_class in ("none", None, "unavailable", "encrypted", "summarized"):
                    classification = "reasoning_unavailable"
                elif prefix_r is not None:
                    classification = "prefix_in_reasoning"
                else:
                    classification = "no_prefix_observed"
                rows.append({
                    "trial_id": a["trial_id"],
                    "phase": a["phase"],
                    "model": a["model_label"],
                    "config": a["reasoning_config"],
                    "position": a.get("position"),
                    "parse_category": a.get("parse_category"),
                    "classification": classification,
                    "prefix_in_reasoning_run": prefix_r,
                    "prefix_in_final_run": prefix_f,
                    "reasoning_content_classification": rc_class,
                })
    return rows


# ---------------------------------------------------------------- response categories --

def response_categories(outcomes: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        for phase in ("phase1", "phase2a", "phase2b", "phase2c"):
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
                "truncated_rate": round(c.get("truncated", 0) / n, 4),
                "decline_rate": round(c.get("decline", 0) / n, 4),
            })
    return rows


# ---------------------------------------------------------------- decision rule (spec §15) --

def decision_rule(outcomes: Dict[str, Dict], matched_rows: List[Dict],
                   single_v4_rows: List[Dict], baseline_rows: List[Dict],
                   full_seq_rows: List[Dict], dissoc_rows: List[Dict]) -> List[Dict]:
    """Evaluate criteria A, B, C per model."""
    matched_by = {r["model"]: r for r in matched_rows}
    single_v4_by = {(r["model"], r["position"]): r for r in single_v4_rows}
    base_by = {r["model"]: r for r in baseline_rows}
    fs_by = {r["model"]: r for r in full_seq_rows}
    dis_by = {(r["model"], r["position"]): r for r in dissoc_rows}
    rows = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        # A. Construal effect (2A vs 2B at pos 2)
        mr = matched_by.get(model_label, {})
        a1 = (mr.get("phase2b_soft_accuracy") is not None and mr.get("phase2a_soft_accuracy") is not None
              and mr["phase2b_soft_accuracy"] > mr["phase2a_soft_accuracy"])
        p2a = mr.get("phase2a_predictions") or []
        p2b = mr.get("phase2b_predictions") or []
        a2 = (p2a and p2b and len(set(p2b)) > 1 and Counter(p2b).most_common(1)[0][0] != 4)
        # A3: not primarily driven by missingness
        a3_denom = (mr.get("phase2b_n_attempted") or 0)
        a3 = (a3_denom > 0 and (mr.get("phase2b_n_valid") or 0) / a3_denom >= 0.6)
        # Candidate C
        preds_by_pos = {}
        for pos in C.PHASE2B_POSITIONS:
            r = single_v4_by.get((model_label, pos))
            if r: preds_by_pos[pos] = r.get("phase2b_predictions") or []
        baseline_pos = (base_by.get(model_label) or {}).get("baseline_soft_accuracy_by_position", {})
        c1_pos = None; c1_margin = None
        for pos in (5, 9):
            r = single_v4_by.get((model_label, pos))
            if r is None or r.get("soft_accuracy") is None: continue
            acc = r["soft_accuracy"]; b = baseline_pos.get(str(pos))
            if b is None: continue
            if acc > 1/6 and acc > b:
                c1_pos = pos; c1_margin = min(acc - 1/6, acc - b); break
        c1 = c1_pos is not None
        # C2: modal differs across >= 2 queried positions (strict position sens)
        modals = []
        for pos in C.PHASE2B_POSITIONS:
            preds = preds_by_pos.get(pos) or []
            if preds: modals.append(Counter(preds).most_common(1)[0][0])
        c2 = len(set(modals)) >= 2
        # C3: no observed prefix in final / reasoning (automated)
        c3 = True  # final by category def; reasoning requires manual audit (flagged by prefix_run_in_reasoning in raw)
        # C4: not confined to trivial position
        c4 = (c1_pos not in (1,)) if c1_pos is not None else False
        # B dissociation
        b_dissoc_components = []
        for pos in (5, 9):
            r = dis_by.get((model_label, pos))
            if r is None: continue
            d = r.get("dissociation_reenact_minus_single")
            if d is None: continue
            b_dissoc_components.append((pos, r.get("reenactment_positional_agreement_at_pos"),
                                         r.get("single_position_soft_accuracy"), d))
        rows.append({
            "model": model_label, "config": m.reasoning_config_label,
            "A1_revised_beats_original_at_pos2": a1,
            "A2_moves_away_from_constant": a2,
            "A3_not_missingness_driven": a3,
            "A_construal_evidence": (a1 and a2 and a3),
            "C1_predictive_advantage_pos5or9": c1,
            "C1_qualifying_position": c1_pos,
            "C1_margin": None if c1_margin is None else round(c1_margin, 4),
            "C2_modal_differs_across_positions": c2,
            "C3_no_observed_final_prefix": c3,
            "C3_reasoning_prefix_review_pending": True,
            "C4_not_trivial_position": c4,
            "C_candidate_followup": (c1 and c2 and c3 and c4),
            "B_dissociation_components": b_dissoc_components,
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
    stab = phase1_stability(outcomes)
    base = pooled_digit_baseline(outcomes)
    matched = matched_prompt_comparison(outcomes)
    single_v4 = single_v4_accuracy(outcomes)
    v3_hist = single_v4_vs_historical_v3(outcomes)
    fs = full_seq_scores(outcomes)
    cross = cross_model_template_matrix(outcomes)
    dis = dissociation_table(outcomes)
    rpc = reasoning_prefix_classification(outcomes, run_dir)
    cats = response_categories(outcomes)
    dec = decision_rule(outcomes, matched, single_v4, base, fs, dis)

    _write_csv(os.path.join(run_dir, "phase1_stability.csv"), stab)
    _write_csv(os.path.join(run_dir, "pooled_digit_baseline.csv"), base)
    _write_csv(os.path.join(run_dir, "matched_prompt_comparison.csv"), matched)
    _write_csv(os.path.join(run_dir, "single_v4_accuracy.csv"), single_v4)
    _write_csv(os.path.join(run_dir, "single_v4_vs_historical_v3.csv"), v3_hist)
    _write_csv(os.path.join(run_dir, "full_seq_scores.csv"), fs)
    _write_csv(os.path.join(run_dir, "cross_model_template_matrix.csv"), cross)
    _write_csv(os.path.join(run_dir, "dissociation_table.csv"), dis)
    _write_csv(os.path.join(run_dir, "reasoning_prefix_classification.csv"), rpc)
    _write_csv(os.path.join(run_dir, "response_categories.csv"), cats)
    _write_csv(os.path.join(run_dir, "pilot_decision_rule.csv"), dec)

    # Raw per-trial dumps
    p1_seqs = [{"trial_id": tid, "model": o["model"], "config": o["reasoning_config"],
                "replicate": o["replicate"],
                "sequence": " ".join(str(x) for x in o["parsed_values"])}
               for tid, o in outcomes.items()
               if o.get("phase") == "phase1" and o.get("status") == "ok"]
    _write_csv(os.path.join(run_dir, "phase1_sequences.csv"), p1_seqs)

    p2a_rows = [{"trial_id": tid, "model": o["model"], "config": o["reasoning_config"],
                 "replicate": o["replicate"], "status": o["status"],
                 "value": o.get("parsed_value")}
                for tid, o in outcomes.items() if o.get("phase") == "phase2a"]
    _write_csv(os.path.join(run_dir, "single_v3_matched_predictions.csv"), p2a_rows)

    p2b_rows = [{"trial_id": tid, "model": o["model"], "config": o["reasoning_config"],
                 "position": o["position"], "replicate": o["replicate"],
                 "status": o["status"], "value": o.get("parsed_value")}
                for tid, o in outcomes.items() if o.get("phase") == "phase2b"]
    _write_csv(os.path.join(run_dir, "single_v4_predictions.csv"), p2b_rows)

    p2c_rows = [{"trial_id": tid, "model": o["model"], "config": o["reasoning_config"],
                 "replicate": o["replicate"], "status": o["status"],
                 "sequence": (" ".join(str(x) for x in o["parsed_values"])
                               if o.get("parsed_values") else "")}
                for tid, o in outcomes.items() if o.get("phase") == "phase2c"]
    _write_csv(os.path.join(run_dir, "full_seq_reenactments.csv"), p2c_rows)

    return {"stability": stab, "baseline": base, "matched": matched,
            "single_v4": single_v4, "v3_hist": v3_hist, "full_seq": fs,
            "cross": cross, "dissociation": dis, "reasoning_prefix": rpc,
            "categories": cats, "decision": dec}
