"""Frozen constants for SPAR Track 1 Experiment 33 (dice forecast scaffolding; handoff of 2026-11-24)."""

from __future__ import annotations

from repo_paths import T1
from spar_dynamic.dice_31_32 import config as C31

TAG = "SPAR_EXP33_DICE_SCAFFOLDING_v1.0"
VERSION = "spar-dice-v1"                              # string used in every design hash (handoff section 2)
DESIGN_SOURCE = "GPT_SPAR_Dice_Scaffolding_Claude_Code_Handoff.md (2026-11-24)"
EXP = T1 / "33_2026-11-24_dice_scaffolding"
EXP28_MAIN = C31.EXP28_MAIN
CORPUS27 = T1 / "27_2026-10-30_crossed_guided_self_prediction" / "corpus"
LAST_FROZEN_INDEX = 32

MODELS = C31.MODELS                                   # ("qwen", "mistral")
MODEL = C31.MODEL
FACES = C31.FACES
SEPARATOR_ID = C31.SEPARATOR_ID
REFERENCES = C31.REFERENCES
NAME = {m: C31.MODEL[m]["model_id"] for m in C31.MODELS}   # exact public checkpoint names (Hugging Face ids)
PHASES = ("core", "extensions")

# Ordered word pairs (left, right); orientation is fixed for analysis only.
DEV_PAIRS = (("red", "green"), ("narrow", "wide"), ("sad", "cheerful"), ("bothered", "unbothered"), ("restless", "settled"),
             ("uneasy", "confident"))
CONF_PAIRS = (("blue", "orange"), ("yellow", "violet"), ("pointy", "round"), ("jagged", "smooth"), ("angry", "calm"),
              ("angsty", "composed"))
WORDS = tuple(w for p in DEV_PAIRS + CONF_PAIRS for w in p)
CONF_WORDS = tuple(w for p in CONF_PAIRS for w in p)
SUBSET_WORDS = ("blue", "orange", "pointy", "round", "angry", "calm")

NEUTRAL, LONG_NEUTRAL = "a shape", "a shape with no further description"
IDENTICAL = "another instance of the exact checkpoint answering this forecast, with identical weights"
GENERIC_LM = "a language model"
IDENTITY_SUBJECTS = {
    "answering": "the language model answering this forecast", "identical": IDENTICAL, "another_lm": "another language model",
    "generic_lm": GENERIC_LM, "name_qwen": NAME["qwen"], "name_mistral": NAME["mistral"],
    "we": "the group referred to by \"we\""}
FACTUAL_SUBJECTS = {
    "country_china": "a language model from a developer based in China", "country_france": "a language model from a developer based in France",
    "org_alibaba": "a language model developed by Alibaba", "org_mistral": "a language model developed by Mistral AI",
    "params_32": "a language model with approximately 32 billion parameters",
    "params_24": "a language model with approximately 24 billion parameters"}
OBJECT_SUBJECTS = {
    **{f"{c}_{s}": f"a shape described as {c} and {s}" for c in ("blue", "orange") for s in ("pointy", "round")},
    **{f"{a}_{n}": f"a {n} described as {a}" for a in ("angry", "sad") for n in ("square", "circle")},
    "square": "a square", "circle": "a circle", "blue_square": "a blue square", "red_square": "a red square", "salmon": "a dead salmon"}

SCAFFOLDS = {
    "plain": None,
    "physical": "Imagine the die leaving the roller's hand, striking the ground, and settling. Follow the rolls in order.",
    "textual": "Imagine the described roller receiving the original text and producing its reply. Consider how it continues the sequence.",
    "preamble": "The description and the earlier rolls appear here together. Read both lines before giving the requested answer."}

# History bank
N_DEV_FAMILIES, N_FAMILIES, SUBSET_RANKS = 4, 16, (5, 6, 7, 8)
KS = tuple(range(4, 11))                              # roll being scored; prefix length k - 1
STRATA = {"4-5": (4, 5), "6": (6,), "7": (7,), "8-10": (8, 9, 10)}
N_ARCHIVE_PATHS = 8                                   # sampled paths per source in the bounded forecast replication
WORKED = ((5, 2, 6), REFERENCES[("qwen", "G")][:6], REFERENCES[("mistral", "G")][:6])
EXPECTED = dict(dev_histories=28, conf_histories=84, plain_per_model=2912, t2_per_model=392, scaffold_per_model=588,
                identity_per_model=196, association_per_model=384)

# Readouts, scoring, QC
VERBAL_MAX_NEW, FREE_MAX_NEW = 128, 96
VERBAL_TOL_PP = 1.0
TOP_STORED = 5
LOW_MASS = 0.50                                       # flag: median valid-face mass of a core dice condition/model below this
SCORER_TOL_LOGP = C31.SCORER_TOL_LOGP                 # 1e-4 nats
FLOOR_STOP_P = C31.FLOOR_STOP_P                       # 0.25
N_REPRO = 64                                          # forecasts re-scored for bit-identity per model
BOOT_B, BOOT_SEED = 10_000, 241124
GPU_CAP_USD = 15.0
