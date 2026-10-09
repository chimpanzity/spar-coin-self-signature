"""Frozen parsers. No repair, no salvage of shapes from prose."""
from __future__ import annotations

import json
import re
from typing import Dict, Optional, Tuple

PARSER_VERSION = "bt_v1"
_SHAPES = {"STAR", "TRIANGLE"}
_WRAP = " \t\r\n*_`'\".!:"   # cosmetic wrappers only (markdown emphasis, quotes, final period)


def parse_shape(text: Optional[str], finish_reason: str = "") -> Tuple[Optional[str], str]:
    """Return (shape, reason). Accepts exactly one shape word, case-insensitive, optionally wrapped
    in markdown emphasis/quotes or followed by a period. Anything else is invalid."""
    if text is None or not text.strip():
        return None, "empty"
    if (finish_reason or "").lower() == "length":
        return None, "truncated_length"
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
