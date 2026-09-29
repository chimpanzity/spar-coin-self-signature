"""Thin OpenRouter wrapper with cost tracking and structured-output support.

Reuses the existing project's client construction pattern (OpenAI-compatible
base_url = openrouter.ai). Every completed call returns an APIResult with the
raw response, parsed content, token usage, cost estimate, and provenance.

Pricing table is captured at run start from the /models endpoint; costs are
computed from returned token counts.
"""

import json, os, re, time, uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from . import config as C


@dataclass
class APIResult:
    request_id: str
    call_utc: str
    requested_model: str
    served_model: str
    provider: str
    generation_id: str
    prompt_text: str
    prompt_hash: str
    response_text: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: int
    attempts: int
    error_message: str
    response_mode: str        # "chat" | "json_schema" | "text"


class CostAccountant:
    """Tracks cumulative USD spend and per-model pricing pulled from OpenRouter."""

    def __init__(self, client: OpenAI):
        self._client = client
        self.prices: Dict[str, Tuple[float, float]] = {}   # slug -> (prompt$/tok, completion$/tok)
        self.spent_usd = 0.0
        self.calls_by_kind: Dict[str, int] = {}
        self.spent_by_kind: Dict[str, float] = {}

    def snapshot_catalog(self) -> Dict[str, Any]:
        import urllib.request
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        by_id = {}
        for m in data.get("data", []):
            mid = m["id"]
            p = m.get("pricing", {}) or {}
            try:
                pt = float(p.get("prompt", "0") or 0.0)
                ct = float(p.get("completion", "0") or 0.0)
            except (TypeError, ValueError):
                pt = ct = 0.0
            by_id[mid] = {"pricing": {"prompt": pt, "completion": ct},
                          "context_length": m.get("context_length", 0)}
            self.prices[mid] = (pt, ct)
        return by_id

    def estimate_cost(self, slug: str, prompt_toks: int, completion_toks: int) -> float:
        pt, ct = self.prices.get(slug, (0.0, 0.0))
        return prompt_toks * pt + completion_toks * ct

    def record(self, kind: str, cost_usd: float):
        self.spent_usd += cost_usd
        self.calls_by_kind[kind] = self.calls_by_kind.get(kind, 0) + 1
        self.spent_by_kind[kind] = self.spent_by_kind.get(kind, 0.0) + cost_usd


class BudgetExceeded(Exception):
    pass


class ModelUnavailable(Exception):
    pass


def make_client(timeout_s: float = 120.0) -> OpenAI:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set in environment.")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key, timeout=timeout_s)


def _sha256(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _extract_usage(response) -> Tuple[int, int, int, int]:
    """Returns (prompt, completion, reasoning, total). All zero if missing."""
    pt = ct = rt = tt = 0
    u = getattr(response, "usage", None)
    if u is not None:
        pt = getattr(u, "prompt_tokens", 0) or 0
        ct = getattr(u, "completion_tokens", 0) or 0
        tt = getattr(u, "total_tokens", 0) or 0
        details = getattr(u, "completion_tokens_details", None)
        if details is not None:
            rt = getattr(details, "reasoning_tokens", 0) or 0
    return int(pt), int(ct), int(rt), int(tt)


def call_model(
    client: OpenAI,
    accountant: CostAccountant,
    *,
    kind: str,                # "batch"|"online"|"judgment"|"smoke"
    slug: str,
    prompt_text: str,
    max_tokens: int,
    temperature: float = C.TEMPERATURE,
    response_format: Optional[Dict[str, Any]] = None,  # OpenAI JSON schema format
    max_transport_retries: int = C.TRANSPORT_RETRIES,
) -> APIResult:
    """Single API call with transport-level retries and cost tracking."""
    if accountant.spent_usd >= C.STOP_AT_PROJECTED_USD:
        raise BudgetExceeded(f"budget cap hit before call: ${accountant.spent_usd:.4f}")

    start = time.time()
    call_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start))
    request_id = str(uuid.uuid4())
    prompt_hash = _sha256(prompt_text)
    last_error = ""
    response_mode = "json_schema" if response_format else "chat"

    for attempt in range(max_transport_retries):
        try:
            kwargs: Dict[str, Any] = {
                "model": slug,
                "messages": [{"role": "user", "content": prompt_text}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            # Reasoning-effort control is via extra_body under OpenRouter.
            kwargs["extra_body"] = {"reasoning": {"effort": C.REASONING_EFFORT,
                                                   "exclude": True}}
            if response_format is not None:
                kwargs["response_format"] = response_format
            resp = client.chat.completions.create(**kwargs)
            latency_ms = int((time.time() - start) * 1000)

            text = (resp.choices[0].message.content or "")
            finish = getattr(resp.choices[0], "finish_reason", "") or ""
            served = getattr(resp, "model", "") or ""
            gen = getattr(resp, "id", "") or ""
            provider = getattr(resp, "provider", "") or ""
            pt, ct, rt, tt = _extract_usage(resp)
            cost = accountant.estimate_cost(slug, pt, ct)
            accountant.record(kind, cost)

            return APIResult(
                request_id=request_id, call_utc=call_utc,
                requested_model=slug, served_model=served, provider=provider,
                generation_id=gen,
                prompt_text=prompt_text, prompt_hash=prompt_hash,
                response_text=text, finish_reason=finish,
                prompt_tokens=pt, completion_tokens=ct,
                reasoning_tokens=rt, total_tokens=tt,
                cost_usd=cost, latency_ms=latency_ms,
                attempts=attempt + 1, error_message="",
                response_mode=response_mode,
            )
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            if attempt < max_transport_retries - 1:
                time.sleep(C.TRANSPORT_BACKOFF_BASE_S ** (attempt + 1))
                continue

    latency_ms = int((time.time() - start) * 1000)
    return APIResult(
        request_id=request_id, call_utc=call_utc,
        requested_model=slug, served_model="", provider="", generation_id="",
        prompt_text=prompt_text, prompt_hash=prompt_hash,
        response_text="", finish_reason="",
        prompt_tokens=0, completion_tokens=0, reasoning_tokens=0, total_tokens=0,
        cost_usd=0.0, latency_ms=latency_ms,
        attempts=max_transport_retries, error_message=last_error,
        response_mode=response_mode,
    )


# --- parsers --------------------------------------------------------------
_BATCH_RE = re.compile(r"^[HT]{50}$")
_ONLINE_RE = re.compile(r"^[HT]$")

def parse_batch(text: str) -> Optional[str]:
    if not text:
        return None
    stripped = "".join(text.split()).upper()
    return stripped if _BATCH_RE.match(stripped) else None

def parse_online(text: str) -> Optional[str]:
    if not text:
        return None
    stripped = text.strip().upper()
    return stripped if _ONLINE_RE.match(stripped) else None

def parse_judgment_json(text: str) -> Optional[str]:
    """Return 'SAME' | 'DIFFERENT' or None."""
    if not text:
        return None
    try:
        obj = json.loads(text.strip())
        v = obj.get("judgment")
        if v in ("SAME", "DIFFERENT"):
            return v
    except Exception:
        pass
    # sometimes models wrap in ```json fences
    m = re.search(r"\{[^{}]*\"judgment\"\s*:\s*\"(SAME|DIFFERENT)\"[^{}]*\}", text)
    if m:
        return m.group(1)
    return None

def parse_judgment_text(text: str) -> Optional[str]:
    if not text:
        return None
    up = text.strip().upper()
    if up in ("SAME", "DIFFERENT"):
        return up
    # last-token fallback
    tokens = re.findall(r"\b(SAME|DIFFERENT)\b", up)
    return tokens[-1] if tokens else None
