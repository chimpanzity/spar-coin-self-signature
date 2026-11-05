"""Isolated worker for one generated predictor. Standalone: imports nothing from the repository.

Launched by sandbox.py as `python -I -S sandbox_worker.py` with an empty environment, a fresh empty working directory and a
Windows Job Object (memory cap, no child processes). Reads {"source", "histories", "call_limit_s"} from stdin, then installs an
audit hook that, from that point on, refuses file opens, sockets, subprocesses, ctypes and every import except `math`, and
only then compiles and runs the program. Writes {"ok", "outputs" | "error"} to stdout (one JSON line).
"""
import json
import math
import sys
import time

ALLOWED_IMPORTS = {"math"}
BLOCKED_PREFIXES = ("socket.", "subprocess.", "os.system", "os.exec", "os.spawn", "os.posix_spawn", "os.startfile", "os.fork",
                    "os.kill", "os.remove", "os.rename", "os.mkdir", "os.rmdir", "os.chdir", "os.listdir", "os.scandir",
                    "shutil.", "ctypes.", "winreg.", "urllib.", "http.", "ftplib.", "smtplib.", "webbrowser.", "_winapi.",
                    "msvcrt.", "sys._getframe", "code.", "pdb.", "marshal.load", "pickle.find_class", "sqlite3.")


def main():
    req = json.loads(sys.stdin.readline())
    out = sys.stdout
    armed = {"on": False}

    def hook(event, args):
        if not armed["on"]:
            return
        if event == "open":
            raise PermissionError("sandbox: file access refused")
        if event == "import":
            name = args[0]
            if name.split(".")[0] not in ALLOWED_IMPORTS:
                raise ImportError(f"sandbox: import of {name} refused")
            return
        if event.startswith(BLOCKED_PREFIXES):
            raise PermissionError(f"sandbox: {event} refused")

    sys.addaudithook(hook)
    armed["on"] = True
    try:
        ns = {"__name__": "predictor"}
        exec(compile(req["source"], "<predictor>", "exec"), ns)
        fn = ns.get("predict")
        if not callable(fn):
            raise TypeError("no callable predict(history)")
        outputs = []
        for h in req["histories"]:
            t0 = time.perf_counter()
            r = fn(json.loads(json.dumps(h)))        # a fresh copy: the program cannot alter what later calls receive
            dt = time.perf_counter() - t0
            if dt > req["call_limit_s"]:
                raise TimeoutError(f"predict() took {dt:.2f} s")
            if not isinstance(r, (tuple, list)) or len(r) != 2:
                raise TypeError(f"predict() returned {type(r).__name__} {r!r:.80}, not a pair")
            pair = []
            for v in r:
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    raise TypeError(f"non-numeric probability {v!r:.40}")
                v = float(v)
                if not math.isfinite(v) or v < 0.0 or v > 1.0:
                    raise ValueError(f"probability {v!r} not finite in [0, 1]")
                pair.append(v)
            outputs.append(pair)
        res = {"ok": True, "outputs": outputs}
    except BaseException as e:                       # noqa: BLE001 (any failure of generated code is a contract failure)
        res = {"ok": False, "error": f"{type(e).__name__}: {e}"[:500]}
    armed["on"] = False
    out.write(json.dumps(res) + "\n")
    out.flush()


if __name__ == "__main__":
    main()
