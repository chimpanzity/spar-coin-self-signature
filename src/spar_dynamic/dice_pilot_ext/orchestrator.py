"""Orchestration for DICE_PILOT_EXT_v1.0.

Phase 1 → usability gate → Phase 2 per model. One fixed reasoning
configuration per model. Resumable: completed valid calls are not repeated.
"""

from __future__ import annotations

import hashlib, json, os, random, time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from openai import OpenAI

from . import config as C
from .prompts import PHASE1_PROMPT, phase2_prompt
from .parsers import parse_phase1, parse_phase2

# Re-use the v3.1 runner primitives verbatim (same ledger, cost model, retry).
from spar_dynamic.dice_pilot.runner import (
    CallResult, CostLedger, call_once, log_attempt,
    make_openrouter_client, request_config_hash,
    worst_case_cost_usd, _prefix_tokens_in_text,
)


# ---------------------------------------------------------------- manifest --

@dataclass(frozen=True)
class ExtManifestEntry:
    trial_id: str
    phase: str                         # "phase1" | "phase2"
    model_label: str
    reasoning_config_label: str        # e.g. "R_low" or "R_min"
    position: Optional[int]
    replicate: int


def build_manifest(scheduling_seed: int = C.SCHEDULING_SEED) -> List[ExtManifestEntry]:
    rng = random.Random(scheduling_seed)
    out: List[ExtManifestEntry] = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        cfg = m.reasoning_config_label
        for rep in range(C.PHASE1_CALLS_PER_MODEL):
            tid = f"phase1|{model_label}|{cfg}|rep{rep:02d}"
            out.append(ExtManifestEntry(trial_id=tid, phase="phase1",
                                         model_label=model_label,
                                         reasoning_config_label=cfg,
                                         position=None, replicate=rep))
        p2 = [(pos, rep) for pos in C.PHASE2_POSITIONS
              for rep in range(C.PHASE2_REPLICATES_PER_POSITION)]
        rng.shuffle(p2)
        for (pos, rep) in p2:
            tid = f"phase2|{model_label}|{cfg}|pos{pos}|rep{rep:02d}"
            out.append(ExtManifestEntry(trial_id=tid, phase="phase2",
                                         model_label=model_label,
                                         reasoning_config_label=cfg,
                                         position=pos, replicate=rep))
    return out


# ---------------------------------------------------------------- state helpers --

def _utc(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
def _outcomes_path(run_dir): return os.path.join(run_dir, "trial_outcomes.json")
def _ledger_path(run_dir): return os.path.join(run_dir, "cost_ledger.json")

def _read_json(path, default):
    if not os.path.exists(path): return default
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def _write_json_atomic(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f, indent=2, sort_keys=True)
    os.replace(tmp, path)

def load_outcomes(run_dir): return _read_json(_outcomes_path(run_dir), {})
def save_outcomes(run_dir, outcomes): _write_json_atomic(_outcomes_path(run_dir), outcomes)
def load_ledger(run_dir, cap):
    d = _read_json(_ledger_path(run_dir), None)
    if d is None: return CostLedger(cap_usd=cap)
    return CostLedger(cap_usd=cap, spent_usd=float(d.get("spent_usd", 0.0)))
def save_ledger(run_dir, L): _write_json_atomic(_ledger_path(run_dir), L.to_dict())


# ---------------------------------------------------------------- per-model request shape --

def reasoning_spec_for(model: C.ExtModel) -> Dict[str, Any]:
    """Build the extra_body.reasoning dict for an extension model.

    If the paid preflight established that the model accepts a genuine
    reasoning-off switch (`supports_reasoning_disable=True`), use
    {'enabled': False}. Otherwise use the frozen `reasoning_effort_requested`.
    """
    if model.supports_reasoning_disable is True:
        return {"enabled": False}
    return {"effort": model.reasoning_effort_requested}


def temperature_for(model: C.ExtModel) -> Optional[float]:
    return C.TEMPERATURE_WHEN_SUPPORTED if model.supports_temperature else None


def provider_pin_for(model: C.ExtModel) -> Optional[str]:
    return model.preferred_provider or None


# ---------------------------------------------------------------- one trial --

def run_one_trial(client: OpenAI, entry: ExtManifestEntry,
                   run_dir: str, ledger: CostLedger,
                   pricing: Dict[str, Dict[str, float]], log) -> Dict:
    raw_path = os.path.join(run_dir, "raw_attempts.jsonl")
    model = C.MODELS_BY_LABEL[entry.model_label]
    temperature = temperature_for(model)
    reasoning_spec = reasoning_spec_for(model)
    provider_pin = provider_pin_for(model)
    req_hash = request_config_hash(model.slug, provider_pin, C.MAX_TOKENS,
                                    temperature, reasoning_spec)

    if entry.phase == "phase1":
        prompt_text = PHASE1_PROMPT
    else:
        prompt_text = phase2_prompt(entry.position)
    phash = hashlib.sha256(prompt_text.encode()).hexdigest()
    price = pricing[model.slug]

    attempts_meta: List[Dict] = []
    first_response_category: Optional[str] = None
    final: Optional[Dict] = None
    content_retries_used = 0
    attempt_i = 0
    while True:
        attempt_i += 1
        reservation = worst_case_cost_usd(prompt_text, C.MAX_TOKENS,
                                           price["prompt"], price["completion"])
        if not ledger.reserve(reservation):
            final = {"status": "abandoned", "missing_reason": "budget_cap_prevents_dispatch",
                     "attempts": attempt_i - 1}
            break
        res: CallResult = call_once(client, model.slug, prompt_text,
                                      C.MAX_TOKENS, temperature, reasoning_spec,
                                      provider_pin, price)
        ledger.commit(res.cost_usd, reservation)

        rec = {
            "experiment_name": C.__name__.split(".")[-2] if False else "dice_pilot_ext",
            "specification_version": "DICE_PILOT_EXT_v1.0",
            "trial_id": entry.trial_id,
            "phase": entry.phase,
            "model_label": entry.model_label,
            "reasoning_config": entry.reasoning_config_label,
            "position": entry.position,
            "replicate": entry.replicate,
            "attempt_number": attempt_i,
            "prompt_hash": phash,
            "prompt_text": prompt_text,
            "requested_model_id": model.slug,
            "requested_provider": provider_pin or "",
            "requested_temperature": temperature,
            "temperature_effective": res.temperature_effective,
            "requested_reasoning": reasoning_spec,
            "returned_model_id": res.served_model,
            "provider": res.provider,
            "generation_id": res.generation_id,
            "finish_reason": res.finish_reason,
            "raw_text": res.raw_text,
            "reasoning_content_classification": res.reasoning_content_classification,
            "reasoning_content": res.reasoning_content if isinstance(res.reasoning_content, str) else None,
            "prefix_tokens_in_final": _prefix_tokens_in_text(res.raw_text),
            "prefix_tokens_in_reasoning": (
                _prefix_tokens_in_text(res.reasoning_content)
                if isinstance(res.reasoning_content, str) else None),
            "error": res.error,
            "input_tokens": res.prompt_tokens,
            "output_tokens": res.completion_tokens,
            "reasoning_tokens": res.reasoning_tokens,
            "latency_ms": res.latency_ms,
            "cost_usd": res.cost_usd,
            "judge_request_config_hash": req_hash,
            "timestamp": _utc(),
        }
        if res.error:
            rec["parse_category"] = "transport_error"
        else:
            if entry.phase == "phase1":
                p1 = parse_phase1(res.raw_text)
                rec["parse_category"] = "valid" if p1.valid else "invalid"
                rec["parsed_values"] = p1.values
                rec["parsed_reason"] = p1.reason
                rec["had_trailing_punct"] = p1.had_trailing_punct
            else:
                p2 = parse_phase2(res.raw_text)
                rec["parse_category"] = p2.category
                rec["parsed_value"] = p2.value
                rec["parsed_reason"] = p2.reason
                rec["parsed_extracted_integers"] = p2.extracted_integers

        log_attempt(raw_path, rec=rec)
        attempts_meta.append({
            "attempt_number": attempt_i, "parse_category": rec["parse_category"],
            "error": res.error, "cost_usd": res.cost_usd,
            "reasoning_tokens": res.reasoning_tokens,
            "output_tokens": res.completion_tokens,
            "finish_reason": res.finish_reason,
        })
        if first_response_category is None:
            first_response_category = rec["parse_category"]

        cat = rec["parse_category"]
        if cat == "transport_error":
            if attempt_i >= C.TRANSPORT_RETRY_CAP:
                final = {"status": "abandoned", "missing_reason": "transport_error_exhausted",
                         "attempts": attempt_i}
                break
            time.sleep(min(2 ** attempt_i, 10) + 0.3)
            continue

        if entry.phase == "phase1":
            if cat == "valid":
                final = {"status": "ok", "parsed_values": rec["parsed_values"],
                         "attempts": attempt_i,
                         "had_trailing_punct": rec["had_trailing_punct"]}
                break
            if content_retries_used < C.CONTENT_RETRY_CAP:
                content_retries_used += 1
                continue
            final = {"status": "invalid",
                     "missing_reason": rec.get("parsed_reason") or "parse_failed",
                     "attempts": attempt_i}
            break
        else:
            if cat == "valid":
                final = {"status": "ok", "parsed_value": rec["parsed_value"],
                         "attempts": attempt_i}
                break
            if cat == "decline":
                final = {"status": "decline", "attempts": attempt_i}
                break
            if cat == "prefix_leak":
                final = {"status": "prefix_leak",
                         "extracted_integers": rec["parsed_extracted_integers"],
                         "attempts": attempt_i}
                break
            if content_retries_used < C.CONTENT_RETRY_CAP:
                content_retries_used += 1
                continue
            final = {"status": "invalid",
                     "missing_reason": rec.get("parsed_reason") or "parse_failed",
                     "attempts": attempt_i}
            break

    return {
        "trial_id": entry.trial_id, "model": entry.model_label,
        "reasoning_config": entry.reasoning_config_label,
        "phase": entry.phase, "position": entry.position, "replicate": entry.replicate,
        "first_response_category": first_response_category,
        "attempts_meta": attempts_meta,
        "total_cost_usd": round(sum(a["cost_usd"] for a in attempts_meta), 6),
        **(final or {}),
    }


# ---------------------------------------------------------------- usability --

def phase1_usability_pass(outcomes: Dict[str, Dict], model: str, cfg: str) -> bool:
    n_valid = sum(1 for tid, o in outcomes.items()
                   if tid.startswith(f"phase1|{model}|{cfg}|")
                   and o.get("status") == "ok")
    return n_valid >= C.PHASE1_USABILITY_THRESHOLD


# ---------------------------------------------------------------- top-level --

def run(client: OpenAI, run_dir: str, pricing: Dict[str, Dict[str, float]],
        log, scheduling_seed: int = C.SCHEDULING_SEED,
        skip_phase2_if_usability_fails: bool = True) -> Dict:
    manifest = build_manifest(scheduling_seed)
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, "experiment_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({
            "scheduling_seed": scheduling_seed,
            "n_entries": len(manifest),
            "entries": [asdict(e) for e in manifest],
            "spec_version": "DICE_PILOT_EXT_v1.0",
        }, f, indent=2, sort_keys=True)
    outcomes = load_outcomes(run_dir)
    ledger = load_ledger(run_dir, C.BUDGET_USD_CAP)
    log(f"START manifest_size={len(manifest)}  prior_outcomes={len(outcomes)}  "
        f"spent=${ledger.spent_usd:.4f}  cap=${ledger.cap_usd:.2f}")

    skipped_configs: List[str] = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        cfg = m.reasoning_config_label
        phase1_entries = [e for e in manifest
                           if e.phase == "phase1" and e.model_label == model_label]
        log(f"=== {model_label}/{cfg} Phase 1 ({len(phase1_entries)} calls) ===")
        for e in phase1_entries:
            if e.trial_id in outcomes and outcomes[e.trial_id].get("status") == "ok":
                continue
            out = run_one_trial(client, e, run_dir, ledger, pricing, log)
            outcomes[e.trial_id] = out
            save_outcomes(run_dir, outcomes); save_ledger(run_dir, ledger)
            log(f"  {e.trial_id} status={out['status']} cost=${out['total_cost_usd']:.4f}")
            if out["status"] == "abandoned" and out.get("missing_reason") == "budget_cap_prevents_dispatch":
                log("BUDGET STOP"); return {"outcomes": outcomes, "ledger": ledger.to_dict(),
                                              "skipped": skipped_configs, "stopped": "budget_cap"}

        if not phase1_usability_pass(outcomes, model_label, cfg):
            log(f"USABILITY FAIL: {model_label}/{cfg} <4 valid Phase 1. Skipping Phase 2.")
            skipped_configs.append(f"{model_label}/{cfg}:phase2(usability_fail)")
            if skip_phase2_if_usability_fails:
                continue

        phase2_entries = [e for e in manifest
                           if e.phase == "phase2" and e.model_label == model_label]
        log(f"=== {model_label}/{cfg} Phase 2 ({len(phase2_entries)} calls) ===")
        for e in phase2_entries:
            if e.trial_id in outcomes and outcomes[e.trial_id].get("status") in ("ok", "decline", "prefix_leak"):
                continue
            out = run_one_trial(client, e, run_dir, ledger, pricing, log)
            outcomes[e.trial_id] = out
            save_outcomes(run_dir, outcomes); save_ledger(run_dir, ledger)
            log(f"  {e.trial_id} status={out['status']} val={out.get('parsed_value')} cost=${out['total_cost_usd']:.4f}")
            if out["status"] == "abandoned" and out.get("missing_reason") == "budget_cap_prevents_dispatch":
                log("BUDGET STOP"); return {"outcomes": outcomes, "ledger": ledger.to_dict(),
                                              "skipped": skipped_configs, "stopped": "budget_cap"}
    log(f"COMPLETE spent=${ledger.spent_usd:.4f}  outcomes={len(outcomes)}  skipped={skipped_configs}")
    return {"outcomes": outcomes, "ledger": ledger.to_dict(),
             "skipped": skipped_configs, "stopped": None}
