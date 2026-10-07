"""Judgment phase: one fresh, stateless API call per trial, no feedback, no model names.

Response handling:
  * structured: JSON-schema response_format (schemas/judgment.schema.json). Used only if every
    judge passes the preflight (free catalog check + optional tiny live call). Otherwise all
    judges fall back to one_word so the response method is identical across judges.
  * one_word: plain SAME / DIFFERENT, parsed strictly.

Invalid judgments stay in the raw data. A replacement attempt is a new judgment record whose
`replacement_for` points to the invalid one; up to judgment.max_attempts_per_trial malformed
attempts per trial. API/transport failures are recorded (invalid_reason "api_error"), stop the
phase, and do not count toward that ceiling.
"""

from __future__ import annotations

import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from .build_trials import render_prompt
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
    structured_response_format,
)
from .parse import parse_judgment, parse_judgment_structured
from .records import (
    JudgmentRecord,
    RunPaths,
    TrialRecord,
    append_jsonl,
    iso,
    latest_judgments_by_trial,
    read_jsonl,
    sha256_text,
    update_manifest,
    utc_now,
    write_raw_response,
)
from .run_setup import relative_to_run

log = logging.getLogger(__name__)

PREFLIGHT_PROMPT = "This is a format check. Return the requested JSON with the judgment field set to SAME."


def judge_payload(cfg: PilotConfig, label: str, prompt_text: str, response_mode: str,
                  schema: dict[str, Any] | None, seed: int | None = None) -> dict[str, Any]:
    j = cfg.judgment
    if response_mode == "structured" and schema is None:
        raise ValueError("structured mode requires the judgment schema")
    rf = structured_response_format(schema) if response_mode == "structured" else None
    return build_chat_payload(
        seed=seed,
        model_id=cfg.model_id(label),
        user_prompt=prompt_text,
        system_prompt=j.system_prompt,
        max_tokens=j.max_tokens,
        reasoning_effort=j.reasoning_effort,
        include_reasoning=j.include_reasoning,
        temperature=j.temperature,
        provider_allow_fallbacks=cfg.openrouter.provider_allow_fallbacks,
        provider_require_parameters=cfg.openrouter.provider_require_parameters,
        response_format=rf,
        provider_order=[cfg.models[label].provider] if cfg.models[label].provider else None,
    )


def template_for_mode(prompts: dict[str, dict[str, str]], response_mode: str) -> str:
    key = "judge_same_different_structured" if response_mode == "structured" else "judge_same_different"
    return prompts[key]["text"]


def _max_attempt_on_disk(paths: RunPaths, subdir: str, stem: str) -> int:
    """Highest attempt number for which a raw response file already exists (crash guard)."""
    d = paths.responses_dir / subdir
    best = 0
    if d.exists():
        for f in d.glob(f"{stem}_a*.json"):
            m = re.fullmatch(re.escape(stem) + r"_a(\d+)\.json", f.name)
            if m:
                best = max(best, int(m.group(1)))
    return best


# ---------------------------------------------------------------- preflight

def catalog_preflight(catalog_models: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Free check: does each judge's catalog entry advertise response_format support?"""
    out: dict[str, dict[str, Any]] = {}
    for label, info in catalog_models.items():
        params = info.get("supported_parameters") or []
        ok = "response_format" in params
        note = "" if "structured_outputs" in params else "structured_outputs not advertised; "
        out[label] = {"pass": ok, "detail": f"{note}supported_parameters={params}"}
    return out


def live_preflight(
    cfg: PilotConfig, client: ChatClient, paths: RunPaths, run_id: str,
    catalog_entries: dict[str, dict[str, Any]], budget: BudgetGuard, schema: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """One tiny paid structured call per judge; records are kept in preflight_calls.jsonl.

    A budget stop here raises BudgetExceeded (it is not a schema failure and must not force the
    one-word fallback).
    """
    results: dict[str, dict[str, Any]] = {}
    existing = read_jsonl(paths.preflight_calls, JudgmentRecord)
    for label in cfg.model_labels:
        prior = [r for r in existing if r.judge_model_label == label]
        done = next((r for r in prior if r.valid), None) or (prior[-1] if prior else None)
        if done is not None and (done.valid or done.invalid_reason != "api_error"):
            results[label] = {"pass": bool(done.valid and done.parsed_judgment == "SAME"),
                              "detail": f"reused earlier preflight {done.judgment_id}: valid={done.valid} {done.invalid_reason or ''}"}
            continue
        attempt = max(len(prior), _max_attempt_on_disk(paths, "preflight", f"preflight_{label}")) + 1
        judgment_id = f"preflight_{label}_a{attempt}"
        payload = judge_payload(cfg, label, PREFLIGHT_PROMPT, "structured", schema)
        est = estimate_call_cost(catalog_entries[label], 40, 100)
        raw_path = paths.responses_dir / "preflight" / f"{judgment_id}.json"
        started = utc_now()
        budget.reserve(est)  # raises BudgetExceeded: caller stops the phase
        try:
            result = client.chat_completion(payload)
        except OpenRouterAPIError as exc:
            budget.settle(est, 0.0)
            completed = utc_now()
            write_raw_response(raw_path, {"error": str(exc), "status_code": exc.status_code, "body": exc.body})
            rec = JudgmentRecord(
                run_id=run_id, judgment_id=judgment_id, trial_id=f"preflight_{label}", judge_model_label=label,
                requested_model_id=cfg.model_id(label), response_mode="structured",
                prompt_hash=sha256_text(PREFLIGHT_PROMPT), request_payload_sanitized=payload,
                raw_response_path=relative_to_run(paths, raw_path), valid=False, invalid_reason="api_error",
                attempt_number=attempt, started_at=iso(started), completed_at=iso(completed),
                latency_ms=int((completed - started).total_seconds() * 1000), error=str(exc),
            )
            append_jsonl(paths.preflight_calls, rec)
            results[label] = {"pass": False, "detail": f"API error: {exc}"}
            continue
        est_from_usage = estimate_cost_from_usage(catalog_entries[label], result.usage, est)
        budget.settle(est, result.cost if result.cost is not None else est_from_usage)
        write_raw_response(raw_path, result.raw_dump())
        parsed = parse_judgment_structured(result.content)
        rec = JudgmentRecord(
            run_id=run_id, judgment_id=judgment_id, trial_id=f"preflight_{label}", judge_model_label=label,
            requested_model_id=cfg.model_id(label), returned_model_id=result.returned_model,
            provider=result.provider, response_mode="structured", prompt_hash=sha256_text(PREFLIGHT_PROMPT),
            request_payload_sanitized=payload, raw_response_path=relative_to_run(paths, raw_path),
            raw_completion=result.content, parsed_judgment=parsed.value, valid=parsed.valid,
            invalid_reason=parsed.reason, attempt_number=attempt, request_id=result.request_id,
            started_at=result.started_at, completed_at=result.completed_at, latency_ms=result.latency_ms,
            token_usage=result.usage, reported_cost=result.cost, estimated_cost=est_from_usage,
            call_attempts=result.attempts, finish_reason=result.finish_reason,
        )
        append_jsonl(paths.preflight_calls, rec)
        ok = parsed.valid and parsed.value == "SAME"
        results[label] = {"pass": ok, "detail": f"content={result.content!r} parsed={parsed.value} {parsed.reason or ''}"}
    return results


def decide_response_mode(
    cfg: PilotConfig, catalog_models: dict[str, dict[str, Any]],
    live: dict[str, dict[str, Any]] | None,
) -> tuple[str, dict[str, Any]]:
    """Pick the response mode used for every judge, with the evidence."""
    requested = cfg.judgment.response_mode
    if requested != "structured":
        return requested, {"requested": requested, "reason": "one_word requested in config"}
    cat = catalog_preflight(catalog_models)
    failures = [f"{l}: catalog ({v['detail']})" for l, v in cat.items() if not v["pass"]]
    if live:
        failures += [f"{l}: live ({v['detail']})" for l, v in live.items() if not v["pass"]]
    if failures:
        mode = cfg.judgment.fallback_response_mode
        return mode, {"requested": requested, "catalog_preflight": cat, "live_preflight": live,
                      "reason": "fallback: " + " | ".join(failures)}
    return "structured", {"requested": requested, "catalog_preflight": cat, "live_preflight": live,
                          "reason": "all judges passed preflight"}


# ---------------------------------------------------------------- planning / resume

@dataclass
class JudgmentPlan:
    per_judge: dict[str, dict[str, int]]
    total_planned_calls: int
    pending_trial_ids: list[str]
    abandoned_trial_ids: list[str]


def _trial_status(cfg: PilotConfig, trials: list[TrialRecord], judgments: list[JudgmentRecord]) -> dict[str, dict[str, Any]]:
    """Per trial: has a valid judgment? how many malformed attempts? latest record?"""
    latest = latest_judgments_by_trial(judgments)
    malformed: dict[str, int] = {}
    valid: set[str] = set()
    for r in judgments:
        if r.valid:
            valid.add(r.trial_id)
        elif r.invalid_reason != "api_error":
            malformed[r.trial_id] = malformed.get(r.trial_id, 0) + 1
    out: dict[str, dict[str, Any]] = {}
    for t in trials:
        n_bad = malformed.get(t.trial_id, 0)
        out[t.trial_id] = {
            "valid": t.trial_id in valid,
            "malformed_attempts": n_bad,
            "abandoned": t.trial_id not in valid and n_bad >= cfg.judgment.max_attempts_per_trial,
            "latest": latest.get(t.trial_id),
        }
    return out


def pending_trials(cfg: PilotConfig, trials: list[TrialRecord], judgments: list[JudgmentRecord]) -> list[TrialRecord]:
    """Trials that still need a call, ordered round-robin across judges by position, so a
    `--limit N` smoke test touches every judge and concurrent workers spread across providers."""
    status = _trial_status(cfg, trials, judgments)
    label_index = {l: i for i, l in enumerate(cfg.model_labels)}
    pend = [t for t in trials if not status[t.trial_id]["valid"] and not status[t.trial_id]["abandoned"]]
    return sorted(pend, key=lambda t: (t.trial_position, label_index.get(t.judge_model_label, 99)))


def plan_judgments(cfg: PilotConfig, paths: RunPaths, trials: list[TrialRecord]) -> JudgmentPlan:
    judgments = read_jsonl(paths.judgment_calls, JudgmentRecord)
    status = _trial_status(cfg, trials, judgments)
    pend = pending_trials(cfg, trials, judgments)
    per_judge: dict[str, dict[str, int]] = {}
    for label in cfg.model_labels:
        js = [t for t in trials if t.judge_model_label == label]
        per_judge[label] = {
            "trials": len(js),
            "valid_judgments": sum(1 for t in js if status[t.trial_id]["valid"]),
            "invalid_attempts": sum(1 for r in judgments if r.judge_model_label == label and not r.valid
                                    and r.invalid_reason != "api_error"),
            "api_errors": sum(1 for r in judgments if r.judge_model_label == label and r.invalid_reason == "api_error"),
            "abandoned_trials": sum(1 for t in js if status[t.trial_id]["abandoned"]),
            "planned_calls": sum(1 for t in pend if t.judge_model_label == label),
        }
    return JudgmentPlan(
        per_judge=per_judge, total_planned_calls=len(pend),
        pending_trial_ids=[t.trial_id for t in pend],
        abandoned_trial_ids=[t.trial_id for t in trials if status[t.trial_id]["abandoned"]],
    )


@dataclass
class JudgmentOutcome:
    calls_made: int
    valid_total: int
    invalid_total: int
    complete: bool
    budget: dict[str, Any]
    stop_reason: str | None = None
    error: str | None = None
    per_judge: dict[str, dict[str, int]] = field(default_factory=dict)


# ---------------------------------------------------------------- running

def run_judgments(
    cfg: PilotConfig,
    client: ChatClient,
    paths: RunPaths,
    run_id: str,
    catalog_entries: dict[str, dict[str, Any]],
    budget: BudgetGuard,
    trials: list[TrialRecord],
    prompt_template: str,
    response_mode: str,
    schema: dict[str, Any] | None,
    limit: int | None = None,
) -> JudgmentOutcome:
    lock = threading.Lock()
    state = {"calls": 0, "stop": None, "error": None}
    records: list[JudgmentRecord] = read_jsonl(paths.judgment_calls, JudgmentRecord)
    latest = latest_judgments_by_trial(records)
    # crash guard: never reuse an attempt number that already has a raw response file
    disk_attempt = {t.trial_id: _max_attempt_on_disk(paths, "judgment", f"j_{t.trial_id}") for t in trials}
    est_by_label = {
        label: estimate_call_cost(catalog_entries[label], cfg.estimate.judgment_prompt_tokens,
                                  cfg.estimate.judgment_completion_tokens)
        for label in cfg.model_labels
    }

    def one_trial(t: TrialRecord) -> None:
        label = t.judge_model_label
        with lock:
            if state["stop"]:
                return
            if limit is not None and state["calls"] >= limit:
                state["stop"] = "limit"
                return
            try:
                budget.reserve(est_by_label[label])
            except BudgetExceeded as exc:
                state["stop"] = "budget"
                log.error("%s", exc)
                return
            state["calls"] += 1
            prev = latest.get(t.trial_id)
            attempt = max(prev.attempt_number if prev else 0, disk_attempt.get(t.trial_id, 0)) + 1
            disk_attempt[t.trial_id] = attempt
            replacement_for = prev.judgment_id if (prev and not prev.valid) else None
        judgment_id = f"j_{t.trial_id}_a{attempt}"
        prompt_text = render_prompt(prompt_template, t.string_1_display, t.string_2_display)
        api_seed, send = seed_for_call(cfg.openrouter.send_seed, cfg.run.seed, judgment_id, catalog_entries[label])
        payload = judge_payload(cfg, label, prompt_text, response_mode, schema, seed=api_seed if send else None)
        raw_path = paths.responses_dir / "judgment" / f"{judgment_id}.json"
        started = utc_now()
        try:
            result = client.chat_completion(payload)
        except OpenRouterAPIError as exc:
            budget.settle(est_by_label[label], 0.0)
            completed = utc_now()
            write_raw_response(raw_path, {"error": str(exc), "status_code": exc.status_code, "body": exc.body,
                                          "started_at": iso(started), "completed_at": iso(completed)})
            rec = JudgmentRecord(
                run_id=run_id, judgment_id=judgment_id, trial_id=t.trial_id, judge_model_label=label,
                requested_model_id=cfg.model_id(label), response_mode=response_mode,  # type: ignore[arg-type]
                prompt_hash=sha256_text(prompt_text), request_payload_sanitized=payload,
                raw_response_path=relative_to_run(paths, raw_path), valid=False, invalid_reason="api_error",
                replacement_for=replacement_for, attempt_number=attempt, started_at=iso(started),
                completed_at=iso(completed), latency_ms=int((completed - started).total_seconds() * 1000),
                error=str(exc),
            )
            append_jsonl(paths.judgment_calls, rec)
            with lock:
                records.append(rec)
                latest[t.trial_id] = rec
                state["stop"] = "api_error"
                state["error"] = f"{judgment_id}: {exc}"
            log.error("API error for %s: %s", judgment_id, exc)
            return
        est_from_usage = estimate_cost_from_usage(catalog_entries[label], result.usage, est_by_label[label])
        budget.settle(est_by_label[label], result.cost if result.cost is not None else est_from_usage)
        write_raw_response(raw_path, result.raw_dump())
        parsed = parse_judgment(result.content, response_mode, lenient=cfg.judgment.lenient_parse)
        rec = JudgmentRecord(
            run_id=run_id, judgment_id=judgment_id, trial_id=t.trial_id, judge_model_label=label,
            requested_model_id=cfg.model_id(label), returned_model_id=result.returned_model,
            provider=result.provider, response_mode=response_mode,  # type: ignore[arg-type]
            prompt_hash=sha256_text(prompt_text), request_payload_sanitized=payload,
            raw_response_path=relative_to_run(paths, raw_path), raw_completion=result.content,
            parsed_judgment=parsed.value, valid=parsed.valid, invalid_reason=parsed.reason,
            correct=(parsed.value == t.correct_answer) if parsed.valid else None,
            replacement_for=replacement_for, attempt_number=attempt, request_id=result.request_id,
            started_at=result.started_at, completed_at=result.completed_at, latency_ms=result.latency_ms,
            token_usage=result.usage, reported_cost=result.cost, estimated_cost=est_from_usage,
            call_attempts=result.attempts, finish_reason=result.finish_reason,
        )
        append_jsonl(paths.judgment_calls, rec)
        with lock:
            records.append(rec)
            latest[t.trial_id] = rec
        log.info("judgment %s: %s -> %s (%s)", judgment_id, parsed.value or f"INVALID {parsed.reason}",
                 "correct" if rec.correct else ("wrong" if rec.correct is False else "n/a"), result.returned_model)

    # Passes: first every pending trial, then replacement attempts for malformed ones, until
    # nothing is pending or nothing more can be done in this invocation.
    while True:
        with lock:
            pend = pending_trials(cfg, trials, records)
        if not pend or state["stop"]:
            break
        before = state["calls"]
        with ThreadPoolExecutor(max_workers=max(1, cfg.openrouter.concurrency)) as ex:
            list(ex.map(one_trial, pend))
        if state["calls"] == before:
            break

    status = _trial_status(cfg, trials, records)
    valid_total = sum(1 for s in status.values() if s["valid"])
    invalid_total = sum(1 for r in records if not r.valid and r.invalid_reason != "api_error")
    api_errors_total = sum(1 for r in records if r.invalid_reason == "api_error")
    complete = all(s["valid"] for s in status.values())
    per_judge = {}
    for label in cfg.model_labels:
        js = [t for t in trials if t.judge_model_label == label]
        per_judge[label] = {
            "trials": len(js),
            "valid_judgments": sum(1 for t in js if status[t.trial_id]["valid"]),
            "abandoned_trials": sum(1 for t in js if status[t.trial_id]["abandoned"]),
        }
    outcome = JudgmentOutcome(
        calls_made=state["calls"], valid_total=valid_total, invalid_total=invalid_total,
        complete=complete, budget=budget.snapshot(), stop_reason=state["stop"], error=state["error"],
        per_judge=per_judge,
    )
    update_manifest(paths, phases={"judgments": {
        "last_run_at": iso(utc_now()),
        "complete": complete,
        "calls_made_this_invocation": state["calls"],
        "valid_judgments": valid_total,
        "invalid_attempts_total": invalid_total,
        "api_errors_total": api_errors_total,
        "per_judge": per_judge,
        "budget": budget.snapshot(),
        "stop_reason": state["stop"],
        "error": state["error"],
    }})
    return outcome
