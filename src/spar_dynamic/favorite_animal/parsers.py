"""Parsers for FAVORITE_ANIMAL_v1.0.

Phase 1 / Phase 2B parser (`parse_animal`):
  Accept a short response that looks like an animal common-name.
  Rules:
    - Normalize: strip whitespace, strip surrounding quotes, strip trailing
      ".", lowercase.
    - Must consist only of letters, spaces, and hyphens.
    - Must contain at least two alphabetic letters (spec §3 "minimum name
      length": all four queried positions must be defined).
    - Must not contain commas, semicolons, or newlines (reject multi-animal
      lists and explanatory prose).
    - Must not contain any digits.
  Scoring string = normalized name with spaces and hyphens removed.

Phase 2A parser (`parse_letter`):
  Accept exactly one alphabetic letter, case-insensitive.
  Classify valid / prefix_leak / decline / invalid.
  Preserve raw.

Response-category constants + a `is_truncated` helper match the v4.1 shape.
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
class AnimalParse:
    valid: bool
    raw: str                           # exact raw response, pre-normalization
    normalized_name: Optional[str]     # lowercase, spaces/hyphens preserved
    scoring_string: Optional[str]      # letters only (spaces + hyphens removed)
    reason: str
    had_trailing_punct: bool


# A short "clean animal response" is one or more lowercase words of letters,
# optionally hyphen-joined, separated by single spaces. No commas / periods
# (apart from an allowed trailing one, which we strip up front) / newlines
# / digits.
_ANIMAL_RE = re.compile(r"^[a-z]+(?:[-\s][a-z]+)*$")


_SURROUND_QUOTES = ("\"", "'", "‘", "’", "“", "”")


def parse_animal(text: str) -> AnimalParse:
    raw = text or ""
    s = raw.strip()
    if not s:
        return AnimalParse(False, raw, None, None, "empty", False)
    had_trailing = s.endswith(".") or s.endswith(",")
    # Peel surrounding whitespace, quotes, and terminal punctuation iteratively
    # so '"octopus".' and '."octopus"' and 'octopus.' all land on 'octopus'.
    for _ in range(8):
        prev = s
        s = s.strip()
        for q in _SURROUND_QUOTES:
            if s.startswith(q): s = s[1:]
            if s.endswith(q): s = s[:-1]
        s = s.rstrip(".,").strip()
        if s == prev: break
    s_core = s
    if not s_core:
        return AnimalParse(False, raw, None, None, "empty_after_strip", had_trailing)
    # Reject anything with a newline (lists / explanations typically multi-line)
    if "\n" in s_core:
        return AnimalParse(False, raw, None, None, "multi-line", had_trailing)
    # Reject commas and semicolons (lists)
    if "," in s_core or ";" in s_core:
        return AnimalParse(False, raw, None, None, "comma_or_semicolon", had_trailing)
    # Reject digits
    if any(c.isdigit() for c in s_core):
        return AnimalParse(False, raw, None, None, "contains_digits", had_trailing)
    lowered = s_core.lower()
    # Collapse multiple spaces (preserve single internal spaces)
    normalized = re.sub(r"\s+", " ", lowered)
    if not _ANIMAL_RE.fullmatch(normalized):
        return AnimalParse(False, raw, None, None, "non_letter_characters", had_trailing)
    # Reject responses that look like explanatory prose. Common English animal
    # names rarely exceed 5 space-separated words ("northern white-faced owl"
    # is 3 tokens; "blue-footed booby" is 2). Longer responses are explanations.
    tokens = normalized.split()
    if len(tokens) > 5:
        return AnimalParse(False, raw, None, None, "too_many_words", had_trailing)
    # Reject responses starting with an article/possessive (spec: "respond
    # with only the common English name"; "the octopus" / "my favorite" are
    # not themselves animal names).
    if tokens and tokens[0] in {"the", "a", "an", "my", "i", "its"}:
        return AnimalParse(False, raw, None, None, "starts_with_article", had_trailing)
    # Scoring string: strip spaces and hyphens
    scoring = re.sub(r"[-\s]", "", normalized)
    if len(scoring) < 2:
        return AnimalParse(False, raw, None, None, "too_short", had_trailing)
    return AnimalParse(True, raw, normalized, scoring, "", had_trailing)


# Phase 2B reuses the same parser as Phase 1.
parse_phase1 = parse_animal
parse_phase2b = parse_animal


# ---------------------------------------------------------------- Phase 2A --

@dataclass(frozen=True)
class LetterParse:
    category: str                      # "valid" | "prefix_leak" | "decline" | "invalid"
    letter: Optional[str]              # lowercase single letter when valid
    reason: str
    extracted_letters: List[str]       # letters surfaced from the response


# Reuse the dice-pilot decline regex (U+2019 fix applied there).
from spar_dynamic.dice_pilot.parsers import _DECLINE_RE as _DECLINE_RE_DICE   # noqa: E402

_SINGLE_LETTER_RE = re.compile(r"^[A-Za-z]$")
# A "bare letter token" in prose: a single letter not adjacent to another alpha.
_LETTER_TOKEN_RE = re.compile(r"(?<![A-Za-z])([A-Za-z])(?![A-Za-z])")
# A contiguous word (>=2 letters) somewhere in the response — likely a prefix leak
# of the animal's name.
_CONTIGUOUS_WORD_RE = re.compile(r"(?<![A-Za-z])[A-Za-z]{2,}(?![A-Za-z])")


def parse_phase2a(text: str) -> LetterParse:
    raw = text or ""
    s = raw.strip()
    if not s:
        return LetterParse("invalid", None, "empty", [])
    # Peel quotes and trailing punctuation iteratively so '"R".' lands on 'R'.
    for _ in range(8):
        prev = s
        s = s.strip()
        for q in _SURROUND_QUOTES:
            if s.startswith(q): s = s[1:]
            if s.endswith(q): s = s[:-1]
        s = s.rstrip(".,").strip()
        if s == prev: break
    s_core = s
    # Happy path: whole response is exactly one letter
    if _SINGLE_LETTER_RE.fullmatch(s_core):
        return LetterParse("valid", s_core.lower(), "", [s_core.lower()])
    # Decline language takes precedence over prefix-leak classification —
    # a prose refusal naturally contains many letter-words.
    bare = [m.group(1).lower() for m in _LETTER_TOKEN_RE.finditer(raw)]
    if _DECLINE_RE_DICE.search(raw):
        return LetterParse("decline", None, "contains decline/hedge language", bare)
    # Contiguous-word prefix leak: any 2+ letter alphabetic run
    words = _CONTIGUOUS_WORD_RE.findall(raw)
    if words:
        letters = [c.lower() for w in words for c in w]
        return LetterParse("prefix_leak", None,
                           f"contiguous letter word(s) found: {words}", letters)
    # Multiple standalone single letters (e.g. "C, D")
    if len(bare) > 1:
        return LetterParse("prefix_leak", None,
                           f"{len(bare)} bare letter tokens: {bare}", bare)
    # Single bare letter embedded in prose
    if len(bare) == 1:
        return LetterParse("invalid", None,
                           "single letter present but response contains additional text",
                           bare)
    return LetterParse("invalid", None, "no letter token and no decline marker", bare)


# ---------------------------------------------------------------- helpers --

def letter_at(scoring_string: str, position: str) -> Optional[str]:
    """Return the letter at the specified position within `scoring_string`,
    or None if the string is too short."""
    s = scoring_string
    if not s or len(s) < 2: return None
    if position == "first":        return s[0]
    if position == "second":       return s[1]
    if position == "penultimate":  return s[-2]
    if position == "last":         return s[-1]
    raise ValueError(f"unknown position {position!r}")
