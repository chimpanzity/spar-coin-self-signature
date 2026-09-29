"""Orchestrator for Pilot 4 — Astra provenance replication with no-provenance control.

Run:
  python -m spar_dynamic.orchestrator_astra_followup --live --yes \\
    [--run-id <id>] [--skip-smoke]

Phases (all resume-safe):
  1. catalog snapshot + model verification
  2. smoke test (2 sources per model + 3 judgment calls, disposable)
  3. cost projection
  4. fresh source generation (astra 10/10, fable 5/5, qwen 5/5) — batch then online
  5. source validation
  6. trial construction (120 = 40 x 3)
  7. 120 judgments
  8. strict validation — refuses COMPLETE if any abandoned trial or cell short
  9. analysis + report + FINAL marker
"""

import argparse, csv, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from typing import Dict, List, Tuple

from . import config as C
from .api import CostAccountant, call_model, make_client, BudgetExceeded, parse_self_other
from .analyze import (sequence_features, summarize_astra_followup,
                      distance_to_astra_per_trial,
                      nearest_centroid_loo, FEATURE_NAMES)
from .astra_followup import (build_trials, judge_one_trial, load_pilot4_sources,
                              AstraFollowupTrial, JUDGE_SLUG, ASTRA_LABEL)
from .source import generate_batch_source, generate_online_source
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
    """Small smoke: 1 batch source per model + 1 judgment call per stated condition."""
    from .api import parse_batch, parse_online
    from .source import _existing_valid_trajectory_ids
    smoke_records = []
    for m in C.MODELS:
        r = call_model(client, accountant, kind="smoke", slug=m.slug,
                       prompt_text=C.BATCH_PROMPT, max_tokens=C.BATCH_MAX_TOKENS)
        parsed = parse_batch(r.response_text)
        smoke_records.append({"phase": f"batch_{m.label}",
                              "valid": bool(parsed),
                              "cost_usd": r.cost_usd, "prompt_tokens": r.prompt_tokens,
                              "completion_tokens": r.completion_tokens,
                              "reasoning_tokens": r.reasoning_tokens})
        log(f"  smoke batch/{m.label}: valid={bool(parsed)} cost=${r.cost_usd:.4f}")
    disposable = "HTHHTHTTHTHHTTHTHHTTHHTHTHTHHTHTHHTHHTHTHTHTHTHTHT"
    for stated in C.STATED_CONDITIONS:
        prompt = C.astra_followup_prompt(disposable, stated)
        r = call_model(client, accountant, kind="smoke", slug=JUDGE_SLUG,
                       prompt_text=prompt, max_tokens=C.ASTRA_FOLLOWUP_MAX_TOKENS,
                       response_format=None)
        parsed = parse_self_other(r.response_text)
        smoke_records.append({"phase": f"judgment_{stated}",
                              "parsed": parsed,
                              "cost_usd": r.cost_usd,
                              "prompt_tokens": r.prompt_tokens,
                              "completion_tokens": r.completion_tokens,
                              "reasoning_tokens": r.reasoning_tokens})
        log(f"  smoke judgment {stated}: parsed={parsed!r} cost=${r.cost_usd:.4f} "
            f"c/r={r.completion_tokens}/{r.reasoning_tokens}")
    return smoke_records


def project_full_cost(smoke_records, accountant) -> Dict:
    # rough projection: sum of expected source calls * observed per-call costs
    batch_cost_by_model = {}
    for m in C.MODELS:
        # find the smoke batch cost for this model
        r = next((r for r in smoke_records if r["phase"] == f"batch_{m.label}"), None)
        batch_cost_by_model[m.label] = r["cost_usd"] if r else 0.0
    judgment_avg = 0.0
    j = [r for r in smoke_records if r["phase"].startswith("judgment_")]
    if j:
        judgment_avg = sum(r["cost_usd"] for r in j) / len(j)
    # source projection: astra=10+10=20, fable=5+5=10, qwen=5+5=10
    # batch is cheap; online is 50 calls per trajectory but each is a tiny prompt+response
    # use batch as a proxy for online per-step cost estimate (rough)
    projected_source = 0.0
    for m in C.MODELS:
        n_batch = C.ASTRA_FOLLOWUP_SOURCE_COUNTS[m.label]
        n_online_steps = C.ASTRA_FOLLOWUP_SOURCE_COUNTS[m.label] * 50
        projected_source += batch_cost_by_model[m.label] * n_batch
        # online single-flip calls cost < batch calls; use 0.3x batch as an estimate
        projected_source += batch_cost_by_model[m.label] * 0.3 * n_online_steps
    # judgments: 120 calls at astra judgment avg
    projected_judgment = judgment_avg * 120 * 1.10  # small retry overhead
    total = accountant.spent_usd + projected_source + projected_judgment
    return {"spent_so_far": accountant.spent_usd,
            "projected_source_usd": projected_source,
            "projected_judgment_usd": projected_judgment,
            "projected_total_usd": total,
            "budget_usd": C.ASTRA_FOLLOWUP_BUDGET_USD}


def phase_source(client, accountant, paths: RunPaths, log):
    log("PHASE: fresh source generation (astra 10/10, fable 5/5, qwen 5/5)")
    # BATCH first (fast)
    for m in C.MODELS:
        generate_batch_source(client, accountant, paths, m, log=log,
                              valid_needed=C.ASTRA_FOLLOWUP_SOURCE_COUNTS[m.label])
    # ONLINE (concurrent trajectories, sequential steps within each)
    from .source import generate_online_trajectory
    tasks = []
    for m in C.MODELS:
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
        needed = C.ASTRA_FOLLOWUP_SOURCE_COUNTS[m.label] - existing_valid
        start_index = (max(existing_indices) + 1) if existing_indices else 0
        for i in range(needed):
            tasks.append((m, start_index + i))
    with ThreadPoolExecutor(max_workers=C.SOURCE_CONCURRENCY) as pool:
        futures = {pool.submit(generate_online_trajectory, client, accountant,
                                paths, m, idx, log=log): (m.label, idx)
                    for (m, idx) in tasks}
        for fut in as_completed(futures):
            fut.result()


def phase_validate_sources(paths: RunPaths, log) -> Dict:
    counts = {}
    for arch in C.ARCHITECTURES:
        for m in C.MODELS:
            d = os.path.join(paths.source_batch if arch == "batch" else paths.source_online,
                             m.label)
            if not os.path.isdir(d):
                counts[(arch, m.label)] = 0; continue
            n = 0
            for fn in os.listdir(d):
                if fn.endswith(".json") and ".steps." not in fn:
                    rec = read_json(os.path.join(d, fn))
                    if rec and rec.get("valid"):
                        n += 1
            counts[(arch, m.label)] = n
    ok = True
    for m in C.MODELS:
        need = C.ASTRA_FOLLOWUP_SOURCE_COUNTS[m.label]
        for arch in C.ARCHITECTURES:
            got = counts[(arch, m.label)]
            if got < need:
                log(f"  source short: {arch}/{m.label} = {got} of {need}")
                ok = False
    return {"counts": {f"{a}/{m}": v for (a, m), v in counts.items()},
            "sources_ok": ok}


def phase_trials(paths: RunPaths, log) -> List[AstraFollowupTrial]:
    manifest_path = os.path.join(paths.trials, "astra_followup_trial_manifest.json")
    existing = read_json(manifest_path)
    if existing:
        log(f"  resume: {len(existing)} trials on disk")
        return [AstraFollowupTrial(**t) for t in existing]
    sources = load_pilot4_sources(paths.root)
    # Trim OTHER pool to exactly N per (model, arch) so we don't accidentally overinclude
    # if source phase produced extras. (Ordering is deterministic from load_pilot4_sources.)
    trimmed = []
    per_cell_taken = {}
    for (ml, arch, tid, seq) in sources:
        key = (arch, ml)
        n_taken = per_cell_taken.get(key, 0)
        cap = C.ASTRA_FOLLOWUP_SOURCE_COUNTS[ml]
        if n_taken >= cap:
            continue
        trimmed.append((ml, arch, tid, seq))
        per_cell_taken[key] = n_taken + 1
    log(f"  sources loaded: {len(trimmed)} (astra "
        f"{sum(1 for x in trimmed if x[0]=='astra')}, others "
        f"{sum(1 for x in trimmed if x[0]!='astra')})")
    trials = build_trials(trimmed)
    write_json(manifest_path, [asdict(t) for t in trials])
    log(f"  wrote {len(trials)} trials")
    return trials


def phase_judgment(client, accountant, paths: RunPaths,
                   trials: List[AstraFollowupTrial], log):
    def _done(t):
        p = os.path.join(paths.judgment, f"astraf-{t.trial_id}.json")
        if os.path.exists(p):
            rec = read_json(p)
            if rec and rec.get("trial_status") in ("ok", "abandoned"):
                return True
        return False
    pending = [t for t in trials if not _done(t)]
    log(f"  {len(pending)} pending of {len(trials)}")

    def _do(t: AstraFollowupTrial):
        rec = judge_one_trial(client, accountant, t)
        write_json(os.path.join(paths.judgment, f"astraf-{t.trial_id}.json"), asdict(rec))
        return rec

    with ThreadPoolExecutor(max_workers=C.JUDGMENT_CONCURRENCY) as pool:
        futures = {pool.submit(_do, t): t.trial_id for t in pending}
        n_done = 0
        for fut in as_completed(futures):
            r = fut.result(); n_done += 1
            if n_done % 10 == 0 or n_done == len(pending):
                log(f"  judgment {n_done}/{len(pending)}: {r.true_source_identity}/"
                    f"actual={r.actual_architecture}/{r.stated_condition} "
                    f"parsed={r.parsed_judgment!r} correct={r.correct} "
                    f"status={r.trial_status} spent=${accountant.spent_usd:.4f}")


def phase_validate(paths: RunPaths, trials: List[AstraFollowupTrial], log) -> Dict:
    n_planned = len(trials)
    records = []
    for t in trials:
        p = os.path.join(paths.judgment, f"astraf-{t.trial_id}.json")
        if not os.path.exists(p):
            log(f"  MISSING record for {t.trial_id}")
            continue
        records.append(read_json(p))
    n_valid = sum(1 for r in records if r.get("valid"))
    n_abandoned = sum(1 for r in records if r.get("trial_status") == "abandoned")
    from collections import Counter
    cell_counter = Counter((r["true_source_identity"], r["actual_architecture"], r["stated_condition"])
                            for r in records if r.get("valid"))
    cell_ok = True
    for identity in ("SELF", "OTHER"):
        for arch in C.ARCHITECTURES:
            for stated in C.STATED_CONDITIONS:
                need = 10
                got = cell_counter[(identity, arch, stated)]
                if got != need:
                    log(f"  cell short: {identity}/{arch}/{stated} = {got}"); cell_ok = False
    ok = (len(records) == n_planned and n_valid == n_planned and n_abandoned == 0 and cell_ok)
    result = {"n_planned": n_planned, "n_records": len(records),
              "n_valid": n_valid, "n_abandoned": n_abandoned,
              "cell_counts_ok": cell_ok, "run_complete_ok": ok}
    write_json(os.path.join(paths.results, "validation_report.json"), result)
    return result


def phase_analysis(paths: RunPaths, log, accountant, val: Dict):
    records = []
    for fn in sorted(os.listdir(paths.judgment)):
        if not fn.startswith("astraf-"): continue
        rec = read_json(os.path.join(paths.judgment, fn))
        if rec: records.append(rec)

    # Source features (from THIS pilot's sources)
    sources = load_pilot4_sources(paths.root)
    features_by_traj = {}
    source_by_arch_model: Dict[Tuple[str, str], List[Dict[str, float]]] = {}
    for (ml, arch, tid, seq) in sources:
        f = sequence_features(seq)
        features_by_traj[tid] = f
        source_by_arch_model.setdefault((arch, ml), []).append(f)

    # source-model 3-way classifier on the NEW source set
    def _feats(arch):
        return {ml: source_by_arch_model.get((arch, ml), []) for ml in C.MODEL_LABELS}
    clf_batch = clf_online = None
    if all(len(_feats("batch")[ml]) >= 2 for ml in C.MODEL_LABELS):
        clf_batch = nearest_centroid_loo(_feats("batch"))
    if all(len(_feats("online")[ml]) >= 2 for ml in C.MODEL_LABELS):
        clf_online = nearest_centroid_loo(_feats("online"))

    summ = summarize_astra_followup(records)
    dist_rows = distance_to_astra_per_trial(records, features_by_traj, source_by_arch_model)

    # CSV outputs
    _write_csv(os.path.join(paths.results, "trial_level.csv"),
               [{k: v for k, v in r.items()
                 if k not in ("sequence_display", "prompt_text",
                              "raw_completion", "attempt_records")}
                for r in records])
    _write_csv(os.path.join(paths.results, "condition_summary.csv"), summ["cells"])
    _write_csv(os.path.join(paths.results, "primary_interaction.csv"),
               [summ["primary"]])
    _write_csv(os.path.join(paths.results, "baseline_vs_none.csv"),
               [summ["baseline_vs_none"]])
    _write_csv(os.path.join(paths.results, "paired_provenance_switches.csv"),
               summ["paired_switches"])
    _write_csv(os.path.join(paths.results, "switch_table.csv"), summ["switch_table"])
    _write_csv(os.path.join(paths.results, "mcnemar.csv"), summ["mcnemar"])
    _write_csv(os.path.join(paths.results, "source_model_breakdown.csv"),
               summ["source_breakdown"])
    _write_csv(os.path.join(paths.results, "actual_arch_breakdown.csv"),
               summ["actual_arch_rows"])
    _write_csv(os.path.join(paths.results, "distance_to_astra.csv"), dist_rows)

    _write_report(paths, accountant, val, summ, dist_rows, clf_batch, clf_online)


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


def _write_report(paths, accountant, val, summ, dist_rows, clf_batch, clf_online):
    p = os.path.join(paths.results, "ASTRA_PROVENANCE_REPLICATION_REPORT.md")
    lines = []
    lines.append("# SPAR Pilot 4 — Astra Provenance Replication (with No-Provenance Control)")
    lines.append("")
    lines.append(f"Run root: `{paths.root}`")
    lines.append(f"Experiment tag: `{C.ASTRA_FOLLOWUP_TAG}`")
    lines.append(f"Judge: `{JUDGE_SLUG}`")
    lines.append(f"Total spend: **${accountant.spent_usd:.4f}** / ${C.ASTRA_FOLLOWUP_BUDGET_USD:.2f} cap")
    lines.append("")
    lines.append("## Design")
    lines.append("")
    lines.append("Astra is the only judge. Fresh independent source trajectories: 10 Astra batch,")
    lines.append("10 Astra online, 5 Fable batch, 5 Fable online, 5 Qwen batch, 5 Qwen online")
    lines.append("(= 40 unique). Every trajectory judged three times: told-batch, told-online,")
    lines.append("no-provenance = 120 total judgments.")
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

    lines.append("## Primary result — Selective ONLINE-cue SELF Effect")
    lines.append("")
    pr = summ["primary"]
    lines.append(f"- P(SELF | Astra source, told-batch) = **{pr['astra_told_batch_self_rate']:.3f}**")
    lines.append(f"- P(SELF | Astra source, told-online) = **{pr['astra_told_online_self_rate']:.3f}**")
    lines.append(f"- P(SELF | Astra source, no-provenance) = {pr['astra_no_provenance_self_rate']:.3f}")
    lines.append(f"- P(SELF | Other source, told-batch) = {pr['other_told_batch_self_rate']:.3f}")
    lines.append(f"- P(SELF | Other source, told-online) = {pr['other_told_online_self_rate']:.3f}")
    lines.append(f"- P(SELF | Other source, no-provenance) = {pr['other_no_provenance_self_rate']:.3f}")
    lines.append("")
    lines.append(f"- **SELF-source online shift** = {pr['self_online_shift']:+.3f}")
    lines.append(f"- **OTHER-source online shift** = {pr['other_online_shift']:+.3f}")
    lines.append(f"- **Selective Online SELF Effect** = {pr['selective_online_self_effect']:+.3f}")
    lines.append(f"  (positive replicates the prior pilot 3 finding)")
    lines.append("")

    lines.append("## Baseline vs no-provenance")
    lines.append("")
    b = summ["baseline_vs_none"]
    lines.append(f"- Astra SELF: told-online vs no-provenance = {b['self_online_vs_none']:+.3f}")
    lines.append(f"- Astra SELF: told-batch vs no-provenance = {b['self_batch_vs_none']:+.3f}")
    lines.append(f"- Other:      told-online vs no-provenance = {b['other_online_vs_none']:+.3f}")
    lines.append(f"- Other:      told-batch vs no-provenance = {b['other_batch_vs_none']:+.3f}")
    lines.append("")
    lines.append("A positive `self_online_vs_none` means the told-online cue *facilitated* SELF")
    lines.append("attribution above the natural baseline. A negative `self_batch_vs_none` means")
    lines.append("the told-batch cue *suppressed* SELF attribution below baseline.")
    lines.append("")

    lines.append("## Cell summary")
    lines.append("")
    lines.append("| true id | actual | stated | n | SELF resp | SELF rate | accuracy |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in summ["cells"]:
        lines.append(f"| {row['true_source_identity']} | {row['actual_architecture']} | "
                     f"{row['stated_condition']} | {row['n']} | {row['self_responses']} | "
                     f"{row['self_rate']:.3f} | {row['accuracy']:.3f} |")
    lines.append("")

    lines.append("## Actual-architecture breakdown (SELF rate)")
    lines.append("")
    lines.append("| true id | actual | stated | n | SELF rate |")
    lines.append("|---|---|---|---|---|")
    for row in summ["actual_arch_rows"]:
        lines.append(f"| {row['true_source_identity']} | {row['actual_architecture']} | "
                     f"{row['stated_condition']} | {row['n']} | {row['self_rate']:.3f} |")
    lines.append("")

    lines.append("## Paired within-trajectory switches (told-batch vs told-online)")
    lines.append("")
    lines.append("| true id | n_pairs | OTHER->SELF | SELF->OTHER | no_change | net online shift |")
    lines.append("|---|---|---|---|---|---|")
    for row in summ["switch_table"]:
        lines.append(f"| {row['true_source_identity']} | {row['n_pairs']} | "
                     f"{row['OTHER_to_SELF']} | {row['SELF_to_OTHER']} | "
                     f"{row['no_change']} | {row['net_online_shift']:+d} |")
    lines.append("")

    lines.append("## McNemar test (told-batch vs told-online, paired within trajectory)")
    lines.append("")
    lines.append("| true id | n discordant | chi-square (cc) | exact two-sided p | b→o | o→b |")
    lines.append("|---|---|---|---|---|---|")
    for row in summ["mcnemar"]:
        chi = row.get("chi_square", float("nan"))
        p_val = row.get("p_value_two_sided_exact_binomial", float("nan"))
        chi_str = f"{chi:.3f}" if isinstance(chi, float) and chi == chi else str(chi)
        p_str = f"{p_val:.4f}" if isinstance(p_val, float) and p_val == p_val else str(p_val)
        lines.append(f"| {row['true_source_identity']} | {row.get('n_discordant', 0)} | "
                     f"{chi_str} | {p_str} | {row.get('b_to_o', 0)} | {row.get('o_to_b', 0)} |")
    lines.append("")

    lines.append("## OTHER-source breakdown (Fable vs Qwen)")
    lines.append("")
    lines.append("| source | stated | n | SELF rate | OTHER-CR rate | accuracy |")
    lines.append("|---|---|---|---|---|---|")
    for row in summ["source_breakdown"]:
        lines.append(f"| {row['source_model_label']} | {row['stated_condition']} | "
                     f"{row['n']} | {row['self_rate']:.3f} | {row['other_cr_rate']:.3f} | "
                     f"{row['accuracy']:.3f} |")
    lines.append("")

    lines.append("## Baselines from the fresh source set")
    lines.append("")
    lines.append("### Source-model 3-way classifier (LOO nearest centroid)")
    if clf_batch: lines.append(f"- batch: {clf_batch['accuracy']:.3f} (n={clf_batch['n']})")
    if clf_online: lines.append(f"- online: {clf_online['accuracy']:.3f} (n={clf_online['n']})")
    lines.append("")

    # Outcome classification (per spec section 31)
    ss = summ["primary"]["selective_online_self_effect"]
    self_shift = summ["primary"]["self_online_shift"]
    other_shift = summ["primary"]["other_online_shift"]
    self_vs_none = summ["baseline_vs_none"]["self_online_vs_none"]
    self_batch_vs_none = summ["baseline_vs_none"]["self_batch_vs_none"]
    other_shift_abs = abs(other_shift) if other_shift == other_shift else float("nan")

    if ss >= 0.20 and self_shift >= 0.20 and other_shift_abs <= 0.10:
        outcome = "A"; desc = ("Prior interaction REPLICATED: told-online selectively increases "
                                "SELF attribution for Astra-source trajectories.")
    elif self_shift >= 0.20 and other_shift >= 0.20:
        outcome = "B"; desc = "ONLINE cue creates a generic SELF-response bias — not self-specific."
    elif abs(self_shift) < 0.10 and abs(other_shift) < 0.10:
        outcome = "C"; desc = "ONLINE cue has no meaningful effect on SELF responses — prior effect did not replicate."
    elif self_batch_vs_none <= -0.15 and self_vs_none <= 0.10:
        outcome = "D"; desc = "TOLD-BATCH suppresses SELF responses (rather than ONLINE facilitating)."
    elif self_vs_none >= 0.15 and self_batch_vs_none <= -0.15:
        outcome = "E"; desc = "Both ONLINE facilitation and BATCH suppression relative to no-provenance."
    else:
        outcome = "?"; desc = "Mixed / ambiguous pattern; inspect the cell table above."
    lines.append("## Predefined outcome classification")
    lines.append("")
    lines.append(f"**Outcome {outcome}**: {desc}")
    lines.append("")

    lines.append("## Interpretation caveats")
    lines.append("")
    lines.append("- 10 trials per (identity x actual x stated) cell; granularity 0.10.")
    lines.append("- The primary test is the difference-in-differences (SELF online shift − OTHER online shift).")
    lines.append("- Do not describe positive results as self-awareness or introspection.")
    lines.append("- The prior effect was NOT a truthful-provenance congruence effect. This replication tests the")
    lines.append("  observed pattern, not the original spec-anticipated congruence.")

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
    ap.add_argument("--skip-smoke", action="store_true")
    args = ap.parse_args()

    run_id = args.run_id or ("spar-astra-followup-" + _now_stamp())
    paths = RunPaths(args.data_root, run_id); paths.ensure()
    log, log_file = _log_writer(os.path.join(paths.logs, "orchestrator_astra_followup.log"))
    log(f"START run_id={run_id}")

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
            log(f"  cost projection: source=${proj['projected_source_usd']:.4f} "
                f"judgment=${proj['projected_judgment_usd']:.4f} "
                f"total=${proj['projected_total_usd']:.4f} budget=${proj['budget_usd']:.2f}")
            write_json(os.path.join(paths.smoke, "smoke_records.json"), smoke)
            write_json(os.path.join(paths.smoke, "cost_projection.json"), proj)
            if proj["projected_total_usd"] > C.ASTRA_FOLLOWUP_STOP_AT_PROJECTED_USD:
                log("ABORT: projected > cap")
                _write_stop(paths, "budget_projection_exceeded",
                            f"projected {proj['projected_total_usd']:.4f}", accountant.spent_usd)
                return

        write_json(paths.manifest, {"run_id": run_id, "experiment_tag": C.ASTRA_FOLLOWUP_TAG,
                                    "judge": JUDGE_SLUG, "started_utc": _now_stamp(),
                                    "budget_usd": C.ASTRA_FOLLOWUP_BUDGET_USD})

        phase_source(client, accountant, paths, log)
        src_val = phase_validate_sources(paths, log)
        log(f"  source validation: {src_val}")
        if not src_val["sources_ok"]:
            _write_stop(paths, "source_shortfall", str(src_val), accountant.spent_usd)
            return

        log("PHASE: trial construction")
        trials = phase_trials(paths, log)
        log("PHASE: judgment")
        phase_judgment(client, accountant, paths, trials, log)
        log("PHASE: validate")
        val = phase_validate(paths, trials, log)
        log(f"  validation: {val}")
        log("PHASE: analysis + report")
        phase_analysis(paths, log, accountant, val)

        report_path = os.path.join(paths.results, "ASTRA_PROVENANCE_REPLICATION_REPORT.md")
        if val["run_complete_ok"]:
            log(f"COMPLETE total_spend=${accountant.spent_usd:.4f}")
            _write_complete(paths, accountant.spent_usd, report_path)
        else:
            log(f"STOP: validation not clean")
            _write_stop(paths, "validation_incomplete",
                        f"n_abandoned={val['n_abandoned']} cell_ok={val['cell_counts_ok']}",
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
