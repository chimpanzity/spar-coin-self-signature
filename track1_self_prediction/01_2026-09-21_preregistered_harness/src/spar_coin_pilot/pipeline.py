"""Command orchestration: glue between config, client, run directories, and the phase modules."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from .build_trials import (
    balance_report,
    balance_report_markdown,
    build_all_sessions,
    render_prompt,
    trial_manifest_markdown,
)
from .config import PilotConfig, load_api_key
from .estimate import call_counts, cost_estimate, estimate_markdown, usage_based_estimate, usage_estimate_markdown
from .fake_client import FakeOpenRouterClient
from .generate import plan_generation, run_generation, source_payload
from .judge import (
    decide_response_mode,
    judge_payload,
    live_preflight,
    plan_judgments,
    run_judgments,
    template_for_mode,
)
from .openrouter_client import (
    BudgetExceeded,
    BudgetGuard,
    ChatClient,
    OpenRouterClient,
    supported_parameters,
    validate_catalog,
)
from .records import (
    JudgmentRecord,
    RunPaths,
    SourceRecord,
    effective_cost,
    iso,
    load_manifest,
    load_trials,
    read_jsonl,
    update_manifest,
    utc_now,
    valid_sources_by_model,
    write_json,
)
from .run_setup import (  # noqa: F401  (ConfigConflict re-exported for the CLI)
    ConfigConflict,
    check_provider_pins,
    config_from_manifest,
    create_or_open_run,
    load_judgment_schema,
    load_prompts,
    reconcile_config,
    record_key_usage,
    run_paths,
    snapshot_catalog_into_manifest,
)
from .summarize import summarize_run
from .validate import validate_run

log = logging.getLogger(__name__)


class UserAbort(Exception):
    pass


# ---------------------------------------------------------------- helpers

def make_client(cfg: PilotConfig, fake: bool, need_key: bool, fake_kwargs: dict[str, Any] | None = None) -> ChatClient:
    if fake:
        kwargs = {"model_ids": [m.model_id for m in cfg.models.values()], "seed": cfg.run.seed,
                  "string_length": cfg.generation.string_length, "alphabet": cfg.generation.alphabet}
        kwargs.update(fake_kwargs or {})
        return FakeOpenRouterClient(**kwargs)
    key = load_api_key(cfg, required=need_key)
    return OpenRouterClient(cfg.openrouter, key)


def spent_so_far(paths: RunPaths) -> float:
    """Cost already incurred by this run: reported cost where available, else our estimate."""
    total = 0.0
    for p, model in ((paths.source_calls, SourceRecord), (paths.judgment_calls, JudgmentRecord),
                     (paths.preflight_calls, JudgmentRecord)):
        total += sum(effective_cost(r) for r in read_jsonl(p, model))
    return total


def _run_config(cfg: PilotConfig, manifest: dict) -> PilotConfig:
    """Use the run's stored config snapshot; warn if the live YAML has drifted from it."""
    snap, differing = config_from_manifest(manifest, cfg)
    if differing:
        _print(f"note: live config differs from the run's stored snapshot in {differing}; "
               "using the stored snapshot for this run")
    return snap


def confirm(prompt: str, yes: bool) -> None:
    if yes:
        return
    if not sys.stdin.isatty():
        raise UserAbort("refusing to make paid calls without confirmation (no TTY); pass --yes to proceed")
    answer = input(f"{prompt} [y/N] ").strip().lower()
    if answer not in ("y", "yes"):
        raise UserAbort("aborted by user before any paid call")


def _print(msg: str = "") -> None:
    print(msg, flush=True)


def _placeholder_pool(cfg: PilotConfig) -> dict[str, list[tuple[str, str]]]:
    """Placeholder strings for dry-run trial construction (same sample numbering as a clean run)."""
    a, b = cfg.generation.alphabet[0], cfg.generation.alphabet[1]
    pool: dict[str, list[tuple[str, str]]] = {}
    for mi, label in enumerate(cfg.model_labels):
        pool[label] = []
        for i in range(1, cfg.generation.valid_strings_per_model + 1):
            # deterministic, visibly synthetic: alternating blocks whose length encodes model/sample
            block = 2 + (mi + i) % 4
            s = "".join((a if (k // block) % 2 == 0 else b) for k in range(cfg.generation.string_length))
            pool[label].append((f"src_{label}_{i:03d}", s))
    return pool


# ---------------------------------------------------------------- commands

def cmd_snapshot_models(cfg: PilotConfig, fake: bool = False) -> dict[str, Any]:
    client = make_client(cfg, fake, need_key=False)
    try:
        catalog = client.list_models()
        model_ids = {label: m.model_id for label, m in cfg.models.items()}
        entries = validate_catalog(catalog, model_ids)
        snapshot: dict[str, Any] = {"fetched_at": iso(utc_now()), "n_models_in_catalog": len(catalog), "models": {}}
        for label, entry in entries.items():
            snapshot["models"][label] = {
                "catalog_entry": entry,
                "supported_parameters": supported_parameters(entry),
                "endpoints": client.get_endpoints(entry["id"]),
            }
        out_dir = cfg.root() / cfg.paths.data_dir / "catalog"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"openrouter_models_{utc_now().strftime('%Y%m%d_%H%M%S')}.json"
        write_json(out, snapshot)
        _print(f"Catalog: {len(catalog)} models; all {len(entries)} configured IDs present. Saved {out}")
        for label, info in snapshot["models"].items():
            e = info["catalog_entry"]
            pricing = e.get("pricing") or {}
            _print(f"- {label}: {e.get('id')}  name={e.get('name')!r}  created={e.get('created')}")
            _print(f"    pricing $/Mtok prompt={float(pricing.get('prompt', 0) or 0) * 1e6:.4f} "
                   f"completion={float(pricing.get('completion', 0) or 0) * 1e6:.4f}  context={e.get('context_length')}")
            _print(f"    supported_parameters={info['supported_parameters']}")
            eps = info.get("endpoints") or {}
            for ep in (eps.get("endpoints") or []) if isinstance(eps, dict) else []:
                _print(f"    endpoint: {ep.get('provider_name')}  params={ep.get('supported_parameters')}")
        return snapshot
    finally:
        client.close()


def cmd_estimate(cfg: PilotConfig, fake: bool = False, run_id: str | None = None) -> dict[str, Any]:
    client = make_client(cfg, fake, need_key=False)
    try:
        catalog = client.list_models()
        entries = validate_catalog(catalog, {label: m.model_id for label, m in cfg.models.items()})
    finally:
        client.close()
    est = cost_estimate(cfg, entries)
    _print(estimate_markdown(est))
    if run_id:
        paths = run_paths(cfg, run_id)
        sources = read_jsonl(paths.source_calls, SourceRecord)
        judgments = read_jsonl(paths.judgment_calls, JudgmentRecord)
        trials = load_trials(paths) if paths.trials_json.exists() else []
        ub = usage_based_estimate(cfg, entries, sources, judgments, trials, spent_so_far(paths))
        _print(usage_estimate_markdown(ub, run_id))
        est["usage_based"] = ub
    return est


def cmd_dry_run(cfg: PilotConfig, fake: bool = False, out_dir: Path | None = None) -> Path:
    """Full plan without API chat calls: counts, cost, exact prompts and payloads, placeholder trials."""
    prompts = load_prompts(cfg)
    schema = load_judgment_schema(cfg)
    client = make_client(cfg, fake, need_key=False)
    try:
        catalog = client.list_models()
        entries = validate_catalog(catalog, {label: m.model_id for label, m in cfg.models.items()})
        endpoints = {label: client.get_endpoints(e["id"]) for label, e in entries.items()}
    finally:
        client.close()
    est = cost_estimate(cfg, entries)
    counts = call_counts(cfg)

    out = out_dir or (cfg.root() / cfg.paths.results_dir / f"dryrun_{utc_now().strftime('%Y%m%d_%H%M%S')}")
    out.mkdir(parents=True, exist_ok=True)

    # generation payloads (identical except for model id)
    gen_payloads = {label: source_payload(cfg, label, prompts["generate_coin"]["text"]) for label in cfg.model_labels}
    write_json(out / "generation_payloads.json", gen_payloads)

    # placeholder trials -> exact structure of the real run
    pool = _placeholder_pool(cfg)
    trials, infos = build_all_sessions("dryrun", cfg.model_labels, pool, cfg.judgment.trials_per_cell,
                                       cfg.run.seed, cfg.judgment.display_alphabet, cfg.generation.alphabet)
    write_json(out / "trials_placeholder.json", [t.model_dump() for t in trials])
    (out / "trial_manifest_placeholder.md").write_text(trial_manifest_markdown(trials, cfg.model_labels), encoding="utf-8")
    report = balance_report(trials, cfg.model_labels, cfg.judgment.trials_per_cell)
    write_json(out / "balance_report.json", report)
    (out / "balance_report.md").write_text(balance_report_markdown(report, infos), encoding="utf-8")

    # judgment payload examples, one per judge, for both response modes
    examples: dict[str, Any] = {}
    for mode in ("structured", "one_word"):
        tmpl = template_for_mode(prompts, mode)
        examples[mode] = {}
        for label in cfg.model_labels:
            t = next(tr for tr in trials if tr.judge_model_label == label)
            prompt_text = render_prompt(tmpl, t.string_1_display, t.string_2_display)
            examples[mode][label] = judge_payload(cfg, label, prompt_text, mode, schema if mode == "structured" else None)
    write_json(out / "judgment_payload_examples.json", examples)

    all_checks_pass = all(c["pass"] for r in report.values() for c in r["checks"])
    lines = [f"# Dry-run report ({'FAKE catalog' if fake else 'live OpenRouter catalog'})", "",
             f"Generated {iso(utc_now())} from {cfg.config_path}. No chat-completion calls were made.", "",
             "## Model catalog check", ""]
    for label, e in entries.items():
        params = supported_parameters(e)
        pin = cfg.models[label].provider
        lines.append(f"- {label}: provider pin: {pin or 'none (OpenRouter default routing, no fallbacks)'}")
        lines.append(f"- {label}: `{e.get('id')}` present (name: {e.get('name')}); response_format "
                     f"{'supported' if 'response_format' in params else 'NOT advertised'}; structured_outputs "
                     f"{'supported' if 'structured_outputs' in params else 'NOT advertised'}; reasoning "
                     f"{'supported' if 'reasoning' in params else 'NOT advertised'}; temperature "
                     f"{'supported' if 'temperature' in params else 'not advertised (not sent anyway)'}")
        eps = endpoints.get(label) or {}
        if isinstance(eps, dict) and eps.get("endpoints"):
            lines.append("  - endpoints: " + "; ".join(f"{ep.get('provider_name')} ({', '.join(ep.get('supported_parameters') or [])})"
                                                      for ep in eps["endpoints"]))
    lines += ["", estimate_markdown(est), "## Exact prompts", "", "### Source prompt (prompts/generate_coin.txt)", "",
              "```text", prompts["generate_coin"]["text"], "```", "",
              "### Judge prompt, structured mode (prompts/judge_same_different_structured.txt)", "",
              "```text", prompts["judge_same_different_structured"]["text"], "```", "",
              "### Judge prompt, one-word fallback (prompts/judge_same_different.txt)", "",
              "```text", prompts["judge_same_different"]["text"], "```", "",
              "### JSON schema (schemas/judgment.schema.json)", "", "```json", json.dumps(schema, indent=2), "```", "",
              "## Example request payloads", "", "Source call (astra shown; the others differ only in `model`):", "",
              "```json", json.dumps(gen_payloads[cfg.model_labels[0]], indent=2), "```", "",
              f"Judgment call, structured mode ({cfg.model_labels[0]} shown, placeholder strings):", "",
              "```json", json.dumps(examples["structured"][cfg.model_labels[0]], indent=2), "```", "",
              "## Trial structure (placeholder strings; identical pairing structure to the real run)", "",
              f"Balance checks: {'ALL PASS' if all_checks_pass else 'FAILURES PRESENT'} (details in balance_report.md). "
              "Sample IDs shown are the ones a clean run will produce if no source call is invalid; "
              "replacement calls shift sample numbers but not the pairing structure.", ""]
    for judge, r in report.items():
        lines.append(f"- {judge}: cells {r['trials_per_cell']}, answers {r['answers']}, pairs {r['source_pair_frequencies']}, "
                     f"use-count range {r['use_count_range_by_model']}, max cell run {r['longest_run_any_cell']}")
    lines += ["", "## Planned call totals", "",
              f"- {counts['source_calls']} source calls, {counts['judgment_calls']} judgment calls"
              + (f", {counts['preflight_calls']} preflight calls" if counts['preflight_calls'] else ""),
              f"- {counts['total_without_replacements']} successful calls before any replacements", ""]
    report_path = out / "dry_run_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    _print("\n".join(lines))
    _print(f"Dry-run files written to {out}")
    return out


def cmd_generate(cfg: PilotConfig, run_id: str | None, dry_run: bool, limit: int | None, yes: bool,
                 fake: bool, allow_drift: bool = False, fake_kwargs: dict[str, Any] | None = None) -> str:
    prompts = load_prompts(cfg)
    prompt_text = prompts["generate_coin"]["text"]
    if dry_run:
        _print("DRY RUN (run.dry_run is true or --dry-run given): no API calls. Pass --live (or set dry_run: false) to run.")
        rid = run_id or "(new run id will be assigned)"
        if run_id:
            paths = run_paths(cfg, run_id)
            plan = plan_generation(cfg, paths, prompt_text)
        else:
            tmp = RunPaths(Path("/nonexistent"), Path("/nonexistent"), Path("/nonexistent"))
            plan = plan_generation(cfg, tmp, prompt_text)
        _print(f"Run: {rid}")
        for label, p in plan.per_model.items():
            _print(f"- {label}: existing valid {p['existing_valid']}, existing invalid {p['existing_invalid']}, "
                   f"api errors {p['existing_api_errors']}, planned calls {p['planned_calls']}"
                   + (" (invalid ceiling reached)" if p['invalid_ceiling_reached'] else ""))
        _print(f"Total planned source calls: {plan.total_planned_calls}")
        _print("Example payload (" + cfg.model_labels[0] + "):")
        _print(json.dumps(plan.example_payloads[cfg.model_labels[0]], indent=2))
        return rid

    client = make_client(cfg, fake, need_key=True, fake_kwargs=fake_kwargs)
    try:
        run_id, paths, manifest = create_or_open_run(cfg, run_id, fake=fake)
        for change in reconcile_config(cfg, paths, manifest):
            _print(f"config change applied to this run: {change}")
        entries = snapshot_catalog_into_manifest(cfg, client, paths, manifest, allow_drift=allow_drift)
        for note in check_provider_pins(cfg, manifest, paths):
            _print(f"provider pin: {note}")
        plan = plan_generation(cfg, paths, prompt_text)
        est = cost_estimate(cfg, entries)
        spent = spent_so_far(paths)
        _print(f"Run id: {run_id}")
        per_model_txt = ", ".join(f"{l}: {p['planned_calls']}" for l, p in plan.per_model.items())
        _print(f"Planned source calls: {plan.total_planned_calls} ({per_model_txt})"
               + (f"; capped at --limit {limit}" if limit is not None else ""))
        _print(f"Estimated cost for the whole pilot: ${est['est_total_usd']} (ceiling ${cfg.run.max_cost_usd:.2f}; "
               f"already reported for this run: ${spent:.4f})")
        if plan.total_planned_calls == 0:
            _print("Nothing to do: every model already has its valid strings.")
            return run_id
        if not fake:
            confirm("Proceed with paid source-generation calls?", yes)
        budget = BudgetGuard(cfg.run.max_cost_usd, spent_usd=spent)
        record_key_usage(client, paths, "before_generate")
        outcome = run_generation(cfg, client, paths, run_id, entries, budget, prompt_text, limit=limit)
        record_key_usage(client, paths, "after_generate")
        for label, p in outcome.progress.items():
            _print(f"- {label}: valid {p.valid}/{cfg.generation.valid_strings_per_model}, invalid {p.invalid}, "
                   f"api errors {p.api_errors}, calls {p.calls}, stop: {p.stop_reason}")
        _print(f"Calls this invocation: {outcome.calls_made}; reported spend this run: ${outcome.budget['spent_usd']:.4f}")
        if outcome.error:
            _print(f"STOPPED on API error: {outcome.error}\nFix the cause and re-run the same command to resume.")
        elif not outcome.complete:
            _print("Generation incomplete (limit, budget, or invalid ceiling). Re-run the same command to resume.")
        else:
            _print("Generation complete.")
        return run_id
    finally:
        client.close()


def cmd_build_trials(cfg: PilotConfig, run_id: str) -> dict[str, Any]:
    paths = run_paths(cfg, run_id)
    manifest = load_manifest(paths)
    cfg = _run_config(cfg, manifest)
    sources = read_jsonl(paths.source_calls, SourceRecord)
    by_model = valid_sources_by_model(sources, cfg.model_labels)
    short = {l: len(v) for l, v in by_model.items() if len(v) < cfg.generation.valid_strings_per_model}
    if short:
        raise RuntimeError(f"not enough valid strings to build trials: {short} "
                           f"(need {cfg.generation.valid_strings_per_model} per model); run `generate` first")
    pool = {l: [(r.sample_id, r.parsed_string or "") for r in by_model[l][: cfg.generation.valid_strings_per_model]]
            for l in cfg.model_labels}
    if paths.trials_json.exists():
        existing = load_trials(paths)
        _print(f"trials already exist for {run_id} ({len(existing)} trials); rebuilding deterministically and checking equality")
    seed = int(manifest["config"]["run"]["seed"])
    trials, infos = build_all_sessions(run_id, cfg.model_labels, pool, cfg.judgment.trials_per_cell, seed,
                                       cfg.judgment.display_alphabet, cfg.generation.alphabet)
    if paths.trials_json.exists():
        old = [t.model_dump() for t in load_trials(paths)]
        new = [t.model_dump() for t in trials]
        if old != new:
            raise RuntimeError("rebuilt trials differ from the stored trials; refusing to overwrite. "
                               "Delete trials/ manually only if the stored version is known to be wrong.")
    report = balance_report(trials, cfg.model_labels, cfg.judgment.trials_per_cell)
    failures = [(j, c["check"], c["detail"]) for j, r in report.items() for c in r["checks"] if not c["pass"]]
    if failures:
        _print(balance_report_markdown(report, infos))
        raise RuntimeError(f"balance checks failed; trials NOT written: {failures}")
    paths.trials_dir.mkdir(parents=True, exist_ok=True)
    write_json(paths.trials_json, [t.model_dump() for t in trials])
    paths.trial_manifest_md.write_text(trial_manifest_markdown(trials, cfg.model_labels), encoding="utf-8")
    write_json(paths.balance_report_json, report)
    md = balance_report_markdown(report, infos)
    paths.balance_report_md.write_text(md, encoding="utf-8")
    update_manifest(paths, phases={"build_trials": {
        "built_at": iso(utc_now()), "n_trials": len(trials), "seed": seed,
        "per_judge": infos, "balance_ok": not failures,
    }})
    _print(md)
    _print(f"{len(trials)} trials written to {paths.trials_json}; manifest {paths.trial_manifest_md}")
    return {"trials": trials, "report": report}


def cmd_run_judgments(cfg: PilotConfig, run_id: str, dry_run: bool, limit: int | None, yes: bool, fake: bool,
                      allow_drift: bool = False, fake_kwargs: dict[str, Any] | None = None) -> dict[str, Any]:
    paths = run_paths(cfg, run_id)
    manifest = load_manifest(paths)
    trials = load_trials(paths)
    schema = load_judgment_schema(cfg)
    prompts = manifest["prompts"]
    plan = plan_judgments(cfg, paths, trials)
    per_judge_txt = ", ".join(f"{l}: {p['planned_calls']}" for l, p in plan.per_judge.items())
    _print(f"Run id: {run_id}; trials: {len(trials)}; planned judgment calls: {plan.total_planned_calls} "
           f"({per_judge_txt})" + (f"; capped at --limit {limit}" if limit is not None else ""))
    if plan.abandoned_trial_ids:
        _print(f"WARNING: {len(plan.abandoned_trial_ids)} trial(s) reached judgment.max_attempts_per_trial "
               f"without a valid answer and will not be retried: {plan.abandoned_trial_ids}")
    if dry_run:
        _print("DRY RUN: no API calls. Example payload (structured mode, first pending trial):")
        if plan.pending_trial_ids:
            t = next(tr for tr in trials if tr.trial_id == plan.pending_trial_ids[0])
            tmpl = template_for_mode(prompts, cfg.judgment.response_mode)
            payload = judge_payload(cfg, t.judge_model_label, render_prompt(tmpl, t.string_1_display, t.string_2_display),
                                    cfg.judgment.response_mode, schema)
            _print(json.dumps(payload, indent=2))
        return {"planned": plan.total_planned_calls}
    if plan.total_planned_calls == 0:
        _print("Nothing to do: every trial already has a valid judgment (or reached max attempts).")
        return {"planned": 0}

    client = make_client(cfg, fake, need_key=True, fake_kwargs=fake_kwargs)
    try:
        for change in reconcile_config(cfg, paths, manifest):
            _print(f"config change applied to this run: {change}")
        entries = snapshot_catalog_into_manifest(cfg, client, paths, manifest, allow_drift=allow_drift)
        for note in check_provider_pins(cfg, manifest, paths):
            _print(f"provider pin: {note}")
        spent = spent_so_far(paths)
        budget = BudgetGuard(cfg.run.max_cost_usd, spent_usd=spent)
        est = cost_estimate(cfg, entries)
        _print(f"Estimated judgment-phase cost: ${sum(r['est_judgment_usd'] for r in est['rows']):.4f}; "
               f"ceiling ${cfg.run.max_cost_usd:.2f}; already reported for this run: ${spent:.4f}")
        if not fake:
            confirm("Proceed with paid judgment calls (including the structured-output preflight, if enabled)?", yes)

        # Response mode: decided once per run and reused on resume.
        decided = manifest.get("judgment_response_mode")
        if decided and decided.get("effective"):
            mode = decided["effective"]
            _print(f"Response mode (decided earlier for this run): {mode}")
        else:
            live = None
            if cfg.judgment.response_mode == "structured" and cfg.judgment.preflight_live:
                record_key_usage(client, paths, "before_preflight")
                try:
                    live = live_preflight(cfg, client, paths, run_id, entries, budget, schema)
                except BudgetExceeded as exc:
                    _print(f"STOPPED during preflight: {exc}")
                    return {"outcome": None, "mode": None, "stop_reason": "budget"}
            mode, evidence = decide_response_mode(cfg, manifest["catalog"]["models"], live)
            update_manifest(paths, judgment_response_mode={"effective": mode, "decided_at": iso(utc_now()), **evidence})
            _print(f"Response mode: {mode} ({evidence['reason']})")
        template = template_for_mode(prompts, mode)
        record_key_usage(client, paths, "before_judgments")
        outcome = run_judgments(cfg, client, paths, run_id, entries, budget, trials, template, mode,
                                schema if mode == "structured" else None, limit=limit)
        record_key_usage(client, paths, "after_judgments")
        for label, p in outcome.per_judge.items():
            _print(f"- {label}: valid judgments {p['valid_judgments']}/{p['trials']}"
                   + (f", abandoned {p['abandoned_trials']}" if p['abandoned_trials'] else ""))
        _print(f"Calls this invocation: {outcome.calls_made}; invalid attempts total: {outcome.invalid_total}; "
               f"reported spend this run: ${outcome.budget['spent_usd']:.4f}")
        if outcome.error:
            _print(f"STOPPED on API error: {outcome.error}\nFix the cause and re-run the same command to resume.")
        elif not outcome.complete:
            _print(f"Judgments incomplete (stop reason: {outcome.stop_reason}). Re-run the same command to resume.")
        else:
            _print("Judgment phase complete.")
        return {"outcome": outcome, "mode": mode}
    finally:
        client.close()


def cmd_validate(cfg: PilotConfig, run_id: str) -> Any:
    paths = run_paths(cfg, run_id)
    cfg = _run_config(cfg, load_manifest(paths))
    rep = validate_run(cfg, paths)
    paths.results_dir.mkdir(parents=True, exist_ok=True)
    write_json(paths.results_dir / "validation_report.json", rep.to_dict())
    (paths.results_dir / "validation_report.md").write_text(rep.markdown(), encoding="utf-8")
    d = rep.to_dict()
    _print(f"Validation: {d['status']} ({d['n_pass']} pass, {d['n_fail']} fail, {d['n_warn']} warn)")
    for c in rep.checks:
        if c.status != "PASS":
            _print(f"  {c.status}: {c.name}: {c.detail}")
    _print(f"Report: {paths.results_dir / 'validation_report.md'}")
    update_manifest(paths, phases={"validate": {"at": iso(utc_now()), "status": d["status"], "n_fail": d["n_fail"]}})
    return rep


def cmd_export(cfg: PilotConfig, run_id: str) -> Any:
    """Rebuild the flat CSVs (data/derived/<run_id>/) from the raw records, without the summary."""
    from .export import export_run
    paths = run_paths(cfg, run_id)
    cfg = _run_config(cfg, load_manifest(paths))
    out = export_run(cfg, paths)
    for name, path in out["files"].items():
        _print(f"{name}: {len(out['frames'][name])} rows -> {path}")
    _print(f"column dictionary: {paths.derived_dir / 'columns.md'}")
    return out


def cmd_summarize(cfg: PilotConfig, run_id: str) -> Any:
    paths = run_paths(cfg, run_id)
    cfg = _run_config(cfg, load_manifest(paths))
    status = None
    vr = paths.results_dir / "validation_report.json"
    if vr.exists():
        status = json.loads(vr.read_text(encoding="utf-8")).get("status")
    else:
        _print("note: validation has not been run for this run id (run `validate` first for a status line)")
    out = summarize_run(cfg, paths, validation_status=status)
    _print((paths.results_dir / "summary.md").read_text(encoding="utf-8"))
    _print(f"Summary written to {out['summary_md']}; result CSVs alongside; flat per-call CSVs "
           f"(calls_all.csv, sources.csv, judgments.csv, preflight.csv, trials.csv, columns.md) in {paths.derived_dir}")
    return out


def cmd_demo_fake(cfg: PilotConfig, fake_kwargs: dict[str, Any] | None = None) -> str:
    """End-to-end run with the fake client (no network, no cost): generate, build, judge, validate, summarize."""
    kwargs = {"invalid_source_schedule": {4, 17}, "invalid_judgment_schedule": {5, 40}}
    kwargs.update(fake_kwargs or {})
    run_id = cmd_generate(cfg, None, dry_run=False, limit=None, yes=True, fake=True, fake_kwargs=kwargs)
    cmd_build_trials(cfg, run_id)
    cmd_run_judgments(cfg, run_id, dry_run=False, limit=None, yes=True, fake=True, fake_kwargs=kwargs)
    cmd_validate(cfg, run_id)
    cmd_summarize(cfg, run_id)
    return run_id
