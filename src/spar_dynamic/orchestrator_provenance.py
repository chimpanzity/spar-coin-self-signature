"""Orchestrator for Pilot 3 — Provenance-manipulation SELF/OTHER.

Run:
  python -m spar_dynamic.orchestrator_provenance \\
    --live --yes \\
    --source-run-root data/spar_dynamic/spar-dynamic-run-20260929T081814Z \\
    [--run-id <id>] [--skip-smoke]

Resume-safe. Validation is strict: any abandoned trial produces
OVERNIGHT_RUN_STOPPED, not COMPLETE.
"""

import argparse, csv, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from typing import Dict, List, Tuple

from . import config as C
from .api import CostAccountant, call_model, make_client, BudgetExceeded, parse_self_other
from .analyze import (sequence_features, summarize_provenance,
                      arch_conditioned_feature_baseline,
                      nearest_centroid_loo, FEATURE_NAMES)
from .provenance import (build_provenance_trials, judge_one_trial,
                          ProvenanceTrial)
from .self_other import load_source_trajectories
from .state import RunPaths, read_json, write_json


def _now_stamp():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _log_writer(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8", buffering=1)
    def w(msg):
        line = f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {msg}"
        print(line, flush=True); f.write(line + "\n"); f.flush()
    return w, f


def phase_smoke(client, accountant, log):
    disposable = "HTHHTHTTHTHHTTHTHHTTHHTHTHTHHTHTHHTHHTHTHTHTHTHTHT"
    out = []
    for m in C.MODELS:
        # smoke each judge on one told-batch and one told-online call (short)
        prompt = C.provenance_prompt(disposable, "batch")
        r = call_model(client, accountant, kind="smoke", slug=m.slug,
                       prompt_text=prompt, max_tokens=C.PROVENANCE_MAX_TOKENS,
                       response_format=None)
        parsed = parse_self_other(r.response_text)
        out.append({"model": m.label, "stated": "batch", "raw": r.response_text,
                    "parsed": parsed, "cost_usd": r.cost_usd,
                    "prompt_tokens": r.prompt_tokens, "completion_tokens": r.completion_tokens,
                    "reasoning_tokens": r.reasoning_tokens,
                    "finish_reason": r.finish_reason, "latency_ms": r.latency_ms,
                    "error_message": r.error_message})
        log(f"  smoke {m.label} told-batch: raw={r.response_text[:60]!r} parsed={parsed!r} "
            f"cost=${r.cost_usd:.4f} c/r toks={r.completion_tokens}/{r.reasoning_tokens}")
    return out


def project_full_cost(smoke_records, accountant, n_planned=240) -> Dict:
    per = {r["model"]: r["cost_usd"] for r in smoke_records}
    projected_judgment = 0.0
    for m in C.MODELS:
        projected_judgment += per.get(m.label, 0.0) * 80 * 1.15  # 80 trials per judge, 15% retry overhead
    total = accountant.spent_usd + projected_judgment
    return {"spent_so_far": accountant.spent_usd,
            "projected_judgment_usd": projected_judgment,
            "projected_total_usd": total,
            "budget_usd": C.PROVENANCE_BUDGET_USD}


def phase_trials(paths: RunPaths, source_run_root: str, log) -> List[ProvenanceTrial]:
    manifest_path = os.path.join(paths.trials, "provenance_trial_manifest.json")
    existing = read_json(manifest_path)
    if existing:
        log(f"  resume: {len(existing)} trials on disk")
        return [ProvenanceTrial(**t) for t in existing]
    src = load_source_trajectories(source_run_root)
    for (arch, ml), lst in src.items():
        if len(lst) < C.PROVENANCE_UNIQUE_TRAJECTORIES_PER_CELL:
            raise RuntimeError(f"insufficient source trajectories for ({arch}, {ml}): {len(lst)}")
    trials = build_provenance_trials(src)
    write_json(manifest_path, [asdict(t) for t in trials])
    log(f"  wrote {len(trials)} trials")
    return trials


def phase_judgment(client, accountant, paths: RunPaths,
                   trials: List[ProvenanceTrial], log):
    slug_by_label = {m.label: m.slug for m in C.MODELS}
    def _done(t):
        p = os.path.join(paths.judgment, f"prov-{t.trial_id}.json")
        if os.path.exists(p):
            rec = read_json(p)
            if rec and rec.get("trial_status") in ("ok", "abandoned"):
                return True
        return False
    pending = [t for t in trials if not _done(t)]
    log(f"  {len(pending)} trials pending of {len(trials)}")

    def _do(t: ProvenanceTrial):
        slug = slug_by_label[t.judge_label]
        rec = judge_one_trial(client, accountant, t, slug)
        p = os.path.join(paths.judgment, f"prov-{t.trial_id}.json")
        write_json(p, asdict(rec))
        return rec

    with ThreadPoolExecutor(max_workers=C.JUDGMENT_CONCURRENCY) as pool:
        futures = {pool.submit(_do, t): t.trial_id for t in pending}
        n_done = 0
        for fut in as_completed(futures):
            r = fut.result(); n_done += 1
            if n_done % 20 == 0 or n_done == len(pending):
                log(f"  judgment {n_done}/{len(pending)}: {r.judge_label}/{r.true_source_identity}/"
                    f"actual={r.actual_architecture}/told={r.stated_architecture} "
                    f"parsed={r.parsed_judgment!r} correct={r.correct} "
                    f"status={r.trial_status} spent=${accountant.spent_usd:.4f}")


def phase_validate(paths: RunPaths, trials: List[ProvenanceTrial], log) -> Dict:
    n_planned = len(trials)
    records = []
    for t in trials:
        p = os.path.join(paths.judgment, f"prov-{t.trial_id}.json")
        if not os.path.exists(p):
            log(f"  MISSING record for {t.trial_id}")
            continue
        records.append(read_json(p))
    n_valid = sum(1 for r in records if r.get("valid"))
    n_abandoned = sum(1 for r in records if r.get("trial_status") == "abandoned")
    # cell balance: 10 per (judge x source_identity x actual_arch x stated_arch)
    cell_counts_ok = True
    from collections import Counter
    cell_counter = Counter((r["judge_label"], r["true_source_identity"],
                             r["actual_architecture"], r["stated_architecture"])
                            for r in records if r.get("valid"))
    for judge in C.MODEL_LABELS:
        for src in ("SELF", "OTHER"):
            for a in C.ARCHITECTURES:
                for s in C.ARCHITECTURES:
                    if cell_counter[(judge, src, a, s)] != 10:
                        cell_counts_ok = False
                        log(f"  cell short: {judge}/{src}/actual={a}/told={s} = "
                            f"{cell_counter[(judge, src, a, s)]}")
    ok = (len(records) == n_planned and n_valid == n_planned and n_abandoned == 0 and cell_counts_ok)
    result = {"n_planned": n_planned, "n_records": len(records),
              "n_valid": n_valid, "n_abandoned": n_abandoned,
              "cell_counts_ok": cell_counts_ok,
              "run_complete_ok": ok}
    write_json(os.path.join(paths.results, "validation_report.json"), result)
    return result


def phase_analysis(paths: RunPaths, source_run_root: str, log, accountant, val: Dict):
    records = []
    for fn in sorted(os.listdir(paths.judgment)):
        if not fn.startswith("prov-"): continue
        rec = read_json(os.path.join(paths.judgment, fn))
        if rec: records.append(rec)

    src = load_source_trajectories(source_run_root)
    features_by_traj: Dict[str, Dict[str, float]] = {}
    source_by_arch_model: Dict[Tuple[str, str], List[Dict[str, float]]] = {}
    for (arch, ml), lst in src.items():
        source_by_arch_model[(arch, ml)] = []
        for (_, tid, seq) in lst:
            f = sequence_features(seq)
            features_by_traj[tid] = f
            source_by_arch_model[(arch, ml)].append(f)

    # source-model 3-way classifiers (prior finding)
    clf_batch = clf_online = None
    def _feats(arch):
        return {ml: source_by_arch_model.get((arch, ml), []) for ml in C.MODEL_LABELS}
    if all(len(_feats("batch")[ml]) >= 2 for ml in C.MODEL_LABELS):
        clf_batch = nearest_centroid_loo(_feats("batch"))
    if all(len(_feats("online")[ml]) >= 2 for ml in C.MODEL_LABELS):
        clf_online = nearest_centroid_loo(_feats("online"))

    summ = summarize_provenance(records)
    base = arch_conditioned_feature_baseline(records, features_by_traj, source_by_arch_model)

    # CSVs
    _write_csv(os.path.join(paths.results, "trial_level.csv"),
               [{k: v for k, v in r.items()
                 if k not in ("sequence_display", "prompt_text",
                              "raw_completion", "attempt_records")}
                for r in records])
    _write_csv(os.path.join(paths.results, "cell_summary.csv"), summ["cells"])
    _write_csv(os.path.join(paths.results, "congruence_summary.csv"), summ["congruence"])
    _write_csv(os.path.join(paths.results, "self_specific_provenance_effect.csv"),
               summ["self_specific_provenance_effect"])
    _write_csv(os.path.join(paths.results, "arch_conditional_self_response.csv"),
               summ["arch_conditional_self"])
    _write_csv(os.path.join(paths.results, "paired_provenance_effects.csv"),
               summ["paired_delta_per_pair"])
    _write_csv(os.path.join(paths.results, "paired_provenance_summary.csv"),
               summ["paired_delta_summary"])
    _write_csv(os.path.join(paths.results, "signal_detection.csv"), summ["signal_detection"])
    _write_csv(os.path.join(paths.results, "architecture_conditioned_baseline.csv"),
               base["trial_rows"])
    _write_csv(os.path.join(paths.results, "architecture_conditioned_baseline_summary.csv"),
               [{"stated_architecture": a, **v} for a, v in base["per_stated_arch"].items()])

    _write_report(paths, accountant, val, summ, base, clf_batch, clf_online)


def _write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8") as f: f.write("")
        return
    keys = []; seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen: keys.append(k); seen.add(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows: w.writerow(r)


def _write_report(paths, accountant, val, summ, base, clf_batch, clf_online):
    p = os.path.join(paths.results, "PROVENANCE_SELF_ATTRIBUTION_REPORT.md")
    lines = []
    lines.append("# SPAR Pilot 3 — Provenance-Manipulated SELF vs OTHER Attribution")
    lines.append("")
    lines.append(f"Run root: `{paths.root}`")
    lines.append(f"Experiment tag: `{C.PROVENANCE_TAG}`")
    lines.append(f"Total spend: **${accountant.spent_usd:.4f}** / ${C.PROVENANCE_BUDGET_USD:.2f} cap")
    lines.append("")
    lines.append("## Design")
    lines.append("")
    lines.append("2 x 2 x 2 factorial per judge:")
    lines.append("- Source identity: SELF vs OTHER")
    lines.append("- Actual architecture: batch vs online (of the source trajectory)")
    lines.append("- Stated architecture: told-batch vs told-online (what the judge is told)")
    lines.append("")
    lines.append("Each unique trajectory presented twice in fresh stateless calls, once per")
    lines.append("stated-architecture condition. Trajectory identity constant across the two")
    lines.append("presentations; only the verbal description of production regime changes.")
    lines.append("")
    lines.append("- 10 trials per cell x 8 cells = 80 trials/judge x 3 judges = **240 total**")
    lines.append("")

    lines.append("## Stated-architecture sentences")
    lines.append("")
    lines.append("**told-batch**:")
    lines.append(f"> {C.PROVENANCE_STATED_BATCH}")
    lines.append("")
    lines.append("**told-online**:")
    lines.append(f"> {C.PROVENANCE_STATED_ONLINE}")
    lines.append("")

    lines.append("## Run integrity")
    for k, v in val.items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    lines.append("## Spend by phase")
    for k, v in sorted(accountant.spent_by_kind.items()):
        n = accountant.calls_by_kind.get(k, 0)
        lines.append(f"- {k}: {n} calls, ${v:.4f}")
    lines.append("")

    lines.append("## Eight-cell summary (per judge)")
    lines.append("")
    lines.append("| judge | source | actual | stated | n | acc | SELF resp rate |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in summ["cells"]:
        lines.append(f"| {row['judge']} | {row['true_source_identity']} | "
                     f"{row['actual_architecture']} | {row['stated_architecture']} | "
                     f"{row['n']} | {row['accuracy']:.3f} | {row['self_response_rate']:.3f} |")
    lines.append("")

    lines.append("## Congruence contrasts (per judge x source_identity)")
    lines.append("")
    lines.append("| judge | source | congruent acc | incongruent acc | Δ (congruent - incongruent) |")
    lines.append("|---|---|---|---|---|")
    for row in summ["congruence"]:
        lines.append(f"| {row['judge']} | {row['true_source_identity']} | "
                     f"{row['congruent_accuracy']:.3f} | {row['incongruent_accuracy']:.3f} | "
                     f"{row['congruence_advantage']:+.3f} |")
    lines.append("")

    lines.append("## Self-specific provenance effect")
    lines.append("")
    lines.append("`self_specific = congruence_advantage_SELF - congruence_advantage_OTHER`. ")
    lines.append("Positive values would suggest that accurate provenance information disproportionately")
    lines.append("helps self-attribution — an architecture-conditional behavioral self-signature.")
    lines.append("")
    lines.append("| judge | Δ_SELF | Δ_OTHER | self-specific |")
    lines.append("|---|---|---|---|")
    for row in summ["self_specific_provenance_effect"]:
        lines.append(f"| {row['judge']} | {row['congruence_advantage_SELF']:+.3f} | "
                     f"{row['congruence_advantage_OTHER']:+.3f} | "
                     f"{row['self_specific_provenance_effect']:+.3f} |")
    lines.append("")

    lines.append("## Architecture-conditional SELF response (true SELF trials only)")
    lines.append("")
    lines.append("For each judge and each actual architecture of the judge's own trajectories,")
    lines.append("compare P(SELF) when told-batch vs told-online. A positive `delta` means the")
    lines.append("judge is more likely to claim SELF when told the trajectory was generated online.")
    lines.append("")
    lines.append("| judge | actual arch | P(SELF) told-batch | P(SELF) told-online | Δ (online-batch) |")
    lines.append("|---|---|---|---|---|")
    for row in summ["arch_conditional_self"]:
        lines.append(f"| {row['judge']} | {row['actual_architecture']} | "
                     f"{row['p_self_told_batch']:.3f} | {row['p_self_told_online']:.3f} | "
                     f"{row['delta_told_online_minus_batch']:+.3f} |")
    lines.append("")
    lines.append("**Expected crossover pattern if the judge holds an architecture-conditional")
    lines.append("self-model**: for `actual batch` rows, delta tends negative (own batch strings")
    lines.append("look more SELF when told batch); for `actual online` rows, delta tends positive.")
    lines.append("")

    lines.append("## Paired within-trajectory provenance deltas")
    lines.append("")
    lines.append("Across matched trajectory pairs, `delta = SELF_response(told-online) - SELF_response(told-batch)`.")
    lines.append("Each pair contributes exactly one delta in {-1, 0, +1}. Positive means the same")
    lines.append("trajectory got more SELF-attributions when described as online than as batch.")
    lines.append("")
    lines.append("| judge | source | actual arch | n_pairs | mean Δ | n(Δ>0) | n(Δ<0) | n(Δ=0) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for row in summ["paired_delta_summary"]:
        lines.append(f"| {row['judge']} | {row['true_source_identity']} | "
                     f"{row['actual_architecture']} | {row['n_pairs']} | "
                     f"{row['mean_delta_told_online_minus_batch']:+.3f} | "
                     f"{row['n_delta_positive']} | {row['n_delta_negative']} | "
                     f"{row['n_delta_zero']} |")
    lines.append("")

    lines.append("## Signal detection (per judge x actual x stated)")
    lines.append("")
    lines.append("| judge | actual | stated | hits | FA | HR | FAR | d' | criterion |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for row in summ["signal_detection"]:
        lines.append(f"| {row['judge']} | {row['actual_architecture']} | {row['stated_architecture']} | "
                     f"{row['self_hits']} | {row['false_alarms']} | "
                     f"{row['hit_rate']:.3f} | {row['false_alarm_rate']:.3f} | "
                     f"{row['d_prime']:+.3f} | {row['criterion']:+.3f} |")
    lines.append("")

    lines.append("## Baselines")
    lines.append("")
    lines.append("### Source-model 3-way classifier (leave-one-out nearest centroid on features)")
    if clf_batch: lines.append(f"- batch: {clf_batch['accuracy']:.3f} (n={clf_batch['n']})")
    if clf_online: lines.append(f"- online: {clf_online['accuracy']:.3f} (n={clf_online['n']})")
    lines.append("")
    lines.append("### Architecture-conditioned feature baseline")
    lines.append("For each trial, uses features_of(trajectory) and compares against the")
    lines.append("judge's own model centroid **under the STATED architecture**. Then predicts")
    lines.append("SELF/OTHER by which model centroid the trajectory is closest to under the")
    lines.append("stated arch. If judge behavior mirrors this rule, the judge is behaving")
    lines.append("as a stated-arch-conditioned feature classifier.")
    lines.append("")
    lines.append("| stated arch | n | feature rule accuracy vs ground truth | judge agrees with rule |")
    lines.append("|---|---|---|---|")
    for arch, v in base["per_stated_arch"].items():
        lines.append(f"| {arch} | {v['n']} | {v['feature_rule_accuracy']:.3f} | "
                     f"{v['judge_agrees_with_feature_rule_rate']:.3f} |")
    lines.append("")

    # Outcome classification
    ss = summ["self_specific_provenance_effect"]
    sig_self_specific = any(r["self_specific_provenance_effect"] >= 0.15 for r in ss if r["self_specific_provenance_effect"] == r["self_specific_provenance_effect"])
    sig_congruence_generic = any(abs(r["congruence_advantage"]) >= 0.10 for r in summ["congruence"] if r["congruence_advantage"] == r["congruence_advantage"])
    accs = [r["accuracy"] for r in summ["cells"] if r["accuracy"] == r["accuracy"]]
    any_above_chance = any(a >= 0.65 for a in accs)
    # simple label:
    if not any_above_chance:
        outcome = "G"; desc = "No SELF/OTHER performance meaningfully above chance."
    elif sig_self_specific:
        outcome = "D"; desc = ("Congruent provenance disproportionately improves SELF attribution — "
                                "key positive SPAR pattern (self-specific provenance effect).")
    elif sig_congruence_generic:
        outcome = "C"; desc = "Congruent provenance improves SELF and OTHER accuracy similarly (generic)."
    else:
        outcome = "A"; desc = "Actual architecture matters; stated provenance has little effect."
    lines.append("## Predefined outcome classification")
    lines.append("")
    lines.append(f"**Outcome {outcome}**: {desc}")
    lines.append("")

    lines.append("## Interpretation caveats")
    lines.append("")
    lines.append("- 10 trials per cell; accuracy granularity within a cell is 0.10.")
    lines.append("- A positive self-specific provenance effect is the key SPAR pattern; a")
    lines.append("  generic congruence effect is not evidence for a behavioral self-model.")
    lines.append("- Do not describe positive results as self-awareness, consciousness, or introspection.")
    lines.append("- Baselines above (source-model classifier and architecture-conditioned feature")
    lines.append("  baseline) provide feature-based upper bounds against which to weigh judge behavior.")

    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _write_stop(paths, phase, reason, spent):
    with open(os.path.join(paths.root, "OVERNIGHT_RUN_STOPPED.md"), "w") as f:
        f.write(f"# Overnight run stopped\n\n- run_id: {paths.run_id}\n- phase: {phase}\n"
                f"- spend_so_far_usd: ${spent:.4f}\n- reason: {reason}\n"
                f"- resume: rerun with --run-id {paths.run_id} --skip-smoke (idempotent)\n")


def _write_complete(paths, spent, report_path):
    with open(os.path.join(paths.root, "OVERNIGHT_RUN_COMPLETE.md"), "w") as f:
        f.write(f"# Overnight run complete\n\n- run_id: {paths.run_id}\n"
                f"- total_spend_usd: ${spent:.4f}\n- completed_utc: {_now_stamp()}\n"
                f"- final_report: {report_path}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", required=True)
    ap.add_argument("--yes", action="store_true", required=True)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--data-root", default="data/spar_dynamic")
    ap.add_argument("--source-run-root", required=True)
    ap.add_argument("--skip-smoke", action="store_true")
    args = ap.parse_args()

    run_id = args.run_id or ("spar-provenance-" + _now_stamp())
    paths = RunPaths(args.data_root, run_id); paths.ensure()
    log, log_file = _log_writer(os.path.join(paths.logs, "orchestrator_provenance.log"))
    log(f"START run_id={run_id}  source_run_root={args.source_run_root}")

    try:
        client = make_client()
        accountant = CostAccountant(client)
        catalog = accountant.snapshot_catalog()
        missing = [m.slug for m in C.MODELS if m.slug not in catalog]
        if missing:
            log(f"ABORT: missing model(s): {missing}")
            _write_stop(paths, "model_missing", f"missing: {missing}", accountant.spent_usd)
            return
        write_json(paths.catalog, catalog)

        if not args.skip_smoke:
            log("PHASE: smoke")
            smoke = phase_smoke(client, accountant, log)
            proj = project_full_cost(smoke, accountant)
            log(f"  cost projection: total=${proj['projected_total_usd']:.4f} "
                f"budget=${proj['budget_usd']:.2f}")
            write_json(os.path.join(paths.smoke, "smoke_records.json"), smoke)
            write_json(os.path.join(paths.smoke, "cost_projection.json"), proj)
            if proj["projected_total_usd"] > C.PROVENANCE_STOP_AT_PROJECTED_USD:
                log(f"ABORT: projected > cap")
                _write_stop(paths, "budget_projection_exceeded",
                            f"projected {proj['projected_total_usd']:.4f}",
                            accountant.spent_usd)
                return

        write_json(paths.manifest, {"run_id": run_id, "experiment_tag": C.PROVENANCE_TAG,
                                    "source_run_root": args.source_run_root,
                                    "started_utc": _now_stamp(),
                                    "budget_usd": C.PROVENANCE_BUDGET_USD})

        log("PHASE: trial construction")
        trials = phase_trials(paths, args.source_run_root, log)
        log("PHASE: judgment")
        phase_judgment(client, accountant, paths, trials, log)
        log("PHASE: validate")
        val = phase_validate(paths, trials, log)
        log(f"  validation: {val}")
        log("PHASE: analysis + report")
        phase_analysis(paths, args.source_run_root, log, accountant, val)

        report_path = os.path.join(paths.results, "PROVENANCE_SELF_ATTRIBUTION_REPORT.md")
        if val["run_complete_ok"]:
            log(f"COMPLETE total_spend=${accountant.spent_usd:.4f}")
            _write_complete(paths, accountant.spent_usd, report_path)
        else:
            log(f"STOP: validation not clean.")
            _write_stop(paths, "validation_incomplete",
                        f"n_abandoned={val['n_abandoned']} cell_counts_ok={val['cell_counts_ok']}",
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
