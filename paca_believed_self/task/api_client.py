"""
api_client.py — OpenRouter wrapper with COMPREHENSIVE metadata capture.

Returns everything the response exposes so no data point is lost:
  choice, response_text, choice_source, latency, retries, error,
  served model id, generation id, provider, finish_reason,
  token usage (prompt/completion/reasoning/total), and the raw sampling params.

choice_source values:
  "model"                - parsed a choice from the model's reply
  "fallback_parse_fail"  - API ok but parser found no TRIANGLE/STAR -> RNG fallback
  "fallback_api_fail"    - all retries exhausted -> RNG fallback
"""

import re, time, random
from dataclasses import dataclass, field
from typing import Optional
from openai import OpenAI

CLIENT_VERSION = "committed-harness-v1"
PARSER_VERSION = "parse_choice-v1"   # bump if parse_choice() logic changes


@dataclass
class APIResult:
    choice: str
    response_text: str
    choice_source: str
    latency_ms: int
    retries_used: int
    error_message: str
    # rich metadata (None/0 when unavailable)
    served_model: str = ""
    generation_id: str = ""
    provider: str = ""
    finish_reason: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    max_tokens_used: int = 0   # the budget actually granted (after any escalation)
    truncated: bool = False    # True iff the final attempt hit finish_reason == "length"


def make_client(api_key: str, timeout: float = 120.0) -> OpenAI:
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key, timeout=timeout)


def parse_choice(text: str) -> Optional[str]:
    if not text:
        return None
    matches = list(re.finditer(r"\b(triangle|star)\b", text, re.IGNORECASE))
    if matches:
        return "T" if matches[-1].group(1).lower() == "triangle" else "S"
    lines = [ln.strip() for ln in text.split("\n")]
    nonempty = [ln for ln in lines if ln]
    if nonempty:
        clean = re.sub(r"[^\w]+$", "", nonempty[-1]).strip()
        if clean.upper() in ("T", "S") and len(clean) == 1:
            return clean.upper()
    cands = [re.sub(r"[^\w]+$", "", ln).strip().upper() for ln in lines]
    cands = [c for c in cands if c in ("T", "S")]
    return cands[-1] if cands else None


def _extract_usage(response):
    pt = ct = rt = tt = 0
    u = getattr(response, "usage", None)
    if u is not None:
        pt = getattr(u, "prompt_tokens", 0) or 0
        ct = getattr(u, "completion_tokens", 0) or 0
        tt = getattr(u, "total_tokens", 0) or 0
        details = getattr(u, "completion_tokens_details", None)
        if details is not None:
            rt = getattr(details, "reasoning_tokens", 0) or 0
    return pt, ct, rt, tt


def call_model(client, model, system_prompt, user_prompt,
               temperature=0.0, max_tokens=20000, top_p=None,
               max_retries=3, rng=None,
               escalate_on_truncation=True, max_tokens_ceiling=80000,
               parse_fn=None) -> APIResult:
    """
    Truncation-aware. If a call finishes with finish_reason == "length" and no
    parseable choice (the model spent its budget reasoning), the SAME trial is
    retried with a doubled token budget, up to max_tokens_ceiling. A choice that
    fails only because the budget ran out is NEVER silently coin-substituted:
    it is returned as choice_source == "fallback_truncation" with truncated=True,
    so the caller can flag/abort instead of poisoning the game with a fake choice.

    choice_source outcomes:
      "model"                - parsed a real choice
      "fallback_truncation"  - hit "length" even at the ceiling; NOT a real choice
      "fallback_parse_fail"  - finished normally (stop) but no parseable action
      "fallback_api_fail"    - network/API errors exhausted retries
    """
    if rng is None:
        rng = random
    if parse_fn is None:
        parse_fn = parse_choice   # default parser; supplemental conditions inject a label-aware one
    start = time.time()
    last_error = ""
    cur_max = max_tokens

    while True:  # token-escalation loop (bounded by the ceiling)
        for attempt in range(max_retries):  # network-retry loop
            try:
                kwargs = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": cur_max,
                }
                if temperature is not None:
                    kwargs["temperature"] = temperature
                if top_p is not None:
                    kwargs["top_p"] = top_p

                response = client.chat.completions.create(**kwargs)
                latency_ms = int((time.time() - start) * 1000)
                response_text = (response.choices[0].message.content or "")
                finish_reason = getattr(response.choices[0], "finish_reason", "") or ""
                served_model = getattr(response, "model", "") or ""
                generation_id = getattr(response, "id", "") or ""
                provider = getattr(response, "provider", "") or ""
                pt, ct, rt, tt = _extract_usage(response)
                choice = parse_fn(response_text)

                if choice is not None:
                    return APIResult(
                        choice=choice, response_text=response_text, choice_source="model",
                        latency_ms=latency_ms, retries_used=attempt, error_message="",
                        served_model=served_model, generation_id=generation_id, provider=provider,
                        finish_reason=finish_reason, prompt_tokens=pt, completion_tokens=ct,
                        reasoning_tokens=rt, total_tokens=tt, max_tokens_used=cur_max,
                        truncated=(finish_reason == "length"))

                # No parseable choice. Was it truncation?
                if finish_reason == "length":
                    if escalate_on_truncation and cur_max < max_tokens_ceiling:
                        cur_max = min(cur_max * 2, max_tokens_ceiling)
                        break  # re-enter the while-loop with a bigger budget
                    # Unrecoverable truncation — DO NOT coin-substitute silently.
                    return APIResult(
                        choice="", response_text=response_text, choice_source="fallback_truncation",
                        latency_ms=latency_ms, retries_used=attempt,
                        error_message=f"truncated at max_tokens={cur_max} (finish_reason=length)",
                        served_model=served_model, generation_id=generation_id, provider=provider,
                        finish_reason=finish_reason, prompt_tokens=pt, completion_tokens=ct,
                        reasoning_tokens=rt, total_tokens=tt, max_tokens_used=cur_max, truncated=True)

                # Finished normally (stop) but unparseable — genuine non-answer; coin + flag.
                fallback = "T" if rng.random() < 0.5 else "S"
                return APIResult(
                    choice=fallback, response_text=response_text, choice_source="fallback_parse_fail",
                    latency_ms=latency_ms, retries_used=attempt,
                    error_message="no parseable action despite finish_reason=" + finish_reason,
                    served_model=served_model, generation_id=generation_id, provider=provider,
                    finish_reason=finish_reason, prompt_tokens=pt, completion_tokens=ct,
                    reasoning_tokens=rt, total_tokens=tt, max_tokens_used=cur_max, truncated=False)

            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                if attempt < max_retries - 1:
                    time.sleep(2 ** (attempt + 1))
                    continue
                # network retries exhausted
                latency_ms = int((time.time() - start) * 1000)
                fallback = "T" if rng.random() < 0.5 else "S"
                return APIResult(
                    choice=fallback, response_text="", choice_source="fallback_api_fail",
                    latency_ms=latency_ms, retries_used=max_retries - 1,
                    error_message=last_error, max_tokens_used=cur_max)
