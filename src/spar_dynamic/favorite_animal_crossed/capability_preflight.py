"""Capability + pricing preflight for FAVORITE_ANIMAL_CROSSED_v1.0."""

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
            issues.append(f"{m.label}: catalog entry missing")
            continue
        sp = set(info["supported_parameters"])
        v = {
            "label": m.label, "slug": m.slug,
            "supports_temperature_live": "temperature" in sp,
            "supports_temperature_config": m.supports_temperature,
            "pricing_prompt_per_mtok": info["pricing"]["prompt"] * 1e6,
            "pricing_completion_per_mtok": info["pricing"]["completion"] * 1e6,
            "preferred_provider": m.preferred_provider,
            "max_tokens": m.max_tokens,
            "reasoning_config_label": m.reasoning_config_label,
        }
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
    return 400 * pp + v["max_tokens"] * cp


def budget_projection(verdict: Dict[str, Any]) -> Dict[str, Any]:
    """Project worst case per PREDICTOR (not per model). Each predictor
    appears in `len(C.MODELS)-1 = 2` cross-pairs; each pair is
    CALLS_PER_PAIR = 20 calls."""
    pairs_per_predictor = len(C.MODELS) - 1
    calls_per_predictor = pairs_per_predictor * C.CALLS_PER_PAIR
    rows = []; total = 0.0
    for m in C.MODELS:
        if m.label not in verdict["per_model"]:
            continue
        per_call = worst_case_per_call_cost(m.label, verdict["per_model"])
        subtotal = per_call * calls_per_predictor
        total += subtotal
        rows.append({"predictor_model": m.label, "config": m.reasoning_config_label,
                      "pairs_as_predictor": pairs_per_predictor,
                      "n_calls": calls_per_predictor,
                      "per_call_usd_worst_case": round(per_call, 6),
                      "subtotal_usd_worst_case": round(subtotal, 4),
                      "max_tokens": m.max_tokens})
    return {"rows": rows,
            "total_usd_worst_case": round(total, 4),
            "budget_cap_usd": C.BUDGET_USD_CAP,
            "within_cap": total <= C.BUDGET_USD_CAP,
            "total_calls_planned": C.TOTAL_CALLS_MAX}
