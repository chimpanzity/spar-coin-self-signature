"""Frozen parsers (Sections 4.4 and 13.6).

Generation parser: extract a single unambiguous ordered list of 20 outcomes.
Never concatenates separate lists, pads, trims or repairs.

Answer parser: bare JSON scalar/array/object, with one tolerated wrapper
(single code fence or one unique JSON payload amid harmless text).
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

GEN_PARSER_VERSION = "gen_v2"
ANSWER_PARSER_VERSION = "ans_v1"

# ---------------------------------------------------------------------------
# Generation parsing
# ---------------------------------------------------------------------------

_BREAK = " § "  # section sign: never a separator, always breaks a list

# Aggregate counts ("Heads: 11", "11 heads", "H = 9") and legends are removed
# before tokenising so they cannot join an outcome list.
_COUNT_PATTERNS = [
    # gen_v2: markdown emphasis may surround the label or colon ("**Heads:** 10")
    re.compile(r"\b(heads?|tails?|h|t)[*_ \t]*[:=][*_ \t]*\d+", re.I),
    re.compile(r"\b\d+[*_ \t]*(heads?|tails?)\b", re.I),
    re.compile(r"\b(heads?|tails?)[ \t]*(count|total)\b", re.I),
    re.compile(r"\b(h|t)[ \t]*=[ \t]*(heads?|tails?)\b", re.I),
    re.compile(r"\b(heads?|tails?)[ \t]*=[ \t]*(h|t)\b", re.I),
]
# "Heads (H)" / "H (Heads)" annotations collapse to one token.
_ANNOT_WORD_LETTER = re.compile(r"\b(heads?|tails?)\s*\(\s*[ht]\s*\)", re.I)
_ANNOT_LETTER_WORD = re.compile(r"\b([ht])\s*\(\s*(heads?|tails?)\s*\)", re.I)

_TOKEN = re.compile(r"\b(heads?|tails?|[ht]+)\b", re.I)
# What may sit between two outcome tokens of the same list.
_SEPARATOR = re.compile(
    r"^(?:[\s,;|/\-–—.()\[\]{}*_`'\"·•∙⋅>]"
    r"|(?:flip|coin|toss|throw|result|outcome)s?\s*#?\s*\d+\s*[.):\-]?"
    r"|#?\d+\s*[.):\-]"
    r"|\d+\s*(?=\s)"
    r")*$",
    re.I,
)


@dataclass
class GenParse:
    valid: bool
    outcomes: Optional[str]
    reason: str
    repeated_list: bool = False
    span: Optional[Tuple[int, int]] = None
    n_candidate_lists: int = 0
    candidate_lengths: List[int] = field(default_factory=list)


def _token_outcomes(tok: str) -> str:
    t = tok.lower()
    if t.startswith("head"):
        return "H"
    if t.startswith("tail"):
        return "T"
    return t.upper()


def _candidate_lists(text: str) -> List[Tuple[str, Tuple[int, int]]]:
    work = text
    for pat in _COUNT_PATTERNS:
        work = pat.sub(lambda m: _BREAK.ljust(len(m.group(0)))[: len(m.group(0))], work)
    work = _ANNOT_WORD_LETTER.sub(lambda m: m.group(1).ljust(len(m.group(0))), work)
    work = _ANNOT_LETTER_WORD.sub(lambda m: m.group(1).ljust(len(m.group(0))), work)
    lists: List[Tuple[str, Tuple[int, int]]] = []
    cur = ""
    start = end = None
    last_end = None
    for m in _TOKEN.finditer(work):
        between = work[last_end:m.start()] if last_end is not None else None
        if cur and between is not None and _SEPARATOR.match(between) and "§" not in between:
            cur += _token_outcomes(m.group(0))
            end = m.end()
        else:
            if cur:
                lists.append((cur, (start, end)))
            cur = _token_outcomes(m.group(0))
            start, end = m.start(), m.end()
        last_end = m.end()
    if cur:
        lists.append((cur, (start, end)))
    return lists


def parse_generation(text: Optional[str], finish_reason: str = "", length: int = 20) -> GenParse:
    if text is None or not text.strip():
        return GenParse(False, None, "empty")
    lists = _candidate_lists(text)
    lengths = [len(s) for s, _ in lists]
    exact = [(s, sp) for s, sp in lists if len(s) == length]
    base = dict(n_candidate_lists=len(lists), candidate_lengths=lengths)
    if (finish_reason or "").lower() == "length":
        return GenParse(False, exact[0][0] if exact else None, "truncated_length", **base)
    if not exact:
        if any(n > 3 for n in lengths):
            return GenParse(False, None, "wrong_length", **base)
        return GenParse(False, None, "no_list", **base)
    distinct = {s for s, _ in exact}
    if len(distinct) > 1:
        return GenParse(False, None, "conflicting_lists", **base)
    seq, span = exact[0]
    return GenParse(True, seq, "ok", repeated_list=len(exact) > 1, span=span, **base)


# ---------------------------------------------------------------------------
# Answer parsing
# ---------------------------------------------------------------------------

@dataclass
class AnswerParse:
    valid: bool
    value: Any
    reason: str
    strict_valid: bool = False
    wrapped_payload: bool = False
    normalized: bool = False
    raw_value: Any = None


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S | re.I)
_ARRAY = re.compile(r"\[[^\[\]]*\]", re.S)
_OBJECT = re.compile(r"\{[^{}]*\}", re.S)
_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?:[eE]-?\d+)?(?![\w.])")


def _is_prob(x: Any) -> bool:
    return (isinstance(x, (int, float)) and not isinstance(x, bool)
            and math.isfinite(float(x)) and 0.0 <= float(x) <= 1.0)


def _validate(kind: str, obj: Any) -> Tuple[bool, Any, str, bool, Any]:
    """Return (ok, value, reason, normalized, raw)."""
    if kind == "scalar":
        if _is_prob(obj):
            return True, float(obj), "ok", False, obj
        return False, None, "scalar_out_of_range_or_type", False, obj
    if kind == "array10":
        if not isinstance(obj, list) or len(obj) != 10:
            return False, None, "array_wrong_length", False, obj
        if not all(_is_prob(v) for v in obj):
            return False, None, "array_bad_value", False, obj
        return True, [float(v) for v in obj], "ok", False, obj
    if kind == "named3":
        if not isinstance(obj, dict) or set(obj.keys()) != {"C1", "C2", "C3"}:
            return False, None, "object_wrong_keys", False, obj
        vals = [obj["C1"], obj["C2"], obj["C3"]]
        if not all(_is_prob(v) for v in vals):
            return False, None, "object_bad_value", False, obj
        s = sum(float(v) for v in vals)
        if abs(s - 1.0) > 1e-3:
            return False, None, "object_sum_not_one", False, obj
        norm = abs(s - 1.0) > 0
        value = {k: float(obj[k]) / s for k in ("C1", "C2", "C3")}
        return True, value, "ok", norm, obj
    raise ValueError(kind)


def _try_json(s: str) -> Tuple[bool, Any]:
    try:
        return True, json.loads(s)
    except Exception:
        return False, None


def parse_answer(text: Optional[str], kind: str, finish_reason: str = "") -> AnswerParse:
    if text is None or not text.strip():
        return AnswerParse(False, None, "empty")
    if (finish_reason or "").lower() == "length":
        return AnswerParse(False, None, "truncated_length")
    s = text.strip()
    ok, obj = _try_json(s)
    if ok:
        good, val, reason, norm, raw = _validate(kind, obj)
        return AnswerParse(good, val, reason, strict_valid=good, normalized=norm, raw_value=raw)
    if "%" in s and kind == "scalar":
        return AnswerParse(False, None, "percentage")
    # One code fence.
    fences = _FENCE.findall(s)
    if len(fences) == 1:
        ok, obj = _try_json(fences[0].strip())
        if ok:
            good, val, reason, norm, raw = _validate(kind, obj)
            return AnswerParse(good, val, reason, wrapped_payload=True, normalized=norm, raw_value=raw)
    if len(fences) > 1:
        return AnswerParse(False, None, "multiple_fences")
    # One unique payload amid text.
    if kind in ("array10", "named3"):
        pat = _ARRAY if kind == "array10" else _OBJECT
        cands = []
        for m in pat.finditer(s):
            ok, obj = _try_json(m.group(0))
            if ok:
                cands.append(obj)
        if len(cands) == 1:
            good, val, reason, norm, raw = _validate(kind, cands[0])
            return AnswerParse(good, val, reason, wrapped_payload=True, normalized=norm, raw_value=raw)
        return AnswerParse(False, None, "ambiguous_or_missing_payload")
    # scalar amid text: exactly one number and no booleans.
    if re.search(r"\b(true|false)\b", s, re.I):
        return AnswerParse(False, None, "boolean")
    nums = _NUMBER.findall(s)
    if len(nums) == 1:
        v = float(nums[0])
        if _is_prob(v):
            return AnswerParse(True, v, "ok", wrapped_payload=True, raw_value=nums[0])
        return AnswerParse(False, None, "scalar_out_of_range_or_type")
    return AnswerParse(False, None, "multiple_or_no_numbers")
