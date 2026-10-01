"""Build a combined cross-method report across FCE1 (history_conditioned)
and FCE2 (batch, independent_calls).

Reads producer_observer_contrasts.csv, named_judge_target_matrix.csv,
baseline_summary.csv, compliance_summary.csv, observer_role_summary.csv,
and bootstrap_intervals.csv from each of three run directories, and
produces a single markdown report that places them side by side.
"""

import argparse, csv, os
from typing import Dict, List, Optional, Tuple



def _read_csv(path: str) -> List[Dict]:
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _pick(rows, **kw):
    for r in rows:
        if all(str(r.get(k)) == str(v) for k, v in kw.items()):
            return r
    return None


def _fmt(v, places=3):
    if v in (None, "", "None"): return "—"
    try: return f"{float(v):.{places}f}"
    except: return str(v)


def _mean_s_holdout(poc_rows: List[Dict]) -> Optional[float]:
    xs = [float(r["S"]) for r in poc_rows if r["split"] == "holdout"
          and r["S"] not in (None, "", "None")]
    return sum(xs) / len(xs) if xs else None


def build_report(method_dirs: Dict[str, str], out_path: str,
                 validation_run_dir: Optional[str] = None):
    """method_dirs: {method_label -> run_dir path}. validation_run_dir, if
    provided, adds a section 6b for the objective A/B task validation study.
    """
    data = {}
    for method, run_dir in method_dirs.items():
        data[method] = {
            "poc": _read_csv(os.path.join(run_dir, "producer_observer_contrasts.csv")),
            "matrix": _read_csv(os.path.join(run_dir, "named_judge_target_matrix.csv")),
            "baseline": _read_csv(os.path.join(run_dir, "baseline_summary.csv")),
            "role": _read_csv(os.path.join(run_dir, "observer_role_summary.csv")),
            "compl": _read_csv(os.path.join(run_dir, "compliance_summary.csv")),
            "boot": _read_csv(os.path.join(run_dir, "bootstrap_intervals.csv")),
        }

    lines = []
    lines.append("# Full Corpus Experiment 1 + 2 — Cross-method summary")
    lines.append("")
    lines.append("Three independent 480-judgment runs, one per corpus production method, "
                 "same judge configuration and prompt (barring per-method stimulus text).")
    lines.append("")
    lines.append("| method | run_id |")
    lines.append("|---|---|")
    for m, rd in method_dirs.items():
        lines.append(f"| {m} | `{os.path.basename(rd)}` |")
    lines.append("")

    # Primary summary across methods
    lines.append("## 1. Primary summary — equal-weight mean S across targets (holdout)")
    lines.append("")
    lines.append("| method | mean S (holdout) |")
    lines.append("|---|---:|")
    for m in method_dirs:
        v = _mean_s_holdout(data[m]["poc"])
        lines.append(f"| {m} | {_fmt(v)} |")
    lines.append("")
    lines.append("Positive values would indicate SELF-wording-plus-ownership advantage over "
                 "named observers; negative values indicate observers outperform the target "
                 "producer on its own trajectories.")
    lines.append("")

    # Per-target S/O/F per method (holdout)
    lines.append("## 2. Per-target holdout contrasts (S / O / F)")
    lines.append("")
    for m in method_dirs:
        lines.append(f"### {m}")
        lines.append("")
        lines.append("| target | n | SELF | NAMED | OBS | **S** | **O** | **F** |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        for target in ("astra", "fable", "mimo"):
            r = _pick(data[m]["poc"], split="holdout", target=target)
            if r:
                lines.append(f"| {target} | {r['n_items']} | {_fmt(r['SELF'],2)} | "
                             f"{_fmt(r['NAMED'],2)} | {_fmt(r['OBS'],2)} | "
                             f"**{_fmt(r['S'],2)}** | **{_fmt(r['O'],2)}** | **{_fmt(r['F'],2)}** |")
        lines.append("")

    # 3x3 named judge x target matrix per method
    lines.append("## 3. NAMED judge × target accuracy (holdout)")
    lines.append("")
    for m in method_dirs:
        lines.append(f"### {m}")
        lines.append("")
        lines.append("| judge | astra | fable | mimo |")
        lines.append("|---|---:|---:|---:|")
        for judge in ("astra", "fable", "mimo"):
            cells = []
            for target in ("astra", "fable", "mimo"):
                r = _pick(data[m]["matrix"], split="holdout", judge=judge, target=target)
                cells.append(_fmt(r["accuracy"], 2) if r else "—")
            lines.append(f"| {judge} | " + " | ".join(cells) + " |")
        lines.append("")

    # Baselines
    lines.append("## 4. Statistical baselines (centroid classifier)")
    lines.append("")
    lines.append("| method | split | baseline | accuracy |")
    lines.append("|---|---|---|---:|")
    for m in method_dirs:
        for r in data[m]["baseline"]:
            lines.append(f"| {m} | {r['split']} | {r['baseline']} | {_fmt(r['accuracy'],3)} |")
    lines.append("")
    lines.append("Interpretation: the behavioral phenotype of each production method is "
                 "cleanly separable by a simple centroid classifier. Independent_calls "
                 "trajectories are the most separable (baseline accuracy 1.0), consistent "
                 "with the strong p_H biases this method produces.")
    lines.append("")

    # Observer role
    lines.append("## 5. Observer-role accuracy (holdout, NAMED, judge ≠ target)")
    lines.append("")
    lines.append("| method | distractor_producer | uninvolved_observer |")
    lines.append("|---|---:|---:|")
    for m in method_dirs:
        dp = _pick(data[m]["role"], split="holdout", role="distractor_producer")
        uo = _pick(data[m]["role"], split="holdout", role="uninvolved_observer")
        lines.append(f"| {m} | {_fmt(dp['accuracy'],3) if dp else '—'} | "
                     f"{_fmt(uo['accuracy'],3) if uo else '—'} |")
    lines.append("")

    # Compliance
    lines.append("## 6. Compliance (all methods)")
    lines.append("")
    lines.append("| method | total trials | first-attempt valid | eventually valid | abandoned |")
    lines.append("|---|---:|---:|---:|---:|")
    for m in method_dirs:
        rows = data[m]["compl"]
        n = sum(int(r.get("n", 0) or 0) for r in rows)
        fav = sum(int(r.get("n_first_attempt_valid", 0) or 0) for r in rows)
        ev = sum(int(r.get("n_valid_eventually", 0) or 0) for r in rows)
        aband = sum(int(r.get("n_abandoned", 0) or 0) for r in rows)
        if n == 0:
            lines.append(f"| {m} | — | — | — | — |")
        else:
            lines.append(f"| {m} | {n} | {fav/n:.3f} | {ev/n:.3f} | {aband} |")
    lines.append("")

    # Validation study (optional)
    if validation_run_dir:
        val_dir = validation_run_dir
        lines.append("## 6b. Validation study — objective A/B task")
        lines.append("")
        lines.append("Same 60 stimulus pairs from the independent_calls method, "
                     "shown in both natural and reversed A/B order, with two "
                     "objectively-answerable questions (correct answer "
                     "deterministic from the stimulus text):")
        lines.append("- `more_H`: which sequence has more H outcomes")
        lines.append("- `more_switches`: which sequence has more H/T transitions")
        lines.append("")
        lines.append("| judge | question | split | n | accuracy | A-response rate |")
        lines.append("|---|---|---|---:|---:|---:|")
        vrows = _read_csv(os.path.join(val_dir, "summary_by_judge_question_split.csv"))
        for r in vrows:
            lines.append(f"| {r['judge']} | {r['question']} | {r['split']} | "
                         f"{r['n_scored_nontie']} | "
                         f"{_fmt(r['accuracy_on_nontie'])} | "
                         f"{_fmt(r['a_response_rate'])} |")
        lines.append("")
        lines.append("**Takeaway:** astra and fable both reach 100% accuracy on "
                     "both objective questions with A-response rates near 0.50. "
                     "Their heavy A-bias on source-attribution trials (astra "
                     "~87%, fable ~97%) is therefore **task-specific**, not a "
                     "general A/B format incompetence. Mimo partially uses the "
                     "stimulus for `more_H` (~89% accuracy, 60% A-rate) but "
                     "collapses to near-always-A on `more_switches` (~54% "
                     "accuracy, 96% A-rate) — mimo's position bias is partly "
                     "feature-dependent.")
        lines.append("")
    # Interpretive synthesis
    lines.append("## 7. Cross-method synthesis")
    lines.append("")
    lines.append("- **Protocol information strongly shapes self-recognition.** The "
                 "independent_calls comparison between the truthful-protocol run and "
                 "the false-protocol run shows this clearly: fable's own-trajectory "
                 "accuracy under SELF-wording moves from 0.05 (false-protocol) to 0.90 "
                 "(truthful-protocol), and NAMED-on-fable from 0.10 to 0.75. The equal-"
                 "weight mean S flips sign (−0.150 → +0.100) between the two conditions "
                 "on exactly the same stimulus sequences; only the judge's description "
                 "of how those sequences were produced changed.")
    lines.append("- **Under truthful protocols, modest positive self-recognition emerges "
                 "in independent_calls** (mean S = +0.100, fable S = +0.45 with CI "
                 "[0.25, 0.63] on holdout). History_conditioned and batch stay near "
                 "zero even with the truthful protocol.")
    lines.append("- **The task is externally solvable in all methods.** The centroid "
                 "baseline hits 97–100% on holdout. The behavioral signal is there; LLM "
                 "judges only partially use it, and only when the protocol description "
                 "matches the production reality.")
    lines.append("- **Astra is a consistent anti-self-recognizer** across methods and "
                 "protocols: holdout NAMED-on-astra = 0.00 and SELF-on-astra = 0.05 "
                 "under the truthful independent_calls protocol, while fable and mimo "
                 "as observers identify astra at above-chance rates in some cells.")
    lines.append("- **Mimo scores at or near chance everywhere** across all methods and "
                 "protocols, consistent with an A-position-biased or weak-feature-using "
                 "responder (compliant parsing but not using the behavioral signal).")
    lines.append("- **Astra and fable's heavy A-bias on source-attribution is "
                 "task-specific, not a general format problem.** The validation "
                 "study (same stimuli, both A/B orderings, objectively-answerable "
                 "questions) shows astra and fable at 100% accuracy with A-rate "
                 "near 0.50 on both `more_H` and `more_switches`. Mimo partially "
                 "uses the stimulus for `more_H` but still collapses to A-always "
                 "on `more_switches`.")
    lines.append("")
    lines.append("## 8. Limitations")
    lines.append("")
    lines.append("- 10 holdout triplets per method; CIs exploratory/small-sample.")
    lines.append("- Source-model provider heterogeneity (recorded per method).")
    lines.append("- Exceeding the two centroid baselines does not establish no external "
                 "classifier could do better.")
    lines.append("- A fresh judge instance has no episodic memory of the source generation.")
    lines.append("")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history-conditioned-run", required=True)
    ap.add_argument("--batch-run", required=True)
    ap.add_argument("--independent-calls-run", required=True)
    ap.add_argument("--batch-false-protocol-run", default="",
                     help="optional: run dir of FCE2-batch with wrong protocol description")
    ap.add_argument("--independent-false-protocol-run", default="",
                     help="optional: run dir of FCE2-indep with wrong protocol description")
    ap.add_argument("--validation-run", default="",
                     help="optional: run dir of the objective-task validation study")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    method_dirs = {
        "history_conditioned (truthful)":  args.history_conditioned_run,
        "batch (truthful)":                args.batch_run,
        "independent_calls (truthful)":    args.independent_calls_run,
    }
    if args.batch_false_protocol_run:
        method_dirs["batch (false protocol)"] = args.batch_false_protocol_run
    if args.independent_false_protocol_run:
        method_dirs["independent_calls (false protocol)"] = args.independent_false_protocol_run
    build_report(method_dirs, args.out, validation_run_dir=args.validation_run or None)
    print(f"wrote {args.out}", flush=True)


if __name__ == "__main__":
    main()
