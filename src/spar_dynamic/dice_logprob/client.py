"""One OpenRouter call per record, with the full raw response archived (handoff sections 2 and 6.1).

Transport errors are retried with bounded exponential backoff and every
attempt is recorded. Invalid scientific observations are never re-asked.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import time
from typing import Any, Dict, Optional

CONFIG: Dict[str, Any] = dict(
    slug="qwen/qwen3-32b", provider="SiliconFlow", temperature=0, max_tokens=128,
    reasoning={"enabled": False}, logprobs=True, top_logprobs=20, require_parameters=True,
    price_per_token=(0.14e-6, 0.57e-6),   # SiliconFlow listing, 2026-10-29
)
MAX_TRANSPORT_RETRIES = 4


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def request_body(prompt: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    return dict(
        model=cfg["slug"], messages=[{"role": "user", "content": prompt}],
        temperature=cfg["temperature"], max_tokens=cfg["max_tokens"],
        logprobs=cfg["logprobs"], top_logprobs=cfg["top_logprobs"],
        extra_body={"reasoning": cfg["reasoning"],
                    "provider": {"order": [cfg["provider"]], "allow_fallbacks": False,
                                 "require_parameters": cfg["require_parameters"]}},
    )


def call(client, prompt: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    body = request_body(prompt, cfg)
    attempts = []
    for attempt in range(1, MAX_TRANSPORT_RETRIES + 1):
        t0 = time.time()
        stamp = dt.datetime.now(dt.timezone.utc).isoformat()
        try:
            r = client.chat.completions.create(**body)
        except Exception as e:
            status = getattr(e, "status_code", None)
            err_body = getattr(e, "body", None)
            attempts.append(dict(attempt=attempt, timestamp=stamp, error=str(e)[:1500], status_code=status,
                                 error_body=err_body, latency_ms=int(1000 * (time.time() - t0))))
            # 4xx other than 408/429 is a configuration answer, not transport noise: do not retry.
            if status is not None and 400 <= status < 500 and status not in (408, 429):
                break
            time.sleep(2 ** attempt)
            continue
        raw = r.model_dump()
        attempts.append(dict(attempt=attempt, timestamp=stamp, latency_ms=int(1000 * (time.time() - t0)), ok=True))
        return dict(ok=True, request_json=body, raw_response=raw, attempts=attempts, **summarise_response(raw, cfg))
    return dict(ok=False, request_json=body, raw_response=None, attempts=attempts, **summarise_response(None, cfg))


def summarise_response(raw: Optional[Dict[str, Any]], cfg: Dict[str, Any]) -> Dict[str, Any]:
    if not raw or not raw.get("choices"):
        return dict(served_model=None, served_provider=None, response_id=None, raw_choice_content=None,
                    finish_reason=None, tool_calls=False, raw_logprobs_content=None, raw_reasoning_fields=None,
                    prompt_tokens=None, completion_tokens=None, reasoning_tokens="unknown", cost_usd=0.0,
                    system_fingerprint=None)
    ch = raw["choices"][0]
    msg = ch.get("message") or {}
    lp = ch.get("logprobs")
    usage = raw.get("usage") or {}
    det = usage.get("completion_tokens_details") or {}
    rt = det.get("reasoning_tokens", "unknown") if det else "unknown"
    pt, ct = usage.get("prompt_tokens") or 0, usage.get("completion_tokens") or 0
    cost = usage.get("cost")
    if cost is None:
        cost = pt * cfg["price_per_token"][0] + ct * cfg["price_per_token"][1]
    return dict(
        served_model=raw.get("model"), served_provider=raw.get("provider"), response_id=raw.get("id"),
        raw_choice_content=msg.get("content"), finish_reason=ch.get("finish_reason") or ch.get("native_finish_reason"),
        tool_calls=bool(msg.get("tool_calls")),
        raw_logprobs_content=(lp or {}).get("content") if isinstance(lp, dict) else None,
        raw_reasoning_fields={k: msg.get(k) for k in ("reasoning", "reasoning_content", "reasoning_details") if msg.get(k)},
        prompt_tokens=pt, completion_tokens=ct, reasoning_tokens=rt, cost_usd=float(cost),
        system_fingerprint=raw.get("system_fingerprint"))
