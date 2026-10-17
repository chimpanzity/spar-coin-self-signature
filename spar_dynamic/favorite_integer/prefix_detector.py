"""Reasoning-prefix detector for FAVORITE_INTEGER_v1.0.

Spec §8: flag only when at least FOUR consecutive 0-9 digits appear with no
intervening prose. The dice-pilot detector was restricted to 1-6 digits and
required whitespace/comma separators between each digit. For the favorite-
integer task we also accept zero-separator runs (`"1234567890"`) because the
Phase 1 prompt specifies "no spaces or other text" — the natural
representation is contiguous digits.

Common false positives to avoid:
  "ten digits"          — the word "ten", not digits
  "digits 0 to 9"       — "0" and "9" are separated by prose
  "0-9", "1-9"          — ranges, not sequences
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple


# A single digit 0-9 not inside an alphanumeric token.
_DIGIT = r"(?<![A-Za-z0-9])[0-9](?![0-9A-Za-z])"

# A run of >=4 contiguous digits (e.g. "1234567890"). Must not be adjacent to
# a letter so we skip IDs like "sha256-abcdef1234".
_CONTIGUOUS_RE = re.compile(r"(?<![A-Za-z0-9])[0-9]{4,}(?![A-Za-z0-9])")

# A run of >=4 digits separated by whitespace/comma only (e.g. "3 5 2 6 1").
_SEPARATED_RE = re.compile(
    rf"(?:{_DIGIT}[ \t,]+){{3,}}{_DIGIT}"
)


def find_prefix_run(text: Optional[str]) -> Optional[Tuple[str, List[int]]]:
    """Return (matched_substring, [digits]) for the longest run of
    >= 4 consecutive 0-9 digits — either contiguous ("1234") or separated
    only by whitespace/commas ("1 2 3 4"). None if no such run exists.
    """
    if not text: return None
    best: Optional[re.Match] = None
    for pattern in (_CONTIGUOUS_RE, _SEPARATED_RE):
        for m in pattern.finditer(text):
            if best is None or (m.end() - m.start()) > (best.end() - best.start()):
                best = m
    if best is None: return None
    sub = best.group(0)
    digits = [int(d) for d in re.findall(r"[0-9]", sub)]
    return sub, digits


def has_prefix_run(text: Optional[str]) -> bool:
    return find_prefix_run(text) is not None
