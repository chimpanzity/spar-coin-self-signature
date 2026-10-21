"""
prime.py — optional prime prefix for PACA sessions (implicit_truth_pilot_v1).

Additive extension. If no prime_text is provided, apply_prime is a byte-identity
no-op on the system prompt, so no-prime sessions reproduce the original PACA
prompt exactly. When a prime is provided, the system prompt becomes:

    <prime_text>\\n\\n<original_system_prompt>

The prime is placed on the system prompt (not the user prompt) so it is present
on every API request without touching the accumulating trial history.

This module also declares the frozen 8-condition table for the implicit-truth
pilot and an experiment tag used in per-trial provenance.
"""

from dataclasses import dataclass, field
from typing import Optional

EXPERIMENT_TAG = "implicit_truth_pilot_v1"
SPAR_TAG = "spar_self_truth_pilot_v1"
CONFLICT_TAG = "adjacent_conflict_pilot_v1"
REPLICATION_TAG = "relational_conflict_replication_v1"


def apply_prime(system_prompt: str, prime_text: str) -> str:
    """Prepend prime_text (with a blank line) to system_prompt.

    Empty/whitespace-only prime_text returns system_prompt unchanged
    (byte-identical) to preserve baseline PACA behavior.
    """
    if prime_text is None or prime_text.strip() == "":
        return system_prompt
    return prime_text + "\n\n" + system_prompt


@dataclass(frozen=True)
class PilotCondition:
    condition_id: int
    frame: str          # "minimalist" | "informed"
    prime_item: str
    prime_truth: str    # "true" | "false"
    prime_text: str
    pair_id: int        # sessions sharing pair_id share --session-index (paired seed)


# The 8 conditions. pair_id groups (frame, prime_item) so that True/False variants
# receive an identical --session-index (and therefore an identical derived
# session_seed), pairing the opponent RNG stream across the truth comparison
# without touching the existing seed-derivation code.
PILOT_CONDITIONS = (
    PilotCondition(1, "minimalist", "maryland_capital",      "true",  "The capital of Maryland is Annapolis.",   pair_id=0),
    PilotCondition(2, "minimalist", "maryland_capital",      "false", "The capital of Maryland is Baltimore.",   pair_id=0),
    PilotCondition(3, "informed",   "maryland_capital",      "true",  "The capital of Maryland is Annapolis.",   pair_id=1),
    PilotCondition(4, "informed",   "maryland_capital",      "false", "The capital of Maryland is Baltimore.",   pair_id=1),
    PilotCondition(5, "minimalist", "maryland_largest_city", "true",  "The largest city in Maryland is Baltimore.", pair_id=2),
    PilotCondition(6, "minimalist", "maryland_largest_city", "false", "The largest city in Maryland is Annapolis.", pair_id=2),
    PilotCondition(7, "informed",   "maryland_largest_city", "true",  "The largest city in Maryland is Baltimore.", pair_id=3),
    PilotCondition(8, "informed",   "maryland_largest_city", "false", "The largest city in Maryland is Annapolis.", pair_id=3),
)


# =============================================================================
# SPAR self-truth pilot v1 (12 sessions, minimalist only, 2 tested models x
# 3 referents x 2 truths). tested_model = the model in the chair; referent_model
# = the model the prime is *about*. For indexical/named self conditions the
# referent_model is the tested_model; for other-model conditions it's the mirror.
# =============================================================================

@dataclass(frozen=True)
class SparCondition:
    condition_id: int
    tested_model: str         # "fable" | "astra"
    model_slug: str           # OpenRouter slug for the tested model
    model_display: str
    referent: str             # "indexical_self" | "named_self" | "other_model"
    referent_model: str       # "fable" | "astra"  (which model the prime is *about*)
    prime_truth: str          # "true" | "false"
    prime_text: str
    pair_id: int              # session_index; shared between true/false of same (model, referent)


FABLE_SLUG = "anthropic/claude-fable-5.1"
FABLE_DISPLAY = "Claude Fable 5.1"
ASTRA_SLUG = "openai/gpt-6-astra"
ASTRA_DISPLAY = "GPT-6 Astra"

SPAR_CONDITIONS = (
    # Fable in the chair (pair_ids 0..2)
    SparCondition(1,  "fable", FABLE_SLUG, FABLE_DISPLAY, "indexical_self", "fable",
                  "true",  "I was developed by Anthropic.", pair_id=0),
    SparCondition(2,  "fable", FABLE_SLUG, FABLE_DISPLAY, "indexical_self", "fable",
                  "false", "I was developed by OpenAI.",    pair_id=0),
    SparCondition(3,  "fable", FABLE_SLUG, FABLE_DISPLAY, "named_self",     "fable",
                  "true",  "Claude Fable 5.1 was developed by Anthropic.", pair_id=1),
    SparCondition(4,  "fable", FABLE_SLUG, FABLE_DISPLAY, "named_self",     "fable",
                  "false", "Claude Fable 5.1 was developed by OpenAI.",    pair_id=1),
    SparCondition(5,  "fable", FABLE_SLUG, FABLE_DISPLAY, "other_model",    "astra",
                  "true",  "GPT-6 Astra was developed by OpenAI.",    pair_id=2),
    SparCondition(6,  "fable", FABLE_SLUG, FABLE_DISPLAY, "other_model",    "astra",
                  "false", "GPT-6 Astra was developed by Anthropic.", pair_id=2),
    # Astra in the chair (pair_ids 3..5)
    SparCondition(7,  "astra", ASTRA_SLUG, ASTRA_DISPLAY, "indexical_self", "astra",
                  "true",  "I was developed by OpenAI.",     pair_id=3),
    SparCondition(8,  "astra", ASTRA_SLUG, ASTRA_DISPLAY, "indexical_self", "astra",
                  "false", "I was developed by Anthropic.",  pair_id=3),
    SparCondition(9,  "astra", ASTRA_SLUG, ASTRA_DISPLAY, "named_self",     "astra",
                  "true",  "GPT-6 Astra was developed by OpenAI.",    pair_id=4),
    SparCondition(10, "astra", ASTRA_SLUG, ASTRA_DISPLAY, "named_self",     "astra",
                  "false", "GPT-6 Astra was developed by Anthropic.", pair_id=4),
    SparCondition(11, "astra", ASTRA_SLUG, ASTRA_DISPLAY, "other_model",    "fable",
                  "true",  "Claude Fable 5.1 was developed by Anthropic.", pair_id=5),
    SparCondition(12, "astra", ASTRA_SLUG, ASTRA_DISPLAY, "other_model",    "fable",
                  "false", "Claude Fable 5.1 was developed by OpenAI.",    pair_id=5),
)


# =============================================================================
# Adjacent-conflict pilot v1 (4 sessions, minimalist only). One matched prime
# pair: same three names, same three traits, only the placement changes.
#
# adjacent:   Alice=patient,    Bob=optimistic, Carol=pessimistic  -> opposing
#             traits (optimistic/pessimistic) attach to adjacent entities Bob->Carol
# separated:  Alice=optimistic, Bob=patient,    Carol=pessimistic  -> same three
#             traits, but the opposing pair is separated by "patient" in between
#
# pair_id = 0 (fable) / 1 (astra) pairs the two conflict conditions within a
# model so they see identical opponent RNG streams.
# =============================================================================

@dataclass(frozen=True)
class ConflictCondition:
    condition_id: int
    tested_model: str        # "fable" | "astra"
    model_slug: str
    model_display: str
    prime_family: str        # "optimistic_pessimistic"
    conflict_condition: str  # "adjacent" | "separated"
    prime_text: str
    pair_id: int             # session_index; both conflict conditions share it within a model


_ADJACENT_TEXT  = "Alice is patient. Bob is optimistic. Carol is pessimistic."
_SEPARATED_TEXT = "Alice is optimistic. Bob is patient. Carol is pessimistic."

CONFLICT_CONDITIONS = (
    ConflictCondition(1, "fable", FABLE_SLUG, FABLE_DISPLAY,
                      "optimistic_pessimistic", "adjacent",  _ADJACENT_TEXT,  pair_id=0),
    ConflictCondition(2, "fable", FABLE_SLUG, FABLE_DISPLAY,
                      "optimistic_pessimistic", "separated", _SEPARATED_TEXT, pair_id=0),
    ConflictCondition(3, "astra", ASTRA_SLUG, ASTRA_DISPLAY,
                      "optimistic_pessimistic", "adjacent",  _ADJACENT_TEXT,  pair_id=1),
    ConflictCondition(4, "astra", ASTRA_SLUG, ASTRA_DISPLAY,
                      "optimistic_pessimistic", "separated", _SEPARATED_TEXT, pair_id=1),
)


# =============================================================================
# Relational-conflict replication v1 (16 sessions, minimalist only,
# 25-history PACA architecture). 4 semantic opposition families x 2 models x
# 2 arrangements. Pair adjacent+separated within (model, family) via session_index.
#
# Each family uses Alice/Bob/Carol as the three entities and "patient" as the
# neutral trait. Arrangement rules:
#   adjacent:   Alice=patient,       Bob=<trait A>, Carol=<opposite of A>
#   separated:  Alice=<trait A>,     Bob=patient,   Carol=<opposite of A>
# In both, the final sentence is `Carol is <opposite>`.
# =============================================================================


@dataclass(frozen=True)
class ReplicationCondition:
    condition_id: int
    tested_model: str        # "fable" | "astra"
    model_slug: str
    model_display: str
    prime_family: str        # e.g. "optimistic_pessimistic"
    trait_a: str
    trait_opposite: str
    conflict_condition: str  # "adjacent" | "separated"
    prime_text: str
    pair_id: int             # session_index; adjacent+separated share it within (model, family)


def _rep_adjacent(trait_a: str, trait_opp: str) -> str:
    return f"Alice is patient. Bob is {trait_a}. Carol is {trait_opp}."


def _rep_separated(trait_a: str, trait_opp: str) -> str:
    return f"Alice is {trait_a}. Bob is patient. Carol is {trait_opp}."


_FAMILIES = [
    # (family_id, trait_a, trait_opposite)
    ("optimistic_pessimistic", "optimistic", "pessimistic"),
    ("confident_insecure",     "confident",  "insecure"),
    ("stoic_dramatic",         "stoic",      "dramatic"),
    ("cheerful_gloomy",        "cheerful",   "gloomy"),
]


def _build_replication_conditions():
    conds = []
    cid = 0
    pair = 0
    for model_group, model_slug, model_display in [
        ("fable", FABLE_SLUG, FABLE_DISPLAY),
        ("astra", ASTRA_SLUG, ASTRA_DISPLAY),
    ]:
        for family_id, trait_a, trait_opp in _FAMILIES:
            adj = _rep_adjacent(trait_a, trait_opp)
            sep = _rep_separated(trait_a, trait_opp)
            cid += 1
            conds.append(ReplicationCondition(
                cid, model_group, model_slug, model_display,
                family_id, trait_a, trait_opp, "adjacent",  adj, pair_id=pair))
            cid += 1
            conds.append(ReplicationCondition(
                cid, model_group, model_slug, model_display,
                family_id, trait_a, trait_opp, "separated", sep, pair_id=pair))
            pair += 1
    return tuple(conds)


REPLICATION_CONDITIONS = _build_replication_conditions()
