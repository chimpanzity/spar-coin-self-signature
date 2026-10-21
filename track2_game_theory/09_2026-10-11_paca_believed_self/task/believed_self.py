"""
believed_self.py — frozen configuration for the PACA believed-self generator pilot (SPAR, 2026-10-11).

2 x 2 within each model: actual generator of the blue-circle location (Proteus | IID coin) x believed generator
(another instance of self | a different LLM). One 200-trial session per cell; models run Fable -> Astra -> Qwen.

Everything else is baseline PACA, reused verbatim:
  - system prompt: prompts.SYS_MINIMALIST, with the believed-generator sentence prepended by prime.apply_prime
    ("<sentence>\\n\\n<SYS_MINIMALIST>"), the convention of the SPAR self-truth pilot;
  - user prompt: prompts.build_prompt(history, desc_window=5, compact_window=25): the model sees only the last 25
    trials (5 described in words), while Proteus conditions on the full session history;
  - opponent: protean_committed.choose_opponent_move ("proteus" or "random"), committed from trials 1..t-1;
  - parser: api_client.parse_choice; call layer: api_client.call_model (no coin substitution is ever used).
"""
from __future__ import annotations

import hashlib
import os
import random
from dataclasses import dataclass
from typing import Dict, Tuple

EXPERIMENT_TAG = "paca_believed_self_pilot_v1"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data", "believed_self_pilot")

MASTER_SEED = 20261011
N_TRIALS = 200
DESC_WINDOW = 5            # PACA default
COMPACT_WINDOW = 25        # PACA default: the model sees the last 25 trials; Proteus sees the full history
MAX_TOKENS = 20000         # PACA default
MAX_TOKENS_CEILING = 80000  # PACA default truncation escalation ceiling
MAX_TRIAL_ATTEMPTS = 3     # a trial whose call returns no usable choice is re-requested at most twice, then the session stops
BUDGET_CAP_USD = 60.0      # proposed; requires Chris's approval

# Exact slugs and provider pins from the SPAR configuration (spar-coin-self-signature/opponent_disclosure_*_3models/config.py).
# Temperature 0 (PACA main setting) is sent only where the pinned endpoint supports it.
MODELS: Dict[str, Dict] = {
    "fable": {"slug": "anthropic/claude-fable-5.1", "provider": "anthropic", "send_temperature": False},
    "astra": {"slug": "openai/gpt-6-astra", "provider": "openai", "send_temperature": False},
    "qwen": {"slug": "qwen/qwen3.8-27b", "provider": "alibaba", "send_temperature": True},
}
MODEL_ORDER: Tuple[str, ...] = ("fable", "astra", "qwen")     # execution order (Qwen last)

BELIEF_SENTENCE = {
    "self": "Another instance of your model is generating the sequence of blue circle landings.",
    "other": "An instance of a different language model is generating the sequence of blue circle landings.",
}
GENERATORS = ("proteus", "random")      # protean_committed opponent_type values
CONDITION_CODES = {("proteus", "self"): "P-S", ("proteus", "other"): "P-O", ("random", "self"): "R-S", ("random", "other"): "R-O"}


@dataclass(frozen=True)
class Session:
    model: str
    generator: str      # actual: proteus | random
    belief: str         # believed: self | other
    session_index: int  # self/other of the same (model, generator) share it -> identical opponent RNG stream

    @property
    def code(self) -> str:
        return CONDITION_CODES[(self.generator, self.belief)]

    @property
    def session_id(self) -> str:
        return f"{self.model}_{self.code}"

    @property
    def seed(self) -> int:
        # identical to run_session.derive_session_seed(MASTER_SEED, session_index)
        return random.Random(f"{MASTER_SEED}-{self.session_index}").randint(0, 2**31 - 1)


def sessions():
    out = []
    for mi, m in enumerate(MODEL_ORDER):
        for gi, g in enumerate(GENERATORS):
            for b in ("self", "other"):
                out.append(Session(m, g, b, session_index=10 * (mi + 1) + gi))
    return out


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
