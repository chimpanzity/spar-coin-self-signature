"""Frozen prompts for SPAR_DICE_PREFIX_DECLARATIVE_v1.0 (handoff section 5).

H(k) asks for the next three integers of another instance's response to Experiment 21's G instruction after
revealing its first k integers (k = 0, 3, 6). N(k), S(k) and O(k) are H(k) with one paragraph inserted directly
before "Predict": a report of a *separate earlier response* to the same instruction whose first six integers use
each face once, framed as an observation, not a guarantee. The three versions differ only in its source:

  S  "from an instance of your own model"     (true: Experiment 21's greedy G, 5 2 6 3 1 4 ...)
  N  "from an instance of an unspecified model" (true for the same response; no source identity)
  O  "from an instance of a different model"  (true: Experiment 22's Mistral Small 3.2 sequences)

Handoff 4.3 asks for an information-equivalent pair; the draft wording there made the neutral sentence a claim
about the target itself, so all three versions describe a separate earlier response instead.
G and F are Experiment 21's prompts imported unchanged (hash-checked against the archive).
"""

from __future__ import annotations

import hashlib
from typing import Dict, List

from spar_dynamic.dice_logprob import prompts as P21
from spar_dynamic.dice_prefix_declarative import config as C

GEN = P21.GEN
HEAD = "Another instance of your model was given the following instruction:\n\n" + GEN + "\n\n"
NUMBER_WORDS = {0: "zero", 3: "three", 6: "six"}

SOURCE = {"S": "an instance of your own model",
          "N": "an instance of an unspecified model",
          "O": "an instance of a different model"}
DESCRIPTION = ("An earlier response to this exact instruction, from {SOURCE}, used each die face exactly once in its "
               "first six integers; this observation does not guarantee anything about the response you are "
               "predicting, and it does not determine any order.")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prefix_line(k: int) -> str:
    if k == 0:
        return "No part of its response has been revealed."
    return f"The first {NUMBER_WORDS[k]} integers in that instance's response were: " + " ".join(map(str, C.G_REF[:k]))


def ask(k: int) -> str:
    return (f"Predict the next three integers in that same ten-integer response (positions {k + 1} through {k + 3}), "
            "in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, "
            "separated by single spaces, with no other text.")


def description(arm: str) -> str:
    return DESCRIPTION.format(SOURCE=SOURCE[arm])


def prompt(arm: str, k: int) -> str:
    assert arm in C.ARMS and k in C.KS
    insert = "" if arm == "H" else description(arm) + "\n\n"
    return HEAD + prefix_line(k) + "\n\n" + insert + ask(k)


def conditions() -> List[Dict]:
    """The 12 prediction conditions in (k, arm) order, with original target positions and the true G window."""
    out = []
    for k in C.KS:
        for arm in C.ARMS:
            p = prompt(arm, k)
            out.append(dict(condition=f"{arm}{k}", arm=arm, k=k, positions=list(range(k + 1, k + C.WINDOW + 1)),
                            target=list(C.G_REF[k:k + C.WINDOW]), prompt=p, prompt_sha256=sha256(p)))
    return out


def references() -> Dict[str, Dict]:
    """Experiment 21's G and F, byte-identical (hashes asserted against the archive)."""
    g, f = P21.prompt_g(), P21.prompt_f()
    assert sha256(g) == C.G_PROMPT_SHA256 and sha256(f) == C.F_PROMPT_SHA256
    return {"G": dict(condition="G", prompt=g, prompt_sha256=sha256(g), reference=list(C.G_REF)),
            "F": dict(condition="F", prompt=f, prompt_sha256=sha256(f), reference=list(C.F_REF))}


def render_frozen() -> str:
    conds = conditions()
    parts = [f"# {C.TAG}: frozen prompts\n\n",
             "Byte-exact text, SHA-256 of the UTF-8 bytes. One user message, no system message, Qwen3 chat template "
             "with `enable_thinking=False`.\n\n## The inserted paragraph (N, S, O)\n\n",
             "Inserted, followed by a blank line, directly before \"Predict\". Only the source phrase differs; each "
             f"version is {len(description('S').split())} words.\n\n| Arm | Source phrase | Full paragraph |\n|---|---|---|\n"]
    for a in ("N", "S", "O"):
        parts.append(f"| {a} | `{SOURCE[a]}` | {description(a)} |\n")
    parts.append("\n## Per-k lines (shared by all four arms)\n\n| k | Revealed line | Target positions | True G window |\n|---|---|---|---|\n")
    for k in C.KS:
        parts.append(f"| {k} | {prefix_line(k)} | {k + 1}-{k + 3} | `{' '.join(map(str, C.G_REF[k:k + 3]))}` |\n")
    for c in conds:
        parts.append(f"\n## {c['condition']}  (sha256 `{c['prompt_sha256']}`)\n\n```text\n{c['prompt']}\n```\n")
    for name, r in references().items():
        parts.append(f"\n## Reference {name} (Experiment 21, unchanged; sha256 `{r['prompt_sha256']}`)\n\n```text\n{r['prompt']}\n```\n")
    return "".join(parts)
