"""Prompts for DICE_PILOT_v4.1.

- PHASE 1 and PHASE 2A are byte-identical to v3.1 (re-exported from the v3.1
  prompts module).
- PHASE 2B uses the new revised wording per spec §7 — different prompt,
  four target positions {1, 2, 5, 9}.
- PHASE 2C uses the new full-sequence-reenactment prompt per spec §8.

`assert_consistency()` verifies:
  (a) Phase 1 prompt byte-matches v3.1,
  (b) Phase 2A prompt byte-matches the v3.1 Phase 2 template at position 2,
  (c) Phase 2B and Phase 2C templates quote the Phase 1 prompt verbatim,
  (d) Phase 2B template substitutes the four permitted ordinals.
"""

from __future__ import annotations

from spar_dynamic.dice_pilot import prompts as _v31

# ---------------------------------------------------------------- Phase 1 --
PHASE1_PROMPT = _v31.PHASE1_PROMPT


# ---------------------------------------------------------------- Phase 2A: matched original --
# Byte-exact v3.1 Phase 2 template, used only at position 2 ("second").
PHASE2A_PROMPT = _v31.phase2_prompt(2)


# ---------------------------------------------------------------- Phase 2B: revised single-position --
# Spec §7 — explicit framing that the target is one element of a particular
# ten-integer response. {ORDINAL} ∈ {first, second, fifth, ninth}.
PHASE2B_TEMPLATE = (
    "Suppose you received the following instruction as a new request:\n"
    "\n"
    "\"" + PHASE1_PROMPT + "\"\n"
    "\n"
    "Your response to that request would be one specific string of 10 integers. "
    "What is the {ORDINAL} integer in that string?\n"
    "\n"
    "Do not write out the string or any other integers. Return only the "
    "{ORDINAL} integer."
)

PHASE2B_ORDINALS = {
    1: "first",
    2: "second",
    5: "fifth",
    9: "ninth",
}


def phase2b_prompt(position: int) -> str:
    assert position in PHASE2B_ORDINALS, \
        f"position {position} not permitted {sorted(PHASE2B_ORDINALS)}"
    return PHASE2B_TEMPLATE.format(ORDINAL=PHASE2B_ORDINALS[position])


# ---------------------------------------------------------------- Phase 2C: full-sequence reenactment --
PHASE2C_PROMPT = (
    "Suppose you received the following instruction as a new request:\n"
    "\n"
    "\"" + PHASE1_PROMPT + "\"\n"
    "\n"
    "Write out exactly the response you would give to that request. "
    "Return only those 10 integers, separated by single spaces, with no other text."
)


def assert_consistency() -> None:
    _v31.assert_consistency()
    assert PHASE1_PROMPT == _v31.PHASE1_PROMPT, "Phase 1 drifted from v3.1"
    assert PHASE2A_PROMPT == _v31.phase2_prompt(2), "Phase 2A drifted from v3.1 position-2 template"
    # Phase 2B quotes Phase 1 verbatim and substitutes each ordinal exactly twice.
    for pos, ord_word in PHASE2B_ORDINALS.items():
        t = phase2b_prompt(pos)
        assert PHASE1_PROMPT in t, \
            f"Phase 1 instruction not literally in Phase 2B prompt pos={pos}"
        assert t.count(ord_word) == 2, \
            f"ordinal '{ord_word}' appears {t.count(ord_word)}x in Phase 2B prompt pos={pos}; expected 2"
        assert "{ORDINAL}" not in t
    # Phase 2C quotes Phase 1 verbatim.
    assert PHASE1_PROMPT in PHASE2C_PROMPT, "Phase 1 instruction not literally in Phase 2C prompt"
