"""Orchestration for DICE_PILOT_v4.1.

For each model (in EXECUTION_ORDER):
  1. Run Phase 1 (5 calls, no scheduling needed — these are the reference).
  2. Apply usability gate (>=4 of 5 valid).
  3. Interleave Phase 2A (5) + Phase 2B (20) + Phase 2C (5) = 30 calls,
     randomized together under a saved scheduling seed.

Truncation handling (spec §3.2): any call with finish_reason == "length"
is classified `truncated` and NOT retried as content error.

Declines (spec §3.3): once-only, no retry regardless of position/condition.

Resumable: completed `ok` (and terminal non-ok categories like decline,
prefix_leak, truncated) are not re-dispatched.
"""

from __future__ import annotations

import hashlib, json, os, random, time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from openai import OpenAI

from . import config as C
from .parsers import (parse_phase1, parse_phase2, is_truncated,
                       RESPONSE_CATEGORY_TRUNCATED)
from .prompts import (PHASE1_PROMPT, PHASE2A_PROMPT, PHASE2C_PROMPT,
                       phase2b_prompt, PHASE2B_ORDINALS)
from .prefix_detector import find_prefix_run
from .runner import (call_once, CallResult, CostLedger, log_attempt,
                      make_openrouter_client, request_config_hash,
                      worst_case_cost_usd)


# ---------------------------------------------------------------- manifest --

@dataclass(frozen=True)
class ManifestEntryV41:
    trial_id: str                      # phase{1|2a|2b|2c}|<model>|<extra>
    phase: str                         # "phase1" | "phase2a" | "phase2b" | "phase2c"
    model_label: str
    reasoning_config_label: str
    position: Optional[int]            # None for phase1 / 2c; 2 for phase2a; {1,2,5,9} for phase2b
    replicate: int


def build_manifest(scheduling_seed: int = C.SCHEDULING_SEED) -> List[ManifestEntryV41]:
    rng = random.Random(scheduling_seed)
    out: List[ManifestEntryV41] = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        cfg = m.reasoning_config_label
        # Phase 1: run sequentially up front
        for rep in range(C.PHASE1_CALLS_PER_MODEL):
            tid = f"phase1|{model_label}|{cfg}|rep{rep:02d}"
            out.append(ManifestEntryV41(trial_id=tid, phase="phase1",
                                         model_label=model_label,
                                         reasoning_config_label=cfg,
                                         position=None, replicate=rep))
        # Phase 2A/B/C: INTERLEAVE randomly within this model (spec §9).
        p2: List[ManifestEntryV41] = []
        for rep in range(C.PHASE2A_REPLICATES):
            tid = f"phase2a|{model_label}|{cfg}|pos2|rep{rep:02d}"
            p2.append(ManifestEntryV41(tid, "phase2a", model_label, cfg, 2, rep))
        for pos in C.PHASE2B_POSITIONS:
            for rep in range(C.PHASE2B_REPLICATES_PER_POSITION):
                tid = f"phase2b|{model_label}|{cfg}|pos{pos}|rep{rep:02d}"
                p2.append(ManifestEntryV41(tid, "phase2b", model_label, cfg, pos, rep))
        for rep in range(C.PHASE2C_REPLICATES):
            tid = f"phase2c|{model_label}|{cfg}|full|rep{rep:02d}"
            p2.append(ManifestEntryV41(tid, "phase2c", model_label, cfg, None, rep))
        rng.shuffle(p2)
        out.extend(p2)
    return out


# ---------------------------------------------------------------- state --

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


# ---------------------------------------------------------------- request shape --

def reasoning_spec_for(model: C.ModelV41) -> Dict[str, Any]:
    if model.reasoning_enabled_false:
        return {"enabled": False}
    if model.reasoning_effort_requested:
        return {"effort": model.reasoning_effort_requested}
    return {}


def temperature_for(model: C.ModelV41) -> Optional[float]:
    return C.TEMPERATURE_WHEN_SUPPORTED if model.supports_temperature else None


def provider_pin_for(model: C.ModelV41) -> Optional[str]:
    return model.preferred_provider or None


def prompt_for(entry: ManifestEntryV41) -> str:
    if entry.phase == "phase1":  return PHASE1_PROMPT
    if entry.phase == "phase2a": return PHASE2A_PROMPT
    if entry.phase == "phase2b":
        assert entry.position in PHASE2B_ORDINALS
        return phase2b_prompt(entry.position)
    if entry.phase == "phase2c": return PHASE2C_PROMPT
    raise ValueError(f"unknown phase {entry.phase}")


# ---------------------------------------------------------------- one trial --

def run_one_trial(client: OpenAI, entry: ManifestEntryV41,
                   run_dir: str, ledger: CostLedger,
                   pricing: Dict[str, Dict[str, float]], log) -> Dict:
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
            final = {"status": "abandoned", "missing_reason": "budget_cap_prevents_dispatch",
                     "attempts": attempt_i - 1}
            break
        res: CallResult = call_once(client, model.slug, prompt_text,
                                      model.max_tokens, temperature, reasoning_spec,
                                      provider_pin, price)
        ledger.commit(res.cost_usd, reservation)

        truncated = is_truncated(res.finish_reason)
        prefix_run = find_prefix_run(res.reasoning_content if isinstance(res.reasoning_content, str) else "")
        final_prefix_run = find_prefix_run(res.raw_text or "")

        rec = {
            "experiment_name": "dice_pilot_v41",
            "specification_version": "DICE_PILOT_v4.1",
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
            "prefix_run_in_reasoning": None if prefix_run is None else {
                "run_text": prefix_run[0], "digits": prefix_run[1],
                "length": len(prefix_run[1])},
            "prefix_run_in_final": None if final_prefix_run is None else {
                "run_text": final_prefix_run[0], "digits": final_prefix_run[1],
                "length": len(final_prefix_run[1])},
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
            # Spec §3.2: truncated is its own terminal category; do NOT reclassify.
            rec["parse_category"] = RESPONSE_CATEGORY_TRUNCATED
        else:
            # Parse based on phase
            if entry.phase in ("phase1", "phase2c"):
                p1 = parse_phase1(res.raw_text)
                rec["parse_category"] = "valid" if p1.valid else "invalid"
                rec["parsed_values"] = p1.values
                rec["parsed_reason"] = p1.reason
                rec["had_trailing_punct"] = p1.had_trailing_punct
            else:
                # phase2a / phase2b: single-integer
                p2 = parse_phase2(res.raw_text)
                rec["parse_category"] = p2.category
                rec["parsed_value"] = p2.value
                rec["parsed_reason"] = p2.reason
                rec["parsed_extracted_integers"] = p2.extracted_integers

        log_attempt(raw_path, rec=rec)
        attempts_meta.append({
            "attempt_number": attempt_i,
            "parse_category": rec["parse_category"],
            "error": res.error, "cost_usd": res.cost_usd,
            "reasoning_tokens": res.reasoning_tokens,
            "output_tokens": res.completion_tokens,
            "finish_reason": res.finish_reason,
            "truncated": truncated,
        })
        if first_cat is None: first_cat = rec["parse_category"]

        cat = rec["parse_category"]
        if cat == "transport_error":
            if attempt_i >= C.TRANSPORT_RETRY_CAP:
                final = {"status": "abandoned", "missing_reason": "transport_error_exhausted",
                         "attempts": attempt_i}
                break
            time.sleep(min(2 ** attempt_i, 10) + 0.3)
            continue
        if cat == RESPONSE_CATEGORY_TRUNCATED:
            final = {"status": "truncated", "attempts": attempt_i,
                     "output_tokens": res.completion_tokens,
                     "reasoning_tokens": res.reasoning_tokens}
            break

        if entry.phase in ("phase1", "phase2c"):
            if cat == "valid":
                final = {"status": "ok", "parsed_values": rec["parsed_values"],
                         "attempts": attempt_i,
                         "had_trailing_punct": rec["had_trailing_punct"]}
                break
            # Phase 1 / 2C invalid: one content retry
            if content_retries_used < C.CONTENT_RETRY_CAP:
                content_retries_used += 1
                continue
            final = {"status": "invalid",
                     "missing_reason": rec.get("parsed_reason") or "parse_failed",
                     "attempts": attempt_i}
            break
        else:
            # Phase 2A / 2B single-integer
            if cat == "valid":
                final = {"status": "ok", "parsed_value": rec["parsed_value"],
                         "attempts": attempt_i}
                break
            if cat == "decline":
                # Spec §3.3: no retry on decline.
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
        json.dump({
            "scheduling_seed": scheduling_seed,
            "n_entries": len(manifest),
            "entries": [asdict(e) for e in manifest],
            "spec_version": "DICE_PILOT_v4.1",
        }, f, indent=2, sort_keys=True)
    outcomes = load_outcomes(run_dir)
    ledger = load_ledger(run_dir, C.BUDGET_USD_CAP)
    log(f"START v4.1 manifest_size={len(manifest)}  prior_outcomes={len(outcomes)}  "
        f"spent=${ledger.spent_usd:.4f}  cap=${ledger.cap_usd:.2f}")

    skipped: List[str] = []
    for model_label in C.EXECUTION_ORDER:
        m = C.MODELS_BY_LABEL[model_label]
        cfg = m.reasoning_config_label

        # Phase 1 — sequential before interleaved Phase 2
        phase1_entries = [e for e in manifest
                           if e.phase == "phase1" and e.model_label == model_label]
        log(f"=== {model_label}/{cfg} Phase 1 ({len(phase1_entries)} calls, "
            f"max_tokens={m.max_tokens}, provider={m.preferred_provider or '?'}) ===")
        for e in phase1_entries:
            if e.trial_id in outcomes and outcomes[e.trial_id].get("status") == "ok":
                continue
            out = run_one_trial(client, e, run_dir, ledger, pricing, log)
            outcomes[e.trial_id] = out
            save_outcomes(run_dir, outcomes); save_ledger(run_dir, ledger)
            log(f"  {e.trial_id} status={out['status']} cost=${out['total_cost_usd']:.4f}")
            if out["status"] == "abandoned" and out.get("missing_reason") == "budget_cap_prevents_dispatch":
                log("BUDGET STOP"); return {"outcomes": outcomes, "ledger": ledger.to_dict(),
                                              "skipped": skipped, "stopped": "budget_cap"}

        if not phase1_usability_pass(outcomes, model_label, cfg):
            log(f"USABILITY FAIL: {model_label}/{cfg} <4 valid Phase 1. Skipping Phase 2.")
            skipped.append(f"{model_label}/{cfg}:phase2(usability_fail)")
            continue

        # Phase 2 — interleaved across 2A/2B/2C (already shuffled in manifest)
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
            log(f"  {e.trial_id} status={out['status']} "
                f"val={out.get('parsed_value') or (out.get('parsed_values') if out.get('phase') == 'phase2c' else '')} "
                f"cost=${out['total_cost_usd']:.4f}")
            if out["status"] == "abandoned" and out.get("missing_reason") == "budget_cap_prevents_dispatch":
                log("BUDGET STOP"); return {"outcomes": outcomes, "ledger": ledger.to_dict(),
                                              "skipped": skipped, "stopped": "budget_cap"}
    log(f"COMPLETE spent=${ledger.spent_usd:.4f} outcomes={len(outcomes)} skipped={skipped}")
    return {"outcomes": outcomes, "ledger": ledger.to_dict(),
             "skipped": skipped, "stopped": None}
