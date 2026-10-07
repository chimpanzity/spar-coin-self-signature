"""Flat, self-contained CSV export: one row per API call carrying everything known about it.

The raw JSONL records and per-call response files remain the canonical data. This module
denormalizes them so that a single row in `calls_all.csv` (or the per-kind files) contains
the run configuration, seeds, catalog snapshot, exact request parameters, the full raw
completion, token usage broken out, response metadata, and, for judgment calls, the trial
design and both source strings' provenance. Nothing needs to be joined to analyze a row.

Files written to data/derived/<run_id>/:
  calls_all.csv     every call (source, preflight, judgment) with the union of all columns
  sources.csv       source calls + per-string diagnostics
  judgments.csv     judgment calls + trial design + source provenance
  preflight.csv     structured-output preflight calls
  trials.csv        the trial design alone (one row per trial)
  columns.md        column dictionary
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from .config import PilotConfig
from .records import (
    JudgmentRecord,
    RunPaths,
    SourceRecord,
    TrialRecord,
    load_manifest,
    load_trials,
    read_json,
    read_jsonl,
)
from .summarize import string_diagnostics

# Column groups, in output order. Documented in columns.md.
RUN_COLUMNS = [
    "run_id", "run_name", "run_seed", "run_created_at", "fake_client", "config_hash",
    "package_version", "harness_git_commit", "python_version", "platform", "hostname",
    "generation_prompt_sha256", "judge_prompt_one_word_sha256", "judge_prompt_structured_sha256",
    "judgment_response_mode_effective", "judgment_response_mode_reason",
]
CALL_COLUMNS = [
    "call_kind", "record_id", "model_label", "requested_model_id", "returned_model_id", "provider",
    "provider_pin", "attempt_number", "replacement_for", "valid", "invalid_reason", "error",
    "request_id", "started_at", "completed_at", "latency_ms", "call_attempts", "finish_reason",
    "native_finish_reason", "reported_cost_usd", "estimated_cost_usd",
]
REQUEST_COLUMNS = [
    "prompt_text", "prompt_hash", "system_prompt", "max_tokens", "reasoning_effort", "reasoning_exclude",
    "temperature_sent", "api_seed", "api_seed_sent", "provider_allow_fallbacks", "provider_require_parameters",
    "provider_order", "response_format_type", "response_schema_name", "response_schema_strict",
    "request_payload_json",
]
RESPONSE_COLUMNS = [
    "raw_completion", "parsed_string", "parsed_judgment", "correct",
    "response_id", "response_object", "response_created", "system_fingerprint",
    "reasoning_text", "reasoning_detail_types", "reasoning_details_json",
    "http_status", "response_headers_json", "raw_response_path",
]
USAGE_COLUMNS = [
    "prompt_tokens", "completion_tokens", "total_tokens", "reasoning_tokens", "cached_prompt_tokens",
    "audio_tokens", "usage_cost", "usage_json",
]
CATALOG_COLUMNS = [
    "catalog_fetched_at", "catalog_name", "catalog_created", "canonical_slug", "context_length",
    "price_prompt_per_token", "price_completion_per_token", "price_internal_reasoning_per_token",
    "supported_parameters", "endpoint_providers",
]
TRIAL_COLUMNS = [
    "trial_id", "judge_model_label", "trial_position", "analytical_cell", "subcell", "correct_answer",
    "source_pair", "source_1_model_label", "source_2_model_label", "source_1_sample_id", "source_2_sample_id",
    "display_order", "construction_seed", "build_attempts", "order_max_cell_run", "order_max_answer_run",
    "stimulus_hash", "display_alphabet", "string_1_display", "string_2_display",
    "string_1_canonical", "string_2_canonical",
    "source_1_returned_model_id", "source_1_provider", "source_1_request_id", "source_1_completed_at",
    "source_2_returned_model_id", "source_2_provider", "source_2_request_id", "source_2_completed_at",
    "n_attempts_for_trial",
]
DIAG_COLUMNS = [
    "length", "prop_H", "alternation_rate", "n_runs", "expected_runs", "runs_test_z", "runs_test_p",
    "longest_run", "first_outcome", "bigram_HH", "bigram_HT", "bigram_TH", "bigram_TT",
]


def _json(x: Any) -> str | None:
    return None if x is None else json.dumps(x, ensure_ascii=False, sort_keys=True, default=str)


def _run_columns(cfg: PilotConfig, manifest: dict) -> dict[str, Any]:
    env = manifest.get("environment") or {}
    prompts = manifest.get("prompts") or {}
    mode = manifest.get("judgment_response_mode") or {}
    return {
        "run_id": manifest.get("run_id"),
        "run_name": manifest.get("run_name"),
        "run_seed": (manifest.get("config") or {}).get("run", {}).get("seed", cfg.run.seed),
        "run_created_at": manifest.get("created_at"),
        "fake_client": manifest.get("fake_client"),
        "config_hash": manifest.get("config_hash"),
        "package_version": env.get("package_version"),
        "harness_git_commit": env.get("git_commit"),
        "python_version": env.get("python"),
        "platform": env.get("platform"),
        "hostname": env.get("hostname"),
        "generation_prompt_sha256": (prompts.get("generate_coin") or {}).get("sha256"),
        "judge_prompt_one_word_sha256": (prompts.get("judge_same_different") or {}).get("sha256"),
        "judge_prompt_structured_sha256": (prompts.get("judge_same_different_structured") or {}).get("sha256"),
        "judgment_response_mode_effective": mode.get("effective"),
        "judgment_response_mode_reason": mode.get("reason"),
    }


def _catalog_columns(manifest: dict, label: str) -> dict[str, Any]:
    cat = manifest.get("catalog") or {}
    info = (cat.get("models") or {}).get(label) or {}
    entry = info.get("catalog_entry") or {}
    pricing = entry.get("pricing") or {}
    eps = info.get("endpoints") or {}
    names = [e.get("provider_name") for e in (eps.get("endpoints") or [])] if isinstance(eps, dict) else []
    return {
        "catalog_fetched_at": cat.get("fetched_at"),
        "catalog_name": entry.get("name"),
        "catalog_created": entry.get("created"),
        "canonical_slug": entry.get("canonical_slug"),
        "context_length": entry.get("context_length"),
        "price_prompt_per_token": pricing.get("prompt"),
        "price_completion_per_token": pricing.get("completion"),
        "price_internal_reasoning_per_token": pricing.get("internal_reasoning"),
        "supported_parameters": ";".join(info.get("supported_parameters") or []),
        "endpoint_providers": ";".join(n for n in names if n),
    }


def _request_columns(payload: dict[str, Any], prompt_text: str, prompt_hash: str) -> dict[str, Any]:
    msgs = payload.get("messages") or []
    system = next((m.get("content") for m in msgs if m.get("role") == "system"), None)
    reasoning = payload.get("reasoning") or {}
    provider = payload.get("provider") or {}
    rf = payload.get("response_format") or {}
    schema = rf.get("json_schema") or {}
    return {
        "prompt_text": prompt_text,
        "prompt_hash": prompt_hash,
        "system_prompt": system,
        "max_tokens": payload.get("max_tokens"),
        "reasoning_effort": reasoning.get("effort"),
        "reasoning_exclude": reasoning.get("exclude"),
        "temperature_sent": payload.get("temperature"),
        "api_seed": payload.get("seed"),
        "api_seed_sent": "seed" in payload,
        "provider_allow_fallbacks": provider.get("allow_fallbacks"),
        "provider_require_parameters": provider.get("require_parameters"),
        "provider_order": ";".join(provider.get("order") or []) or None,
        "response_format_type": rf.get("type"),
        "response_schema_name": schema.get("name"),
        "response_schema_strict": schema.get("strict"),
        "request_payload_json": _json(payload),
    }


def _response_columns(paths: RunPaths, rec: SourceRecord | JudgmentRecord) -> dict[str, Any]:
    out: dict[str, Any] = {
        "response_id": None, "response_object": None, "response_created": None, "system_fingerprint": None,
        "reasoning_text": None, "reasoning_detail_types": None, "reasoning_details_json": None,
        "http_status": None, "response_headers_json": None, "native_finish_reason": None,
        "prompt_tokens": None, "completion_tokens": None, "total_tokens": None, "reasoning_tokens": None,
        "cached_prompt_tokens": None, "audio_tokens": None, "usage_cost": None, "usage_json": None,
    }
    if not rec.raw_response_path:
        return out
    p = paths.raw_dir / rec.raw_response_path
    if not p.exists():
        return out
    try:
        raw = read_json(p)
    except (OSError, ValueError):
        return out
    out["http_status"] = raw.get("status_code")
    out["response_headers_json"] = _json(raw.get("response_headers")) if raw.get("response_headers") else None
    body = raw.get("response_json") or {}
    if not isinstance(body, dict):
        return out
    out["response_id"] = body.get("id")
    out["response_object"] = body.get("object")
    out["response_created"] = body.get("created")
    out["system_fingerprint"] = body.get("system_fingerprint")
    try:
        choice = body["choices"][0]
        msg = choice.get("message") or {}
    except (KeyError, IndexError, TypeError):
        choice, msg = {}, {}
    out["native_finish_reason"] = choice.get("native_finish_reason")
    reasoning = msg.get("reasoning")
    out["reasoning_text"] = reasoning if isinstance(reasoning, str) else (_json(reasoning) if reasoning else None)
    details = msg.get("reasoning_details")
    if details:
        out["reasoning_details_json"] = _json(details)
        types = [d.get("type") for d in details if isinstance(d, dict)]
        out["reasoning_detail_types"] = ";".join(t for t in types if t) or None
    usage = body.get("usage") or {}
    if isinstance(usage, dict):
        out["prompt_tokens"] = usage.get("prompt_tokens")
        out["completion_tokens"] = usage.get("completion_tokens")
        out["total_tokens"] = usage.get("total_tokens")
        out["usage_cost"] = usage.get("cost")
        ctd = usage.get("completion_tokens_details") or {}
        ptd = usage.get("prompt_tokens_details") or {}
        if isinstance(ctd, dict):
            out["reasoning_tokens"] = ctd.get("reasoning_tokens")
            out["audio_tokens"] = ctd.get("audio_tokens")
        if isinstance(ptd, dict):
            out["cached_prompt_tokens"] = ptd.get("cached_tokens")
        out["usage_json"] = _json(usage)
    return out


def _common_call_columns(rec: SourceRecord | JudgmentRecord, kind: str, record_id: str, label: str,
                         provider_pin: str | None) -> dict[str, Any]:
    return {
        "call_kind": kind,
        "record_id": record_id,
        "model_label": label,
        "requested_model_id": rec.requested_model_id,
        "returned_model_id": rec.returned_model_id,
        "provider": rec.provider,
        "provider_pin": provider_pin,
        "attempt_number": rec.attempt_number,
        "replacement_for": rec.replacement_for,
        "valid": rec.valid,
        "invalid_reason": rec.invalid_reason,
        "error": rec.error,
        "request_id": rec.request_id,
        "started_at": rec.started_at,
        "completed_at": rec.completed_at,
        "latency_ms": rec.latency_ms,
        "call_attempts": rec.call_attempts,
        "finish_reason": rec.finish_reason,
        "reported_cost_usd": rec.reported_cost,
        "estimated_cost_usd": rec.estimated_cost,
        "raw_completion": rec.raw_completion,
        "raw_response_path": rec.raw_response_path,
    }


def flatten_run(cfg: PilotConfig, paths: RunPaths) -> dict[str, pd.DataFrame]:
    manifest = load_manifest(paths)
    run_cols = _run_columns(cfg, manifest)
    pins = {label: m.provider for label, m in cfg.models.items()}
    sources = read_jsonl(paths.source_calls, SourceRecord)
    judgments = read_jsonl(paths.judgment_calls, JudgmentRecord)
    preflight = read_jsonl(paths.preflight_calls, JudgmentRecord)
    trials: list[TrialRecord] = load_trials(paths) if paths.trials_json.exists() else []
    build_info = ((manifest.get("phases") or {}).get("build_trials") or {}).get("per_judge") or {}
    source_by_id = {r.sample_id: r for r in sources}
    trial_by_id = {t.trial_id: t for t in trials}
    attempts_per_trial: dict[str, int] = {}
    for r in judgments:
        attempts_per_trial[r.trial_id] = attempts_per_trial.get(r.trial_id, 0) + 1
    alphabet = cfg.generation.alphabet

    # ---- sources
    src_rows: list[dict[str, Any]] = []
    for r in sources:
        row = dict(run_cols)
        row.update(_common_call_columns(r, "source", r.sample_id, r.source_model_label, pins.get(r.source_model_label)))
        row.update(_request_columns(r.request_payload_sanitized, r.prompt_text, r.prompt_hash))
        row.update(_response_columns(paths, r))
        row.update(_catalog_columns(manifest, r.source_model_label))
        row["parsed_string"] = r.parsed_string
        row["parsed_judgment"] = None
        row["correct"] = None
        if r.valid and r.parsed_string:
            d = string_diagnostics(r.parsed_string, alphabet)
            a, b = alphabet[0], alphabet[1]
            row.update({
                "length": d["length"], "prop_H": d[f"prop_{a}"], "alternation_rate": d["alternation_rate"],
                "n_runs": d["n_runs"], "expected_runs": d["expected_runs"], "runs_test_z": d["runs_test_z"],
                "runs_test_p": d["runs_test_p"], "longest_run": d["longest_run"], "first_outcome": d["first_outcome"],
                "bigram_HH": d[f"bigram_{a}{a}"], "bigram_HT": d[f"bigram_{a}{b}"],
                "bigram_TH": d[f"bigram_{b}{a}"], "bigram_TT": d[f"bigram_{b}{b}"],
            })
        src_rows.append(row)

    # ---- judgments (and preflight)
    def judgment_row(r: JudgmentRecord, kind: str) -> dict[str, Any]:
        row = dict(run_cols)
        row.update(_common_call_columns(r, kind, r.judgment_id, r.judge_model_label, pins.get(r.judge_model_label)))
        prompt_text = next((m.get("content") for m in r.request_payload_sanitized.get("messages", [])
                            if m.get("role") == "user"), None)
        row.update(_request_columns(r.request_payload_sanitized, prompt_text or "", r.prompt_hash))
        row.update(_response_columns(paths, r))
        row.update(_catalog_columns(manifest, r.judge_model_label))
        row["response_mode"] = r.response_mode
        row["parsed_string"] = None
        row["parsed_judgment"] = r.parsed_judgment
        row["correct"] = r.correct
        t = trial_by_id.get(r.trial_id)
        if t is not None:
            s1, s2 = source_by_id.get(t.source_1_sample_id), source_by_id.get(t.source_2_sample_id)
            binfo = build_info.get(t.judge_model_label) or {}
            row.update({
                "trial_id": t.trial_id, "judge_model_label": t.judge_model_label, "trial_position": t.trial_position,
                "analytical_cell": t.analytical_cell, "subcell": t.subcell, "correct_answer": t.correct_answer,
                "source_pair": "-".join(sorted([t.source_1_model_label, t.source_2_model_label])),
                "source_1_model_label": t.source_1_model_label, "source_2_model_label": t.source_2_model_label,
                "source_1_sample_id": t.source_1_sample_id, "source_2_sample_id": t.source_2_sample_id,
                "display_order": t.display_order, "construction_seed": t.construction_seed,
                "build_attempts": binfo.get("attempts"), "order_max_cell_run": binfo.get("max_cell_run"),
                "order_max_answer_run": binfo.get("max_answer_run"),
                "stimulus_hash": t.stimulus_hash, "display_alphabet": cfg.judgment.display_alphabet,
                "string_1_display": t.string_1_display, "string_2_display": t.string_2_display,
                "string_1_canonical": s1.parsed_string if s1 else None,
                "string_2_canonical": s2.parsed_string if s2 else None,
                "source_1_returned_model_id": s1.returned_model_id if s1 else None,
                "source_1_provider": s1.provider if s1 else None,
                "source_1_request_id": s1.request_id if s1 else None,
                "source_1_completed_at": s1.completed_at if s1 else None,
                "source_2_returned_model_id": s2.returned_model_id if s2 else None,
                "source_2_provider": s2.provider if s2 else None,
                "source_2_request_id": s2.request_id if s2 else None,
                "source_2_completed_at": s2.completed_at if s2 else None,
                "n_attempts_for_trial": attempts_per_trial.get(t.trial_id),
            })
        else:
            row["trial_id"] = r.trial_id
            row["judge_model_label"] = r.judge_model_label
        return row

    jud_rows = [judgment_row(r, "judgment") for r in judgments]
    pre_rows = [judgment_row(r, "preflight") for r in preflight]

    all_columns = (RUN_COLUMNS + CALL_COLUMNS + ["response_mode"] + REQUEST_COLUMNS + RESPONSE_COLUMNS
                   + USAGE_COLUMNS + CATALOG_COLUMNS + TRIAL_COLUMNS + DIAG_COLUMNS)
    all_columns = list(dict.fromkeys(all_columns))  # de-duplicate, keep order

    def frame(rows: list[dict[str, Any]], columns: list[str]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame(columns=columns)
        return pd.DataFrame(rows).reindex(columns=columns)

    src_cols = [c for c in all_columns if c not in TRIAL_COLUMNS and c not in ("response_mode", "parsed_judgment", "correct")]
    jud_cols = [c for c in all_columns if c not in DIAG_COLUMNS and c != "parsed_string"]
    trials_df = pd.DataFrame([t.model_dump() for t in trials])
    if len(trials_df):
        trials_df.insert(0, "run_seed", run_cols["run_seed"])
    return {
        "calls_all": frame(src_rows + pre_rows + jud_rows, all_columns),
        "sources": frame(src_rows, src_cols),
        "judgments": frame(jud_rows, jud_cols),
        "preflight": frame(pre_rows, jud_cols),
        "trials": trials_df,
    }


COLUMN_DOC = """# Column dictionary for the flat CSV exports

One row per API call. Every row is self-contained: it carries the run configuration and seeds,
the catalog snapshot for its model, the exact request, the full raw completion, token usage,
response metadata, and (judgment rows) the trial design and the provenance of both strings.
The raw JSONL records and responses/ files remain the canonical data; these CSVs are rebuilt
from them by `summarize` / `export`.

Run: run_id, run_name, run_seed (the seed that fixes every judge's trial construction),
run_created_at, fake_client, config_hash, package_version, harness_git_commit (if the project is
a git checkout), python_version, platform, hostname, generation_prompt_sha256,
judge_prompt_one_word_sha256, judge_prompt_structured_sha256, judgment_response_mode_effective,
judgment_response_mode_reason.

Call: call_kind (source | preflight | judgment), record_id (sample_id or judgment_id),
model_label, requested_model_id, returned_model_id, provider (as served), provider_pin (as
configured), attempt_number, replacement_for (the invalid call this one replaces), valid,
invalid_reason (parser diagnosis or api_error), error, request_id, started_at, completed_at
(UTC), latency_ms, call_attempts (HTTP attempts incl. retries), finish_reason,
native_finish_reason, reported_cost_usd (OpenRouter usage.cost), estimated_cost_usd (token
usage x catalog price; used for budgeting when no cost is reported). response_mode (judgment
and preflight rows).

Request: prompt_text (exact user message), prompt_hash (sha256), system_prompt, max_tokens,
reasoning_effort, reasoning_exclude, temperature_sent (empty when no temperature was sent),
api_seed and api_seed_sent (the per-call seed is sent only when openrouter.send_seed is on and
the model advertises `seed`; otherwise the column is empty and api_seed_sent is False), provider_allow_fallbacks,
provider_require_parameters, provider_order, response_format_type, response_schema_name,
response_schema_strict, request_payload_json (the complete request body).

Response: raw_completion (verbatim), parsed_string / parsed_judgment, correct, response_id,
response_object, response_created, system_fingerprint, reasoning_text and
reasoning_details_json / reasoning_detail_types (present only if reasoning is not excluded),
http_status, response_headers_json (x-* headers), raw_response_path.

Usage: prompt_tokens, completion_tokens, total_tokens, reasoning_tokens
(completion_tokens_details.reasoning_tokens when the route reports it; reasoning tokens are
billed as completion tokens), cached_prompt_tokens, audio_tokens, usage_cost, usage_json.

Catalog snapshot at run start: catalog_fetched_at, catalog_name, catalog_created,
canonical_slug, context_length, price_prompt_per_token, price_completion_per_token,
price_internal_reasoning_per_token (USD per token), supported_parameters, endpoint_providers.

Trial (judgment rows): trial_id, judge_model_label, trial_position (presentation order 1..24),
analytical_cell (A-D), subcell (B:<other>, C:<other>), correct_answer, source_pair (unordered
model pair), source_1/2_model_label,
source_1/2_sample_id, display_order (orig | flipped relative to the canonical pair order),
construction_seed (<run_seed>:<judge>), build_attempts (construction attempts before all
constraints were met), order_max_cell_run, order_max_answer_run, stimulus_hash,
display_alphabet, string_1/2_display (exactly as shown), string_1/2_canonical (H/T source
strings), source_1/2_returned_model_id, _provider, _request_id, _completed_at (provenance of
each string), n_attempts_for_trial.

String diagnostics (source rows, valid strings only): length, prop_H, alternation_rate
(switches / 49), n_runs, expected_runs, runs_test_z, runs_test_p (Wald-Wolfowitz, two-sided
normal approximation), longest_run, first_outcome, bigram_HH/HT/TH/TT (counts over 49 bigrams).
"""


def export_run(cfg: PilotConfig, paths: RunPaths) -> dict[str, Any]:
    frames = flatten_run(cfg, paths)
    paths.derived_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, df in frames.items():
        out = paths.derived_dir / f"{name}.csv"
        df.to_csv(out, index=False)
        written[name] = out
    (paths.derived_dir / "columns.md").write_text(COLUMN_DOC, encoding="utf-8")
    return {"files": written, "frames": frames}
