"""Strict parsers for source strings and judgments.

Nothing here repairs a response. A response either parses or is recorded as invalid with a
reason, and the raw completion is always kept alongside.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

LABELS = ("SAME", "DIFFERENT")


@dataclass(frozen=True)
class ParseResult:
    value: str | None
    valid: bool
    reason: str | None = None


# ---------------------------------------------------------------- source strings

def parse_source_string(raw: str | None, length: int = 50, alphabet: str = "HT") -> ParseResult:
    """Accept only ^[<alphabet>]{length}$ after trimming leading/trailing whitespace."""
    if raw is None:
        return ParseResult(None, False, "empty_completion")
    text = raw.strip()
    if text == "":
        return ParseResult(None, False, "empty_completion")
    pattern = re.compile(rf"^[{re.escape(alphabet)}]{{{length}}}$")
    if pattern.fullmatch(text):
        return ParseResult(text, True, None)
    # Diagnose why, for the invalid_reason field (the raw completion is kept regardless).
    bad_chars = sorted({c for c in text if c not in alphabet})
    if bad_chars:
        shown = "".join(bad_chars)[:20]
        return ParseResult(None, False, f"disallowed_characters:{shown!r}")
    return ParseResult(None, False, f"wrong_length:{len(text)}")


# ---------------------------------------------------------------- judgments

_EDGE_JUNK = " \t\r\n\"'`*_.!?:;,()[]{}"


def _normalize_one_word(text: str) -> str:
    return text.strip(_EDGE_JUNK).upper()


def parse_judgment_one_word(raw: str | None, lenient: bool = False) -> ParseResult:
    """Parse a plain-text SAME / DIFFERENT answer.

    Strict: after stripping surrounding whitespace, quotes, markdown emphasis and terminal
    punctuation, the answer must be exactly one label (case-insensitive).
    Lenient: additionally accept a short reply (<= 12 words) containing exactly one label as a
    standalone word. An answer containing both labels is never accepted.
    """
    if raw is None or raw.strip() == "":
        return ParseResult(None, False, "empty_completion")
    norm = _normalize_one_word(raw)
    if norm in LABELS:
        return ParseResult(norm, True, None)
    upper = raw.upper()
    present = [lab for lab in LABELS if re.search(rf"\b{lab}\b", upper)]
    if len(present) == 2:
        return ParseResult(None, False, "both_labels_present")
    if lenient and len(present) == 1 and len(raw.split()) <= 12:
        if re.search(r"\b(not|no|never)\b|n't", raw, flags=re.IGNORECASE):
            return ParseResult(None, False, "negated_label")
        return ParseResult(present[0], True, None)
    if len(present) == 1:
        return ParseResult(None, False, "label_embedded_in_extra_text")
    return ParseResult(None, False, "no_label")


def parse_judgment_structured(raw: str | None, lenient: bool = False) -> ParseResult:
    """Parse a JSON object {"judgment": "SAME" | "DIFFERENT"}.

    Accepts surrounding whitespace and a ```json fence (some routes add one despite strict
    mode); the object itself must have exactly the expected shape. If the content is not JSON
    at all and lenient is set, the one-word parser is tried as a last resort and the reason
    records that fallback.
    """
    if raw is None or raw.strip() == "":
        return ParseResult(None, False, "empty_completion")
    text = raw.strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        if lenient:
            fallback = parse_judgment_one_word(raw, lenient=True)
            if fallback.valid:
                return ParseResult(fallback.value, True, "lenient_non_json_fallback")
        return ParseResult(None, False, "not_json")
    if not isinstance(obj, dict):
        return ParseResult(None, False, "json_not_object")
    if set(obj.keys()) != {"judgment"}:
        return ParseResult(None, False, f"unexpected_keys:{sorted(obj.keys())}")
    val = obj["judgment"]
    if not isinstance(val, str):
        return ParseResult(None, False, "judgment_not_string")
    norm = val.strip().upper()
    if norm in LABELS:
        return ParseResult(norm, True, None)
    return ParseResult(None, False, f"judgment_not_in_enum:{val!r}")


def parse_judgment(raw: str | None, response_mode: str, lenient: bool = False) -> ParseResult:
    if response_mode == "structured":
        return parse_judgment_structured(raw, lenient=lenient)
    if response_mode == "one_word":
        return parse_judgment_one_word(raw, lenient=lenient)
    raise ValueError(f"unknown response_mode {response_mode!r}")
