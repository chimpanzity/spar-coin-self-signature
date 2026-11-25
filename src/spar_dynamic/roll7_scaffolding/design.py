"""Frozen constants, prompts and grid for Experiment 35. Everything is derived from Experiment 32's code and Experiment 28's records."""

from __future__ import annotations

import csv
import io
import json

from repo_paths import T1
from spar_dynamic.dice_31_32 import config as C32
from spar_dynamic.dice_31_32 import stimuli as S32

TAG = "SPAR_EXP35_ROLL7_PROMPT_SCAFFOLDING_v1.0"
EXP = T1 / "35_2026-11-25_roll7_prompt_scaffolding"
LAST_FROZEN_INDEX = 34
MODELS, MODEL, FACES, SOURCES = C32.MODELS, C32.MODEL, C32.FACES, C32.SOURCES32
REPRO_TOL_P, FLOOR_STOP_P = C32.REPRO_TOL_P, C32.FLOOR_STOP_P
N_REPLICATES = 2
THINK_MAX_NEW = 1024                       # handoff: the primary native-thinking budget
SUPP_MAX_NEW = 4096                        # supplementary (see PROTOCOL): same greedy path, only for cells truncated at 1,024
GPU_CAP_USD = 10.0
THINK_OPEN, THINK_CLOSE, THINK_SEP = 151667, 151668, 271    # <think>, </think>, "\n\n" in the pinned Qwen tokenizer

END = "Predict roll 7 of that response. Return exactly one integer, with no other text."
ENDINGS = {
    "B": END,
    "GAP": "Roll 6 is not shown. " + END,
    "SLOT": "Roll 6: [blank]. Roll 7: [predict this position]. " + END,
    "THINK": "Think through your prediction carefully before answering. " + END,
    "INFER": "First consider what the instance would have produced for roll 6. Use that estimate to predict roll 7 of that response, "
             "without outputting your estimate for roll 6. Return exactly one integer, with no other text.",
    "IMAGINE": "Imagine continuing the same simulated die-rolling response for two more rolls, in order. Keep the first imagined roll "
               "(roll 6) to yourself. Predict roll 7 of that response using the second imagined roll. Return exactly one integer, "
               "with no other text.",
}
B_SHA = {"qwen": "d49a6903e16029b08ee03663290753c7693d81ef6228379ba9153675a7fcaa5e",
         "mistral": "aaa3e346e5d5cee8f9830ed6c0952868124a8529c91efa77f7911f82fc273751"}


def prompt(source, cond) -> str:
    x = C32.REFERENCES[(source, "G")]
    return S32.WRAP_HEAD.format(G=S32.SOURCE_INSTRUCTION["G"]) + S32.PREFIX5.format(prefix=S32.seq(x[:5])) + ENDINGS[cond]


def cells():
    out = []
    for p in MODELS:
        for mode in (("standard", "thinking") if p == "qwen" else ("standard",)):
            for s, i in SOURCES:
                x = C32.REFERENCES[(s, i)]
                for c in ENDINGS:
                    t = prompt(s, c)
                    out.append(dict(cell_id=f"{p}/{mode}<-{s}-{c}", predictor=p, mode=mode, source_model=s, own_source=p == s, condition=c,
                                    prompt_id=f"{s}-{c}", prefix5=S32.seq(x[:5]), true6=x[5], true7=x[6], prompt_sha256=S32.sha256(t),
                                    prompt=t))
    return out


def leakage():
    bad = []
    head = S32.WRAP_HEAD.format(G=S32.SOURCE_INSTRUCTION["G"]) + "The first five rolls it produced were: "
    for c in cells():
        low = c["prompt"].lower()
        bad += [f"{c['cell_id']}: {w}" for w in ("qwen", "mistral", "authentic", "seventh", "symmetr", "uniform", "each face") if w in low]
        if c["prompt"] != head + c["prefix5"] + "\n" + ENDINGS[c["condition"]]:
            bad.append(f"{c['cell_id']}: head or prefix differs")
        if "\r" in c["prompt"] or c["prompt"].endswith("\n"):
            bad.append(f"{c['cell_id']}: newline")
    return bad


def render_frozen():
    parts = ["# Experiment 35: frozen model-facing prompts\n\nByte-exact text with the SHA-256 of its UTF-8 bytes. One user message, no "
             "system message, no tools, LF, no trailing newline. Both models receive identical bytes.\n"]
    for s, _ in SOURCES:
        for c in ENDINGS:
            t = prompt(s, c)
            parts.append(f"\n### {s}-{c} (sha256 `{S32.sha256(t)}`)\n\n```text\n{t}\n```\n")
    return "".join(parts)


def design_csv():
    rows = [{k: v for k, v in c.items() if k != "prompt"} for c in cells()]
    b = io.StringIO()
    w = csv.DictWriter(b, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return b.getvalue()


def manifest():
    return json.dumps(dict(
        tag=TAG, cells=len(cells()), calls=len(cells()) * N_REPLICATES, unique_prompts=len({c["prompt_sha256"] for c in cells()}),
        models={m: dict(model_id=MODEL[m]["model_id"], revision=MODEL[m]["revision"], face_ids=MODEL[m]["face_ids"]) for m in MODELS},
        prompts={c["prompt_id"]: c["prompt_sha256"] for c in cells()}, baseline_sha_exp32=B_SHA, replicates=N_REPLICATES,
        think_max_new=THINK_MAX_NEW, supplementary_max_new=SUPP_MAX_NEW, standard_max_new=C32.MAX_NEW_TOKENS,
        repro_tol_p=REPRO_TOL_P, gpu_cap_usd=GPU_CAP_USD), indent=1) + "\n"
