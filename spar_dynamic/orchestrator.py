"""End-to-end orchestrator for the SPAR Dynamic Behavioral Self-Signature Pilot.

Run:  python -m spar_dynamic.orchestrator --live --yes [--run-id <id>] [--skip-smoke]

Every phase is idempotent so that re-running the orchestrator after an interruption
picks up from the last completed step rather than duplicating paid work.
"""

import argparse, csv, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from typing import Dict, List, Tuple

from . import config as C
from .api import CostAccountant, make_client, BudgetExceeded
from .source import (generate_batch_source, generate_online_source,
                     generate_online_trajectory, TrajectoryRecord)
from .trials import build_all_trials, Trial
from .judgment import judge_one_trial, preflight_response_mode, JudgmentRecord
from .analyze import (sequence_features, nearest_centroid_loo,
                      summarize_judgment, feature_distance_baseline,
                      FEATURE_NAMES)
from .state import RunPaths, read_json, read_jsonl, write_json


def _now_stamp():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _log_writer(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8", buffering=1)   # line-buffered
    def _write(msg):
        line = f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {msg}"
        print(line, flush=True)
        f.write(line + "\n"); f.flush()
    return _write, f


def _collect_source_trajectories(paths: RunPaths) -> Dict[Tuple[str, str], List[Tuple[str, str, str]]]:
    """From disk, return dict[(arch, model_label)] -> list of (model_label, traj_id, sequence)."""
    out: Dict[Tuple[str, str], List[Tuple[str, str, str]]] = {}
    for arch in C.ARCHITECTURES:
        base = paths.source_batch if arch == "batch" else paths.source_online
        for m in C.MODELS:
            key = (arch, m.label)
            out[key] = []
            model_dir = os.path.join(base, m.label)
            if not os.path.isdir(model_dir):
                continue
            for fn in sorted(os.listdir(model_dir)):
                if not fn.endswith(".json") or ".steps." in fn:
                    continue
                rec = read_json(os.path.join(model_dir, fn))
                if rec and rec.get("valid"):
                    out[key].append((m.label, rec["trajectory_id"], rec["parsed_sequence"]))
    return out


def smoke_test(client, accountant: CostAccountant, paths: RunPaths, log) -> Dict:
    """Small live test to verify infra + measure per-call cost. Records go under paths.smoke."""
    smoke_records = []
    for m in C.MODELS:
        log(f"  smoke: batch call for {m.label}")
        from .api import call_model, parse_batch
        r_batch = call_model(client, accountant, kind="smoke", slug=m.slug,
                             prompt_text=C.BATCH_PROMPT,
                             max_tokens=C.BATCH_MAX_TOKENS)
        parsed = parse_batch(r_batch.response_text)
        smoke_records.append({"phase": "batch", "model": m.label,
                              "valid": bool(parsed),
                              **asdict(r_batch)})
        log(f"    -> valid={bool(parsed)} tokens p={r_batch.prompt_tokens} "
            f"c={r_batch.completion_tokens} r={r_batch.reasoning_tokens} "
            f"cost=${r_batch.cost_usd:.4f} err={r_batch.error_message[:60]!r}")

        # 3-step online preflight
        log(f"  smoke: 3-step online for {m.label}")
        history = ""
        for step in range(1, 4):
            prompt = C.online_trial_prompt(history)
            r = call_model(client, accountant, kind="smoke", slug=m.slug,
                           prompt_text=prompt, max_tokens=C.ONLINE_MAX_TOKENS)
            from .api import parse_online
            p = parse_online(r.response_text) or ""
            smoke_records.append({"phase": f"online_step{step}", "model": m.label,
                                  "parsed": p, **asdict(r)})
            log(f"    step{step}: raw={r.response_text!r} parsed={p!r} "
                f"cost=${r.cost_usd:.4f}")
            if not p:
                log(f"    smoke online: parse fail at step {step} for {m.label}")
                break
            history += p

    log("  smoke: judgment structured-output preflight")
    mode = preflight_response_mode(client, accountant,
                                   [m.slug for m in C.MODELS], log=log)
    write_json(os.path.join(paths.smoke, "smoke_records.json"), smoke_records)
    write_json(os.path.join(paths.smoke, "smoke_summary.json"),
               {"response_mode": mode,
                "spent_usd_so_far": accountant.spent_usd,
                "records": smoke_records})
    return {"response_mode": mode, "records": smoke_records}


def project_full_cost(smoke_records: List[Dict], accountant: CostAccountant) -> Dict:
    """Estimate the cost of the full remaining run from smoke observations."""
    per_model_batch: Dict[str, float] = {}
    per_model_online_step: Dict[str, float] = {}
    # split records by phase
    for rec in smoke_records:
        m = rec["model"]
        if rec["phase"] == "batch":
            per_model_batch[m] = per_model_batch.get(m, 0.0) + rec["cost_usd"]
        elif rec["phase"].startswith("online_step"):
            # average online step cost per model
            per_model_online_step.setdefault(m, []).append(rec["cost_usd"])
    # convert lists to means
    for m in per_model_online_step:
        v = per_model_online_step[m]
        per_model_online_step[m] = sum(v) / len(v) if v else 0.0

    # projections
    n_batch_per_model = C.TRAJECTORIES_PER_MODEL_ARCH
    n_online_calls_per_model = C.TRAJECTORIES_PER_MODEL_ARCH * C.TRAJECTORY_LENGTH
    projected_source = 0.0
    for m in C.MODELS:
        projected_source += per_model_batch.get(m.label, 0.0) * n_batch_per_model
        projected_source += per_model_online_step.get(m.label, 0.0) * n_online_calls_per_model
    # judgments: approximate as 2x observed structured smoke cost per judge
    # (144 total = 48 per judge). Use accountant "smoke" spend for judgment prefx * ratio.
    judgment_est = accountant.spent_by_kind.get("smoke", 0.0)  # rough proxy
    # a more useful estimate: assume judgment call ~ 2x online step cost (with the pair strings)
    judgment_est = 0.0
    for m in C.MODELS:
        judgment_est += per_model_online_step.get(m.label, 0.0) * 2.5 * (144 // len(C.MODELS))
    total_projected = accountant.spent_usd + projected_source + judgment_est
    return {"spent_so_far": accountant.spent_usd,
            "projected_source_usd": projected_source,
            "projected_judgment_usd": judgment_est,
            "projected_total_usd": total_projected,
            "budget_usd": C.BUDGET_USD}


# ---------------- phase runners --------------------------------------------

def phase_source(client, accountant: CostAccountant, paths: RunPaths, log):
    log("PHASE: source generation (batch + online)")
    # Batch first (fast). Concurrency=1 per model to keep things predictable.
    for m in C.MODELS:
        generate_batch_source(client, accountant, paths, m, log=log)
    # Online: within a model, trajectories can be parallelized (each is independent)
    # Small concurrency (3) across model+trajectory boundaries.
    trajectory_tasks = []
    for m in C.MODELS:
        # Determine how many remaining trajectories needed for this model
        # by counting existing valid ones on disk.
        model_dir = os.path.join(paths.source_online, m.label)
        os.makedirs(model_dir, exist_ok=True)
        existing_valid = 0
        existing_indices = []
        if os.path.isdir(model_dir):
            for fn in sorted(os.listdir(model_dir)):
                if not fn.endswith(".json") or ".steps." in fn:
                    continue
                rec = read_json(os.path.join(model_dir, fn))
                if rec:
                    existing_indices.append(int(rec["replicate_index"]))
                    if rec.get("valid"):
                        existing_valid += 1
        needed = C.TRAJECTORIES_PER_MODEL_ARCH - existing_valid
        start_index = (max(existing_indices) + 1) if existing_indices else 0
        for i in range(needed):
            trajectory_tasks.append((m, start_index + i))

    # Run trajectories with limited concurrency
    with ThreadPoolExecutor(max_workers=C.SOURCE_CONCURRENCY) as pool:
        futures = {pool.submit(generate_online_trajectory, client, accountant,
                                paths, m, idx, log=log): (m.label, idx)
                    for (m, idx) in trajectory_tasks}
        for fut in as_completed(futures):
            _ = fut.result()


def phase_trials(paths: RunPaths, log) -> List[Trial]:
    log("PHASE: trial construction")
    trial_manifest = read_json(paths.trial_manifest)
    if trial_manifest:
        log(f"  resume: reading existing trial manifest with {len(trial_manifest)} trials")
        return [Trial(**t) for t in trial_manifest]
    source = _collect_source_trajectories(paths)
    for (arch, ml), lst in source.items():
        if len(lst) < C.TRAJECTORIES_PER_MODEL_ARCH:
            raise RuntimeError(f"Insufficient valid trajectories for ({arch}, {ml}): "
                               f"{len(lst)} of {C.TRAJECTORIES_PER_MODEL_ARCH}")
    trials = build_all_trials(source)
    write_json(paths.trial_manifest, [asdict(t) for t in trials])
    log(f"  wrote {len(trials)} trials to {paths.trial_manifest}")
    return trials


def phase_judgment(client, accountant: CostAccountant, paths: RunPaths,
                   trials: List[Trial], response_mode: str, log):
    log(f"PHASE: judgment ({len(trials)} trials, response_mode={response_mode})")
    slug_by_label = {m.label: m.slug for m in C.MODELS}
    # Resume by skipping trials whose record already exists
    def _pending(trials_):
        out = []
        for t in trials_:
            p = paths.judgment_path(t.trial_id)
            if os.path.exists(p):
                rec = read_json(p)
                if rec and rec.get("parsed_judgment") in ("SAME", "DIFFERENT"):
                    continue
            out.append(t)
        return out
    pending = _pending(trials)
    log(f"  {len(pending)} trials pending (of {len(trials)} total)")

    def _do(t: Trial):
        judge_slug = slug_by_label[t.judge_label]
        rec = judge_one_trial(client, accountant, t, judge_slug, response_mode)
        write_json(paths.judgment_path(t.trial_id), asdict(rec))
        return rec

    with ThreadPoolExecutor(max_workers=C.JUDGMENT_CONCURRENCY) as pool:
        futures = {pool.submit(_do, t): t.trial_id for t in pending}
        done = 0
        for fut in as_completed(futures):
            r = fut.result()
            done += 1
            if done % 10 == 0 or done == len(pending):
                log(f"  judgment progress {done}/{len(pending)}  "
                    f"latest: {r.judge_label}/{r.architecture}/{r.cell} "
                    f"parsed={r.parsed_judgment!r} correct={r.correct} "
                    f"spent=${accountant.spent_usd:.4f}")


def phase_analysis_and_report(paths: RunPaths, accountant: CostAccountant,
                              response_mode: str, log):
    log("PHASE: analysis + reports")
    # 1) source features
    source_traj = _collect_source_trajectories(paths)
    features_by_traj: Dict[str, Dict[str, float]] = {}
    source_rows = []
    feats_by_model_batch: Dict[str, List[Dict[str, float]]] = {ml: [] for ml in C.MODEL_LABELS}
    feats_by_model_online: Dict[str, List[Dict[str, float]]] = {ml: [] for ml in C.MODEL_LABELS}
    for (arch, ml), lst in source_traj.items():
        for (label, tid, seq) in lst:
            f = sequence_features(seq)
            features_by_traj[tid] = f
            row = {"trajectory_id": tid, "architecture": arch, "model": ml,
                   "sequence": seq, **f}
            source_rows.append(row)
            if arch == "batch":
                feats_by_model_batch[ml].append(f)
            else:
                feats_by_model_online[ml].append(f)
    _write_csv(os.path.join(paths.results, "source_metrics.csv"), source_rows)

    # 2) classifier per architecture (only if all 3 models have data)
    def _clf(feats_by_model):
        if all(len(feats_by_model[ml]) >= 2 for ml in C.MODEL_LABELS):
            return nearest_centroid_loo(feats_by_model)
        return None
    clf_batch = _clf(feats_by_model_batch)
    clf_online = _clf(feats_by_model_online)
    classifier_rows = []
    if clf_batch:
        classifier_rows.append({"architecture": "batch", "accuracy": clf_batch["accuracy"],
                                "n": clf_batch["n"],
                                **{f"confusion:{k}": v for k, v in clf_batch["confusion"].items()}})
    if clf_online:
        classifier_rows.append({"architecture": "online", "accuracy": clf_online["accuracy"],
                                "n": clf_online["n"],
                                **{f"confusion:{k}": v for k, v in clf_online["confusion"].items()}})
    _write_csv(os.path.join(paths.results, "source_model_classifier.csv"), classifier_rows)

    # 3) judgments
    judgment_records = []
    for fn in sorted(os.listdir(paths.judgment)):
        if not fn.endswith(".json"):
            continue
        rec = read_json(os.path.join(paths.judgment, fn))
        if rec:
            judgment_records.append(rec)
    # Write flat trial-level csv
    _write_csv(os.path.join(paths.results, "trial_level.csv"),
               [{k: v for k, v in r.items()
                 if k not in ("display_string_1", "display_string_2",
                              "prompt_text", "raw_response")} for r in judgment_records])
    summ = summarize_judgment(judgment_records)
    _write_csv(os.path.join(paths.results, "cell_summary.csv"), summ["per_cell"])
    _write_csv(os.path.join(paths.results, "judge_summary.csv"),
               summ["per_judge_arch"])
    _write_csv(os.path.join(paths.results, "self_advantage_by_architecture.csv"),
               [{"judge": j, "architecture": arch,
                 "own_accuracy": summ["per_judge_arch"][k].get("own_accuracy"),
                 "other_accuracy": summ["per_judge_arch"][k].get("other_accuracy"),
                 "self_advantage": summ["per_judge_arch"][k].get("self_advantage"),
                 "total_accuracy": summ["per_judge_arch"][k].get("total_accuracy"),
                 "same_rate": summ["per_judge_arch"][k].get("same_response_rate")}
                for k, row in enumerate(summ["per_judge_arch"])
                for j, arch in [(row["judge"], row["architecture"])]])
    _write_csv(os.path.join(paths.results, "architecture_contrast.csv"), summ["dynamic_gain"])

    # 4) feature-distance baseline
    fd = feature_distance_baseline(judgment_records, features_by_traj)
    _write_csv(os.path.join(paths.results, "feature_distance_baseline.csv"),
               [{"architecture": a, **v} for a, v in fd["per_arch"].items()]
               + fd["per_cell"])

    # 5) Markdown FINAL_OVERNIGHT_REPORT
    report_path = os.path.join(paths.results, "FINAL_OVERNIGHT_REPORT.md")
    _write_final_report(report_path, paths, accountant, response_mode,
                        source_rows, clf_batch, clf_online, summ, fd)
    log(f"  wrote {report_path}")


def _write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        return
    # union of keys
    keys = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                keys.append(k); seen.add(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _write_final_report(path, paths, accountant, response_mode,
                        source_rows, clf_batch, clf_online, summ, fd):
    lines = []
    lines.append("# SPAR Dynamic Behavioral Self-Signature Pilot — Final Report")
    lines.append("")
    lines.append(f"Run root: `{paths.root}`")
    lines.append(f"Experiment tag: `{C.EXPERIMENT_TAG}`")
    lines.append(f"Judgment response mode: `{response_mode}`")
    lines.append(f"Total spend: **${accountant.spent_usd:.4f}** / ${C.BUDGET_USD:.2f} cap")
    lines.append("")
    lines.append("## Spend by phase")
    for k, v in sorted(accountant.spent_by_kind.items()):
        n = accountant.calls_by_kind.get(k, 0)
        lines.append(f"- {k}: {n} calls, ${v:.4f}")
    lines.append("")

    lines.append("## Source integrity")
    # Count valid trajectories per model x architecture
    by_key = {}
    for r in source_rows:
        by_key.setdefault((r["architecture"], r["model"]), []).append(r)
    lines.append("| architecture | model | n valid | mean p(H) | mean switch | mean runs_Z | mean longest_run |")
    lines.append("|---|---|---|---|---|---|---|")
    for arch in C.ARCHITECTURES:
        for m in C.MODEL_LABELS:
            rows = by_key.get((arch, m), [])
            import numpy as _np
            if rows:
                phs = [r["prop_H"] for r in rows]; sws = [r["switch_rate"] for r in rows]
                rzs = [r["runs_Z"] for r in rows]; lrs = [r["longest_run"] for r in rows]
                lines.append(f"| {arch} | {m} | {len(rows)} | {_np.mean(phs):.3f} | "
                             f"{_np.mean(sws):.3f} | {_np.mean(rzs):+.2f} | {_np.mean(lrs):.2f} |")
            else:
                lines.append(f"| {arch} | {m} | 0 | - | - | - | - |")
    lines.append("")

    lines.append("## Source-model identifiability (leave-one-out nearest centroid)")
    lines.append("")
    if clf_batch:
        lines.append(f"- batch: **{clf_batch['accuracy']:.3f}** (n={clf_batch['n']})")
        for kk, vv in clf_batch["confusion"].items():
            lines.append(f"  - {kk}: {vv}")
    else:
        lines.append("- batch: not computed (insufficient data)")
    if clf_online:
        lines.append(f"- online: **{clf_online['accuracy']:.3f}** (n={clf_online['n']})")
        for kk, vv in clf_online["confusion"].items():
            lines.append(f"  - {kk}: {vv}")
    else:
        lines.append("- online: not computed (insufficient data)")
    if clf_batch and clf_online:
        lines.append("")
        lines.append(f"Architecture contrast: online - batch = "
                     f"**{clf_online['accuracy'] - clf_batch['accuracy']:+.3f}**")
    lines.append("")

    lines.append("## Judgment performance (per judge x architecture)")
    lines.append("")
    lines.append("| judge | arch | n | total acc | A | B | C | D | own | other | self_adv | A-C | B-D | SAME rate |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for row in summ["per_judge_arch"]:
        lines.append("| {j} | {a} | {n} | {tot:.3f} | {A:.3f} | {B:.3f} | {C:.3f} | {D:.3f} | "
                     "{own:.3f} | {other:.3f} | {sa:+.3f} | {ac:+.3f} | {bd:+.3f} | {sr:.3f} |".format(
                        j=row["judge"], a=row["architecture"], n=row["n"],
                        tot=row["total_accuracy"], A=row["accuracy_A"], B=row["accuracy_B"],
                        C=row["accuracy_C"], D=row["accuracy_D"],
                        own=row["own_accuracy"], other=row["other_accuracy"],
                        sa=row["self_advantage"], ac=row["A_minus_C"], bd=row["B_minus_D"],
                        sr=row["same_response_rate"]))
    lines.append("")

    lines.append("## Central result: dynamic self-signature gain per judge")
    lines.append("")
    lines.append("| judge | self_advantage_batch | self_advantage_online | dynamic_self_signature_gain |")
    lines.append("|---|---|---|---|")
    for row in summ["dynamic_gain"]:
        lines.append(f"| {row['judge']} | {row['self_advantage_batch']:+.3f} | "
                     f"{row['self_advantage_online']:+.3f} | "
                     f"{row['dynamic_self_signature_gain']:+.3f} |")
    lines.append("")
    lines.append("### Pooled across judges (weighted by n)")
    lines.append("")
    for arch, p in summ["pooled_by_architecture"].items():
        if p:
            lines.append(f"- {arch}: pooled self_advantage = **{p['self_advantage']:+.3f}** "
                         f"(own={p['own_accuracy']:.3f}, other={p['other_accuracy']:.3f})")
    lines.append("")

    lines.append("## Feature-distance baseline (per architecture)")
    lines.append("")
    for arch, v in fd["per_arch"].items():
        lines.append(f"- {arch}: median-threshold accuracy = {v['median_threshold_accuracy']:.3f} "
                     f"(n={v['n']}, median distance = {v['median_distance']:.3f})")
    lines.append("")
    lines.append("### Per-cell feature distances")
    lines.append("| architecture | cell | n | mean distance | sd distance |")
    lines.append("|---|---|---|---|---|")
    for row in fd["per_cell"]:
        lines.append(f"| {row['architecture']} | {row['cell']} | {row['n']} | "
                     f"{row['mean_distance']:.3f} | {row['sd_distance']:.3f} |")
    lines.append("")

    lines.append("## Interpretation notes")
    lines.append("")
    lines.append("- One session per (judge x architecture x cell) block; 6 trials per cell means accuracy granularity is 1/6.")
    lines.append("- `self_advantage` (own_accuracy - other_accuracy) can arise from either genuine own-model discrimination OR from own-involving trials being objectively easier at the visible-feature level. Compare against the feature-distance baseline and per-cell distances above.")
    lines.append("- The central hypothesis is `self_advantage_online > self_advantage_batch` (positive dynamic gain).")
    lines.append("- Descriptive pilot only; do not infer self-awareness or introspection from this data.")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------- CLI ------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", required=True,
                    help="explicit confirmation that this run makes live paid calls")
    ap.add_argument("--yes", action="store_true", required=True,
                    help="skip all interactive confirmations")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--data-root", default="data/spar_dynamic")
    ap.add_argument("--skip-smoke", action="store_true",
                    help="assume a smoke run already occurred; skip live smoke calls")
    ap.add_argument("--response-mode", default="",
                    choices=["", "json_schema", "chat"],
                    help="override the smoke-selected response mode")
    args = ap.parse_args()

    run_id = args.run_id or _now_stamp()
    paths = RunPaths(args.data_root, run_id)
    paths.ensure()
    log, log_file = _log_writer(os.path.join(paths.logs, "orchestrator.log"))
    log(f"START run_id={run_id}  data_root={args.data_root}")

    try:
        client = make_client()
        accountant = CostAccountant(client)
        log("  fetching OpenRouter model catalog and pricing snapshot")
        catalog = accountant.snapshot_catalog()
        # verify our three models are present
        missing = [m.slug for m in C.MODELS if m.slug not in catalog]
        if missing:
            log(f"ABORT: missing model(s) from catalog: {missing}")
            _write_stop_marker(paths, "model_missing", accountant.spent_usd,
                               f"missing: {missing}")
            return
        write_json(paths.catalog, catalog)

        response_mode = args.response_mode
        if not args.skip_smoke:
            log("PHASE: smoke test")
            r = smoke_test(client, accountant, paths, log)
            response_mode = response_mode or r["response_mode"]
            # cost projection
            proj = project_full_cost(r["records"], accountant)
            log(f"  cost projection: spent=${proj['spent_so_far']:.4f}, "
                f"projected_source=${proj['projected_source_usd']:.4f}, "
                f"projected_judgment=${proj['projected_judgment_usd']:.4f}, "
                f"projected_total=${proj['projected_total_usd']:.4f}, "
                f"budget=${proj['budget_usd']:.2f}")
            write_json(os.path.join(paths.smoke, "cost_projection.json"), proj)
            if proj["projected_total_usd"] > C.STOP_AT_PROJECTED_USD:
                log(f"ABORT: projected total ${proj['projected_total_usd']:.2f} > "
                    f"budget cap ${C.STOP_AT_PROJECTED_USD:.2f}")
                _write_stop_marker(paths, "budget_projection_exceeded",
                                    accountant.spent_usd,
                                    f"projected ${proj['projected_total_usd']:.2f} > ${C.STOP_AT_PROJECTED_USD:.2f}")
                return
        response_mode = response_mode or "json_schema"
        write_json(paths.manifest, {"run_id": run_id, "response_mode": response_mode,
                                    "started_utc": _now_stamp(),
                                    "budget_usd": C.BUDGET_USD})

        phase_source(client, accountant, paths, log)
        trials = phase_trials(paths, log)
        phase_judgment(client, accountant, paths, trials, response_mode, log)
        phase_analysis_and_report(paths, accountant, response_mode, log)

        log(f"COMPLETE  total_spend=${accountant.spent_usd:.4f}")
        _write_complete_marker(paths, accountant.spent_usd)
    except BudgetExceeded as e:
        log(f"BUDGET STOP: {e}")
        _write_stop_marker(paths, "budget_cap_hit_during_run", accountant.spent_usd, str(e))
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        log(f"FATAL {type(e).__name__}: {e}\n{tb}")
        _write_stop_marker(paths, "fatal_exception",
                            accountant.spent_usd if 'accountant' in dir() else 0.0,
                            f"{type(e).__name__}: {e}")
    finally:
        try: log_file.close()
        except Exception: pass


def _write_stop_marker(paths, phase, spent, reason):
    p = os.path.join(paths.root, "OVERNIGHT_RUN_STOPPED.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"# Overnight run stopped\n\n"
                f"- run_id: {paths.run_id}\n"
                f"- phase: {phase}\n"
                f"- spend_so_far_usd: ${spent:.4f}\n"
                f"- reason: {reason}\n"
                f"- resume: rerun `python -m spar_dynamic.orchestrator --live --yes "
                f"--run-id {paths.run_id} --skip-smoke` (idempotent)\n")


def _write_complete_marker(paths, spent):
    p = os.path.join(paths.root, "OVERNIGHT_RUN_COMPLETE.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"# Overnight run complete\n\n"
                f"- run_id: {paths.run_id}\n"
                f"- total_spend_usd: ${spent:.4f}\n"
                f"- completed_utc: {_now_stamp()}\n"
                f"- final_report: {os.path.join(paths.results, 'FINAL_OVERNIGHT_REPORT.md')}\n")


if __name__ == "__main__":
    main()
