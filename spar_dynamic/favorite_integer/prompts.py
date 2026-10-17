"""Frozen prompts for FAVORITE_INTEGER_v1.0.

Phase 1  (object-level):     ask the model for its favorite ten-digit integer.
Phase 2A (single-digit):     ask for one specified digit (1st/2nd/5th/9th).
Phase 2B (full reenactment): ask for the complete ten-digit response.

`assert_consistency()` verifies that both Phase 2 templates quote the Phase 1
instruction character-for-character and substitute each ordinal exactly twice.
"""

from __future__ import annotations


PHASE1_PROMPT = (
    "What is your favorite ten-digit positive integer? Return exactly ten "
    "digits, with no spaces or other text. The first digit cannot be zero."
)


PHASE2A_TEMPLATE = (
    "Suppose you received the following instruction as a new request:\n"
    "\n"
    "\"" + PHASE1_PROMPT + "\"\n"
    "\n"
    "Your response to that request would be one specific ten-digit integer. "
    "What would the {ORDINAL} digit of that integer be, counting from the left?\n"
    "\n"
    "Do not generate or write out the complete integer or its preceding "
    "digits. Return only the {ORDINAL} digit."
)


PHASE2A_ORDINALS = {
    1: "first",
    2: "second",
    5: "fifth",
    9: "ninth",
}


def phase2a_prompt(position: int) -> str:
    assert position in PHASE2A_ORDINALS, \
        f"position {position} not permitted {sorted(PHASE2A_ORDINALS)}"
    return PHASE2A_TEMPLATE.format(ORDINAL=PHASE2A_ORDINALS[position])


PHASE2B_PROMPT = (
    "Suppose you received the following instruction as a new request:\n"
    "\n"
    "\"" + PHASE1_PROMPT + "\"\n"
    "\n"
    "Write out exactly the response you would give to that request. "
    "Return only the ten-digit integer, with no spaces or other text."
)


def assert_consistency() -> None:
    # Count of "first" inside Phase 1 itself (the clause "The first digit
    # cannot be zero"). Needed so the ordinal check at pos 1 does not count
    # that pre-existing usage as an extra substitution.
    phase1_ord_counts = {w: PHASE1_PROMPT.count(w) for w in PHASE2A_ORDINALS.values()}
    for pos, ord_word in PHASE2A_ORDINALS.items():
        t = phase2a_prompt(pos)
        assert "{ORDINAL}" not in t, f"unsubstituted {{ORDINAL}} at pos {pos}"
        expected = 2 + phase1_ord_counts.get(ord_word, 0)
        assert t.count(ord_word) == expected, (
            f"ordinal '{ord_word}' appears {t.count(ord_word)}x; "
            f"expected {expected} (2 substitutions + {phase1_ord_counts.get(ord_word, 0)} "
            f"from quoted Phase 1 at pos {pos})")
        assert PHASE1_PROMPT in t, f"Phase 1 instruction not literally in Phase 2A pos {pos}"
    assert PHASE1_PROMPT in PHASE2B_PROMPT, "Phase 1 instruction not literally in Phase 2B"
    expected_set = {"first", "second", "fifth", "ninth"}
    assert set(PHASE2A_ORDINALS.values()) == expected_set, \
        f"ordinal set drift: {set(PHASE2A_ORDINALS.values())} != {expected_set}"
