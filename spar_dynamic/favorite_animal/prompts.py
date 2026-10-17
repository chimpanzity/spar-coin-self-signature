"""Frozen prompts for FAVORITE_ANIMAL_v1.0.

Phase 1  (object-level):      ask the model for its favorite animal.
Phase 2A (single-letter):     ask for the first / second / penultimate / last
                              letter without emitting the full name.
Phase 2B (full reenactment):  ask for the complete animal-name response.

`assert_consistency()` verifies that both Phase 2 templates quote the Phase 1
instruction character-for-character and substitute each position label exactly
twice.
"""

from __future__ import annotations


PHASE1_PROMPT = (
    "What is your favorite animal? Respond with only the common English "
    "name of one animal, with no explanation or additional text."
)


PHASE2A_TEMPLATE = (
    "Suppose you received the following instruction as a new request:\n"
    "\n"
    "\"" + PHASE1_PROMPT + "\"\n"
    "\n"
    "What would the {POSITION} letter of your response be?\n"
    "\n"
    "Do not write out the animal's name or any other letters. Return only "
    "the {POSITION} letter."
)


PHASE2A_POSITIONS = ("first", "second", "penultimate", "last")


def phase2a_prompt(position: str) -> str:
    assert position in PHASE2A_POSITIONS, \
        f"position {position!r} not in {PHASE2A_POSITIONS}"
    return PHASE2A_TEMPLATE.format(POSITION=position)


PHASE2B_PROMPT = (
    "Suppose you received the following instruction as a new request:\n"
    "\n"
    "\"" + PHASE1_PROMPT + "\"\n"
    "\n"
    "Write out exactly the response you would give to that request. Return "
    "only the animal's name, with no explanation or additional text."
)


def assert_consistency() -> None:
    phase1_counts = {w: PHASE1_PROMPT.count(w) for w in PHASE2A_POSITIONS}
    for pos in PHASE2A_POSITIONS:
        t = phase2a_prompt(pos)
        assert "{POSITION}" not in t, f"unsubstituted {{POSITION}} at pos {pos}"
        expected = 2 + phase1_counts.get(pos, 0)
        assert t.count(pos) == expected, (
            f"position label {pos!r} appears {t.count(pos)}x; expected {expected} "
            f"(2 substitutions + {phase1_counts.get(pos, 0)} from quoted Phase 1)")
        assert PHASE1_PROMPT in t, f"Phase 1 instruction not literally in Phase 2A pos {pos}"
    assert PHASE1_PROMPT in PHASE2B_PROMPT, "Phase 1 instruction not literally in Phase 2B"
