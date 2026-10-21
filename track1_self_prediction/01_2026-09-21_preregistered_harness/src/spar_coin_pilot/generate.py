"""Source-string generation: one fresh, stateless API call per string.

Invalid responses are recorded as invalid (raw response retained) and replaced by a new call
with a new sample_id whose `replacement_for` points at the invalid sample. Generation for a
model stops when the configured number of valid strings exists or the invalid-attempt ceiling
is reached. Re-running the command resumes from the records already on disk.

API/transport failures are recorded too (invalid_reason "api_error") and stop the phase, but
they do not count toward the malformed-output ceiling.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from .config import PilotConfig
from .openrouter_client import (
    BudgetExceeded,
    BudgetGuard,
    ChatClient,
    OpenRouterAPIError,
    build_chat_payload,
    estimate_call_cost,
    estimate_cost_from_usage,
    seed_for_call,
)
from .parse import parse_source_string
from .records import (
    RunPaths,
    SourceRecord,
    append_jsonl,
    iso,
    read_jsonl,
    sha256_text,
    update_manifest,
    utc_now,
    write_raw_response,
)
from .run_setup import relative_to_run

log = logging.getLogger(__name__)


def source_payload(cfg: PilotConfig, label: str, prompt_text: str, seed: int | None = None) -> dict[str, Any]:
    g = cfg.generation
    return build_chat_payload(
        seed=seed,
        model_id=cfg.model_id(label),
        user_prompt=prompt_text,
        system_prompt=g.system_prompt,
        max_tokens=g.max_tokens,
        reasoning_effort=g.reasoning_effort,
        include_reasoning=g.include_reasoning,
        temperature=g.temperature,
        provider_allow_fallbacks=cfg.openrouter.provider_allow_fallbacks,
        provider_require_parameters=cfg.openrouter.provider_require_parameters,
        provider_order=[cfg.models[label].provider] if cfg.models[label].provider else None,
    )


@dataclass
class ModelProgress:
    valid: int = 0
    invalid: int = 0          # malformed completions (count toward the ceiling)
    api_errors: int = 0       # transport / API failures (do not count toward the ceiling)
    calls: int = 0
    last_invalid_sample_id: str | None = None
    stop_reason: str | None = None


@dataclass
class GenerationPlan:
    per_model: dict[str, dict[str, Any]]
    total_planned_calls: int
    example_payloads: dict[str, dict[str, Any]]


@dataclass
class GenerationOutcome:
    progress: dict[str, ModelProgress]
    calls_made: int
    budget: dict[str, Any]
    error: str | None = None
    complete: bool = False
    stop_reasons: dict[str, str | None] = field(default_factory=dict)


def _existing_progress(cfg: PilotConfig, paths: RunPaths) -> dict[str, ModelProgress]:
    records = read_jsonl(paths.source_calls, SourceRecord)
    progress = {label: ModelProgress() for label in cfg.model_labels}
    for r in records:
        p = progress.get(r.source_model_label)
        if p is None:
            continue
        p.calls = max(p.calls, r.attempt_number)
        if r.valid:
            p.valid += 1
            p.last_invalid_sample_id = None
        else:
            if r.invalid_reason == "api_error":
                p.api_errors += 1
            else:
                p.invalid += 1
            p.last_invalid_sample_id = r.sample_id
    # Guard against a crash between writing a raw file and appending its record: never reuse
    # a sample number that already has a raw response file.
    src_dir = paths.responses_dir / "source"
    if src_dir.exists():
        for f in src_dir.glob("src_*_*.json"):
            m = re.fullmatch(r"src_([a-z_0-9]+)_(\d+)\.json", f.name)
            if m and m.group(1) in progress:
                progress[m.group(1)].calls = max(progress[m.group(1)].calls, int(m.group(2)))
    return progress


def plan_generation(cfg: PilotConfig, paths: RunPaths, prompt_text: str) -> GenerationPlan:
    """What a (resumed or fresh) generation run would do, without making calls."""
    progress = _existing_progress(cfg, paths)
    per_model: dict[str, dict[str, Any]] = {}
    total = 0
    for label in cfg.model_labels:
        p = progress[label]
        ceiling_hit = p.invalid >= cfg.generation.max_invalid_attempts_per_model
        planned = 0 if ceiling_hit else max(0, cfg.generation.valid_strings_per_model - p.valid)
        per_model[label] = {
            "existing_valid": p.valid,
            "existing_invalid": p.invalid,
            "existing_api_errors": p.api_errors,
            "planned_calls": planned,
            "invalid_ceiling_reached": ceiling_hit,
        }
        total += planned
    examples = {label: source_payload(cfg, label, prompt_text) for label in cfg.model_labels}
    return GenerationPlan(per_model=per_model, total_planned_calls=total, example_payloads=examples)


def run_generation(
    cfg: PilotConfig,
    client: ChatClient,
    paths: RunPaths,
    run_id: str,
    catalog_entries: dict[str, dict[str, Any]],
    budget: BudgetGuard,
    prompt_text: str,
    limit: int | None = None,
) -> GenerationOutcome:
    """Make source calls until every model has its valid strings (or a stop condition hits).

    Dispatch is strict round-robin across models: call k+1 for any model is not dispatched
    until every model that still needs strings has dispatched call k (config order breaks
    ties), and at most one call per model is in flight at any time. So `--limit 3` means
    exactly one call per model, `--limit 7` means 3/2/2, every model advances at the same
    pace however fast or slow its provider is (a slow provider is the bottleneck either way),
    and each model's invalid -> replacement chain is strictly sequential.
    """
    g = cfg.generation
    prompt_hash = sha256_text(prompt_text)
    progress = _existing_progress(cfg, paths)
    lock = threading.Lock()
    total_calls = {"n": 0}
    fatal: dict[str, str | None] = {"error": None}
    stop_all = {"reason": None}
    est_cost = {label: estimate_call_cost(catalog_entries[label], cfg.estimate.source_prompt_tokens,
                                          cfg.estimate.source_completion_tokens) for label in cfg.model_labels}
    # calls dispatched in this invocation, per model (drives the round-robin choice)
    dispatched = {label: 0 for label in cfg.model_labels}
    in_flight = {label: 0 for label in cfg.model_labels}

    WAIT = "wait"

    def wants_more(label: str) -> bool:
        p = progress[label]
        return p.valid < g.valid_strings_per_model and p.invalid < g.max_invalid_attempts_per_model

    def next_job() -> tuple[str, int, str, str | None] | str | None:
        """Reserve the next call (label, attempt number, sample id, replacement_for), WAIT if
        the next round-robin slot belongs to a model whose call is still in flight, or None."""
        with lock:
            if fatal["error"] or stop_all["reason"]:
                return None
            if limit is not None and total_calls["n"] >= limit:
                stop_all["reason"] = "limit"
                return None
            needing = [l for l in cfg.model_labels if wants_more(l)]
            if not needing:
                return None
            min_dispatched = min(dispatched[l] for l in needing)
            ready = [l for l in needing if dispatched[l] == min_dispatched and in_flight[l] == 0]
            if not ready:
                return WAIT
            label = ready[0]
            try:
                budget.reserve(est_cost[label])
            except BudgetExceeded as exc:
                stop_all["reason"] = "budget"
                log.error("%s", exc)
                return None
            p = progress[label]
            p.calls += 1
            total_calls["n"] += 1
            dispatched[label] += 1
            in_flight[label] += 1
            # The pending replacement link is claimed by exactly one call. If that call is itself
            # invalid, its own sample id becomes the next link, so chains stay one-to-one.
            replacement_for = p.last_invalid_sample_id
            p.last_invalid_sample_id = None
            return label, p.calls, f"src_{label}_{p.calls:03d}", replacement_for

    def do_call(label: str, n: int, sample_id: str, replacement_for: str | None) -> None:
        p = progress[label]
        api_seed, send = seed_for_call(cfg.openrouter.send_seed, cfg.run.seed, sample_id, catalog_entries[label])
        payload = source_payload(cfg, label, prompt_text, seed=api_seed if send else None)
        raw_path = paths.responses_dir / "source" / f"{sample_id}.json"
        started = utc_now()
        try:
            result = client.chat_completion(payload)
        except OpenRouterAPIError as exc:
            completed = utc_now()
            budget.settle(est_cost[label], 0.0)
            write_raw_response(raw_path, {
                "error": str(exc), "status_code": exc.status_code, "body": exc.body,
                "started_at": iso(started), "completed_at": iso(completed),
            })
            rec = SourceRecord(
                run_id=run_id, sample_id=sample_id, source_model_label=label,
                requested_model_id=cfg.model_id(label), prompt_text=prompt_text, prompt_hash=prompt_hash,
                request_payload_sanitized=payload, raw_response_path=relative_to_run(paths, raw_path),
                valid=False, invalid_reason="api_error", replacement_for=replacement_for,
                attempt_number=n, started_at=iso(started), completed_at=iso(completed),
                latency_ms=int((completed - started).total_seconds() * 1000), error=str(exc),
            )
            append_jsonl(paths.source_calls, rec)
            with lock:
                in_flight[label] -= 1
                p.api_errors += 1
                p.last_invalid_sample_id = sample_id
                fatal["error"] = f"{label}/{sample_id}: {exc}"
            log.error("API error for %s (%s): %s", label, sample_id, exc)
            return

        est_from_usage = estimate_cost_from_usage(catalog_entries[label], result.usage, est_cost[label])
        budget.settle(est_cost[label], result.cost if result.cost is not None else est_from_usage)
        write_raw_response(raw_path, result.raw_dump())
        parsed = parse_source_string(result.content, g.string_length, g.alphabet)
        rec = SourceRecord(
            run_id=run_id, sample_id=sample_id, source_model_label=label,
            requested_model_id=cfg.model_id(label), returned_model_id=result.returned_model,
            provider=result.provider, prompt_text=prompt_text, prompt_hash=prompt_hash,
            request_payload_sanitized=payload, request_id=result.request_id,
            raw_response_path=relative_to_run(paths, raw_path), raw_completion=result.content,
            parsed_string=parsed.value, valid=parsed.valid, invalid_reason=parsed.reason,
            replacement_for=replacement_for, attempt_number=n,
            started_at=result.started_at, completed_at=result.completed_at, latency_ms=result.latency_ms,
            token_usage=result.usage, reported_cost=result.cost, estimated_cost=est_from_usage,
            call_attempts=result.attempts, finish_reason=result.finish_reason,
        )
        append_jsonl(paths.source_calls, rec)
        with lock:
            in_flight[label] -= 1
            if parsed.valid:
                p.valid += 1
            else:
                p.invalid += 1
                p.last_invalid_sample_id = sample_id
        log.info("source %s: %s (%s) cost=%s", sample_id, "valid" if parsed.valid else f"INVALID {parsed.reason}",
                 result.returned_model, result.cost)

    def worker() -> None:
        while True:
            job = next_job()
            if job is None:
                return
            if job == WAIT:
                time.sleep(0.05)
                continue
            do_call(*job)

    workers = max(1, min(cfg.openrouter.concurrency, len(cfg.model_labels)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(lambda _: worker(), range(workers)))

    for label, p in progress.items():
        if p.valid >= g.valid_strings_per_model:
            p.stop_reason = "complete"
        elif fatal["error"]:
            p.stop_reason = "api_error" if fatal["error"].startswith(f"{label}/") else "aborted_after_error_elsewhere"
        elif p.invalid >= g.max_invalid_attempts_per_model:
            p.stop_reason = "invalid_ceiling"
        else:
            p.stop_reason = stop_all["reason"] or "incomplete"

    complete = all(p.valid >= g.valid_strings_per_model for p in progress.values())
    outcome = GenerationOutcome(
        progress=progress, calls_made=total_calls["n"], budget=budget.snapshot(),
        error=fatal["error"], complete=complete,
        stop_reasons={label: p.stop_reason for label, p in progress.items()},
    )
    update_manifest(paths, phases={"generate": {
        "last_run_at": iso(utc_now()),
        "complete": complete,
        "calls_made_this_invocation": total_calls["n"],
        "per_model": {label: {"valid": p.valid, "invalid": p.invalid, "api_errors": p.api_errors,
                              "calls": p.calls, "stop_reason": p.stop_reason}
                      for label, p in progress.items()},
        "budget": budget.snapshot(),
        "error": fatal["error"],
    }})
    return outcome
