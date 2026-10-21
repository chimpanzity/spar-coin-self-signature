"""Orchestrator for Pilot 5 — SPAR Stimulus Corpus.

Runs three generation methods (batch, history_conditioned, independent_calls)
across three models (astra, fable, mistral), 10 trajectories per cell,
100 flips per trajectory. Produces a reusable stimulus bank for later
self-recognition and PACA-comparison studies.

Resume-safe: per-attempt records go to raw_attempts.jsonl; completed
trajectories persist as trajectory-<id>.json. On restart, in-progress
trajectories are reconstructed from raw_attempts.jsonl and picked up mid-way.

Cost is derived from raw_attempts.jsonl on startup so resumes never lose
accumulated spend (fix for prior in-memory-only accounting).
"""

import argparse, csv, json, os, random, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from . import config as C
from .api import (CostAccountant, make_client, BudgetExceeded)
from .analyze import (sequence_features, corpus_cell_summary,
                      corpus_classification, corpus_representative_trajectories,
                      corpus_prefix_metrics, FEATURE_NAMES)
from .state import RunPaths, read_json, read_jsonl, write_json, append_jsonl
from .stimulus_corpus import (CorpusTrajectory,
                                generate_batch_trajectory,
                                generate_history_conditioned_trajectory,
                                generate_independent_calls_trajectory,
                                third_model_preflight,
                                rebuild_trajectory_state_from_attempts)


def _now_stamp():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _log_writer(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8", buffering=1)
    def w(msg):
        line = f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {msg}"
        print(line, flush=True); f.write(line + "\n"); f.flush()
    return w, f


# ---------------------------------------------------------------------------
# Directory conventions
# ---------------------------------------------------------------------------

def _corpus_paths(paths: RunPaths) -> Dict[str, str]:
    """Return the corpus-specific paths under a run root."""
    return {
        "raw_attempts_jsonl": os.path.join(paths.root, "raw_attempts.jsonl"),
        "trajectory_dir":     os.path.join(paths.root, "trajectories"),
        "results_dir":        paths.results,
        "figures_dir":        os.path.join(paths.results, "figures"),
        "execution_manifest": os.path.join(paths.root, "execution_manifest.csv"),
        "trajectory_manifest_json": os.path.join(paths.root, "trajectory_manifest.json"),
    }


def _trajectory_path(paths: RunPaths, trajectory_id: str) -> str:
    corpus = _corpus_paths(paths)
    return os.path.join(corpus["trajectory_dir"], f"trajectory-{trajectory_id}.json")


# ---------------------------------------------------------------------------
# Execution schedule construction (deterministic randomized)
# ---------------------------------------------------------------------------

def build_execution_schedule(seed: int = C.CORPUS_EXECUTION_SEED) -> List[Dict[str, Any]]:
    """Deterministic randomized (model, method, replicate) schedule.
    Each trajectory itself runs sequentially; the schedule only permutes
    across trajectories."""
    schedule = []
    for m in C.CORPUS_MODELS:
        for method in C.CORPUS_GENERATION_METHODS:
            for k in range(C.CORPUS_TRAJECTORIES_PER_CELL):
                traj_id = f"{m.label}_{method}_{k:02d}"
                schedule.append({
                    "trajectory_id": traj_id,
                    "model_label": m.label,
                    "model_slug": m.slug,
                    "method": method,
                    "replicate_index": k,
                })
    rng = random.Random(seed)
    rng.shuffle(schedule)
    for i, s in enumerate(schedule):
        s["execution_order"] = i
    return schedule


# ---------------------------------------------------------------------------
# Phase: mistral compliance preflight
# ---------------------------------------------------------------------------

def phase_third_model_preflight(client, accountant, paths: RunPaths, log) -> Dict:
    corpus = _corpus_paths(paths)
    third_label = next(m.label for m in C.CORPUS_MODELS
                        if m.label not in ("astra", "fable"))
    log(f"PHASE: {third_label} compliance preflight (23 calls)")
    preflight_dir = os.path.join(paths.root, "preflight")
    os.makedirs(preflight_dir, exist_ok=True)
    preflight_jsonl = os.path.join(preflight_dir, "raw_attempts.jsonl")
    res = third_model_preflight(client, accountant, preflight_jsonl,
                                log=log, model_label=third_label)
    write_json(os.path.join(preflight_dir, "preflight_summary.json"), res)
    return res


# ---------------------------------------------------------------------------
# Phase: source generation
# ---------------------------------------------------------------------------

def phase_source_generation(client, accountant, paths: RunPaths,
                            schedule: List[Dict], log):
    corpus = _corpus_paths(paths)
    os.makedirs(corpus["trajectory_dir"], exist_ok=True)

    # split into batch first (fast), then step-based methods (which can concurrently
    # run trajectories but stay sequential within each)
    batch_tasks = [s for s in schedule if s["method"] == "batch"]
    step_tasks = [s for s in schedule if s["method"] != "batch"]

    # write execution manifest before starting
    with open(corpus["execution_manifest"], "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(schedule[0].keys()))
        w.writeheader()
        for s in schedule:
            w.writerow(s)

    def _done(traj_id: str) -> bool:
        p = _trajectory_path(paths, traj_id)
        if not os.path.exists(p):
            return False
        r = read_json(p)
        return bool(r and r.get("status") == "ok" and len(r.get("parsed_sequence", "")) == C.CORPUS_SEQUENCE_LENGTH)

    def _run_one(sched_entry):
        traj_id = sched_entry["trajectory_id"]
        if _done(traj_id):
            return None
        model = C.CORPUS_MODEL_BY_LABEL[sched_entry["model_label"]]
        method = sched_entry["method"]
        k = sched_entry["replicate_index"]
        raw_path = corpus["raw_attempts_jsonl"]

        if method == "batch":
            rec = generate_batch_trajectory(
                client, accountant,
                run_id=paths.run_id, trajectory_id=traj_id,
                model=model, replicate_index=k,
                raw_jsonl_path=raw_path, log=log)
        elif method == "history_conditioned":
            resume_seq = rebuild_trajectory_state_from_attempts(raw_path, traj_id)
            if resume_seq:
                log(f"  {traj_id}: resuming history_conditioned from step {len(resume_seq)+1}")
            rec = generate_history_conditioned_trajectory(
                client, accountant,
                run_id=paths.run_id, trajectory_id=traj_id,
                model=model, replicate_index=k,
                raw_jsonl_path=raw_path,
                resume_history=resume_seq, log=log)
        elif method == "independent_calls":
            resume_seq = rebuild_trajectory_state_from_attempts(raw_path, traj_id)
            if resume_seq:
                log(f"  {traj_id}: resuming independent_calls from step {len(resume_seq)+1}")
            rec = generate_independent_calls_trajectory(
                client, accountant,
                run_id=paths.run_id, trajectory_id=traj_id,
                model=model, replicate_index=k,
                raw_jsonl_path=raw_path,
                resume_history=resume_seq, log=log)
        else:
            raise ValueError(f"unknown method: {method}")

        write_json(_trajectory_path(paths, traj_id), asdict(rec))
        log(f"  finished {traj_id}: status={rec.status} n_calls={rec.n_calls} "
            f"cost=${rec.total_cost_usd:.4f} spent=${accountant.spent_usd:.4f}")
        return rec

    # BATCH: run sequentially (very fast; keeps costs cleanly attributed)
    log(f"PHASE: batch trajectories ({len(batch_tasks)} planned)")
    for s in batch_tasks:
        _run_one(s)

    # STEP-BASED: concurrent across trajectories, sequential within each
    log(f"PHASE: step-based trajectories ({len(step_tasks)} planned) "
        f"concurrency={C.CORPUS_SOURCE_CONCURRENCY}")
    with ThreadPoolExecutor(max_workers=C.CORPUS_SOURCE_CONCURRENCY) as pool:
        futures = {pool.submit(_run_one, s): s["trajectory_id"] for s in step_tasks}
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as e:
                log(f"  trajectory failed with exception: {e}")


# ---------------------------------------------------------------------------
# Validation (spec section 31)
# ---------------------------------------------------------------------------

def phase_validate(paths: RunPaths, schedule: List[Dict], log) -> Dict:
    corpus = _corpus_paths(paths)
    n_planned = len(schedule)
    trajectories = []
    from collections import Counter
    cell_counts: Counter = Counter()
    invalid = []
    for s in schedule:
        p = _trajectory_path(paths, s["trajectory_id"])
        if not os.path.exists(p):
            invalid.append((s["trajectory_id"], "missing_file"))
            continue
        r = read_json(p)
        if r is None:
            invalid.append((s["trajectory_id"], "unreadable")); continue
        trajectories.append(r)
        if r.get("status") == "ok" and len(r.get("parsed_sequence", "")) == C.CORPUS_SEQUENCE_LENGTH:
            cell_counts[(r["model_label"], r["method"])] += 1
        else:
            invalid.append((s["trajectory_id"], f"status={r.get('status')} len={len(r.get('parsed_sequence',''))}"))

    cell_ok = all(cell_counts[(m, meth)] == C.CORPUS_TRAJECTORIES_PER_CELL
                  for m in C.CORPUS_MODEL_LABELS
                  for meth in C.CORPUS_GENERATION_METHODS)
    for m in C.CORPUS_MODEL_LABELS:
        for meth in C.CORPUS_GENERATION_METHODS:
            n = cell_counts.get((m, meth), 0)
            if n != C.CORPUS_TRAJECTORIES_PER_CELL:
                log(f"  cell short: {m}/{meth} = {n}")

    # Integrity: for history_conditioned, every step's history_before must equal prior parsed flips.
    # (Runs only on aggregated attempt log for efficiency.)
    history_ok = True
    history_check_failures = []
    raw = corpus["raw_attempts_jsonl"]
    if os.path.exists(raw):
        # collect per-trajectory ordered attempts
        by_traj: Dict[str, List[Dict]] = {}
        with open(raw, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try: rec = json.loads(line)
                except: continue
                if rec.get("method") == "history_conditioned":
                    by_traj.setdefault(rec["trajectory_id"], []).append(rec)
                elif rec.get("method") == "independent_calls":
                    # spec 32: history_before must be empty/null
                    hb = rec.get("history_before")
                    if hb not in (None, ""):
                        history_ok = False
                        history_check_failures.append(
                            f"{rec['trajectory_id']} indep step {rec.get('trial_index')} "
                            f"had non-empty history_before")
        for traj_id, attempts in by_traj.items():
            # sort attempts, walk step by step, verify history_before at each step
            attempts.sort(key=lambda x: (x.get("trial_index") or 0, x.get("attempt_index") or 0))
            valid_flips_by_step: Dict[int, str] = {}
            for a in attempts:
                if a.get("valid"):
                    step = a.get("trial_index")
                    if isinstance(step, int) and step not in valid_flips_by_step:
                        valid_flips_by_step[step] = a["parsed_flip"]
            # rebuild the accumulated history at every step and compare against the logged history_before
            accum = ""
            step = 1
            while step in valid_flips_by_step:
                # find the attempt at this step and compare
                attempts_at_step = [a for a in attempts if a.get("trial_index") == step]
                for a in attempts_at_step:
                    expected = accum
                    got = a.get("history_before") or ""
                    if expected != got:
                        history_ok = False
                        history_check_failures.append(
                            f"{traj_id} step {step} attempt {a.get('attempt_index')}: "
                            f"expected history_before len={len(expected)}, got len={len(got)}")
                        break
                accum += valid_flips_by_step[step]
                step += 1

    ok = (not invalid) and cell_ok and history_ok
    result = {
        "n_planned": n_planned,
        "n_records": len(trajectories),
        "n_valid_cell_counted": sum(cell_counts.values()),
        "cell_counts": {f"{m}/{meth}": cell_counts.get((m, meth), 0)
                        for m in C.CORPUS_MODEL_LABELS for meth in C.CORPUS_GENERATION_METHODS},
        "cell_counts_ok": cell_ok,
        "invalid_trajectories": invalid,
        "history_integrity_ok": history_ok,
        "history_integrity_failures": history_check_failures[:20],
        "run_complete_ok": ok,
    }
    write_json(os.path.join(corpus["results_dir"], "validation_report.json"), result)
    return result


# ---------------------------------------------------------------------------
# Analysis + reports
# ---------------------------------------------------------------------------

def _write_csv(path, rows, fieldnames=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8") as f: f.write("")
        return
    if fieldnames is None:
        keys = []; seen = set()
        for r in rows:
            for k in r.keys():
                if k not in seen: keys.append(k); seen.add(k)
        fieldnames = keys
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows: w.writerow({k: r.get(k, "") for k in fieldnames})


def phase_analysis_and_report(paths: RunPaths, log, accountant, val: Dict,
                              preflight_result: Optional[Dict]):
    corpus = _corpus_paths(paths)
    # Load all trajectories
    trajectories = []
    for fn in sorted(os.listdir(corpus["trajectory_dir"])):
        if fn.startswith("trajectory-") and fn.endswith(".json"):
            r = read_json(os.path.join(corpus["trajectory_dir"], fn))
            if r: trajectories.append(r)

    # 1. source_trajectories.csv — one row per completed trajectory with derived metrics
    src_rows = []
    for t in trajectories:
        if not t.get("valid"):
            src_rows.append({
                "run_id": t["run_id"], "trajectory_id": t["trajectory_id"],
                "model": t["model_label"], "model_id": t["requested_model_id"],
                "method": t["method"], "replicate": t["replicate_index"],
                "sequence_length": len(t.get("parsed_sequence", "")),
                "sequence": t.get("parsed_sequence", ""),
                "status": t["status"],
            })
            continue
        f = sequence_features(t["parsed_sequence"])
        src_rows.append({
            "run_id": t["run_id"], "trajectory_id": t["trajectory_id"],
            "model": t["model_label"], "model_id": t["requested_model_id"],
            "method": t["method"], "replicate": t["replicate_index"],
            "sequence_length": len(t["parsed_sequence"]),
            "sequence": t["parsed_sequence"],
            "n_H": t["parsed_sequence"].count("H"),
            "n_T": t["parsed_sequence"].count("T"),
            "p_H": f["prop_H"], "p_T": 1.0 - f["prop_H"],
            "n_runs": f["longest_run"],   # placeholder replaced below
            "runs_z": f["runs_Z"],
            "switch_count": int(round(f["switch_rate"] * (len(t["parsed_sequence"]) - 1))),
            "switch_rate": f["switch_rate"],
            "longest_run": f["longest_run"],
            "HH": f["HH"], "HT": f["HT"], "TH": f["TH"], "TT": f["TT"],
            "status": t["status"],
        })
    _write_csv(os.path.join(corpus["results_dir"], "source_trajectories.csv"), src_rows)

    # 2. prefix_metrics.csv — features at 20, 50, 100
    prefix_rows = []
    for t in trajectories:
        if not t.get("valid"): continue
        for row in corpus_prefix_metrics(t["parsed_sequence"]):
            prefix_rows.append({
                "trajectory_id": t["trajectory_id"], "model": t["model_label"],
                "method": t["method"], **row})
    _write_csv(os.path.join(corpus["results_dir"], "prefix_metrics.csv"), prefix_rows)

    # 3. cell_summary.csv
    cell_rows = corpus_cell_summary(trajectories)
    _write_csv(os.path.join(corpus["results_dir"], "cell_summary.csv"), cell_rows)

    # 4. classification_results.csv
    clf_rows = corpus_classification(trajectories)
    _write_csv(os.path.join(corpus["results_dir"], "classification_results.csv"), clf_rows)

    # 5. representative_trajectories.csv
    rep_rows = corpus_representative_trajectories(trajectories)
    _write_csv(os.path.join(corpus["results_dir"], "representative_trajectories.csv"), rep_rows)

    # 6. cost_summary.csv — derived from disk (raw_attempts.jsonl)
    from .api import load_prior_spend_from_jsonl
    total_from_disk, by_kind, calls_by_kind = load_prior_spend_from_jsonl(
        corpus["raw_attempts_jsonl"])
    cost_rows = [{"kind": k, "calls": calls_by_kind.get(k, 0),
                  "cost_usd": v} for k, v in sorted(by_kind.items())]
    cost_rows.append({"kind": "TOTAL", "calls": sum(calls_by_kind.values()),
                      "cost_usd": total_from_disk})
    _write_csv(os.path.join(corpus["results_dir"], "cost_summary.csv"), cost_rows)

    # 7. THREE_ARCHITECTURE_SOURCE_REPORT.md
    _write_report(paths, corpus, accountant, val, preflight_result,
                  trajectories, cell_rows, clf_rows, rep_rows,
                  total_from_disk, by_kind, calls_by_kind)


def _write_report(paths, corpus, accountant, val, preflight,
                  trajectories, cell_rows, clf_rows, rep_rows,
                  total_from_disk, by_kind, calls_by_kind):
    p = os.path.join(corpus["results_dir"], "THREE_ARCHITECTURE_SOURCE_REPORT.md")
    lines = []
    lines.append("# SPAR Stimulus Corpus — Three Production Architectures")
    lines.append("")
    lines.append(f"Run root: `{paths.root}`")
    lines.append(f"Experiment tag: `{C.STIMULUS_CORPUS_TAG}`")
    lines.append(f"Total spend (from persisted raw attempts): **${total_from_disk:.4f}** / ${C.STIMULUS_CORPUS_BUDGET_USD:.2f} cap")
    lines.append("")
    lines.append("## Canonical dataset")
    lines.append("")
    lines.append("The canonical stimulus bank is `corpus/trajectories.csv` (180 rows, one row")
    lines.append("per valid trajectory). `source_trajectories.csv` in this directory is the")
    lines.append("raw analysis-side view and retains 187 rows including 7 abandoned")
    lines.append("mimo/history_conditioned trajectories (the backfill re-ran under fresh")
    lines.append("replicate indices and succeeded). Use `corpus/` for any downstream work;")
    lines.append("this file is the study writeup.")
    lines.append("")
    lines.append("## 1. Scientific question")
    lines.append("")
    lines.append("For the same nominal task (\"simulate a sequence of fair coin flips\"),")
    lines.append("how does the architecture of sequence production alter the behavioral")
    lines.append(f"phenotype of {' / '.join(C.CORPUS_MODEL_LABELS)}?")
    lines.append("")
    lines.append("Three architectures compared:")
    lines.append("- **batch**: one API call generates all 100 flips via within-completion autoregression")
    lines.append("- **history_conditioned**: 100 sequential API calls; each receives the complete prior history")
    lines.append("- **independent_calls**: 100 sequential API calls; every call receives an identical fixed prompt, no history")
    lines.append("")

    lines.append("## 2. Run integrity")
    lines.append("")
    for k, v in val.items():
        if isinstance(v, list) and len(v) > 5:
            v = f"{len(v)} entries (first 5 shown): {v[:5]}"
        lines.append(f"- {k}: {v}")
    lines.append("")
    if preflight:
        lines.append("### Third-model preflight (spec section 14)")
        summary = preflight.get("summary", {})
        lines.append(f"- step_accuracy: {summary.get('step_accuracy', float('nan')):.3f}")
        lines.append(f"- batch_valid: {summary.get('batch_valid', 0)}/{summary.get('batch_total', 3)}")
        lines.append(f"- passes_threshold: {summary.get('passes_threshold', False)}")
        lines.append("")

    lines.append("## 3. Behavioral phenotypes (per model x method, mean +/- SD over trajectories)")
    lines.append("")
    lines.append("### At prefix length 100 (full trajectory)")
    lines.append("")
    lines.append("| model | method | n | mean p_H | mean switch | mean runs_Z | mean longest_run | mean HT | mean TH |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for row in cell_rows:
        if row.get("prefix_length") != 100: continue
        lines.append(f"| {row['model']} | {row['method']} | {row['n_trajectories']} | "
                     f"{row['mean_prop_H']:.3f} | {row['mean_switch_rate']:.3f} | "
                     f"{row['mean_runs_Z']:+.2f} | {row['mean_longest_run']:.1f} | "
                     f"{row['mean_HT']:.3f} | {row['mean_TH']:.3f} |")
    lines.append("")

    lines.append("## 4. Architecture comparison — per model, per prefix length")
    lines.append("")
    lines.append("| model | method | prefix | mean p_H | mean switch | mean runs_Z | mean longest_run |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in cell_rows:
        lines.append(f"| {row['model']} | {row['method']} | {row['prefix_length']} | "
                     f"{row['mean_prop_H']:.3f} | {row['mean_switch_rate']:.3f} | "
                     f"{row['mean_runs_Z']:+.2f} | {row['mean_longest_run']:.1f} |")
    lines.append("")

    lines.append("## 5. Source-model identifiability (LOO nearest centroid, per method x prefix)")
    lines.append("")
    lines.append("Chance = 1/3 = 0.333")
    lines.append("")
    lines.append("| method | prefix | n | accuracy | vs chance |")
    lines.append("|---|---|---|---|---|")
    for row in clf_rows:
        acc = row.get("accuracy", float("nan"))
        if acc == acc:  # not nan
            lines.append(f"| {row['method']} | {row['prefix_length']} | {row['n']} | "
                         f"{acc:.3f} | {acc - 1/3:+.3f} |")
        else:
            lines.append(f"| {row['method']} | {row['prefix_length']} | - | n/a | - |")
    lines.append("")

    lines.append("## 6. Representative trajectories (closest to standardized cell centroid)")
    lines.append("")
    lines.append("| model | method | p_H | switch | runs_Z | longest_run | sequence |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in rep_rows:
        lines.append(f"| {row['model']} | {row['method']} | {row['prop_H']:.2f} | "
                     f"{row['switch_rate']:.2f} | {row['runs_Z']:+.2f} | {row['longest_run']:.0f} | "
                     f"`{row['sequence']}` |")
    lines.append("")

    lines.append("## 7. Temporal emergence — classification accuracy vs prefix length")
    lines.append("")
    # simple text table of accuracy across prefix lengths per method
    from collections import defaultdict
    by_method = defaultdict(dict)
    for row in clf_rows:
        by_method[row["method"]][row["prefix_length"]] = row.get("accuracy", float("nan"))
    lines.append("| method | acc @ 20 | acc @ 50 | acc @ 100 |")
    lines.append("|---|---|---|---|")
    for method in C.CORPUS_GENERATION_METHODS:
        v = by_method.get(method, {})
        lines.append(f"| {method} | {v.get(20, float('nan')):.3f} | "
                     f"{v.get(50, float('nan')):.3f} | {v.get(100, float('nan')):.3f} |")
    lines.append("")

    lines.append("## 8. Relation to prior 50-flip pilot")
    lines.append("")
    lines.append("The previous 50-flip source pilot compared batch vs history_conditioned only")
    lines.append("and found substantially stronger source-model identifiability under")
    lines.append("history_conditioned generation (0.933 online vs 0.700 batch). The current")
    lines.append("100-flip corpus adds an independent_calls control and Mimo in place of Qwen.")
    lines.append("The independent_calls vs batch comparison indexes the effect of crossing")
    lines.append("fresh inference boundaries WITHOUT explicit accumulated history; the")
    lines.append("independent_calls vs history_conditioned comparison indexes the additional")
    lines.append("effect of explicit history conditioning.")
    lines.append("")

    lines.append("## 9. Implications for self-recognition studies (no judgments here)")
    lines.append("")
    lines.append("This corpus is stimulus-only. Judgments belong to a later study. The")
    lines.append("architecture-effect results above can inform which cells look most")
    lines.append("informative to include as stimuli in a follow-up recognition experiment.")
    lines.append("")

    lines.append("## 10. Relevance to PACA baseline")
    lines.append("")
    lines.append("Each trajectory is 100 binary outcomes — the same length as a PACA / Proteus")
    lines.append("matching-pennies session. Later work can compare these context-free coin")
    lines.append("phenotypes against 100-trial PACA choice streams from the same models,")
    lines.append("bearing in mind that PACA adds an adaptive opponent, outcomes, and game history.")
    lines.append("")

    lines.append("## 11. Limitations")
    lines.append("")
    lines.append(f"- Only {C.CORPUS_TRAJECTORIES_PER_CELL} trajectories per (model, method) cell "
                 f"({C.CORPUS_DEV_PER_CELL} development + {C.CORPUS_HOLDOUT_PER_CELL} evaluation); "
                 "feature-classifier estimates are noisy.")
    lines.append("- Model/API dependence: OpenRouter serving of the exact same model_id may vary over time.")
    lines.append("- Call architecture may alter hidden serving behavior beyond what we can observe.")
    lines.append("- Prefix analyses reflect prefixes of a 100-flip generation, NOT separately requested lengths.")
    lines.append("- Coin simulation is not equivalent to strategic play.")
    lines.append("")

    lines.append("## Spend breakdown (derived from raw_attempts.jsonl)")
    lines.append("")
    lines.append("| kind | calls | cost |")
    lines.append("|---|---|---|")
    for k in sorted(by_kind.keys()):
        lines.append(f"| {k} | {calls_by_kind.get(k, 0)} | ${by_kind[k]:.4f} |")
    lines.append(f"| **TOTAL** | {sum(calls_by_kind.values())} | **${total_from_disk:.4f}** |")

    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# STOP / COMPLETE markers
# ---------------------------------------------------------------------------

def _write_stop(paths, phase, reason, spent):
    with open(os.path.join(paths.root, "OVERNIGHT_RUN_STOPPED.md"), "w") as f:
        f.write(f"# Overnight run stopped\n\n- run_id: {paths.run_id}\n- phase: {phase}\n"
                f"- spend_so_far_usd: ${spent:.4f}\n- reason: {reason}\n"
                f"- resume: rerun with --run-id {paths.run_id} --skip-preflight (idempotent)\n")


def _write_complete(paths, spent, report_path):
    with open(os.path.join(paths.root, "OVERNIGHT_RUN_COMPLETE.md"), "w") as f:
        f.write(f"# Overnight run complete\n\n- run_id: {paths.run_id}\n"
                f"- total_spend_usd: ${spent:.4f}\n- completed_utc: {_now_stamp()}\n"
                f"- final_report: {report_path}\n")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", required=True)
    ap.add_argument("--yes", action="store_true", required=True)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--data-root", default="data/spar_dynamic")
    ap.add_argument("--skip-preflight", action="store_true")
    args = ap.parse_args()

    run_id = args.run_id or ("spar-stimulus-corpus-" + _now_stamp())
    paths = RunPaths(args.data_root, run_id); paths.ensure()
    corpus = _corpus_paths(paths)
    os.makedirs(corpus["trajectory_dir"], exist_ok=True)
    log, log_file = _log_writer(os.path.join(paths.logs, "orchestrator_stimulus_corpus.log"))
    log(f"START run_id={run_id}")

    try:
        client = make_client()
        accountant = CostAccountant(client)
        # Bootstrap prior spend from disk (resume-safe accounting)
        accountant.bootstrap_from_disk(corpus["raw_attempts_jsonl"])
        # Preflight raw jsonl also contributes
        preflight_raw = os.path.join(paths.root, "preflight", "raw_attempts.jsonl")
        if os.path.exists(preflight_raw):
            accountant.bootstrap_from_disk(preflight_raw)
        log(f"  bootstrap spend from disk = ${accountant.spent_usd:.4f}")

        catalog = accountant.snapshot_catalog()
        missing = [m.slug for m in C.CORPUS_MODELS if m.slug not in catalog]
        if missing:
            log(f"ABORT: missing model(s): {missing}")
            _write_stop(paths, "model_missing", f"missing: {missing}", accountant.spent_usd)
            return
        write_json(paths.catalog, catalog)

        preflight_result = None
        if not args.skip_preflight:
            preflight_result = phase_third_model_preflight(client, accountant, paths, log)
            if not preflight_result["summary"]["passes_threshold"]:
                log(f"ABORT: {preflight_result['model']} preflight failed")
                _write_stop(paths, "third_model_preflight_failed",
                            json.dumps(preflight_result["summary"]),
                            accountant.spent_usd)
                return

        # write manifest
        write_json(paths.manifest, {"run_id": run_id,
                                    "experiment_tag": C.STIMULUS_CORPUS_TAG,
                                    "started_utc": _now_stamp(),
                                    "budget_usd": C.STIMULUS_CORPUS_BUDGET_USD})

        schedule = build_execution_schedule()
        write_json(corpus["trajectory_manifest_json"], schedule)

        phase_source_generation(client, accountant, paths, schedule, log)
        val = phase_validate(paths, schedule, log)
        log(f"  validation: {val}")
        phase_analysis_and_report(paths, log, accountant, val, preflight_result)
        report_path = os.path.join(corpus["results_dir"],
                                     "THREE_ARCHITECTURE_SOURCE_REPORT.md")
        if val["run_complete_ok"]:
            log(f"COMPLETE total_spend=${accountant.spent_usd:.4f}")
            _write_complete(paths, accountant.spent_usd, report_path)
        else:
            log(f"STOP: validation not clean")
            _write_stop(paths, "validation_incomplete",
                        json.dumps({k: v for k, v in val.items()
                                     if k not in ("invalid_trajectories",
                                                   "history_integrity_failures")}),
                        accountant.spent_usd)
    except BudgetExceeded as e:
        log(f"BUDGET STOP: {e}")
        _write_stop(paths, "budget_cap", str(e), accountant.spent_usd)
    except Exception as e:
        import traceback
        log(f"FATAL {type(e).__name__}: {e}\n{traceback.format_exc()}")
        try: spent = accountant.spent_usd
        except: spent = 0.0
        _write_stop(paths, "fatal_exception", f"{type(e).__name__}: {e}", spent)
    finally:
        try: log_file.close()
        except: pass


if __name__ == "__main__":
    main()
