"""Orchestrator for Pilot 2 — SELF vs OTHER attribution.

Run:
  python -m spar_dynamic.orchestrator_self_other \\
    --live --yes \\
    --source-run-root data/spar_dynamic/spar-dynamic-run-20260929T081814Z \\
    [--run-id <id>] [--skip-smoke]

Reuses the source trajectories from an existing pilot-1 run root, builds a
deterministic 120-trial manifest, runs judgment calls with plain-text
SELF/OTHER parsing, retries invalids, and produces the SELF_OTHER_PILOT_REPORT.

VALIDATION RULE: the run is labeled COMPLETE only when every planned trial
has a valid parsed judgment. Any abandoned trial produces an OVERNIGHT_RUN_STOPPED
marker with the abandoned-trial count explicit.
"""

import argparse, csv, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from typing import Dict, List, Tuple

from . import config as C
from .api import CostAccountant, call_model, make_client, BudgetExceeded, parse_self_other
from .analyze import (sequence_features, summarize_self_other,
                      self_other_dynamic_gain,
                      self_other_feature_distance,
                      self_other_loo_classifier,
                      nearest_centroid_loo, FEATURE_NAMES)
from .self_other import (build_self_other_trials, load_source_trajectories,
                          judge_one_trial, judgment_prompt, SelfOtherTrial)
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
    """One tiny judgment call per judge on a disposable trajectory. Records go
    into the smoke dir so they don't contaminate experimental data."""
    disposable = "HTHHTHTTHTHHTTHTHHTTHHTHTHTHHTHTHHTHHTHTHTHTHTHTHT"  # 50 chars, disposable
    prompt = judgment_prompt(disposable)
    out = []
    for m in C.MODELS:
        r = call_model(client, accountant, kind="smoke", slug=m.slug,
                       prompt_text=prompt, max_tokens=C.SELF_OTHER_MAX_TOKENS,
                       response_format=None)
        parsed = parse_self_other(r.response_text)
        out.append({"model": m.label, "raw": r.response_text, "parsed": parsed,
                    "cost_usd": r.cost_usd, "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                    "reasoning_tokens": r.reasoning_tokens,
                    "finish_reason": r.finish_reason,
                    "latency_ms": r.latency_ms,
                    "error_message": r.error_message})
        log(f"  smoke {m.label}: raw={r.response_text!r} parsed={parsed!r} "
            f"cost=${r.cost_usd:.4f} tokens p={r.prompt_tokens}/c={r.completion_tokens}/r={r.reasoning_tokens}")
    return out


def project_full_cost(smoke_records, accountant, n_planned=120) -> Dict:
    total_smoke_cost = sum(r["cost_usd"] for r in smoke_records)
    avg = total_smoke_cost / len(smoke_records) if smoke_records else 0.0
    # weighted-average projection: 40 trials per judge, 3 judges
    per_judge_avg = {r["model"]: r["cost_usd"] for r in smoke_records}
    projected_judgment = 0.0
    for m in C.MODELS:
        # 40 trials per judge; add some retry overhead (assume avg 1.15 attempts/trial)
        projected_judgment += per_judge_avg.get(m.label, avg) * 40 * 1.15
    total = accountant.spent_usd + projected_judgment
    return {"spent_so_far": accountant.spent_usd,
            "projected_judgment_usd": projected_judgment,
            "projected_total_usd": total,
            "budget_usd": C.SELF_OTHER_BUDGET_USD}


def phase_trials(paths: RunPaths, source_run_root: str, log) -> List[SelfOtherTrial]:
    manifest_path = os.path.join(paths.trials, "self_other_trial_manifest.json")
    existing = read_json(manifest_path)
    if existing:
        log(f"  resume: {len(existing)} trials on disk")
        return [SelfOtherTrial(**t) for t in existing]
    src = load_source_trajectories(source_run_root)
    # sanity: full 60
    for (arch, ml), lst in src.items():
        if len(lst) < C.SELF_OTHER_TRIALS_PER_LABEL:
            raise RuntimeError(f"insufficient source trajectories for ({arch}, {ml}): "
                               f"{len(lst)}")
    trials = build_self_other_trials(src)
    write_json(manifest_path, [asdict(t) for t in trials])
    log(f"  wrote {len(trials)} trials to {manifest_path}")
    return trials


def phase_judgment(client, accountant, paths: RunPaths,
                   trials: List[SelfOtherTrial], log):
    slug_by_label = {m.label: m.slug for m in C.MODELS}
    def _done(t):
        p = os.path.join(paths.judgment, f"selfother-{t.trial_id}.json")
        if os.path.exists(p):
            rec = read_json(p)
            if rec and rec.get("trial_status") in ("ok", "abandoned"):
                return True
        return False
    pending = [t for t in trials if not _done(t)]
    log(f"  {len(pending)} trials pending of {len(trials)}")

    def _do(t: SelfOtherTrial):
        slug = slug_by_label[t.judge_label]
        rec = judge_one_trial(client, accountant, t, slug)
        p = os.path.join(paths.judgment, f"selfother-{t.trial_id}.json")
        write_json(p, asdict(rec))
        return rec

    with ThreadPoolExecutor(max_workers=C.JUDGMENT_CONCURRENCY) as pool:
        futures = {pool.submit(_do, t): t.trial_id for t in pending}
        n_done = 0
        for fut in as_completed(futures):
            r = fut.result(); n_done += 1
            if n_done % 10 == 0 or n_done == len(pending):
                log(f"  judgment {n_done}/{len(pending)}: latest "
                    f"{r.judge_label}/{r.architecture} correct_answer={r.correct_answer} "
                    f"parsed={r.parsed_judgment!r} correct={r.correct} "
                    f"status={r.trial_status} spent=${accountant.spent_usd:.4f}")


def phase_validate(paths: RunPaths, trials: List[SelfOtherTrial], log) -> Dict:
    """Return a dict indicating whether the run is complete. If any trial is
    abandoned, we do NOT mark COMPLETE — spec-mandated fix."""
    n_planned = len(trials)
    records = []
    for t in trials:
        p = os.path.join(paths.judgment, f"selfother-{t.trial_id}.json")
        if not os.path.exists(p):
            log(f"  MISSING record for trial {t.trial_id}")
            continue
        records.append(read_json(p))
    n_valid = sum(1 for r in records if r.get("valid"))
    n_abandoned = sum(1 for r in records if r.get("trial_status") == "abandoned")
    ok = (len(records) == n_planned) and (n_valid == n_planned) and (n_abandoned == 0)
    result = {"n_planned": n_planned, "n_records": len(records),
              "n_valid": n_valid, "n_abandoned": n_abandoned,
              "run_complete_ok": ok}
    write_json(os.path.join(paths.results, "validation_report.json"), result)
    return result


def phase_analysis(paths: RunPaths, source_run_root: str, log, accountant, val: Dict):
    # Read all records
    records = []
    for fn in sorted(os.listdir(paths.judgment)):
        if not fn.startswith("selfother-"): continue
        rec = read_json(os.path.join(paths.judgment, fn))
        if rec: records.append(rec)

    # Source features (from the reused source-run root)
    src = load_source_trajectories(source_run_root)
    features_by_traj: Dict[str, Dict[str, float]] = {}
    source_by_arch_model: Dict[Tuple[str, str], List[Dict[str, float]]] = {}
    for (arch, ml), lst in src.items():
        source_by_arch_model[(arch, ml)] = []
        for (_, tid, seq) in lst:
            f = sequence_features(seq)
            features_by_traj[tid] = f
            source_by_arch_model[(arch, ml)].append(f)

    # Source-model 3-way classifier per architecture (reproduces prior finding)
    def _feats_by_model(arch):
        return {ml: source_by_arch_model.get((arch, ml), []) for ml in C.MODEL_LABELS}
    clf_batch = None; clf_online = None
    if all(len(_feats_by_model("batch")[ml]) >= 2 for ml in C.MODEL_LABELS):
        clf_batch = nearest_centroid_loo(_feats_by_model("batch"))
    if all(len(_feats_by_model("online")[ml]) >= 2 for ml in C.MODEL_LABELS):
        clf_online = nearest_centroid_loo(_feats_by_model("online"))

    # Judgment summary
    summ = summarize_self_other(records)
    dynamic = self_other_dynamic_gain(summ["per_ja"])
    fd = self_other_feature_distance(records, features_by_traj, source_by_arch_model)
    loo = self_other_loo_classifier(source_by_arch_model)

    # CSVs
    _write_csv(os.path.join(paths.results, "trial_level.csv"),
               [{k: v for k, v in r.items()
                 if k not in ("sequence_display", "prompt_text",
                              "raw_completion", "attempt_records")}
                for r in records])
    _write_csv(os.path.join(paths.results, "judge_summary.csv"),
               list(summ["per_ja"].values()))
    _write_csv(os.path.join(paths.results, "other_source_breakdown.csv"),
               summ["per_other_source"])
    _write_csv(os.path.join(paths.results, "architecture_contrast.csv"), dynamic)
    _write_csv(os.path.join(paths.results, "feature_distance_per_trial.csv"),
               fd["trial_rows"])
    _write_csv(os.path.join(paths.results, "feature_distance_per_arch.csv"),
               [{"architecture": a, **v} for a, v in fd["per_arch"].items()])
    _write_csv(os.path.join(paths.results, "self_other_feature_classifier_baseline.csv"),
               loo["rows"])

    # Report
    _write_report(paths, accountant, val, summ, dynamic, fd, loo,
                  clf_batch, clf_online, records)


def _write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        return
    keys = []; seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen: keys.append(k); seen.add(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows: w.writerow(r)


def _write_report(paths, accountant, val, summ, dynamic, fd, loo,
                  clf_batch, clf_online, records):
    p = os.path.join(paths.results, "SELF_OTHER_PILOT_REPORT.md")
    lines = []
    lines.append("# SPAR Pilot 2 — SELF vs OTHER Attribution")
    lines.append("")
    lines.append(f"Run root: `{paths.root}`")
    lines.append(f"Experiment tag: `{C.SELF_OTHER_TAG}`")
    lines.append(f"Total spend: **${accountant.spent_usd:.4f}** / ${C.SELF_OTHER_BUDGET_USD:.2f} cap")
    lines.append("")
    lines.append("## Design")
    lines.append("")
    lines.append("Single trajectory per trial. Judge decides SELF (produced by the same")
    lines.append("underlying model as itself) or OTHER (produced by a different model).")
    lines.append("Uses the exact 60 source trajectories from the pilot-1 dynamic run.")
    lines.append("Plain-text one-word response (SELF or OTHER); no JSON schema.")
    lines.append("")
    lines.append(f"- 10 SELF trials + 10 OTHER trials per (judge x architecture)")
    lines.append(f"- 24 (per judge x arch) x 3 judges x 2 archs = **120 total trials**")
    lines.append(f"- OTHER trials split evenly: 5 from each non-self model")
    lines.append(f"- SELF trials use every one of the judge's own 10 trajectories exactly once")
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

    lines.append("## Primary results — per judge x architecture")
    lines.append("")
    lines.append("| judge | arch | n_valid | acc | balanced_acc | SELF hit | OTHER CR | SELF rate | d' | criterion |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for judge in C.MODEL_LABELS:
        for arch in C.ARCHITECTURES:
            r = summ["per_ja"].get((judge, arch))
            if not r:
                lines.append(f"| {judge} | {arch} | - | - | - | - | - | - | - | - |")
                continue
            lines.append(
                "| {j} | {a} | {n} | {acc:.3f} | {ba:.3f} | {sh:.3f} | {oc:.3f} | "
                "{sr:.3f} | {d:+.3f} | {c:+.3f} |".format(
                    j=r["judge"], a=r["architecture"], n=r["n_valid"],
                    acc=r["accuracy"], ba=r["balanced_accuracy"],
                    sh=r["self_hit_rate"], oc=r["other_cr_rate"],
                    sr=r["self_response_rate"], d=r["d_prime"], c=r["criterion"]))
    lines.append("")

    lines.append("## Architecture contrast per judge")
    lines.append("")
    lines.append("| judge | batch BA | online BA | Δ BA | batch d' | online d' | Δ d' |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in dynamic:
        lines.append(
            "| {j} | {bb:.3f} | {ob:.3f} | {db:+.3f} | {bd:+.3f} | {od:+.3f} | {dd:+.3f} |".format(
                j=row["judge"], bb=row["balanced_accuracy_batch"], ob=row["balanced_accuracy_online"],
                db=row["dynamic_gain_balanced_accuracy"], bd=row["d_prime_batch"],
                od=row["d_prime_online"], dd=row["dynamic_gain_d_prime"]))
    lines.append("")

    lines.append("## OTHER-source breakdown")
    lines.append("")
    lines.append("| judge | arch | other source | n | correct OTHER | OTHER CR rate |")
    lines.append("|---|---|---|---|---|---|")
    for row in summ["per_other_source"]:
        lines.append(f"| {row['judge']} | {row['architecture']} | {row['other_source_model']} | "
                     f"{row['n']} | {row['n_correct_other']} | {row['other_cr_rate']:.3f} |")
    lines.append("")

    lines.append("## Baselines")
    lines.append("")
    lines.append("### Source-model 3-way classifier (leave-one-out nearest centroid on features)")
    if clf_batch:
        lines.append(f"- batch: {clf_batch['accuracy']:.3f} (n={clf_batch['n']})")
    if clf_online:
        lines.append(f"- online: {clf_online['accuracy']:.3f} (n={clf_online['n']})")
    lines.append("")
    lines.append("### SELF/OTHER binary feature classifier (per judge x arch, LOO)")
    lines.append("| judge | arch | self hit | other CR | balanced acc |")
    lines.append("|---|---|---|---|---|")
    for row in loo["rows"]:
        lines.append(f"| {row['judge']} | {row['architecture']} | "
                     f"{row['self_hit_rate']:.3f} | {row['other_cr_rate']:.3f} | "
                     f"{row['balanced_accuracy']:.3f} |")
    lines.append("")
    lines.append("### Judge-response vs nearest-centroid agreement (per architecture)")
    lines.append("Rows: agreement between LLM judge's SELF/OTHER response and the answer given by a")
    lines.append("simple 'closer to your own model's centroid → SELF' rule.")
    lines.append("")
    lines.append("| arch | n | judge agrees w/ nearest-centroid rule | rule accuracy vs ground truth |")
    lines.append("|---|---|---|---|")
    for arch, v in fd["per_arch"].items():
        lines.append(f"| {arch} | {v['n']} | {v['agreement_rate']:.3f} | "
                     f"{v['nearest_centroid_rule_accuracy']:.3f} |")
    lines.append("")

    # Interpretation via predefined Outcome A-G
    def _above_chance(ba, n, delta=0.10):
        # descriptive: >= 0.5 + delta counts as "above chance" for this pilot
        return not (ba != ba) and ba >= 0.5 + delta
    per = summ["per_ja"]
    batch_bas = [per[(j, "batch")]["balanced_accuracy"] for j in C.MODEL_LABELS if (j, "batch") in per]
    online_bas = [per[(j, "online")]["balanced_accuracy"] for j in C.MODEL_LABELS if (j, "online") in per]
    any_batch = any(_above_chance(b, 20) for b in batch_bas)
    any_online = any(_above_chance(b, 20) for b in online_bas)
    all_batch = all(_above_chance(b, 20) for b in batch_bas) if batch_bas else False
    all_online = all(_above_chance(b, 20) for b in online_bas) if online_bas else False
    outcome = "A"; desc = "Batch and online both near chance."
    if not any_batch and any_online:
        outcome = "B"; desc = "Batch near chance; online above chance."
    elif all_online and all_batch:
        outcome = "C"; desc = "Both above chance."
    if outcome != "A" and any_online:
        # compare online LLM to feature classifier on online
        online_llm_avg = sum(online_bas) / len(online_bas)
        loo_online = [r["balanced_accuracy"] for r in loo["rows"] if r["architecture"] == "online"]
        if loo_online:
            loo_online_avg = sum(loo_online) / len(loo_online)
            if online_llm_avg <= loo_online_avg + 0.05:
                outcome = "D"; desc = ("Online LLM above chance but no better than the "
                                        "matched feature classifier — likely ordinary phenotype classification.")
            elif online_llm_avg >= loo_online_avg + 0.10:
                outcome = "E"; desc = ("Online LLM substantially exceeds the matched feature "
                                        "classifier. Potentially uses richer model-specific information "
                                        "than obvious sequence statistics.")
    lines.append("## Predefined outcome classification")
    lines.append("")
    lines.append(f"**Outcome {outcome}**: {desc}")
    lines.append("")

    lines.append("## Interpretation caveats")
    lines.append("")
    lines.append("- 10 SELF + 10 OTHER trials per (judge x arch); accuracy granularity 1/20 = 0.05.")
    lines.append("- Above-chance SELF/OTHER attribution does NOT demonstrate privileged self-specific")
    lines.append("  processing. Compare against the feature-based baselines above.")
    lines.append("- Do not describe positive results as self-awareness, consciousness, introspection, or self-recognition.")
    lines.append("- A named-OTHER attribution control belongs in a separate future pilot; not included here.")

    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _write_stop(paths, phase, reason, spent):
    with open(os.path.join(paths.root, "OVERNIGHT_RUN_STOPPED.md"), "w") as f:
        f.write(f"# Overnight run stopped\n\n"
                f"- run_id: {paths.run_id}\n"
                f"- phase: {phase}\n"
                f"- spend_so_far_usd: ${spent:.4f}\n"
                f"- reason: {reason}\n"
                f"- resume: rerun `python -m spar_dynamic.orchestrator_self_other --live --yes "
                f"--run-id {paths.run_id} --skip-smoke --source-run-root <same-source-run>` (idempotent)\n")


def _write_complete(paths, spent):
    with open(os.path.join(paths.root, "OVERNIGHT_RUN_COMPLETE.md"), "w") as f:
        f.write(f"# Overnight run complete\n\n"
                f"- run_id: {paths.run_id}\n"
                f"- total_spend_usd: ${spent:.4f}\n"
                f"- completed_utc: {_now_stamp()}\n"
                f"- final_report: {os.path.join(paths.results, 'SELF_OTHER_PILOT_REPORT.md')}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", required=True)
    ap.add_argument("--yes", action="store_true", required=True)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--data-root", default="data/spar_dynamic")
    ap.add_argument("--source-run-root", required=True,
                    help="path to the pilot-1 source run root (must contain source/{batch,online}/...)")
    ap.add_argument("--skip-smoke", action="store_true")
    args = ap.parse_args()

    run_id = args.run_id or ("spar-self-other-" + _now_stamp())
    paths = RunPaths(args.data_root, run_id); paths.ensure()
    log, log_file = _log_writer(os.path.join(paths.logs, "orchestrator_self_other.log"))
    log(f"START run_id={run_id}  source_run_root={args.source_run_root}")

    try:
        client = make_client()
        accountant = CostAccountant(client)
        log("  fetching OpenRouter model catalog + pricing snapshot")
        catalog = accountant.snapshot_catalog()
        missing = [m.slug for m in C.MODELS if m.slug not in catalog]
        if missing:
            log(f"ABORT: missing model(s) from catalog: {missing}")
            _write_stop(paths, "model_missing", f"missing: {missing}", accountant.spent_usd)
            return
        write_json(paths.catalog, catalog)

        if not args.skip_smoke:
            log("PHASE: smoke")
            smoke = phase_smoke(client, accountant, log)
            proj = project_full_cost(smoke, accountant)
            log(f"  cost projection: spent=${proj['spent_so_far']:.4f} "
                f"projected_judgment=${proj['projected_judgment_usd']:.4f} "
                f"total=${proj['projected_total_usd']:.4f} budget=${proj['budget_usd']:.2f}")
            write_json(os.path.join(paths.smoke, "smoke_records.json"), smoke)
            write_json(os.path.join(paths.smoke, "cost_projection.json"), proj)
            if proj["projected_total_usd"] > C.SELF_OTHER_STOP_AT_PROJECTED_USD:
                log(f"ABORT: projected total ${proj['projected_total_usd']:.2f} > cap")
                _write_stop(paths, "budget_projection_exceeded",
                            f"projected {proj['projected_total_usd']:.4f} > cap",
                            accountant.spent_usd)
                return

        write_json(paths.manifest, {"run_id": run_id, "experiment_tag": C.SELF_OTHER_TAG,
                                    "source_run_root": args.source_run_root,
                                    "started_utc": _now_stamp(),
                                    "budget_usd": C.SELF_OTHER_BUDGET_USD})

        log("PHASE: trial construction")
        trials = phase_trials(paths, args.source_run_root, log)
        log("PHASE: judgment")
        phase_judgment(client, accountant, paths, trials, log)
        log("PHASE: validate")
        val = phase_validate(paths, trials, log)
        log(f"  validation: {val}")
        log("PHASE: analysis + report")
        phase_analysis(paths, args.source_run_root, log, accountant, val)

        if val["run_complete_ok"]:
            log(f"COMPLETE total_spend=${accountant.spent_usd:.4f}")
            _write_complete(paths, accountant.spent_usd)
        else:
            log(f"STOP: run had abandoned trials — NOT labeling COMPLETE per spec.")
            _write_stop(paths, "validation_incomplete",
                        f"n_abandoned={val['n_abandoned']} of n_planned={val['n_planned']}",
                        accountant.spent_usd)
    except BudgetExceeded as e:
        log(f"BUDGET STOP: {e}")
        _write_stop(paths, "budget_cap_hit_during_run", str(e), accountant.spent_usd)
    except Exception as e:
        import traceback
        log(f"FATAL {type(e).__name__}: {e}\n{traceback.format_exc()}")
        try: spent = accountant.spent_usd
        except Exception: spent = 0.0
        _write_stop(paths, "fatal_exception", f"{type(e).__name__}: {e}", spent)
    finally:
        try: log_file.close()
        except Exception: pass


if __name__ == "__main__":
    main()
