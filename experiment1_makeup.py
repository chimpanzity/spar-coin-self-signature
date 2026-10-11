"""Make-up games for Qwen-interrupted games (Study 1 Experiment 1). Rules: EXPERIMENT1_MAKEUP_GAMES.md, Section 3.

For each interrupted game in a run, play fresh 20-round games in the same cell (<orig>_MU1, _MU2, ...) with the frozen
package until one completes. Never touches calls.jsonl / game_logs.jsonl; writes makeup_calls.jsonl,
makeup_game_logs.jsonl and a combined with_makeups/ analysis. Idempotent: rerunning resumes from logged calls.

    python experiment1_makeup.py {rps|mp} [--live] [--rd DIR]     # without --live: fake transport (needs --rd copy)
    python experiment1_makeup.py {rps|mp} --combine-only
"""
from __future__ import annotations

import argparse
import importlib
import json
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent
NOTES = REPO / "EXPERIMENT1_MAKEUP_GAMES.md"
GAMES = {"rps": ("opponent_disclosure_rps_3models", "rps3m-p2-20261010", "frozen_manifest.json"),
         "mp": ("opponent_disclosure_mp_3models", "mp3m-p2-20261010", "manifest.json")}
CELL_KEYS = ("p1_model", "p2_model", "condition", "p1_informed", "p2_informed", "replicate")


def _jsonl(p: Path):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def combine(game: str, rd: Path) -> Path:
    pkg = GAMES[game][0]
    out = rd / "with_makeups"
    out.mkdir(exist_ok=True)
    games = _jsonl(rd / "game_logs.jsonl") + _jsonl(rd / "makeup_game_logs.jsonl")
    (out / "game_logs.jsonl").write_text("".join(json.dumps(g) + "\n" for g in games))
    (out / "calls.jsonl").write_text((rd / "calls.jsonl").read_text() + ((rd / "makeup_calls.jsonl").read_text() if (rd / "makeup_calls.jsonl").exists() else ""))
    (out / "README.md").write_text("Amended (make-up) analysis: original games plus all make-up attempts; see "
                                   "EXPERIMENT1_MAKEUP_GAMES.md. 'planned' counts in REPORT.md are games attempted per "
                                   "cell. Original raw files are in the parent folder, unchanged.\n")
    importlib.import_module(f"{pkg}.analysis").analyze(out)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("game", choices=list(GAMES))
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--rd")
    ap.add_argument("--combine-only", action="store_true")
    a = ap.parse_args(argv)
    pkg, run, manname = GAMES[a.game]
    C = importlib.import_module(f"{pkg}.config")
    G = importlib.import_module(f"{pkg}.game")
    rd = Path(a.rd) if a.rd else C.RESULTS / run
    if a.combine_only:
        print(combine(a.game, rd)); return
    if a.live and a.rd:
        raise SystemExit("--live only on the real run folder")
    man = json.loads((rd / manname).read_text())
    if man["code_hash"] != C.code_hash() or man["schedule_sha256"] != G.schedule_hash(G.schedule()):
        raise SystemExit("package code or schedule differs from the frozen manifest; refusing")
    targets = [g for g in _jsonl(rd / "game_logs.jsonl") if g["status"] != "complete"]
    prior = {g["game_id"]: g for g in _jsonl(rd / "makeup_game_logs.jsonl")}
    r = G.Runner(rd, live=a.live, log_name="makeup_calls.jsonl")
    r.acct.spent += sum(float(c.get("cost_usd") or 0) for c in _jsonl(rd / "makeup_calls.jsonl"))
    lock = threading.Lock()
    mg = dict(prior)
    tag = f"{a.game.upper()} {run}" + ("" if a.live else " [FAKE]")
    G.progress(rd, f"MAKEUP start ({tag}): {len(targets)} targets; spent incl. make-ups ${r.acct.spent:.2f}, cap ${C.BUDGET_CAP_USD:.0f}")
    if a.live:
        with open(NOTES, "a") as f:
            f.write(f"\n### {tag}: launch {time.strftime('%Y-%m-%d %H:%M:%S')}, {len(targets)} targets, spent before make-ups "
                    f"${r.acct.spent:.2f} of ${C.BUDGET_CAP_USD:.0f}\n\n| time | target | attempt | status | valid rounds | note | spent |\n|---|---|---:|---|---:|---|---:|\n")

    def record(res):
        with lock:
            new = prior.get(res["game_id"], {}).get("status") != res["status"]
            mg[res["game_id"]] = res
            tmp = rd / "makeup_game_logs.jsonl.tmp"
            tmp.write_text("".join(json.dumps(g) + "\n" for g in sorted(mg.values(), key=lambda g: (g["makeup_for"], g["attempt"]))))
            tmp.replace(rd / "makeup_game_logs.jsonl")
            if new and a.live:
                with open(NOTES, "a") as f:
                    f.write(f"| {time.strftime('%H:%M:%S')} | {res['makeup_for']} | {res['attempt']} | {res['status']} | "
                            f"{res['n_valid_rounds']} | {res['note'] or ''} | ${r.acct.spent:.2f} |\n")
            if new:
                G.progress(rd, f"  MAKEUP {res['game_id']}: {res['status']} {res['n_valid_rounds']} rounds {res['note']} (spent ${r.acct.spent:.2f})")

    def fill(t):
        k = 1
        while not r.stop.is_set():
            g = {key: t[key] for key in CELL_KEYS}
            g.update(game_id=f"{t['game_id']}_MU{k}", makeup_for=t["game_id"], attempt=k)
            res = r.play(g, prefix="makeup")
            if res["status"] == "interrupted" and "budget/stop" in res["note"]:
                return res                                    # not an attempt outcome; resumable
            record(res)
            if res["status"] == "complete":
                return res
            k += 1
        return None

    with ThreadPoolExecutor(max_workers=min(16, len(targets) or 1)) as pool:
        results = list(pool.map(fill, targets))
    filled = sum(1 for x in results if x and x["status"] == "complete")
    msg = f"MAKEUP end ({tag}): {filled}/{len(targets)} targets filled; attempts {len(mg)}; spent ${r.acct.spent:.2f}" + ("; STOPPED at budget cap" if r.stop.is_set() else "")
    G.progress(rd, msg)
    if a.live:
        with open(NOTES, "a") as f:
            f.write(f"\n{msg}\n")
    combine(a.game, rd)


if __name__ == "__main__":
    main()
