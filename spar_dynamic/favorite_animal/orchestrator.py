"""Orchestration for FAVORITE_ANIMAL_v1.0.

Per spec §11: for each model (Astra → Fable → OSS-120):
  1. Phase 1 (5 sequential calls).
  2. Usability gate (>=4 of 5 valid).
  3. Interleaved Phase 2A (20) + Phase 2B (5) under scheduling seed.
"""

from __future__ import annotations

import hashlib, json, os, random, time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from openai import OpenAI

from . import config as C
from .parsers import (parse_animal, parse_phase2a, is_truncated,
                       RESPONSE_CATEGORY_TRUNCATED)
from .prompts import (PHASE1_PROMPT, PHASE2B_PROMPT, phase2a_prompt,
                       PHASE2A_POSITIONS)
from .candidate_detector import classify as classify_reasoning
from spar_dynamic.dice_pilot.runner import (
    CallResult, CostLedger, call_once, log_attempt,
    make_openrouter_client, request_config_hash, worst_case_cost_usd,
)


@dataclass(frozen=True)
class AnimalManifestEntry:
    trial_id: str
    phase: str                         # "phase1" | "phase2a" | "phase2b"
    model_label: str
    reasoning_config_label: str
    position: Optional[str]            # "first"/"second"/"penultimate"/"last" for 2A
    replicate: int


def build_manifest(scheduling_seed: int = C.SCHEDULING_SEED) -> List[AnimalManifestEntry]:
    rng = random.Random(scheduling_seed)
    out: List[AnimalManifestEntry] = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        cfg = m.reasoning_config_label
        for rep in range(C.PHASE1_CALLS_PER_MODEL):
            out.append(AnimalManifestEntry(
                trial_id=f"phase1|{model_label}|{cfg}|rep{rep:02d}",
                phase="phase1", model_label=model_label,
                reasoning_config_label=cfg, position=None, replicate=rep))
        p2: List[AnimalManifestEntry] = []
        for pos in C.PHASE2A_POSITIONS:
            for rep in range(C.PHASE2A_REPLICATES_PER_POSITION):
                p2.append(AnimalManifestEntry(
                    trial_id=f"phase2a|{model_label}|{cfg}|pos{pos}|rep{rep:02d}",
                    phase="phase2a", model_label=model_label,
                    reasoning_config_label=cfg, position=pos, replicate=rep))
        for rep in range(C.PHASE2B_REPLICATES):
            p2.append(AnimalManifestEntry(
                trial_id=f"phase2b|{model_label}|{cfg}|full|rep{rep:02d}",
                phase="phase2b", model_label=model_label,
                reasoning_config_label=cfg, position=None, replicate=rep))
        rng.shuffle(p2)
        out.extend(p2)
    return out


# ---------------------------------------------------------------- state --

def _utc(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
def _outcomes_path(d): return os.path.join(d, "trial_outcomes.json")
def _ledger_path(d): return os.path.join(d, "cost_ledger.json")

def _read_json(path, default):
    if not os.path.exists(path): return default
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def _write_json_atomic(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f, indent=2, sort_keys=True)
    os.replace(tmp, path)

def load_outcomes(d): return _read_json(_outcomes_path(d), {})
def save_outcomes(d, o): _write_json_atomic(_outcomes_path(d), o)
def load_ledger(d, cap):
    data = _read_json(_ledger_path(d), None)
    if data is None: return CostLedger(cap_usd=cap)
    return CostLedger(cap_usd=cap, spent_usd=float(data.get("spent_usd", 0.0)))
def save_ledger(d, L): _write_json_atomic(_ledger_path(d), L.to_dict())


# ---------------------------------------------------------------- helpers --

def reasoning_spec_for(model: C.FavoriteAnimalModel) -> Dict[str, Any]:
    if model.reasoning_enabled_false: return {"enabled": False}
    if model.reasoning_effort_requested: return {"effort": model.reasoning_effort_requested}
    return {}


def temperature_for(model: C.FavoriteAnimalModel) -> Optional[float]:
    return C.TEMPERATURE_WHEN_SUPPORTED if model.supports_temperature else None


def provider_pin_for(model: C.FavoriteAnimalModel) -> Optional[str]:
    return model.preferred_provider or None


def prompt_for(entry: AnimalManifestEntry) -> str:
    if entry.phase == "phase1":  return PHASE1_PROMPT
    if entry.phase == "phase2a":
        assert entry.position in PHASE2A_POSITIONS
        return phase2a_prompt(entry.position)
    if entry.phase == "phase2b": return PHASE2B_PROMPT
    raise ValueError(f"unknown phase {entry.phase}")


# ---------------------------------------------------------------- one trial --

def run_one_trial(client: OpenAI, entry: AnimalManifestEntry, run_dir: str,
                   ledger: CostLedger, pricing: Dict[str, Dict[str, float]], log) -> Dict:
    raw_path = os.path.join(run_dir, "raw_attempts.jsonl")
    model = C.MODELS_BY_LABEL[entry.model_label]
    temperature = temperature_for(model)
    reasoning_spec = reasoning_spec_for(model)
    provider_pin = provider_pin_for(model)
    req_hash = request_config_hash(model.slug, provider_pin, model.max_tokens,
                                    temperature, reasoning_spec)
    prompt_text = prompt_for(entry)
    phash = hashlib.sha256(prompt_text.encode()).hexdigest()
    price = pricing[model.slug]

    attempts_meta: List[Dict] = []
    first_cat: Optional[str] = None
    final: Optional[Dict] = None
    content_retries_used = 0
    attempt_i = 0

    while True:
        attempt_i += 1
        reservation = worst_case_cost_usd(prompt_text, model.max_tokens,
                                           price["prompt"], price["completion"])
        if not ledger.reserve(reservation):
            final = {"status": "abandoned",
                     "missing_reason": "budget_cap_prevents_dispatch",
                     "attempts": attempt_i - 1}
            break
        res: CallResult = call_once(client, model.slug, prompt_text,
                                      model.max_tokens, temperature, reasoning_spec,
                                      provider_pin, price)
        ledger.commit(res.cost_usd, reservation)

        truncated = is_truncated(res.finish_reason)

        rec = {
            "experiment_name": "favorite_animal",
            "specification_version": "FAVORITE_ANIMAL_v1.0",
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
            "requested_max_tokens": model.max_tokens,
            "returned_model_id": res.served_model,
            "provider": res.provider,
            "generation_id": res.generation_id,
            "finish_reason": res.finish_reason,
            "truncated": truncated,
            "raw_text": res.raw_text,
            "reasoning_content_classification": res.reasoning_content_classification,
            "reasoning_content": res.reasoning_content if isinstance(res.reasoning_content, str) else None,
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
        elif truncated:
            rec["parse_category"] = RESPONSE_CATEGORY_TRUNCATED
        else:
            if entry.phase in ("phase1", "phase2b"):
                p = parse_animal(res.raw_text)
                rec["parse_category"] = "valid" if p.valid else "invalid"
                rec["parsed_normalized_name"] = p.normalized_name
                rec["parsed_scoring_string"] = p.scoring_string
                rec["parsed_reason"] = p.reason
                rec["had_trailing_punct"] = p.had_trailing_punct
            else:
                p = parse_phase2a(res.raw_text)
                rec["parse_category"] = p.category
                rec["parsed_letter"] = p.letter
                rec["parsed_reason"] = p.reason
                rec["parsed_extracted_letters"] = p.extracted_letters

        log_attempt(raw_path, rec=rec)
        attempts_meta.append({
            "attempt_number": attempt_i, "parse_category": rec["parse_category"],
            "error": res.error, "cost_usd": res.cost_usd,
            "reasoning_tokens": res.reasoning_tokens,
            "output_tokens": res.completion_tokens,
            "finish_reason": res.finish_reason, "truncated": truncated,
        })
        if first_cat is None: first_cat = rec["parse_category"]

        cat = rec["parse_category"]
        if cat == "transport_error":
            if attempt_i >= C.TRANSPORT_RETRY_CAP:
                final = {"status": "abandoned",
                         "missing_reason": "transport_error_exhausted",
                         "attempts": attempt_i}
                break
            time.sleep(min(2 ** attempt_i, 10) + 0.3)
            continue
        if cat == RESPONSE_CATEGORY_TRUNCATED:
            final = {"status": "truncated", "attempts": attempt_i,
                     "output_tokens": res.completion_tokens,
                     "reasoning_tokens": res.reasoning_tokens}
            break

        if entry.phase in ("phase1", "phase2b"):
            if cat == "valid":
                final = {"status": "ok",
                         "parsed_normalized_name": rec["parsed_normalized_name"],
                         "parsed_scoring_string": rec["parsed_scoring_string"],
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
                final = {"status": "ok", "parsed_letter": rec["parsed_letter"],
                         "attempts": attempt_i}
                break
            if cat == "decline":
                final = {"status": "decline", "attempts": attempt_i}
                break
            if cat == "prefix_leak":
                final = {"status": "prefix_leak",
                         "extracted_letters": rec["parsed_extracted_letters"],
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
        "phase": entry.phase, "position": entry.position,
        "replicate": entry.replicate,
        "first_response_category": first_cat,
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

TERMINAL_SKIP_STATES = ("ok", "decline", "prefix_leak", "truncated")


def run(client: OpenAI, run_dir: str, pricing: Dict[str, Dict[str, float]],
        log, scheduling_seed: int = C.SCHEDULING_SEED) -> Dict:
    manifest = build_manifest(scheduling_seed)
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, "experiment_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"scheduling_seed": scheduling_seed,
                    "n_entries": len(manifest),
                    "entries": [asdict(e) for e in manifest],
                    "spec_version": "FAVORITE_ANIMAL_v1.0"},
                   f, indent=2, sort_keys=True)
    outcomes = load_outcomes(run_dir)
    ledger = load_ledger(run_dir, C.BUDGET_USD_CAP)
    log(f"START favorite_animal manifest_size={len(manifest)}  "
        f"prior_outcomes={len(outcomes)}  spent=${ledger.spent_usd:.4f}  "
        f"cap=${ledger.cap_usd:.2f}")

    skipped: List[str] = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        cfg = m.reasoning_config_label
        phase1_entries = [e for e in manifest
                           if e.phase == "phase1" and e.model_label == model_label]
        log(f"=== {model_label}/{cfg} Phase 1 ({len(phase1_entries)} calls, "
            f"max_tokens={m.max_tokens}, provider={m.preferred_provider}) ===")
        for e in phase1_entries:
            if e.trial_id in outcomes and outcomes[e.trial_id].get("status") == "ok":
                continue
            out = run_one_trial(client, e, run_dir, ledger, pricing, log)
            outcomes[e.trial_id] = out
            save_outcomes(run_dir, outcomes); save_ledger(run_dir, ledger)
            log(f"  {e.trial_id} status={out['status']} cost=${out['total_cost_usd']:.4f}")
            if out["status"] == "abandoned" and out.get("missing_reason") == "budget_cap_prevents_dispatch":
                log("BUDGET STOP")
                return {"outcomes": outcomes, "ledger": ledger.to_dict(),
                         "skipped": skipped, "stopped": "budget_cap"}

        if not phase1_usability_pass(outcomes, model_label, cfg):
            log(f"USABILITY FAIL: {model_label}/{cfg} <4 valid Phase 1. Skipping Phase 2.")
            skipped.append(f"{model_label}/{cfg}:phase2(usability_fail)")
            continue

        phase2_entries = [e for e in manifest
                           if e.phase.startswith("phase2") and e.model_label == model_label]
        log(f"=== {model_label}/{cfg} Phase 2 interleaved ({len(phase2_entries)} calls) ===")
        for e in phase2_entries:
            prev = outcomes.get(e.trial_id)
            if prev is not None and prev.get("status") in TERMINAL_SKIP_STATES:
                continue
            out = run_one_trial(client, e, run_dir, ledger, pricing, log)
            outcomes[e.trial_id] = out
            save_outcomes(run_dir, outcomes); save_ledger(run_dir, ledger)
            val_disp = out.get("parsed_letter") if e.phase == "phase2a" else out.get("parsed_normalized_name")
            log(f"  {e.trial_id} status={out['status']} val={val_disp!r} cost=${out['total_cost_usd']:.4f}")
            if out["status"] == "abandoned" and out.get("missing_reason") == "budget_cap_prevents_dispatch":
                log("BUDGET STOP")
                return {"outcomes": outcomes, "ledger": ledger.to_dict(),
                         "skipped": skipped, "stopped": "budget_cap"}
    log(f"COMPLETE spent=${ledger.spent_usd:.4f} outcomes={len(outcomes)} skipped={skipped}")
    return {"outcomes": outcomes, "ledger": ledger.to_dict(),
             "skipped": skipped, "stopped": None}
