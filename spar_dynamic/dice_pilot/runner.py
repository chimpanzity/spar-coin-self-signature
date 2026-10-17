"""One-call runner for the dice pilot (spec §4, §6, §10).

Separate from the FCE1 runner so the dice-pilot capture is complete per
spec §10 (temperature requested + effective, reasoning metadata, prefix in
reasoning trace flag, etc.).
"""

from __future__ import annotations

import hashlib, json, os, re, time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from openai import OpenAI

from . import config as C


# --------------------------------------------------------------- ledger --

@dataclass
class CostLedger:
    cap_usd: float
    spent_usd: float = 0.0
    reserved_usd: float = 0.0

    def can_reserve(self, reservation: float) -> bool:
        return (self.spent_usd + self.reserved_usd + reservation) <= self.cap_usd

    def reserve(self, reservation: float) -> bool:
        if not self.can_reserve(reservation): return False
        self.reserved_usd += float(reservation); return True

    def commit(self, actual: float, reservation: float):
        self.spent_usd += float(actual)
        self.reserved_usd -= float(reservation)
        if self.reserved_usd < 0: self.reserved_usd = 0.0

    def release(self, reservation: float):
        self.reserved_usd -= float(reservation)
        if self.reserved_usd < 0: self.reserved_usd = 0.0

    def to_dict(self) -> Dict:
        return {"cap_usd": self.cap_usd, "spent_usd": self.spent_usd,
                "reserved_usd": self.reserved_usd}


# --------------------------------------------------------------- helpers --

def make_openrouter_client(api_key: str, timeout_s: float = 120.0) -> OpenAI:
    return OpenAI(base_url="https://openrouter.ai/api/v1",
                  api_key=api_key, timeout=timeout_s)


def _append_jsonl(path: str, rec: Dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")


def worst_case_cost_usd(prompt_text: str, max_tokens: int,
                        prompt_price_per_tok: float,
                        completion_price_per_tok: float) -> float:
    prompt_tokens = max(32, len(prompt_text) // 4 + 1)
    # worst: all max_tokens are output+reasoning billed at completion rate
    return prompt_tokens * prompt_price_per_tok + max_tokens * completion_price_per_tok


def request_config_hash(slug: str, provider_pin: Optional[str],
                         max_tokens: int, temperature: Optional[float],
                         reasoning_spec: Optional[Dict]) -> str:
    h = hashlib.sha256()
    h.update(json.dumps({
        "slug": slug,
        "provider_pin": provider_pin or "",
        "max_tokens": max_tokens,
        "temperature_requested": temperature,
        "reasoning_spec": reasoning_spec,
    }, sort_keys=True).encode())
    return h.hexdigest()


# --------------------------------------------------------------- call API --

@dataclass
class CallResult:
    ok: bool                           # True iff the API returned a choice with content
    error: str
    raw_text: str
    finish_reason: str
    provider: str
    served_model: str
    generation_id: str
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    reasoning_content: Optional[str]   # if the provider exposes it
    reasoning_content_classification: str  # "raw" | "summarized" | "encrypted" | "unavailable" | "none"
    temperature_effective: Optional[float]  # if we can read it back
    latency_ms: int
    cost_usd: float


def _classify_reasoning(reasoning_content: Any) -> str:
    if reasoning_content is None: return "none"
    if isinstance(reasoning_content, str):
        if not reasoning_content: return "none"
        # Heuristic: if it looks like a numeric prefix sequence, call it raw;
        # otherwise raw (we don't have a provider-explicit summarized marker here).
        return "raw"
    if isinstance(reasoning_content, dict):
        # OpenRouter sometimes returns {"content": "...", "format": "...", ...}
        if reasoning_content.get("encrypted"): return "encrypted"
        if reasoning_content.get("summary"): return "summarized"
        return "raw"
    return "unavailable"


def _prefix_tokens_in_text(text: str, max_tokens: int = 10) -> bool:
    """Spec §4, §8: flag whether an observable prefix sequence appears. Return
    True if there are at least 2 bare 1..6 tokens separated by whitespace or
    commas."""
    if not text: return False
    ints = re.findall(r"(?<![A-Za-z0-9])([1-6])(?![0-9A-Za-z])", text)
    return len(ints) >= 2


def call_once(client: OpenAI, slug: str, prompt_text: str,
              max_tokens: int,
              temperature: Optional[float],
              reasoning_spec: Optional[Dict],
              provider_pin: Optional[str],
              pricing: Dict[str, float]) -> CallResult:
    """Single API call. Caller handles retries + ledger reserve/commit."""
    extra_body: Dict[str, Any] = {}
    if reasoning_spec is not None:
        extra_body["reasoning"] = dict(reasoning_spec)
    if provider_pin:
        extra_body["provider"] = {"order": [provider_pin], "allow_fallbacks": False}
    kwargs: Dict[str, Any] = {
        "model": slug,
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": max_tokens,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if extra_body:
        kwargs["extra_body"] = extra_body

    t0 = time.time()
    try:
        r = client.chat.completions.create(**kwargs)
    except Exception as e:
        return CallResult(ok=False, error=str(e)[:400], raw_text="",
                          finish_reason="error", provider="", served_model="",
                          generation_id="", prompt_tokens=0, completion_tokens=0,
                          reasoning_tokens=0, reasoning_content=None,
                          reasoning_content_classification="unavailable",
                          temperature_effective=None,
                          latency_ms=int(1000 * (time.time() - t0)),
                          cost_usd=0.0)
    latency_ms = int(1000 * (time.time() - t0))
    choices = getattr(r, "choices", None) or []
    if not choices:
        return CallResult(ok=False, error="provider_returned_no_choices",
                          raw_text="", finish_reason="no_choices",
                          provider=getattr(r, "provider", "") or "",
                          served_model=getattr(r, "model", "") or "",
                          generation_id=getattr(r, "id", "") or "",
                          prompt_tokens=0, completion_tokens=0,
                          reasoning_tokens=0, reasoning_content=None,
                          reasoning_content_classification="unavailable",
                          temperature_effective=None,
                          latency_ms=latency_ms, cost_usd=0.0)
    choice = choices[0]
    msg = getattr(choice, "message", None)
    raw_text = (getattr(msg, "content", None) or "") if msg is not None else ""
    finish_reason = getattr(choice, "finish_reason", "") or ""

    # Reasoning content: provider surfaces may expose it as msg.reasoning or
    # msg.reasoning_content. We try both and never ask the model to disclose.
    reasoning_content: Optional[Any] = None
    for attr in ("reasoning", "reasoning_content"):
        if msg is not None and hasattr(msg, attr):
            v = getattr(msg, attr)
            if v: reasoning_content = v; break
    r_class = _classify_reasoning(reasoning_content)

    usage = getattr(r, "usage", None)
    pt = ct = rt = 0
    if usage is not None:
        pt = getattr(usage, "prompt_tokens", 0) or 0
        ct = getattr(usage, "completion_tokens", 0) or 0
        details = getattr(usage, "completion_tokens_details", None)
        if details is not None:
            rt = getattr(details, "reasoning_tokens", 0) or 0

    # Billed cost: completion is billed at completion rate; reasoning is
    # billed at completion rate too (internal_reasoning price = $0/M across
    # all three target slugs on 2026-10-15), AND reasoning tokens are already
    # counted inside completion_tokens on OpenRouter's accounting. To avoid
    # double counting, use ct (which includes rt on OR) and pt only.
    cost = pt * pricing["prompt"] + ct * pricing["completion"]
    return CallResult(
        ok=True, error="", raw_text=raw_text, finish_reason=finish_reason,
        provider=getattr(r, "provider", "") or "",
        served_model=getattr(r, "model", "") or "",
        generation_id=getattr(r, "id", "") or "",
        prompt_tokens=pt, completion_tokens=ct, reasoning_tokens=rt,
        reasoning_content=reasoning_content,
        reasoning_content_classification=r_class,
        temperature_effective=None,     # OpenRouter doesn't report this back
        latency_ms=latency_ms, cost_usd=cost,
    )


def log_attempt(path: str, *, rec: Dict):
    _append_jsonl(path, rec)
