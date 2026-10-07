"""Representation transforms applied to canonical source strings for display to judges.

Canonical strings are never altered on disk; a renderer produces the judge-facing form.
Pilot 1 uses the identity renderer (HT). AB relabeling is available. Additional renderers
(STAY/SWITCH transitions, summary statistics) plug in here later without touching source
generation or trial construction.
"""

from __future__ import annotations

from typing import Callable

Renderer = Callable[[str, str], str]  # (canonical_string, canonical_alphabet) -> display string


def render_identity(s: str, alphabet: str) -> str:
    return s


def render_ab(s: str, alphabet: str) -> str:
    mapping = {alphabet[0]: "A", alphabet[1]: "B"}
    return "".join(mapping[c] for c in s)


def render_stay_switch(s: str, alphabet: str) -> str:
    """Transition string (length n-1): S = same as previous outcome, W = switched.

    Not an active Pilot 1 condition; provided so the same machinery can be reused later.
    """
    return "".join("S" if s[i] == s[i - 1] else "W" for i in range(1, len(s)))


RENDERERS: dict[str, Renderer] = {
    "HT": render_identity,
    "AB": render_ab,
    "STAY_SWITCH": render_stay_switch,
}

# Only these may be selected via config for Pilot 1.
ACTIVE_DISPLAY_MODES = ("HT", "AB")


def render(s: str, display_alphabet: str, canonical_alphabet: str = "HT") -> str:
    try:
        return RENDERERS[display_alphabet](s, canonical_alphabet)
    except KeyError:
        raise ValueError(f"unknown display mode {display_alphabet!r}") from None
