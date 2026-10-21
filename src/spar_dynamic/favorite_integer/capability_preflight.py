"""Capability + pricing preflight for FAVORITE_INTEGER_v1.0.

Fetches live OR catalog for the three target slugs, verifies against the
config, and projects worst-case cost against the $10 cap. Providers are
hard-pinned in config (astra→openai, fable→anthropic, oss120→DeepInfra); no
endpoints-API probe is needed this time.
"""

from __future__ import annotations

import json, os, time
from typing import Any, Dict, List

from openai import OpenAI

from . import config as C


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def verify_against_config(catalog: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[str] = []
    per_model: Dict[str, Dict[str, Any]] = {}
    if catalog.get("missing"):
        issues.append(f"missing slugs in catalog: {catalog['missing']}")
    for m in C.MODELS:
        info = catalog["models"].get(m.slug)
        if info is None:
            issues.append(f"{m.label} ({m.slug}): catalog entry missing")
            continue
        sp = set(info["supported_parameters"])
        temp_live = "temperature" in sp
        v = {
            "label": m.label, "slug": m.slug,
            "supports_temperature_live": temp_live,
            "supports_temperature_config": m.supports_temperature,
            "temperature_flag_matches": temp_live == m.supports_temperature,
            "supports_reasoning_live": ("reasoning" in sp) or ("reasoning_effort" in sp),
            "pricing_prompt_per_mtok": info["pricing"]["prompt"] * 1e6,
            "pricing_completion_per_mtok": info["pricing"]["completion"] * 1e6,
            "pricing_internal_reasoning_per_mtok": info["pricing"]["internal_reasoning"] * 1e6,
            "context_length": info["context_length"],
            "supported_parameters": info["supported_parameters"],
            "preferred_provider": m.preferred_provider,
            "max_tokens": m.max_tokens,
            "reasoning_config_label": m.reasoning_config_label,
            "reasoning_effort_requested": m.reasoning_effort_requested,
        }
        if not v["temperature_flag_matches"]:
            issues.append(
                f"{m.label}: supports_temperature drift (config={m.supports_temperature}, live={temp_live})")
        per_model[m.label] = v
    return {"ok": not issues, "issues": issues, "per_model": per_model,
            "fetched_utc": catalog.get("fetched_utc")}


def write_capability_report(client: OpenAI, out_dir: str) -> Dict[str, Any]:
    catalog = fetch_catalog(client)
    verdict = verify_against_config(catalog)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "model_capabilities.json"), "w", encoding="utf-8") as f:
        json.dump({"catalog": catalog, "verdict": verdict}, f, indent=2, sort_keys=True)
    return verdict


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
