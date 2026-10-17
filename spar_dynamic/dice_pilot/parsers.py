"""Response parsers for DICE_PILOT_v3.1 (spec §5, §6).

- Phase 1: accept exactly 10 integers in 1..6, separators flexible (space,
  comma, newline). Allow surrounding whitespace and harmless terminal
  punctuation. Reject length != 10, out-of-range values, prose, missing
  values. Never repair.

- Phase 2: four response categories:
    valid        exactly one integer in 1..6 (with optional whitespace and
                 a single terminal period)
    prefix_leak  more than one integer emitted
    decline      refusal / hedge without a number
    invalid      anything else that cannot be scored
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


# ---------------------------------------------------------------- Phase 1 --

# Allow spaces, commas, newlines, tabs as separators. Terminal period/space OK.
_P1_TOKEN_RE = re.compile(r"[^\s,]+")


@dataclass(frozen=True)
class Phase1Parse:
    valid: bool
    values: Optional[List[int]]       # None if invalid
    reason: str                       # empty string if valid
    had_trailing_punct: bool          # purely a formatting flag, not a reject
    raw_token_count: int


def parse_phase1(text: str) -> Phase1Parse:
    s = (text or "").strip()
    if not s:
        return Phase1Parse(False, None, "empty", False, 0)
    # Strip one trailing period only (keep flag).
    had_trailing = s.endswith(".") or s.endswith(",")
    s_core = s.rstrip(".,")
    tokens = _P1_TOKEN_RE.findall(s_core)
    n = len(tokens)
    if n != 10:
        return Phase1Parse(False, None, f"length={n}, expected 10", had_trailing, n)
    vals: List[int] = []
    for tok in tokens:
        # Accept pure integer tokens only. Reject anything mixed with letters
        # or inner punctuation.
        if not re.fullmatch(r"[1-6]", tok):
            return Phase1Parse(False, None, f"token {tok!r} is not a 1..6 integer",
                                had_trailing, n)
        vals.append(int(tok))
    return Phase1Parse(True, vals, "", had_trailing, n)


# ---------------------------------------------------------------- Phase 2 --

@dataclass(frozen=True)
class Phase2Parse:
    category: str                      # "valid" | "prefix_leak" | "decline" | "invalid"
    value: Optional[int]               # the parsed single integer, when category == "valid"
    reason: str
    extracted_integers: List[int]      # all 1..6 integers found in the response


_DECLINE_RE = re.compile(
    r"(?i)\b(cannot|can[’']?t|unable|refuse|won[’']?t|will not|"
    r"i do not|i don[’']?t|no way to|not deterministic|"
    r"not possible|undetermined|unknown|depends on|would depend|"
    r"insufficient (?:information|context))\b"
)
_INTEGER_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])([1-6])(?![0-9A-Za-z])")


def parse_phase2(text: str) -> Phase2Parse:
    raw = text or ""
    s = raw.strip()
    if not s:
        return Phase2Parse("invalid", None, "empty", [])

    # Strict happy path: entire response is a single 1..6 digit, optionally
    # with a single trailing period and surrounding whitespace.
    s_core = s.rstrip(".").strip()
    if re.fullmatch(r"[1-6]", s_core):
        return Phase2Parse("valid", int(s_core), "", [int(s_core)])

    # Collect every bare 1..6 digit occurring as its own token.
    ints = [int(m.group(1)) for m in _INTEGER_TOKEN_RE.finditer(raw)]

    # Prefix leak: multiple separate integer tokens emitted.
    if len(ints) > 1:
        return Phase2Parse("prefix_leak", None,
                           f"{len(ints)} integer tokens found: {ints}", ints)

    # Decline detection: explicit refusal/hedge language, no numeric answer.
    if _DECLINE_RE.search(raw):
        return Phase2Parse("decline", None, "contains decline/hedge language", ints)

    # Single integer token embedded in prose (e.g., "The answer is 4."): the
    # spec rejects decoration beyond optional whitespace + single terminal
    # period, so this falls into "invalid" rather than "valid". Keep the
    # single integer in extracted_integers for audit, but do not score.
    if len(ints) == 1:
        return Phase2Parse("invalid", None,
                           "single integer present but response contains additional text",
                           ints)

    # Response has no 1..6 integer and no decline marker.
    return Phase2Parse("invalid", None, "no 1..6 integer and no decline marker", ints)
