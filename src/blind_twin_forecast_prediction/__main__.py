"""Blind Twin forecast prediction command line.

  plan       offline acceptance checks; snapshot author messages, endpoints and prices; write plan/run_plan.json and an
             unapproved APPROVAL.md (refuses to change a frozen plan)
  dryrun     the whole pipeline with a fake author transport into dry_run/ (no network)
  run        the four live author calls (needs APPROVAL.md with the approval line and the plan hash); resumable
  freeze     extract and hash the four programs (programs/, sources_sha256.json); never overwrites
  validate   contract check of each frozen program on synthetic histories only (validation/contract.json)
  score      run the frozen programs on the archived inputs and score them (scoring/); zero API calls

Usage: PYTHONPATH=src python -m blind_twin_forecast_prediction <command>
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

from blind_twin_forecast_prediction import authors as AU
from blind_twin_forecast_prediction import config as C
from blind_twin_forecast_prediction import data as D
from blind_twin_forecast_prediction import execute as X
from blind_twin_forecast_prediction import prompts as P
from blind_twin_forecast_prediction import scoring as S
from blind_twin_selfself import config as BT
from spar_dynamic.phase2.client import utc_now

PLAN = C.RD / "plan"


def write_once(path: Path, text: str):
    if path.exists() and path.read_text(encoding="utf-8").replace("\r\n", "\n") != text:
        raise SystemExit(f"{path} is frozen and would change; refusing")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def git_head() -> dict:
    run = lambda *a: subprocess.run(["git", *a], cwd=C.REPO, capture_output=True, text=True).stdout.strip()
    return dict(commit=run("rev-parse", "HEAD"), branch=run("rev-parse", "--abbrev-ref", "HEAD"),
                dirty_tracked=bool(run("status", "--porcelain", "--untracked-files=no")))


def input_hashes() -> dict:
    files = [C.ORIGINAL_CSV, C.RETEST_CSV, C.REPO / BT.SOURCES["mp"]["games"], BT.PKG / "config.py", BT.PKG / "judge.py",
             C.REPO / "src" / "blind_twin_retest.py", C.ORIGINAL_SNAPSHOT]
    return {str(Path(p).relative_to(C.REPO)).replace("\\", "/"): C.canonical_sha(p) for p in files}


def code_hashes() -> dict:
    return {f"src/blind_twin_forecast_prediction/{p.name}": C.canonical_sha(p) for p in sorted(C.PKG.glob("*.py"))}


def endpoint_snapshot() -> dict:
    snap = {"fetched_utc": utc_now(), "endpoints": {}}
    for m in C.MODELS.values():
        with urllib.request.urlopen(f"https://openrouter.ai/api/v1/models/{m['slug']}/endpoints", timeout=60) as r:
            d = json.load(r)["data"]
        snap["endpoints"][m["slug"]] = [{"provider": e["provider_name"], "tag": e["tag"], "status": e.get("status"), "pricing": e["pricing"],
                                         "max_completion_tokens": e.get("max_completion_tokens")} for e in d["endpoints"]
                                        if e["tag"].split("/")[0] == m["provider"]]
    return snap


def plan_sha() -> str:
    return C.canonical_sha(PLAN / "run_plan.json")


def plan():
    ev = D.evaluation_set()
    acc = D.acceptance(ev)
    if not acc["ok"]:
        raise SystemExit(f"offline acceptance checks failed; no plan written: {acc}")
    for j, msg in P.messages().items():
        write_once(PLAN / f"author_message_target_{j}.txt", msg)
    if (PLAN / "run_plan.json").exists():
        print("plan already frozen:", plan_sha())
        return
    snap = endpoint_snapshot()
    (PLAN / "endpoint_snapshot.json").write_text(json.dumps(snap, indent=1) + "\n", encoding="utf-8", newline="\n")
    prices = AU.snapshot_prices(snap)
    from types import SimpleNamespace
    from spar_dynamic.phase2.client import Accountant
    acct = Accountant(C.CAP_USD, prices)
    cells = {}
    for a, j in C.CELLS:
        body = P.request_body(a, j)
        cells[AU.cell_id(a, j)] = dict(author=a, target=j, slug=body["model"], provider=body["provider"], program=C.PROGRAM[(a, j)],
                                       message_sha256=C.sha(body["messages"][0]["content"]), request_sha256=C.sha(json.dumps(body, sort_keys=True)),
                                       worst_case_usd=acct.estimate(SimpleNamespace(params=body, messages=body["messages"])))
    rp = dict(protocol=C.PROTOCOL, created_utc=utc_now(), repo=git_head(), handoff="SPAR_Blind_Twin_Forecast_Prediction_Handoff.md",
              acceptance=acc, inputs_sha256=input_hashes(), code_sha256=code_hashes(),
              messages_sha256={j: C.sha(m) for j, m in P.messages().items()}, cells=cells,
              settings=dict(reasoning=C.REASONING, max_tokens=C.MAX_TOKENS, temperature="omitted", tools="none", generations_per_cell=1,
                            cap_usd=C.CAP_USD, worst_case_total_usd=sum(c["worst_case_usd"] for c in cells.values()),
                            sandbox=dict(timeout_s=C.SANDBOX_TIMEOUT_S, call_limit_s=C.SANDBOX_CALL_LIMIT_S, memory_mb=C.SANDBOX_MEMORY_MB),
                            parser=AU.PARSER_VERSION),
              endpoint_snapshot_sha256=C.canonical_sha(PLAN / "endpoint_snapshot.json"))
    write_once(PLAN / "run_plan.json", json.dumps(rp, indent=2) + "\n")
    sha = plan_sha()
    write_once(C.RD / "APPROVAL.md", f"# APPROVAL\n\nRun plan `plan/run_plan.json` sha256 `{sha}`.\n\nFour author calls (Astra and Fable x two "
               f"targets), one generation each, worst case ${rp['settings']['worst_case_total_usd']:.2f}, hard cap ${C.CAP_USD:.2f}.\n\n"
               "LIVE RUN APPROVED BY CHRIS: no\n")
    print("plan frozen:", sha, "worst case $%.3f" % rp["settings"]["worst_case_total_usd"])


# ---------- pipeline steps (shared by dry run and live) ----------

def freeze(rd: Path = C.RD) -> dict:
    m = AU.freeze_programs(rd)
    print(json.dumps(m, indent=1))
    return m


def validate(rd: Path = C.RD) -> dict:
    man = json.loads((rd / "programs" / "sources_sha256.json").read_text(encoding="utf-8"))
    out = {}
    for name, info in man.items():
        if info["status"] != "frozen":
            out[name] = dict(ok=False, error=f"technical failure: {info['status']} ({info.get('reason')})")
            continue
        src = (rd / "programs" / name).read_text(encoding="utf-8").replace("\r\n", "\n")
        if C.sha(src) != info["sha256"]:
            raise SystemExit(f"{name} changed since freeze")
        out[name] = X.validate(src)
    (rd / "validation").mkdir(parents=True, exist_ok=True)
    (rd / "validation" / "contract.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    for k, v in out.items():
        print(k, "VALID" if v["ok"] else f"INVALID: {v['error']}")
    return out


def _csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def score(rd: Path = C.RD) -> dict:
    """Zero API calls: frozen programs (hash-checked) x archived inputs and labels."""
    man = json.loads((rd / "programs" / "sources_sha256.json").read_text(encoding="utf-8"))
    contract = json.loads((rd / "validation" / "contract.json").read_text(encoding="utf-8"))
    ev = D.evaluation_set()
    acc = D.acceptance(ev)
    assert acc["ok"], acc
    tables, status = {}, {}
    for (a, j), name in C.PROGRAM.items():
        if not contract.get(name, {}).get("ok"):
            status[name] = "technical failure (contract)"
            continue
        src = (rd / "programs" / name).read_text(encoding="utf-8").replace("\r\n", "\n")
        if C.sha(src) != man[name]["sha256"]:
            raise SystemExit(f"{name} changed since freeze")
        r = X.execute(src, ev["inputs"])
        if not r["ok"]:
            status[name] = f"technical failure (execution): {r['error']}"
            continue
        tables[(a, j)], status[name] = r["table"], "valid"
    out = dict(protocol=C.PROTOCOL, program_status=status, sources_sha256={k: v.get("sha256") for k, v in man.items()},
               acceptance=acc, n_items=len(ev["items"]))
    if len(tables) == 4:
        out.update(S.score_all(tables, ev))
        _csv(rd / "scoring" / "item_predictions.csv", S.item_rows(tables, ev["items"]))
    else:
        out["primary"] = "not computed: the primary crossover requires four valid programs"
    (rd / "scoring").mkdir(parents=True, exist_ok=True)
    (rd / "scoring" / "results.json").write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: out[k] for k in ("program_status",)}, indent=1))
    if len(tables) == 4:
        print(json.dumps(out["primary"]["B"], indent=1), json.dumps(out["primary"]["contrasts"], indent=1))
    return out


def run_live():
    sha = plan_sha()
    if not AU.approved(C.RD, sha):
        raise SystemExit(f"APPROVAL.md lacks '{AU.APPROVAL_LINE}' for plan {sha}; no network calls made")
    from spar_dynamic.phase2.client import OpenRouterTransport
    prices = AU.snapshot_prices(json.loads((PLAN / "endpoint_snapshot.json").read_text(encoding="utf-8")))
    AU.run_cells(C.RD, OpenRouterTransport(), prices, sha)


def dryrun():
    """Whole pipeline offline with the fake author transport, into dry_run/ (never touches the live folders)."""
    rd = C.RD / "dry_run"
    if rd.exists():
        import shutil
        shutil.rmtree(rd)
    rd.mkdir(parents=True)
    sha = plan_sha()
    if AU.approved(C.RD, sha):
        print("note: live approval present; the dry run still uses the fake transport only")
    prices = AU.snapshot_prices(json.loads((PLAN / "endpoint_snapshot.json").read_text(encoding="utf-8")))
    AU.run_cells(rd, AU.FakeAuthor(), prices, sha)
    AU.run_cells(rd, AU.FakeAuthor(), prices, sha)            # resume: nothing regenerated
    freeze(rd)
    validate(rd)
    res = score(rd)
    calls = [json.loads(l) for l in (rd / "responses" / "calls.jsonl").read_text(encoding="utf-8").splitlines()]
    summary = dict(calls=len(calls), transport={c["transport"] for c in calls} == {"fake"}, all_valid=all(v == "valid" for v in res["program_status"].values()),
                   primary_computed=isinstance(res.get("primary"), dict), approval_gate_live=AU.approved(C.RD, sha))
    (rd / "DRY_RUN.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("dry run:", summary)


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"plan": plan, "dryrun": dryrun, "run": run_live, "freeze": freeze, "validate": validate, "score": score}[cmd]()
