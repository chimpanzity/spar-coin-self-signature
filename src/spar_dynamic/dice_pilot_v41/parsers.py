"""Parsers for DICE_PILOT_v4.1.

- Phase 1 and Phase 2C: 10-integer sequence parser (reuse v3.1 Phase 1
  parser; same specification).
- Phase 2A and Phase 2B: single-integer parser (reuse v3.1 Phase 2 parser,
  which already classifies valid / prefix_leak / decline / invalid).
- NEW `truncated` category: spec §3.2 requires that any call ending with
  `finish_reason == "length"` is classified truncated, distinct from an
  ordinary parsing failure. This is applied at orchestration time (we need
  the finish_reason + raw_text), so the parsing module here only defines the
  category constants used elsewhere.
"""

from __future__ import annotations

from spar_dynamic.dice_pilot.parsers import (  # noqa: F401
    Phase1Parse, Phase2Parse, parse_phase1, parse_phase2,
)


# Shared constants
RESPONSE_CATEGORY_VALID = "valid"
RESPONSE_CATEGORY_PREFIX_LEAK = "prefix_leak"
RESPONSE_CATEGORY_DECLINE = "decline"
RESPONSE_CATEGORY_INVALID = "invalid"
RESPONSE_CATEGORY_TRUNCATED = "truncated"      # NEW in v4.1
RESPONSE_CATEGORY_TRANSPORT_ERROR = "transport_error"


def is_truncated(finish_reason: str) -> bool:
    """Spec §3.2: finish_reason == 'length' means the model hit the output cap."""
    return (finish_reason or "").lower() == "length"
