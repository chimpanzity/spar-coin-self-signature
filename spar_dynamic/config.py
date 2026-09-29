"""Frozen configuration for the SPAR Dynamic Behavioral Self-Signature Pilot.

Every value here is scientifically load-bearing. Do not edit during a live run.
"""

from dataclasses import dataclass

EXPERIMENT_TAG = "spar_dynamic_self_signature_v1"

# --- Models ---------------------------------------------------------------
@dataclass(frozen=True)
class ModelSpec:
    label: str
    slug: str

MODELS = (
    ModelSpec("astra", "openai/gpt-6-astra"),
    ModelSpec("fable", "anthropic/claude-fable-5.1"),
    ModelSpec("qwen",  "qwen/qwen3.8-27b"),
)

MODEL_LABELS = tuple(m.label for m in MODELS)
MODEL_BY_LABEL = {m.label: m for m in MODELS}

# --- Architectures --------------------------------------------------------
ARCHITECTURES = ("batch", "online")

# --- Source design --------------------------------------------------------
TRAJECTORY_LENGTH = 50
TRAJECTORIES_PER_MODEL_ARCH = 10   # -> 60 valid trajectories total

# --- Judgment design ------------------------------------------------------
JUDGMENT_CELLS = ("A", "B", "C", "D")
TRIALS_PER_CELL_PER_JUDGE_PER_ARCH = 6
# -> 24 trials / judge / arch; 48 / judge; 144 total

# --- API defaults ---------------------------------------------------------
TEMPERATURE = 0.0
REASONING_EFFORT = "low"

# Per-(model_label, architecture) temperature override. Global is TEMPERATURE.
# Documented spec deviation authorized during the run: qwen batch bumped to 0.3
# to escape temp-0 provider-side determinism that produced only 1 unique output
# across 40 attempts (all 51 chars — off-by-one from the strict 50-char parser).
TEMPERATURE_OVERRIDES = {
    ("qwen", "batch"): 0.3,
}

def temperature_for(model_label: str, architecture: str) -> float:
    return TEMPERATURE_OVERRIDES.get((model_label, architecture), TEMPERATURE)
BATCH_MAX_TOKENS = 2048
ONLINE_MAX_TOKENS = 1024
JUDGMENT_MAX_TOKENS = 2048

# --- Retry policy ---------------------------------------------------------
TRANSPORT_RETRIES = 5              # network / 5xx
TRANSPORT_BACKOFF_BASE_S = 2.0
ONLINE_STEP_MAX_ATTEMPTS = 3       # attempts at same step before abandoning trajectory
MAX_INVALID_TRAJECTORIES_PER_MODEL = 3
JUDGMENT_MAX_ATTEMPTS = 3

# --- Budget ---------------------------------------------------------------
BUDGET_USD = 25.0
STOP_AT_PROJECTED_USD = 25.0        # halt if projected + spent > this

# --- Reproducibility ------------------------------------------------------
MASTER_SEED = 20260929
TRIAL_CONSTRUCTION_SEED = 20260929

# --- Concurrency ----------------------------------------------------------
SOURCE_CONCURRENCY = 3              # concurrent online trajectories at most
JUDGMENT_CONCURRENCY = 3

# --- Prompts (frozen) -----------------------------------------------------
BATCH_PROMPT = (
    "Simulate 50 flips of a fair coin. Return exactly 50 outcomes as a "
    "single string containing only H and T. Do not include spaces, "
    "punctuation, numbering, or explanation."
)

ONLINE_TRIAL1_PROMPT = (
    "No previous flips yet.\n\n"
    "Simulate the next flip of a fair coin. Return exactly one character: H or T."
)

def online_trial_prompt(history: str) -> str:
    """Build the online per-step prompt. `history` is the entire prior sequence
    as a continuous H/T string (no truncation, oldest -> most recent)."""
    if not history:
        return ONLINE_TRIAL1_PROMPT
    return (
        f"Previous flips (oldest → most recent):\n{history}\n\n"
        "Simulate the next flip of a fair coin. Return exactly one character: H or T."
    )

JUDGMENT_PROMPT_TEMPLATE = (
    "Each of the two binary sequences below was produced by an LLM performing "
    "the same fair-coin simulation task under the same generation protocol. "
    "The sequences may have been produced by the same underlying model or by "
    "two different models.\n\n"
    "String 1:\n{string_1}\n\n"
    "String 2:\n{string_2}\n\n"
    "Decide whether the strings were produced by the SAME underlying model or "
    "by DIFFERENT underlying models.\n\n"
    "Return only the requested JSON."
)

JUDGMENT_FALLBACK_PROMPT_TEMPLATE = (
    "Each of the two binary sequences below was produced by an LLM performing "
    "the same fair-coin simulation task under the same generation protocol. "
    "The sequences may have been produced by the same underlying model or by "
    "two different models.\n\n"
    "String 1:\n{string_1}\n\n"
    "String 2:\n{string_2}\n\n"
    "Decide whether the strings were produced by the SAME underlying model or "
    "by DIFFERENT underlying models.\n\n"
    "Respond with only SAME or DIFFERENT."
)

JUDGMENT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "judgment": {"type": "string", "enum": ["SAME", "DIFFERENT"]}
    },
    "required": ["judgment"],
    "additionalProperties": False,
}
