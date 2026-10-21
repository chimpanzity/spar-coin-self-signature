"""Frozen configuration for DICE_PILOT_EXT_v1.0.

One reasoning configuration per model.
Labels follow spec §4: `R_low` where reasoning cannot be genuinely disabled.
Final label per model is confirmed by a smoke test in the preflight step.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class ExtModel:
    label: str                      # short name used in trial IDs
    slug: str                       # OpenRouter model id
    display_name: str
    preferred_provider: str         # provider pin (spec §3); may be empty if the model is single-provider
    supports_temperature: bool      # confirmed from catalog at preflight time
    supports_reasoning_disable: Optional[bool]  # None until the paid smoke test
    reasoning_effort_requested: str # e.g. "minimal", "low"; actual value sent at run time
    reasoning_config_label: str     # e.g. "R_low", "R_min"; what the trial-id uses
    notes: str = ""


# Resolved from OpenRouter catalog on 2026-10-15.
MODELS = (
    ExtModel(
        label="oss120",
        slug="openai/gpt-oss-120b",
        display_name="OpenAI GPT-OSS-120B",
        preferred_provider="",      # provider pin resolved at paid preflight (open-weight; multi-provider)
        supports_temperature=True,
        supports_reasoning_disable=None,
        reasoning_effort_requested="low",   # §4: prefer lowest supported; "low" is the smallest effort value we assume safe
        reasoning_config_label="R_low",
        notes="Open-weight; OpenRouter supported_parameters includes temperature. "
              "Smoke test should attempt reasoning={'enabled':false} to determine "
              "whether a genuine off switch exists. If disable rejected, keep R_low.",
    ),
    ExtModel(
        label="oss20",
        slug="openai/gpt-oss-20b",
        display_name="OpenAI GPT-OSS-20B",
        preferred_provider="",
        supports_temperature=True,
        supports_reasoning_disable=None,
        reasoning_effort_requested="low",
        reasoning_config_label="R_low",
        notes="Open-weight sibling of OSS-120. Same preflight requirements.",
    ),
    ExtModel(
        label="sonnet",
        slug="anthropic/claude-sonnet-5.5",
        display_name="Anthropic Claude Sonnet 5.5",
        preferred_provider="anthropic",
        supports_temperature=False,       # §4 CONFOUND: catalog does not expose 'temperature'
        supports_reasoning_disable=None,
        reasoning_effort_requested="minimal",   # Fable-family precedent: 'minimal' is the lowest supported effort
        reasoning_config_label="R_min",
        notes="Anthropic frontier sibling of Fable. Catalog lacks 'temperature' — "
              "spec §4 explicitly flags this as needing approval. Based on fable precedent, "
              "'reasoning={enabled:false}' is likely rejected on the OR endpoint.",
    ),
)

MODELS_BY_LABEL: Dict[str, ExtModel] = {m.label: m for m in MODELS}
EXECUTION_ORDER = ("oss120", "oss20", "sonnet")


# -------------------------------------------------- experimental factors --
PHASE1_REPLICATES = 5
PHASE2_POSITIONS = (1, 2, 5, 9)
PHASE2_REPLICATES_PER_POSITION = 5
PHASE1_USABILITY_THRESHOLD = 4

PHASE1_CALLS_PER_MODEL = PHASE1_REPLICATES
PHASE2_CALLS_PER_MODEL = len(PHASE2_POSITIONS) * PHASE2_REPLICATES_PER_POSITION
TOTAL_CALLS_PER_MODEL = PHASE1_CALLS_PER_MODEL + PHASE2_CALLS_PER_MODEL   # 25
TOTAL_CALLS_MAX = TOTAL_CALLS_PER_MODEL * len(MODELS)                      # 75


# -------------------------------------------------- API settings --
TEMPERATURE_WHEN_SUPPORTED = 0.0
MAX_TOKENS = 1024                   # per spec §8: adequate for OSS reasoning expansion


# -------------------------------------------------- retry policy --
TRANSPORT_RETRY_CAP = 3
CONTENT_RETRY_CAP = 1


# -------------------------------------------------- budget guardrail --
BUDGET_USD_CAP = 10.0           # §12: separate $10 ceiling for the extension


# -------------------------------------------------- seeds --
SCHEDULING_SEED = 2026101502    # distinct from v3.1's 2026101501
