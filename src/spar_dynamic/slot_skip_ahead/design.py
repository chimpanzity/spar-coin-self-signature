"""Frozen constants, sources, prompts and grid for Experiment 38 (SLOT at every position).

Experiment 35's SLOT ending (blank roll 6, predict roll 7) generalised to every k = 1..8: show rolls 1..k, mark roll k+1 blank,
ask for roll k+2. B (no slot markers) and C (roll k+1 supplied) are the within-prefix controls. At k = 5 the three prompts equal
Experiment 35 SLOT, Experiment 32 B and Experiment 32 C byte for byte.

Sources: every G-instruction sequence on record for the two checkpoints, i.e. Experiment 28's two greedy G outputs and
Experiment 27's 64 sampled G sequences (T = 0.7; 32 per generator). Prompts depend only on the rolls shown, so the unit of model
computation is the unique prefix; sequences are used only to score realised rolls.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from repo_paths import T1
from spar_dynamic.dice_31_32 import config as C32
from spar_dynamic.dice_31_32 import stimuli as S32
from spar_dynamic.dice_crossed_guidance.analysis import read_jsonl

TAG = "SPAR_EXP38_SLOT_SKIP_AHEAD_v1.0"
EXP = T1 / "38_2026-11-27_slot_skip_ahead"
EXP27_CORPUS = T1 / "27_2026-10-30_crossed_guided_self_prediction" / "corpus"
EXP35 = T1 / "35_2026-11-25_roll7_prompt_scaffolding"
LAST_FROZEN_INDEX = 37
MODELS, MODEL, FACES = C32.MODELS, C32.MODEL, C32.FACES
KS = tuple(range(1, 9))                     # rolls shown; target is roll k+2 (3..10)
CONDITIONS = ("SLOT", "B", "C")
REPRO_TOL_P = C32.REPRO_TOL_P               # 0.01 six-face |dp| for every replay gate
N_REPLICATES = 2                            # first-answer distribution scored twice (must be bit-identical)
GPU_CAP_USD = 5.0
CLUSTER_LEN = 2                             # bootstrap clusters: prefixes sharing their first two rolls
N_BOOT = 10000
BOOT_SEED = 20261127

WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}
END = "Predict roll {t} of that response. Return exactly one integer, with no other text."
SLOT_PRE = "Roll {b}: [blank]. Roll {t}: [predict this position]. "

# Anchors (byte-exact earlier prompts at k = 5)
EXP35_SLOT_SHA = {"qwen": "65a6de12f9c9bf079c54d82227d1ad7a7aaf2662949c00ccf665b7b7665d830d",
                  "mistral": "e429650413ac59a67a66c381c65feecfb5d52f5ffaf2af3ba4f0dbf0786d9802"}
EXP32_B_SHA = {"qwen": "d49a6903e16029b08ee03663290753c7693d81ef6228379ba9153675a7fcaa5e",
               "mistral": "aaa3e346e5d5cee8f9830ed6c0952868124a8529c91efa77f7911f82fc273751"}


def shown(xs) -> str:
    """'The first k rolls it produced were: ...' (k = 1 is singular)."""
    if len(xs) == 1:
        return f"The first roll it produced was: {xs[0]}\n"
    return f"The first {WORDS[len(xs)]} rolls it produced were: {S32.seq(xs)}\n"


def prompt(cond, prefix) -> str:
    """SLOT and B show `prefix` (k rolls) and ask for roll k+2. C shows `prefix` (k+1 rolls) and asks for roll k+2 = the next roll."""
    head = S32.WRAP_HEAD.format(G=S32.SOURCE_INSTRUCTION["G"]) + shown(prefix)
    n = len(prefix)
    if cond == "SLOT":
        return head + SLOT_PRE.format(b=n + 1, t=n + 2) + END.format(t=n + 2)
    if cond == "B":
        return head + END.format(t=n + 2)
    if cond == "C":
        return head + END.format(t=n + 1)
    raise ValueError(cond)


# ---------- sources ----------

def sources():
    """Every G sequence on record, in a fixed order: Experiment 28 greedy G (re-read and checked), then Experiment 27 sampled."""
    gt = S32.ground_truth()
    out = []
    for g in MODELS:
        out.append(dict(source_id=f"{g}-greedy", generator=g, kind="exp28_greedy", seed=None, rolls=gt[(g, "G")]))
    for g in MODELS:
        for r in read_jsonl(EXP27_CORPUS / g / "sampled.jsonl"):
            if r["prompt_sha256"] != S32.G_SHA256 or not r["valid"] or r["finish_reason"] != "stop":
                raise ValueError(f"Experiment 27 {g} seed {r['seed']}: not a valid G sample")
            x = tuple(int(v) for v in r["content"].split(" "))
            assert len(x) == 10 and set(x) <= set(FACES)
            out.append(dict(source_id=f"{g}-s{r['seed']}", generator=g, kind=f"exp27_{r['condition']}", seed=r["seed"], rolls=x))
    return out


def prefixes():
    """Unique k-roll prefixes (k in KS), sorted by length then lexically; with the source ids that contain them."""
    by = {}
    for s in sources():
        for k in KS:
            by.setdefault(s["rolls"][:k], []).append(s["source_id"])
    return [dict(prefix=p, k=len(p), prefix_id=S32.seq(p).replace(" ", ""), sources=v) for p, v in sorted(by.items(), key=lambda kv: (len(kv[0]), kv[0]))]


def c_prefixes():
    """Unique (k+1)-roll prefixes for C: the true roll k+1 of some source appended to a k-roll prefix."""
    return sorted({s["rolls"][:k + 1] for s in sources() for k in KS}, key=lambda p: (len(p), p))


def prompt_items():
    """One row per unique model-facing prompt (both predictors receive the same bytes)."""
    out = []
    for p in prefixes():
        for cond in ("SLOT", "B"):
            out.append(dict(prompt_id=f"{cond}-{p['prefix_id']}", condition=cond, k=p["k"], rolls_shown=S32.seq(p["prefix"]),
                            target_roll=p["k"] + 2))
    for q in c_prefixes():
        out.append(dict(prompt_id=f"C-{''.join(map(str, q))}", condition="C", k=len(q) - 1, rolls_shown=S32.seq(q), target_roll=len(q) + 1))
    for r in out:
        t = prompt(r["condition"], tuple(int(v) for v in r["rolls_shown"].split(" ")))
        r.update(prompt=t, prompt_sha256=S32.sha256(t))
    return out


def policy_items():
    """Teacher-forced G policy contexts per generator: every k-roll prefix (one-step) and each of its six one-roll extensions
    (two-step). Prefix lengths 1..9 are covered (C's conditional target is a two-step branch)."""
    return [dict(policy_id=p["prefix_id"], prefix=S32.seq(p["prefix"]), k=p["k"]) for p in prefixes()]


def anchors():
    """k = 5 prompts that must equal earlier frozen prompts byte for byte."""
    out = []
    for g in MODELS:
        x = C32.REFERENCES[(g, "G")]
        out += [dict(anchor=f"exp35-{g}-SLOT", prompt=prompt("SLOT", x[:5]), sha=EXP35_SLOT_SHA[g]),
                dict(anchor=f"exp32-{g}-G-B", prompt=prompt("B", x[:5]), sha=EXP32_B_SHA[g]),
                dict(anchor=f"exp32-{g}-G-C", prompt=prompt("C", x[:6]), sha=S32.sha256(S32.prompt32("C", x[:5], x[5])))]
    return out


def leakage():
    bad = []
    head = S32.WRAP_HEAD.format(G=S32.SOURCE_INSTRUCTION["G"])
    for r in prompt_items():
        t, low = r["prompt"], r["prompt"].lower()
        bad += [f"{r['prompt_id']}: {w}" for w in ("qwen", "mistral", "authentic", "sampled", "greedy", "uniform", "each face", "permutation") if w in low]
        rolls = tuple(int(v) for v in r["rolls_shown"].split(" "))
        if t != head + shown(rolls) + t[len(head + shown(rolls)):] or shown(rolls) not in t:
            bad.append(f"{r['prompt_id']}: head or rolls differ")
        if "\r" in t or t.endswith("\n"):
            bad.append(f"{r['prompt_id']}: newline")
    return bad


# ---------- frozen files ----------

def render_frozen():
    parts = ["# Experiment 38: frozen model-facing prompts\n\nOne user message, no system message, no tools, LF, no trailing newline, thinking "
             "disabled (Qwen3 template `enable_thinking=False`; Mistral via mistral_common tekken). Both predictors receive identical bytes. "
             "Every prompt is listed with its SHA-256 in `design_prompts.csv`; the templates and the k = 5 anchors are shown here.\n\n"
             "## Templates\n\nCommon head (Experiment 32, byte-exact), then the rolls line and an ending. k rolls are shown for SLOT and B, "
             "k + 1 for C.\n\n```text\n" + S32.WRAP_HEAD.format(G=S32.SOURCE_INSTRUCTION["G"]) + "The first {k words} rolls it produced were: "
             "{r1 ... rk}\n```\n\nFor k = 1 the line is `The first roll it produced was: {r1}`.\n\n| Condition | Ending |\n|---|---|\n",
             f"| SLOT | `{SLOT_PRE.format(b='{k+1}', t='{k+2}')}{END.format(t='{k+2}')}` |\n",
             f"| B | `{END.format(t='{k+2}')}` |\n",
             f"| C (k+1 rolls shown) | `{END.format(t='{k+2}')}` |\n\n## Anchors (k = 5)\n"]
    for a in anchors():
        parts.append(f"\n### {a['anchor']} (sha256 `{S32.sha256(a['prompt'])}`)\n\n```text\n{a['prompt']}\n```\n")
    ex = prompt("SLOT", (5, 2, 6, 3))
    parts.append(f"\n## Example (SLOT, k = 4, sha256 `{S32.sha256(ex)}`)\n\n```text\n{ex}\n```\n")
    return "".join(parts)


def _csv(rows):
    b = io.StringIO()
    w = csv.DictWriter(b, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return b.getvalue()


def sources_csv():
    return _csv([dict(source_id=s["source_id"], generator=s["generator"], kind=s["kind"], seed=s["seed"], rolls=S32.seq(s["rolls"]))
                 for s in sources()])


def prompts_csv():
    return _csv([{k: v for k, v in r.items() if k != "prompt"} for r in prompt_items()])


def manifest():
    it = prompt_items()
    return json.dumps(dict(
        tag=TAG, ks=list(KS), conditions=list(CONDITIONS), sources=len(sources()), unique_sequences=len({s["rolls"] for s in sources()}),
        prefixes=len(prefixes()), prompts={c: sum(r["condition"] == c for r in it) for c in CONDITIONS}, prompts_total=len(it),
        policy_contexts_per_generator=len(policy_items()) * 7,
        models={m: dict(model_id=MODEL[m]["model_id"], revision=MODEL[m]["revision"], face_ids=MODEL[m]["face_ids"]) for m in MODELS},
        anchors={a["anchor"]: a["sha"] for a in anchors()}, replicates=N_REPLICATES, standard_max_new=C32.MAX_NEW_TOKENS,
        repro_tol_p=REPRO_TOL_P, gpu_cap_usd=GPU_CAP_USD, cluster_len=CLUSTER_LEN, n_boot=N_BOOT, boot_seed=BOOT_SEED), indent=1) + "\n"


def read_rows(p: Path):
    return list(csv.DictReader(open(p, encoding="utf-8")))
