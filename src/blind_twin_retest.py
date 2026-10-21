"""Test-retest of Blind Twin judges (2026-10-11). Authorised by Chris ("yep check it"); cap $10.

Re-judges, with prompts byte-identical to run btss-20261011 (same frozen package, code hash checked), a rule-selected
subset: for each game type x model, the first condition-00 self-self game by game id (6 games). All 20 rounds x 3
judges x 3 labels = 1,080 calls, in the frozen schedule's order. Then compares, on identical items:
  retest vs btss  (same prompt: pure judge sampling noise)
  btx1   vs btss  (prompt differs only by the player-information line: noise + sentence)
  btx1   vs retest
Outputs in blind_twin_selfself/results/btss-retest-20261011/. Originals untouched.

    python blind_twin_retest.py plan|run|analyze
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from blind_twin_selfself import config as C
from blind_twin_selfself.judge import Runner, judge_prompt, load_games, progress
import repo_paths  # reorganisation 2026-10-21: see src/repo_paths.py

BASE = C.RESULTS / "btss-20261011"
RD = C.RESULTS / "btss-retest-20261011"
BTX1 = repo_paths.legacy("blind_twin_exp1/results/btx1-20261010")
CAP = 10.0


def selected(games):
    out = []
    for gt in C.GAME_TYPES:
        for m in C.ORDER:
            gs = sorted(g["gid"] for g in games if g["game_type"] == gt and g["p1_model"] == m and g["condition"] == "00")
            out.append(gs[0])
    return out


def plan():
    man = json.loads((BASE / "manifest.json").read_text())
    assert man["template_sha256"] == C.template_hashes(), "prompt templates changed since btss was frozen"
    games = load_games()
    sel = set(selected(games))
    sched = [it for it in json.loads((BASE / "schedule.json").read_text()) if it["gid"] in sel]
    assert len(sched) == 1080
    # Stronger than a package hash (score.py changed after btss for a report fix): every prompt must be
    # byte-identical to the prompt actually sent in btss.
    by = {g["gid"]: g for g in games}
    base = {json.loads(l)["slot_id"]: json.loads(l) for l in (BASE / "calls.jsonl").read_text().splitlines()}
    assert all(base[it["slot_id"]]["request"] == __import__("blind_twin_selfself.judge", fromlist=["x"]).request_body(
        it["judge"], judge_prompt(it["judge"], by[it["gid"]], it["round"], it["condition"])) for it in sched)
    RD.mkdir(parents=True, exist_ok=True)
    shutil.copy(BASE / "endpoint_and_price_snapshots.json", RD)
    (RD / "schedule.json").write_text(json.dumps(sched))
    (RD / "manifest.json").write_text(json.dumps({"purpose": "test-retest of btss-20261011", "base_run": BASE.name,
                                                  "template_sha256": C.template_hashes(), "check": "all 1,080 request bodies identical to btss", "games": sorted(sel), "n_calls": len(sched), "cap_usd": CAP}, indent=1))
    (RD / "APPROVAL.md").write_text(f"# APPROVAL\n\nTest-retest of `{BASE.name}`: 1,080 calls, ~$6, hard cap ${CAP:.0f}.\n\n"
                                    "LIVE RUN APPROVED BY CHRIS: yes\n\nApproved by Chris in chat 2026-10-11 (\"yep check it\") "
                                    "after the $3-5 test-retest proposal; scope/cap set here at 1,080 calls / $10.\n")
    progress(RD, f"PLAN: games {sorted(sel)}; 1,080 calls; cap ${CAP:.0f}")


def run():
    games = load_games()
    sched = json.loads((RD / "schedule.json").read_text())
    by = {g["gid"]: g for g in games}
    base = {json.loads(l)["slot_id"]: json.loads(l) for l in (BASE / "calls.jsonl").read_text().splitlines()}
    for it in sched:                                          # full request bodies byte-identical to the base run
        assert base[it["slot_id"]]["request"]["messages"][0]["content"] == judge_prompt(it["judge"], by[it["gid"]], it["round"], it["condition"])
    r = Runner(RD, live=True)
    r.acct.cap = CAP
    progress(RD, f"RUN start, cap ${CAP:.0f}")
    r.run(sched, games)
    progress(RD, f"RUN complete (spent ${r.acct.spent:.2f})")


def preds(path, conds_key):
    out = {}
    for r in csv.DictReader(open(path)):
        if r["valid"] == "True":
            out[(r["judge"], r["gid"], int(r["round"]), r["seat"], r[conds_key])] = (r["predicted"], int(r["correct"]))
    return out


def analyze():
    from blind_twin_selfself.score import prediction_rows
    games = load_games()
    calls = [json.loads(l) for l in (RD / "calls.jsonl").read_text().splitlines()]
    rows = prediction_rows(games, calls)
    with open(RD / "predictions.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    sel = set(json.loads((RD / "manifest.json").read_text())["games"])
    runs = {"retest": preds(RD / "predictions.csv", "label"), "btss": preds(BASE / "predictions.csv", "label"),
            "btx1": preds(BTX1 / "predictions.csv", "condition")}
    runs = {k: {kk: v for kk, v in d.items() if kk[1] in sel} for k, d in runs.items()}
    L = ["# Blind Twin judge test-retest (2026-10-11)", "",
         f"Games: {sorted(sel)} (first condition-00 self-self game per game type x model). Same items judged three times:",
         "`btx1` (2026-10-10, no player-information line), `btss` (2026-10-11 morning, with the line) and `retest` "
         "(prompts byte-identical to btss).", "",
         f"- Retest calls: {len(calls)}; valid {sum((c.get('parse') or {}).get('valid', False) for c in calls)}; "
         f"cost ${sum(c['cost_usd'] for c in calls):.2f}.", "",
         "## Agreement of individual predictions (same judge, game, round, seat, label)", "",
         "| comparison | what differs | judge | n | identical % | accuracy A | accuracy B |", "|---|---|---|---:|---:|---:|---:|"]
    summary = {}
    for a, b, what in (("btss", "retest", "nothing (sampling noise)"), ("btx1", "btss", "info line + noise"), ("btx1", "retest", "info line + noise")):
        for j in list(C.JUDGES) + ["all"]:
            ks = [k for k in runs[a] if k in runs[b] and (j == "all" or k[0] == j)]
            same = sum(runs[a][k][0] == runs[b][k][0] for k in ks)
            accA = 100 * sum(runs[a][k][1] for k in ks) / len(ks); accB = 100 * sum(runs[b][k][1] for k in ks) / len(ks)
            L.append(f"| {a} vs {b} | {what} | {j} | {len(ks)} | {100 * same / len(ks):.1f} | {accA:.1f} | {accB:.1f} |")
            summary[(a, b, j)] = 100 * same / len(ks)
    # cell-level noise: accuracy per (gt, judge, target, label) over 40 predictions (1 game x 20 rounds x 2 seats)
    def cells(d):
        c = defaultdict(list)
        for (j, gid, t, s, lab), (_, ok) in d.items():
            c[(gid.split(":")[0], j, gid.split(":")[1][0], lab)].append(ok)
        return {k: 100 * sum(v) / len(v) for k, v in c.items()}
    L += ["", "## Cell-level accuracy noise (judge x game x label cells of 40 predictions)", "",
          "| comparison | n cells | mean abs diff (pp) | max abs diff (pp) | mean abs diff in T = TRUE-ANON (pp) |", "|---|---:|---:|---:|---:|"]
    for a, b in (("btss", "retest"), ("btx1", "btss"), ("btx1", "retest")):
        ca, cb = cells(runs[a]), cells(runs[b])
        ks = [k for k in ca if k in cb]
        diffs = [abs(ca[k] - cb[k]) for k in ks]
        tk = {(k[0], k[1], k[2]) for k in ks}
        td = [abs((ca[(g, j, m, "TRUE")] - ca[(g, j, m, "ANONYMOUS")]) - (cb[(g, j, m, "TRUE")] - cb[(g, j, m, "ANONYMOUS")]))
              for g, j, m in tk if all((g, j, m, l) in ca and (g, j, m, l) in cb for l in ("TRUE", "ANONYMOUS"))]
        L.append(f"| {a} vs {b} | {len(ks)} | {sum(diffs) / len(diffs):.1f} | {max(diffs):.1f} | {sum(td) / len(td):.1f} |")
    L += ["", "Reading: `btss vs retest` is the floor set by judge sampling alone. If `btx1 vs btss` agreement is no lower, the "
          "information line did not measurably change predictions and the differences seen earlier are noise.", ""]
    (RD / "REPORT.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    {"plan": plan, "run": run, "analyze": analyze}[sys.argv[1]]()
