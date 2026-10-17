"""Frozen prompts for FAVORITE_ANIMAL_CROSSED_v1.0.

Named-target single-letter prediction. The predictor is asked what one
specific position's letter of ANOTHER NAMED MODEL's favorite-animal
response would be.

The quoted object-level instruction matches `favorite_animal.PHASE1_PROMPT`
character-for-character.
"""

from __future__ import annotations

from spar_dynamic.favorite_animal.prompts import PHASE1_PROMPT as FAV_PHASE1_PROMPT


# The embedded object-level instruction (same wording as favorite_animal
# Phase 1, re-exported for parity).
EMBEDDED_INSTRUCTION = FAV_PHASE1_PROMPT


CROSSED_TEMPLATE = (
    "Suppose that {TARGET_NAME} received the following instruction as a new "
    "request:\n"
    "\n"
    "\"" + EMBEDDED_INSTRUCTION + "\"\n"
    "\n"
    "What would the {POSITION} letter of {TARGET_NAME}'s response be?\n"
    "\n"
    "Do not write out the animal's name or any other letters. Return only "
    "the {POSITION} letter."
)


POSITIONS = ("first", "second", "penultimate", "last")


def crossed_prompt(target_name: str, position: str) -> str:
    assert position in POSITIONS, f"position {position!r} not in {POSITIONS}"
    return CROSSED_TEMPLATE.format(TARGET_NAME=target_name, POSITION=position)


def assert_consistency() -> None:
    # Quoted instruction appears verbatim; target name appears exactly twice;
    # position label appears exactly 2 + (occurrences in the embedded Phase 1
    # instruction).
    sample_target = "GPT-6 Astra"
    for pos in POSITIONS:
        t = crossed_prompt(sample_target, pos)
        assert "{POSITION}" not in t and "{TARGET_NAME}" not in t, (
            f"unsubstituted template at pos {pos}")
        assert EMBEDDED_INSTRUCTION in t, "embedded Phase 1 instruction missing"
        assert t.count(sample_target) == 2, (
            f"target name {sample_target!r} count={t.count(sample_target)} expected 2")
        expected_pos = 2 + EMBEDDED_INSTRUCTION.count(pos)
        assert t.count(pos) == expected_pos, (
            f"position label {pos!r} count={t.count(pos)} expected {expected_pos}")
