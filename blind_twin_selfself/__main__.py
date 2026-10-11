"""python -m blind_twin_selfself {plan|validate|run|analyze} --run RUN [--live]

plan     : frozen manifest (game-log hash, schedule, code/template hashes), endpoint+price snapshot, cost estimate,
           APPROVAL.md (not approved). No paid calls.
validate : unit tests + no-network fake full run + checks; VALIDATION_REPORT.md.
run      : all judge calls, live; needs approval; resumable; then analysis.
analyze  : analysis + REPORT.md.
"""
from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
import urllib.request

from spar_dynamic.phase2.client import utc_now

from . import config as C
from .judge import Runner, approved, games_hash, judge_prompt, load_games, progress, schedule, schedule_hash
from .score import analyze

PRIOR = ["blind_twin/results/bt2-20261009T0957Z", "blind_twin_rps/results/rps-20261009T1024Z",
         "blind_twin_rps/results/rps-qf-20261009T1045Z", "blind_twin_rps/results/rps-qa-20261009T1124Z"]


def cost_estimate():
    per = {m: [] for m in C.ORDER}
    for rd in PRIOR:
        for l in (C.REPO / rd / "calls.jsonl").read_text().splitlines():
            r = json.loads(l)
            if r.get("kind") == "judge" and r.get("status") == "completed":
                per[r["model"]].append(float(r["cost_usd"]))
    n = C.N_CALLS // 3
    est = {}
    for m, v in per.items():
        v.sort()
        p95 = v[int(0.95 * (len(v) - 1))]
        est[m] = {"prior_judge_calls": len(v), "mean_usd": statistics.mean(v), "p95_usd": p95, "planned_calls": n,
                  "expected_usd": n * statistics.mean(v), "pessimistic_usd": n * p95}
    exp = sum(e["expected_usd"] for e in est.values()); pes = sum(e["pessimistic_usd"] for e in est.values())
    return {"per_model": est, "expected_total_usd": exp, "pessimistic_total_usd": pes, "pessimistic_with_3pct_retries": pes * 1.03,
            "cap_usd": C.BUDGET_CAP_USD, "basis": "judge calls in the four earlier Blind Twin runs (same endpoints/settings, similar prompts)"}


def cmd_plan(rd):
    rd.mkdir(parents=True, exist_ok=True)
    games = load_games()
    sched = schedule(games)
    man = {"created_utc": utc_now(), "protocol": C.PROTOCOL, "code_hash": C.code_hash(), "template_sha256": C.template_hashes(),
           "games_sha256": games_hash(games), "games": [g["gid"] for g in games], "schedule_sha256": schedule_hash(sched),
           "n_calls": len(sched), "false_label": C.FALSE_LABEL, "sources": C.SOURCES, "source_conditions": C.SOURCE_CONDITIONS, "info": C.INFO}
    (rd / "manifest.json").write_text(json.dumps(man, indent=1))
    (rd / "schedule.json").write_text(json.dumps(sched))
    snaps = {"fetched_utc": utc_now(), "endpoints": {}}
    for m in C.MODELS.values():
        with urllib.request.urlopen(f"https://openrouter.ai/api/v1/models/{m['slug']}/endpoints", timeout=60) as r:
            d = json.load(r)["data"]
        snaps["endpoints"][m["slug"]] = [{"provider": e["provider_name"], "tag": e["tag"], "status": e.get("status"), "pricing": e["pricing"]}
                                         for e in d["endpoints"] if e["tag"].split("/")[0] == m["provider"]]
    (rd / "endpoint_and_price_snapshots.json").write_text(json.dumps(snaps, indent=1))
    shutil.copy(C.PKG / "protocol.md", rd / "protocol.md")
    est = cost_estimate()
    (rd / "cost_estimate.json").write_text(json.dumps(est, indent=1))
    L = ["# APPROVAL", "", f"Run `{rd.name}`. Protocol {C.PROTOCOL}. Hard cap ${C.BUDGET_CAP_USD:.2f}.", "",
         "| judge | planned calls | mean $/call | p95 $/call | expected $ | pessimistic $ |", "|---|---:|---:|---:|---:|---:|"]
    for m, e in est["per_model"].items():
        L.append(f"| {m} | {e['planned_calls']} | {e['mean_usd']:.5f} | {e['p95_usd']:.5f} | {e['expected_usd']:.2f} | {e['pessimistic_usd']:.2f} |")
    L += ["", f"Expected ${est['expected_total_usd']:.2f}; pessimistic ${est['pessimistic_total_usd']:.2f} (${est['pessimistic_with_3pct_retries']:.2f} with 3% retries).",
          "", "LIVE RUN APPROVED BY CHRIS: no", ""]
    (rd / "APPROVAL.md").write_text("\n".join(L))
    progress(rd, f"PLAN: {len(games)} games, {len(sched)} judge calls, schedule {man['schedule_sha256'][:12]}, games {man['games_sha256'][:12]}; not approved")


def cmd_validate(rd):
    t = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_blind_twin_selfself.py"], cwd=C.REPO, capture_output=True, text=True)
    fake = C.RESULTS / f"_fake_{rd.name}"
    if fake.exists():
        shutil.rmtree(fake)
    games = load_games()
    r = Runner(fake, live=False)
    r.run(schedule(games), games)
    out = analyze(fake)
    calls = [json.loads(l) for l in (fake / "calls.jsonl").read_text().splitlines()]
    leak = sum(1 for c in calls if any(f"{c['round']} |" in line for line in c["request"]["messages"][0]["content"].splitlines()
                                        if line.startswith(f"{c['round']} |")))
    ok = t.returncode == 0 and len(calls) == C.N_CALLS and leak == 0 and out["indices"]["rps:Delta_selfspec"] is not None and out["indices"]["mp:Delta_selfspec"] is not None
    L = ["# VALIDATION REPORT", "", f"Generated {utc_now()} for `{rd.name}`; code hash {C.code_hash()[:12]}.", "", "## Unit tests", "", "```",
         t.stdout.strip()[-2500:], "```", "", "## No-network fake full run", "",
         f"- Judge calls: {len(calls)} (expected {C.N_CALLS}); transport {calls[0]['transport']}.",
         f"- Prompts containing the to-be-predicted round in the history: {leak} (must be 0).",
         f"- RPS Delta self-specific = {out['indices']['rps:Delta_selfspec']}; MP = {out['indices']['mp:Delta_selfspec']} (fake judges: noise only).", "",
         f"Result: {'PASS' if ok else 'FAIL'}", ""]
    (rd / "VALIDATION_REPORT.md").write_text("\n".join(L))
    shutil.rmtree(fake)
    progress(rd, "VALIDATE: " + L[-2])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="blind_twin_selfself")
    ap.add_argument("cmd", choices=["plan", "validate", "run", "analyze"])
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
    man = json.loads((rd / "manifest.json").read_text())
    games = load_games()
    sched = json.loads((rd / "schedule.json").read_text())
    if (man["code_hash"] != C.code_hash() or man["games_sha256"] != games_hash(games)
            or man["schedule_sha256"] != schedule_hash(schedule(games)) or schedule_hash(sched) != man["schedule_sha256"]):
        raise SystemExit("code, game logs or schedule changed since the manifest was frozen")
    if not (a.live and approved(rd)):
        raise SystemExit("not approved for live calls or --live missing; no network calls made")
    r = Runner(rd, live=True)
    progress(rd, f"RUN start, cap ${C.BUDGET_CAP_USD:.0f}")
    r.run(sched, games)
    if r.stop.is_set():
        progress(rd, "STOPPED: budget cap reached; partial results analysed")
    analyze(rd)
    progress(rd, f"RUN complete: REPORT.md written (spent ${r.acct.spent:.2f})")


if __name__ == "__main__":
    main()
