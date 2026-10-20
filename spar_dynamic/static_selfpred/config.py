"""Model panel and cell plan for STATIC_SELFPRED_v1.0 -- DRAFT, NOT YET FROZEN.

Model settings are copied from dice_pilot_v41.config so that the replication
runs under the same configuration as the pilots it replicates.

Decided 2026-10-20:
  * Open-weight model: Qwen3-32B, with reasoning disabled (R_qwen_default).
    Gate: Qwen parsed 20/20 under the v4.1 dice wording with this config, but
    20/40 were invalid under the v3.1 wording (used here) with the R0/R1
    configs. A parse check on the exact frozen prompts must pass before the
    main run.
  * Dice positions stay at the pilots' {1, 2, 5, 9}; the handoff suggested
    {2, 6, 7, 10}.
  * The neutral-phrasing control is included.
  * Supplied-answer name: each model's modal object-level answer from this
    run's object phase, fixed before any supplied-answer call.
"""

from __future__ import annotations

from typing import Dict, Tuple

from spar_dynamic.dice_pilot_v41.config import MODELS_BY_LABEL as _V41_MODELS
from spar_dynamic.static_selfpred import prompts

PANEL: Tuple[str, ...] = ("astra", "fable", "qwen")
MODELS = tuple(_V41_MODELS[label] for label in PANEL)

# Calls per (model, cell, position). Not a power calculation; handoff §3.
N_MAIN = 100
N_SUPPLIED = 20        # deterministic competence check; 100 adds nothing

# cell -> (positions, calls per position). Positions are None for unpositioned cells.
ANIMAL_CELLS: Dict[str, Tuple[tuple, int]] = {
    "animal_object":       ((None,), N_MAIN),
    "animal_self":         (prompts.ANIMAL_POSITIONS, N_MAIN),
    "animal_generic":      (prompts.ANIMAL_POSITIONS, N_MAIN),
    "animal_generic_name": ((None,), N_MAIN),
    "animal_neutral":      (prompts.ANIMAL_POSITIONS, N_MAIN),
    "animal_supplied":     (prompts.ANIMAL_POSITIONS, N_SUPPLIED),
}

DICE_CELLS: Dict[str, Tuple[tuple, int]] = {
    "dice_object":      ((None,), N_MAIN),
    "dice_self":        (tuple(prompts.DICE_ORDINALS), N_MAIN),
    "dice_single_roll": ((None,), N_MAIN),
    "dice_generic":     (tuple(prompts.DICE_ORDINALS), N_MAIN),
}

# The object phase must finish first: the supplied-answer name depends on it.
# Within the remaining cells, calls are interleaved in a seeded random order.
ORDER_SEED = 20261021


def calls_per_model() -> int:
    cells = {**ANIMAL_CELLS, **DICE_CELLS}
    return sum(len(positions) * n for positions, n in cells.values())


def total_calls() -> int:
    return calls_per_model() * len(PANEL)
