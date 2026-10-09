"""Blind Twin CLI.

    python -m blind_twin fake  --run RUN          # complete offline run with a fake client
    python -m blind_twin smoke --run RUN --live   # 4 technical calls, stored separately
    python -m blind_twin run   --run RUN --live   # games -> freeze -> judges -> analysis (resumable)
    python -m blind_twin analyze --run RUN
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from spar_dynamic.phase2.client import utc_now

from . import config as C
from .runner import Runner, progress
from .score import analyze


def prepare(rd: Path) -> None:
    rd.mkdir(parents=True, exist_ok=True)
    cfgp = rd / "config.json"
    cfg = {**C.frozen_config(), "code_hash": C.code_hash(), "created_utc": utc_now()}
    if cfgp.exists():
        old = json.loads(cfgp.read_text())
        if old["code_hash"] != cfg["code_hash"]:
            raise SystemExit(f"code changed since this run was created ({old['code_hash'][:12]} -> {cfg['code_hash'][:12]})")
    else:
        cfgp.write_text(json.dumps(cfg, indent=1))
    tdir = C.PKG / "templates"
    tdir.mkdir(exist_ok=True)
    for name, text in C.frozen_config()["templates"].items():
        (tdir / f"{name}.txt").write_text(text + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="blind_twin")
    ap.add_argument("cmd", choices=["fake", "smoke", "smoke-games", "run", "analyze"])
    ap.add_argument("--run", required=True)
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args(argv)
    rd = C.RESULTS / a.run
    if a.cmd == "analyze":
        analyze(rd); return
    prepare(rd)
    if a.cmd == "smoke":
        r = Runner(rd, live=a.live, log_name="smoke_calls.jsonl")
        for rec in r.smoke():
            print(rec["slot_id"], rec["status"], rec.get("parse"), repr(((rec.get("response") or {}).get("text") or "")[:80]),
                  rec.get("returned_provider"), f"${rec.get('cost_usd', 0):.5f}")
        return
    if a.cmd == "smoke-games":
        r = Runner(rd, live=a.live, log_name="smoke_calls.jsonl")
        for g in r.smoke_games():
            print(g["game_id"], g["status"], g["n_valid_rounds"], g["note"])
        return
    live = a.live and a.cmd == "run"
    r = Runner(rd, live=live)
    progress(rd, f"RUN start ({'LIVE' if live else 'FAKE'}), cap ${C.BUDGET_CAP_USD:.0f}")
    if (rd / "freeze.json").exists():
        games = [json.loads(l) for l in (rd / "game_logs.jsonl").read_text().splitlines() if l.strip()]
        progress(rd, "games already frozen; resuming judges")
    else:
        games = r.run_games()
        if r.stop.is_set():
            progress(rd, "STOPPED during games (budget); partial game logs preserved; judges not started")
            return
        r.freeze(games)
    r.run_judges()
    if r.stop.is_set():
        progress(rd, "STOPPED during judging (budget); partial results preserved")
    analyze(rd)
    progress(rd, "RUN complete: report.md written")


if __name__ == "__main__":
    main()
