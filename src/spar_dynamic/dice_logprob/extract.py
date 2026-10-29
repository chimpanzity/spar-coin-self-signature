"""Parsing, token-to-face alignment and six-face probability vectors (handoff sections 4.2, 4.3, 6.2, 6.3).

Fail-closed rules:
  * A response is valid only if its content is exactly n integers in 1..6
    separated by single ASCII spaces (no other characters, no newline).
  * A face is scorable only if exactly one output token covers its digit and
    that token's text is the digit itself or a single space plus the digit.
    Multi-digit or otherwise mixed tokens are not comparable.
  * The six candidate faces are read from that token's top_logprobs using
    the same shape as the emitted token (same leading-space pattern). A face
    missing from top_logprobs is missing (None), never zero. A face spelled
    in the other shape is kept raw and flags tokenization ambiguity; it is
    never merged.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Sequence

FACES = (1, 2, 3, 4, 5, 6)
_THINK_RE = re.compile(r"<\s*/?\s*think", re.I)
_TOOL_RE = re.compile(r"<\s*/?\s*tool_call", re.I)


def parse(content: Optional[str], n: int, finish_reason: str = "stop", tool_calls: bool = False) -> Dict[str, Any]:
    text = content if content is not None else ""
    if tool_calls or finish_reason == "tool_calls" or _TOOL_RE.search(text):
        return dict(verdict="tool_use", faces=None)
    if _THINK_RE.search(text):
        return dict(verdict="think_tag", faces=None)
    if finish_reason == "length":
        return dict(verdict="truncated", faces=None)
    if finish_reason not in ("stop", "eos", "end_turn"):
        return dict(verdict=f"finish_{finish_reason or 'missing'}", faces=None)
    if not re.fullmatch(r"[1-6]( [1-6])*", text):
        stripped_ok = bool(re.fullmatch(r"[1-6]( [1-6])*", text.strip()))
        return dict(verdict="format_whitespace" if stripped_ok else "format", faces=None)
    faces = [int(x) for x in text.split(" ")]
    if len(faces) != n:
        return dict(verdict="wrong_count", faces=None)
    return dict(verdict="valid", faces=faces)


def _tok_text(t: Dict[str, Any]) -> str:
    if t.get("bytes"):
        try:
            return bytes(t["bytes"]).decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            pass
    return t.get("token", "")


def align_faces(content: str, tokens: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One record per face digit in content: covering token index(es), shape and the six candidate logprobs."""
    spans, pos = [], 0
    for i, t in enumerate(tokens):
        s = _tok_text(t)
        spans.append((pos, pos + len(s), i, s))
        pos += len(s)
    joined_ok = "".join(s for *_, s in spans) == content
    out = []
    digit_offsets = [m.start() for m in re.finditer(r"[1-6]", content)]
    for local, off in enumerate(digit_offsets, start=1):
        cover = [sp for sp in spans if sp[0] <= off < sp[1]]
        rec: Dict[str, Any] = dict(local_output_index=local, reported_face=int(content[off]), text_offset=off,
                                   token_indices=[c[2] for c in cover], token_texts=[c[3] for c in cover])
        reasons = []
        if not joined_ok:
            reasons.append("tokens do not reconstruct content")
        if len(cover) != 1:
            reasons.append(f"{len(cover)} tokens cover the digit")
        tok_txt = cover[0][3] if len(cover) == 1 else ""
        if tok_txt not in (content[off], " " + content[off]):
            reasons.append(f"token {tok_txt!r} is not a bare face token")
        prefix = tok_txt[:-1] if not reasons else ""
        logp: Dict[int, Optional[float]] = {f: None for f in FACES}
        other_shape: Dict[str, float] = {}
        raw_top: List[Dict[str, Any]] = []
        if not reasons:
            t = tokens[cover[0][2]]
            raw_top = [dict(token=a.get("token"), logprob=a.get("logprob"), bytes=a.get("bytes"))
                       for a in (t.get("top_logprobs") or [])]
            for a in raw_top:
                s = _tok_text(a)
                for f in FACES:
                    if s == prefix + str(f):
                        logp[f] = a["logprob"] if logp[f] is None else max(logp[f], a["logprob"])
                    elif s.strip() == str(f):
                        other_shape[s] = a["logprob"]
            if not raw_top:
                reasons.append("no top_logprobs alternatives")
            selected_lp = t.get("logprob")
            if logp[rec["reported_face"]] is None and selected_lp is not None:
                logp[rec["reported_face"]] = selected_lp
        complete = not reasons and all(v is not None for v in logp.values())
        if not reasons and not complete:
            reasons.append("faces missing from top_logprobs: " + ",".join(str(f) for f in FACES if logp[f] is None))
        rec.update(token_prefix=prefix, logprob_face=logp, other_shape_face_tokens=other_shape,
                   top_logprobs_raw=raw_top, candidate_coverage_complete=complete,
                   tokenization_ambiguity_flag=bool(other_shape), comparable_flag=complete and not other_shape,
                   reason_if_not_comparable="; ".join(reasons) or ("other-shape face tokens present" if other_shape else ""))
        if complete:
            mass = sum(math.exp(v) for v in logp.values())
            rec["six_face_mass"] = mass
            rec["p_raw"] = {f: math.exp(logp[f]) for f in FACES}
            rec["p6"] = p6_from_logp([logp[f] for f in FACES])
        else:
            rec["six_face_mass"], rec["p_raw"], rec["p6"] = None, None, None
        out.append(rec)
    return out


def p6_from_logp(lps: Sequence[float]) -> Dict[int, float]:
    """Normalise six face logprobs to a distribution over faces, in log space (no underflow)."""
    m = max(lps)
    w = [math.exp(x - m) for x in lps]
    z = sum(w)
    return {f: w[i] / z for i, f in enumerate(FACES)}


def js_bits(p: Sequence[float], q: Sequence[float]) -> float:
    """Jensen-Shannon divergence in bits between two complete distributions (0..1)."""
    assert len(p) == len(q) and abs(sum(p) - 1) < 1e-9 and abs(sum(q) - 1) < 1e-9
    m = [(a + b) / 2 for a, b in zip(p, q)]

    def kl(a, b):
        return sum(x * math.log2(x / y) for x, y in zip(a, b) if x > 0)
    return max(0.0, 0.5 * kl(p, m) + 0.5 * kl(q, m))


def rank_of(face: int, p6: Dict[int, float]) -> int:
    """1 = most probable. Ties share the better rank."""
    return 1 + sum(1 for f in FACES if p6[f] > p6[face])
