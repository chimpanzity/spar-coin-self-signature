"""Frozen constants for SPAR_CROSSED_GUIDED_SELFPRED_v1.0 (handoff dated 2026-10-30)."""

from __future__ import annotations

from repo_paths import T1

TAG = "SPAR_CROSSED_GUIDED_SELFPRED_v1.0"
DESIGN_SOURCE = "GPT_SPAR_Experiment_27_Crossed_Qwen_Mistral_Guided_Self_Prediction_Claude_Code_Handoff.md (2026-10-30)"

EXP = T1 / "27_2026-10-30_crossed_guided_self_prediction"
EXP21 = T1 / "21_2026-10-29_dice_logprob" / "main-qwen3-32b-a100"
EXP22 = T1 / "22_2026-10-29_loula_dice_recognition_pilot"
EXP26 = T1 / "26_2026-10-30_dice_prefix_declarative"
PRE, CORPUS, TRIALS, MAIN, ANALYSIS, REPORTS = (EXP / d for d in ("preflight", "corpus", "trials", "main", "analysis", "reports"))
LAST_FROZEN_INDEX = 26                    # experiment folders 01-26 are never written to

MODELS = ("qwen", "mistral")
MODEL = {
    "qwen": dict(model_id="Qwen/Qwen3-32B", revision="9216db5781bf21249d130ec9da846c4624c16137",
                 name="Qwen3-32B", family="Qwen3", tokenizer="Qwen2 BPE via transformers; Qwen3 chat template, enable_thinking=False",
                 face_ids={1: 16, 2: 17, 3: 18, 4: 19, 5: 20, 6: 21}),
    # OpenRouter's hugging_face_id for mistralai/mistral-small-3.2-24b-instruct (Experiment 22's model) is exactly this repo.
    "mistral": dict(model_id="mistralai/Mistral-Small-3.2-24B-Instruct-2506", revision="95a6d26c4bfb886c58daf9d3f7332c857cb27b43",
                    name="Mistral Small 3.2 24B Instruct", family="Mistral3 (text path only)",
                    tokenizer="mistral_common tekken v11 (tekken.json at the pinned revision); one user message, no system prompt",
                    face_ids={1: 1049, 2: 1050, 3: 1051, 4: 1052, 5: 1053, 6: 1054}),
}
OPENROUTER_MISTRAL = "mistralai/mistral-small-3.2-24b-instruct"
MISTRAL_DOWNLOAD = ["config.json", "generation_config.json", "model.safetensors.index.json", "model-*.safetensors",
                    "tekken.json", "params.json"]          # consolidated.safetensors (duplicate weights) is not downloaded

# Experiment 21 / 26 archival references (Qwen)
QWEN_CHAT_TEMPLATE_SHA256 = "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8"
G_PROMPT_SHA256 = "edc7a4a228d493e83a5086181c170aa052e3e7cb8b34b9911ef4dc8147fdb8fe"
F_PROMPT_SHA256 = "8adcaddfff0d9acee6bcc9060917175e7d68167f440c42b00a3800cd32dcef03"
QWEN_G_REF = (5, 2, 6, 3, 1, 4, 6, 2, 5, 3)
QWEN_F_REF = (3, 1, 4, 6, 2, 5, 3, 2, 6, 4)
EXP26_FREE = {"H0": "3 1 6", "N0": "1 2 3", "S0": "1 3 5", "O0": "1 3 5", "H3": "3 1 4", "N3": "3 1 4", "S3": "3 1 4",
              "O3": "3 1 4", "H6": "3 5 2", "N6": "3 2 5", "S6": "2 5 3", "O6": "3 2 5"}

FACES = (1, 2, 3, 4, 5, 6)
SEQ_LEN = 10
MAX_NEW_TOKENS = 128

# Sampled corpora (Tier B targets and the separate reference corpus used for D evidence)
TEMPERATURE = 0.7                          # softmax(fp32 logits / 0.7), top_p = 1.0, no top_k, torch.multinomial
N_TARGETS = 24                             # per generator; the N=40 expansion option is not exercised in this run
N_REFERENCE = 8                            # per generator; never scored as a target
N_FEASIBILITY = 4                          # preflight draws, discarded
MAX_DRAW_FACTOR = 2                        # stop if more than 2N draws are needed to obtain N valid sequences
SEED_BASE = {"feasibility": 27_000_000, "reference": 27_100_000, "target": 27_200_000}
MODEL_SEED_OFFSET = {"qwen": 0, "mistral": 50_000}

# History conditions: (revealed first r rolls, hidden note, scored original positions)
CONDITIONS = {
    "k0": dict(reveal=0, positions=(1, 2, 3), suite="bridge"),
    "k3": dict(reveal=3, positions=(4, 5, 6), suite="immediate"),
    "k6": dict(reveal=6, positions=(7, 8, 9), suite="immediate+fixed7"),
    "k8": dict(reveal=8, positions=(9, 10), suite="immediate"),
    "m0": dict(reveal=0, positions=(7, 8, 9), suite="fixed7"),
    "m3": dict(reveal=3, positions=(7, 8, 9), suite="fixed7"),
}
FRAMINGS = ("A", "T", "R")                 # anonymous, true target name, relational (own model / different model)
EVIDENCE = ("H", "I", "D")                 # history only, length-matched irrelevant paragraph, earlier target-model response
FIXED7 = ("m0", "m3", "k6")
IMMEDIATE = ("k3", "k6", "k8")
BRIDGE = ("k0", "k3", "k6")

ORDER_SEED = 20261050
FULL_PASS_FRACTION_B = 0.05                # Tier B trials re-scored by one full forward pass (all Tier A trials are)
BOOTSTRAP_B = 10000
BOOTSTRAP_SEED = 20261051

# Gates
REPRO_TOL_P = 0.01                         # Qwen G/F/Exp26 vs archive, six-face |dp|
SCORER_TOL_LOGP = 1e-4                     # rescoring own output vs generation (incremental arithmetic)
ENGINE_TOL_LOGP = 0.0                      # Qwen: this package's engine vs Experiment 21's class, bit-identical
MIN_FACE_MASS = 0.5
QWEN_ARCHIVED_FLOOR_P = 0.091              # Experiment 26 incremental vs full-pass floor (a warning, not a threshold)
FLOOR_STOP_P = 0.25                        # numerical instability stop: incremental vs full pass beyond this

# Budget
GPU_CAP_USD = 15.0
GPU_WARN_USD = 10.0
EST_RATE_USD_H = 1.6
EST_SETUP_MIN = 30
EST_SEC_PER_TRIAL = {"qwen": 1.3, "mistral": 1.0}
