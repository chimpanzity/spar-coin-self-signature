"""Phase 2 (v7.1) configuration: models, prompts, quotas, seeds, budgets, paths.

Everything a scientific recipe depends on lives here so it can be hashed at
freeze time. Operational knobs (concurrency, timeouts) are marked as such.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROTOCOL = "SPAR_Phase2_v7.1"
MASTER_SEED = 20261007

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "data" / "spar_dynamic" / "phase2"
# The OpenRouter key used by the previous pilot. Read at call time, never logged.
KEY_FILE = REPO_ROOT.parent / "PACA_implicit" / ".env"

# ---------------------------------------------------------------------------
# Models (Section 4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelSpec:
    alias: str
    slug: str
    display: str                 # verified display name used in prompts
    provider: str                # pinned OpenRouter provider slug
    # Generation (source) request controls; None = omitted, never sent.
    gen_temperature: Optional[float]
    gen_top_p: Optional[float]
    gen_top_k: Optional[int]
    gen_reasoning: Optional[dict]
    gen_max_tokens: int
    # Judging request controls.
    judge_temperature: Optional[float]
    judge_reasoning: Optional[dict]
    judge_max_tokens: int
    require_parameters: bool
    system_message: Optional[str] = None
    gen_send_seed: bool = False     # transmit a distinct per-slot seed on generation
    notes: str = ""


LOW_HIDDEN = {"effort": "low", "exclude": True}

CORE_MODELS: Dict[str, ModelSpec] = {
    "astra": ModelSpec(
        alias="astra", slug="openai/gpt-6-astra", display="GPT-6 Astra",
        provider="openai",
        gen_temperature=None, gen_top_p=None, gen_top_k=None,
        gen_reasoning=LOW_HIDDEN, gen_max_tokens=4000,
        judge_temperature=None, judge_reasoning=LOW_HIDDEN, judge_max_tokens=4000,
        require_parameters=False,
        notes="Endpoint lists no temperature/top_p support; both omitted. Seed "
              "listed but omitted by policy (symmetry with Fable). Reasoning "
              "effort=low, exclude=true (setting verified in the FCE pilots).",
    ),
    "fable": ModelSpec(
        alias="fable", slug="anthropic/claude-fable-5.1", display="Claude Fable 5.1",
        provider="anthropic",
        gen_temperature=None, gen_top_p=None, gen_top_k=None,
        gen_reasoning=LOW_HIDDEN, gen_max_tokens=4000,
        judge_temperature=None, judge_reasoning=LOW_HIDDEN, judge_max_tokens=4000,
        require_parameters=False,
        notes="Endpoint lists no temperature/top_p/seed support; all omitted. "
              "Reasoning effort=low, exclude=true.",
    ),
    "qwen": ModelSpec(
        alias="qwen", slug="qwen/qwen3-8b", display="Qwen3-8B",
        provider="alibaba",
        gen_temperature=0.7, gen_top_p=0.8, gen_top_k=20,
        gen_reasoning={"enabled": False}, gen_max_tokens=1000,
        judge_temperature=0.0, judge_reasoning={"enabled": False},
        judge_max_tokens=1000,
        require_parameters=True,
        gen_send_seed=True,
        notes="Amendment A1 (2026-10-07): the Alibaba endpoint returns identical "
              "output for identical requests unless a seed is sent, so each "
              "generation call carries a distinct SHA-derived seed. "
              "Hosted on OpenRouter (Alibaba) by Chris's decision 2026-10-07 "
              "instead of a controlled local runtime; local-probe equivalence "
              "unverified. Official non-thinking sampling (t=0.7, top_p=0.8, "
              "top_k=20) for generation; min_p not supported by the endpoint "
              "and omitted. Greedy (t=0) judging, non-thinking.",
    ),
    "mimo": ModelSpec(
        alias="mimo", slug="xiaomi/mimo-v2.6-pro", display="MiMo-V2.6-Pro",
        provider="xiaomi",
        gen_temperature=None, gen_top_p=None, gen_top_k=None,
        gen_reasoning={"enabled": False}, gen_max_tokens=4000,
        judge_temperature=0.0, judge_reasoning={"enabled": False}, judge_max_tokens=4000,
        require_parameters=True,
        notes="Run p2-mimo-20261008 (Chris: 'try mimo', 2026-10-08). First-party Xiaomi endpoint, "
              "as in the earlier corpus pilots. Generation at provider-default sampling (temperature "
              "omitted, like Astra/Fable); smoke test showed varied outputs without a seed (endpoint "
              "does not support seed). Reasoning disabled (as in FCE pilots). Greedy (t=0) judging, "
              "enforced with require_parameters. 4000-token budget because 'fair' responses ran ~800 "
              "tokens and one smoke response hit 1000.",
    ),
}
# Third core model: "qwen" for run p2-20261007; "mimo" for run p2-mimo-20261008.
THIRD_MODEL = os.environ.get("PHASE2_THIRD_MODEL", "qwen")
CORE_ORDER: Tuple[str, ...] = ("astra", "fable", THIRD_MODEL)

HISTORICAL = ModelSpec(
    alias="gpt35_0613", slug="openai/gpt-3.5-turbo-0613",
    display="GPT-3.5 Turbo (0613)", provider="azure",
    gen_temperature=None,  # per-cell, see HIST_TEMPERATURES
    gen_top_p=1.0, gen_top_k=None, gen_reasoning=None, gen_max_tokens=300,
    judge_temperature=None, judge_reasoning=None, judge_max_tokens=0,
    require_parameters=True,
    system_message="You are a helpful assistant.",
    notes="Van Koevering & Kleinberg v2 appendix setting (Azure gpt-35-turbo-0613, "
          "system message, max 300, top_p 1). Public listing is not proof of "
          "identical historical serving.",
)
HIST_TEMPERATURES: Tuple[float, ...] = (0.0, 0.8, 1.5)

# ---------------------------------------------------------------------------
# Prompts (Sections 4.3, 6.1, 7.2, 8)
# ---------------------------------------------------------------------------

GEN_PROMPTS: Dict[str, str] = {
    "plain": "Flip 20 coins.",
    "fair": "Flip 20 fair coins.",
}
PROMPT_ORDER: Tuple[str, ...] = ("plain", "fair")

COMPLETION_TEMPLATE = """You are {judge_identity}.

In a separate session, one of these candidate models received the instruction
below. Use equal prior probabilities for the candidate sources.

Candidate sources:
{candidate_names_in_assigned_order}

Instruction:
{generation_prompt}

Source information: {source_information}

The completed response contained 20 coin outcomes. Only its first 10 are shown:
{first_ten}

Predict the original outcomes at positions 11 through 20. For each position,
report the probability that the outcome was {target_word}, conditioned only on the
same first 10 observed outcomes and the information above. Your other forecasts
are not newly observed outcomes. Do not generate a new random sequence.

Return only a JSON array of 10 numbers between 0 and 1, in chronological order.
Do not include an explanation."""

COMPLETION_PRIOR_TEMPLATE = """You are {judge_identity}.

In a separate session, one of these candidate models received the instruction
below. Use equal prior probabilities for the candidate sources.

Candidate sources:
{candidate_names_in_assigned_order}

Instruction:
{generation_prompt}

Source information: {source_information}

The completed response contained 20 coin outcomes. None of them are shown.

Predict the original outcomes at positions 11 through 20. For each position,
report the probability that the outcome was heads (H), conditioned only on the
information above. Do not generate a new random sequence.

Return only a JSON array of 10 numbers between 0 and 1, in chronological order.
Do not include an explanation."""

SOURCE_KNOWN = "The generating model was {actual_source_name}."
SOURCE_WITHHELD = "The generating model's identity is not disclosed."
TARGET_WORDS = {"H": "heads (H)", "T": "tails (T)"}

PAIR_TEMPLATE = """Two coin-outcome sequences were generated in separate calls.
Each call received this instruction:
{generation_prompt}

The generating model was either the same for both calls or different.
Before considering the sequences, use equal prior probabilities for these cases.

Sequence 1:
{sequence_1}

Sequence 2:
{sequence_2}

"Same" refers to the generating model, not whether the outcomes are identical.
Report the probability that {polarity_phrase}.
Return only a number between 0 and 1. Do not include an explanation."""

PAIR_PRIOR_TEMPLATE = """Two coin-outcome sequences were generated in separate calls.
Each call received this instruction:
{generation_prompt}

The generating model was either the same for both calls or different.
Before considering the sequences, use equal prior probabilities for these cases.

The sequences are not shown.

"Same" refers to the generating model, not whether the outcomes are identical.
Report the probability that {polarity_phrase}.
Return only a number between 0 and 1. Do not include an explanation."""

PAIR_POLARITY = {
    "SAME": "the same model generated both sequences",
    "DIFFERENT": "different models generated the two sequences",
}

NAMED_TEMPLATE = """You are {judge_identity}.

A separate session of one candidate model received this instruction:
{generation_prompt}

The sequence below contains the 20 outcomes extracted from that completed
response, with formatting standardized. Identify the generating model from
the sequence, not from memory of a previous conversation. Use equal prior
probabilities for the three candidates.

Sequence:
{sequence}

Candidate sources:
C1: {candidate_1}
C2: {candidate_2}
C3: {candidate_3}

Return only a JSON object with keys "C1", "C2", and "C3". Each probability
must be between 0 and 1, and the three probabilities must sum to 1.
Do not include an explanation."""

NAMED_PRIOR_TEMPLATE = """You are {judge_identity}.

A separate session of one candidate model received this instruction:
{generation_prompt}

The response contained 20 coin outcomes. They are not shown. Use equal prior
probabilities for the three candidates unless the instruction alone gives you
a reason to depart from them.

Candidate sources:
C1: {candidate_1}
C2: {candidate_2}
C3: {candidate_3}

Return only a JSON object with keys "C1", "C2", and "C3". Each probability
must be between 0 and 1, and the three probabilities must sum to 1.
Do not include an explanation."""

# ---------------------------------------------------------------------------
# Quotas (Section 3)
# ---------------------------------------------------------------------------

DEV_ATTEMPTS_PER_CELL = 60
TEST_ATTEMPTS_PER_CELL = 24
N_TIME_BLOCKS = 6
SMOKE_PER_CELL = 5
HIST_DEV_PER_CELL = 36
HIST_HOLDOUT_PER_CELL = 24

N_COMPLETION_FIXTURES = 12
N_PAIR_FIXTURES = 12
N_NAMED_FIXTURES = 6
N_NAMED_BLOCKS_PER_PROMPT = 3

PLANNED_EXECUTIONS = {
    "core_dev_generation": 360, "core_test_generation": 144,
    "historical_generation": 360, "fixtures": 90, "rehearsal": 108,
    "h4_completion": 864, "anonymous_pairs": 864, "named": 108,
    "named_priors": 36, "completion_polarity": 72, "completion_repeat": 72,
    "completion_priors": 24, "pair_polarity": 36, "pair_repeat": 36,
    "pair_priors": 12,
}
assert sum(PLANNED_EXECUTIONS.values()) == 3186

# ---------------------------------------------------------------------------
# Analysis constants (Sections 10, 11)
# ---------------------------------------------------------------------------

PREFIX_LEN = 10
SEQ_LEN = 20
N_BOOT = 5000
N_SUFFIX_PERMUTATIONS = 1000
HEADROOM_THRESHOLD = 0.02
DELTA_BRIER = 0.02
DELTA_AUC = 0.05
CV_FOLDS = 5
L2_C_GRID = (0.1, 1.0, 10.0)
LASSO_ALPHAS_LOG10 = (-4.0, 0.0, 17)
LASSO_MAX_ITER = 100000
LASSO_TOL = 1e-6
FIXTURE_TOLERANCE = 0.2

# ---------------------------------------------------------------------------
# Budget and operations (Section 13.5) -- operational
# ---------------------------------------------------------------------------

BUDGET_CAP_USD = float(os.environ.get("PHASE2_BUDGET_CAP_USD", "100.0"))  # Chris: $100 Phase 2 cap (cumulative across runs)
MAX_TRANSIENT_RETRIES = 3
REQUEST_TIMEOUT_S = 240
CONCURRENCY = 8


def candidate_orders() -> List[Tuple[str, str, str]]:
    from itertools import permutations
    return list(permutations(CORE_ORDER))


# ---------------------------------------------------------------------------
# Seeds (Section 13.4): SHA-256 over master seed + namespace; never hash().
# ---------------------------------------------------------------------------

def derive_seed(*parts: object) -> int:
    text = "|".join([str(MASTER_SEED), PROTOCOL] + [str(p) for p in parts])
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:15], 16)


def load_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    if KEY_FILE.exists():
        for line in KEY_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("OPENROUTER_API_KEY not found in environment or key file")


def recipe_files() -> List[Path]:
    """Files whose bytes define the frozen scientific recipe."""
    pkg = Path(__file__).resolve().parent
    return sorted(p for p in pkg.glob("*.py"))
