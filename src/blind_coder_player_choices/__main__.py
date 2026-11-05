"""First-level Blind Coder command line.

  plan       acceptance checks; freeze author messages, schedule, endpoint/price snapshot, input/code/test hashes and per-call
             worst-case cost in plan/run_plan.json; write an unapproved APPROVAL.md (refuses to change a frozen plan)
  dryrun     the whole pipeline with fake programs into dry_run/ (no network)
  run        the 40 live author calls (needs APPROVAL.md with the approval line and this plan's hash); resumable
  freeze     parse, write and hash all generated sources (programs/); never overwrites
  validate   contract on synthetic histories only (validation/contract.json)
  score      every valid program on all 480 archived decisions; tables in scoring/ (zero API calls)

Usage: PYTHONPATH=src python -m blind_coder_player_choices <command>
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from blind_coder_player_choices import authors as AU
from blind_coder_player_choices import config as C
from blind_coder_player_choices import data as D
from blind_coder_player_choices import execute as X
from blind_coder_player_choices import prompts as P
from blind_coder_player_choices import scoring as S
from blind_twin_forecast_prediction.__main__ import endpoint_snapshot, git_head
from spar_dynamic.phase2.client import Accountant, utc_now

PLAN = C.RD / "plan"
TESTS = C.REPO / "tests" / "test_blind_coder_player_choices.py"


def write_once(path: Path, text: str):
    if path.exists() and path.read_text(encoding="utf-8").replace("\r\n", "\n") != text:
        raise SystemExit(f"{path} is frozen and would change; refusing")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def plan_sha() -> str:
    return C.canonical_sha(PLAN / "run_plan.json")


def plan():
    gs = D.load_games()
    acc = D.acceptance(gs, D.items(gs))
    if not acc["ok"]:
        raise SystemExit(f"acceptance checks failed; no plan written: {acc}")
    for j, m in P.messages().items():
        write_once(PLAN / f"author_message_target_{j}.txt", m)
    write_once(PLAN / "schedule.json", json.dumps(AU.schedule(), indent=1) + "\n")
    if (PLAN / "run_plan.json").exists():
        print("plan already frozen:", plan_sha())
        return
    snap = endpoint_snapshot()
    (PLAN / "endpoint_snapshot.json").write_text(json.dumps(snap, indent=1) + "\n", encoding="utf-8", newline="\n")
    prices = AU.snapshot_prices(snap)
    acct = Accountant(C.CAP_USD, prices)
    worst = {}
    for a, j in C.CELLS:
        b = P.request_body(a, j)
        worst[f"{a}->{j}"] = acct.estimate(SimpleNamespace(params=b, messages=b["messages"]))
    total = sum(worst[f"{s['author']}->{s['target']}"] for s in AU.schedule())
    code = {f"src/blind_coder_player_choices/{p.name}": C.canonical_sha(p) for p in sorted(C.PKG.glob("*.py"))}
    reused = {f"src/blind_twin_forecast_prediction/{n}": C.canonical_sha(C.REPO / "src" / "blind_twin_forecast_prediction" / n)
              for n in ("authors.py", "sandbox.py", "config.py", "__main__.py")}
    inputs = {str(p.relative_to(C.REPO)).replace("\\", "/"): C.canonical_sha(p)
              for p in (C.GAME_LOG, C.REPO / "src" / "opponent_disclosure_mp_3models" / "config.py",
                        C.REPO / "src" / "opponent_disclosure_mp_3models" / "game.py")}
    rp = dict(protocol=C.PROTOCOL, created_utc=utc_now(), repo=git_head(), handoff="SPAR_First_Level_Blind_Coder_Player_Choices_Handoff.md",
              acceptance=acc, inputs_sha256=inputs, code_sha256=code, reused_code_sha256=reused, tests_sha256={str(TESTS.relative_to(C.REPO)).replace("\\", "/"): C.canonical_sha(TESTS)},
              messages_sha256={j: C.sha(m) for j, m in P.messages().items()}, schedule_seed=C.SCHEDULE_SEED,
              schedule_sha256=C.canonical_sha(PLAN / "schedule.json"), n_calls=len(AU.schedule()),
              settings=dict(reasoning=C.REASONING, max_tokens=C.MAX_TOKENS, temperature_top_p_seed="omitted", tools="none", fallbacks="off",
                            cache="no cache directives; every request isolated", cap_usd=C.CAP_USD, worst_case_per_call_usd=worst,
                            worst_case_total_usd=total, sandbox=dict(timeout_s=C.SANDBOX_TIMEOUT_S, call_limit_s=C.SANDBOX_CALL_LIMIT_S,
                                                                    memory_mb=C.SANDBOX_MEMORY_MB), parser=AU.PARSER_VERSION,
                            min_complete_blocks=C.MIN_COMPLETE_BLOCKS),
              endpoint_snapshot_sha256=C.canonical_sha(PLAN / "endpoint_snapshot.json"))
    if total > C.CAP_USD:
        raise SystemExit(f"worst case ${total:.2f} exceeds the ${C.CAP_USD:.0f} cap; no plan written")
    write_once(PLAN / "run_plan.json", json.dumps(rp, indent=2) + "\n")
    sha = plan_sha()
    write_once(C.RD / "APPROVAL.md", f"# APPROVAL\n\nRun plan `plan/run_plan.json` sha256 `{sha}`.\n\n40 author calls (2 authors x 2 named targets x 10 "
               f"blocks), one generation each, worst case ${total:.2f}, hard cap ${C.CAP_USD:.2f}. Folder 21's approval does not apply.\n\n"
               "LIVE RUN APPROVED BY CHRIS: no\n")
    print("plan frozen:", sha, f"worst case ${total:.2f}")


def programs_list(rd: Path) -> list:
    man = json.loads((rd / "programs" / "sources_sha256.json").read_text(encoding="utf-8"))
    contract = json.loads((rd / "validation" / "contract.json").read_text(encoding="utf-8")) if (rd / "validation" / "contract.json").exists() else {}
    out = []
    for name, m in man.items():
        st = m["status"] if m["status"] != "frozen" else ("valid" if contract.get(name, {}).get("ok") else
                                                          f"contract failure: {contract.get(name, {}).get('error')}")
        out.append(dict(id=name, block=m["block"], author=m["author"], target=m["target"], status=st, valid=st == "valid", sha256=m.get("sha256")))
    return out


def freeze(rd: Path = C.RD) -> dict:
    man = AU.freeze_programs(rd)
    print({k: v["status"] for k, v in man.items() if v["status"] != "frozen"} or f"all {len(man)} frozen")
    return man


def validate(rd: Path = C.RD) -> dict:
    man = json.loads((rd / "programs" / "sources_sha256.json").read_text(encoding="utf-8"))
    out = {}
    for name, m in man.items():
        if m["status"] != "frozen":
            out[name] = dict(ok=False, error=f"technical failure: {m['status']} ({m.get('reason')})")
            continue
        src = (rd / "programs" / name).read_text(encoding="utf-8").replace("\r\n", "\n")
        if C.sha(src) != m["sha256"]:
            raise SystemExit(f"{name} changed since freeze")
        out[name] = X.validate(src)
    (rd / "validation").mkdir(parents=True, exist_ok=True)
    (rd / "validation" / "contract.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    bad = {k: v["error"] for k, v in out.items() if not v["ok"]}
    print(f"{len(out) - len(bad)}/{len(out)} valid", bad or "")
    return out


def _csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict, tuple)) else v) for k, v in r.items()})


def score(rd: Path = C.RD) -> dict:
    """Zero API calls: hash-checked frozen programs on the 480 archived decisions."""
    gs = D.load_games()
    items = D.items(gs)
    acc = D.acceptance(gs, items)
    assert acc["ok"], acc
    programs = programs_list(rd)
    preds = {}
    for p in programs:
        if not p["valid"]:
            continue
        src = (rd / "programs" / p["id"]).read_text(encoding="utf-8").replace("\r\n", "\n")
        if C.sha(src) != p["sha256"]:
            raise SystemExit(f"{p['id']} changed since freeze")
        r = X.execute(src, items)
        if not r["ok"]:
            p.update(valid=False, status=f"execution failure: {r['error']}")
            continue
        preds[p["id"]] = X.table(r["preds"], items)
    res = S.score_all(programs, preds, items)
    res.update(protocol=C.PROTOCOL, acceptance=acc, programs=[{k: v for k, v in p.items()} for p in programs])
    out = rd / "scoring"
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")
    _csv(out / "generation_scores.csv", S.generation_table(programs, preds, items))
    _, base = S.baselines(items)
    tidy = []
    for it in items:
        k = S.key(it)
        row = dict(game_id=it["game_id"], round=it["round"], seat=it["seat"], player=it["target"], opponent=it["opponent"],
                   replicate=it["replicate"], y=it["y"], prev_own=it["prev_own"], prev_won=it["prev_won"],
                   **{f"baseline_{n}": v[k] for n, v in base.items()})
        for p in programs:
            if p["id"] in preds:
                row[p["id"].removesuffix(".py")] = preds[p["id"]][k]
        tidy.append(row)
    _csv(out / "item_predictions.csv", tidy)
    if isinstance(res.get("primary"), dict):
        print(json.dumps(dict(L=res["primary"]["L"], contrasts=res["primary"]["contrasts"], blocks=res["primary"]["n_complete"]), indent=1))
    return res


def run_live():
    sha = plan_sha()
    if not AU.approved(C.RD, sha):
        raise SystemExit(f"APPROVAL.md lacks '{AU.APPROVAL_LINE}' for plan {sha}; no network calls made")
    from spar_dynamic.phase2.client import OpenRouterTransport
    prices = AU.snapshot_prices(json.loads((PLAN / "endpoint_snapshot.json").read_text(encoding="utf-8")))
    AU.run_schedule(C.RD, OpenRouterTransport(), prices, sha)


def dryrun():
    import shutil
    rd = C.RD / "dry_run"
    if rd.exists():
        shutil.rmtree(rd)
    rd.mkdir(parents=True)
    sha = plan_sha()
    prices = AU.snapshot_prices(json.loads((PLAN / "endpoint_snapshot.json").read_text(encoding="utf-8")))
    fake = AU.FakeAuthor()
    AU.run_schedule(rd, fake, prices, sha, log=lambda m: None)
    n_after_first = fake.n
    AU.run_schedule(rd, fake, prices, sha, log=lambda m: None)      # resume: no completed slot reissued
    freeze(rd)
    validate(rd)
    res = score(rd)
    summary = dict(calls=n_after_first, reissued_on_resume=fake.n - n_after_first, valid=res["validity"]["valid"],
                   complete_blocks=len(res["validity"]["complete_blocks"]), primary_computed=isinstance(res.get("primary"), dict),
                   live_approval_present=AU.approved(C.RD, sha))
    (rd / "DRY_RUN.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("dry run:", summary)


if __name__ == "__main__":
    {"plan": plan, "dryrun": dryrun, "run": run_live, "freeze": freeze, "validate": validate, "score": score}[sys.argv[1]]()
