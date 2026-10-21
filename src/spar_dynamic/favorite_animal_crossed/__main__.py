"""CLI for FAVORITE_ANIMAL_CROSSED_v1.0: preflight / samples / run / analyze."""

from __future__ import annotations

import argparse, json, os, time

from . import config as C
from . import prompts
from .capability_preflight import (
    write_capability_report, budget_projection,
    fetch_catalog, verify_against_config,
)
from .orchestrator import build_manifest, run as orchestrator_run
from .analysis import write_all
from .parsers import parse_phase2a, is_truncated
from .prompts import crossed_prompt, POSITIONS
from spar_dynamic.dice_pilot.runner import make_openrouter_client, call_once as _call_once
import repo_paths  # reorganisation 2026-10-21: see src/repo_paths.py


EXPERIMENT_DIR_NAME = "favorite_animal_crossed"


def _ts(): return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
def _utc(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _log_writer(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8", buffering=1)
    def log(msg):
        line = f"[{_utc()}] {msg}"
        print(line, flush=True); f.write(line + "\n"); f.flush()
    return log, f


def _run_dir(data_root, run_id):
    return str(repo_paths.legacy(os.path.join(data_root, EXPERIMENT_DIR_NAME, run_id or f"favanimx-{_ts()}")))


def cmd_preflight(args):
    run_dir = _run_dir(args.data_root, args.run_id or f"favanimx-{_ts()}-preflight")
    os.makedirs(run_dir, exist_ok=True)
    log, _ = _log_writer(os.path.join(run_dir, "logs", "favorite_animal_crossed.log"))
    log(f"START preflight run_dir={run_dir}")
    prompts.assert_consistency()
    log("prompt consistency: ok")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    assert api_key, "OPENROUTER_API_KEY not set"
    client = make_openrouter_client(api_key)
    verdict = write_capability_report(client, run_dir)
    for issue in verdict["issues"]:
        log(f"ISSUE: {issue}")

    bp = budget_projection(verdict)
    with open(os.path.join(run_dir, "budget_projection.json"), "w", encoding="utf-8") as f:
        json.dump(bp, f, indent=2, sort_keys=True)
    log(f"budget projection worst case: ${bp['total_usd_worst_case']} / cap ${bp['budget_cap_usd']} within={bp['within_cap']}")
    for r in bp["rows"]:
        log(f"  predictor={r['predictor_model']}/{r['config']}: n_calls={r['n_calls']} "
            f"per-call-worst=${r['per_call_usd_worst_case']} subtotal=${r['subtotal_usd_worst_case']}")

    manifest = build_manifest()
    with open(os.path.join(run_dir, "experiment_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"spec_version": "FAVORITE_ANIMAL_CROSSED_v1.0",
                    "scheduling_seed": C.SCHEDULING_SEED,
                    "n_entries": len(manifest),
                    "entries": [e.__dict__ for e in manifest],
                    "prior_canonical_favorite": C.PRIOR_CANONICAL_FAVORITE,
                    "target_named": C.TARGET_NAMED},
                   f, indent=2, sort_keys=True, default=str)
    log(f"manifest built: {len(manifest)} entries (expected {C.TOTAL_CALLS_MAX})")

    with open(os.path.join(run_dir, "prompts_frozen.txt"), "w", encoding="utf-8") as f:
        for (predictor, target) in C.CROSS_PAIRS:
            name = C.TARGET_NAMED[target]
            for pos in POSITIONS:
                f.write(f"PREDICTOR={predictor}, TARGET={target} ({name!r}), POS={pos}:\n")
                f.write(crossed_prompt(name, pos) + "\n\n")
    log("prompts frozen to prompts_frozen.txt")

    print("\nPREFLIGHT SUMMARY")
    print("=" * 60)
    print(f"Run dir: {run_dir}")
    print(f"Pairs: {len(C.CROSS_PAIRS)}  Calls: {len(manifest)} / {C.TOTAL_CALLS_MAX}")
    print(f"Worst-case cost: ${bp['total_usd_worst_case']} / cap ${bp['budget_cap_usd']}")
    print(f"Within cap: {bp['within_cap']}")


def cmd_samples(args):
    assert args.live and args.yes
    run_dir = _run_dir(args.data_root, args.run_id or f"favanimx-{_ts()}-samples")
    os.makedirs(run_dir, exist_ok=True)
    log, _ = _log_writer(os.path.join(run_dir, "logs", "favorite_animal_crossed.log"))
    log(f"START samples run_dir={run_dir}")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    client = make_openrouter_client(api_key)
    catalog = fetch_catalog(client)
    verdict = verify_against_config(catalog)
    pricing = {}
    for m in C.MODELS:
        v = verdict["per_model"].get(m.label)
        if v: pricing[m.slug] = {"prompt": v["pricing_prompt_per_mtok"] / 1e6,
                                   "completion": v["pricing_completion_per_mtok"] / 1e6}
    samples = []; total_cost = 0.0
    # One sample per predictor × non-self target × "last" position (critical disambiguator)
    for predictor_m in C.MODELS:
        for target in C.EXECUTION_ORDER:
            if target == predictor_m.label: continue
            target_name = C.TARGET_NAMED[target]
            prompt_text = crossed_prompt(target_name, "last")
            temperature = (C.TEMPERATURE_WHEN_SUPPORTED if predictor_m.supports_temperature else None)
            reasoning_spec = ({"enabled": False} if predictor_m.reasoning_enabled_false
                              else ({"effort": predictor_m.reasoning_effort_requested}
                                    if predictor_m.reasoning_effort_requested else {}))
            log(f"sample predictor={predictor_m.label} target={target} ({target_name})")
            res = _call_once(client, predictor_m.slug, prompt_text, predictor_m.max_tokens,
                              temperature, reasoning_spec, predictor_m.preferred_provider,
                              pricing.get(predictor_m.slug) or {"prompt": 0, "completion": 0})
            total_cost += res.cost_usd
            samples.append({
                "predictor": predictor_m.label, "target": target,
                "target_name": target_name,
                "target_favorite": C.PRIOR_CANONICAL_FAVORITE[target],
                "position": "last",
                "raw_text": res.raw_text, "cost_usd": round(res.cost_usd, 6),
                "finish_reason": res.finish_reason,
                "output_tokens": res.completion_tokens,
                "reasoning_tokens": res.reasoning_tokens,
                "reasoning_content_excerpt": (res.reasoning_content[:400]
                                                if isinstance(res.reasoning_content, str) else None),
                "error": res.error,
            })
            log(f"  -> text={res.raw_text[:60]!r}  cost=${res.cost_usd:.5f}")
    with open(os.path.join(run_dir, "preflight_samples.json"), "w", encoding="utf-8") as f:
        json.dump({"total_cost_usd": round(total_cost, 6), "samples": samples},
                   f, indent=2, sort_keys=True)
    print(f"\nTotal sample cost: ${total_cost:.5f}  ({len(samples)} calls)")


def cmd_run(args):
    assert args.live and args.yes
    run_dir = _run_dir(args.data_root, args.run_id or f"favanimx-{_ts()}")
    os.makedirs(run_dir, exist_ok=True)
    log, _ = _log_writer(os.path.join(run_dir, "logs", "favorite_animal_crossed.log"))
    log(f"START run run_dir={run_dir}")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    client = make_openrouter_client(api_key)
    catalog = fetch_catalog(client)
    verdict = verify_against_config(catalog)
    with open(os.path.join(run_dir, "model_capabilities.json"), "w", encoding="utf-8") as f:
        json.dump({"catalog": catalog, "verdict": verdict}, f, indent=2, sort_keys=True)
    if not verdict["ok"]:
        log(f"ABORT: capability flags drift: {verdict['issues']}"); return
    pricing = {}
    for m in C.MODELS:
        v = verdict["per_model"][m.label]
        pricing[m.slug] = {"prompt": v["pricing_prompt_per_mtok"] / 1e6,
                            "completion": v["pricing_completion_per_mtok"] / 1e6}
    bp = budget_projection(verdict)
    log(f"budget projection worst case: ${bp['total_usd_worst_case']} / cap ${bp['budget_cap_usd']} within={bp['within_cap']}")
    if not bp["within_cap"]:
        log("ABORT: projected worst case exceeds budget cap"); return

    r = orchestrator_run(client, run_dir, pricing, log)
    log(f"ORCHESTRATOR RETURN: {r.get('stopped')}  spent=${r['ledger']['spent_usd']:.4f}")


def cmd_analyze(args):
    run_dir = args.run_dir
    log, _ = _log_writer(os.path.join(run_dir, "logs", "favorite_animal_crossed.log"))
    log(f"ANALYZE run_dir={run_dir}")
    write_all(run_dir)
    log("wrote analysis CSVs")


def main():
    ap = argparse.ArgumentParser(prog="python -m spar_dynamic.favorite_animal_crossed")
    sub = ap.add_subparsers(dest="cmd", required=True)
    def _common(sp):
        sp.add_argument("--data-root", default="data/spar_dynamic")
        sp.add_argument("--run-id", default="")

    sp = sub.add_parser("preflight"); _common(sp); sp.set_defaults(func=cmd_preflight)

    sp = sub.add_parser("samples"); _common(sp)
    sp.add_argument("--live", action="store_true", required=True)
    sp.add_argument("--yes", action="store_true", required=True)
    sp.set_defaults(func=cmd_samples)

    sp = sub.add_parser("run"); _common(sp)
    sp.add_argument("--live", action="store_true", required=True)
    sp.add_argument("--yes", action="store_true", required=True)
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("analyze")
    sp.add_argument("--run-dir", required=True)
    sp.set_defaults(func=cmd_analyze)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
