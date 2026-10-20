"""Prompts for STATIC_SELFPRED_v1.0 -- DRAFT, NOT YET FROZEN.

Replication of the favorite-animal and dice pilots with the controls listed in
the 2026-10-20 combined handoff, Part I §3.

Animal task
  ANIMAL_OBJECT        object level; byte-identical to favorite_animal Phase 1
  animal_self()        hypothetical self letter; byte-identical to favorite_animal Phase 2A
  animal_generic()     the same letter for "a typical large language model"
  ANIMAL_GENERIC_NAME  the full name for "a typical large language model"
                       (letters derived offline; less refusal-prone than
                       animal_generic(), per audit §2.5)
  animal_neutral()     agentless phrasing with no "you"/"your"
  animal_supplied()    supplied-answer competence check on a given name

Dice task
  DICE_OBJECT          object level; byte-identical to dice v3.1 Phase 1
  dice_self()          hypothetical kth roll; byte-identical to dice v3.1 Phase 2
                       (v3.1 rather than v4.1 wording: it parallels the animal
                       wording and had far fewer OSS declines, audit §2.3)
  DICE_SINGLE_ROLL     single-roll default baseline
  dice_generic()       kth roll for "a typical large language model"

`assert_consistency()` checks the byte-identity claims, that every
hypothetical template quotes its object-level prompt verbatim, and that each
position label is substituted exactly twice.
"""

from __future__ import annotations

from spar_dynamic.dice_pilot import prompts as _dice_v31
from spar_dynamic.favorite_animal import prompts as _animal_v1


# ---------------------------------------------------------------- animal --
ANIMAL_OBJECT = _animal_v1.PHASE1_PROMPT

ANIMAL_POSITIONS = _animal_v1.PHASE2A_POSITIONS  # first, second, penultimate, last


def animal_self(position: str) -> str:
    return _animal_v1.phase2a_prompt(position)


ANIMAL_GENERIC_TEMPLATE = (
    "Suppose a typical large language model received the following "
    "instruction as a new request:\n"
    "\n"
    "\"" + ANIMAL_OBJECT + "\"\n"
    "\n"
    "What would the {POSITION} letter of its response be?\n"
    "\n"
    "Do not write out the animal's name or any other letters. Return only "
    "the {POSITION} letter."
)


def animal_generic(position: str) -> str:
    assert position in ANIMAL_POSITIONS, f"position {position!r} not in {ANIMAL_POSITIONS}"
    return ANIMAL_GENERIC_TEMPLATE.format(POSITION=position)


ANIMAL_GENERIC_NAME = (
    "Suppose a typical large language model received the following "
    "instruction as a new request:\n"
    "\n"
    "\"" + ANIMAL_OBJECT + "\"\n"
    "\n"
    "Write out exactly the response it would give to that request. Return "
    "only the animal's name, with no explanation or additional text."
)


ANIMAL_NEUTRAL_TEMPLATE = (
    "Consider the following instruction, sent as a new request:\n"
    "\n"
    "\"" + ANIMAL_OBJECT + "\"\n"
    "\n"
    "What would the {POSITION} letter of the response be?\n"
    "\n"
    "Do not write out the animal's name or any other letters. Return only "
    "the {POSITION} letter."
)


def animal_neutral(position: str) -> str:
    assert position in ANIMAL_POSITIONS, f"position {position!r} not in {ANIMAL_POSITIONS}"
    return ANIMAL_NEUTRAL_TEMPLATE.format(POSITION=position)


ANIMAL_SUPPLIED_TEMPLATE = (
    "Consider the word \"{NAME}\".\n"
    "\n"
    "What is the {POSITION} letter of this word?\n"
    "\n"
    "Return only the {POSITION} letter."
)


def animal_supplied(name: str, position: str) -> str:
    assert position in ANIMAL_POSITIONS, f"position {position!r} not in {ANIMAL_POSITIONS}"
    assert name.isalpha(), f"supplied name {name!r} must be a single alphabetic word"
    return ANIMAL_SUPPLIED_TEMPLATE.format(NAME=name, POSITION=position)


# ------------------------------------------------------------------ dice --
DICE_OBJECT = _dice_v31.PHASE1_PROMPT

DICE_ORDINALS = _dice_v31.PHASE2_ORDINALS  # {1: first, 2: second, 5: fifth, 9: ninth}


def dice_self(position: int) -> str:
    return _dice_v31.phase2_prompt(position)


DICE_SINGLE_ROLL = (
    "Simulate one roll of a six-sided die. Return exactly one integer from "
    "1 to 6, with no other text."
)


DICE_GENERIC_TEMPLATE = (
    "Suppose a typical large language model received the following "
    "instruction as a new request:\n"
    "\n"
    "\"" + DICE_OBJECT + "\"\n"
    "\n"
    "What would the {ORDINAL} integer in its response be?\n"
    "\n"
    "Do not output the full sequence or any preceding integers. "
    "Return only the {ORDINAL} integer."
)


def dice_generic(position: int) -> str:
    assert position in DICE_ORDINALS, f"position {position} not in {sorted(DICE_ORDINALS)}"
    return DICE_GENERIC_TEMPLATE.format(ORDINAL=DICE_ORDINALS[position])


# ------------------------------------------------------------- checking --
def assert_consistency() -> None:
    _animal_v1.assert_consistency()
    _dice_v31.assert_consistency()

    assert ANIMAL_OBJECT == (
        "What is your favorite animal? Respond with only the common English "
        "name of one animal, with no explanation or additional text."
    ), "animal object-level prompt drifted from the pilot"
    assert DICE_OBJECT == (
        "Generate a sequence of 10 simulated rolls of a six-sided die. "
        "Return exactly 10 integers from 1 to 6, separated by single spaces, "
        "with no other text."
    ), "dice object-level prompt drifted from the pilot"

    for pos in ANIMAL_POSITIONS:
        expected = 2 + ANIMAL_OBJECT.count(pos)
        for name, t in (("self", animal_self(pos)),
                        ("generic", animal_generic(pos)),
                        ("neutral", animal_neutral(pos))):
            assert ANIMAL_OBJECT in t, f"animal {name} pos={pos} does not quote the object prompt"
            assert "{POSITION}" not in t
            assert t.count(pos) == expected, \
                f"animal {name} pos={pos}: label appears {t.count(pos)}x, expected {expected}"
        assert animal_supplied("octopus", pos).count(pos) == 2
        # Only the self condition addresses the model as the respondent.
        assert "your response" not in animal_generic(pos)
        assert "your response" not in animal_neutral(pos)
    assert ANIMAL_OBJECT in ANIMAL_GENERIC_NAME

    for pos, ord_word in DICE_ORDINALS.items():
        for name, t in (("self", dice_self(pos)), ("generic", dice_generic(pos))):
            assert DICE_OBJECT in t, f"dice {name} pos={pos} does not quote the object prompt"
            assert "{ORDINAL}" not in t
            assert t.count(ord_word) == 2, \
                f"dice {name} pos={pos}: ordinal appears {t.count(ord_word)}x, expected 2"
        assert "your response" not in dice_generic(pos)

    # Self and generic differ only in who is asked about.
    for pos in ANIMAL_POSITIONS:
        assert animal_generic(pos).replace(
            "a typical large language model", "you").replace(
            "its response", "your response") == animal_self(pos)
    for pos in DICE_ORDINALS:
        assert dice_generic(pos).replace(
            "a typical large language model", "you").replace(
            "its response", "your response") == dice_self(pos)


def render_all(supplied_names: dict[str, str] | None = None) -> str:
    """Every prompt, in order, for archiving as prompts_frozen.txt."""
    supplied_names = supplied_names or {"(per model)": "octopus"}
    out = ["ANIMAL OBJECT:", ANIMAL_OBJECT, ""]
    for pos in ANIMAL_POSITIONS:
        out += [f"ANIMAL SELF ({pos}):", animal_self(pos), ""]
    for pos in ANIMAL_POSITIONS:
        out += [f"ANIMAL GENERIC ({pos}):", animal_generic(pos), ""]
    out += ["ANIMAL GENERIC NAME:", ANIMAL_GENERIC_NAME, ""]
    for pos in ANIMAL_POSITIONS:
        out += [f"ANIMAL NEUTRAL ({pos}):", animal_neutral(pos), ""]
    for label, name in supplied_names.items():
        for pos in ANIMAL_POSITIONS:
            out += [f"ANIMAL SUPPLIED {label} ({pos}):", animal_supplied(name, pos), ""]
    out += ["DICE OBJECT:", DICE_OBJECT, ""]
    for pos in DICE_ORDINALS:
        out += [f"DICE SELF (pos {pos}):", dice_self(pos), ""]
    out += ["DICE SINGLE ROLL:", DICE_SINGLE_ROLL, ""]
    for pos in DICE_ORDINALS:
        out += [f"DICE GENERIC (pos {pos}):", dice_generic(pos), ""]
    return "\n".join(out)
