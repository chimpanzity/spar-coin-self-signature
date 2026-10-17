"""Frozen configuration for FAVORITE_INTEGER_v1.0."""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class FavoriteIntegerModel:
    label: str
    slug: str
    display_name: str
    preferred_provider: str
    supports_temperature: bool
    reasoning_effort_requested: Optional[str]
    reasoning_enabled_false: bool
    reasoning_config_label: str
    max_tokens: int
    notes: str = ""


# Three models, lifted from the v4.1 config with verified providers.
MODELS = (
    FavoriteIntegerModel(
        label="astra",
        slug="openai/gpt-6-astra",
        display_name="GPT-6 Astra",
        preferred_provider="openai",
        supports_temperature=False,
        reasoning_effort_requested="minimal",
        reasoning_enabled_false=False,
        reasoning_config_label="R_min",
        max_tokens=1500,
        notes="CONFOUND: catalog excludes temperature. R_min = effort='minimal' surrogate "
              "(OR rejects reasoning={'enabled':false}). Same config as v4.1.",
    ),
    FavoriteIntegerModel(
        label="fable",
        slug="anthropic/claude-fable-5.1",
        display_name="Claude Fable 5.1",
        preferred_provider="anthropic",
        supports_temperature=False,
        reasoning_effort_requested="minimal",
        reasoning_enabled_false=False,
        reasoning_config_label="R_min",
        max_tokens=1500,
        notes="CONFOUND: catalog excludes temperature. R_min = effort='minimal' surrogate "
              "(reasoning mandatory on OR endpoint). Same config as v4.1.",
    ),
    FavoriteIntegerModel(
        label="oss120",
        slug="openai/gpt-oss-120b",
        display_name="OpenAI GPT-OSS-120B",
        preferred_provider="DeepInfra",
        supports_temperature=True,
        reasoning_effort_requested="low",
        reasoning_enabled_false=False,
        reasoning_config_label="R_low",
        max_tokens=4000,
        notes="DeepInfra bf16 (same provider pin as v4.1).",
    ),
)

MODELS_BY_LABEL: Dict[str, FavoriteIntegerModel] = {m.label: m for m in MODELS}
EXECUTION_ORDER = ("astra", "fable", "oss120")


# -------------------------------------------------- experimental factors --
PHASE1_REPLICATES = 5
PHASE2A_POSITIONS = (1, 2, 5, 9)             # 1-indexed into the 10-digit integer
PHASE2A_REPLICATES_PER_POSITION = 5
PHASE2B_REPLICATES = 5
PHASE1_USABILITY_THRESHOLD = 4

PHASE1_CALLS_PER_MODEL = PHASE1_REPLICATES                                           # 5
PHASE2A_CALLS_PER_MODEL = len(PHASE2A_POSITIONS) * PHASE2A_REPLICATES_PER_POSITION    # 20
PHASE2B_CALLS_PER_MODEL = PHASE2B_REPLICATES                                          # 5
TOTAL_CALLS_PER_MODEL = (PHASE1_CALLS_PER_MODEL
                          + PHASE2A_CALLS_PER_MODEL
                          + PHASE2B_CALLS_PER_MODEL)                                  # 30
TOTAL_CALLS_MAX = TOTAL_CALLS_PER_MODEL * len(MODELS)                                 # 90


# -------------------------------------------------- API settings --
TEMPERATURE_WHEN_SUPPORTED = 0.0


# -------------------------------------------------- retry --
TRANSPORT_RETRY_CAP = 3
CONTENT_RETRY_CAP = 1


# -------------------------------------------------- budget --
BUDGET_USD_CAP = 10.0


# -------------------------------------------------- seeds --
SCHEDULING_SEED = 2026101601         # distinct from v3.1 (01), ext (02), v4.1 (03)
