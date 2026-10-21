"""Pilot 5 — SPAR Stimulus Corpus: three production architectures.

For each of {astra, fable, mistral} × {batch, history_conditioned, independent_calls}
generate exactly 10 trajectories of exactly 100 H/T outcomes.

No judgments. No self-recognition. Pure stimulus generation.

The scientific comparison is between three ways the same nominal fair-coin task
can be produced:
  1. batch: one API call produces the entire 100-flip sequence via within-completion autoregression
  2. history_conditioned: 100 sequential API calls; each call receives the complete prior history
  3. independent_calls: 100 sequential API calls; every call receives the SAME fixed prompt with no history
"""

import json, os, time, uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from . import config as C
from .api import (APIResult, CostAccountant, call_model,
                  parse_batch, parse_online)
from .state import append_jsonl, read_json, read_jsonl, write_json


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

@dataclass
class CorpusTrajectory:
    trajectory_id: str
    run_id: str
    model_label: str
    requested_model_id: str
    method: str                      # "batch" | "history_conditioned" | "independent_calls"
    replicate_index: int
    parsed_sequence: str
    valid: bool
    status: str                      # "ok" | "failed"
    invalid_reason: str
    n_calls: int
    total_cost_usd: float
    started_utc: str
    finished_utc: str


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Attempt logging — resume-safe append-only JSONL per trajectory
# ---------------------------------------------------------------------------

def _log_attempt(jsonl_path: str, *, run_id: str, trajectory_id: str,
                 model_label: str, requested_model_id: str,
                 method: str, trial_index: Optional[int], attempt_index: int,
                 prompt_text: str, history_before: Optional[str],
                 raw_response: str, parsed_flip: Optional[str], valid: bool,
                 error_type: str, kind: str,
                 res: APIResult):
    rec = {
        "run_id": run_id,
        "trajectory_id": trajectory_id,
        "source_model": model_label,
        "requested_model_id": requested_model_id,
        "returned_model_id": res.served_model,
        "provider": res.provider,
        "method": method,
        "trial_index": trial_index,
        "attempt_index": attempt_index,
        "prompt_text": prompt_text,
        "history_before": history_before,
        "raw_response": raw_response,
        "parsed_flip": parsed_flip,
        "valid": valid,
        "error_type": error_type,
        "usage": {
            "prompt_tokens": res.prompt_tokens,
            "completion_tokens": res.completion_tokens,
            "reasoning_tokens": res.reasoning_tokens,
            "total_tokens": res.total_tokens,
        },
        "cost_usd": res.cost_usd,
        "kind": kind,
        "timestamp": res.call_utc,
        "request_id": res.request_id,
        "generation_id": res.generation_id,
        "latency_ms": res.latency_ms,
    }
    append_jsonl(jsonl_path, rec)


# ---------------------------------------------------------------------------
# 1. BATCH generation
# ---------------------------------------------------------------------------

def generate_batch_trajectory(client: OpenAI, accountant: CostAccountant,
                              *, run_id: str, trajectory_id: str,
                              model: C.ModelSpec, replicate_index: int,
                              raw_jsonl_path: str,
                              log=print) -> CorpusTrajectory:
    """One API call generates the whole 100-flip sequence. Up to CORPUS_BATCH_MAX_ATTEMPTS
    total attempts; each attempt is logged, none are silently discarded."""
    started_utc = _utc_now()
    max_tokens = C.corpus_max_tokens_batch(model.label)
    temp = C.temperature_for(model.label, "batch")  # honors any overrides
    parsed = None
    total_cost = 0.0
    last_res = None
    for attempt in range(1, C.CORPUS_BATCH_MAX_ATTEMPTS + 1):
        res = call_model(client, accountant,
                         kind="corpus_batch", slug=model.slug,
                         prompt_text=C.CORPUS_BATCH_PROMPT,
                         max_tokens=max_tokens, temperature=temp)
        total_cost += res.cost_usd
        last_res = res
        parsed_seq = parse_batch(res.response_text, length=C.CORPUS_SEQUENCE_LENGTH)
        err = "" if parsed_seq is not None else \
              (f"parse_fail_len={len(''.join(res.response_text.split()))}"
               if res.error_message == "" else f"api:{res.error_message[:60]}")
        _log_attempt(raw_jsonl_path,
                     run_id=run_id, trajectory_id=trajectory_id,
                     model_label=model.label, requested_model_id=model.slug,
                     method="batch", trial_index=None, attempt_index=attempt,
                     prompt_text=C.CORPUS_BATCH_PROMPT, history_before=None,
                     raw_response=res.response_text,
                     parsed_flip=None,
                     valid=(parsed_seq is not None),
                     error_type=err, kind="corpus_batch", res=res)
        if parsed_seq is not None:
            parsed = parsed_seq
            break
    finished_utc = _utc_now()
    ok = parsed is not None
    return CorpusTrajectory(
        trajectory_id=trajectory_id, run_id=run_id,
        model_label=model.label, requested_model_id=model.slug,
        method="batch", replicate_index=replicate_index,
        parsed_sequence=parsed if ok else "",
        valid=ok, status="ok" if ok else "failed",
        invalid_reason="" if ok else f"parse_fail after {C.CORPUS_BATCH_MAX_ATTEMPTS} attempts",
        n_calls=(last_res is not None and 1 or 0),
        total_cost_usd=total_cost,
        started_utc=started_utc, finished_utc=finished_utc,
    )


# ---------------------------------------------------------------------------
# 2. HISTORY-CONDITIONED generation
# ---------------------------------------------------------------------------

def generate_history_conditioned_trajectory(client: OpenAI, accountant: CostAccountant,
                                            *, run_id: str, trajectory_id: str,
                                            model: C.ModelSpec, replicate_index: int,
                                            raw_jsonl_path: str,
                                            resume_history: str = "",
                                            log=print) -> CorpusTrajectory:
    """100 sequential API calls; each receives the complete prior history."""
    started_utc = _utc_now()
    max_tokens = C.corpus_max_tokens_step(model.label)
    history = resume_history
    n_calls = 0
    total_cost = 0.0
    invalid_at = None
    for step in range(len(history) + 1, C.CORPUS_SEQUENCE_LENGTH + 1):
        prompt = C.corpus_history_trial_prompt(history)
        parsed_this_step = None
        for attempt in range(1, C.CORPUS_STEP_MAX_ATTEMPTS + 1):
            res = call_model(client, accountant,
                             kind="corpus_history_conditioned", slug=model.slug,
                             prompt_text=prompt, max_tokens=max_tokens)
            total_cost += res.cost_usd
            n_calls += 1
            p = parse_online(res.response_text)
            err = "" if p is not None else (
                "parse_fail" if not res.error_message else f"api:{res.error_message[:60]}")
            _log_attempt(raw_jsonl_path,
                         run_id=run_id, trajectory_id=trajectory_id,
                         model_label=model.label, requested_model_id=model.slug,
                         method="history_conditioned",
                         trial_index=step, attempt_index=attempt,
                         prompt_text=prompt, history_before=history,
                         raw_response=res.response_text,
                         parsed_flip=p, valid=(p is not None),
                         error_type=err, kind="corpus_history_conditioned", res=res)
            if p is not None:
                parsed_this_step = p
                break
        if parsed_this_step is None:
            invalid_at = step
            break
        history += parsed_this_step
    finished_utc = _utc_now()
    ok = (invalid_at is None) and (len(history) == C.CORPUS_SEQUENCE_LENGTH)
    return CorpusTrajectory(
        trajectory_id=trajectory_id, run_id=run_id,
        model_label=model.label, requested_model_id=model.slug,
        method="history_conditioned", replicate_index=replicate_index,
        parsed_sequence=history if ok else "",
        valid=ok, status="ok" if ok else "failed",
        invalid_reason="" if ok else f"abandoned at step {invalid_at}",
        n_calls=n_calls, total_cost_usd=total_cost,
        started_utc=started_utc, finished_utc=finished_utc,
    )


# ---------------------------------------------------------------------------
# 3. INDEPENDENT-CALLS generation
# ---------------------------------------------------------------------------

def generate_independent_calls_trajectory(client: OpenAI, accountant: CostAccountant,
                                          *, run_id: str, trajectory_id: str,
                                          model: C.ModelSpec, replicate_index: int,
                                          raw_jsonl_path: str,
                                          resume_history: str = "",
                                          log=print) -> CorpusTrajectory:
    """100 sequential API calls; every call receives the SAME fixed prompt with NO history.
    (Sequential per spec section 34, not concurrent, so the trajectory has a well-defined order.)"""
    started_utc = _utc_now()
    max_tokens = C.corpus_max_tokens_step(model.label)
    sequence = resume_history  # already-valid flips
    n_calls = 0
    total_cost = 0.0
    invalid_at = None
    prompt = C.CORPUS_INDEPENDENT_CALLS_PROMPT   # SAME every trial
    for step in range(len(sequence) + 1, C.CORPUS_SEQUENCE_LENGTH + 1):
        parsed_this_step = None
        for attempt in range(1, C.CORPUS_STEP_MAX_ATTEMPTS + 1):
            res = call_model(client, accountant,
                             kind="corpus_independent_calls", slug=model.slug,
                             prompt_text=prompt, max_tokens=max_tokens)
            total_cost += res.cost_usd
            n_calls += 1
            p = parse_online(res.response_text)
            err = "" if p is not None else (
                "parse_fail" if not res.error_message else f"api:{res.error_message[:60]}")
            _log_attempt(raw_jsonl_path,
                         run_id=run_id, trajectory_id=trajectory_id,
                         model_label=model.label, requested_model_id=model.slug,
                         method="independent_calls",
                         trial_index=step, attempt_index=attempt,
                         prompt_text=prompt, history_before=None,
                         raw_response=res.response_text,
                         parsed_flip=p, valid=(p is not None),
                         error_type=err, kind="corpus_independent_calls", res=res)
            if p is not None:
                parsed_this_step = p
                break
        if parsed_this_step is None:
            invalid_at = step
            break
        sequence += parsed_this_step
    finished_utc = _utc_now()
    ok = (invalid_at is None) and (len(sequence) == C.CORPUS_SEQUENCE_LENGTH)
    return CorpusTrajectory(
        trajectory_id=trajectory_id, run_id=run_id,
        model_label=model.label, requested_model_id=model.slug,
        method="independent_calls", replicate_index=replicate_index,
        parsed_sequence=sequence if ok else "",
        valid=ok, status="ok" if ok else "failed",
        invalid_reason="" if ok else f"abandoned at step {invalid_at}",
        n_calls=n_calls, total_cost_usd=total_cost,
        started_utc=started_utc, finished_utc=finished_utc,
    )


# ---------------------------------------------------------------------------
# Resume: rebuild in-progress trajectory from raw_attempts.jsonl
# ---------------------------------------------------------------------------

def rebuild_trajectory_state_from_attempts(raw_jsonl_path: str,
                                            trajectory_id: str) -> str:
    """For history_conditioned / independent_calls: reconstruct the accumulated
    sequence from the persisted attempts, so a restart can pick up mid-trajectory.
    Returns the accumulated H/T string (each step contributes at most one char)."""
    if not os.path.exists(raw_jsonl_path):
        return ""
    step_flip: Dict[int, str] = {}
    with open(raw_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("trajectory_id") != trajectory_id:
                continue
            if not rec.get("valid"):
                continue
            step = rec.get("trial_index")
            p = rec.get("parsed_flip")
            if isinstance(step, int) and p in ("H", "T") and step not in step_flip:
                step_flip[step] = p
    # sequence is step_flip[1] + step_flip[2] + ... contiguous run from step 1
    out = []
    step = 1
    while step in step_flip:
        out.append(step_flip[step])
        step += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Third-model compliance preflight (spec section 14)
# ---------------------------------------------------------------------------

def third_model_preflight(client: OpenAI, accountant: CostAccountant,
                          raw_jsonl_path: str, log=print,
                          model_label: str = None) -> Dict[str, Any]:
    """Purely technical compliance check for the 3rd non-flagship model
    (originally mistral; now gemma). Records under kind='preflight'.

    - 10 independent-calls single-flip requests
    - 10 history-conditioned single-flip requests over short synthetic histories
    - 3 batch 100-flip requests
    """
    if model_label is None:
        # infer: the model in CORPUS_MODELS that isn't astra or fable
        model_label = next(m.label for m in C.CORPUS_MODELS
                            if m.label not in ("astra", "fable"))
    model = C.CORPUS_MODEL_BY_LABEL[model_label]
    slug = model.slug
    results: Dict[str, Any] = {"model": model_label, "slug": slug,
                               "independent_calls": [], "history_conditioned": [],
                               "batch": []}
    max_tok_step = C.corpus_max_tokens_step(model_label)
    max_tok_batch = C.corpus_max_tokens_batch(model_label)

    # 10 independent-calls
    for i in range(10):
        res = call_model(client, accountant, kind="preflight", slug=slug,
                         prompt_text=C.CORPUS_INDEPENDENT_CALLS_PROMPT,
                         max_tokens=max_tok_step)
        p = parse_online(res.response_text)
        results["independent_calls"].append(
            {"i": i, "raw": res.response_text, "parsed": p, "valid": p is not None,
             "cost": res.cost_usd, "c_toks": res.completion_tokens,
             "r_toks": res.reasoning_tokens})
        _log_attempt(raw_jsonl_path, run_id=f"{model_label}-preflight",
                     trajectory_id=f"preflight/independent/{i}",
                     model_label=model_label, requested_model_id=slug,
                     method="independent_calls", trial_index=1, attempt_index=1,
                     prompt_text=C.CORPUS_INDEPENDENT_CALLS_PROMPT,
                     history_before=None, raw_response=res.response_text,
                     parsed_flip=p, valid=p is not None,
                     error_type="" if p else "parse_fail", kind="preflight", res=res)

    # 10 history-conditioned single-flip on short synthetic histories
    synthetic = ["", "H", "T", "HT", "TH", "HHT", "TTH", "HTHT", "THTH", "HHTTH"]
    for i, h in enumerate(synthetic):
        prompt = C.corpus_history_trial_prompt(h)
        res = call_model(client, accountant, kind="preflight", slug=slug,
                         prompt_text=prompt, max_tokens=max_tok_step)
        p = parse_online(res.response_text)
        results["history_conditioned"].append(
            {"i": i, "history": h, "raw": res.response_text, "parsed": p,
             "valid": p is not None, "cost": res.cost_usd,
             "c_toks": res.completion_tokens, "r_toks": res.reasoning_tokens})
        _log_attempt(raw_jsonl_path, run_id=f"{model_label}-preflight",
                     trajectory_id=f"preflight/history/{i}",
                     model_label=model_label, requested_model_id=slug,
                     method="history_conditioned",
                     trial_index=len(h) + 1, attempt_index=1,
                     prompt_text=prompt, history_before=h,
                     raw_response=res.response_text, parsed_flip=p,
                     valid=p is not None,
                     error_type="" if p else "parse_fail", kind="preflight", res=res)

    # 3 batch 100-flip
    for i in range(3):
        res = call_model(client, accountant, kind="preflight", slug=slug,
                         prompt_text=C.CORPUS_BATCH_PROMPT, max_tokens=max_tok_batch)
        parsed = parse_batch(res.response_text, length=C.CORPUS_SEQUENCE_LENGTH)
        results["batch"].append(
            {"i": i, "raw_head": res.response_text[:80], "valid": parsed is not None,
             "len_after_strip": len("".join(res.response_text.split())),
             "cost": res.cost_usd,
             "c_toks": res.completion_tokens, "r_toks": res.reasoning_tokens})
        _log_attempt(raw_jsonl_path, run_id=f"{model_label}-preflight",
                     trajectory_id=f"preflight/batch/{i}",
                     model_label=model_label, requested_model_id=slug,
                     method="batch", trial_index=None, attempt_index=1,
                     prompt_text=C.CORPUS_BATCH_PROMPT, history_before=None,
                     raw_response=res.response_text, parsed_flip=None,
                     valid=parsed is not None,
                     error_type="" if parsed else "parse_fail", kind="preflight", res=res)

    step_correct = (sum(1 for r in results["independent_calls"] if r["valid"])
                    + sum(1 for r in results["history_conditioned"] if r["valid"]))
    step_total = 20
    step_acc = step_correct / step_total
    batch_valid = sum(1 for r in results["batch"] if r["valid"])
    ok = (step_acc >= C.CORPUS_THIRD_MODEL_PREFLIGHT_MIN_STEP_ACCURACY
          and batch_valid >= C.CORPUS_THIRD_MODEL_PREFLIGHT_MIN_BATCH_VALID)
    results["summary"] = {"step_accuracy": step_acc,
                          "batch_valid": batch_valid,
                          "batch_total": 3,
                          "passes_threshold": ok}
    log(f"  {model_label} preflight: step_acc={step_acc:.3f} batch_valid={batch_valid}/3 ok={ok}")
    return results


# Backwards-compat alias (older imports still refer to mistral_preflight)
mistral_preflight = third_model_preflight
