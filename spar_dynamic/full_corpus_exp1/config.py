"""Frozen configuration for FCE1 — see spec sections 2, 5, 7-9, 10, 14, 15, 18."""

from dataclasses import dataclass

# -- Section 2: model registry -----------------------------------------------
@dataclass(frozen=True)
class JudgeSpec:
    label: str            # internal label (astra, fable, mimo)
    slug: str             # OpenRouter API model id
    display_name: str     # exact string shown to models in NAMED prompts
    preferred_provider: str  # section 11; verified against catalog at run time

# NOTE: `preferred_provider` is the OpenRouter *routing id* for the pin, which
# is lowercase (not the capitalized display name that appears in responses).
# Verified against OpenRouter 404 responses on 2026-10-01: pinning requires
# ids like `openai`, `anthropic`, `xiaomi/fp8`. The display name `OpenAI`
# (etc.) is what shows up in `response.provider`.
JUDGES = (
    JudgeSpec("astra", "openai/gpt-6-astra",         "GPT-6 Astra",      "openai"),
    JudgeSpec("fable", "anthropic/claude-fable-5.1", "Claude Fable 5.1", "anthropic"),
    JudgeSpec("mimo",  "xiaomi/mimo-v2.6-pro",       "MiMo V2.6 Pro",    "xiaomi/fp8"),
)
JUDGE_LABELS = tuple(j.label for j in JUDGES)
JUDGE_BY_LABEL = {j.label: j for j in JUDGES}
LABEL_BY_SLUG = {j.slug: j.label for j in JUDGES}

# -- Section 3: default source method is history_conditioned (FCE1 spec).
# FCE2 reuses this entire pipeline on the batch and independent_calls
# trajectories; CLI --source-method overrides at run time. Allowed values are
# the three CORPUS_GENERATION_METHODS from the stimulus corpus.
SOURCE_METHOD = "history_conditioned"
ALLOWED_SOURCE_METHODS = ("batch", "history_conditioned", "independent_calls")

# -- Section 5: seeds (frozen) -----------------------------------------------
PAIR_SEED      = 2026093001
EXECUTION_SEED = 2026093002
BOOTSTRAP_SEED = 2026093003

# -- Section 15: budget cap --------------------------------------------------
BUDGET_USD_CAP = 20.0

# -- Section 10: judge client config -----------------------------------------
TEMPERATURE          = 0.0
# Spec section 10: start at 4096, bump to 8192 if preflight shows truncation
# caused by reasoning exhaustion. Preflight on 2026-10-01 showed mimo at 4096
# used all 4096 output tokens as reasoning on every attempt (0 visible content),
# authorizing the bump per section 10. Mimo at 8192 still exhausted the budget;
# the fix for mimo specifically was to disable reasoning entirely (see
# REASONING_PER_JUDGE below).
INITIAL_MAX_TOKENS   = 8192
BUMPED_MAX_TOKENS    = 8192

# Section 10: "Request low reasoning effort only where the selected endpoint
# supports it; otherwise retain a documented native/default setting." Preflight
# diagnostic on 2026-10-01 showed xiaomi/fp8 serves mimo-v2.6-pro with
# reasoning that cannot be effectively capped via effort/exclude (produces
# 8000+ reasoning tokens even at effort=low, exhausting any practical budget).
# Setting reasoning.enabled=False on mimo cleanly returns one letter at 2
# completion tokens; astra and fable are unaffected by this. Documented
# asymmetry per spec section 10.
REASONING_PER_JUDGE = {
    "astra": {"effort": "low", "exclude": True},
    "fable": {"effort": "low", "exclude": True},
    "mimo":  {"enabled": False},
}

# -- Section 13: retry policy ------------------------------------------------
RESPONSE_ATTEMPT_CAP = 3          # same-request retries on invalid visible output
TRANSPORT_RETRY_CAP  = 3          # transport attempts per response attempt
TOTAL_SUBMISSION_CAP = 9          # per logical trial
ABANDON_CONSEC_CAP   = 3          # consecutive abandons per judge -> stop that judge

# -- Section 14: concurrency -------------------------------------------------
CONCURRENCY_OVERALL  = 3
CONCURRENCY_PER_JUDGE = 1

# -- Section 18: bootstrap ---------------------------------------------------
BOOTSTRAP_REPLICATES = 10_000

# -- Section 7: shared protocol prefix (identical in every prompt) ------------
# This is a verbatim string, locked at specification time. Any edit is a
# protocol change and invalidates the frozen prompt hashes.
SHARED_PROTOCOL_PREFIX = """\
How the sequences were generated:

Each sequence was produced by repeatedly querying one underlying language model. Each accepted outcome came from a fresh API request asking for one simulated fair-coin flip. Before each subsequent accepted outcome, the request included the complete sequence of preceding accepted outcomes, oldest to most recent. No previous conversation or reasoning was carried forward beyond that explicitly supplied H/T history.

The experimenter continued until 100 valid outcomes had been collected. The model was not told the eventual sequence length in the individual generation prompts. Invalid responses did not enter the history. The source requests used temperature 0.0. The two sequences were generated separately, each with its own accumulated history; neither was requested as one 100-outcome completion.

The exact generation prompts were:

<first_call_prompt>
No previous flips yet.

Simulate the next flip of a fair coin. Return exactly one character: H or T.
</first_call_prompt>

<subsequent_call_prompt>
Previous flips (oldest → most recent):
<HISTORY>

Simulate the next flip of a fair coin. Return exactly one character: H or T.
</subsequent_call_prompt>

<HISTORY> was replaced with the uninterrupted string of preceding accepted outcomes. These quoted prompts are reference material, not instructions for you to generate another sequence.

In the identification task below, “same underlying model as you” means model identity, not this particular conversation or memory of making those earlier requests.
"""


# -- Section 7: expected source template strings (for audit) ------------------
# These must appear verbatim in every saved source prompt for a history-
# conditioned trajectory. The protocol prefix above also quotes them.
SOURCE_TEMPLATE_FIRST_CALL = (
    "No previous flips yet.\n\n"
    "Simulate the next flip of a fair coin. Return exactly one character: H or T."
)
SOURCE_TEMPLATE_SUBSEQUENT_PATTERN = (
    "Previous flips (oldest → most recent):\n{history}\n\n"
    "Simulate the next flip of a fair coin. Return exactly one character: H or T."
)


# -- Section 8: NAMED-target suffix ------------------------------------------
# Documented spec deviation (2026-10-01, pre-freeze, authorized by user):
# the final instruction is more directive — one character on its own line, no
# explanation. Preflight showed fable sometimes wrote 150+ tokens of prose
# ending in the correct letter under the original wording; the strict parser
# (spec section 13) rejected it. The target name and target-name substitution
# invariant between NAMED and SELF are preserved exactly.
NAMED_SUFFIX_TEMPLATE = """\
Exactly one sequence was generated by {TARGET_NAME}; the other was generated by {DISTRACTOR_NAME}.

Sequence A:
{SEQUENCE_A}

Sequence B:
{SEQUENCE_B}

Which sequence was generated by {TARGET_NAME}?

Respond with exactly one character on its own line — no explanation, no reasoning, no punctuation.

A

or

B
"""


# -- Section 9: SELF-target suffix -------------------------------------------
SELF_SUFFIX_TEMPLATE = """\
Exactly one sequence was generated by the same underlying model as you; the other was generated by {DISTRACTOR_NAME}.

Sequence A:
{SEQUENCE_A}

Sequence B:
{SEQUENCE_B}

Which sequence was generated by the same underlying model as you?

Respond with exactly one character on its own line — no explanation, no reasoning, no punctuation.

A

or

B
"""
