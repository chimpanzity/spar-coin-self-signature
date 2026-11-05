"""Run a frozen generated predictor in an isolated worker process (handoff section 3).

Isolation on this Windows host (no container runtime is installed):
  - a separate `python -I -S` process (isolated mode: no PYTHONPATH, no user site, no site-packages) running the standalone
    sandbox_worker.py, which imports nothing from the repository;
  - an empty environment except SYSTEMROOT (no API keys or other credentials), stdin/stdout pipes only;
  - a fresh empty temporary working directory, deleted afterwards;
  - a Windows Job Object: per-process memory cap, one active process (no children), kill on close;
  - inside the worker, an audit hook armed before the program is compiled refuses file opens, sockets, subprocesses, ctypes and
    any import other than `math` (network access is therefore blocked in-process, not by an OS firewall);
  - a wall-clock timeout for the whole worker and a per-call time limit.
The program text reaches the worker over stdin only after the process has been assigned to the job.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List

from blind_twin_forecast_prediction import config as C

WORKER = Path(__file__).resolve().parent / "sandbox_worker.py"
# The base interpreter, not a venv launcher stub (on Windows the stub would spawn a child, which the job forbids). The
# worker needs only the standard library.
PYTHON = str(Path(sys.base_prefix) / "python.exe") if os.name == "nt" else sys.executable


def static_check(source: str) -> dict:
    """Syntax, a top-level predict function, and imports limited to math."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return dict(ok=False, error=f"SyntaxError: {e}")
    imports = sorted({a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} |
                     {(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)})
    has_predict = any(isinstance(n, ast.FunctionDef) and n.name == "predict" for n in tree.body)
    bad = [m for m in imports if m != "math"]
    return dict(ok=has_predict and not bad, imports=imports, has_predict=has_predict,
                error=None if has_predict and not bad else f"predict defined: {has_predict}; disallowed imports: {bad}")


def _job_object(proc, memory_mb: int):
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                                                       "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class BASIC(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class EXTENDED(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BASIC), ("IoInfo", IO_COUNTERS), ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    k32.CreateJobObjectW.restype = wintypes.HANDLE
    job = k32.CreateJobObjectW(None, None)
    if not job:
        raise OSError(ctypes.get_last_error(), "CreateJobObjectW")
    info = EXTENDED()
    info.BasicLimitInformation.LimitFlags = 0x100 | 0x8 | 0x2000 | 0x400   # process memory, active processes, kill on close, die on exception
    info.BasicLimitInformation.ActiveProcessLimit = 1
    info.ProcessMemoryLimit = memory_mb * 2**20
    if not k32.SetInformationJobObject(wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info)):
        raise OSError(ctypes.get_last_error(), "SetInformationJobObject")
    if not k32.AssignProcessToJobObject(wintypes.HANDLE(job), wintypes.HANDLE(int(proc._handle))):
        raise OSError(ctypes.get_last_error(), "AssignProcessToJobObject")
    return k32, job


def run(source: str, histories: List[list], timeout_s: float = C.SANDBOX_TIMEOUT_S, call_limit_s: float = C.SANDBOX_CALL_LIMIT_S,
        memory_mb: int = C.SANDBOX_MEMORY_MB) -> dict:
    st = static_check(source)
    if not st["ok"]:
        return dict(ok=False, error=f"static check: {st['error']}", static=st)
    env = {"SYSTEMROOT": os.environ.get("SYSTEMROOT", r"C:\Windows")} if os.name == "nt" else {}
    with tempfile.TemporaryDirectory(prefix="btfp_sandbox_") as wd:
        proc = subprocess.Popen([PYTHON, "-I", "-S", str(WORKER)], cwd=wd, env=env, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        job = _job_object(proc, memory_mb) if os.name == "nt" else None
        try:
            out, err = proc.communicate(json.dumps(dict(source=source, histories=histories, call_limit_s=call_limit_s)) + "\n",
                                        timeout=timeout_s)
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
    res["returncode"] = proc.returncode
    return res
