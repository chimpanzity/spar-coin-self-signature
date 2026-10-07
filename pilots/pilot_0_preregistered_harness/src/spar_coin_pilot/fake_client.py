"""Deterministic fake OpenRouter client for tests and the `demo-fake` command.

It implements the same interface as OpenRouterClient but never touches the network. Responses
mimic the shape of real OpenRouter chat completions (choices, usage with cost, model, provider,
id) so that the rest of the pipeline is exercised unchanged.
"""

from __future__ import annotations

import json
import random
import threading
from typing import Any, Callable

from .openrouter_client import CallResult, OpenRouterAPIError
from .records import iso, utc_now

FAKE_PROVIDER = "FakeProvider"


def default_fake_catalog(model_ids: list[str], name_suffix: str = "") -> list[dict[str, Any]]:
    entries = []
    for mid in model_ids:
        entries.append({
            "id": mid,
            "name": f"Fake {mid}{name_suffix}",
            "created": 1700000000,
            "canonical_slug": f"{mid}-2026-01-01",
            "pricing": {"prompt": "0.000002", "completion": "0.000010", "internal_reasoning": "0.000010"},
            "context_length": 128000,
            "top_provider": {"max_completion_tokens": 32000},
            "supported_parameters": [
                "max_tokens", "reasoning", "include_reasoning", "response_format",
                "structured_outputs", "temperature", "top_p", "seed",
            ],
        })
    entries.append({
        "id": "decoy/decoy-model", "name": "Decoy", "pricing": {"prompt": "0", "completion": "0"},
        "supported_parameters": ["max_tokens"],
    })
    return entries


class FakeOpenRouterClient:
    """A stand-in client.

    Parameters
    ----------
    model_ids: the IDs that should appear in the fake catalog.
    seed: RNG seed for generated strings and judgments.
    invalid_source_schedule: set of 1-based source-call indices that return malformed output.
    invalid_judgment_schedule: set of 1-based judgment-call indices that return malformed output.
    structured_supported: if False, any request carrying response_format fails with HTTP 400.
    judgment_policy: optional callable(payload) -> "SAME" | "DIFFERENT"; default random.
    cost_per_call: reported usage.cost per call (USD).
    fail_on_call: optional set of global call indices that raise a non-retryable error.
    """

    def __init__(
        self,
        model_ids: list[str],
        seed: int = 0,
        invalid_source_schedule: set[int] | None = None,
        invalid_judgment_schedule: set[int] | None = None,
        structured_supported: bool = True,
        judgment_policy: Callable[[dict[str, Any]], str] | None = None,
        cost_per_call: float = 0.001,
        fail_on_call: set[int] | None = None,
        string_length: int = 50,
        alphabet: str = "HT",
        source_bias: dict[str, float] | None = None,
        catalog_name_suffix: str = "",
        report_cost: bool = True,
        provider_name: str = FAKE_PROVIDER,
    ):
        self.model_ids = list(model_ids)
        self.rng = random.Random(seed)
        self.invalid_source_schedule = invalid_source_schedule or set()
        self.invalid_judgment_schedule = invalid_judgment_schedule or set()
        self.structured_supported = structured_supported
        self.judgment_policy = judgment_policy
        self.cost_per_call = cost_per_call
        self.fail_on_call = fail_on_call or set()
        self.string_length = string_length
        self.alphabet = alphabet
        # Per-model P(first symbol) so fake sources are mildly distinguishable.
        self.source_bias = source_bias or {}
        self.catalog_name_suffix = catalog_name_suffix   # non-empty simulates catalog identity drift
        self.report_cost = report_cost                   # False simulates a route that omits usage.cost
        self.provider_name = provider_name               # provider reported in endpoints and responses
        self.calls: list[dict[str, Any]] = []
        self.source_calls = 0
        self.judgment_calls = 0
        self._lock = threading.Lock()

    # -- catalog ---------------------------------------------------------------------------
    def list_models(self) -> list[dict[str, Any]]:
        return default_fake_catalog(self.model_ids, self.catalog_name_suffix)

    def get_endpoints(self, model_id: str) -> dict[str, Any] | None:
        return {
            "id": model_id,
            "endpoints": [{
                "name": f"{model_id} | {self.provider_name}",
                "provider_name": self.provider_name,
                "supported_parameters": ["max_tokens", "reasoning", "response_format", "structured_outputs"],
                "pricing": {"prompt": "0.000002", "completion": "0.000010"},
            }],
        }

    def get_key_info(self) -> dict[str, Any] | None:
        return {"label": "fake-key", "usage": 0.0, "limit": None, "is_free_tier": False}

    # -- chat ------------------------------------------------------------------------------
    def chat_completion(self, payload: dict[str, Any]) -> CallResult:
        with self._lock:
            self.calls.append(json.loads(json.dumps(payload)))
            call_index = len(self.calls)
            user_msgs = [m for m in payload["messages"] if m["role"] == "user"]
            prompt = user_msgs[-1]["content"] if user_msgs else ""
            is_preflight = "format check" in prompt
            is_judgment = is_preflight or "String 1:" in prompt or payload.get("response_format") is not None
            if is_preflight:
                idx = 0  # preflight calls are not counted against the invalid schedules
            elif is_judgment:
                self.judgment_calls += 1
                idx = self.judgment_calls
            else:
                self.source_calls += 1
                idx = self.source_calls

            if call_index in self.fail_on_call:
                raise OpenRouterAPIError("fake non-retryable failure", 400, {"error": "fake"}, retryable=False)

            if payload.get("response_format") is not None and not self.structured_supported:
                raise OpenRouterAPIError(
                    "HTTP 400: response_format is not supported by this provider (fake)", 400,
                    {"error": {"message": "unsupported parameter: response_format"}}, retryable=False,
                )

            if is_judgment:
                content = self._judgment_content(payload, idx)
            else:
                content = self._source_content(payload, idx)

            started = utc_now()
            body = {
                "id": f"gen-fake-{call_index:05d}",
                "model": payload["model"],
                "provider": self.provider_name,
                "object": "chat.completion",
                "created": int(started.timestamp()),
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }],
                "usage": {
                    "prompt_tokens": max(1, len(prompt) // 4),
                    "completion_tokens": max(1, len(content) // 2),
                    "total_tokens": max(1, len(prompt) // 4) + max(1, len(content) // 2),
                },
            }
            if self.report_cost:
                body["usage"]["cost"] = self.cost_per_call
            return CallResult(
                response_json=body, status_code=200, request_id=body["id"],
                started_at=iso(started), completed_at=iso(utc_now()), latency_ms=3, attempts=1,
            )

    def _source_content(self, payload: dict[str, Any], idx: int) -> str:
        a, b = self.alphabet[0], self.alphabet[1]
        p = self.source_bias.get(payload["model"], 0.5)
        s = "".join(a if self.rng.random() < p else b for _ in range(self.string_length))
        if idx in self.invalid_source_schedule:
            variants = [
                f"Sure! Here are your flips: {s}",  # explanation
                s[:-1],                              # 49 chars
                s + "\n" + a,                        # 51 chars with newline
                s.lower(),                           # wrong case
            ]
            return variants[idx % len(variants)]
        return s + ("\n" if idx % 2 == 0 else "")  # trailing whitespace is allowed

    def _judgment_content(self, payload: dict[str, Any], idx: int) -> str:
        structured = payload.get("response_format") is not None
        user_msgs = [m for m in payload["messages"] if m["role"] == "user"]
        if user_msgs and "format check" in user_msgs[-1]["content"]:
            return json.dumps({"judgment": "SAME"}) if structured else "SAME"
        if self.judgment_policy is not None:
            label = self.judgment_policy(payload)
        else:
            label = "SAME" if self.rng.random() < 0.5 else "DIFFERENT"
        if idx in self.invalid_judgment_schedule:
            return '{"judgment": "MAYBE"}' if structured else "I think they are SAME or maybe DIFFERENT."
        if structured:
            return json.dumps({"judgment": label})
        return f"{label}." if idx % 3 == 0 else label

    def close(self) -> None:
        return None
