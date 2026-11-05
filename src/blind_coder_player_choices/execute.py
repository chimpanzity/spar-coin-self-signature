"""Sandboxed execution and contract validation for predict(history, seat).

Isolation is folder 21's (imported unchanged from blind_twin_forecast_prediction.sandbox): base-interpreter `python -I -S`
worker, empty environment (SYSTEMROOT only), fresh empty temporary working folder, Windows Job Object (memory cap, one
process, kill on close), in-process audit hook refusing files, sockets, subprocesses, ctypes and non-math imports, timeouts.
Only the worker script differs (this package's sandbox_worker.py, scalar contract).

Contract on synthetic histories only: round 1 in both seats, 19-round histories, constant/alternating and seeded random legal
histories, each in both seats; a number (not bool) that is finite and in [0, 1]; identical across two passes in one process and
a reversed pass in a second process. No clipping or repair.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

from blind_coder_player_choices import config as C
from blind_twin_forecast_prediction.sandbox import PYTHON, _job_object, static_check

WORKER = Path(__file__).resolve().parent / "sandbox_worker.py"
MOVES = ("STAR", "TRIANGLE")


def run(source: str, calls: List[Tuple[list, str]], timeout_s=C.SANDBOX_TIMEOUT_S, call_limit_s=C.SANDBOX_CALL_LIMIT_S,
        memory_mb=C.SANDBOX_MEMORY_MB) -> dict:
    st = static_check(source)
    if not st["ok"]:
        return dict(ok=False, error=f"static check: {st['error']}", static=st)
    env = {"SYSTEMROOT": os.environ.get("SYSTEMROOT", r"C:\Windows")} if os.name == "nt" else {}
    with tempfile.TemporaryDirectory(prefix="btbc_sandbox_") as wd:
        proc = subprocess.Popen([PYTHON, "-I", "-S", str(WORKER)], cwd=wd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, encoding="utf-8")
        job = _job_object(proc, memory_mb) if os.name == "nt" else None
        try:
            out, err = proc.communicate(json.dumps(dict(source=source, calls=calls, call_limit_s=call_limit_s)) + "\n", timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return dict(ok=False, error=f"timeout after {timeout_s} s", static=st)
        finally:
            if job:
                job[0].CloseHandle(job[1])
    line = out.strip().splitlines()[-1] if out.strip() else ""
    try:
        res = json.loads(line)
    except json.JSONDecodeError:
        return dict(ok=False, error=f"worker exit {proc.returncode}: {(err or out)[-400:]}", static=st)
    res["static"] = st
    return res


def deterministic_run(source: str, calls: List[Tuple[list, str]]) -> dict:
    n = len(calls)
    a = run(source, calls + calls)
    if not a["ok"]:
        return dict(ok=False, error=a["error"])
    b = run(source, list(reversed(calls)))
    if not b["ok"]:
        return dict(ok=False, error=b["error"])
    first, second, rev = a["outputs"][:n], a["outputs"][n:], list(reversed(b["outputs"]))
    if first != second or first != rev:
        i = next(i for i in range(n) if not (first[i] == second[i] == rev[i]))
        return dict(ok=False, error=f"non-deterministic output on call {i}: {first[i]} / {second[i]} / {rev[i]}")
    return dict(ok=True, outputs=first, static=a["static"])


def _rows(moves) -> List[dict]:
    return [{"round": i + 1, "p1": a, "p2": b, "result": "Matcher" if a == b else "Mismatcher"} for i, (a, b) in enumerate(moves)]


def synthetic_calls() -> List[Tuple[list, str]]:
    rng = random.Random(C.CONTRACT_SEED)
    hs = [[], _rows([("STAR", "STAR")] * 19), _rows([("TRIANGLE", "STAR")] * 19), _rows([(MOVES[i % 2], MOVES[i % 2]) for i in range(19)]),
          _rows([("STAR", "TRIANGLE")])]
    hs += [_rows([(rng.choice(MOVES), rng.choice(MOVES)) for _ in range(rng.randint(1, 19))]) for _ in range(C.N_CONTRACT_RANDOM)]
    hs.append(_rows([(rng.choice(MOVES), rng.choice(MOVES)) for _ in range(19)]))
    return [(h, s) for h in hs for s in C.SEATS]


def validate(source: str) -> dict:
    calls = synthetic_calls()
    r = deterministic_run(source, calls)
    out = dict(ok=r["ok"], n_synthetic_calls=len(calls), error=r.get("error"))
    if r["ok"]:
        out.update(imports=r["static"]["imports"], round1_p1=r["outputs"][0], round1_p2=r["outputs"][1],
                   len19_outputs=r["outputs"][2:4], distinct_outputs=len(set(r["outputs"])))
    return out


def execute(source: str, items: List[dict]) -> dict:
    """p_STAR for every item (each item's own seat and history), in item order."""
    r = deterministic_run(source, [(it["history"], it["seat"]) for it in items])
    return dict(ok=True, preds=r["outputs"]) if r["ok"] else dict(ok=False, error=r["error"])


def item_key(it) -> Tuple[str, int, str]:
    return it["game_id"], it["round"], it["seat"]


def table(preds: List[float], items: List[dict]) -> Dict[Tuple[str, int, str], float]:
    return {item_key(it): p for it, p in zip(items, preds)}
