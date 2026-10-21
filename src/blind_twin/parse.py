"""Frozen parsers. No repair, no salvage of shapes from prose."""
from __future__ import annotations

import json
import re
from typing import Dict, Optional, Tuple

from . import config as C

PARSER_VERSION = {"v1": "bt_v1", "v2": "bt_v2_final_line"}[C.VERSION]
_SHAPES = {"STAR", "TRIANGLE"}
_WRAP = " \t\r\n*_`'\".!:"   # cosmetic wrappers only (markdown emphasis, quotes, final period)


def _bare_shape(line: str) -> Optional[str]:
    core = line.strip().strip(_WRAP).strip().upper()
    return core if core in _SHAPES else None


def parse_shape(text: Optional[str], finish_reason: str = "") -> Tuple[Optional[str], str]:
    """Return (shape, reason).

    v1: the whole response must be exactly one shape word (cosmetic wrappers allowed).
    v2: the LAST non-empty line must be exactly one shape word (cosmetic wrappers allowed); earlier
        lines are free reasoning, except that an earlier line which is itself a bare DIFFERENT shape
        makes the answer ambiguous. No shape is ever searched for inside reasoning text."""
    if text is None or not text.strip():
        return None, "empty"
    if (finish_reason or "").lower() == "length":
        return None, "truncated_length"
    if C.VERSION == "v2":
        lines = [l for l in text.strip().splitlines() if l.strip()]
        last = _bare_shape(lines[-1])
        if last is None:
            return None, "final_line_not_a_shape"
        earlier = {x for x in (_bare_shape(l) for l in lines[:-1]) if x}
        if earlier - {last}:
            return None, "ambiguous_bare_shapes"
        return last, "ok" if len(lines) == 1 and text.strip() == last else "ok_final_line"
    core = text.strip().strip(_WRAP).strip()
    up = core.upper()
    if up in _SHAPES:
        return up, "ok" if core == up and text.strip() == up else "ok_wrapped"
    return None, "not_a_single_shape"


_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.S | re.I)


def parse_judge(text: Optional[str], finish_reason: str = "") -> Tuple[Optional[Dict[str, str]], str]:
    """Return ({'matcher': shape, 'mismatcher': shape}, reason). Bare JSON object, or the same
    object inside a single code fence. Exact keys; values STAR/TRIANGLE (case-insensitive)."""
    if text is None or not text.strip():
        return None, "empty"
    if (finish_reason or "").lower() == "length":
        return None, "truncated_length"
    s = text.strip()
    wrapped = False
    m = _FENCE.match(s)
    if m:
        s, wrapped = m.group(1).strip(), True
    try:
        obj = json.loads(s)
    except Exception:
        return None, "not_json"
    if not isinstance(obj, dict) or set(obj.keys()) != {"matcher", "mismatcher"}:
        return None, "wrong_keys"
    out = {}
    for k in ("matcher", "mismatcher"):
        v = obj[k]
        if not isinstance(v, str) or v.strip().upper() not in _SHAPES:
            return None, "bad_value"
        out[k] = v.strip().upper()
    return out, "ok_wrapped" if wrapped else "ok"
