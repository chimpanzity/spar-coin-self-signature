"""Frozen configuration for FAVORITE_ANIMAL_CROSSED_v1.0."""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


# Reuse the favorite_animal ModelV* dataclass by importing from the sibling
# package. Any config drift in favorite_animal shows up here immediately.
from spar_dynamic.favorite_animal.config import (            # noqa: F401
    FavoriteAnimalModel as CrossedModel,
    MODELS as _FAV_MODELS, MODELS_BY_LABEL as _FAV_MODELS_BY_LABEL,
    EXECUTION_ORDER as _FAV_EXECUTION_ORDER,
    TEMPERATURE_WHEN_SUPPORTED,
    TRANSPORT_RETRY_CAP, CONTENT_RETRY_CAP,
)


# Same three models and configuration as favorite_animal
MODELS = _FAV_MODELS
MODELS_BY_LABEL = _FAV_MODELS_BY_LABEL
EXECUTION_ORDER = _FAV_EXECUTION_ORDER


# -------------------------------------------------- experimental factors --
# Each model's canonical favorite as established by favorite_animal pilot
# (run dicepilot-style ID: favanim-20261016T103809Z). These are frozen
# ground truth for the crossed-prediction scoring.
PRIOR_CANONICAL_FAVORITE: Dict[str, str] = {
    "astra":  "octopus",
    "fable":  "octopus",
    "oss120": "elephant",
}


# Named-target reference phrases used in the Phase 2 prompt.
# These must match the display names the models themselves would plausibly
# recognize for identifying each other. The crossed-prediction task is thus
# BOTH an introspection probe (predicting the target's self-generated
# response) AND a knowledge probe (knowing which target produces which
# animal). We keep the names clean and unambiguous.
TARGET_NAMED: Dict[str, str] = {
    "astra":  "GPT-6 Astra",
    "fable":  "Claude Fable 5.1",
    "oss120": "GPT-OSS-120B",
}


# Pairs (predictor, target) where predictor != target.
CROSS_PAIRS: Tuple[Tuple[str, str], ...] = tuple(
    (p, t) for p in EXECUTION_ORDER for t in EXECUTION_ORDER if p != t
)
# → (astra, fable), (astra, oss120), (fable, astra), (fable, oss120),
#   (oss120, astra), (oss120, fable)


PHASE2_POSITIONS = ("first", "second", "penultimate", "last")
PHASE2_REPLICATES_PER_POSITION = 5

# No Phase 1 here — the self-generated favorites are inherited from the
# prior pilot. The usability-gate concept is replaced by: this experiment
# runs only against models whose prior canonical favorite is on file.

CALLS_PER_PAIR = len(PHASE2_POSITIONS) * PHASE2_REPLICATES_PER_POSITION   # 20
TOTAL_CALLS_MAX = len(CROSS_PAIRS) * CALLS_PER_PAIR                        # 120


# -------------------------------------------------- API settings --
# No new TRANSPORT_RETRY_CAP / CONTENT_RETRY_CAP — imported from
# favorite_animal.config above.


# -------------------------------------------------- budget --
BUDGET_USD_CAP = 10.0

# -------------------------------------------------- seeds --
SCHEDULING_SEED = 2026101603
