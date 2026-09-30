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

# Stimulus corpus (pilot 5) uses a different 3rd model. Kept separate so the
# pilot-1..4 MODELS constant stays byte-stable for backwards compatibility.
# NOTE: Original spec proposed mistral-small; seven candidate 3rd models failed
# the strict 100-char batch preflight (mistral x3, gemma, llama-3.3-70b,
# llama-4-maverick, deepseek-v3.1, nemotron-3-super). Only mimo-v2.6-pro
# produced a valid 100-char batch response (1/5 in smoke), so we accept it as
# a low-success-rate 3rd model and compensate with per-trajectory retry
# headroom (CORPUS_BATCH_MAX_ATTEMPTS bumped) rather than swapping in yet
# another candidate.
CORPUS_MODELS = (
    ModelSpec("astra", "openai/gpt-6-astra"),
    ModelSpec("fable", "anthropic/claude-fable-5.1"),
    ModelSpec("mimo",  "xiaomi/mimo-v2.6-pro"),
)
CORPUS_MODEL_LABELS = tuple(m.label for m in CORPUS_MODELS)
CORPUS_MODEL_BY_LABEL = {m.label: m for m in CORPUS_MODELS}

# Per-model max_tokens override for the corpus. Smaller/non-reasoning models
# don't need as much headroom as the flagship reasoning models.
CORPUS_MODEL_MAX_TOKENS_BATCH_OVERRIDE = {
    "mimo": 2048,   # batch smoke: successful attempt used ~200 completion tokens; keep headroom
}
CORPUS_MODEL_MAX_TOKENS_STEP_OVERRIDE = {
    "mimo": 256,    # single H/T needs almost nothing; small ceiling keeps cost floor low
}

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


# =============================================================================
# Pilot 2: SELF vs OTHER — Loula-Experiment-1 analogue.
# Reuses the exact 60 source trajectories generated by the pilot-1 dynamic run.
# Uses plain-text one-word responses (deliberately not JSON schema) to sidestep
# structured-output problems observed for qwen in pilot 1.
# =============================================================================

SELF_OTHER_TAG = "spar_self_other_pilot_v1"
SELF_OTHER_BUDGET_USD = 10.0
SELF_OTHER_STOP_AT_PROJECTED_USD = 10.0

# 10 SELF + 10 OTHER = 20 trials per (judge x architecture); 3 judges x 2 archs = 120 trials.
SELF_OTHER_TRIALS_PER_LABEL = 10
SELF_OTHER_OTHER_FROM_EACH_NON_SELF = 5
SELF_OTHER_MAX_TOKENS = 2048   # bumped from 512 after qwen smoke used ~1975 reasoning tokens
SELF_OTHER_MAX_JUDGMENT_ATTEMPTS = 3

SELF_OTHER_PROMPT_TEMPLATE = (
    "The binary sequence below was generated by an LLM performing a fair-coin "
    "simulation task.\n\n"
    "Sequence:\n{sequence}\n\n"
    "Was this sequence generated by the same underlying model as you, or by a "
    "different underlying model?\n\n"
    "Respond with exactly one word: SELF or OTHER."
)

# Fixed seed for trial construction (per-judge-per-architecture blocks are
# derived deterministically from this).
SELF_OTHER_CONSTRUCTION_SEED = 20260929


# =============================================================================
# Pilot 3: Provenance-manipulation SELF/OTHER (2 x 2 x 2 design)
# Source identity (SELF/OTHER) x actual architecture (batch/online) x stated
# architecture (told-batch/told-online). Same 60 source trajectories reused.
# Each unique trajectory shown twice — once told-batch, once told-online —
# in fresh stateless calls.
# =============================================================================

PROVENANCE_TAG = "spar_provenance_self_attribution_pilot_v1"
PROVENANCE_BUDGET_USD = 10.0
PROVENANCE_STOP_AT_PROJECTED_USD = 10.0

# Per judge: 10 SELF batch + 10 SELF online + 10 OTHER batch + 10 OTHER online = 40 unique trajectories
# Each shown twice (told-batch, told-online) = 80 trials per judge
# 3 judges = 240 trials total. 8 cells x 10 = 80 per judge.
PROVENANCE_UNIQUE_TRAJECTORIES_PER_CELL = 10
PROVENANCE_OTHER_FROM_EACH_NON_SELF_PER_ARCH = 5
PROVENANCE_MAX_TOKENS = 4096     # bumped from 2048 after 2 qwen trials abandoned at 2048
PROVENANCE_MAX_JUDGMENT_ATTEMPTS = 3
PROVENANCE_CONSTRUCTION_SEED = 20260929
PROVENANCE_MIN_PAIR_SEPARATION = 5   # minimum trials between two versions of the same trajectory

# Neutral, parallel-worded stated-architecture sentences (frozen).
PROVENANCE_STATED_BATCH = (
    "This sequence was generated by an LLM in a single call that simulated "
    "all 50 fair-coin flips at once."
)
PROVENANCE_STATED_ONLINE = (
    "This sequence was generated by an LLM across 50 separate calls that "
    "simulated one fair-coin flip per call, with the complete preceding "
    "flip history provided on each call."
)

PROVENANCE_PROMPT_TEMPLATE = (
    "{stated_sentence}\n\n"
    "Sequence:\n{sequence}\n\n"
    "Was this sequence generated by the same underlying model as you, or by a "
    "different underlying model?\n\n"
    "Respond with exactly one word: SELF or OTHER."
)


def provenance_prompt(sequence: str, stated_arch: str) -> str:
    stated = PROVENANCE_STATED_BATCH if stated_arch == "batch" else PROVENANCE_STATED_ONLINE
    return PROVENANCE_PROMPT_TEMPLATE.format(stated_sentence=stated, sequence=sequence)


# =============================================================================
# Pilot 4: Astra-only provenance replication (with no-provenance control).
# Fresh independent source trajectories. Astra is the only judge.
# 3 conditions per trajectory: told-batch, told-online, no-provenance.
# =============================================================================

ASTRA_FOLLOWUP_TAG = "spar_astra_provenance_replication_v1"
ASTRA_FOLLOWUP_BUDGET_USD = 10.0
ASTRA_FOLLOWUP_STOP_AT_PROJECTED_USD = 10.0

# Fresh source counts per model per architecture.
# NOTE: Redesign — dropped Qwen from OTHER pool after qwen batch showed
# ~1.5% success rate at temp 0.3 (down from ~10% in pilot 1). Rebalanced
# so OTHER = 20 fable trajectories (10 batch + 10 online), matching SELF's
# 20 astra trajectories. Cost of losing the Fable-vs-Qwen OTHER breakdown
# is documented in the report.
ASTRA_FOLLOWUP_ASTRA_TRAJ_PER_ARCH = 10
ASTRA_FOLLOWUP_FABLE_TRAJ_PER_ARCH = 10
ASTRA_FOLLOWUP_QWEN_TRAJ_PER_ARCH = 0
# per-model counts lookup for source generation
ASTRA_FOLLOWUP_SOURCE_COUNTS = {
    "astra": ASTRA_FOLLOWUP_ASTRA_TRAJ_PER_ARCH,
    "fable": ASTRA_FOLLOWUP_FABLE_TRAJ_PER_ARCH,
    "qwen":  ASTRA_FOLLOWUP_QWEN_TRAJ_PER_ARCH,
}

ASTRA_FOLLOWUP_MAX_TOKENS = 4096   # matches pilot-3 ceiling (qwen needs headroom)
ASTRA_FOLLOWUP_MAX_JUDGMENT_ATTEMPTS = 3
ASTRA_FOLLOWUP_CONSTRUCTION_SEED = 20260930
ASTRA_FOLLOWUP_MIN_REPEAT_SEPARATION = 5

# The three stated conditions for pilot 4.
STATED_CONDITIONS = ("told_batch", "told_online", "no_provenance")

# Prompt for the no-provenance condition. Identical to pilot 2's SELF/OTHER prompt.
ASTRA_FOLLOWUP_NO_PROV_PROMPT_TEMPLATE = (
    "The binary sequence below was generated by an LLM performing a fair-coin "
    "simulation task.\n\n"
    "Sequence:\n{sequence}\n\n"
    "Was this sequence generated by the same underlying model as you, or by a "
    "different underlying model?\n\n"
    "Respond with exactly one word: SELF or OTHER."
)


def astra_followup_prompt(sequence: str, stated_condition: str) -> str:
    if stated_condition == "told_batch":
        return PROVENANCE_PROMPT_TEMPLATE.format(
            stated_sentence=PROVENANCE_STATED_BATCH, sequence=sequence)
    if stated_condition == "told_online":
        return PROVENANCE_PROMPT_TEMPLATE.format(
            stated_sentence=PROVENANCE_STATED_ONLINE, sequence=sequence)
    if stated_condition == "no_provenance":
        return ASTRA_FOLLOWUP_NO_PROV_PROMPT_TEMPLATE.format(sequence=sequence)
    raise ValueError(f"unknown stated_condition: {stated_condition!r}")


# =============================================================================
# Pilot 5: SPAR Stimulus Corpus — 3 models x 3 generation methods x 10 traj x 100 flips.
# No judgments — this is a stimulus-generation study only.
# Preserves prior source-generation settings for astra/fable; adds a new
# `independent_calls` method (fresh stateless call with identical prompt every trial).
# =============================================================================

STIMULUS_CORPUS_TAG = "spar_stimulus_corpus_v1"
# Budget bumped from $25 -> $60 to cover doubled trajectory count (10 -> 20 per
# cell) plus mimo batch retry headroom. User authorized the scale-up.
STIMULUS_CORPUS_BUDGET_USD = 60.0
STIMULUS_CORPUS_STOP_AT_PROJECTED_USD = 60.0

CORPUS_SEQUENCE_LENGTH = 100
# Bumped from 10 to 20 per cell per user direction ("20 valid 100-char strings
# with each of the three methods ... just keep going until you get all 180").
CORPUS_TRAJECTORIES_PER_CELL = 20
CORPUS_GENERATION_METHODS = ("batch", "history_conditioned", "independent_calls")
CORPUS_PREFIX_LENGTHS = (20, 50, 100)

# Preserves prior batch wording exactly, changing only 50 -> 100.
CORPUS_BATCH_PROMPT = (
    "Simulate 100 flips of a fair coin. Return exactly 100 outcomes as a "
    "single string containing only H and T. Do not include spaces, "
    "punctuation, numbering, or explanation."
)

# Preserves prior history-conditioned wording verbatim; unchanged from pilot 1's
# online generation. History grows to 99 chars by trial 100.
CORPUS_HISTORY_TRIAL1_PROMPT = ONLINE_TRIAL1_PROMPT   # exact reuse
def corpus_history_trial_prompt(history: str) -> str:
    return online_trial_prompt(history)               # exact reuse

# Independent-calls prompt: same fixed prompt every trial. No history, no trial
# index, no positional hints. Per spec section 10.
CORPUS_INDEPENDENT_CALLS_PROMPT = (
    "Simulate one fair coin flip.\n\n"
    "Respond with exactly one character: H or T."
)

CORPUS_BATCH_MAX_TOKENS = 2048         # same as pilot 1 (used for astra/fable batch)
CORPUS_STEP_MAX_TOKENS = 1024          # same as pilot 1 online step (astra/fable)
CORPUS_STEP_MAX_ATTEMPTS = 3           # per spec section 13
# Bumped from 3 to 25 because mimo produces valid 100-char batches only ~1/5
# of the time in smoke. Astra/fable succeed on attempt 1 in the vast majority
# of cases so the higher ceiling only spends money for mimo cells.
CORPUS_BATCH_MAX_ATTEMPTS = 25
# Compliance preflight thresholds (spec section 14) — apply to the 3rd model
# whichever it is. Kept as spec required.
CORPUS_THIRD_MODEL_PREFLIGHT_MIN_STEP_ACCURACY = 0.95
CORPUS_THIRD_MODEL_PREFLIGHT_MIN_BATCH_VALID = 2   # of 3 attempts
# Backwards-compat aliases (older tests / imports)
CORPUS_MISTRAL_MAX_TOKENS = 512
CORPUS_MISTRAL_PREFLIGHT_MIN_STEP_ACCURACY = CORPUS_THIRD_MODEL_PREFLIGHT_MIN_STEP_ACCURACY
CORPUS_MISTRAL_PREFLIGHT_MIN_BATCH_VALID = CORPUS_THIRD_MODEL_PREFLIGHT_MIN_BATCH_VALID


def corpus_max_tokens_batch(model_label: str) -> int:
    return CORPUS_MODEL_MAX_TOKENS_BATCH_OVERRIDE.get(model_label, CORPUS_BATCH_MAX_TOKENS)


def corpus_max_tokens_step(model_label: str) -> int:
    return CORPUS_MODEL_MAX_TOKENS_STEP_OVERRIDE.get(model_label, CORPUS_STEP_MAX_TOKENS)
CORPUS_SOURCE_CONCURRENCY = 3          # concurrent trajectories
CORPUS_EXECUTION_SEED = 20260929
CORPUS_MAX_INVALID_TRAJECTORIES_PER_CELL = 3

# Corpus compilation — dev/holdout split.
# Frozen seed, used only for the stratified random 10/10 split within each
# (model, method) cell. Kept separate from CORPUS_EXECUTION_SEED so the split
# is independent of the execution shuffle.
CORPUS_SPLIT_SEED = 20260930
CORPUS_DEV_PER_CELL = 10
CORPUS_HOLDOUT_PER_CELL = 10
