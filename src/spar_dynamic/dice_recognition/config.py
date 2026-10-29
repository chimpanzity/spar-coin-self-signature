"""Frozen configuration for the LOULA_DICE_RECOGNITION pilot v1.0 (handoff 2026-10-29).

Changing any value here after the corpus is collected is a protocol deviation and must be approved.
"""

from __future__ import annotations

TAG = "LOULA_DICE_RECOGNITION_PILOT_v1.0"

# One pinned provider per model for the whole pilot; no fallbacks; endpoints must support every parameter.
MODELS = {
    "qwen": dict(slug="qwen/qwen3-32b", provider="SiliconFlow", reasoning={"enabled": False},
                 price_per_token=(0.14e-6, 0.57e-6), display="Qwen3-32B"),
    "mistral": dict(slug="mistralai/mistral-small-3.2-24b-instruct", provider="DeepInfra", reasoning=None,
                    price_per_token=(0.075e-6, 0.20e-6), display="Mistral Small 3.2 24B"),
}
SOURCES = ("qwen", "mistral")

GENERATION = dict(temperature=0.7, top_p=1.0, max_tokens=64)
JUDGMENT = dict(temperature=0.0, top_p=1.0, max_tokens=8)

N_VALID_PER_MODEL = 50
MAX_ATTEMPTS_PER_MODEL = 75
N_DEV, N_HOLDOUT = 30, 20

COST_CAP_USD = 5.00
MAX_CALL_COST_PRIOR_USD = 0.002          # conservative per-call upper bound used by the pre-call guard

# Seeds (recorded in the manifest)
GEN_ORDER_SEED = 2026102901
SPLIT_SEED = 2026102902
PAIR_SEED = 2026102903
TRIAL_ORDER_SEED = 2026102904
PERMUTATION_SEED = 2026102905
BOOTSTRAP_SEED = 2026102906

AUC_GATE = 0.65
CV_FOLDS = 5
N_PERMUTATIONS = 1000
N_BOOTSTRAP = 10000

MAX_TRANSPORT_RETRIES = 4
