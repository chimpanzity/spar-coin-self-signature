"""CLI for the dice-pilot extension: preflight / smoke-test / run / analyze."""

from __future__ import annotations

import argparse, json, os, time

from . import config as C
from . import prompts
from .capability_preflight import (
    write_capability_report, budget_projection,
    fetch_capabilities, verify_against_config,
    reasoning_disable_smoke_test,
)
from .orchestrator import build_manifest, run as orchestrator_run
from .analysis import write_all
from spar_dynamic.dice_pilot.runner import make_openrouter_client


EXPERIMENT_DIR_NAME = "dice_pilot_ext"


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
    return os.path.join(data_root, EXPERIMENT_DIR_NAME, run_id or f"dicepilotext-{_ts()}")


# --------------------------------------------------------------- preflight (unpaid) --

def cmd_preflight(args):
    run_dir = _run_dir(args.data_root, args.run_id or f"dicepilotext-{_ts()}-preflight")
    os.makedirs(run_dir, exist_ok=True)
    log, _ = _log_writer(os.path.join(run_dir, "logs", "dice_pilot_ext.log"))
    log(f"START preflight run_dir={run_dir}")

    prompts.assert_consistency()
    log("prompt consistency: ok (byte-exact with DICE_PILOT_v3.1)")

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
        log(f"  {r['model']}/{r['config']}: supported={r['supported']} "
            f"calls={r['n_calls']} per-call-worst=${r['per_call_usd_worst_case']} "
            f"subtotal=${r['subtotal_usd_worst_case']}")

    manifest = build_manifest()
    with open(os.path.join(run_dir, "experiment_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"spec_version": "DICE_PILOT_EXT_v1.0",
                    "scheduling_seed": C.SCHEDULING_SEED,
                    "n_entries": len(manifest),
                    "entries": [e.__dict__ if hasattr(e, '__dict__') else dict(e._asdict())
                                 for e in manifest]},
                   f, indent=2, sort_keys=True, default=str)
    log(f"manifest built: {len(manifest)} entries")

    with open(os.path.join(run_dir, "prompts_frozen.txt"), "w", encoding="utf-8") as f:
        f.write("PHASE 1:\n")
        f.write(prompts.PHASE1_PROMPT + "\n\n")
        for pos in sorted(prompts.PHASE2_ORDINALS):
            f.write(f"PHASE 2 (position {pos} = {prompts.PHASE2_ORDINALS[pos]!r}):\n")
            f.write(prompts.phase2_prompt(pos) + "\n\n")
    log("prompts frozen to prompts_frozen.txt")

    print("\nPREFLIGHT SUMMARY")
    print("=" * 60)
    print(f"Run dir: {run_dir}")
    print(f"Capability drift: {'none' if verdict['ok'] else 'DETECTED'}")
    print(f"Manifest size: {len(manifest)} (expected {C.TOTAL_CALLS_MAX} = 3 * 25)")
    print(f"Worst-case total cost: ${bp['total_usd_worst_case']} (cap ${bp['budget_cap_usd']})")
    print(f"Within cap: {bp['within_cap']}")
    print("\nNEXT: review this run_dir and approve. If approved, call:")
    print(f"  python3 -m spar_dynamic.dice_pilot_ext smoke --run-id {os.path.basename(run_dir)} --live --yes")
    print(f"  python3 -m spar_dynamic.dice_pilot_ext run --run-id <fresh id> --live --yes")


# --------------------------------------------------------------- smoke (paid, minimal) --

def cmd_smoke(args):
    assert args.live and args.yes, "require --live --yes"
    run_dir = _run_dir(args.data_root, args.run_id or f"dicepilotext-{_ts()}-smoke")
    os.makedirs(run_dir, exist_ok=True)
    log, _ = _log_writer(os.path.join(run_dir, "logs", "dice_pilot_ext.log"))
    log(f"START smoke run_dir={run_dir}")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    assert api_key, "OPENROUTER_API_KEY not set"
    client = make_openrouter_client(api_key)

    results = {}
    for m in C.MODELS:
        log(f"smoke-test {m.label} ({m.slug}): reasoning.enabled=False with 32-token budget")
        res = reasoning_disable_smoke_test(client, m.label, m.slug, log)
        results[m.label] = res
        log(f"  {m.label}: accepted={res['accepted']}  err={res['error'][:120]!r}  "
            f"pt={res.get('prompt_tokens')} ct={res.get('completion_tokens')}")

    with open(os.path.join(run_dir, "reasoning_disable_smoke.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, sort_keys=True)
    print("\nSMOKE TEST SUMMARY")
    print("=" * 60)
    for label, r in results.items():
        print(f"  {label}: reasoning.enabled=False  ->  {'ACCEPTED' if r['accepted'] else 'REJECTED'}")
        if not r["accepted"]:
            print(f"    error: {r['error'][:200]}")
    print("\nNEXT: inspect reasoning_disable_smoke.json. Update config.py "
          "ExtModel.supports_reasoning_disable per model if any disable was ACCEPTED, "
          "and relabel to R0. Then run the paid experiment.")


# --------------------------------------------------------------- run (paid) --

def cmd_run(args):
    assert args.live and args.yes, "require --live --yes"
    run_dir = _run_dir(args.data_root, args.run_id or f"dicepilotext-{_ts()}")
    os.makedirs(run_dir, exist_ok=True)
    log, _ = _log_writer(os.path.join(run_dir, "logs", "dice_pilot_ext.log"))
    log(f"START run run_dir={run_dir}")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    assert api_key, "OPENROUTER_API_KEY not set"
    client = make_openrouter_client(api_key)

    caps = fetch_capabilities(client)
    verdict = verify_against_config(caps)
    with open(os.path.join(run_dir, "model_capabilities.json"), "w", encoding="utf-8") as f:
        json.dump({"caps": caps, "verdict": verdict}, f, indent=2, sort_keys=True)
    if not verdict["ok"]:
        log(f"ABORT: capability flags drift: {verdict['issues']}"); return

    pricing = {}
    for m in C.MODELS:
        v = verdict["per_model"][m.label]
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
    log, _ = _log_writer(os.path.join(run_dir, "logs", "dice_pilot_ext.log"))
    log(f"ANALYZE run_dir={run_dir}")
    results = write_all(run_dir)
    log("wrote phase1_stability, pooled_digit_baseline, prediction_accuracy, "
        "response_failures, pilot_decision_rule")
    return results


# --------------------------------------------------------------- entry --

def main():
    ap = argparse.ArgumentParser(prog="python -m spar_dynamic.dice_pilot_ext")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def _common(sp):
        sp.add_argument("--data-root", default="data/spar_dynamic")
        sp.add_argument("--run-id", default="")

    sp = sub.add_parser("preflight"); _common(sp); sp.set_defaults(func=cmd_preflight)

    sp = sub.add_parser("smoke"); _common(sp)
    sp.add_argument("--live", action="store_true", required=True)
    sp.add_argument("--yes", action="store_true", required=True)
    sp.set_defaults(func=cmd_smoke)

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
