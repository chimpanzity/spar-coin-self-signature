"""Frozen prompts for SPAR_DICE_LOGPROB_CROSSMODEL_v2.0.

G, F and S1-S10 are Experiment 21's functions, called unchanged. The window prompts use Experiment 21's window template
byte for byte with the investigator's windows (1-5, 3-7, 6-10); `tests/` checks that this template reproduces Experiment
21's own W prompts for its windows (1-5, 3-8, 5-10). W1-5 is therefore byte-identical to Experiment 21's W1-5.
"""

from __future__ import annotations

from typing import Dict, List

from spar_dynamic.dice_logprob import prompts as P21
from spar_dynamic.dice_logprob_crossmodel import config as C

GEN = P21.GEN
sha256 = P21.sha256


def prompt_w(a: int, b: int) -> str:
    """Experiment 21's prompt_w text without its window assertion."""
    n = b - a + 1
    return P21._PRED_HEAD + (f"Return only the integers at positions {a} through {b}, inclusive, of the 10 integers you "
                             f"predict that instance would output. Return exactly {n} integers from 1 to 6, in their "
                             "original order, separated by single spaces, with no other text.")


def conditions() -> List[Dict]:
    """The 15 conditions, each with its original serial positions (1-based) in output order."""
    out = [dict(condition="G", condition_type="G", positions=list(range(1, 11)), prompt=P21.prompt_g()),
           dict(condition="F", condition_type="F", positions=list(range(1, 11)), prompt=P21.prompt_f())]
    out += [dict(condition=f"S{k}", condition_type="S", positions=[k], prompt=P21.prompt_s(k)) for k in range(1, 11)]
    out += [dict(condition=f"W{a}-{b}", condition_type="W", positions=list(range(a, b + 1)), prompt=prompt_w(a, b))
            for a, b in C.WINDOWS]
    for c in out:
        c["n_expected"] = len(c["positions"])
        c["prompt_sha256"] = sha256(c["prompt"])
    return out


def by_id() -> Dict[str, Dict]:
    return {c["condition"]: c for c in conditions()}


def render_frozen() -> str:
    parts = [f"# {C.TAG} frozen prompts\n",
             "Byte-exact prompt text for each condition, with SHA-256 of its UTF-8 bytes. One user message, no system message. "
             "G, F, S1-S10 and W1-5 are byte-identical to Experiment 21; W3-7 and W6-10 are new.\n"]
    for c in conditions():
        parts.append(f"\n## {c['condition']}  (original positions {c['positions'][0]}-{c['positions'][-1]}; "
                     f"sha256 `{c['prompt_sha256']}`)\n\n```text\n{c['prompt']}\n```\n")
    return "".join(parts)
