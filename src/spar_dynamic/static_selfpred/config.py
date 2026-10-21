"""Model panel and cell plan for STATIC_SELFPRED_v1.0 -- FROZEN 2026-10-20 (git tag static-selfpred-v1.0).

Model settings are copied from dice_pilot_v41.config so that the replication
runs under the same configuration as the pilots it replicates.

Decided 2026-10-20:
  * Open-weight model: Qwen3-32B, run twice: reasoning off (R_off) and
    reasoning effort high (R_high), both at temperature 0 on SiliconFlow
    with max_tokens=32768 and no tools. Settings are parse_check.CONFIGS
    ["qwen"]. They passed the parse check on these exact prompts
    (parsecheck-qwen-20261021T000345Z: 140/140 and 137/140 usable). DeepInfra
    was dropped because it ignores reasoning.enabled=false.
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
from spar_dynamic.static_selfpred.parse_check import CONFIGS as _PARSE_CHECK_CONFIGS

PANEL: Tuple[str, ...] = ("astra", "fable", "qwen")
# Astra and Fable as in the pilots; Qwen as parse-checked (two configs).
MODELS = tuple(_V41_MODELS[label] for label in ("astra", "fable"))
QWEN_CONFIGS = tuple(_PARSE_CHECK_CONFIGS["qwen"])
N_MODEL_CONFIGS = len(MODELS) + len(QWEN_CONFIGS)

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
    return calls_per_model() * N_MODEL_CONFIGS
