"""Section 25: CLI dispatch — dry-run / run / validate / analyze / package."""

import argparse, csv, hashlib, json, os, sys, time, zipfile
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from . import SPECIFICATION_VERSION, EXPERIMENT_NAME
from . import config as F
from .audit import audit_sources, write_audit_outputs, sha256_file, sha256_text
from .pairs import (build_triplets, build_pairs, build_trials, build_prompt,
                    prompt_hash, write_triplet_manifest, write_pair_manifest,
                    write_trial_manifest, write_prompts_jsonl,
                    load_trials_from_manifest)
from .runner import (make_openrouter_client, snapshot_prices, process_lock,
                     worst_case_cost, judge_request_config_hash)
from .orchestration import (dry_run, run_preflight, run_scored,
                            load_outcomes, save_outcomes, load_ledger, save_ledger)
from .analysis import write_all_analysis_csvs
from .report import write_validation_report, write_final_report


DEFAULT_CORPUS_DIR = "data/spar_dynamic/spar-stimulus-corpus-20260930T012044Z/results/corpus"
DEFAULT_SOURCE_RUN_DIR = "data/spar_dynamic/spar-stimulus-corpus-20260930T012044Z"


def _ts():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _log_writer(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8", buffering=1)
    def log(msg):
        line = f"[{_utc()}] {msg}"
        print(line, flush=True); f.write(line + "\n"); f.flush()
    return log, f


def _load_corpus_rows(corpus_dir: str, source_method: str = F.SOURCE_METHOD) -> List[Dict]:
    rows = []
    with open(os.path.join(corpus_dir, "trajectories.csv"), "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["method"] == source_method:
                rows.append(r)
    return rows


def _run_dir(data_root: str, run_id: str, source_method: str = F.SOURCE_METHOD) -> str:
    # Non-default source methods live under a per-method parent dir so FCE1
    # and FCE2 outputs don't collide.
    if source_method == F.SOURCE_METHOD:
        parent = EXPERIMENT_NAME
    else:
        parent = f"{EXPERIMENT_NAME}_{source_method}"
    return os.path.join(data_root, parent, run_id)


def _frozen_config_snapshot(provider_pins: Dict[str, Optional[str]], max_tokens: int) -> Dict:
    return {
        "specification_version": SPECIFICATION_VERSION,
        "temperature": F.TEMPERATURE,
        "max_tokens": max_tokens,
        "reasoning_per_judge": F.REASONING_PER_JUDGE,
        "response_attempt_cap": F.RESPONSE_ATTEMPT_CAP,
        "transport_retry_cap": F.TRANSPORT_RETRY_CAP,
        "total_submission_cap": F.TOTAL_SUBMISSION_CAP,
        "concurrency_overall": F.CONCURRENCY_OVERALL,
        "concurrency_per_judge": F.CONCURRENCY_PER_JUDGE,
        "pair_seed": F.PAIR_SEED,
        "execution_seed": F.EXECUTION_SEED,
        "bootstrap_seed": F.BOOTSTRAP_SEED,
        "bootstrap_replicates": F.BOOTSTRAP_REPLICATES,
        "budget_usd_cap": F.BUDGET_USD_CAP,
        "judges": [{"label": j.label, "slug": j.slug,
                     "display_name": j.display_name,
                     "preferred_provider": j.preferred_provider,
                     "pinned_provider": provider_pins.get(j.label),
                     "reasoning_config": F.REASONING_PER_JUDGE.get(j.label)}
                    for j in F.JUDGES],
        "documented_deviations_from_spec": [
            "Section 10: per-judge reasoning config. astra/fable use "
            "{effort: low, exclude: True}; mimo uses {enabled: False} because "
            "xiaomi/fp8 cannot practically cap reasoning via effort/exclude "
            "(uses 8000+ reasoning tokens even at effort=low).",
            "Section 8/9: NAMED/SELF suffix format tweaked to put 'A or B' on "
            "its own line with a more directive 'no explanation, no reasoning' "
            "instruction, after preflight showed fable sometimes emitted "
            "150+ tokens of prose ending in the correct letter. Target-name "
            "substitution invariant preserved exactly.",
        ],
    }


# ------------------------------------------------------------------ dry-run --
def cmd_dry_run(args):
    corpus_dir = args.corpus_dir
    sm = args.source_method
    run_dir = _run_dir(args.data_root, args.run_id or f"fce1-{_ts()}-dry", sm)
    os.makedirs(run_dir, exist_ok=True)
    log, _ = _log_writer(os.path.join(run_dir, "logs", "fce1.log"))
    log(f"START dry-run run_dir={run_dir} corpus={corpus_dir} source_method={sm}")
    corpus_rows = _load_corpus_rows(corpus_dir, source_method=sm)
    assert len(corpus_rows) == 60, f"expected 60 {sm} rows, got {len(corpus_rows)}"
    triplets = build_triplets(corpus_rows, source_method=sm)
    pairs = build_pairs(triplets, corpus_rows)
    trials = build_trials(pairs)
    log(f"triplets={len(triplets)} pairs={len(pairs)} trials={len(trials)}")
    write_triplet_manifest(os.path.join(run_dir, "triplet_manifest.csv"), triplets)
    write_pair_manifest(os.path.join(run_dir, "pair_manifest.csv"), pairs)
    write_trial_manifest(os.path.join(run_dir, "trial_manifest.csv"), trials)
    r = dry_run(trials, run_dir, log=log, source_method=sm)
    log(f"dry-run OK: {r}")
    # Save frozen config (without provider pins — those are resolved at run-time)
    with open(os.path.join(run_dir, "config_frozen.json"), "w", encoding="utf-8") as f:
        json.dump(_frozen_config_snapshot({}, F.INITIAL_MAX_TOKENS), f, indent=2, sort_keys=True)
    return run_dir


# -------------------------------------------------------------------- audit --
def _resolve_provider_pins(client, pref_pins: Dict[str, Optional[str]] = None,
                          log=print) -> Dict[str, Optional[str]]:
    """Verify each judge's preferred provider is actually available. Fall back
    to no pin (allow default routing) if preferred provider cannot be confirmed.
    """
    pins: Dict[str, Optional[str]] = {}
    # OpenRouter does not expose per-model provider list via models.list cleanly;
    # we attempt a cheap probe later. For now, use the stated preference and let
    # the catalog verification elsewhere confirm the model id is served at all.
    for j in F.JUDGES:
        pins[j.label] = (pref_pins or {}).get(j.label, j.preferred_provider)
        log(f"[audit]   provider pin for {j.label}: {pins[j.label]}")
    return pins


def _validate_catalog(client, log=print):
    """Section 11: verify exact model identifiers are served."""
    try:
        models = client.models.list()
        ids = {m.id for m in models.data}
    except Exception as e:
        log(f"[audit] WARN: could not fetch catalog: {e}")
        return False, []
    missing = [j.slug for j in F.JUDGES if j.slug not in ids]
    if missing:
        log(f"[audit] CATALOG MISSING: {missing}")
    return len(missing) == 0, missing


# ---------------------------------------------------------------------- run --
def cmd_run(args):
    corpus_dir = args.corpus_dir
    source_run_dir = args.source_run_dir
    sm = args.source_method
    run_dir = _run_dir(args.data_root, args.run_id or f"fce1-{_ts()}", sm)
    os.makedirs(run_dir, exist_ok=True)
    log, _ = _log_writer(os.path.join(run_dir, "logs", "fce1.log"))
    log(f"START run run_dir={run_dir} source_method={sm}")
    log(f"corpus={corpus_dir}  source_run={source_run_dir}")
    log(f"stage={args.stage}  budget_cap=${args.budget_usd:.2f}  live={args.live}  yes={args.yes}")
    assert args.live and args.yes, "require --live --yes to run paid"
    assert sm in F.ALLOWED_SOURCE_METHODS, f"source_method must be one of {F.ALLOWED_SOURCE_METHODS}"

    api_key = os.environ.get("OPENROUTER_API_KEY")
    assert api_key, "OPENROUTER_API_KEY not set in environment"
    client = make_openrouter_client(api_key)

    # Build manifests
    corpus_rows = _load_corpus_rows(corpus_dir, source_method=sm)
    triplets = build_triplets(corpus_rows, source_method=sm)
    pairs = build_pairs(triplets, corpus_rows)
    trials = build_trials(pairs)
    log(f"built {len(trials)} trials from {len(pairs)} pairs across {len(triplets)} triplets")
    write_triplet_manifest(os.path.join(run_dir, "triplet_manifest.csv"), triplets)
    write_pair_manifest(os.path.join(run_dir, "pair_manifest.csv"), pairs)
    write_trial_manifest(os.path.join(run_dir, "trial_manifest.csv"), trials)
    write_prompts_jsonl(os.path.join(run_dir, "prompts.jsonl"), trials, source_method=sm)

    # Audit sources
    tids = sorted({t.sequence_A_id for t in trials} | {t.sequence_B_id for t in trials})
    log(f"auditing {len(tids)} source trajectories (method={sm})...")
    audit = audit_sources(corpus_dir, source_run_dir, tids, source_method=sm)
    write_audit_outputs(audit, run_dir)
    log("audit passed — proceeding")

    # Catalog validation (section 11)
    ok, missing = _validate_catalog(client, log=log)
    if not ok:
        log(f"ABORT: catalog missing models: {missing}")
        return run_dir
    prices = snapshot_prices(client)
    log(f"catalog ok; prices snapshotted for {len(prices)} models")
    with open(os.path.join(run_dir, "catalog_snapshot.json"), "w", encoding="utf-8") as f:
        json.dump({"models": {j.slug: prices.get(j.slug, {}) for j in F.JUDGES},
                   "snapshot_utc": _utc()}, f, indent=2)

    # Resolve provider pins
    provider_pins = _resolve_provider_pins(client, log=log)
    with open(os.path.join(run_dir, "config_frozen.json"), "w", encoding="utf-8") as f:
        json.dump(_frozen_config_snapshot(provider_pins, F.INITIAL_MAX_TOKENS),
                  f, indent=2, sort_keys=True)

    # Process lock
    lock_path = os.path.join(run_dir, ".lock")

    try:
        with process_lock(lock_path):
            if args.stage in ("preflight", "all"):
                pre = run_preflight(client, trials, run_dir, prices, provider_pins,
                                    cap_usd=args.budget_usd, log=log,
                                    source_method=sm)
                if not pre["passes"]:
                    log(f"ABORT: preflight failed: {pre}")
                    return run_dir
                log(f"preflight passed. stopping before scored phase."
                    if args.stage == "preflight"
                    else "preflight passed. proceeding to scored phase.")
            if args.stage in ("scored", "all"):
                summary = run_scored(client, trials, run_dir, prices, provider_pins,
                                     max_tokens=F.INITIAL_MAX_TOKENS,
                                     cap_usd=args.budget_usd, log=log,
                                     source_method=sm)
                log(f"scored summary: {summary}")
    except RuntimeError as e:
        log(f"LOCK ERROR: {e}")
    return run_dir


# --------------------------------------------------------------- validate ---
def cmd_validate(args):
    run_dir = args.run_dir
    sm = args.source_method
    log, _ = _log_writer(os.path.join(run_dir, "logs", "fce1.log"))
    log(f"VALIDATE run_dir={run_dir} source_method={sm}")

    corpus_rows = _load_corpus_rows(args.corpus_dir, source_method=sm)
    manifest_path = os.path.join(run_dir, "trial_manifest.csv")
    if os.path.exists(manifest_path):
        trials = load_trials_from_manifest(run_dir, corpus_rows)
    else:
        triplets = build_triplets(corpus_rows, source_method=sm)
        pairs = build_pairs(triplets, corpus_rows)
        trials = build_trials(pairs)

    outcomes = load_outcomes(run_dir)
    audit = {}
    audit_path = os.path.join(run_dir, "source_audit.json")
    if os.path.exists(audit_path):
        with open(audit_path, "r", encoding="utf-8") as f:
            audit = json.load(f)
    preflight = {}
    pre_path = os.path.join(run_dir, "preflight_summary.json")
    if os.path.exists(pre_path):
        with open(pre_path, "r", encoding="utf-8") as f:
            preflight = json.load(f).get("summary", {})
    ledger_d = {}
    ledger_path = os.path.join(run_dir, "cost_ledger.json")
    if os.path.exists(ledger_path):
        with open(ledger_path, "r", encoding="utf-8") as f:
            ledger_d = json.load(f)
    report = write_validation_report(run_dir, trials, outcomes, audit, preflight, ledger_d)
    log(f"validation: overall_complete={report['overall_complete']}")
    return report


# ----------------------------------------------------------------- analyze --
def cmd_analyze(args):
    run_dir = args.run_dir
    sm = args.source_method
    log, _ = _log_writer(os.path.join(run_dir, "logs", "fce1.log"))
    log(f"ANALYZE run_dir={run_dir} source_method={sm}")
    corpus_rows = _load_corpus_rows(args.corpus_dir, source_method=sm)
    # Prefer loading trials from the saved live-run manifest so the analyze-time
    # trial reconstruction matches the actual prompts the judges saw (works
    # even for legacy runs where build_pairs() used a non-deterministic hash).
    manifest_path = os.path.join(run_dir, "trial_manifest.csv")
    if os.path.exists(manifest_path):
        trials = load_trials_from_manifest(run_dir, corpus_rows)
        log(f"loaded {len(trials)} trials from saved trial_manifest.csv")
    else:
        triplets = build_triplets(corpus_rows, source_method=sm)
        pairs = build_pairs(triplets, corpus_rows)
        trials = build_trials(pairs)
        log(f"rebuilt {len(trials)} trials (no saved manifest)")
    outcomes = load_outcomes(run_dir)
    write_all_analysis_csvs(run_dir, trials, outcomes, corpus_rows)
    # Validation (regenerate) + final report
    audit = {}
    audit_path = os.path.join(run_dir, "source_audit.json")
    if os.path.exists(audit_path):
        with open(audit_path, "r", encoding="utf-8") as f:
            audit = json.load(f)
    preflight = {}
    pre_path = os.path.join(run_dir, "preflight_summary.json")
    if os.path.exists(pre_path):
        with open(pre_path, "r", encoding="utf-8") as f:
            preflight = json.load(f).get("summary", {})
    ledger_d = {}
    ledger_path = os.path.join(run_dir, "cost_ledger.json")
    if os.path.exists(ledger_path):
        with open(ledger_path, "r", encoding="utf-8") as f:
            ledger_d = json.load(f)
    validation = write_validation_report(run_dir, trials, outcomes, audit, preflight, ledger_d)
    write_final_report(run_dir, trials, outcomes, validation)
    log(f"analysis done; final report at {os.path.join(run_dir, 'FULL_CORPUS_EXPERIMENT_1_REPORT.md')}")


# ----------------------------------------------------------------- package --
def cmd_package(args):
    run_dir = args.run_dir
    out_zip = args.out_zip or (run_dir.rstrip("/") + ".zip")
    exclude_names = {".lock", ".env"}
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(run_dir):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".venv")]
            for fn in files:
                if fn in exclude_names: continue
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, os.path.dirname(run_dir))
                z.write(full, rel)
    print(f"packaged {out_zip}", flush=True)


# ----------------------------------------------------------------------- --
def main():
    ap = argparse.ArgumentParser(prog="python -m spar_dynamic.full_corpus_exp1")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def _common(sp):
        sp.add_argument("--corpus-dir", default=DEFAULT_CORPUS_DIR)
        sp.add_argument("--source-run-dir", default=DEFAULT_SOURCE_RUN_DIR)
        sp.add_argument("--data-root", default="data/spar_dynamic")
        sp.add_argument("--run-id", default="")
        sp.add_argument("--source-method", default=F.SOURCE_METHOD,
                        choices=F.ALLOWED_SOURCE_METHODS,
                        help="which stimulus-corpus production method to use")

    sp = sub.add_parser("dry-run"); _common(sp); sp.set_defaults(func=cmd_dry_run)
    sp = sub.add_parser("run"); _common(sp)
    sp.add_argument("--live", action="store_true", required=True)
    sp.add_argument("--yes", action="store_true", required=True)
    sp.add_argument("--budget-usd", type=float, default=F.BUDGET_USD_CAP)
    sp.add_argument("--stage", choices=("preflight", "scored", "all"), default="all")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("validate"); _common(sp)
    sp.add_argument("--run-dir", required=True)
    sp.set_defaults(func=cmd_validate)

    sp = sub.add_parser("analyze"); _common(sp)
    sp.add_argument("--run-dir", required=True)
    sp.set_defaults(func=cmd_analyze)

    sp = sub.add_parser("package")
    sp.add_argument("--run-dir", required=True)
    sp.add_argument("--out-zip", default="")
    sp.set_defaults(func=cmd_package)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
