"""Frozen configuration for the dice-pilot (DICE_PILOT_v3.1)."""

from dataclasses import dataclass


# -------------------------------------------------- model + capability --
@dataclass(frozen=True)
class DiceModel:
    label: str              # internal short name
    slug: str               # OpenRouter model id
    display_name: str
    preferred_provider: str
    # Capability flags resolved from catalog on 2026-10-15. Verified-at-run
    # time by the capability preflight step; do NOT trust these at paid
    # dispatch time without re-running the catalog check.
    supports_temperature: bool
    supports_reasoning: bool
    r0_supported: bool      # whether a GENUINE reasoning-off switch exists
    r1_supported: bool      # whether reasoning-enabled is callable
    notes: str = ""


MODELS = (
    DiceModel(
        label="astra",
        slug="openai/gpt-6-astra",
        display_name="GPT-6 Astra",
        preferred_provider="openai",
        supports_temperature=False,
        supports_reasoning=True,
        # Astra R0 is NOT a genuine reasoning-off switch. User-approved
        # substitution 2026-10-15: use reasoning_effort="minimal" and label
        # the astra R0 vs R1 comparison as CONFOUNDED in the final report.
        # Both astra R0 and astra R1 remain reasoning-enabled; the "off"
        # column is a lower-effort surrogate.
        r0_supported=True,
        r1_supported=True,
        notes="OpenRouter supported_parameters excludes 'temperature'. "
              "Spec confound: provider default sampling. User-approved "
              "spec-§4 deviation: astra R0 uses reasoning_effort=\"minimal\" "
              "as a low-effort surrogate for the (nonexistent) off switch. "
              "The astra R0 vs R1 comparison is CONFOUNDED and must be "
              "labeled as such in the pilot report.",
    ),
    DiceModel(
        label="fable",
        slug="anthropic/claude-fable-5.1",
        display_name="Claude Fable 5.1",
        preferred_provider="anthropic",
        supports_temperature=False,
        supports_reasoning=True,
        # 2026-10-15 run-time discovery: OpenRouter rejects
        # reasoning={'enabled': false} for fable with 400 "Reasoning is
        # mandatory for this endpoint and cannot be disabled." The spec-§4
        # "genuine off" is unavailable. User-approved substitution
        # (parallel to astra R0): fable R0 uses reasoning_effort="minimal"
        # as a low-effort surrogate. fable R0 vs R1 comparison labeled
        # CONFOUNDED in the pilot report.
        r0_supported=True,
        r1_supported=True,
        notes="OpenRouter supported_parameters excludes 'temperature'. "
              "Reasoning is mandatory on the OR endpoint (confirmed 2026-10-15); "
              "fable R0 uses reasoning_effort=\"minimal\" surrogate per user "
              "approval. fable R0 vs R1 is CONFOUNDED and must be labeled.",
    ),
    DiceModel(
        label="qwen",
        slug="qwen/qwen3-32b",
        display_name="Qwen3 32B",
        preferred_provider="",      # resolved at run time; open-weight model, multiple providers
        supports_temperature=True,
        supports_reasoning=True,
        r0_supported=True,         # Qwen3 hybrid-thinking: /no_think disables genuinely
        r1_supported=True,
        notes="Open-weight (HF). Supports temperature=0 directly. Hybrid-thinking model: "
              "/no_think toggle (exposed via reasoning={'enabled': false}) disables "
              "thinking tokens. Spec order: Qwen last to isolate any parsing issues.",
    ),
)

MODELS_BY_LABEL = {m.label: m for m in MODELS}
EXECUTION_ORDER = ("astra", "fable", "qwen")


# -------------------------------------------------- experimental factors --
PHASE1_REPLICATES = 5
PHASE2_POSITIONS = (1, 2, 5, 9)      # 1-indexed
PHASE2_REPLICATES_PER_POSITION = 5
REASONING_CONFIGS = ("R0", "R1")      # R0 = disabled, R1 = enabled medium

# Phase 1 usability gate (spec §5): ≥4 of 5 valid Phase-1 batches to proceed
PHASE1_USABILITY_THRESHOLD = 4

# Call counts per model × config
PHASE1_CALLS_PER_CONFIG = PHASE1_REPLICATES                       # 5
PHASE2_CALLS_PER_CONFIG = len(PHASE2_POSITIONS) * PHASE2_REPLICATES_PER_POSITION  # 20
TOTAL_CALLS_PER_CONFIG = PHASE1_CALLS_PER_CONFIG + PHASE2_CALLS_PER_CONFIG        # 25

# -------------------------------------------------- API settings --
# Spec: temperature 0 where supported; max_tokens tight enough to make the
# $25 ceiling defensible against reasoning blow-ups.
TEMPERATURE_WHEN_SUPPORTED = 0.0

# For R1 (reasoning enabled) the spec requests medium effort "when available".
# All three target models' OR schemas expose reasoning_effort.
REASONING_EFFORT_R1 = "medium"

# Max output tokens (hard cap on reasoning + completion billing per call).
# 1024 is enough for Phase 1 (10 integers + modest reasoning) and Phase 2
# (one integer + modest reasoning), while keeping worst-case per-call cost
# under ~$0.06 for the most expensive model (astra/fable).
MAX_TOKENS = 1024


# -------------------------------------------------- retry policy --
# Spec §6: bounded transport retries; at most one identical content retry
# for malformed responses; no auto-retry on declines.
TRANSPORT_RETRY_CAP = 3
CONTENT_RETRY_CAP = 1               # one identical retry on malformed/parsing-failed content


# -------------------------------------------------- budget guardrail --
BUDGET_USD_CAP = 25.0
PER_CALL_WORST_CASE_FLOOR_USD = 0.0001  # min reservation; real reservation computed per call


# -------------------------------------------------- seeds --
# Scheduling (Phase-2 position/replicate randomization within each config).
SCHEDULING_SEED = 2026101501


# -------------------------------------------------- derived counts --
def total_calls_max() -> int:
    """Upper bound on experimental calls assuming every (model, config) runs."""
    # Spec §2: 3 × 2 × 25 = 150. If a config is marked unsupported it is dropped.
    n = 0
    for m in MODELS:
        if m.r0_supported: n += TOTAL_CALLS_PER_CONFIG
        if m.r1_supported: n += TOTAL_CALLS_PER_CONFIG
    return n


def calls_from_capability_table() -> int:
    """Expected call count given the as-of-2026-10-15 capability flags.

    - astra: R0 unsupported, R1 supported → 25 calls
    - fable: R0 supported, R1 supported     → 50 calls
    - qwen:  R0 supported, R1 supported     → 50 calls
    Expected total: 125 calls (not 150).
    """
    return total_calls_max()
