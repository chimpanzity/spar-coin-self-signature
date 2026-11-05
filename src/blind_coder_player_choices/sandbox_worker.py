"""Isolated worker for one generated player predictor, predict(history, seat) -> p_STAR. Standalone: imports nothing from the
repository. Same isolation as folder 21's worker (blind_twin_forecast_prediction/sandbox_worker.py); only the call contract
differs. Reads {"source", "calls": [[history, seat], ...], "call_limit_s"} from stdin; writes {"ok", "outputs" | "error"}.
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
            if args[0].split(".")[0] not in ALLOWED_IMPORTS:
                raise ImportError(f"sandbox: import of {args[0]} refused")
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
            raise TypeError("no callable predict(history, seat)")
        outputs = []
        for h, seat in req["calls"]:
            t0 = time.perf_counter()
            v = fn(json.loads(json.dumps(h)), seat)      # a fresh copy per call
            dt = time.perf_counter() - t0
            if dt > req["call_limit_s"]:
                raise TimeoutError(f"predict() took {dt:.2f} s")
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise TypeError(f"predict() returned {type(v).__name__} {v!r:.60}, not a number")
            v = float(v)
            if not math.isfinite(v) or v < 0.0 or v > 1.0:
                raise ValueError(f"probability {v!r} not finite in [0, 1]")
            outputs.append(v)
        res = {"ok": True, "outputs": outputs}
    except BaseException as e:                       # noqa: BLE001
        res = {"ok": False, "error": f"{type(e).__name__}: {e}"[:500]}
    armed["on"] = False
    out.write(json.dumps(res) + "\n")
    out.flush()


if __name__ == "__main__":
    main()
