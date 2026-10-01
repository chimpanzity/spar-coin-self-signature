"""Baseline analysis for phenotype-prediction runs.

Given:
- a phenotype-prediction run directory (feature ∈ {p_H, switch_rate})
- the canonical corpus directory

compute:
1. observed per-(model, procedure) feature values from the corpus (and
   sequence-level values for transparency);
2. per-response errors (signed, absolute) joined to each forecast;
3. per-cell summaries: mean predicted, observed, mean signed error,
   mean absolute error (MAE), and MAE of the mean forecast (a different
   quantity — error of the aggregate prediction);
4. self / own-named / observer contrasts, per (target, procedure):
     self_advantage      = observer_MAE − SELF_MAE
     own_model_advantage = observer_MAE − OWN_NAMED_MAE
     SELF_wording_adv    = OWN_NAMED_MAE − SELF_MAE
5. a transparent secondary table using the loose last-line parser on
   first-attempt raw responses, with the extraction rule and preserved
   raw content for the recovered abandoned trials.

Writes under <run_dir>/baseline_<feature>/:
  observed_from_corpus.csv       per (model, procedure) + sequence-level
  trial_errors.csv               per forecast: predicted, actual, errors
  cell_summary.csv               cell MAE / mean prediction / MAE-of-mean
  contrasts.csv                  per (target, procedure) three contrasts
  loose_recovered.csv            responses recovered from abandoned trials
  README.md                      brief methodology
"""

import argparse, csv, hashlib, json, math, os, re, statistics
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------- feature calc

def _p_H(seq: str) -> float:
    n = len(seq)
    return seq.count("H") / n if n else float("nan")


def _switch_rate(seq: str) -> float:
    """Fraction of adjacent pairs where the two outcomes differ. For a 100-
    outcome sequence that is 99 adjacent pairs. Never crosses sequence
    boundaries."""
    n = len(seq)
    if n < 2: return float("nan")
    switches = sum(1 for i in range(1, n) if seq[i] != seq[i-1])
    return switches / (n - 1)


FEATURE_FNS = {"p_H": _p_H, "switch_rate": _switch_rate}


# ---------------------------------------------------------------- corpus load

def load_corpus_sequences(corpus_dir: str) -> List[Dict]:
    rows = []
    path = os.path.join(corpus_dir, "trajectories.csv")
    with open(path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def observed_by_cell(corpus_rows: List[Dict], feature: str
                     ) -> Tuple[Dict[Tuple[str,str], float],
                                 List[Dict]]:
    """Return (mean_by_cell, per_sequence_rows).

    mean_by_cell[(model, procedure)] = unweighted mean over all 20 sequences
    in that cell of the feature. per_sequence_rows preserves the sequence-
    level values for transparency.
    """
    fn = FEATURE_FNS[feature]
    per_seq: List[Dict] = []
    by: Dict[Tuple[str,str], List[float]] = defaultdict(list)
    for r in corpus_rows:
        if r.get("method") not in ("batch","history_conditioned","independent_calls"):
            continue
        model = r["model"]; proc = r["method"]
        val = fn(r["sequence"])
        if val == val:  # not NaN
            per_seq.append({"trajectory_id": r["trajectory_id"],
                             "model": model, "procedure": proc,
                             "feature": feature, "value": round(val, 6)})
            by[(model, proc)].append(val)
    means = {k: (sum(v)/len(v) if v else float("nan")) for k, v in by.items()}
    return means, per_seq


# ---------------------------------------------------------------- parsers

_NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def strict_parse(text: str) -> Optional[float]:
    s = (text or "").strip().rstrip("\n")
    if "\n" in s: return None
    if not _NUMBER_RE.match(s): return None
    try: v = float(s)
    except Exception: return None
    return v if 0.0 <= v <= 1.0 else None


def loose_parse(text: str) -> Optional[float]:
    """Strict first, else try the LAST non-empty line as a bare float in [0,1].
    Documented extraction rule for abandoned-trial recovery."""
    v = strict_parse(text)
    if v is not None: return v
    if not text: return None
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines: return None
    return strict_parse(lines[-1])


# ---------------------------------------------------------------- forecasting

def _load_outcomes(run_dir: str) -> Dict[str, Dict]:
    p = os.path.join(run_dir, "trial_outcomes.json")
    if not os.path.exists(p): return {}
    with open(p, "r", encoding="utf-8") as f: return json.load(f)


def _load_trials(run_dir: str) -> List[Dict]:
    rows = []
    with open(os.path.join(run_dir, "trial_manifest.csv"), "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows


def _load_first_attempt_raw(run_dir: str) -> Dict[str, str]:
    """trial_id -> first-attempt raw_visible_content from raw_attempts.jsonl."""
    raw_path = os.path.join(run_dir, "raw_attempts.jsonl")
    if not os.path.exists(raw_path): return {}
    out: Dict[str, str] = {}
    with open(raw_path, "r", encoding="utf-8") as f:
        for line in f:
            ln = line.strip()
            if not ln: continue
            try: r = json.loads(ln)
            except Exception: continue
            tid = r.get("trial_id"); att = r.get("attempt_number")
            if tid and att == 1 and tid not in out:
                out[tid] = r.get("raw_visible_content") or ""
    return out


# ---------------------------------------------------------------- per-trial errors

def build_trial_errors(trials: List[Dict], outcomes: Dict[str, Dict],
                        first_attempt_raw: Dict[str, str],
                        observed_by_cell_: Dict[Tuple[str,str], float]) -> List[Dict]:
    """One row per manifest trial.

    predicted_strict / predicted_loose / recovered_from_abandoned_only columns
    distinguish primary (strict) and secondary (loose) analyses.
    """
    out: List[Dict] = []
    for t in trials:
        tid = t["trial_id"]
        o = outcomes.get(tid, {})
        status = o.get("status", "pending")
        target = t["target_label"]; proc = t["procedure"]
        obs = observed_by_cell_.get((target, proc))
        pred_strict = None
        pred_loose = None
        recovered = False
        raw = first_attempt_raw.get(tid, "")
        # strict value as stored (predicted_p_H field)
        if status == "ok" and o.get("predicted_p_H") is not None:
            pred_strict = float(o["predicted_p_H"])
            pred_loose = pred_strict
        elif raw:
            lv = loose_parse(raw)
            if lv is not None:
                pred_loose = lv
                recovered = True
        row = {
            "trial_id": tid,
            "feature": t.get("feature", "p_H"),
            "judge_label": t["judge_label"],
            "wording_condition": t["wording_condition"],
            "target_label": target,
            "procedure": proc,
            "replicate": int(t["replicate"]),
            "observed_value": None if obs is None else round(obs, 6),
            "predicted_strict": None if pred_strict is None else round(pred_strict, 6),
            "predicted_loose":  None if pred_loose  is None else round(pred_loose, 6),
            "recovered_from_abandoned_only": int(recovered),
            "signed_error_strict": None if (pred_strict is None or obs is None)
                                     else round(pred_strict - obs, 6),
            "abs_error_strict":    None if (pred_strict is None or obs is None)
                                     else round(abs(pred_strict - obs), 6),
            "signed_error_loose":  None if (pred_loose is None or obs is None)
                                     else round(pred_loose - obs, 6),
            "abs_error_loose":     None if (pred_loose is None or obs is None)
                                     else round(abs(pred_loose - obs), 6),
            "status": status,
            "raw_first_attempt_preview": raw[:200] if recovered else "",
        }
        out.append(row)
    return out


def cell_summary(trial_errors: List[Dict]) -> List[Dict]:
    """Per (judge, wording, target, procedure):
      n_strict, mean_pred_strict, MAE_strict (mean of |errors|),
      MAE_of_mean_strict (|mean(pred) - obs|),
      and the same quantities under loose parsing.
    """
    by: Dict[tuple, List[Dict]] = defaultdict(list)
    for r in trial_errors:
        by[(r["judge_label"], r["wording_condition"], r["target_label"], r["procedure"])].append(r)
    rows = []
    for key, lst in sorted(by.items()):
        judge, wording, target, procedure = key
        # Observed (same for all rows in this cell)
        obs_vals = [r["observed_value"] for r in lst if r["observed_value"] is not None]
        obs = obs_vals[0] if obs_vals else None
        strict_vals = [r["predicted_strict"] for r in lst if r["predicted_strict"] is not None]
        loose_vals  = [r["predicted_loose"]  for r in lst if r["predicted_loose"]  is not None]
        def _stats(vals, obs):
            n = len(vals)
            mean_pred = sum(vals)/n if n else None
            mae = sum(abs(v - obs) for v in vals) / n if (n and obs is not None) else None
            mae_of_mean = (abs(mean_pred - obs) if (mean_pred is not None and obs is not None)
                           else None)
            mean_signed = sum(v - obs for v in vals) / n if (n and obs is not None) else None
            return n, mean_pred, mae, mae_of_mean, mean_signed
        ns, ms, maes, mom_s, signeds = _stats(strict_vals, obs)
        nl, ml, mael, mom_l, signedl = _stats(loose_vals, obs)
        n_attempted = len(lst)
        n_recovered = sum(r["recovered_from_abandoned_only"] for r in lst)
        rows.append({
            "judge": judge, "wording": wording, "target": target,
            "procedure": procedure,
            "n_attempted": n_attempted,
            "n_valid_strict": ns, "n_valid_loose": nl,
            "n_recovered_from_abandoned": n_recovered,
            "observed_value": None if obs is None else round(obs, 6),
            "mean_predicted_strict": None if ms is None else round(ms, 6),
            "mean_predicted_loose":  None if ml is None else round(ml, 6),
            "mean_signed_error_strict": None if signeds is None else round(signeds, 6),
            "mean_signed_error_loose":  None if signedl is None else round(signedl, 6),
            "mae_strict": None if maes is None else round(maes, 6),
            "mae_loose":  None if mael is None else round(mael, 6),
            "mae_of_mean_strict": None if mom_s is None else round(mom_s, 6),
            "mae_of_mean_loose":  None if mom_l is None else round(mom_l, 6),
        })
    return rows


def contrasts(cell_rows: List[Dict], parser_tag: str = "loose") -> List[Dict]:
    """Per (target, procedure), compute the three contrasts under the given parser:
      SELF_MAE: judge=target, wording=SELF
      OWN_NAMED_MAE: judge=target, wording=NAMED
      OBS_MAE: mean MAE of NAMED trials where judge != target
      self_advantage = OBS_MAE - SELF_MAE
      own_model_advantage = OBS_MAE - OWN_NAMED_MAE
      SELF_wording_advantage = OWN_NAMED_MAE - SELF_MAE
    """
    key = f"mae_{parser_tag}"
    out = []
    for target in ("astra","fable","mimo"):
        for procedure in ("batch","history_conditioned","independent_calls"):
            def _mae(judge, wording):
                for r in cell_rows:
                    if (r["judge"] == judge and r["wording"] == wording
                            and r["target"] == target and r["procedure"] == procedure):
                        return r[key]
                return None
            self_mae = _mae(target, "SELF")
            own_named_mae = _mae(target, "NAMED")
            other_judges = [j for j in ("astra","fable","mimo") if j != target]
            obs_maes = [_mae(j, "NAMED") for j in other_judges]
            obs_maes = [v for v in obs_maes if v is not None]
            obs_mae = (sum(obs_maes)/len(obs_maes)) if obs_maes else None
            def _diff(a, b): return None if (a is None or b is None) else round(b - a, 6)
            out.append({
                "parser": parser_tag,
                "target": target, "procedure": procedure,
                "SELF_mae": self_mae, "OWN_NAMED_mae": own_named_mae,
                "OBS_mae": None if obs_mae is None else round(obs_mae, 6),
                "self_advantage":        _diff(self_mae,  obs_mae),
                "own_model_advantage":   _diff(own_named_mae, obs_mae),
                "SELF_wording_advantage": _diff(self_mae,  own_named_mae),
                "n_observer_cells_used": len(obs_maes),
            })
    return out


# ---------------------------------------------------------------- writers

def _write_rows(path: str, rows: List[Dict]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8") as f: f.write("")
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows: w.writerow(r)


def write_readme(out_dir: str, feature: str, run_dir: str, corpus_dir: str,
                 observed_by_cell_: Dict[Tuple[str,str], float],
                 n_trials: int, n_valid_strict: int, n_recovered: int):
    lines = []
    lines.append(f"# Baseline analysis — feature={feature}")
    lines.append("")
    lines.append(f"- Forecast run: `{run_dir}`")
    lines.append(f"- Canonical corpus: `{corpus_dir}`")
    lines.append(f"- Trials attempted: {n_trials}")
    lines.append(f"- Strict-valid: {n_valid_strict}")
    lines.append(f"- Loose-recovered from abandoned trials: {n_recovered}")
    lines.append("")
    lines.append("## Observed feature values (per model × procedure, mean over 20 sequences)")
    lines.append("")
    lines.append("| model | batch | history_conditioned | independent_calls |")
    lines.append("|---|---:|---:|---:|")
    for m in ("astra","fable","mimo"):
        row = [m]
        for p in ("batch","history_conditioned","independent_calls"):
            v = observed_by_cell_.get((m, p))
            row.append(f"{v:.4f}" if v is not None else "—")
        lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |")
    lines.append("")
    lines.append("## Parsers")
    lines.append("")
    lines.append("- **Strict (primary)**: response must be a bare numeric literal in [0,1] "
                 "after whitespace strip. No newlines in the stripped content.")
    lines.append("- **Loose (secondary)**: strict first; if that fails and the response has "
                 "a last non-empty line that is a bare numeric literal in [0,1], use it. "
                 "Applied only to the first-attempt raw response for abandoned trials.")
    lines.append("")
    lines.append("## Contrast definitions (per target × procedure)")
    lines.append("")
    lines.append("- `SELF_mae`: MAE when the judge is the target under SELF wording.")
    lines.append("- `OWN_NAMED_mae`: MAE when the judge is the target under NAMED wording.")
    lines.append("- `OBS_mae`: mean of the two other judges' MAE for this target under NAMED wording.")
    lines.append("- `self_advantage` = OBS_mae − SELF_mae (positive = target better than observers)")
    lines.append("- `own_model_advantage` = OBS_mae − OWN_NAMED_mae")
    lines.append("- `SELF_wording_advantage` = OWN_NAMED_mae − SELF_mae")
    lines.append("")
    lines.append("## Hand checks")
    lines.append("")
    lines.append("- `HHHH`: p(H) = 1.0, switch_rate = 0.0.")
    lines.append("- `HTHT`: p(H) = 0.5, switch_rate = 1.0.")
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------- CLI

def analyze(run_dir: str, corpus_dir: str, feature: str,
            out_dir: Optional[str] = None):
    out_dir = out_dir or os.path.join(run_dir, f"baseline_{feature}")
    os.makedirs(out_dir, exist_ok=True)
    corpus_rows = load_corpus_sequences(corpus_dir)
    means, per_seq = observed_by_cell(corpus_rows, feature)
    _write_rows(os.path.join(out_dir, "observed_per_sequence.csv"), per_seq)
    _write_rows(os.path.join(out_dir, "observed_from_corpus.csv"),
                [{"model": m, "procedure": p, "feature": feature,
                   "mean_over_sequences": round(v, 6)}
                 for (m, p), v in sorted(means.items())])
    trials = _load_trials(run_dir)
    outcomes = _load_outcomes(run_dir)
    first_raw = _load_first_attempt_raw(run_dir)
    te = build_trial_errors(trials, outcomes, first_raw, means)
    _write_rows(os.path.join(out_dir, "trial_errors.csv"), te)
    cs = cell_summary(te)
    _write_rows(os.path.join(out_dir, "cell_summary.csv"), cs)
    cstrict = contrasts(cs, parser_tag="strict")
    cloose  = contrasts(cs, parser_tag="loose")
    _write_rows(os.path.join(out_dir, "contrasts_strict.csv"), cstrict)
    _write_rows(os.path.join(out_dir, "contrasts_loose.csv"), cloose)
    # Loose recovery audit
    recovered = [r for r in te if r["recovered_from_abandoned_only"]]
    _write_rows(os.path.join(out_dir, "loose_recovered.csv"), recovered)
    # README
    n_trials = len(trials)
    n_valid_strict = sum(1 for r in te if r["predicted_strict"] is not None)
    n_recovered = len(recovered)
    write_readme(out_dir, feature, run_dir, corpus_dir, means,
                 n_trials, n_valid_strict, n_recovered)
    return out_dir


def _hand_check():
    """Verifies feature math on hand-checkable sequences."""
    assert _p_H("HHHH") == 1.0, _p_H("HHHH")
    assert _switch_rate("HHHH") == 0.0, _switch_rate("HHHH")
    assert _p_H("HTHT") == 0.5
    assert _switch_rate("HTHT") == 1.0
    assert _p_H("H") == 1.0
    # switch_rate on single-char is NaN; just check it's nan
    sr = _switch_rate("H")
    assert sr != sr, sr


def main():
    _hand_check()
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--corpus-dir",
                    default="data/spar_dynamic/spar-stimulus-corpus-20260930T012044Z/results/corpus")
    ap.add_argument("--feature", default="p_H", choices=("p_H","switch_rate"))
    ap.add_argument("--out-dir", default="")
    args = ap.parse_args()
    out = analyze(args.run_dir, args.corpus_dir, args.feature,
                  args.out_dir or None)
    print(f"wrote baseline analysis under {out}")


if __name__ == "__main__":
    main()
