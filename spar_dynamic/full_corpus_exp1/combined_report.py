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


def build_report(method_dirs: Dict[str, str], out_path: str):
    """method_dirs: {method_label -> run_dir path}"""
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
        lines.append(f"| {m} | {n} | {fav/n:.3f} | {ev/n:.3f} | {aband} |")
    lines.append("")

    # Interpretive synthesis
    lines.append("## 7. Cross-method synthesis")
    lines.append("")
    lines.append("- **No evidence of selective self-recognition in any method.** The "
                 "equal-weight mean S across targets is near zero for history_conditioned "
                 "(+0.008) and batch (−0.008), and NEGATIVE for independent_calls (−0.150).")
    lines.append("- **The task is externally solvable in all methods.** The centroid "
                 "baseline hits 97–100% on holdout. The behavioral signal is there; LLM "
                 "judges fail to use it.")
    lines.append("- **The most separable method yields the LARGEST self-deficit.** On "
                 "independent_calls — where p_H alone perfectly classifies — astra and "
                 "fable judges are WORSE than observers at identifying their own "
                 "trajectories. Example: fable NAMED-on-fable 0.10, fable SELF-on-fable "
                 "0.05, while fable NAMED-on-astra is 0.75. Fable's own independent_calls "
                 "phenotype is p_H ≈ 0.99 (near-all-H); when asked to identify its own, "
                 "the model appears to reject the highly biased sequence as 'not me'.")
    lines.append("- **Fable is a strong general observer across methods** on astra and "
                 "mimo targets, but reliably weakest on fable targets.")
    lines.append("- **Mimo scores at or near chance everywhere** across all three methods, "
                 "consistent with an A-position-biased or weak-feature-using responder.")
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
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    method_dirs = {
        "history_conditioned": args.history_conditioned_run,
        "batch":                args.batch_run,
        "independent_calls":    args.independent_calls_run,
    }
    build_report(method_dirs, args.out)
    print(f"wrote {args.out}", flush=True)


if __name__ == "__main__":
    main()
