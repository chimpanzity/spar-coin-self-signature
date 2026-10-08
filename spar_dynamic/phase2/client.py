"""Audited OpenRouter / fake adapters, budget accountant, and resumable executor.

Every planned scientific slot is executed at most once (plus up to three
transient retries of the SAME payload). Records are append-only JSONL. The API
key is read at call time and never written anywhere.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from . import config as C
from .parse import (ANSWER_PARSER_VERSION, GEN_PARSER_VERSION, parse_answer,
                    parse_generation)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
CATALOG_URL = "https://openrouter.ai/api/v1/models"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def git_state() -> Dict[str, Any]:
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=C.REPO_ROOT,
                              capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=C.REPO_ROOT,
                               capture_output=True, text=True).stdout.strip()
        return {"commit": head, "dirty": bool(dirty)}
    except Exception as e:  # pragma: no cover
        return {"commit": None, "error": str(e)}


def progress(run_dir: Path, msg: str) -> None:
    line = f"- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    with open(run_dir / "PROGRESS.md", "a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="", flush=True)


# ---------------------------------------------------------------------------
# Slots
# ---------------------------------------------------------------------------

@dataclass
class Slot:
    slot_id: str
    task: str                      # generation|fixture|rehearsal|completion|pairs|...
    stage: str                     # stage1|stage2
    alias: str                     # model alias (core alias or historical)
    answer_kind: str               # gen|array10|scalar|named3
    messages: List[Dict[str, str]]
    params: Dict[str, Any]         # request controls actually sent (besides messages)
    meta: Dict[str, Any] = field(default_factory=dict)   # public slot metadata
    wave: int = 0                  # execution wave (completion order control)


def model_spec(alias: str) -> C.ModelSpec:
    if alias in C.CORE_MODELS:
        return C.CORE_MODELS[alias]
    if alias == C.HISTORICAL.alias:
        return C.HISTORICAL
    raise KeyError(alias)


def request_params(spec: C.ModelSpec, role: str, temperature_override: Optional[float] = None,
                   seed: Optional[int] = None) -> Dict[str, Any]:
    """Build request controls. Omitted controls are NOT sent (never nominal zeros)."""
    p: Dict[str, Any] = {"model": spec.slug}
    if role == "generation":
        temp = temperature_override if temperature_override is not None else spec.gen_temperature
        if temp is not None:
            p["temperature"] = temp
        if spec.gen_top_p is not None:
            p["top_p"] = spec.gen_top_p
        if spec.gen_top_k is not None:
            p["top_k"] = spec.gen_top_k
        if spec.gen_reasoning is not None:
            p["reasoning"] = dict(spec.gen_reasoning)
        if spec.gen_send_seed:
            assert seed is not None, "seed required for this generator"
            p["seed"] = seed
        p["max_tokens"] = spec.gen_max_tokens
    else:
        if spec.judge_temperature is not None:
            p["temperature"] = spec.judge_temperature
        if spec.judge_reasoning is not None:
            p["reasoning"] = dict(spec.judge_reasoning)
        p["max_tokens"] = spec.judge_max_tokens
    prov: Dict[str, Any] = {"order": [spec.provider], "allow_fallbacks": False}
    if spec.require_parameters:
        prov["require_parameters"] = True
    p["provider"] = prov
    p["usage"] = {"include": True}
    return p


def build_messages(spec: C.ModelSpec, user_text: str) -> List[Dict[str, str]]:
    msgs = []
    if spec.system_message:
        msgs.append({"role": "system", "content": spec.system_message})
    msgs.append({"role": "user", "content": user_text})
    return msgs


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

class BudgetExceeded(RuntimeError):
    pass


class Accountant:
    def __init__(self, cap: float, prices: Dict[str, Dict[str, float]], spent: float = 0.0):
        self.cap = cap
        self.prices = prices
        self.spent = spent
        self.reserved = 0.0
        self.lock = threading.Lock()

    def estimate(self, slot: Slot) -> float:
        pr = self.prices[slot.params["model"]]
        n_in = sum(len(m["content"]) for m in slot.messages) / 3.0 + 50
        return n_in * pr["prompt"] + slot.params.get("max_tokens", 1000) * pr["completion"]

    def reserve(self, slot: Slot) -> float:
        est = self.estimate(slot)
        with self.lock:
            if self.spent + self.reserved + est > self.cap:
                raise BudgetExceeded(
                    f"cap ${self.cap:.2f}: spent ${self.spent:.4f} + reserved "
                    f"${self.reserved:.4f} + next ${est:.4f}")
            self.reserved += est
        return est

    def settle(self, reserved: float, actual: float) -> None:
        with self.lock:
            self.reserved -= reserved
            self.spent += actual


def fetch_prices(slugs: Iterable[str]) -> Dict[str, Dict[str, float]]:
    with urllib.request.urlopen(CATALOG_URL, timeout=60) as r:
        data = json.load(r)["data"]
    by = {m["id"]: m for m in data}
    out = {}
    for s in slugs:
        m = by[s]
        out[s] = {"prompt": float(m["pricing"]["prompt"]),
                  "completion": float(m["pricing"]["completion"]),
                  "canonical_slug": m.get("canonical_slug"),
                  "supported_parameters": m.get("supported_parameters")}
    return out


# ---------------------------------------------------------------------------
# Transports
# ---------------------------------------------------------------------------

class TransientError(RuntimeError):
    pass


class OpenRouterTransport:
    name = "openrouter"

    def __init__(self):
        self._key = C.load_api_key()

    def send(self, body: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            OPENROUTER_URL, data=data, method="POST",
            headers={"Authorization": f"Bearer {self._key}",
                     "Content-Type": "application/json",
                     "X-Title": "SPAR Phase 2"})
        try:
            with urllib.request.urlopen(req, timeout=C.REQUEST_TIMEOUT_S) as r:
                raw = r.read().decode("utf-8")
                status = r.status
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            if e.code == 429 or e.code >= 500:
                raise TransientError(f"HTTP {e.code}: {raw[:500]}")
            return {"_http_status": e.code, "_error_body": raw[:4000], "_nontransient": True}
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            raise TransientError(f"{type(e).__name__}: {e}")
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            raise TransientError(f"non-JSON body: {raw[:300]}")
        if "error" in obj and not obj.get("choices"):
            raise TransientError(f"provider error in body: {json.dumps(obj['error'])[:500]}")
        if not obj.get("choices"):
            raise TransientError("no choices in body")
        obj["_http_status"] = status
        return obj


class FakeTransport:
    """Seeded stand-in for tests and dry runs. Never touches the network."""
    name = "fake"

    def __init__(self):
        self._n = 0
        self._lock = threading.Lock()

    def send(self, body: Dict[str, Any]) -> Dict[str, Any]:
        text_in = body["messages"][-1]["content"]
        with self._lock:
            self._n += 1
            n = self._n
        rng = random.Random(C.derive_seed("fake", body["model"], text_in, n))
        if "Flip 20" in text_in and len(text_in) < 40:
            bias = {"openai/gpt-6-astra": 0.5, "anthropic/claude-fable-5.1": 0.65,
                    "qwen/qwen3-8b": 0.45, "xiaomi/mimo-v2.6-pro": 0.55}.get(body["model"], 0.5)
            seq, prev = [], None
            for i in range(20):
                if prev is not None and rng.random() < 0.6:
                    c = "T" if prev == "H" else "H"
                else:
                    c = "H" if rng.random() < bias else "T"
                seq.append(c); prev = c
            out = ", ".join(seq) if rng.random() < 0.5 else "".join(seq)
        elif "JSON array of 10" in text_in:
            out = json.dumps([round(rng.uniform(0.3, 0.7), 2) for _ in range(10)])
        elif '"C1", "C2", and "C3"' in text_in:
            a = [rng.random() + 0.1 for _ in range(3)]; s = sum(a)
            v = [round(x / s, 3) for x in a]; v[2] = round(1 - v[0] - v[1], 3)
            out = json.dumps({"C1": v[0], "C2": v[1], "C3": v[2]})
        else:
            out = f"{rng.uniform(0.2, 0.8):.2f}"
        return {"id": "fake-" + str(rng.random())[2:10], "model": body["model"],
                "provider": "Fake", "_http_status": 200,
                "choices": [{"message": {"content": out}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost": 0.0}}


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class CallLog:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()

    def done_ids(self) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        r = json.loads(line)
                        out[r["slot_id"]] = r
        return out

    def append(self, rec: Dict[str, Any]) -> None:
        line = json.dumps(rec, ensure_ascii=False)
        with self.lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())


def _extract(obj: Dict[str, Any]) -> Dict[str, Any]:
    ch = (obj.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    usage = obj.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    return {
        "text": msg.get("content"),
        "finish_reason": ch.get("finish_reason"),
        "native_finish_reason": ch.get("native_finish_reason"),
        "returned_model": obj.get("model"),
        "provider": obj.get("provider"),
        "generation_id": obj.get("id"),
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": details.get("reasoning_tokens"),
            "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
            "cost": usage.get("cost"),
        },
        "has_reasoning_field": bool(msg.get("reasoning")),
    }


class Executor:
    def __init__(self, run_dir: Path, transport, accountant: Accountant, context: Dict[str, Any]):
        self.run_dir = run_dir
        self.transport = transport
        self.acct = accountant
        self.log = CallLog(run_dir / "calls.jsonl")
        self.context = context   # code/config hashes etc.
        self.stop_flag = threading.Event()

    def _body(self, slot: Slot) -> Dict[str, Any]:
        body = dict(slot.params)
        body["messages"] = slot.messages
        return body

    def _execute(self, slot: Slot) -> Dict[str, Any]:
        body = self._body(slot)
        attempts = []
        queued = utc_now()
        reserved = self.acct.reserve(slot)
        obj = None
        t0 = time.monotonic()
        for i in range(1 + C.MAX_TRANSIENT_RETRIES):
            dispatch = utc_now()
            try:
                obj = self.transport.send(body)
                attempts.append({"attempt": i, "dispatch_utc": dispatch, "ok": True})
                break
            except TransientError as e:
                attempts.append({"attempt": i, "dispatch_utc": dispatch, "ok": False, "error": str(e)[:600]})
                if i < C.MAX_TRANSIENT_RETRIES:
                    time.sleep([10, 30, 90][i] + random.random())
        completed = utc_now()
        rec: Dict[str, Any] = {
            "slot_id": slot.slot_id, "task": slot.task, "stage": slot.stage,
            "alias": slot.alias, "answer_kind": slot.answer_kind, "meta": slot.meta,
            "request": {k: v for k, v in body.items()},
            "transport": self.transport.name,
            "queued_utc": queued, "completed_utc": completed,
            "duration_s": round(time.monotonic() - t0, 3),
            "attempts": attempts, **self.context,
        }
        if obj is None:
            rec["status"] = "transport_failed"
            rec["cost_usd"] = 0.0
            rec["cost_status"] = "unknown_possible_charge"
            self.acct.settle(reserved, 0.0)
            return rec
        if obj.get("_nontransient"):
            rec["status"] = "http_error"
            rec["http_status"] = obj["_http_status"]
            rec["error_body"] = obj["_error_body"]
            rec["cost_usd"] = 0.0
            rec["cost_status"] = "none_reported"
            self.acct.settle(reserved, 0.0)
            return rec
        ex = _extract(obj)
        cost = ex["usage"].get("cost")
        if cost is None:
            pr = self.acct.prices[slot.params["model"]]
            cost = ((ex["usage"].get("prompt_tokens") or 0) * pr["prompt"]
                    + (ex["usage"].get("completion_tokens") or 0) * pr["completion"])
            rec["cost_status"] = "estimated_from_tokens"
        else:
            rec["cost_status"] = "reported"
        self.acct.settle(reserved, float(cost))
        rec["cost_usd"] = float(cost)
        rec["status"] = "completed"
        rec["response"] = ex
        rec["raw_response"] = {k: v for k, v in obj.items() if k != "choices"} | {"choices": obj.get("choices")}
        if slot.answer_kind == "gen":
            gp = parse_generation(ex["text"], ex["finish_reason"] or "")
            rec["parse"] = {"version": GEN_PARSER_VERSION, "valid": gp.valid, "outcomes": gp.outcomes,
                            "reason": gp.reason, "repeated_list": gp.repeated_list,
                            "span": gp.span, "candidate_lengths": gp.candidate_lengths}
        else:
            ap = parse_answer(ex["text"], slot.answer_kind, ex["finish_reason"] or "")
            rec["parse"] = {"version": ANSWER_PARSER_VERSION, "valid": ap.valid, "value": ap.value,
                            "reason": ap.reason, "strict_valid": ap.strict_valid,
                            "wrapped_payload": ap.wrapped_payload, "normalized": ap.normalized}
        return rec

    def run(self, slots: List[Slot], label: str, workers: int = C.CONCURRENCY,
            retry_failed: bool = False) -> List[Dict[str, Any]]:
        done = self.log.done_ids()
        todo = []
        for s in slots:
            prev = done.get(s.slot_id)
            if prev is None:
                todo.append(s)
            elif retry_failed and prev["status"] == "transport_failed":
                s2 = Slot(**{**s.__dict__, "slot_id": s.slot_id})
                todo.append(s2)
        if not todo:
            progress(self.run_dir, f"{label}: nothing to do ({len(slots)} slots already recorded)")
            return [done[s.slot_id] for s in slots if s.slot_id in done]
        progress(self.run_dir, f"{label}: dispatching {len(todo)} of {len(slots)} slots "
                               f"(spent so far ${self.acct.spent:.2f})")
        waves = sorted({s.wave for s in todo})
        n_done = 0
        for w in waves:
            batch = [s for s in todo if s.wave == w]
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs = {}
                for s in batch:
                    if self.stop_flag.is_set():
                        break
                    futs[pool.submit(self._safe, s)] = s
                for f in as_completed(futs):
                    rec = f.result()
                    if rec is not None:
                        self.log.append(rec)
                        n_done += 1
                        if n_done % 50 == 0:
                            progress(self.run_dir, f"{label}: {n_done}/{len(todo)} recorded, "
                                                   f"spent ${self.acct.spent:.2f}")
            if self.stop_flag.is_set():
                break
        done = self.log.done_ids()
        recs = [done[s.slot_id] for s in slots if s.slot_id in done]
        n_ok = sum(1 for r in recs if r["status"] == "completed")
        n_valid = sum(1 for r in recs if r.get("parse", {}).get("valid"))
        progress(self.run_dir, f"{label}: finished; {len(recs)}/{len(slots)} recorded, "
                               f"{n_ok} completed, {n_valid} valid; spent ${self.acct.spent:.2f}")
        return recs

    def _safe(self, slot: Slot) -> Optional[Dict[str, Any]]:
        try:
            return self._execute(slot)
        except BudgetExceeded as e:
            self.stop_flag.set()
            progress(self.run_dir, f"BUDGET STOP: {e}")
            return None
