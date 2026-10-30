"""Frozen configuration for LOULA_DICE_AB_LOGPROB v2.1 (handoff 2026-10-29, Experiment 24).

Serving reuses Experiment 21's validated open-weight configuration unchanged. Stimuli are read from the archived
Experiment 22 and 23 files and never rewritten. Changing any value here after `freeze` writes PROTOCOL_FROZEN.md
is a versioned amendment needing approval.
"""

from __future__ import annotations

import repo_paths

TAG = "LOULA_DICE_AB_LOGPROB_v2.1"
HANDOFF = "GPT_SPAR_Loula_v2_1_OpenWeight_AB_Logprob_Claude_Code_Handoff"

EXP = repo_paths.T1_EXP["dice_recognition_logprob"]
EXP22 = repo_paths.T1_EXP["dice_recognition"]
EXP23 = repo_paths.T1_EXP["dice_recognition_v2"]

SOURCES = {
    "calibration_items": EXP23 / "calibration" / "items.csv",
    "exp23_protocol": EXP23 / "PROTOCOL_FROZEN.md",
    "exp23_raw_attempts": EXP23 / "calibration" / "raw_attempts.jsonl",
    "exp23_responses": EXP23 / "calibration" / "responses.csv",
    "exp23_gate_table": EXP23 / "calibration" / "gate_table.csv",
    "recognition_pairs": EXP22 / "judgments" / "pairs.csv",
    "exp22_responses": EXP22 / "judgments" / "responses.csv",
    "classifier_gate": EXP22 / "corpus" / "classifier_gate.json",
}

# --- serving (Experiment 21) ----------------------------------------------------------------------------------
MODEL_ID = "Qwen/Qwen3-32B"
REVISION = "9216db5781bf21249d130ec9da846c4624c16137"
THINK_SUFFIX = "<think>\n\n</think>\n\n"            # fixed empty think block that enable_thinking=False appends
LABELS = ("A", "B")
GREEDY_MAX_NEW_TOKENS = 16                           # preflight greedy completions only
TOP_N = 10                                           # top tokens archived per scored position
PRIMARY_METHOD = "prefill"                           # one cached forward pass over the rendered prompt
DIAGNOSTIC_METHOD = "tokenwise"                      # prefix prefill, then the rest one token at a time

# --- Stage 0 technical preflight (handoff 5) -------------------------------------------------------------------
PREFLIGHT_ITEMS = ("MORE_SIXES-01", "MORE_REPEATS-01")   # first item of the first two tasks in items.csv
GREEDY_MIN_AB = 4                                    # of 5 technical prompts: first greedy token is A or B
EPSILON_FLOOR = 0.05                                 # log-odds units
EPSILON_MULTIPLIER = 2.0                             # epsilon = max(floor, 2 * delta)
EPSILON_STOP = 1.0                                   # epsilon >= 1.0 stops the pilot
DETERMINISM_REPEATS = 3
DETERMINISM_TOL = 1e-3                               # max |d| spread across repeats

# --- Stage A calibration gate (handoff 6) ----------------------------------------------------------------------
TASKS = ("MORE_SIXES", "MORE_REPEATS", "GEN_RULE")
N_PER_TASK = 12
GATE_TOTAL = 29                                      # of 36 items with S_correct > epsilon
GATE_TASK = {"GEN_RULE": 10, "MORE_SIXES": 9, "MORE_REPEATS": 8}
GATE_BOTH_ORDERS = 24                                # of 36 items with d_XY > eps and -d_YX > eps

# --- Stage B recognition screen (handoff 7) --------------------------------------------------------------------
N_PAIRS = 20
FRAMES = ("AUTH", "TYP")
NAMED_ARM = "RUN"                                    # frozen before Stage A: runs iff Stage A passes
NAMED_TARGET = "qwen"
NAME_ORDERS = ("QM", "MQ")                           # QM: NAME_1 = Qwen3-32B; MQ: NAME_1 = Mistral

# --- execution ---------------------------------------------------------------------------------------------------
ORDER_SEED = 20261030                                # trial order on the GPU (scores are deterministic)
BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 20261031
GPU_CAP_USD = 8.0
