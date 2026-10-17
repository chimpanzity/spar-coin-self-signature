"""Parsers for DICE_PILOT_EXT_v1.0 — re-export of v3.1 parsers.

Spec §8 explicitly requires the same parsing and classification rules.
"""

from spar_dynamic.dice_pilot.parsers import (  # noqa: F401
    Phase1Parse, Phase2Parse, parse_phase1, parse_phase2,
)
