"""OpenRouter calls for the pilot: pinned provider, no fallbacks, full raw response archived, cost-capped.

Transport errors retry with exponential backoff (recorded); invalid answers are never re-asked.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import threading
import time
from typing import Any, Dict, Optional

from spar_dynamic.dice_recognition import config as C


def request_body(model_key: str, prompt: str, kind: str) -> Dict[str, Any]:
    m = C.MODELS[model_key]
    s = C.GENERATION if kind == "generation" else C.JUDGMENT
    extra: Dict[str, Any] = {"provider": {"order": [m["provider"]], "only": [m["provider"]],
                                          "allow_fallbacks": False, "require_parameters": True}}
    if m["reasoning"] is not None:
        extra["reasoning"] = m["reasoning"]
    return dict(model=m["slug"], messages=[{"role": "user", "content": prompt}], temperature=s["temperature"],
                top_p=s["top_p"], max_tokens=s["max_tokens"], extra_body=extra)


def summarise(raw: Optional[Dict[str, Any]], model_key: str) -> Dict[str, Any]:
    if not raw or not raw.get("choices"):
        return dict(content=None, finish_reason=None, served_model=None, served_provider=None, response_id=None,
                    reasoning_fields={}, reasoning_tokens="unknown", tool_calls=False, prompt_tokens=0,
                    completion_tokens=0, cost_usd=0.0, cost_source="none")
    ch = raw["choices"][0]
    msg = ch.get("message") or {}
    u = raw.get("usage") or {}
    det = u.get("completion_tokens_details") or {}
    pt, ct = u.get("prompt_tokens") or 0, u.get("completion_tokens") or 0
    cost, src = u.get("cost"), "openrouter_usage"
    if cost is None:
        p = C.MODELS[model_key]["price_per_token"]
        cost, src = pt * p[0] + ct * p[1], "estimated_from_listed_price"
    return dict(content=msg.get("content"), finish_reason=ch.get("finish_reason"), served_model=raw.get("model"),
                served_provider=raw.get("provider") or "unknown", response_id=raw.get("id"),
                reasoning_fields={k: msg.get(k) for k in ("reasoning", "reasoning_content", "reasoning_details") if msg.get(k)},
                reasoning_tokens=det.get("reasoning_tokens", "unknown") if det else "unknown",
                tool_calls=bool(msg.get("tool_calls")), prompt_tokens=pt, completion_tokens=ct,
                cost_usd=float(cost), cost_source=src)


class Ledger:
    """Cumulative spend across all phases, persisted in <exp>/cost_ledger.json; refuses calls that could pass the cap."""

    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        self.spent = json.load(open(path))["spent_usd"] if os.path.exists(path) else 0.0
        self.calls = json.load(open(path))["calls"] if os.path.exists(path) else 0

    def check(self):
        with self.lock:
            if self.spent + C.MAX_CALL_COST_PRIOR_USD > C.COST_CAP_USD:
                raise RuntimeError(f"STOP: cost cap ${C.COST_CAP_USD} would be exceeded (spent ${self.spent:.4f})")

    def add(self, usd: float):
        with self.lock:
            self.spent += usd
            self.calls += 1
            with open(self.path, "w") as f:
                json.dump(dict(spent_usd=round(self.spent, 8), calls=self.calls, cap_usd=C.COST_CAP_USD,
                               updated_utc=dt.datetime.now(dt.timezone.utc).isoformat()), f, indent=2)


def call(client, ledger: Ledger, model_key: str, prompt: str, kind: str) -> Dict[str, Any]:
    body = request_body(model_key, prompt, kind)
    attempts = []
    for attempt in range(1, C.MAX_TRANSPORT_RETRIES + 1):
        ledger.check()
        t0, stamp = time.time(), dt.datetime.now(dt.timezone.utc).isoformat()
        try:
            r = client.chat.completions.create(**body)
            raw = r.model_dump()
        except Exception as e:
            status = getattr(e, "status_code", None)
            attempts.append(dict(attempt=attempt, timestamp=stamp, error=str(e)[:1500], status_code=status,
                                 latency_ms=int(1000 * (time.time() - t0))))
            if status is not None and 400 <= status < 500 and status not in (408, 429):
                break                                   # configuration answer, not transport noise
            time.sleep(2 ** attempt)
            continue
        s = summarise(raw, model_key)
        ledger.add(s["cost_usd"])
        attempts.append(dict(attempt=attempt, timestamp=stamp, ok=True, latency_ms=int(1000 * (time.time() - t0))))
        return dict(ok=bool(raw.get("choices")), request=body, raw_response=raw, attempts=attempts,
                    requested_provider=C.MODELS[model_key]["provider"], model_key=model_key, kind=kind, **s)
    return dict(ok=False, request=body, raw_response=None, attempts=attempts,
                requested_provider=C.MODELS[model_key]["provider"], model_key=model_key, kind=kind, **summarise(None, model_key))


def thinking_clean(rec: Dict[str, Any]) -> bool:
    """No reasoning payload, no <think> text and, where reported, zero reasoning tokens."""
    txt = (rec.get("content") or "").lower()
    rt = rec.get("reasoning_tokens")
    return not rec.get("reasoning_fields") and "<think" not in txt and (rt in (0, "unknown"))


def provider_ok(rec: Dict[str, Any]) -> bool:
    return rec.get("served_provider") == rec.get("requested_provider")
