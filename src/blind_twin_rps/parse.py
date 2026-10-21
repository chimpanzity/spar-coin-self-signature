"""Frozen RPS parsers (final-line rule, as Blind Twin v2). No repair, no salvage from prose."""
from __future__ import annotations

import json
import re
from typing import Dict, Optional, Tuple

PARSER_VERSION = "btrps_v1_final_line"
_MOVES = {"ROCK", "PAPER", "SCISSORS"}
_WRAP = " \t\r\n*_`'\".!:"


def _bare(line: str) -> Optional[str]:
    core = line.strip().strip(_WRAP).strip().upper()
    return core if core in _MOVES else None


def parse_shape(text: Optional[str], finish_reason: str = "") -> Tuple[Optional[str], str]:
    """Last non-empty line must be exactly one move (cosmetic wrappers allowed); an earlier line that is
    itself a bare DIFFERENT move makes the answer ambiguous. No move is searched for inside reasoning."""
    if text is None or not text.strip():
        return None, "empty"
    if (finish_reason or "").lower() == "length":
        return None, "truncated_length"
    lines = [l for l in text.strip().splitlines() if l.strip()]
    last = _bare(lines[-1])
    if last is None:
        return None, "final_line_not_a_move"
    earlier = {x for x in (_bare(l) for l in lines[:-1]) if x}
    if earlier - {last}:
        return None, "ambiguous_bare_moves"
    return last, "ok" if len(lines) == 1 and text.strip() == last else "ok_final_line"


_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.S | re.I)


def parse_judge(text: Optional[str], finish_reason: str = "") -> Tuple[Optional[Dict[str, str]], str]:
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
    if not isinstance(obj, dict) or set(obj.keys()) != {"player_a", "player_b"}:
        return None, "wrong_keys"
    out = {}
    for k in ("player_a", "player_b"):
        v = obj[k]
        if not isinstance(v, str) or v.strip().upper() not in _MOVES:
            return None, "bad_value"
        out[k] = v.strip().upper()
    return out, "ok_wrapped" if wrapped else "ok"
