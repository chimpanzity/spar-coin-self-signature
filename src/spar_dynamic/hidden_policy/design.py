"""Frozen constants, prompts, prefix bank and grouped folds for Experiment 36. Pure Python; no model calls."""

from __future__ import annotations

import csv
import io
import itertools
import json

from repo_paths import T1
from spar_dynamic.dice_31_32 import config as C31
from spar_dynamic.dice_scaffolding import config as C33
from spar_dynamic.dice_scaffolding import design as D33

TAG = "SPAR_EXP36_HIDDEN_ACTIVATION_DICE_POLICY_v1.0"
EXP = T1 / "36_2026-11-25_hidden_activation_dice_policy"
LAST_FROZEN_INDEX = 35
MODELS, MODEL, FACES, SEPARATOR_ID = C31.MODELS, C31.MODEL, C31.FACES, C31.SEPARATOR_ID
G, sha256, seq = D33.G, D33.sha256, D33.seq
REPRO_TOL_P = C31.REPRO_TOL_P
SUBJECT = {"agent": "an agent", "shape": C33.NEUTRAL, "self": "the language model answering this forecast", "generic": "a language model"}
PROMPTS = tuple(SUBJECT)
MODES = PROMPTS + ("direct",)
PILOT_FAMILIES = ("125", "146")            # Experiment 33 development families c01, c02 (and c10, same set as c02)
N_OUTER, N_INNER = 5, 4
DEPTHS = (25, 50, 75, 100)
SLOTS = ("b25", "b50", "b75", "b100", "final_norm")     # b*: post-block residual, pre final normalisation
PRIMARY_SLOT = "b75"
EMIT_TOKENS = 16                            # greedy tokens recorded for the agent forecast
PROJ_TOL = 1e-3                            # nats; head applied to one position vs the whole prompt (fp32 summation order)
GPU_CAP_USD = 10.0


def block_index(n_layers, depth):
    """0-based block whose output is closest to `depth` per cent of the stack."""
    return round(n_layers * depth / 100) - 1


def forecast(kind, prefix):
    return D33.forecast_prompt(SUBJECT[kind], prefix)


def family(x):
    return "".join(map(str, sorted(x[:3])))


def bank():
    pilot_prefixes = {r["history"] for r in D33.constructed() if r["k"] in (4, 5) and family(D33.faces_of(r["history"])) in PILOT_FAMILIES}
    out = []
    for n in (3, 4):
        for x in itertools.permutations(FACES, n):
            f = family(x)
            out.append(dict(prefix=seq(x), family=f, roll=n + 1, unused=seq([v for v in FACES if v not in x]),
                            pilot_prefix=seq(x) in pilot_prefixes, fold=folds().get(f), eligible=f not in PILOT_FAMILIES))
    return out


def folds():
    """Outer fold of each eligible family: hash order, round robin. The pilot families have none."""
    fam = ["".join(map(str, t)) for t in itertools.combinations(FACES, 3)]
    fam = sorted((f for f in fam if f not in PILOT_FAMILIES), key=lambda f: sha256(f"{TAG}|fold|{f}"))
    return {f: i % N_OUTER for i, f in enumerate(fam)}


def inner_folds(train_families):
    fam = sorted(train_families, key=lambda f: sha256(f"{TAG}|inner|{f}"))
    return {f: i % N_INNER for i, f in enumerate(fam)}


def pilot_prefixes():
    return [b["prefix"] for b in bank() if b["pilot_prefix"]]


def prompt_rows():
    return [dict(mode=m, prefix=b["prefix"], prompt_sha256=sha256(forecast(m, b["prefix"]))) for m in PROMPTS for b in bank()] + \
        [dict(mode="direct", prefix=b["prefix"], prompt_sha256=sha256(G)) for b in bank()]


def leakage():
    bad = []
    for b in bank():
        ts = [forecast(m, b["prefix"]).split("\n") for m in PROMPTS]
        if any(len(t) != 7 for t in ts) or any(len({t[i] for t in ts}) != 1 for i in (0, 1, 2, 3, 5, 6)):
            bad.append(f"{b['prefix']}: more than the description line differs")
        if any(w in "\n".join(sum(ts, [])).lower() for w in ("qwen", "mistral", "unused")) or f"Earlier rolls in order: {b['prefix']}." != ts[0][5]:
            bad.append(f"{b['prefix']}: content")
    return bad


def _csv(rows):
    b = io.StringIO()
    w = csv.DictWriter(b, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return b.getvalue()


def render_frozen():
    p = "5 2 6"
    parts = ["# Experiment 36: frozen prompts\n\nOne user message, no system message, no tools, thinking disabled, LF, no trailing newline. "
             "Shown for the prefix `5 2 6`; only the description line and the prefix vary. SHA-256 of every prompt is in `prompt_hashes.csv`.\n"]
    for m in PROMPTS:
        parts.append(f"\n### {m} (sha256 `{sha256(forecast(m, p))}`)\n\n```text\n{forecast(m, p)}\n```\n")
    parts.append(f"\n### direct (sha256 `{sha256(G)}`; the prefix and a trailing separator are forced as the assistant turn)\n\n```text\n{G}\n```\n")
    return "".join(parts)


def manifest():
    b = bank()
    el = [x for x in b if x["eligible"]]
    return json.dumps(dict(
        tag=TAG, prefixes=len(b), eligible_prefixes=len(el), eligible_families=len({x["family"] for x in el}), pilot_families=PILOT_FAMILIES,
        pilot_prefixes=pilot_prefixes(), folds=folds(), rows_per_model=len(prompt_rows()), n_inner=N_INNER, slots=SLOTS, primary_slot=PRIMARY_SLOT,
        pairs=sum(3 if x["roll"] == 4 else 1 for x in el),
        models={m: dict(model_id=MODEL[m]["model_id"], revision=MODEL[m]["revision"]) for m in MODELS}, gpu_cap_usd=GPU_CAP_USD), indent=1) + "\n"


def built():
    return {"prompts_frozen.md": render_frozen(), "prompt_hashes.csv": _csv(prompt_rows()), "design_prefixes.csv": _csv(bank()),
            "manifest.json": manifest()}
