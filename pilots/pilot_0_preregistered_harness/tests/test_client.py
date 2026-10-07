"""Real OpenRouterClient behavior against an httpx.MockTransport (no network)."""

import json

import httpx
import pytest
from tenacity import wait_none

from spar_coin_pilot.config import OpenRouterConfig
from spar_coin_pilot.openrouter_client import (
    ModelCatalogError,
    OpenRouterAPIError,
    OpenRouterClient,
    build_chat_payload,
    structured_response_format,
    validate_catalog,
)

OK_BODY = {
    "id": "gen-123", "model": "openai/gpt-6-astra", "provider": "OpenAI",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "HT" * 25}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 40, "completion_tokens": 30, "total_tokens": 70, "cost": 0.0021},
}


def make_client(handler, max_retries=3):
    cfg = OpenRouterConfig(max_retries=max_retries, request_timeout_seconds=5)
    return OpenRouterClient(cfg, "sk-test", transport=httpx.MockTransport(handler), retry_wait=wait_none())


def payload(**kw):
    base = dict(model_id="openai/gpt-6-astra", user_prompt="hi", system_prompt=None, max_tokens=100,
                reasoning_effort="low", include_reasoning=False, temperature=None,
                provider_allow_fallbacks=False, provider_require_parameters=True)
    base.update(kw)
    return build_chat_payload(**base)


def test_payload_shape_matches_openrouter_api():
    p = payload(response_format=structured_response_format({"type": "object"}))
    assert p["messages"] == [{"role": "user", "content": "hi"}]
    assert p["reasoning"] == {"effort": "low", "exclude": True}
    assert p["provider"] == {"allow_fallbacks": False, "require_parameters": True}
    assert p["usage"] == {"include": True}
    assert p["response_format"]["type"] == "json_schema"
    assert p["response_format"]["json_schema"]["strict"] is True
    assert "temperature" not in p and p["stream"] is False
    p2 = payload(temperature=0.0, system_prompt="sys", reasoning_effort=None)
    assert p2["temperature"] == 0.0 and "reasoning" not in p2
    assert [m["role"] for m in p2["messages"]] == ["system", "user"]


def test_successful_call_records_headers_and_usage():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        seen["title"] = request.headers.get("x-title")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=OK_BODY, headers={"x-request-id": "req-1"})

    c = make_client(handler)
    r = c.chat_completion(payload())
    assert seen["auth"] == "Bearer sk-test" and seen["title"] == "spar-coin-pilot"
    assert seen["body"]["model"] == "openai/gpt-6-astra"
    assert r.content == "HT" * 25 and r.cost == pytest.approx(0.0021) and r.returned_model == "openai/gpt-6-astra"
    assert r.provider == "OpenAI" and r.request_id == "gen-123" and r.attempts == 1
    assert r.finish_reason == "stop"


def test_429_then_success_is_retried():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, json={"error": {"message": "rate limited"}})
        return httpx.Response(200, json=OK_BODY)

    r = make_client(handler).chat_completion(payload())
    assert calls["n"] == 3 and r.attempts == 3 and r.content == "HT" * 25


def test_400_is_not_retried_and_raises_api_error():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(400, json={"error": {"message": "unsupported parameter: temperature", "code": 400}})

    with pytest.raises(OpenRouterAPIError) as ei:
        make_client(handler).chat_completion(payload())
    assert calls["n"] == 1 and ei.value.status_code == 400 and not ei.value.retryable
    assert "temperature" in str(ei.value)


def test_transport_errors_exhaust_retries_and_become_api_error():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        raise httpx.ConnectError("boom")

    with pytest.raises(OpenRouterAPIError) as ei:
        make_client(handler, max_retries=2).chat_completion(payload())
    assert calls["n"] == 3
    assert "transport failure after 3 attempt(s)" in str(ei.value)


def test_error_inside_200_body_and_inside_choice_are_api_errors():
    def handler_body(request):
        return httpx.Response(200, json={"error": {"message": "provider down", "code": 502}})

    with pytest.raises(OpenRouterAPIError) as ei:
        make_client(handler_body, max_retries=1).chat_completion(payload())
    assert "provider down" in str(ei.value)

    def handler_choice(request):
        body = dict(OK_BODY)
        body["choices"] = [{"index": 0, "message": {"role": "assistant", "content": ""}, "finish_reason": "error",
                            "error": {"message": "upstream overloaded", "code": 400}}]
        return httpx.Response(200, json=body)

    with pytest.raises(OpenRouterAPIError) as ei:
        make_client(handler_choice, max_retries=1).chat_completion(payload())
    assert "upstream overloaded" in str(ei.value)


def test_missing_model_id_aborts_before_spending():
    catalog = [{"id": "openai/gpt-6-astra"}, {"id": "anthropic/claude-fable-5.1"}, {"id": "qwen/qwen3.8-27b-instruct"}]
    with pytest.raises(ModelCatalogError) as ei:
        validate_catalog(catalog, {"astra": "openai/gpt-6-astra", "fable": "anthropic/claude-fable-5.1",
                                   "qwen": "qwen/qwen3.8-27b"})
    msg = str(ei.value)
    assert "qwen -> qwen/qwen3.8-27b" in msg and "qwen/qwen3.8-27b-instruct" in msg
    found = validate_catalog(catalog, {"astra": "openai/gpt-6-astra"})
    assert found["astra"]["id"] == "openai/gpt-6-astra"


def test_list_models_uses_data_array():
    def handler(request):
        assert request.url.path.endswith("/models")
        return httpx.Response(200, json={"data": [{"id": "a/b"}]})

    assert make_client(handler).list_models() == [{"id": "a/b"}]
