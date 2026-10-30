"""OpenRouter calls for v2: v1's pinned-provider request, response summary and validity checks, extended to
multi-turn messages and the two judgment formats. Bounded-concurrency runner with resume and dispatch order.

Transport errors retry with backoff (logged); substantive invalid answers are never re-asked.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

from spar_dynamic.dice_recognition.client import provider_ok, summarise, thinking_clean   # noqa: F401 (re-export)
from spar_dynamic.dice_recognition_v2 import config as C, prompts as P


def settings(kind: str) -> Dict[str, Any]:
    return C.GENERATION if kind == "generation" else C.JUDGMENT[kind]


def request_body(model_key: str, messages: List[Dict[str, str]], kind: str) -> Dict[str, Any]:
    m, s = C.MODELS[model_key], settings(kind)
    extra: Dict[str, Any] = {"provider": {"order": [m["provider"]], "only": [m["provider"]],
                                          "allow_fallbacks": False, "require_parameters": True}}
    if m["reasoning"] is not None:
        extra["reasoning"] = m["reasoning"]
    return dict(model=m["slug"], messages=messages, temperature=s["temperature"], top_p=s["top_p"],
                max_tokens=s["max_tokens"], extra_body=extra)


class Ledger:
    """Cumulative v2 spend in <exp>/cost_ledger.json; refuses any call that could pass the cap."""

    def __init__(self, path: str):
        self.path, self.lock = path, threading.Lock()
        d = json.load(open(path)) if os.path.exists(path) else {}
        self.spent, self.calls = d.get("spent_usd", 0.0), d.get("calls", 0)
        self.by_stage = d.get("by_stage", {})

    def check(self):
        with self.lock:
            if self.spent + C.MAX_CALL_COST_PRIOR_USD > C.COST_CAP_USD:
                raise RuntimeError(f"STOP: cost cap ${C.COST_CAP_USD} would be exceeded (spent ${self.spent:.4f})")

    def add(self, usd: float, stage: str):
        with self.lock:
            self.spent += usd
            self.calls += 1
            b = self.by_stage.setdefault(stage, {"usd": 0.0, "calls": 0})
            b["usd"] += usd
            b["calls"] += 1
            with open(self.path, "w") as f:
                json.dump(dict(spent_usd=round(self.spent, 8), calls=self.calls, cap_usd=C.COST_CAP_USD,
                               by_stage=self.by_stage, updated_utc=dt.datetime.now(dt.timezone.utc).isoformat()), f, indent=2)


def call(client, ledger: Ledger, model_key: str, messages, kind: str, stage: str) -> Dict[str, Any]:
    body = request_body(model_key, messages, kind)
    attempts = []
    for attempt in range(1, C.MAX_TRANSPORT_RETRIES + 1):
        ledger.check()
        t0, stamp = time.time(), dt.datetime.now(dt.timezone.utc).isoformat()
        try:
            raw = client.chat.completions.create(**body).model_dump()
        except Exception as e:
            status = getattr(e, "status_code", None)
            attempts.append(dict(attempt=attempt, timestamp=stamp, error=str(e)[:1500], status_code=status,
                                 latency_ms=int(1000 * (time.time() - t0))))
            if status is not None and 400 <= status < 500 and status not in (408, 429):
                break
            time.sleep(2 ** attempt)
            continue
        s = summarise(raw, model_key)
        ledger.add(s["cost_usd"], stage)
        attempts.append(dict(attempt=attempt, timestamp=stamp, ok=True, latency_ms=int(1000 * (time.time() - t0))))
        return dict(ok=bool(raw.get("choices")), request=body, raw_response=raw, attempts=attempts,
                    requested_provider=C.MODELS[model_key]["provider"], model_key=model_key, kind=kind, **s)
    return dict(ok=False, request=body, raw_response=None, attempts=attempts,
                requested_provider=C.MODELS[model_key]["provider"], model_key=model_key, kind=kind,
                **summarise(None, model_key))


def judged(rec: Dict[str, Any], fmt: str):
    """Parsed choice, or None if transport failed, provider drifted, thinking appeared, output truncated or malformed."""
    if not rec.get("ok") or not provider_ok(rec) or not thinking_clean(rec) or rec.get("tool_calls"):
        return None
    if fmt == "brief" and rec.get("finish_reason") != "stop":
        return None
    return P.parse_choice(rec.get("content"), fmt)


def run_judgments(oai, ledger, trials, path, stage, label=None):
    """Run fresh-context judgments with bounded concurrency; resume by trial_id. Each trial dict carries judge, fmt,
    prompt and correct ('A'/'B'). Appends one JSON line per trial. Stops (SystemExit) on provider drift or when a
    judge's invalid share exceeds the frozen stage limit."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    done = {json.loads(l)["trial_id"]: json.loads(l) for l in open(path, encoding="utf-8")} if os.path.exists(path) else {}
    todo = [t for t in trials if t["trial_id"] not in done]
    lock, stop = threading.Lock(), {"why": None}
    tally = {j: [0, 0] for j in C.SOURCES}               # [n, invalid]
    for r in done.values():
        tally[r["judge"]][0] += 1
        tally[r["judge"]][1] += not r["valid"]

    def one(t):
        if stop["why"]:
            return
        msgs = t.get("messages") or [{"role": "user", "content": t["prompt"]}]
        rec = call(oai, ledger, t["judge"], msgs, t["fmt"], stage)
        choice = judged(rec, t["fmt"])
        rec.update({k: v for k, v in t.items() if k not in ("prompt", "messages")}, prompt_text=msgs[-1]["content"],
                   prompt_sha256=P.sha256(msgs[-1]["content"]), messages=msgs, choice=choice, valid=choice is not None,
                   is_correct=(choice == t["correct"]) if choice else None,
                   completed_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        with lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, default=str) + "\n")
            n = tally[t["judge"]]
            n[0] += 1
            n[1] += choice is None
            if rec.get("ok") and not provider_ok(rec):
                stop["why"] = f"STOP: {t['judge']} served by {rec.get('served_provider')}"
            elif rec.get("ok") and not thinking_clean(rec):
                stop["why"] = f"STOP: reasoning payload from {t['judge']} on {t['trial_id']}"
            elif n[0] >= C.STAGE_MIN_N and n[1] / n[0] > C.STAGE_MAX_INVALID_SHARE:
                stop["why"] = f"STOP: {t['judge']} invalid share {n[1]}/{n[0]} exceeds {C.STAGE_MAX_INVALID_SHARE}"
            print(f"[{label or stage} {t['dispatch_index']}] {t['trial_id']}: {(rec.get('content') or '')[-40:]!r} -> {choice} "
                  f"(correct {t['correct']}; ${getattr(ledger, "spent", 0):.4f})", flush=True)

    with ThreadPoolExecutor(C.CONCURRENCY) as ex:
        list(ex.map(one, todo))
    if stop["why"]:
        raise SystemExit(stop["why"])
    return [json.loads(l) for l in open(path, encoding="utf-8")]
