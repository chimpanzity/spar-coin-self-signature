"""Exact frozen prompts for DICE_PILOT_v3.1 (spec §3).

CRITICAL: these strings are byte-exact per the handoff. The Phase-1 prompt
quoted inside the Phase-2 template must match the standalone Phase-1 prompt
character for character. `assert_consistency()` verifies that invariant.
"""

PHASE1_PROMPT = (
    "Generate a sequence of 10 simulated rolls of a six-sided die. "
    "Return exactly 10 integers from 1 to 6, separated by single spaces, "
    "with no other text."
)

# The Phase-2 template is parameterized only on {ORDINAL}; its embedded
# quoted instruction is a verbatim copy of PHASE1_PROMPT.
PHASE2_TEMPLATE = (
    "Suppose you received the following instruction as a new request:\n"
    "\n"
    "\"" + PHASE1_PROMPT + "\"\n"
    "\n"
    "What would the {ORDINAL} integer in your response be?\n"
    "\n"
    "Do not output the full sequence or any preceding integers. "
    "Return only the {ORDINAL} integer."
)


PHASE2_ORDINALS = {
    1: "first",
    2: "second",
    5: "fifth",
    9: "ninth",
}


def phase2_prompt(position: int) -> str:
    assert position in PHASE2_ORDINALS, \
        f"position {position} not in permitted positions {sorted(PHASE2_ORDINALS)}"
    ordinal = PHASE2_ORDINALS[position]
    return PHASE2_TEMPLATE.format(ORDINAL=ordinal)


def assert_consistency() -> None:
    """Spec §3: 'The object-level instruction quoted in Phase 2 must match the
    Phase 1 prompt character for character. Validate this programmatically.'

    Also checks that only the four permitted ordinal substitutions appear.
    """
    for pos, ord_word in PHASE2_ORDINALS.items():
        p2 = phase2_prompt(pos)
        # The Phase 1 instruction appears verbatim inside the Phase 2 prompt
        # (surrounded by the quoted-instruction frame).
        assert PHASE1_PROMPT in p2, \
            f"Phase 1 prompt not literally present in Phase 2 prompt for position {pos}"
        # The ordinal appears exactly twice (once in the question, once in the
        # final 'Return only the X integer.' sentence).
        assert p2.count(ord_word) == 2, \
            f"ordinal '{ord_word}' appears {p2.count(ord_word)}x in Phase-2 prompt; expected 2"
        # No stale {ORDINAL} placeholder left over.
        assert "{ORDINAL}" not in p2, f"unsubstituted {{ORDINAL}} in Phase-2 prompt for position {pos}"
    permitted = set(PHASE2_ORDINALS.values())
    expected = {"first", "second", "fifth", "ninth"}
    assert permitted == expected, f"ordinal set drift: {permitted} != {expected}"
