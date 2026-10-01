"""Section 23: FULL_CORPUS_EXPERIMENT_1_REPORT.md and validation_report."""

import csv, json, os
from typing import Dict, List


def _read_csv(path: str) -> List[Dict]:
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_validation_report(out_dir: str, trials, outcomes: Dict,
                            audit: Dict, preflight: Dict, ledger: Dict) -> Dict:
    """Hard validation (section 22)."""
    n_planned = len(trials)
    n_ok = sum(1 for o in outcomes.values() if o["status"] == "ok")
    n_abandoned = sum(1 for o in outcomes.values() if o["status"] == "abandoned")

    report = {
        "specification_version": "FCE1_v1.0",
        "source_integrity": {
            "trajectory_count_audited": audit.get("trajectory_count"),
            "hard_errors": audit.get("hard_errors", []),
            "duplicates_present": bool(audit.get("duplicates", {})),
            "input_hashes": audit.get("input_hashes", {}),
        },
        "collection_completeness": {
            "n_planned": n_planned,
            "n_ok": n_ok,
            "n_abandoned": n_abandoned,
            "ok_eq_planned": n_ok == n_planned,
        },
        "analysis_completeness": {
            "all_csvs_exist": all(os.path.exists(os.path.join(out_dir, p)) for p in (
                "trial_level.csv", "compliance_summary.csv",
                "accuracy_by_judge_target_frame.csv", "named_judge_target_matrix.csv",
                "producer_observer_contrasts.csv", "self_wording_contrasts.csv",
                "observer_role_summary.csv", "target_complementarity.csv",
                "baseline_predictions.csv", "baseline_summary.csv",
                "bootstrap_intervals.csv")),
        },
        "scientific_limitations": {
            "known_source_provider_heterogeneity": True,
            "ten_held_out_triplets_small_sample_bootstrap": True,
        },
        "cost_ledger": ledger,
        "preflight_summary": preflight,
        "overall_complete": (n_ok == n_planned
                             and not audit.get("hard_errors")),
    }
    with open(os.path.join(out_dir, "validation_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    # Also a human-readable .md
    lines = ["# Validation report — FCE1", "",
             f"- specification_version: `{report['specification_version']}`",
             f"- overall_complete: **{report['overall_complete']}**",
             "", "## Source integrity"]
    for k, v in report["source_integrity"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Collection completeness")
    for k, v in report["collection_completeness"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Analysis completeness")
    for k, v in report["analysis_completeness"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Cost ledger")
    for k, v in ledger.items():
        lines.append(f"- {k}: {v}")
    with open(os.path.join(out_dir, "validation_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return report


def write_final_report(out_dir: str, trials, outcomes: Dict, validation: Dict):
    """FULL_CORPUS_EXPERIMENT_1_REPORT.md — see section 23 required order."""
    read = lambda p: _read_csv(os.path.join(out_dir, p))

    poc = read("producer_observer_contrasts.csv")
    matrix = read("named_judge_target_matrix.csv")
    boot = read("bootstrap_intervals.csv")
    baseline = read("baseline_summary.csv")
    compl = read("compliance_summary.csv")
    role = read("observer_role_summary.csv")

    lines = []
    lines.append("# Full Corpus Experiment 1 — Producer-vs-Observer Identification")
    lines.append("")
    lines.append(f"Specification: `FCE1_v1.0`")
    lines.append(f"Experiment status: **{'COMPLETE' if validation['overall_complete'] else 'INCOMPLETE'}**")
    lines.append("")

    lines.append("## 1. Integrity and actual counts")
    lines.append("")
    lines.append(f"- planned trials: {validation['collection_completeness']['n_planned']}")
    lines.append(f"- ok trials: {validation['collection_completeness']['n_ok']}")
    lines.append(f"- abandoned: {validation['collection_completeness']['n_abandoned']}")
    lines.append(f"- source integrity hard errors: {len(validation['source_integrity']['hard_errors'])}")
    lines.append(f"- duplicates present: {validation['source_integrity']['duplicates_present']}")
    lines.append("")

    def _pick(rows, **kw):
        for r in rows:
            if all(str(r.get(k)) == str(v) for k, v in kw.items()):
                return r
        return None

    lines.append("## 2. Primary holdout results (per-target contrasts)")
    lines.append("")
    lines.append("| target | n_items | SELF | NAMED | OBS | S | O | F |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for target in ("astra", "fable", "mimo"):
        r = _pick(poc, split="holdout", target=target)
        if r:
            lines.append(f"| {target} | {r['n_items']} | {r['SELF']} | {r['NAMED']} | {r['OBS']} | "
                         f"{r['S']} | {r['O']} | {r['F']} |")
    lines.append("")
    # equal-weight average S across targets (holdout)
    S_vals = [float(r["S"]) for r in poc if r["split"] == "holdout" and r["S"] not in (None, "", "None")]
    if S_vals:
        avg_S = sum(S_vals) / len(S_vals)
        lines.append(f"**Primary summary (equal-weight mean S across targets, holdout): {avg_S:+.3f}**")
    lines.append("")

    lines.append("## 3. S / O / F decomposition — holdout bootstrap 95% intervals")
    lines.append("")
    lines.append("| target | stat | mean | 95% CI (triplet bootstrap) |")
    lines.append("|---|---|---:|---|")
    for target in ("astra", "fable", "mimo"):
        for stat in ("S", "O", "F"):
            r = _pick(boot, split="holdout", target=target, stat=stat)
            if r:
                lines.append(f"| {target} | {stat} | {r['mean']} | [{r['ci_lo']}, {r['ci_hi']}] |")
    lines.append("")

    lines.append("## 4. NAMED judge x target accuracy matrix")
    lines.append("")
    lines.append("### Holdout")
    lines.append("| judge | astra | fable | mimo |")
    lines.append("|---|---:|---:|---:|")
    for judge in ("astra", "fable", "mimo"):
        cells = []
        for target in ("astra", "fable", "mimo"):
            r = _pick(matrix, split="holdout", judge=judge, target=target)
            cells.append(f"{r['accuracy']}" if r else "—")
        lines.append(f"| {judge} | " + " | ".join(cells) + " |")
    lines.append("")

    lines.append("## 5. Observer-role accuracy (NAMED, judge != target)")
    lines.append("")
    lines.append("| split | role | n | accuracy |")
    lines.append("|---|---|---:|---:|")
    for r in role:
        lines.append(f"| {r['split']} | {r['role']} | {r['n']} | {r['accuracy']} |")
    lines.append("")

    lines.append("## 6. Statistical baselines (centroid classifier)")
    lines.append("")
    lines.append("| split | baseline | n_scored | n_ties | accuracy |")
    lines.append("|---|---|---:|---:|---:|")
    for r in baseline:
        lines.append(f"| {r['split']} | {r['baseline']} | {r['n_scored']} | {r['n_ties']} | {r['accuracy']} |")
    lines.append("")

    lines.append("## 7. Compliance (first-attempt and eventual)")
    lines.append("")
    lines.append("| judge | wording | n | first-attempt valid | eventually valid | abandoned |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for r in compl:
        lines.append(f"| {r['judge']} | {r['wording']} | {r['n']} | "
                     f"{r['pct_first_attempt_valid']} | {r['pct_valid_eventually']} | {r['n_abandoned']} |")
    lines.append("")

    lines.append("## 8. Limitations and interpretive guardrails")
    lines.append("")
    lines.append("- Fresh instances do not have episodic memory of the original calls; SELF here means model-identity.")
    lines.append("- Only 10 holdout triplets; triplet-bootstrap intervals are exploratory/small-sample.")
    lines.append("- Source trajectories were served by heterogeneous providers (recorded in source_provider_audit.csv).")
    lines.append("- Exceeding the two centroid baselines does not establish that no classifier could do better.")
    lines.append("- A single judge excelling on all targets does not establish self-specific access.")
    lines.append("")
    lines.append("See `producer_observer_contrasts.csv`, `bootstrap_intervals.csv`, "
                 "`baseline_summary.csv`, `compliance_summary.csv`, "
                 "`target_complementarity.csv`, and `named_judge_target_matrix.csv` "
                 "for the raw numbers underlying each table above.")

    with open(os.path.join(out_dir, "FULL_CORPUS_EXPERIMENT_1_REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
