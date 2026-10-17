"""Reasoning-trace candidate-animal-name detector (spec §8).

Objective: flag whether an exposed reasoning trace mentions a plausible
candidate animal name — ideally one the model would commit to as its
favorite.

Strict detection of "a candidate animal name" from free text is hard. We
use two complementary signals:

  (1) Does the reasoning contain any specific-animal reference pattern?
      Phrases like "the X" or "a X" or "pick X" where X is a lowercase
      2-20 letter word. This is a heuristic surface pattern.

  (2) Does the reasoning literally contain the model's Phase-1 modal
      animal name? If we pass that into the detector, it is a strict
      membership test. This is the stronger signal.

Spec §8 note: do not rely on a naive animal-word detector that mistakes
common words or examples for actual hypothetical candidate responses.
Flagging here is for AUDIT — all flagged cases need hand review.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple


# "Candidate" surface patterns. These are heuristics; a hand audit of all
# flagged traces catches false positives.
# Pattern 1: "pick <word>" / "choose <word>" / "say <word>"
_CHOICE_RE = re.compile(
    r"\b(?:pick|choose|say|answer|respond(?:ing)? with|go(?:ing)? with|"
    r"commit(?:ting)? to|land on|settle on)\s+(?:\"|')?([A-Za-z][A-Za-z]{1,19})",
    re.IGNORECASE,
)
# Pattern 2: "my favorite is <word>" / "favorite animal is <word>"
_FAV_RE = re.compile(
    r"\bfavorite(?:\s+animal)?\s+(?:is|would be|might be)\s+(?:a |an |the )?"
    r"(?:\"|')?([A-Za-z][A-Za-z]{1,19})",
    re.IGNORECASE,
)
# Pattern 3: a parenthetical candidate like "my favorite (the octopus) is..."
_PAREN_RE = re.compile(
    r"\((?:\s*(?:a|an|the)\s+)?([A-Za-z][A-Za-z]{1,19})\s*\)",
)


def find_candidate_names(text: Optional[str]) -> List[str]:
    """Return a de-duplicated list of lowercase candidate animal-name words
    extracted via surface patterns. Everything here needs manual audit."""
    if not text: return []
    found = []
    for pat in (_CHOICE_RE, _FAV_RE, _PAREN_RE):
        for m in pat.finditer(text):
            found.append(m.group(1).lower())
    # Deduplicate while preserving order
    seen = set(); out = []
    for w in found:
        if w not in seen:
            seen.add(w); out.append(w)
    return out


def mentions_name(text: Optional[str], name: str) -> bool:
    """Return True iff `text` contains `name` as a whole-word match
    (case-insensitive). `name` may be multi-word; its spaces are matched
    literally."""
    if not text or not name: return False
    pat = r"\b" + re.escape(name) + r"\b"
    return re.search(pat, text, re.IGNORECASE) is not None


def classify(reasoning_content: Optional[str], reasoning_classification: str,
              phase1_modal_name: Optional[str] = None) -> Tuple[str, dict]:
    """Return (classification, info) tuple per spec §8:

      classification ∈ { "candidate_name_in_reasoning",
                         "no_candidate_observed",
                         "reasoning_unavailable" }

    `info` includes any extracted candidates and whether the modal animal
    name was literally mentioned.
    """
    if reasoning_classification in (None, "none", "unavailable", "encrypted", "summarized"):
        return "reasoning_unavailable", {"candidates": [], "modal_mentioned": False}
    if not isinstance(reasoning_content, str) or not reasoning_content:
        return "reasoning_unavailable", {"candidates": [], "modal_mentioned": False}
    cands = find_candidate_names(reasoning_content)
    modal_mentioned = (phase1_modal_name is not None
                        and mentions_name(reasoning_content, phase1_modal_name))
    if cands or modal_mentioned:
        return "candidate_name_in_reasoning", {
            "candidates": cands,
            "modal_mentioned": modal_mentioned,
            "phase1_modal_name": phase1_modal_name,
        }
    return "no_candidate_observed", {
        "candidates": [], "modal_mentioned": False,
        "phase1_modal_name": phase1_modal_name,
    }
