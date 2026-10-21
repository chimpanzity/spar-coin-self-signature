"""Finalize the pilot 5 report after backfill.

Main orchestrator's phase_analysis_and_report crashed on a prop_T KeyError.
After fixing that and backfilling mimo/history_conditioned to 20 valid, this
script builds the val dict from the trajectory files on disk (including the
backfilled ones with replicate indices 20-26), reruns validation manually,
and emits the analysis outputs.
"""

import argparse, glob, json, os
from collections import Counter

from . import config as C
from .api import CostAccountant, make_client, load_prior_spend_from_jsonl
from .state import RunPaths, read_json
from .orchestrator_stimulus_corpus import (
    _corpus_paths, phase_analysis_and_report, _write_complete)


def build_val_from_disk(paths: RunPaths) -> dict:
    corpus = _corpus_paths(paths)
    traj_dir = corpus["trajectory_dir"]
    cell_counts = Counter()
    trajectories = []
    invalid = []
    for fn in sorted(os.listdir(traj_dir)):
        if not (fn.startswith("trajectory-") and fn.endswith(".json")):
            continue
        r = read_json(os.path.join(traj_dir, fn))
        if not r:
            invalid.append((fn, "unreadable")); continue
        trajectories.append(r)
        if r.get("status") == "ok" and len(r.get("parsed_sequence", "")) == C.CORPUS_SEQUENCE_LENGTH:
            cell_counts[(r["model_label"], r["method"])] += 1
        else:
            invalid.append((r.get("trajectory_id", fn),
                            f"status={r.get('status')} len={len(r.get('parsed_sequence',''))}"))
    cell_ok = all(cell_counts[(m, meth)] >= C.CORPUS_TRAJECTORIES_PER_CELL
                  for m in C.CORPUS_MODEL_LABELS
                  for meth in C.CORPUS_GENERATION_METHODS)
    return {
        "n_records": len(trajectories),
        "cell_counts": {f"{m}/{meth}": cell_counts.get((m, meth), 0)
                        for m in C.CORPUS_MODEL_LABELS
                        for meth in C.CORPUS_GENERATION_METHODS},
        "cell_counts_ok": cell_ok,
        "cell_counts_min_required": C.CORPUS_TRAJECTORIES_PER_CELL,
        "invalid_trajectories": invalid,
        "run_complete_ok": cell_ok,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--data-root", default="data/spar_dynamic")
    args = ap.parse_args()

    paths = RunPaths(args.data_root, args.run_id); paths.ensure()
    corpus = _corpus_paths(paths)

    client = make_client()
    accountant = CostAccountant(client)
    accountant.bootstrap_from_disk(corpus["raw_attempts_jsonl"])
    preflight_raw = os.path.join(paths.root, "preflight", "raw_attempts.jsonl")
    if os.path.exists(preflight_raw):
        accountant.bootstrap_from_disk(preflight_raw)

    def log(msg):
        print(f"[finalize] {msg}", flush=True)

    log(f"bootstrap spend = ${accountant.spent_usd:.4f}")
    val = build_val_from_disk(paths)
    log(f"validation: cells_ok={val['cell_counts_ok']} n_records={val['n_records']}")
    for k, v in val["cell_counts"].items():
        log(f"  {k}: {v}")

    # Overwrite the stale validation_report.json left over from the main run
    # (that one was written before the mimo/history_conditioned backfill).
    val_report_path = os.path.join(corpus["results_dir"], "validation_report.json")
    with open(val_report_path, "w", encoding="utf-8") as f:
        json.dump(val, f, indent=2)
    log(f"wrote {val_report_path}")

    phase_analysis_and_report(paths, log, accountant, val, preflight_result=None)
    report_path = os.path.join(corpus["results_dir"],
                                "THREE_ARCHITECTURE_SOURCE_REPORT.md")
    if val["run_complete_ok"]:
        _write_complete(paths, accountant.spent_usd, report_path)
        log(f"WROTE COMPLETE marker")
    log(f"final report: {report_path}")
    log(f"total spend from disk: ${accountant.spent_usd:.4f}")


if __name__ == "__main__":
    main()
