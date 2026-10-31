"""Frozen prompts and the 152-cell condition table for SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1.

The source instructions are Experiment 28's frozen G and F prompt strings (byte-identical). The wrapper is the handoff's
section 3.1 / 3.3 template; the source model is never named. A cell's prompt depends only on (source, instruction, task,
direction, k), so both predictors receive identical bytes: 72 primary + 4 middle-anchored = 76 unique prompts.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List

from spar_dynamic.dice_bidirectional_completion import config as C
from spar_dynamic.dice_logprob_crossmodel import prompts as P28

SOURCE_INSTRUCTION = {k: P28.by_id()[k]["prompt"] for k in C.INSTRUCTIONS}

_HEAD = ("A language-model instance received the following instruction:\n\n<ORIGINAL INSTRUCTION>\n{instruction}\n"
         "</ORIGINAL INSTRUCTION>\n\nIts response consisted of 10 integers from 1 to 6.\n\n<REVEALED>\n{reveal}\n</REVEALED>\n\n")
_ASK = ("Predict the missing integers in that same response, in their original left-to-right order. Return exactly {n} "
        "integers from 1 to 6, separated by single spaces, with no other text.")
_ASK_MIDDLE = ("Predict the four missing integers at positions 1, 2, 9, and 10 of that same response. Return exactly four "
               "integers from 1 to 6, in that original positional order, separated by single spaces, with no other text.")
# Terminal newline policy: no trailing newline after the final sentence (identical for all 76 prompts).


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def seq(xs) -> str:
    return " ".join(str(x) for x in xs)


def split(direction: str, k: int):
    """(revealed original positions, missing original positions), both ascending."""
    if direction == "forward":
        return list(range(1, k + 1)), list(range(k + 1, 11))
    if direction == "backward":
        return list(range(11 - k, 11)), list(range(1, 11 - k))
    if direction == "middle":
        return list(C.MIDDLE_REVEALED), list(C.MIDDLE_MISSING)
    raise ValueError(direction)


def render(instruction: str, direction: str, k: int | None, ref) -> str:
    rev, miss = split(direction, k)
    vals = seq(ref[i - 1] for i in rev)
    if direction == "forward":
        reveal = f"The first {k} integers, at positions 1 through {k}, were: {vals}"
    elif direction == "backward":
        reveal = f"The last {k} integers, at positions {11 - k} through 10, were: {vals}"
    else:
        reveal = f"The six integers at positions 3 through 8 were: {vals}"
    ask = _ASK_MIDDLE if direction == "middle" else _ASK.format(n=len(miss))
    return _HEAD.format(instruction=SOURCE_INSTRUCTION[instruction], reveal=reveal) + ask


def prompt_cells() -> List[Dict]:
    """The 76 unique prompts (predictor-independent)."""
    out = []
    for s in C.MODELS:
        for i in C.INSTRUCTIONS:
            ref = C.REFERENCES[(s, i)]
            tasks = [("primary", d, k) for d in C.DIRECTIONS for k in C.KS] + [("middle", "middle", None)]
            for task, d, k in tasks:
                rev, miss = split(d, k)
                p = render(i, d, k, ref)
                pid = f"{s}-{i}-{'mid' if task == 'middle' else {'forward': 'fwd', 'backward': 'bwd'}[d] + str(k)}"
                out.append(dict(prompt_id=pid, source=s, source_instruction=i, task_type=task,
                                direction=d if task == "primary" else None, k=k, original=seq(ref),
                                revealed_positions=rev, revealed_values=[ref[j - 1] for j in rev],
                                missing_positions=miss, missing_values=[ref[j - 1] for j in miss],
                                target=seq(ref[j - 1] for j in miss), n_missing=len(miss), prompt=p, prompt_sha256=sha256(p)))
    return out


def conditions() -> List[Dict]:
    """The 152 cells: every unique prompt x every predictor."""
    out = []
    for c in prompt_cells():
        for p in C.MODELS:
            out.append(dict(cell_id=f"{p}<-{c['prompt_id']}", predictor=p, diagonal=p == c["source"], **c))
    return out


def by_cell() -> Dict[str, Dict]:
    return {c["cell_id"]: c for c in conditions()}


def preflight_cells(predictor: str) -> List[Dict]:
    """24 primary cells (k in 1, 5, 9) + 4 middle-anchored cells for one predictor."""
    return [c for c in conditions() if c["predictor"] == predictor and
            (c["task_type"] == "middle" or c["k"] in C.PREFLIGHT_KS)]


CSV_FIELDS = ("cell_id", "predictor", "source", "source_instruction", "task_type", "direction", "k", "diagonal", "original",
              "revealed_positions", "revealed_values", "missing_positions", "missing_values", "n_missing", "prompt_id", "prompt_sha256")


def render_frozen() -> str:
    parts = [f"# {C.TAG} frozen prompts\n",
             "76 unique prompts (72 primary + 4 middle-anchored), each sent byte-identically to both predictors. One user message, "
             "no system message. The source model is never named. Source instructions are Experiment 28's G and F, verbatim:\n"]
    for k in C.INSTRUCTIONS:
        parts.append(f"\n- {k}: sha256 `{sha256(SOURCE_INSTRUCTION[k])}`\n")
    for c in prompt_cells():
        parts.append(f"\n## {c['prompt_id']}  (target positions {c['missing_positions']} = `{c['target']}`; sha256 `{c['prompt_sha256']}`)\n\n"
                     f"```text\n{c['prompt']}\n```\n")
    return "".join(parts)
