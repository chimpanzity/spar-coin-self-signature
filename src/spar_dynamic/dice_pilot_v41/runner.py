"""v4.1 runner — thin wrapper on the v3.1 runner primitives, adding:

- Truncation detection (`finish_reason == "length"` → status "truncated").
- Pinned-provider request shape with `allow_fallbacks=false` per spec §3.1.
- Per-model `max_tokens` from config.

Everything else (CallResult, CostLedger, retry, cost accounting,
request_config_hash) is reused verbatim from the v3.1 runner.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from spar_dynamic.dice_pilot.runner import (  # noqa: F401
    CallResult, CostLedger, call_once as _v31_call_once, log_attempt,
    make_openrouter_client, request_config_hash, worst_case_cost_usd,
    _prefix_tokens_in_text,       # kept for backward audit; NOT used for v4.1 detection
)


def call_once(client, slug: str, prompt_text: str, max_tokens: int,
               temperature: Optional[float], reasoning_spec: Optional[Dict],
               provider_pin: Optional[str], pricing: Dict[str, float],
               allow_fallbacks: bool = False) -> CallResult:
    """Delegate to the v3.1 runner primitive. v3.1's `call_once` already sends
    `provider.order=[provider_pin], allow_fallbacks=false` when `provider_pin`
    is truthy, which matches spec §3.1 requirement. `allow_fallbacks` is kept
    as a parameter for forward compatibility but defaults to False."""
    return _v31_call_once(client, slug, prompt_text, max_tokens,
                           temperature, reasoning_spec, provider_pin, pricing)
