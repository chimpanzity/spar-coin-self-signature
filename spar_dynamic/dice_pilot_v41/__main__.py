"""CLI for DICE_PILOT_v4.1: preflight / samples / run / analyze."""

from __future__ import annotations

import argparse, json, os, time

from . import config as C
from . import prompts
from .capability_preflight import (
    write_capability_report, budget_projection,
    fetch_catalog, verify_against_config, resolve_providers,
)
from .orchestrator import build_manifest, run as orchestrator_run
from .analysis import write_all
from .runner import make_openrouter_client, call_once as _call_once
from .parsers import parse_phase1, parse_phase2, is_truncated
from .prompts import (PHASE1_PROMPT, PHASE2A_PROMPT, PHASE2C_PROMPT,
                       phase2b_prompt, PHASE2B_ORDINALS)


EXPERIMENT_DIR_NAME = "dice_pilot_v41"


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
    return os.path.join(data_root, EXPERIMENT_DIR_NAME, run_id or f"dicepilotv41-{_ts()}")


# --------------------------------------------------------------- preflight --

def cmd_preflight(args):
    run_dir = _run_dir(args.data_root, args.run_id or f"dicepilotv41-{_ts()}-preflight")
    os.makedirs(run_dir, exist_ok=True)
    log, _ = _log_writer(os.path.join(run_dir, "logs", "dice_pilot_v41.log"))
    log(f"START preflight run_dir={run_dir}")
    prompts.assert_consistency()
    log("prompt consistency: ok (Phase 1 + Phase 2A byte-exact with v3.1; Phase 2B/2C quote Phase 1)")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    assert api_key, "OPENROUTER_API_KEY not set"
    client = make_openrouter_client(api_key)
    verdict = write_capability_report(client, api_key, run_dir)
    for issue in verdict["issues"]:
        log(f"ISSUE: {issue}")

    bp = budget_projection(verdict)
    with open(os.path.join(run_dir, "budget_projection.json"), "w", encoding="utf-8") as f:
        json.dump(bp, f, indent=2, sort_keys=True)
    log(f"budget projection worst case: ${bp['total_usd_worst_case']} / cap ${bp['budget_cap_usd']} within={bp['within_cap']}")
    for r in bp["rows"]:
        log(f"  {r['model']}/{r['config']}: calls={r['n_calls']} max_tok={r.get('max_tokens')} "
            f"per-call-worst=${r['per_call_usd_worst_case']} subtotal=${r['subtotal_usd_worst_case']}")

    manifest = build_manifest()
    with open(os.path.join(run_dir, "experiment_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"spec_version": "DICE_PILOT_v4.1",
                    "scheduling_seed": C.SCHEDULING_SEED,
                    "n_entries": len(manifest),
                    "entries": [e.__dict__ for e in manifest]},
                   f, indent=2, sort_keys=True, default=str)
    log(f"manifest built: {len(manifest)} entries (expected {C.TOTAL_CALLS_MAX})")

    # Freeze prompts
    with open(os.path.join(run_dir, "prompts_frozen.txt"), "w", encoding="utf-8") as f:
        f.write("PHASE 1:\n" + PHASE1_PROMPT + "\n\n")
        f.write("PHASE 2A (original wording, pos 2):\n" + PHASE2A_PROMPT + "\n\n")
        for pos in sorted(PHASE2B_ORDINALS):
            f.write(f"PHASE 2B (revised wording, pos {pos} = {PHASE2B_ORDINALS[pos]!r}):\n")
            f.write(phase2b_prompt(pos) + "\n\n")
        f.write("PHASE 2C (full-sequence reenactment):\n" + PHASE2C_PROMPT + "\n\n")
    log("prompts frozen to prompts_frozen.txt")

    print("\nPREFLIGHT SUMMARY")
    print("=" * 60)
    print(f"Run dir: {run_dir}")
    print(f"Capability drift: {'none' if verdict['ok'] else 'DETECTED (' + '; '.join(verdict['issues']) + ')'}")
    print(f"Manifest: {len(manifest)} / {C.TOTAL_CALLS_MAX}")
    print(f"Worst-case cost: ${bp['total_usd_worst_case']} / cap ${bp['budget_cap_usd']}")
    print(f"Within cap: {bp['within_cap']}")
    print("\nNEXT: review and approve. Then:")
    print(f"  python3 -m spar_dynamic.dice_pilot_v41 samples --run-id {os.path.basename(run_dir)} --live --yes")
    print(f"  python3 -m spar_dynamic.dice_pilot_v41 run --run-id <fresh id> --live --yes")


# --------------------------------------------------------------- paid samples --

def cmd_samples(args):
    assert args.live and args.yes
    run_dir = _run_dir(args.data_root, args.run_id or f"dicepilotv41-{_ts()}-samples")
    os.makedirs(run_dir, exist_ok=True)
    log, _ = _log_writer(os.path.join(run_dir, "logs", "dice_pilot_v41.log"))
    log(f"START samples run_dir={run_dir}")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    assert api_key, "OPENROUTER_API_KEY not set"
    client = make_openrouter_client(api_key)

    catalog = fetch_catalog(client)
    providers = resolve_providers(api_key)
    verdict = verify_against_config(catalog, providers)
    pricing = {}
    for m in C.MODELS:
        v = verdict["per_model"].get(m.label)
        if not v: continue
        pricing[m.slug] = {
            "prompt": v["pricing_prompt_per_mtok"] / 1e6,
            "completion": v["pricing_completion_per_mtok"] / 1e6,
        }

    samples = []
    total_cost = 0.0
    for m in C.MODELS:
        provider_pin = (verdict["per_model"].get(m.label) or {}).get("resolved_provider") or m.preferred_provider
        temperature = C.TEMPERATURE_WHEN_SUPPORTED if m.supports_temperature else None
        reasoning_spec = ({"enabled": False} if m.reasoning_enabled_false
                          else ({"effort": m.reasoning_effort_requested}
                                if m.reasoning_effort_requested else {}))
        for phase_name, prompt_text in (
            ("phase1", PHASE1_PROMPT),
            ("phase2a", PHASE2A_PROMPT),
            ("phase2b_pos5", phase2b_prompt(5)),
            ("phase2c", PHASE2C_PROMPT),
        ):
            log(f"sample {m.label}/{phase_name}: provider={provider_pin} max_tok={m.max_tokens}")
            res = _call_once(client, m.slug, prompt_text, m.max_tokens,
                              temperature, reasoning_spec, provider_pin,
                              pricing.get(m.slug) or {"prompt": 0.0, "completion": 0.0})
            total_cost += res.cost_usd
            samples.append({
                "model": m.label, "slug": m.slug, "phase": phase_name,
                "provider_pin_requested": provider_pin,
                "provider_served": res.provider,
                "finish_reason": res.finish_reason,
                "truncated": is_truncated(res.finish_reason),
                "input_tokens": res.prompt_tokens,
                "output_tokens": res.completion_tokens,
                "reasoning_tokens": res.reasoning_tokens,
                "cost_usd": round(res.cost_usd, 6),
                "latency_ms": res.latency_ms,
                "raw_text": res.raw_text,
                "reasoning_content_classification": res.reasoning_content_classification,
                "reasoning_content_excerpt": (res.reasoning_content[:400]
                                                if isinstance(res.reasoning_content, str) else None),
                "error": res.error,
            })
            log(f"  -> finish={res.finish_reason!r} out_tok={res.completion_tokens} "
                f"reas_tok={res.reasoning_tokens} cost=${res.cost_usd:.5f} "
                f"text={res.raw_text[:60]!r}")

    with open(os.path.join(run_dir, "preflight_samples.json"), "w", encoding="utf-8") as f:
        json.dump({"total_cost_usd": round(total_cost, 6), "samples": samples},
                   f, indent=2, sort_keys=True)
    print(f"\nTotal sample cost: ${total_cost:.5f}  ({len(samples)} calls)")
    print(f"Written to {run_dir}/preflight_samples.json")


# --------------------------------------------------------------- paid run --

def cmd_run(args):
    assert args.live and args.yes
    run_dir = _run_dir(args.data_root, args.run_id or f"dicepilotv41-{_ts()}")
    os.makedirs(run_dir, exist_ok=True)
    log, _ = _log_writer(os.path.join(run_dir, "logs", "dice_pilot_v41.log"))
    log(f"START run run_dir={run_dir}")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    assert api_key, "OPENROUTER_API_KEY not set"
    client = make_openrouter_client(api_key)
    catalog = fetch_catalog(client)
    providers = resolve_providers(api_key)
    verdict = verify_against_config(catalog, providers)
    with open(os.path.join(run_dir, "model_capabilities.json"), "w", encoding="utf-8") as f:
        json.dump({"catalog": catalog, "providers": providers, "verdict": verdict},
                   f, indent=2, sort_keys=True)
    # Inject resolved providers into live MODELS tuple (frozen dataclass → build mutable overlay)
    overlay = {}
    for m in C.MODELS:
        pinned = (verdict["per_model"].get(m.label) or {}).get("resolved_provider") or m.preferred_provider
        overlay[m.label] = pinned
    # Patch config.MODELS_BY_LABEL entries by creating new ModelV41 objects
    import dataclasses
    new_models = tuple(dataclasses.replace(m, preferred_provider=overlay[m.label]) for m in C.MODELS)
    C.MODELS = new_models
    C.MODELS_BY_LABEL = {m.label: m for m in new_models}
    for m in C.MODELS:
        log(f"pinned provider: {m.label} -> {m.preferred_provider}")

    pricing = {}
    for m in C.MODELS:
        v = verdict["per_model"].get(m.label)
        if not v:
            log(f"ABORT: no capability for {m.label}"); return
        pricing[m.slug] = {
            "prompt": v["pricing_prompt_per_mtok"] / 1e6,
            "completion": v["pricing_completion_per_mtok"] / 1e6,
        }

    bp = budget_projection(verdict)
    log(f"budget projection worst case: ${bp['total_usd_worst_case']} / cap ${bp['budget_cap_usd']} within={bp['within_cap']}")
    if not bp["within_cap"]:
        log("ABORT: projected worst case exceeds budget cap"); return

    r = orchestrator_run(client, run_dir, pricing, log)
    log(f"ORCHESTRATOR RETURN: {r.get('stopped')}  spent=${r['ledger']['spent_usd']:.4f}")


# --------------------------------------------------------------- analyze --

def cmd_analyze(args):
    run_dir = args.run_dir
    log, _ = _log_writer(os.path.join(run_dir, "logs", "dice_pilot_v41.log"))
    log(f"ANALYZE run_dir={run_dir}")
    write_all(run_dir)
    log("wrote 11 analysis CSVs + sequence/prediction/reenactment dumps")


# --------------------------------------------------------------- entry --

def main():
    ap = argparse.ArgumentParser(prog="python -m spar_dynamic.dice_pilot_v41")
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
