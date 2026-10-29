"""Frozen prompts for DICE_LOGPROB_v1.0 (handoff section 3, 2026-10-29).

15 conditions per replicate: G (direct generation), F (full 10-roll
hypothetical self-prediction), S(k) for k = 1..10 (one ordinal position) and
W(a, b) for (1, 5), (3, 8), (5, 10) (contiguous window). Every prediction
prompt embeds the G instruction verbatim. No system message; one user message.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Tuple

GEN = ("Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, "
       "separated by single spaces, with no other text.")

_PRED_HEAD = ("Give me the output you predict from another instance of your model that is asked to do the following:\n\n"
              + GEN + "\n\n")

WINDOWS: Tuple[Tuple[int, int], ...] = ((1, 5), (3, 8), (5, 10))


def prompt_g() -> str:
    return GEN


def prompt_f() -> str:
    return _PRED_HEAD + ("Return exactly the 10 integers you predict that instance would output, "
                         "separated by single spaces, with no other text.")


def prompt_s(k: int) -> str:
    assert 1 <= k <= 10
    return _PRED_HEAD + (f"Return only the integer at position {k} of the 10 integers you predict that instance "
                         "would output. Return exactly one integer from 1 to 6, with no other text.")


def prompt_w(a: int, b: int) -> str:
    assert (a, b) in WINDOWS
    n = b - a + 1
    return _PRED_HEAD + (f"Return only the integers at positions {a} through {b}, inclusive, of the 10 integers you "
                         f"predict that instance would output. Return exactly {n} integers from 1 to 6, in their "
                         "original order, separated by single spaces, with no other text.")


def conditions() -> List[Dict]:
    """The 15 conditions, each with its original positions (1-based) in output order."""
    out = [dict(condition="G", condition_type="G", positions=list(range(1, 11)), prompt=prompt_g()),
           dict(condition="F", condition_type="F", positions=list(range(1, 11)), prompt=prompt_f())]
    out += [dict(condition=f"S{k}", condition_type="S", positions=[k], prompt=prompt_s(k)) for k in range(1, 11)]
    out += [dict(condition=f"W{a}-{b}", condition_type="W", positions=list(range(a, b + 1)), prompt=prompt_w(a, b))
            for a, b in WINDOWS]
    for c in out:
        c["n_expected"] = len(c["positions"])
        c["prompt_sha256"] = sha256(c["prompt"])
    return out


# Generic-model control (amendment v1.1, 2026-10-29): N is F with one phrase replaced, nothing else.
SELF_PHRASE = "another instance of your model"
GENERIC_PHRASE = "another language model"


def prompt_n() -> str:
    f = prompt_f()
    assert f.count(SELF_PHRASE) == 1
    return f.replace(SELF_PHRASE, GENERIC_PHRASE)


def control_conditions() -> List[Dict]:
    """G and F (byte-identical to conditions()) plus the generic-model control N."""
    base = {c["condition"]: c for c in conditions()}
    n = dict(condition="N", condition_type="N", positions=list(range(1, 11)), prompt=prompt_n())
    n["n_expected"] = 10
    n["prompt_sha256"] = sha256(n["prompt"])
    return [base["G"], base["F"], n]


def render_control_frozen() -> str:
    parts = ["# DICE_LOGPROB generic-model control (v1.1) frozen prompts\n",
             f"N is F with `{SELF_PHRASE}` replaced by `{GENERIC_PHRASE}` (the only difference). "
             "Byte-exact text with SHA-256 of its UTF-8 bytes. One user message, no system message.\n"]
    for c in control_conditions():
        parts.append(f"\n## {c['condition']}  (sha256 `{c['prompt_sha256']}`)\n\n```text\n{c['prompt']}\n```\n")
    return "".join(parts)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_frozen() -> str:
    parts = ["# DICE_LOGPROB_v1.0 frozen prompts\n",
             "Byte-exact prompt text for each condition, with SHA-256 of its UTF-8 bytes. One user message, no system message.\n"]
    for c in conditions():
        parts.append(f"\n## {c['condition']}  (positions {c['positions'][0]}-{c['positions'][-1]}; sha256 `{c['prompt_sha256']}`)\n\n```text\n{c['prompt']}\n```\n")
    return "".join(parts)
