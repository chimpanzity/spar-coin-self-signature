"""Source generation (batch + online), resume-safe.

Batch: one call → 50 flips → validate → save trajectory.
Online: 50 sequential calls, each with full accumulated history in prompt.
        Each step is retained; a step-level invalid triggers up to 3 attempts;
        an unrecoverable step abandons the trajectory. Replacement trajectories
        start from empty history.
"""

import os
from dataclasses import asdict, dataclass, field
from typing import List, Optional

from openai import OpenAI

from . import config as C
from .api import (APIResult, CostAccountant, call_model,
                  parse_batch, parse_online, BudgetExceeded)
from .state import RunPaths, write_json, read_json, append_jsonl, read_jsonl


@dataclass
class TrajectoryRecord:
    trajectory_id: str
    architecture: str
    source_model_label: str
    requested_model_id: str
    replicate_index: int
    parsed_sequence: str
    valid: bool
    invalid_reason: str
    n_calls: int
    total_cost_usd: float
    started_utc: str
    finished_utc: str
    attempts_summary: dict = field(default_factory=dict)


def _existing_valid_trajectory_ids(dir_path: str) -> List[int]:
    """Return sorted list of replicate_index for trajectories already valid on disk."""
    if not os.path.isdir(dir_path):
        return []
    out = []
    for fn in sorted(os.listdir(dir_path)):
        if not fn.endswith(".json") or ".steps." in fn:
            continue
        p = os.path.join(dir_path, fn)
        rec = read_json(p)
        if rec and rec.get("valid"):
            out.append(int(rec["replicate_index"]))
    return sorted(out)


# --- BATCH -----------------------------------------------------------------

def generate_batch_source(client: OpenAI, accountant: CostAccountant, paths: RunPaths,
                          model: C.ModelSpec, *, log=print,
                          valid_needed: int = None) -> List[TrajectoryRecord]:
    """Generate `valid_needed` valid batch trajectories for one model. Resume-safe.

    Defaults to C.TRAJECTORIES_PER_MODEL_ARCH (10) if not specified.
    """
    if valid_needed is None:
        valid_needed = C.TRAJECTORIES_PER_MODEL_ARCH
    out_dir = os.path.join(paths.source_batch, model.label)
    os.makedirs(out_dir, exist_ok=True)
    existing = _existing_valid_trajectory_ids(out_dir)
    log(f"  batch/{model.label}: {len(existing)} valid on disk already (need {valid_needed})")
    trajectories: List[TrajectoryRecord] = []

    replicate_index = 0
    invalid_count = 0

    # Preload existing valid records so we can return them all
    for k in existing:
        rec = read_json(paths.batch_trajectory_path(model.label, k))
        trajectories.append(TrajectoryRecord(**rec))
        replicate_index = max(replicate_index, k + 1)

    while len([t for t in trajectories if t.valid]) < valid_needed:
        started_utc = _utc_now()
        # For batch, one API call per trajectory attempt.
        # Per-cell temperature override honored here (spec deviation for qwen batch).
        temp = C.temperature_for(model.label, "batch")
        res = call_model(client, accountant,
                         kind="batch", slug=model.slug,
                         prompt_text=C.BATCH_PROMPT,
                         max_tokens=C.BATCH_MAX_TOKENS,
                         temperature=temp)
        parsed = parse_batch(res.response_text) or ""
        valid = bool(parsed)
        invalid_reason = "" if valid else f"parse_fail: raw={res.response_text[:120]!r}"
        finished_utc = _utc_now()
        rec = TrajectoryRecord(
            trajectory_id=f"batch/{model.label}/{replicate_index:02d}",
            architecture="batch", source_model_label=model.label,
            requested_model_id=model.slug, replicate_index=replicate_index,
            parsed_sequence=parsed, valid=valid, invalid_reason=invalid_reason,
            n_calls=1, total_cost_usd=res.cost_usd,
            started_utc=started_utc, finished_utc=finished_utc,
            attempts_summary={"raw_response": res.response_text,
                              "served_model": res.served_model,
                              "provider": res.provider,
                              "prompt_tokens": res.prompt_tokens,
                              "completion_tokens": res.completion_tokens,
                              "reasoning_tokens": res.reasoning_tokens,
                              "finish_reason": res.finish_reason,
                              "cost_usd": res.cost_usd,
                              "latency_ms": res.latency_ms,
                              "error_message": res.error_message},
        )
        write_json(paths.batch_trajectory_path(model.label, replicate_index), asdict(rec))
        trajectories.append(rec)
        log(f"    batch/{model.label} rep{replicate_index}: "
            f"{'ok' if valid else 'INVALID'} cost=${res.cost_usd:.4f} "
            f"tokens p={res.prompt_tokens}/c={res.completion_tokens}/r={res.reasoning_tokens}")
        replicate_index += 1
        if not valid:
            invalid_count += 1
            # Batch retries are cheap and can succeed if providers give slight
            # variation even at temperature 0. Cap generously; if a model
            # persistently fails, this ceiling still stops us in bounded time.
            # (Bumped to 200 after qwen batch showed ~9% success rate at temp 0.3.)
            if invalid_count >= 200:
                log(f"    batch/{model.label}: too many invalids ({invalid_count}); aborting")
                break

    return trajectories


# --- ONLINE ----------------------------------------------------------------

def generate_online_trajectory(client: OpenAI, accountant: CostAccountant,
                               paths: RunPaths, model: C.ModelSpec,
                               replicate_index: int, *, log=print) -> TrajectoryRecord:
    """Generate a single 50-step online trajectory (or return an invalid record).

    Persists per-step records to trajectory-{k}.steps.jsonl and the trajectory
    summary to trajectory-{k}.json when done.
    """
    started_utc = _utc_now()
    history = ""
    trajectory_id = f"online/{model.label}/{replicate_index:02d}"
    n_calls = 0
    total_cost = 0.0
    step_path = paths.online_steps_path(model.label, replicate_index)
    # Resume-safe: re-load prior valid steps if any.
    prior_steps = read_jsonl(step_path)
    valid_steps = [s for s in prior_steps if s.get("valid_step")]
    for s in valid_steps:
        history += s["parsed_flip"]
        n_calls += s.get("total_attempts_at_step", 1)
        total_cost += s.get("total_cost_at_step", 0.0)
    if history:
        log(f"    online/{model.label} rep{replicate_index}: resumed from step {len(history)+1}")

    invalid_at = None
    for step in range(len(history) + 1, C.TRAJECTORY_LENGTH + 1):
        prompt = C.online_trial_prompt(history)
        step_attempts = []
        parsed = None
        step_cost = 0.0
        for attempt_no in range(1, C.ONLINE_STEP_MAX_ATTEMPTS + 1):
            res = call_model(client, accountant,
                             kind="online", slug=model.slug,
                             prompt_text=prompt,
                             max_tokens=C.ONLINE_MAX_TOKENS)
            step_cost += res.cost_usd
            step_attempts.append({
                "attempt_no": attempt_no,
                "raw_response": res.response_text,
                "parsed": parse_online(res.response_text),
                "served_model": res.served_model, "provider": res.provider,
                "generation_id": res.generation_id,
                "prompt_tokens": res.prompt_tokens,
                "completion_tokens": res.completion_tokens,
                "reasoning_tokens": res.reasoning_tokens,
                "finish_reason": res.finish_reason,
                "cost_usd": res.cost_usd, "latency_ms": res.latency_ms,
                "error_message": res.error_message,
                "call_utc": res.call_utc, "request_id": res.request_id,
            })
            parsed = parse_online(res.response_text)
            if parsed is not None:
                break

        step_rec = {
            "trajectory_id": trajectory_id, "step": step,
            "prompt_text": prompt, "history_before": history,
            "parsed_flip": parsed or "",
            "valid_step": parsed is not None,
            "attempts": step_attempts,
            "total_attempts_at_step": len(step_attempts),
            "total_cost_at_step": step_cost,
        }
        append_jsonl(step_path, step_rec)
        n_calls += len(step_attempts)
        total_cost += step_cost

        if parsed is None:
            invalid_at = step
            log(f"    online/{model.label} rep{replicate_index}: ABANDON at step {step} "
                f"(all {C.ONLINE_STEP_MAX_ATTEMPTS} attempts invalid)")
            break
        history += parsed

    finished_utc = _utc_now()
    valid = (invalid_at is None) and (len(history) == C.TRAJECTORY_LENGTH)
    rec = TrajectoryRecord(
        trajectory_id=trajectory_id, architecture="online",
        source_model_label=model.label, requested_model_id=model.slug,
        replicate_index=replicate_index,
        parsed_sequence=history if valid else "",
        valid=valid,
        invalid_reason="" if valid else f"abandoned at step {invalid_at}",
        n_calls=n_calls, total_cost_usd=total_cost,
        started_utc=started_utc, finished_utc=finished_utc,
        attempts_summary={"partial_history": history,
                          "invalid_at_step": invalid_at},
    )
    write_json(paths.online_trajectory_path(model.label, replicate_index), asdict(rec))
    log(f"    online/{model.label} rep{replicate_index}: "
        f"{'ok' if valid else 'INVALID'} calls={n_calls} cost=${total_cost:.4f}")
    return rec


def generate_online_source(client: OpenAI, accountant: CostAccountant,
                           paths: RunPaths, model: C.ModelSpec,
                           *, log=print,
                           valid_needed: int = None) -> List[TrajectoryRecord]:
    """Generate `valid_needed` valid online trajectories for one model. Resume-safe."""
    if valid_needed is None:
        valid_needed = C.TRAJECTORIES_PER_MODEL_ARCH
    out_dir = os.path.join(paths.source_online, model.label)
    os.makedirs(out_dir, exist_ok=True)
    existing = _existing_valid_trajectory_ids(out_dir)
    log(f"  online/{model.label}: {len(existing)} valid on disk already (need {valid_needed})")
    trajectories: List[TrajectoryRecord] = []
    for k in existing:
        rec = read_json(paths.online_trajectory_path(model.label, k))
        trajectories.append(TrajectoryRecord(**rec))

    replicate_index = max(existing, default=-1) + 1
    invalid_count = 0

    # Also account for existing INVALID trajectories on disk so we count them
    if os.path.isdir(out_dir):
        for fn in sorted(os.listdir(out_dir)):
            if not fn.endswith(".json") or ".steps." in fn:
                continue
            p = os.path.join(out_dir, fn)
            rec = read_json(p)
            if rec and not rec.get("valid"):
                invalid_count += 1

    while len([t for t in trajectories if t.valid]) < valid_needed:
        if invalid_count >= C.MAX_INVALID_TRAJECTORIES_PER_MODEL:
            log(f"    online/{model.label}: feasibility failure "
                f"({invalid_count} invalid trajectories); aborting model")
            break
        rec = generate_online_trajectory(client, accountant, paths, model,
                                         replicate_index, log=log)
        trajectories.append(rec)
        replicate_index += 1
        if not rec.valid:
            invalid_count += 1

    return trajectories


# --- helper ----------------------------------------------------------------

def _utc_now() -> str:
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
