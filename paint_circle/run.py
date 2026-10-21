"""Run paint-and-circle self-play sessions.

A batch is a directory holding plan.json (the session list) and one
subdirectory per session with rounds.jsonl. Each round: both players'
requests are rendered from the same completed history, then dispatched
together; the round is appended only when both choices parse. Invalid
responses are re-requested (same prompt, fresh call) up to MAX_ATTEMPTS per
seat; a seat that still fails ends the session as "failed".

Resumable: rerunning a batch continues each session from its last logged
round. Budget: the batch stops dispatching new rounds once the summed cost
of every call in the batch reaches the cap given in plan.json.

Usage:
    python -m paint_circle.run <batch_dir> [--concurrency N]
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI

from paint_circle import game

MAX_ATTEMPTS = 4      # raised to 10 via --max-attempts when resuming failed sessions
MAX_TRANSPORT_RETRIES = 6

MODELS: Dict[str, Dict[str, Any]] = {
    "astra": dict(slug="openai/gpt-6-astra", provider="openai", reasoning={"effort": "low"},
                  temperature=None, max_tokens=4000),
    "fable": dict(slug="anthropic/claude-fable-5.1", provider="anthropic", reasoning={"effort": "low"},
                  temperature=None, max_tokens=4000),
    "qwen": dict(slug="qwen/qwen3-32b", provider="SiliconFlow", reasoning={"enabled": False},
                 temperature=0.0, max_tokens=4000),
}


class Batch:
    def __init__(self, batch_dir: str, client: OpenAI):
        self.dir = batch_dir
        self.client = client
        self.plan = json.load(open(os.path.join(batch_dir, "plan.json"), encoding="utf-8"))
        self.cap = float(self.plan["cost_cap_usd"])
        self.lock = threading.Lock()
        self.spent = 0.0
        for s in self.plan["sessions"]:
            p = os.path.join(batch_dir, s["session_id"], "rounds.jsonl")
            if os.path.exists(p):
                for line in open(p, encoding="utf-8"):
                    self.spent += json.loads(line)["round_cost_usd"]
            p = os.path.join(batch_dir, s["session_id"], "rejected_attempts.jsonl")
            if os.path.exists(p):
                for line in open(p, encoding="utf-8"):
                    self.spent += json.loads(line).get("cost_usd", 0.0)
        self.over_budget = threading.Event()

    def log(self, msg: str):
        with self.lock, open(os.path.join(self.dir, "progress.log"), "a", encoding="utf-8") as f:
            f.write(f"{dt.datetime.now().isoformat(timespec='seconds')} {msg}\n")

    def add_cost(self, c: float):
        with self.lock:
            self.spent += c
            if self.spent >= self.cap:
                self.over_budget.set()

    def call(self, model: str, system: str, user: str) -> Dict[str, Any]:
        cfg = MODELS[model]
        kwargs = dict(model=cfg["slug"], max_tokens=cfg["max_tokens"],
                      messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                      extra_body={"reasoning": cfg["reasoning"],
                                  "provider": {"order": [cfg["provider"]], "allow_fallbacks": False}})
        if cfg["temperature"] is not None:
            kwargs["temperature"] = cfg["temperature"]
        err = ""
        for attempt in range(1, MAX_TRANSPORT_RETRIES + 1):
            t0 = time.time()
            try:
                r = self.client.chat.completions.create(**kwargs)
                if not r.choices:
                    raise RuntimeError("no_choices")
            except Exception as e:
                err = str(e)[:300]
                time.sleep(min(60, 2 ** attempt))
                continue
            ch, u = r.choices[0], r.usage
            det = getattr(u, "completion_tokens_details", None)
            cost = float(getattr(u, "cost", None) or 0.0)
            self.add_cost(cost)
            return dict(ok=True, text=ch.message.content or "", finish_reason=ch.finish_reason or "",
                        tool_calls=bool(getattr(ch.message, "tool_calls", None)),
                        provider=getattr(r, "provider", "") or "", served_model=r.model or "",
                        generation_id=r.id or "", prompt_tokens=u.prompt_tokens or 0,
                        completion_tokens=u.completion_tokens or 0,
                        reasoning_tokens=(getattr(det, "reasoning_tokens", 0) or 0) if det else 0,
                        cost_usd=cost, latency_ms=int(1000 * (time.time() - t0)), transport_attempts=attempt)
        return dict(ok=False, error=err, text="", cost_usd=0.0, transport_attempts=MAX_TRANSPORT_RETRIES)

    def seat_move(self, sdir: str, round_no: int, seat: str, model: str, system: str, user: str):
        for attempt in range(1, MAX_ATTEMPTS + 1):
            res = self.call(model, system, user)
            choice = game.parse_choice(res["text"]) if res["ok"] and not res.get("tool_calls") else None
            if choice and res.get("finish_reason") != "length":
                return choice, dict(res, attempt=attempt, strict_last_line=game.strict_last_line(res["text"]),
                                    abbreviated=game.abbreviated_choice(res["text"]))
            with self.lock, open(os.path.join(sdir, "rejected_attempts.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(dict(round=round_no, seat=seat, attempt=attempt, **res)) + "\n")
        return None, None

    def run_session(self, s: Dict[str, Any]) -> str:
        sdir = os.path.join(self.dir, s["session_id"])
        os.makedirs(sdir, exist_ok=True)
        rpath = os.path.join(sdir, "rounds.jsonl")
        paint = circle = ""
        if os.path.exists(rpath):
            for line in open(rpath, encoding="utf-8"):
                r = json.loads(line)
                paint += r["paint"]
                circle += r["circle"]
        sys_a = game.system_prompt("A", s["disclosure_A"])
        sys_b = game.system_prompt("B", s["disclosure_B"])
        with cf.ThreadPoolExecutor(2) as ex:
            while len(paint) < s["rounds"]:
                if self.over_budget.is_set():
                    return "budget_stop"
                t = len(paint) + 1
                user = game.render_history(paint, circle, s["window"])
                h = game.history_hash(paint, circle)
                fa = ex.submit(self.seat_move, sdir, t, "A", s["model_A"], sys_a, user)
                fb = ex.submit(self.seat_move, sdir, t, "B", s["model_B"], sys_b, user)
                (pa, ra), (pb, rb) = fa.result(), fb.result()
                if pa is None or pb is None:
                    self.log(f"{s['session_id']}: round {t} failed to parse after {MAX_ATTEMPTS} attempts")
                    return "failed"
                rec = dict(session_id=s["session_id"], round=t, history_sha=h, paint=pa, circle=pb,
                           a_wins=game.a_wins(pa, pb), user_message=user,
                           response_A=ra, response_B=rb,
                           round_cost_usd=ra["cost_usd"] + rb["cost_usd"],
                           timestamp=dt.datetime.now(dt.timezone.utc).isoformat())
                with open(rpath, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec) + "\n")
                paint += pa
                circle += pb
        return "complete"

    def run(self, concurrency: int, only: Optional[List[str]] = None):
        todo = [s for s in self.plan["sessions"] if not only or s["session_id"] in only]
        self.log(f"start: {len(todo)} sessions, spent so far ${self.spent:.2f} of cap ${self.cap:.2f}")
        status = {}
        with cf.ThreadPoolExecutor(concurrency) as ex:
            futs = {ex.submit(self.run_session, s): s["session_id"] for s in todo}
            for f in cf.as_completed(futs):
                sid = futs[f]
                try:
                    status[sid] = f.result()
                except Exception as e:
                    status[sid] = f"error: {e!r}"[:300]
                self.log(f"{sid}: {status[sid]} (batch spent ${self.spent:.2f})")
        with open(os.path.join(self.dir, "status.json"), "w", encoding="utf-8") as f:
            json.dump(dict(spent_usd=round(self.spent, 4), status=status), f, indent=2)
        return status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch_dir")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--only", nargs="*", help="run only these session_ids")
    ap.add_argument("--max-attempts", type=int, default=MAX_ATTEMPTS)
    a = ap.parse_args()
    globals()["MAX_ATTEMPTS"] = a.max_attempts
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY not set (load .env first)")
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key, timeout=600.0, max_retries=0)
    status = Batch(a.batch_dir, client).run(a.concurrency, a.only)
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
