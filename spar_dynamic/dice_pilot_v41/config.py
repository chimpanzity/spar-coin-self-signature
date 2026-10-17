"""Frozen configuration for DICE_PILOT_v4.1.

One reasoning configuration per model, pinned provider (resolved during the
unpaid preflight step), per-model output-token limit, three Phase-2
conditions per model.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class ModelV41:
    label: str                      # short name used in trial IDs
    slug: str                       # OpenRouter model id
    display_name: str
    preferred_provider: Optional[str]       # None at config time; resolved by preflight
    supports_temperature: bool
    reasoning_effort_requested: Optional[str]       # "minimal" / "low" / None (qwen uses disable)
    reasoning_enabled_false: bool           # True iff this model should request reasoning={"enabled":false}
    reasoning_config_label: str             # "R_min" / "R_low" / "R_qwen_default"
    max_tokens: int                         # per spec §3.2: 4000 default, 8000 for Qwen
    notes: str = ""


# Resolved from OpenRouter catalog on 2026-10-15.
MODELS = (
    ModelV41(
        label="astra",
        slug="openai/gpt-6-astra",
        display_name="GPT-6 Astra",
        preferred_provider="openai",         # single provider on OR
        supports_temperature=False,
        reasoning_effort_requested="minimal",
        reasoning_enabled_false=False,
        reasoning_config_label="R_min",
        max_tokens=1500,                      # 65x the 23-token sample max; v3.1 fit in 1024
        notes="Catalog excludes 'temperature'. Reasoning mandatory; R_min = effort='minimal'. "
              "max_tokens=1500 chosen to fit budget cap; observed samples <=23 output tokens.",
    ),
    ModelV41(
        label="fable",
        slug="anthropic/claude-fable-5.1",
        display_name="Claude Fable 5.1",
        preferred_provider="anthropic",
        supports_temperature=False,
        reasoning_effort_requested="minimal",
        reasoning_enabled_false=False,
        reasoning_config_label="R_min",
        max_tokens=1500,
        notes="Catalog excludes 'temperature'. Reasoning mandatory on OR endpoint. "
              "max_tokens=1500 chosen to fit budget cap; observed samples <=21 output tokens.",
    ),
    ModelV41(
        label="sonnet",
        slug="anthropic/claude-sonnet-5.5",
        display_name="Claude Sonnet 5.5",
        preferred_provider="anthropic",
        supports_temperature=False,
        reasoning_effort_requested="minimal",
        reasoning_enabled_false=False,
        reasoning_config_label="R_min",
        max_tokens=1500,
        notes="Catalog excludes 'temperature'. Reasoning mandatory on OR endpoint "
              "(confirmed 2026-10-15 ext smoke test). max_tokens=1500; observed samples <=21.",
    ),
    ModelV41(
        label="oss120",
        slug="openai/gpt-oss-120b",
        display_name="OpenAI GPT-OSS-120B",
        preferred_provider="DeepInfra",       # bf16 (best quantization available for consistency with Qwen)
        supports_temperature=True,
        reasoning_effort_requested="low",
        reasoning_enabled_false=False,
        reasoning_config_label="R_low",
        max_tokens=4000,
        notes="Pinned to DeepInfra bf16 for highest-fidelity serving (vs other providers' "
              "int4/fp4 quantization). Observed samples <=88 output tokens, 0 reasoning.",
    ),
    ModelV41(
        label="oss20",
        slug="openai/gpt-oss-20b",
        display_name="OpenAI GPT-OSS-20B",
        preferred_provider="DekaLLM",         # bf16 (switched from DeepInfra after 429 rate limits on 2026-10-16)
        supports_temperature=True,
        reasoning_effort_requested="low",
        reasoning_enabled_false=False,
        reasoning_config_label="R_low",
        max_tokens=4000,
        notes="Pinned to DekaLLM bf16 (initial DeepInfra attempt failed with upstream 429 "
              "rate limit, 4/5 Phase 1 abandoned). DekaLLM also bf16 per OR endpoints catalog.",
    ),
    ModelV41(
        label="qwen",
        slug="qwen/qwen3-32b",
        display_name="Qwen3 32B",
        preferred_provider="DeepInfra",       # fp8 (only fp8 available for qwen3-32b)
        supports_temperature=True,
        reasoning_effort_requested=None,
        reasoning_enabled_false=True,         # genuine /no_think via reasoning.enabled=false
        reasoning_config_label="R_qwen_default",
        max_tokens=8000,                      # per spec §3.2
        notes="Hybrid-thinking model with genuine /no_think disable; "
              "label R_qwen_default per spec §2 unless disabling verified. "
              "DeepInfra fp8 (only quant available for qwen3-32b). "
              "Observed samples up to 1811 output + 1861 reasoning tokens.",
    ),
)

MODELS_BY_LABEL: Dict[str, ModelV41] = {m.label: m for m in MODELS}
EXECUTION_ORDER = ("astra", "fable", "sonnet", "oss120", "oss20", "qwen")


# -------------------------------------------------- experimental factors --
PHASE1_REPLICATES = 5
PHASE2A_REPLICATES = 5                  # original wording at position 2
PHASE2B_POSITIONS = (1, 2, 5, 9)        # revised wording, four positions
PHASE2B_REPLICATES_PER_POSITION = 5
PHASE2C_REPLICATES = 5                  # full-sequence reenactment

# Usability gate (spec §5): ≥4 of 5 Phase-1 batches valid.
PHASE1_USABILITY_THRESHOLD = 4

# Call counts per model
PHASE1_CALLS_PER_MODEL = PHASE1_REPLICATES                            # 5
PHASE2A_CALLS_PER_MODEL = PHASE2A_REPLICATES                           # 5
PHASE2B_CALLS_PER_MODEL = len(PHASE2B_POSITIONS) * PHASE2B_REPLICATES_PER_POSITION  # 20
PHASE2C_CALLS_PER_MODEL = PHASE2C_REPLICATES                           # 5
TOTAL_CALLS_PER_MODEL = (PHASE1_CALLS_PER_MODEL + PHASE2A_CALLS_PER_MODEL
                          + PHASE2B_CALLS_PER_MODEL + PHASE2C_CALLS_PER_MODEL)   # 35
TOTAL_CALLS_MAX = TOTAL_CALLS_PER_MODEL * len(MODELS)                             # 210


# -------------------------------------------------- API settings --
TEMPERATURE_WHEN_SUPPORTED = 0.0


# -------------------------------------------------- retry policy --
TRANSPORT_RETRY_CAP = 3
CONTENT_RETRY_CAP = 1


# -------------------------------------------------- budget --
BUDGET_USD_CAP = 10.0


# -------------------------------------------------- seeds --
SCHEDULING_SEED = 2026101503        # distinct from v3.1 (01) and ext (02)
