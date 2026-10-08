"""Phase 2 command-line entry point.

    python -m spar_dynamic.phase2 init      --run RUN
    python -m spar_dynamic.phase2 generate  --run RUN --split development [--smoke-only] [--live]
    python -m spar_dynamic.phase2 stage1    --run RUN [--live]    # fixtures, report, rehearsal, headroom
    python -m spar_dynamic.phase2 freeze    --run RUN
    python -m spar_dynamic.phase2 stage2    --run RUN [--live]    # test generation + core tasks
    python -m spar_dynamic.phase2 retained  --run RUN [--live]    # named + historical
    python -m spar_dynamic.phase2 analyze   --run RUN
    python -m spar_dynamic.phase2 verify    --run RUN --fake      # full fake end-to-end

Without --live a FakeTransport is used and nothing is sent anywhere.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict

from . import config as C
from .client import (Accountant, Executor, FakeTransport, OpenRouterTransport,
                     fetch_prices, git_state, progress, utc_now)
from .parse import ANSWER_PARSER_VERSION, GEN_PARSER_VERSION


def run_dir_for(run: str) -> Path:
    d = C.DATA_ROOT / run
    d.mkdir(parents=True, exist_ok=True)
    return d


def recipe_hash() -> Dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in C.recipe_files()}


def combined_hash() -> str:
    h = hashlib.sha256()
    for k, v in sorted(recipe_hash().items()):
        h.update(f"{k}:{v}\n".encode())
    return h.hexdigest()


def spent_so_far(run_dir: Path) -> float:
    total = 0.0
    p = run_dir / "calls.jsonl"
    if p.exists():
        last: Dict[str, float] = {}
        with open(p, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    # every record (including superseded resumes) may have cost money
                    total += float(r.get("cost_usd") or 0.0)
    return total


def make_executor(run_dir: Path, live: bool) -> Executor:
    slugs = [m.slug for m in C.CORE_MODELS.values()] + [C.HISTORICAL.slug]
    prices_path = run_dir / "pricing_snapshot.json"
    if prices_path.exists():
        prices = json.loads(prices_path.read_text())
    else:
        prices = fetch_prices(slugs)
        prices_path.write_text(json.dumps({"fetched_utc": utc_now(), **prices}, indent=1))
    prices = {k: v for k, v in prices.items() if k != "fetched_utc"}
    acct = Accountant(C.BUDGET_CAP_USD, prices, spent=spent_so_far(run_dir))
    transport = OpenRouterTransport() if live else FakeTransport()
    ctx = {"code": git_state(), "recipe_hash": combined_hash(),
           "parsers": {"generation": GEN_PARSER_VERSION, "answer": ANSWER_PARSER_VERSION},
           "protocol": C.PROTOCOL}
    return Executor(run_dir, transport, acct, ctx)


def cmd_init(args) -> None:
    rd = run_dir_for(args.run)
    cfg = {
        "protocol": C.PROTOCOL, "master_seed": C.MASTER_SEED, "created_utc": utc_now(),
        "core_models": {k: v.__dict__ for k, v in C.CORE_MODELS.items()},
        "historical": C.HISTORICAL.__dict__, "historical_temperatures": C.HIST_TEMPERATURES,
        "generation_prompts": C.GEN_PROMPTS, "planned_executions": C.PLANNED_EXECUTIONS,
        "budget_cap_usd": C.BUDGET_CAP_USD, "recipe_hashes": recipe_hash(),
        "key_source": "previous pilot key file (path recorded, value never logged)",
    }
    (rd / "config_resolved.json").write_text(json.dumps(cfg, indent=1, default=str))
    snaps = rd / "endpoint_snapshots"
    snaps.mkdir(exist_ok=True)
    for slug in [m.slug for m in C.CORE_MODELS.values()] + [C.HISTORICAL.slug]:
        with urllib.request.urlopen(f"https://openrouter.ai/api/v1/models/{slug}/endpoints", timeout=60) as r:
            (snaps / (slug.replace("/", "__") + ".json")).write_text(r.read().decode())
    progress(rd, f"init: run {args.run} created; recipe hash {combined_hash()[:12]}")


def cmd_generate(args) -> None:
    from .tasks import generation_slots
    rd = run_dir_for(args.run)
    ex = make_executor(rd, args.live)
    slots = generation_slots(args.split)
    if args.smoke_only:
        slots = [s for s in slots if s.meta.get("smoke")]
    ex.run(slots, f"generation/{args.split}{' smoke' if args.smoke_only else ''}")
    from .corpus import load_calls, sequence_rows, write_csv, cell_summary
    rows = sequence_rows(load_calls(rd))
    write_csv(rd / "sequences.csv", rows)
    for c in cell_summary([r for r in rows if r["split"] == args.split]):
        progress(rd, f"  {c['split']}/{c['source']}/{c['prompt']}: {c['valid']}/{c['attempted']} valid "
                     f"{c['failure_reasons'] or ''} mean_heads={c['mean_heads']} switch={c['switch_rate']}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="spar_dynamic.phase2")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("init", "generate", "stage1", "freeze", "stage2", "retained", "analyze", "verify"):
        sp = sub.add_parser(name)
        sp.add_argument("--run", required=True)
        sp.add_argument("--live", action="store_true")
        sp.add_argument("--fake", action="store_true")
        sp.add_argument("--split", default="development")
        sp.add_argument("--smoke-only", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd == "init":
        cmd_init(args)
    elif args.cmd == "generate":
        cmd_generate(args)
    else:
        from . import pipeline
        getattr(pipeline, f"cmd_{args.cmd}")(args)


if __name__ == "__main__":
    main()
