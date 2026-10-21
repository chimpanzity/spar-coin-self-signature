"""Capability + endpoint + provider-pin preflight for DICE_PILOT_v4.1.

Three unpaid responsibilities:

1. Fetch OpenRouter model catalog, verify every target slug exists, read
   supported_parameters and pricing per model.
2. For each model, call OpenRouter's `/models/{slug}/endpoints` endpoint to
   list the providers that serve it (plus their quantization info). Pick
   one and set it as the pinned provider for that model, recording the
   choice in a report.
3. Project worst-case total cost against the $10 cap under the per-model
   `max_tokens` setting.
"""

from __future__ import annotations

import json, os, time, urllib.request
from typing import Any, Dict, List, Optional

from openai import OpenAI

from . import config as C


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------- catalog --

def fetch_catalog(client: OpenAI) -> Dict[str, Any]:
    want = {m.slug for m in C.MODELS}
    found: Dict[str, Any] = {}
    models = client.models.list()
    for m in models.data:
        if m.id in want:
            pricing = (getattr(m, "pricing", {}) or {})
            found[m.id] = {
                "id": m.id,
                "pricing": {
                    "prompt": float(pricing.get("prompt", 0.0) or 0.0),
                    "completion": float(pricing.get("completion", 0.0) or 0.0),
                    "internal_reasoning": float(pricing.get("internal_reasoning", 0.0) or 0.0),
                },
                "context_length": getattr(m, "context_length", None),
                "supported_parameters": sorted(getattr(m, "supported_parameters", None) or []),
            }
    missing = sorted(want - set(found.keys()))
    return {"fetched_utc": _utc(), "models": found, "missing": missing}


# ---------------------------------------------------------------- endpoints --

def fetch_endpoints(api_key: str, slug: str) -> Dict[str, Any]:
    """Query OR's /api/v1/models/{slug}/endpoints. Returns raw JSON dict.

    This endpoint lists every provider that serves a given model id, along
    with quantization, context length, and status fields where exposed.
    """
    # slug can contain '/'; URL-encode by splitting on first '/' into author/slug
    url = f"https://openrouter.ai/api/v1/models/{slug}/endpoints"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def pick_pinned_provider(endpoints_payload: Dict[str, Any]) -> Dict[str, Any]:
    """From an /endpoints response, pick the first non-batch provider as the
    pin. Return {provider, quantization, context_length, status} dict.

    Batch endpoints are identified by `is_batch=True` or by their id/name
    containing ':batch'. OR's schema uses nested `endpoints` list.
    """
    data = endpoints_payload.get("data") or endpoints_payload
    eps = data.get("endpoints") or []
    non_batch = [e for e in eps if not str(e.get("provider_name") or "").endswith(":batch")]
    non_batch = [e for e in non_batch if not str(e.get("name") or "").endswith(":batch")]
    non_batch = [e for e in non_batch if not e.get("is_batch", False)]
    if not non_batch and eps:
        non_batch = eps  # fall back
    if not non_batch:
        return {"provider_name": None, "quantization": None,
                "context_length": None, "status": None,
                "all_providers": []}
    pick = non_batch[0]
    return {
        "provider_name": pick.get("provider_name") or pick.get("name"),
        "quantization": pick.get("quantization"),
        "context_length": pick.get("context_length"),
        "max_completion_tokens": pick.get("max_completion_tokens"),
        "status": pick.get("status"),
        "supported_parameters": sorted(pick.get("supported_parameters") or []),
        "all_providers": [e.get("provider_name") or e.get("name") for e in eps],
    }


def resolve_providers(api_key: str) -> Dict[str, Dict[str, Any]]:
    """For each MODEL, if its config has no preferred_provider, query the
    endpoints API and pick one. Return per-label resolution dict."""
    out: Dict[str, Dict[str, Any]] = {}
    for m in C.MODELS:
        info: Dict[str, Any] = {"slug": m.slug, "configured_pin": m.preferred_provider}
        if m.preferred_provider:
            info["resolved_provider"] = m.preferred_provider
            info["source"] = "config"
            info["all_providers"] = [m.preferred_provider]
        else:
            try:
                payload = fetch_endpoints(api_key, m.slug)
                pick = pick_pinned_provider(payload)
                info.update(pick)
                info["resolved_provider"] = pick.get("provider_name")
                info["source"] = "endpoints_api"
            except Exception as e:
                info["error"] = str(e)[:200]
                info["resolved_provider"] = None
                info["source"] = "error"
        out[m.label] = info
    return out


# ---------------------------------------------------------------- verification --

def verify_against_config(catalog: Dict[str, Any],
                            providers: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    issues: List[str] = []
    per_model: Dict[str, Dict[str, Any]] = {}
    if catalog.get("missing"):
        issues.append(f"missing slugs in catalog: {catalog['missing']}")
    for m in C.MODELS:
        info = catalog["models"].get(m.slug)
        prov = providers.get(m.label) or {}
        if info is None:
            issues.append(f"{m.label} ({m.slug}): catalog entry missing")
            continue
        sp = set(info["supported_parameters"])
        temp_live = "temperature" in sp
        reas_live = ("reasoning" in sp) or ("reasoning_effort" in sp)
        v = {
            "label": m.label, "slug": m.slug,
            "supports_temperature_live": temp_live,
            "supports_temperature_config": m.supports_temperature,
            "temperature_flag_matches": temp_live == m.supports_temperature,
            "supports_reasoning_live": reas_live,
            "pricing_prompt_per_mtok": info["pricing"]["prompt"] * 1e6,
            "pricing_completion_per_mtok": info["pricing"]["completion"] * 1e6,
            "pricing_internal_reasoning_per_mtok": info["pricing"]["internal_reasoning"] * 1e6,
            "context_length": info["context_length"],
            "supported_parameters": info["supported_parameters"],
            "reasoning_config_label": m.reasoning_config_label,
            "reasoning_effort_requested": m.reasoning_effort_requested,
            "reasoning_enabled_false": m.reasoning_enabled_false,
            "max_tokens": m.max_tokens,
            "resolved_provider": prov.get("resolved_provider"),
            "quantization": prov.get("quantization"),
            "all_providers": prov.get("all_providers"),
            "provider_source": prov.get("source"),
        }
        if not v["temperature_flag_matches"]:
            issues.append(
                f"{m.label}: supports_temperature drift (config={m.supports_temperature}, live={temp_live})")
        if v["resolved_provider"] is None:
            issues.append(f"{m.label}: no provider resolved")
        per_model[m.label] = v
    return {"ok": not issues, "issues": issues, "per_model": per_model,
            "fetched_utc": catalog.get("fetched_utc")}


def write_capability_report(client: OpenAI, api_key: str, out_dir: str) -> Dict[str, Any]:
    catalog = fetch_catalog(client)
    providers = resolve_providers(api_key)
    verdict = verify_against_config(catalog, providers)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "model_capabilities.json"), "w", encoding="utf-8") as f:
        json.dump({"catalog": catalog, "providers": providers,
                    "verdict": verdict}, f, indent=2, sort_keys=True)
    return verdict


# ---------------------------------------------------------------- cost projection --

def worst_case_per_call_cost(label: str, verdict_per_model: Dict[str, Any]) -> float:
    v = verdict_per_model[label]
    pp = v["pricing_prompt_per_mtok"] / 1e6
    cp = v["pricing_completion_per_mtok"] / 1e6
    prompt_tokens_worst = 400
    return prompt_tokens_worst * pp + v["max_tokens"] * cp


def budget_projection(verdict: Dict[str, Any]) -> Dict[str, Any]:
    rows = []
    total = 0.0
    for m in C.MODELS:
        if m.label not in verdict["per_model"]:
            rows.append({"model": m.label, "config": m.reasoning_config_label,
                          "supported": False, "n_calls": 0,
                          "per_call_usd_worst_case": None,
                          "subtotal_usd_worst_case": 0.0})
            continue
        per_call = worst_case_per_call_cost(m.label, verdict["per_model"])
        subtotal = per_call * C.TOTAL_CALLS_PER_MODEL
        total += subtotal
        rows.append({"model": m.label, "config": m.reasoning_config_label,
                      "supported": True, "n_calls": C.TOTAL_CALLS_PER_MODEL,
                      "per_call_usd_worst_case": round(per_call, 6),
                      "subtotal_usd_worst_case": round(subtotal, 4),
                      "max_tokens": m.max_tokens})
    return {"rows": rows, "total_usd_worst_case": round(total, 4),
            "budget_cap_usd": C.BUDGET_USD_CAP,
            "within_cap": total <= C.BUDGET_USD_CAP}
