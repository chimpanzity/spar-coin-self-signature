"""OpenRouter HTTP client with catalog validation, retries, usage accounting, and a budget guard.

Every chat call is a fresh, stateless request. The client never keeps conversation state.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .config import OpenRouterConfig
from .records import iso, utc_now

log = logging.getLogger(__name__)

RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class OpenRouterError(Exception):
    """Base class for API-level failures."""


class OpenRouterAPIError(OpenRouterError):
    """A non-retryable (or retries-exhausted) API error."""

    def __init__(self, message: str, status_code: int | None = None, body: Any = None,
                 retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.retryable = retryable


class BudgetExceeded(OpenRouterError):
    """Raised before dispatch when the next call could push spend over the ceiling."""


class ModelCatalogError(OpenRouterError):
    """A configured model ID is missing from the live catalog."""


@dataclass
class CallResult:
    """Everything we keep from one chat completion call."""

    response_json: dict[str, Any]
    status_code: int
    request_id: str | None
    started_at: str
    completed_at: str
    latency_ms: int
    attempts: int = 1
    response_headers: dict[str, str] = field(default_factory=dict)

    @property
    def content(self) -> str | None:
        try:
            msg = self.response_json["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            return None
        content = msg.get("content")
        if isinstance(content, list):  # some routes return content parts
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return content

    @property
    def returned_model(self) -> str | None:
        return self.response_json.get("model")

    @property
    def provider(self) -> str | None:
        return self.response_json.get("provider")

    @property
    def usage(self) -> dict[str, Any] | None:
        u = self.response_json.get("usage")
        return u if isinstance(u, dict) else None

    @property
    def cost(self) -> float | None:
        u = self.usage
        if u and u.get("cost") is not None:
            try:
                return float(u["cost"])
            except (TypeError, ValueError):
                return None
        return None

    @property
    def finish_reason(self) -> str | None:
        try:
            return self.response_json["choices"][0].get("finish_reason")
        except (KeyError, IndexError, TypeError):
            return None

    def raw_dump(self) -> dict[str, Any]:
        return {
            "status_code": self.status_code,
            "request_id": self.request_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "latency_ms": self.latency_ms,
            "attempts": self.attempts,
            "response_headers": self.response_headers,
            "response_json": self.response_json,
        }


class ChatClient(Protocol):
    """The interface shared by the real and fake clients."""

    def list_models(self) -> list[dict[str, Any]]: ...
    def get_endpoints(self, model_id: str) -> dict[str, Any] | None: ...
    def get_key_info(self) -> dict[str, Any] | None: ...
    def chat_completion(self, payload: dict[str, Any]) -> CallResult: ...
    def close(self) -> None: ...


# ---------------------------------------------------------------- payload construction

def build_chat_payload(
    *,
    model_id: str,
    user_prompt: str,
    system_prompt: str | None,
    max_tokens: int,
    reasoning_effort: str | None,
    include_reasoning: bool,
    temperature: float | None,
    provider_allow_fallbacks: bool,
    provider_require_parameters: bool,
    response_format: dict[str, Any] | None = None,
    provider_order: list[str] | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """Build one stateless chat-completion payload.

    Parameters that are None are not sent at all (e.g. temperature on routes that do not
    support it). Reasoning uses OpenRouter's unified `reasoning` object; `exclude: true`
    is the unified form of `include_reasoning: false`. `provider_order` pins the request to
    the named provider(s) (OpenRouter tries them in order; with allow_fallbacks false, nothing
    else is ever used).
    """
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    provider: dict[str, Any] = {
        "allow_fallbacks": provider_allow_fallbacks,
        "require_parameters": provider_require_parameters,
    }
    if provider_order:
        provider["order"] = list(provider_order)
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": False,
        "usage": {"include": True},
        "provider": provider,
    }
    if reasoning_effort is not None:
        payload["reasoning"] = {"effort": reasoning_effort, "exclude": not include_reasoning}
    if temperature is not None:
        payload["temperature"] = temperature
    if response_format is not None:
        payload["response_format"] = response_format
    if seed is not None:
        payload["seed"] = seed
    return payload


def deterministic_seed(run_seed: int, record_id: str) -> int:
    """A stable 31-bit seed for one call, derived from the run seed and the record id."""
    import hashlib
    h = hashlib.sha256(f"{run_seed}:{record_id}".encode("utf-8")).hexdigest()
    return int(h[:8], 16) & 0x7FFFFFFF


def seed_for_call(cfg_send_seed: bool, run_seed: int, record_id: str, catalog_entry: dict[str, Any]) -> tuple[int, bool]:
    """(seed value, whether to send it). Sent only when enabled and the model advertises `seed`."""
    value = deterministic_seed(run_seed, record_id)
    return value, bool(cfg_send_seed and "seed" in supported_parameters(catalog_entry))


def structured_response_format(schema: dict[str, Any], name: str = "judgment") -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {"name": name, "strict": True, "schema": schema},
    }


# ---------------------------------------------------------------- budget guard

class BudgetGuard:
    """Hard cost ceiling enforced before every dispatch.

    `reserve` must be called before a request goes out and `settle` afterwards. In-flight
    reservations count against the ceiling so concurrent workers cannot jointly exceed it.
    """

    def __init__(self, max_cost_usd: float, spent_usd: float = 0.0):
        self.max_cost_usd = float(max_cost_usd)
        self.spent_usd = float(spent_usd)
        self.reserved_usd = 0.0
        self.calls = 0
        self._lock = threading.Lock()

    def reserve(self, est_cost_usd: float) -> None:
        with self._lock:
            projected = self.spent_usd + self.reserved_usd + est_cost_usd
            if projected > self.max_cost_usd:
                raise BudgetExceeded(
                    f"budget ceiling: spent ${self.spent_usd:.4f} + reserved ${self.reserved_usd:.4f} "
                    f"+ next ${est_cost_usd:.4f} would exceed max_cost_usd ${self.max_cost_usd:.2f}"
                )
            self.reserved_usd += est_cost_usd

    def settle(self, est_cost_usd: float, actual_cost_usd: float | None) -> None:
        with self._lock:
            self.reserved_usd = max(0.0, self.reserved_usd - est_cost_usd)
            self.spent_usd += actual_cost_usd if actual_cost_usd is not None else est_cost_usd
            self.calls += 1

    def snapshot(self) -> dict[str, float | int]:
        with self._lock:
            return {
                "max_cost_usd": self.max_cost_usd,
                "spent_usd": round(self.spent_usd, 6),
                "calls": self.calls,
            }


# ---------------------------------------------------------------- pricing helpers

def price_per_token(catalog_entry: dict[str, Any], kind: str) -> float:
    """Price in USD per token for 'prompt' or 'completion' from a catalog entry."""
    pricing = catalog_entry.get("pricing") or {}
    try:
        return float(pricing.get(kind) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def estimate_call_cost(catalog_entry: dict[str, Any], prompt_tokens: int, completion_tokens: int) -> float:
    return (prompt_tokens * price_per_token(catalog_entry, "prompt")
            + completion_tokens * price_per_token(catalog_entry, "completion"))


def estimate_cost_from_usage(catalog_entry: dict[str, Any], usage: dict[str, Any] | None, fallback: float) -> float:
    """Cost estimate from the response's token counts x catalog prices; `fallback` if no usage."""
    if not usage:
        return fallback
    try:
        p = int(usage.get("prompt_tokens") or 0)
        c = int(usage.get("completion_tokens") or 0)
    except (TypeError, ValueError):
        return fallback
    if p == 0 and c == 0:
        return fallback
    return estimate_call_cost(catalog_entry, p, c)


# ---------------------------------------------------------------- real client

def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):  # timeouts, connection errors, protocol errors
        return True
    return isinstance(exc, OpenRouterAPIError) and exc.retryable


class OpenRouterClient:
    def __init__(self, cfg: OpenRouterConfig, api_key: str | None, transport: Any = None, retry_wait: Any = None):
        """`transport` and `retry_wait` exist for tests (httpx.MockTransport, tenacity.wait_none())."""
        self.cfg = cfg
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if cfg.app_title:
            headers["X-Title"] = cfg.app_title
        self._client = httpx.Client(
            base_url=cfg.base_url.rstrip("/"),
            headers=headers,
            timeout=httpx.Timeout(cfg.request_timeout_seconds, connect=30.0),
            transport=transport,
        )
        self._retry = retry(
            reraise=True,
            retry=retry_if_exception(_is_retryable),
            stop=stop_after_attempt(max(1, cfg.max_retries + 1)),
            wait=retry_wait if retry_wait is not None else wait_exponential_jitter(initial=2, max=30, jitter=2),
            before_sleep=lambda rs: log.warning(
                "retrying OpenRouter call (attempt %d) after: %s", rs.attempt_number, rs.outcome.exception()
            ),
        )

    # -- catalog -------------------------------------------------------------------------
    def list_models(self) -> list[dict[str, Any]]:
        resp = self._client.get("/models")
        resp.raise_for_status()
        data = resp.json().get("data")
        if not isinstance(data, list):
            raise OpenRouterAPIError("unexpected /models response shape", resp.status_code, resp.text)
        return data

    def get_endpoints(self, model_id: str) -> dict[str, Any] | None:
        try:
            resp = self._client.get(f"/models/{model_id}/endpoints")
            if resp.status_code != 200:
                log.warning("endpoints lookup for %s returned HTTP %s", model_id, resp.status_code)
                return {"error": f"HTTP {resp.status_code}", "body": _safe_json(resp)}
            return resp.json().get("data")
        except httpx.HTTPError as exc:
            log.warning("endpoints lookup for %s failed: %s", model_id, exc)
            return {"error": str(exc)}

    def get_key_info(self) -> dict[str, Any] | None:
        try:
            resp = self._client.get("/auth/key")
            if resp.status_code != 200:
                return {"error": f"HTTP {resp.status_code}"}
            return resp.json().get("data")
        except httpx.HTTPError as exc:
            return {"error": str(exc)}

    # -- chat ----------------------------------------------------------------------------
    def chat_completion(self, payload: dict[str, Any]) -> CallResult:
        started = utc_now()
        t0 = time.perf_counter()
        attempts = {"n": 0}

        def _once() -> tuple[httpx.Response, dict[str, Any]]:
            attempts["n"] += 1
            resp = self._client.post("/chat/completions", json=payload)
            body = _safe_json(resp)
            if resp.status_code != 200:
                msg = _error_message(body) or resp.text[:500]
                raise OpenRouterAPIError(
                    f"HTTP {resp.status_code}: {msg}", resp.status_code, body,
                    retryable=resp.status_code in RETRYABLE_STATUS,
                )
            if isinstance(body, dict) and body.get("error"):
                code = body["error"].get("code") if isinstance(body["error"], dict) else None
                try:
                    code_int = int(code) if code is not None else None
                except (TypeError, ValueError):
                    code_int = None
                raise OpenRouterAPIError(
                    f"API error in 200 body: {_error_message(body)}", code_int, body,
                    retryable=code_int in RETRYABLE_STATUS,
                )
            if not isinstance(body, dict) or "choices" not in body:
                raise OpenRouterAPIError("response has no choices", resp.status_code, body, retryable=True)
            # OpenRouter reports some provider-side failures inside the choice (finish_reason "error").
            try:
                choice0 = body["choices"][0]
            except (IndexError, TypeError):
                raise OpenRouterAPIError("response has an empty choices list", resp.status_code, body, retryable=True)
            if isinstance(choice0, dict) and (choice0.get("error") or choice0.get("finish_reason") == "error"):
                err = choice0.get("error") or {}
                code = err.get("code") if isinstance(err, dict) else None
                try:
                    code_int = int(code) if code is not None else None
                except (TypeError, ValueError):
                    code_int = None
                raise OpenRouterAPIError(
                    f"provider error in choice: {_error_message({'error': err}) or choice0.get('finish_reason')}",
                    code_int, body, retryable=code_int in RETRYABLE_STATUS,
                )
            return resp, body

        try:
            resp, body = self._retry(_once)()
        except httpx.TransportError as exc:
            # Retries exhausted on timeouts / connection errors: surface as an API error so the
            # phase records it and stops cleanly instead of crashing with a traceback.
            raise OpenRouterAPIError(
                f"transport failure after {attempts['n']} attempt(s): {exc.__class__.__name__}: {exc}",
                None, None, retryable=False,
            ) from exc
        except RetryError as exc:  # pragma: no cover - reraise=True means we rarely get here
            raise OpenRouterAPIError(f"retries exhausted: {exc}") from exc
        completed = utc_now()
        latency_ms = int((time.perf_counter() - t0) * 1000)
        headers = {k: v for k, v in resp.headers.items() if k.lower().startswith("x-") or k.lower() == "date"}
        request_id = body.get("id") or resp.headers.get("x-request-id")
        return CallResult(
            response_json=body,
            status_code=resp.status_code,
            request_id=request_id,
            started_at=iso(started),
            completed_at=iso(completed),
            latency_ms=latency_ms,
            attempts=attempts["n"],
            response_headers=headers,
        )

    def close(self) -> None:
        self._client.close()


def _safe_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except (json.JSONDecodeError, ValueError):
        return {"raw_text": resp.text[:2000]}


def _error_message(body: Any) -> str | None:
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            meta = err.get("metadata")
            msg = str(err.get("message", ""))
            if isinstance(meta, dict) and meta.get("raw"):
                msg += f" | {str(meta['raw'])[:300]}"
            return msg
        if err:
            return str(err)
    return None


# ---------------------------------------------------------------- catalog validation

def validate_catalog(catalog: list[dict[str, Any]], model_ids: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Return {label: catalog_entry} for the configured IDs; raise if any ID is missing."""
    by_id = {m.get("id"): m for m in catalog if isinstance(m, dict)}
    found: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for label, model_id in model_ids.items():
        entry = by_id.get(model_id)
        if entry is None:
            missing.append(f"{label} -> {model_id}")
        else:
            found[label] = entry
    if missing:
        # Offer near matches to make a typo or a renamed ID easy to spot.
        hints = []
        for label, model_id in model_ids.items():
            if label in found:
                continue
            stem = model_id.split("/")[-1].split("-")[0][:6].lower()
            near = [i for i in by_id if isinstance(i, str) and stem and stem in i.lower()][:8]
            hints.append(f"  {model_id}: similar catalog IDs -> {near or 'none'}")
        raise ModelCatalogError(
            "configured model ID(s) not present in the OpenRouter catalog: "
            + "; ".join(missing) + "\n" + "\n".join(hints)
        )
    return found


def supported_parameters(entry: dict[str, Any]) -> list[str]:
    params = entry.get("supported_parameters")
    return list(params) if isinstance(params, list) else []
