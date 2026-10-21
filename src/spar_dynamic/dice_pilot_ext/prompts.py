"""Prompts for DICE_PILOT_EXT_v1.0 — re-export of v3.1 frozen prompts.

Spec §5 explicitly requires byte-identical prompts to the v3.1 pilot. We
import the strings from the v3.1 package and re-export them here, plus a
byte-identity assertion that fails loudly if the parent prompts ever drift.
"""

from __future__ import annotations

from spar_dynamic.dice_pilot import prompts as _p

# Byte re-export (do NOT re-type the strings).
PHASE1_PROMPT = _p.PHASE1_PROMPT
PHASE2_TEMPLATE = _p.PHASE2_TEMPLATE
PHASE2_ORDINALS = dict(_p.PHASE2_ORDINALS)
phase2_prompt = _p.phase2_prompt


def assert_consistency() -> None:
    """Both: run v3.1's own invariant check, and verify byte identity with the
    v3.1 module's prompt constants. If anyone edits v3.1 prompts, this fails."""
    _p.assert_consistency()
    assert PHASE1_PROMPT == _p.PHASE1_PROMPT
    assert PHASE2_TEMPLATE == _p.PHASE2_TEMPLATE
    assert PHASE2_ORDINALS == _p.PHASE2_ORDINALS
