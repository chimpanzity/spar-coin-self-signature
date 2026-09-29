"""Judgment call handling — one call per trial, up to JUDGMENT_MAX_ATTEMPTS invalid-response retries.

Uses structured JSON output by default; falls back to plain-text SAME/DIFFERENT if
a preflight indicates structured output is not supported for a given judge.
"""

import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from openai import OpenAI

from . import config as C
from .api import (APIResult, CostAccountant, call_model,
                  parse_judgment_json, parse_judgment_text)
from .state import RunPaths, read_json, write_json
from .trials import Trial


@dataclass
class JudgmentRecord:
    trial_id: str
    judge_label: str
    architecture: str
    cell: str
    correct_answer: str
    source_model_1: str
    source_model_2: str
    trajectory_id_1: str
    trajectory_id_2: str
    display_string_1: str
    display_string_2: str
    prompt_text: str
    raw_response: str
    parsed_judgment: str
    correct: Optional[bool]
    response_mode: str
    attempts: int
    total_cost_usd: float
    served_model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    finish_reason: str
    latency_ms: int
    error_message: str
    call_utc: str


def _judgment_prompt(t: Trial, mode: str) -> str:
    tmpl = (C.JUDGMENT_PROMPT_TEMPLATE if mode == "json_schema"
            else C.JUDGMENT_FALLBACK_PROMPT_TEMPLATE)
    return tmpl.format(string_1=t.display_string_1, string_2=t.display_string_2)


def judge_one_trial(client: OpenAI, accountant: CostAccountant,
                    trial: Trial, judge_slug: str, response_mode: str) -> JudgmentRecord:
    prompt = _judgment_prompt(trial, response_mode)
    response_format = None
    if response_mode == "json_schema":
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": "judgment_response",
                            "strict": True,
                            "schema": C.JUDGMENT_JSON_SCHEMA},
        }
    total_cost = 0.0
    last: APIResult = None
    parsed = None
    attempts = 0
    for attempt in range(1, C.JUDGMENT_MAX_ATTEMPTS + 1):
        res = call_model(client, accountant,
                         kind="judgment", slug=judge_slug,
                         prompt_text=prompt,
                         max_tokens=C.JUDGMENT_MAX_TOKENS,
                         response_format=response_format)
        total_cost += res.cost_usd
        last = res
        attempts = attempt
        if response_mode == "json_schema":
            parsed = parse_judgment_json(res.response_text)
        else:
            parsed = parse_judgment_text(res.response_text)
        if parsed is not None:
            break
    correct = None
    if parsed is not None:
        correct = (parsed == trial.correct_answer)
    return JudgmentRecord(
        trial_id=trial.trial_id, judge_label=trial.judge_label,
        architecture=trial.architecture, cell=trial.cell,
        correct_answer=trial.correct_answer,
        source_model_1=trial.source_model_1, source_model_2=trial.source_model_2,
        trajectory_id_1=trial.trajectory_id_1, trajectory_id_2=trial.trajectory_id_2,
        display_string_1=trial.display_string_1, display_string_2=trial.display_string_2,
        prompt_text=prompt, raw_response=last.response_text if last else "",
        parsed_judgment=parsed or "",
        correct=correct,
        response_mode=response_mode,
        attempts=attempts,
        total_cost_usd=total_cost,
        served_model=last.served_model if last else "",
        provider=last.provider if last else "",
        prompt_tokens=last.prompt_tokens if last else 0,
        completion_tokens=last.completion_tokens if last else 0,
        reasoning_tokens=last.reasoning_tokens if last else 0,
        finish_reason=last.finish_reason if last else "",
        latency_ms=last.latency_ms if last else 0,
        error_message=last.error_message if last else "",
        call_utc=last.call_utc if last else "",
    )


def preflight_response_mode(client: OpenAI, accountant: CostAccountant,
                            judge_slugs: List[str], log=print) -> str:
    """Try structured output on each judge with a dummy pair. If any fails,
    fall back to plain-text SAME/DIFFERENT for ALL judges (per spec)."""
    dummy_s1 = "H" * 25 + "T" * 25
    dummy_s2 = "T" * 25 + "H" * 25
    for slug in judge_slugs:
        prompt = C.JUDGMENT_PROMPT_TEMPLATE.format(string_1=dummy_s1, string_2=dummy_s2)
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": "judgment_response",
                            "strict": True,
                            "schema": C.JUDGMENT_JSON_SCHEMA},
        }
        res = call_model(client, accountant, kind="smoke", slug=slug,
                         prompt_text=prompt, max_tokens=C.JUDGMENT_MAX_TOKENS,
                         response_format=response_format,
                         max_transport_retries=2)
        parsed = parse_judgment_json(res.response_text)
        if parsed is None:
            log(f"  preflight: {slug} structured-output FAILED "
                f"(raw={res.response_text[:80]!r}); falling back to plain text")
            return "chat"
        log(f"  preflight: {slug} structured-output ok ({parsed})")
    return "json_schema"
