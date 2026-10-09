"""python -m opponent_disclosure {fake|smoke|run|analyze} --run RUN [--live]"""
from __future__ import annotations

import argparse
import hashlib
import json

from spar_dynamic.phase2.client import utc_now

from . import config as C
from .analysis import analyze
from .game import Runner, progress


def main(argv=None):
    ap = argparse.ArgumentParser(prog="opponent_disclosure")
    ap.add_argument("cmd", choices=["fake", "smoke", "run", "analyze"])
    ap.add_argument("--run", required=True)
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args(argv)
    rd = C.RESULTS / a.run
    if a.cmd == "analyze":
        analyze(rd); return
    rd.mkdir(parents=True, exist_ok=True)
    cfg = rd / "config.json"
    if cfg.exists() and json.loads(cfg.read_text())["code_hash"] != C.code_hash():
        raise SystemExit("code changed since this run was created")
    if not cfg.exists():
        cfg.write_text(json.dumps({**C.frozen_config(), "code_hash": C.code_hash(), "created_utc": utc_now()}, indent=1))
    if a.cmd == "smoke":
        r = Runner(rd, live=a.live, log_name="smoke_calls.jsonl")
        for c in ("00", "11"):
            mi, msi = C.CONDITIONS[c]
            g = r.play({"game_id": f"SMK{c}", "condition": c, "matcher_informed": mi, "mismatcher_informed": msi, "replicate": 0}, prefix="smoke")
            print(g["game_id"], g["status"], g["n_valid_rounds"], g["note"])
        return
    live = a.live and a.cmd == "run"
    r = Runner(rd, live=live)
    progress(rd, f"RUN start ({'LIVE' if live else 'FAKE'}), cap ${C.BUDGET_CAP_USD:.0f}")
    games = r.run_all()
    (rd / "freeze.json").write_text(json.dumps({"frozen_utc": utc_now(), "code_hash": C.code_hash(),
                                                "game_logs_sha256": hashlib.sha256((rd / "game_logs.jsonl").read_bytes()).hexdigest()}, indent=1))
    if r.stop.is_set():
        progress(rd, "STOPPED (budget); partial results preserved")
    analyze(rd)
    progress(rd, "RUN complete: report.md written")


if __name__ == "__main__":
    main()
