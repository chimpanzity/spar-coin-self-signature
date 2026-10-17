"""OpenRouter capability + pricing preflight for the dice-pilot (spec §4).

Fetches live model metadata for the three target slugs and writes
`model_capabilities.json` into a run directory. Verifies the as-of-now
`supports_temperature` and `supports_reasoning` flags we baked into
`config.MODELS` against what OpenRouter currently reports. If anything has
changed since 2026-10-15, the preflight fails loudly rather than silently.
"""

from __future__ import annotations

import json, os, time
from typing import Any, Dict, List

from openai import OpenAI

from . import config as C


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def fetch_capabilities(client: OpenAI) -> Dict[str, Any]:
    want = {m.slug for m in C.MODELS}
    found: Dict[str, Any] = {}
    try:
        models = client.models.list()
    except Exception as e:
        raise RuntimeError(f"OpenRouter catalog fetch failed: {e}") from e
    for m in models.data:
        if m.id in want:
            found[m.id] = {
                "id": m.id,
                "pricing": {
                    "prompt": float((getattr(m, "pricing", {}) or {}).get("prompt", 0.0) or 0.0),
                    "completion": float((getattr(m, "pricing", {}) or {}).get("completion", 0.0) or 0.0),
                    "internal_reasoning": float((getattr(m, "pricing", {}) or {}).get("internal_reasoning", 0.0) or 0.0),
                },
                "context_length": getattr(m, "context_length", None),
                "supported_parameters": sorted(getattr(m, "supported_parameters", None) or []),
            }
    missing = sorted(want - set(found.keys()))
    return {"fetched_utc": _utc(), "models": found, "missing": missing}


def verify_against_config(caps: Dict[str, Any]) -> Dict[str, Any]:
    """Compare live capabilities to config.MODELS flags and return a verdict."""
    issues: List[str] = []
    verdict_per_model: Dict[str, Dict[str, Any]] = {}
    if caps.get("missing"):
        issues.append(f"missing slugs in catalog: {caps['missing']}")
    for m in C.MODELS:
        info = caps["models"].get(m.slug)
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
            "supports_reasoning_config": m.supports_reasoning,
            "reasoning_flag_matches": reas_live == m.supports_reasoning,
            "pricing_prompt_per_mtok": info["pricing"]["prompt"] * 1e6,
            "pricing_completion_per_mtok": info["pricing"]["completion"] * 1e6,
            "pricing_internal_reasoning_per_mtok": info["pricing"]["internal_reasoning"] * 1e6,
            "context_length": info["context_length"],
            "supported_parameters": info["supported_parameters"],
        }
        if not v["temperature_flag_matches"]:
            issues.append(
                f"{m.label}: supports_temperature flag drift (config={m.supports_temperature}, "
                f"live={temp_live})")
        if not v["reasoning_flag_matches"]:
            issues.append(
                f"{m.label}: supports_reasoning flag drift (config={m.supports_reasoning}, "
                f"live={reas_live})")
        verdict_per_model[m.label] = v
    return {"ok": not issues, "issues": issues, "per_model": verdict_per_model,
            "fetched_utc": caps.get("fetched_utc")}


def write_capability_report(client: OpenAI, out_dir: str) -> Dict[str, Any]:
    caps = fetch_capabilities(client)
    verdict = verify_against_config(caps)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "model_capabilities.json"), "w", encoding="utf-8") as f:
        json.dump({"caps": caps, "verdict": verdict}, f, indent=2, sort_keys=True)
    return verdict


def worst_case_per_call_cost(label: str, verdict_per_model: Dict[str, Any],
                              r1: bool) -> float:
    """Cost upper bound for a single call at MAX_TOKENS output and ~200-token
    prompt. On R1 the full max_tokens budget may be reasoning tokens; on R0
    assume at most ~64 output tokens of reasoning noise."""
    v = verdict_per_model[label]
    prompt_tokens_worst = 400
    completion_cap = C.MAX_TOKENS                       # worst: all tokens billed at completion rate
    pp = v["pricing_prompt_per_mtok"] / 1e6
    cp = v["pricing_completion_per_mtok"] / 1e6
    # internal_reasoning price is $0/M for all three models (per 2026-10-15 catalog).
    # Reasoning tokens therefore bill at the completion rate.
    out_tokens_worst = completion_cap if r1 else 64
    return prompt_tokens_worst * pp + out_tokens_worst * cp


def budget_projection(verdict: Dict[str, Any]) -> Dict[str, Any]:
    """Project total pilot cost per model/config using the worst-case bound."""
    rows = []
    total = 0.0
    for m in C.MODELS:
        for config_name, is_r1 in (("R0", False), ("R1", True)):
            supported = m.r1_supported if is_r1 else m.r0_supported
            if not supported:
                rows.append({"model": m.label, "config": config_name,
                             "supported": False, "n_calls": 0,
                             "per_call_usd_worst_case": None,
                             "subtotal_usd_worst_case": 0.0})
                continue
            per_call = worst_case_per_call_cost(m.label, verdict["per_model"], is_r1)
            subtotal = per_call * C.TOTAL_CALLS_PER_CONFIG
            total += subtotal
            rows.append({"model": m.label, "config": config_name,
                          "supported": True, "n_calls": C.TOTAL_CALLS_PER_CONFIG,
                          "per_call_usd_worst_case": round(per_call, 4),
                          "subtotal_usd_worst_case": round(subtotal, 4)})
    return {"rows": rows, "total_usd_worst_case": round(total, 4),
            "budget_cap_usd": C.BUDGET_USD_CAP,
            "within_cap": total <= C.BUDGET_USD_CAP}
