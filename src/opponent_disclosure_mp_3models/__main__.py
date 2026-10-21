"""python -m opponent_disclosure_mp_3models {plan|validate|fake|smoke|run|analyze} --run RUN [--live]

plan      : create run dir, frozen manifest.json + hashes, config, price/endpoint snapshot, cost estimate,
            APPROVAL.md (NOT approved). No paid calls.
validate  : run unit tests + a no-network fake full run; write VALIDATION_REPORT.md.
smoke     : 3 technical games (one same-model game per model, condition 11), live; needs approval.
run       : full schedule, live; needs approval. Resumable.
analyze   : analysis + report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import statistics
import subprocess
import sys
import urllib.request
from pathlib import Path

from spar_dynamic.phase2.client import utc_now

from . import config as C
from .analysis import analyze
from .game import Runner, approved, parse_move, player_prompt, progress, schedule, schedule_hash
import repo_paths  # reorganisation 2026-10-21: see src/repo_paths.py

REPO = repo_paths.REPO   # was C.PKG.parent
PRIOR_RPS_RUNS = [str(repo_paths.legacy(p)) for p in [
    "blind_twin_rps/results/rps-20261009T1024Z", "blind_twin_rps/results/rps-qf-20261009T1045Z",
    "blind_twin_rps/results/rps-qa-20261009T1124Z"]]


def cost_estimate() -> dict:
    per = {m: [] for m in C.ORDER}
    for rd in PRIOR_RPS_RUNS:
        for l in (REPO / rd / "calls.jsonl").read_text().splitlines():
            r = json.loads(l)
            if r.get("kind") == "player" and r["status"] == "completed" and r["model"] in per:
                per[r["model"]].append(float(r["cost_usd"]))
    calls_per_model = C.N_CALLS // 3
    est = {}
    for m, v in per.items():
        v.sort()
        est[m] = {"prior_player_calls": len(v), "mean_usd": statistics.mean(v), "p95_usd": v[int(0.95 * (len(v) - 1))],
                  "max_usd": v[-1], "planned_calls": calls_per_model,
                  "expected_usd": calls_per_model * statistics.mean(v), "pessimistic_usd": calls_per_model * v[int(0.95 * (len(v) - 1))]}
    exp = sum(e["expected_usd"] for e in est.values())
    pes = sum(e["pessimistic_usd"] for e in est.values())
    smoke = 3 * 40 * max(e["mean_usd"] for e in est.values())
    reservation = 2 * C.GAME_CONCURRENCY * (C.MAX_TOKENS * 5e-5 + 4000 * 1e-5)
    return {"per_model": est, "expected_total_usd": exp, "pessimistic_total_usd": pes,
            "retry_allowance_usd": 0.03 * pes, "smoke_usd": smoke, "max_inflight_reservation_usd": reservation,
            "pessimistic_with_retries_and_smoke_usd": pes * 1.03 + smoke, "cap_usd": C.BUDGET_CAP_USD,
            "basis": "per-call costs of all completed player calls in the three Blind Twin RPS runs (same endpoints/settings; MP prompts are about the same length). The Astra-only MP pilot od-20261009T1200Z ($0.0052/call) is consistent with the Astra figure."}


def cmd_plan(rd: Path) -> None:
    rd.mkdir(parents=True, exist_ok=True)
    sched = schedule()
    man = {"created_utc": utc_now(), "protocol": C.PROTOCOL, "code_hash": C.code_hash(), "template_sha256": C.template_hashes(),
           "schedule_sha256": schedule_hash(sched), "n_games": len(sched), "n_planned_calls": C.N_CALLS, "schedule": sched}
    (rd / "manifest.json").write_text(json.dumps(man, indent=1))
    (rd / "resolved_config.json").write_text(json.dumps(C.resolved_config(), indent=1))
    snaps = {"fetched_utc": utc_now(), "endpoints": {}}
    for m in C.MODELS.values():
        with urllib.request.urlopen(f"https://openrouter.ai/api/v1/models/{m['slug']}/endpoints", timeout=60) as r:
            d = json.load(r)["data"]
        ep = [e for e in d["endpoints"] if e["tag"].split("/")[0] == m["provider"]]
        snaps["endpoints"][m["slug"]] = [{"provider": e["provider_name"], "tag": e["tag"], "status": e.get("status"),
                                          "pricing": e["pricing"], "supported_parameters": e.get("supported_parameters")} for e in ep]
    (rd / "endpoint_and_price_snapshots.json").write_text(json.dumps(snaps, indent=1))
    shutil.copy(C.PKG / "protocol.md", rd / "protocol.md")
    est = cost_estimate()
    (rd / "cost_estimate.json").write_text(json.dumps(est, indent=1))
    L = ["# APPROVAL", "", f"Run `{rd.name}`. Protocol {C.PROTOCOL}. Hard cap ${C.BUDGET_CAP_USD:.2f} for this experiment (smoke + retries included).", "",
         "## Cost estimate (from prior per-call costs on the same endpoints)", "", "| model | planned calls | mean $/call | p95 $/call | expected $ | pessimistic $ |", "|---|---:|---:|---:|---:|---:|"]
    for m, e in est["per_model"].items():
        L.append(f"| {m} | {e['planned_calls']} | {e['mean_usd']:.5f} | {e['p95_usd']:.5f} | {e['expected_usd']:.2f} | {e['pessimistic_usd']:.2f} |")
    L += ["", f"- Expected total: ${est['expected_total_usd']:.2f}; pessimistic (every call at p95): ${est['pessimistic_total_usd']:.2f}; "
          f"with 3% retry allowance and ${est['smoke_usd']:.2f} smoke: ${est['pessimistic_with_retries_and_smoke_usd']:.2f}.",
          f"- Maximum in-flight worst-case reservation: ${est['max_inflight_reservation_usd']:.2f} (enforced against the cap before every dispatch).", "",
          "## Status", "", "LIVE RUN APPROVED BY CHRIS: no", "",
          "Live calls are blocked until the line above reads exactly `LIVE RUN APPROVED BY CHRIS: yes`, which Claude writes only after Chris's explicit approval in chat.", ""]
    (rd / "APPROVAL.md").write_text("\n".join(L))
    progress(rd, f"PLAN: manifest ({len(sched)} games, schedule {man['schedule_sha256'][:12]}), config, snapshots, cost estimate written; not approved")


def fable_parser_check() -> str:
    """Take every multi-line Fable response from earlier runs (Blind Twin RPS, Phase 2) and map the final RPS move to a
    shape; the MP parser must recover exactly that shape from the explanation-plus-final-line text."""
    swap = {"ROCK": "STAR", "PAPER": "TRIANGLE", "SCISSORS": "STAR"}
    n = ok = 0
    for rd in PRIOR_RPS_RUNS:
        for l in (REPO / rd / "calls.jsonl").read_text().splitlines():
            r = json.loads(l)
            text = ((r.get("response") or {}).get("text") or "")
            if r.get("model") != "fable" or len([x for x in text.splitlines() if x.strip()]) < 2:
                continue
            lines = text.rstrip().splitlines()
            last = lines[-1].strip().upper()
            if last not in swap:
                continue
            lines[-1] = lines[-1].upper().replace(last, swap[last])
            n += 1
            ok += parse_move("\n".join(lines))[0] == swap[last]
    return f"- Multi-line Fable responses re-expressed as shapes: {n}; parsed to the intended shape: {ok}. {'PASS' if n and ok == n else ('NO MULTI-LINE CASES' if n == 0 else 'FAIL')}"


def prompt_invariants() -> str:
    rows = [{"round": 1, "p1": "STAR", "p2": "TRIANGLE", "result": "Mismatcher"}]
    bad = []
    for own, opp in C.PAIRINGS:
        for seat in C.ROLES:
            i, u = (player_prompt(seat, own, opp, f, rows, 2).splitlines() for f in (True, False))
            diff = [k for k, (x, y) in enumerate(zip(i, u)) if x != y]
            if len(i) != len(u) or len(diff) != 1 or C.MODELS[opp]["name"] not in i[diff[0]]:
                bad.append((own, opp, seat))
    return f"- Informed vs uninformed prompts differ only in the opponent-identity line, which names the true opponent, for all 9 pairings x 2 seats: {'PASS' if not bad else 'FAIL ' + str(bad)}"


def cmd_validate(rd: Path) -> None:
    t = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_mp_disclosure_3models.py"], cwd=REPO, capture_output=True, text=True)
    fake = C.RESULTS / f"_fake_{rd.name}"
    if fake.exists():
        shutil.rmtree(fake)
    r = Runner(fake, live=False)
    games = r.run(schedule())
    res = analyze(fake)
    calls = [json.loads(l) for l in (fake / "calls.jsonl").read_text().splitlines()]
    hist_equal = all(len(set(json.dumps(c["public_history"]) for c in calls if c["game_id"] == g and c["round"] == t)) == 1
                     for g, t in {(c["game_id"], c["round"]) for c in calls})
    L = ["# VALIDATION REPORT", "", f"Generated {utc_now()} for run `{rd.name}`; code hash {C.code_hash()[:12]}.", "",
         "## Unit tests", "", "```", t.stdout.strip()[-3000:], "```", "",
         "## No-network fake full run", "",
         f"- Games: {len(games)} (expected {C.N_GAMES}); complete: {sum(g['status'] == 'complete' for g in games)}.",
         f"- Player calls: {len(calls)} (expected {C.N_CALLS}); transport: {calls[0]['transport']}.",
         f"- Both seats received identical history in every round: {hist_equal}.",
         f"- D computed: {res['contrasts']['D']}; independent rescore D: {res['rescore']['D_rescore']}; round-result mismatches: {res['rescore']['round_result_mismatches']}.",
         f"- Outputs: {sorted(p.name for p in fake.iterdir() if p.is_file())}", "",
         "## Parser against real Fable explanation-plus-final-answer responses", "", fable_parser_check(), "",
         "## Prompt invariants", "", prompt_invariants(), "",
         f"Result: {'PASS' if t.returncode == 0 and 'FAIL' not in fable_parser_check() + prompt_invariants() and len(calls) == C.N_CALLS and hist_equal and res['rescore']['round_result_mismatches'] == 0 and abs((res['contrasts']['D'] or 0) - (res['rescore']['D_rescore'] or 0)) < 1e-12 else 'FAIL'}", ""]
    (rd / "VALIDATION_REPORT.md").write_text("\n".join(L))
    shutil.rmtree(fake)
    progress(rd, "VALIDATE: " + L[-2])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="opponent_disclosure_mp_3models")
    ap.add_argument("cmd", choices=["plan", "validate", "fake", "smoke", "run", "analyze"])
    ap.add_argument("--run", required=True)
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args(argv)
    rd = C.RESULTS / a.run
    if a.cmd == "plan":
        cmd_plan(rd); return
    if a.cmd == "validate":
        cmd_validate(rd); return
    if a.cmd == "analyze":
        analyze(rd); return
    if a.cmd == "fake":
        r = Runner(rd, live=False); r.run(schedule()); analyze(rd); return
    man = json.loads((rd / "manifest.json").read_text())
    if man["code_hash"] != C.code_hash() or man["schedule_sha256"] != schedule_hash(schedule()):
        raise SystemExit("code or schedule changed since the manifest was frozen")
    if not (a.live and approved(rd)):
        raise SystemExit("not approved for live calls (APPROVAL.md) or --live missing; no network calls made")
    if a.cmd == "smoke":
        r = Runner(rd, live=True, log_name="smoke_calls.jsonl")
        for m in C.ORDER:
            g = {"game_id": f"SMK_{m}", "p1_model": m, "p2_model": m, "condition": "11", "p1_informed": True,
                 "p2_informed": True, "replicate": 0}
            res = r.play(g, prefix="smoke")
            progress(rd, f"SMOKE {res['game_id']}: {res['status']} {res['n_valid_rounds']} rounds {res['note']} (spent ${r.acct.spent:.2f})")
        return
    r = Runner(rd, live=True)
    progress(rd, f"RUN start, cap ${C.BUDGET_CAP_USD:.0f}")
    r.run(man["schedule"])
    if r.stop.is_set():
        progress(rd, "STOPPED: budget reached; partial results preserved; incomplete cells reported")
    analyze(rd)
    progress(rd, "RUN complete: REPORT.md written")


if __name__ == "__main__":
    main()
