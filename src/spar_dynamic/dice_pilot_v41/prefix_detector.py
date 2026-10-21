"""Corrected reasoning-prefix detector (spec §3.4).

The v3.1 detector flagged *any* two bare 1-6 digits anywhere in a text,
which produced false positives on ordinary English like "between 1 and 6"
(the "and" is prose, but 1 and 6 are two bare digits in range).

v4.1 definition: flag only when at least FOUR consecutive integers in the
range 1-6 appear, separated only by whitespace or commas, with no
intervening prose.

Returns the extracted longest-run sequence and its length so audits can
compare it against the model's Phase-1 modal.

This is an automated screening heuristic, NOT proof of simulation.
Spec requires manual audit of all flagged traces and 10% of unflagged.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

# A single digit 1..6 that is not part of a larger alphanumeric token.
_DIGIT = r"(?<![A-Za-z0-9])[1-6](?![0-9A-Za-z])"

# One digit + one separator block containing only whitespace or commas.
# At least 4 consecutive digits = three such separator-joined pairs plus a
# final digit.
_RUN_RE = re.compile(
    rf"(?:{_DIGIT}[ \t,]+){{3,}}{_DIGIT}"
)


def find_prefix_run(text: Optional[str]) -> Optional[Tuple[str, List[int]]]:
    """Return (matched_substring, [digits]) for the longest run of >=4
    consecutive 1-6 digits separated only by whitespace or commas, or None
    if no such run exists.

    `text` may be None or empty; returns None in those cases.
    """
    if not text: return None
    best: Optional[re.Match] = None
    for m in _RUN_RE.finditer(text):
        if best is None or (m.end() - m.start()) > (best.end() - best.start()):
            best = m
    if best is None: return None
    sub = best.group(0)
    digits = [int(d) for d in re.findall(r"[1-6]", sub)]
    return sub, digits


def has_prefix_run(text: Optional[str]) -> bool:
    return find_prefix_run(text) is not None
