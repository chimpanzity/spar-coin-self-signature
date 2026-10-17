"""Parsers for FAVORITE_INTEGER_v1.0.

- Phase 1 / Phase 2B parser: accept exactly 10 digits, first digit 1-9, rest
  0-9. Preserve as a 10-character string, NOT an int (prevents accidental
  formatting changes). Reject internal spaces, separators, or prose.
- Phase 2A parser: accept exactly one digit. 1-9 at position 1; 0-9 at the
  other target positions. Classify valid / prefix_leak / decline / invalid.

Response-category constants plus a truncation helper match the v4.1 shape
so the orchestrator can use the same classification pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


# Shared category constants
RESPONSE_CATEGORY_VALID = "valid"
RESPONSE_CATEGORY_PREFIX_LEAK = "prefix_leak"
RESPONSE_CATEGORY_DECLINE = "decline"
RESPONSE_CATEGORY_INVALID = "invalid"
RESPONSE_CATEGORY_TRUNCATED = "truncated"


def is_truncated(finish_reason: str) -> bool:
    return (finish_reason or "").lower() == "length"


# ---------------------------------------------------------------- Phase 1 / 2B --

@dataclass(frozen=True)
class IntegerParse:
    valid: bool
    integer_str: Optional[str]       # exactly 10 chars when valid; preserved as string
    reason: str                       # empty when valid
    had_trailing_punct: bool
    raw_token_count: int


_INT_STR_RE = re.compile(r"^[1-9][0-9]{9}$")


def parse_phase1(text: str) -> IntegerParse:
    """Accept exactly 10 digits, first in 1-9, rest in 0-9. Preserve as str."""
    s = (text or "").strip()
    if not s:
        return IntegerParse(False, None, "empty", False, 0)
    had_trailing = s.endswith(".")
    s_core = s.rstrip(".").strip()
    # Reject any whitespace, comma, or non-digit character inside the integer
    if _INT_STR_RE.fullmatch(s_core):
        return IntegerParse(True, s_core, "", had_trailing, len(s_core))
    # Specific failure reasons
    if re.fullmatch(r"[0-9]+", s_core) is None:
        return IntegerParse(False, None, "contains non-digit characters",
                            had_trailing, len(s_core))
    if len(s_core) != 10:
        return IntegerParse(False, None, f"length={len(s_core)}, expected 10",
                            had_trailing, len(s_core))
    if s_core[0] == "0":
        return IntegerParse(False, None, "leading zero", had_trailing, 10)
    return IntegerParse(False, None, "unknown parse failure",
                        had_trailing, len(s_core))


# ---------------------------------------------------------------- Phase 2A --

@dataclass(frozen=True)
class DigitParse:
    category: str                      # "valid" | "prefix_leak" | "decline" | "invalid"
    digit: Optional[int]
    reason: str
    extracted_digits: List[int]


# Reuse the v3.1 decline regex (with the typographic-apostrophe fix applied there).
# Importing avoids drift; the decline language is identical in meaning.
from spar_dynamic.dice_pilot.parsers import _DECLINE_RE as _DECLINE_RE_DICE   # noqa: E402

_SINGLE_DIGIT_RE = re.compile(r"^[0-9]$")
# A single digit NOT adjacent to another alphanumeric character — picks up a
# token appearing inside prose but not embedded in a word like "2nd".
_INT_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])([0-9])(?![0-9A-Za-z])")
# A contiguous run of >=2 digits (e.g. "3141592653") — the natural way the
# favorite-integer prompt elicits a prefix leak since Phase 1 forbids spaces.
_CONTIGUOUS_DIGITS_RE = re.compile(r"(?<![A-Za-z0-9])[0-9]{2,}(?![A-Za-z0-9])")


def parse_phase2a(text: str, position: int) -> DigitParse:
    """Classify a Phase-2A response.

    `position` is 1 / 2 / 5 / 9 (1-indexed). At position 1 a valid answer
    must be 1-9; at others any 0-9.
    """
    raw = text or ""
    s = raw.strip()
    if not s:
        return DigitParse("invalid", None, "empty", [])
    # Happy path: whole response is a single digit (optional trailing period).
    s_core = s.rstrip(".").strip()
    if _SINGLE_DIGIT_RE.fullmatch(s_core):
        d = int(s_core)
        if position == 1 and d == 0:
            return DigitParse("invalid", None, "leading zero at position 1", [d])
        return DigitParse("valid", d, "", [d])
    # First: contiguous-digit prefix leak (e.g. "3141592653") — the natural
    # way the favorite-integer prompt elicits a leaked integer.
    contiguous = _CONTIGUOUS_DIGITS_RE.findall(raw)
    if contiguous:
        all_digits = [int(d) for run in contiguous for d in run]
        return DigitParse("prefix_leak", None,
                          f"contiguous digit run(s) found: {contiguous}", all_digits)
    # Collect every standalone 0-9 token in the raw text
    digits = [int(m.group(1)) for m in _INT_TOKEN_RE.finditer(raw)]
    # Prefix leak: more than one standalone digit token
    if len(digits) > 1:
        return DigitParse("prefix_leak", None,
                          f"{len(digits)} digit tokens found: {digits}", digits)
    # Decline language
    if _DECLINE_RE_DICE.search(raw):
        return DigitParse("decline", None, "contains decline/hedge language", digits)
    # Single digit embedded in prose
    if len(digits) == 1:
        return DigitParse("invalid", None,
                          "single digit present but response contains additional text",
                          digits)
    return DigitParse("invalid", None, "no digit token and no decline marker", digits)


# Phase 2B uses the same parser as Phase 1 (whole 10-digit integer).
parse_phase2b = parse_phase1
