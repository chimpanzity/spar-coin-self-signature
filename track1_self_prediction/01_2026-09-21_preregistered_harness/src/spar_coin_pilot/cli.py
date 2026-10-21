"""Command-line interface.

    python -m spar_coin_pilot snapshot-models --config config/pilot_coin.yaml
    python -m spar_coin_pilot estimate        --config config/pilot_coin.yaml
    python -m spar_coin_pilot dry-run         --config config/pilot_coin.yaml
    python -m spar_coin_pilot generate        --config config/pilot_coin.yaml [--live] [--limit N] [--yes]
    python -m spar_coin_pilot build-trials    --config config/pilot_coin.yaml --run-id RUN_ID
    python -m spar_coin_pilot run-judgments   --config config/pilot_coin.yaml --run-id RUN_ID [--live] [--limit N] [--yes]
    python -m spar_coin_pilot validate        --config config/pilot_coin.yaml --run-id RUN_ID
    python -m spar_coin_pilot summarize       --config config/pilot_coin.yaml --run-id RUN_ID
    python -m spar_coin_pilot export          --config config/pilot_coin.yaml --run-id RUN_ID
    python -m spar_coin_pilot demo-fake       --config config/pilot_coin.yaml

Paid calls happen only in `generate` and `run-judgments`, only when the run is live
(config run.dry_run: false, or --live), and only after an interactive confirmation (or --yes).
"""

from __future__ import annotations

import argparse
import logging
import sys

import httpx

from . import pipeline
from .config import load_config
from .openrouter_client import ModelCatalogError, OpenRouterAPIError


def _add_common(p: argparse.ArgumentParser, run_id_required: bool = False) -> None:
    p.add_argument("--config", default="config/pilot_coin.yaml", help="path to the YAML config")
    p.add_argument("--run-id", required=run_id_required, default=None, help="run id (data/raw/<run_id>)")
    p.add_argument("--fake", action="store_true", help="use the deterministic fake client (no network, no cost)")
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging")


def _add_call_flags(p: argparse.ArgumentParser) -> None:
    g = p.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", help="build payloads and plans only; never call the API")
    g.add_argument("--live", action="store_true", help="make paid calls even if config run.dry_run is true")
    p.add_argument("--limit", type=int, default=None, help="cap the number of calls in this invocation (smoke test)")
    p.add_argument("--yes", action="store_true", help="skip the interactive confirmation before paid calls")
    p.add_argument("--allow-catalog-drift", action="store_true",
                   help="continue even if a model's catalog identity changed since the run started")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="spar_coin_pilot", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("snapshot-models", help="fetch the OpenRouter catalog and verify the configured IDs")
    _add_common(p)
    p = sub.add_parser("estimate", help="call counts and cost estimate from live prices; with --run-id, "
                                        "re-project the remaining cost from that run's actual token usage")
    _add_common(p)
    p = sub.add_parser("dry-run", help="full plan: prompts, payloads, placeholder trials, balance report, cost")
    _add_common(p)
    p = sub.add_parser("generate", help="source-string generation (resumable)")
    _add_common(p)
    _add_call_flags(p)
    p = sub.add_parser("build-trials", help="build the balanced per-judge trial lists")
    _add_common(p, run_id_required=True)
    p = sub.add_parser("run-judgments", help="judgment calls, one fresh context per trial (resumable)")
    _add_common(p, run_id_required=True)
    _add_call_flags(p)
    p = sub.add_parser("validate", help="PASS/FAIL validation report for a run")
    _add_common(p, run_id_required=True)
    p = sub.add_parser("summarize", help="descriptive summary (CSV + Markdown) for a run")
    _add_common(p, run_id_required=True)
    p = sub.add_parser("export", help="rebuild the flat per-call CSVs (data/derived/<run_id>/) from the raw records")
    _add_common(p, run_id_required=True)
    p = sub.add_parser("demo-fake", help="end-to-end run with the fake client (no network, no cost)")
    _add_common(p)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        cfg = load_config(args.config)
    except Exception as exc:  # config problems should be readable, not a traceback
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    try:
        if args.command == "snapshot-models":
            pipeline.cmd_snapshot_models(cfg, fake=args.fake)
        elif args.command == "estimate":
            pipeline.cmd_estimate(cfg, fake=args.fake, run_id=args.run_id)
        elif args.command == "dry-run":
            pipeline.cmd_dry_run(cfg, fake=args.fake)
        elif args.command == "generate":
            dry = args.dry_run or (cfg.run.dry_run and not args.live)
            pipeline.cmd_generate(cfg, args.run_id, dry_run=dry, limit=args.limit, yes=args.yes, fake=args.fake,
                                  allow_drift=args.allow_catalog_drift)
        elif args.command == "build-trials":
            pipeline.cmd_build_trials(cfg, args.run_id)
        elif args.command == "run-judgments":
            dry = args.dry_run or (cfg.run.dry_run and not args.live)
            pipeline.cmd_run_judgments(cfg, args.run_id, dry_run=dry, limit=args.limit, yes=args.yes, fake=args.fake,
                                       allow_drift=args.allow_catalog_drift)
        elif args.command == "validate":
            rep = pipeline.cmd_validate(cfg, args.run_id)
            return 0 if rep.complete else 1
        elif args.command == "summarize":
            pipeline.cmd_summarize(cfg, args.run_id)
        elif args.command == "export":
            pipeline.cmd_export(cfg, args.run_id)
        elif args.command == "demo-fake":
            pipeline.cmd_demo_fake(cfg)
        else:  # pragma: no cover
            print(f"unknown command {args.command}", file=sys.stderr)
            return 2
    except pipeline.UserAbort as exc:
        print(str(exc))
        return 130
    except httpx.HTTPError as exc:
        print(f"network error talking to OpenRouter ({exc.__class__.__name__}): {exc}\n"
              "Check connectivity / proxy settings; no calls were made beyond this point.", file=sys.stderr)
        return 1
    except (ModelCatalogError, OpenRouterAPIError, pipeline.ConfigConflict, RuntimeError, OSError) as exc:
        print(f"error: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
