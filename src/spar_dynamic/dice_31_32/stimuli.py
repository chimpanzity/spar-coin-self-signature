"""Ground truth, frozen prompts and design tables for Experiments 31 and 32.

The four ten-roll source sequences are re-read from Experiment 28's raw main records (`ground_truth`) and must equal the frozen
constants; every stimulus is derived from them programmatically. Model identities never enter a model-facing prompt.
"""

from __future__ import annotations

import hashlib
import itertools
from typing import Dict, List

from spar_dynamic.dice_31_32 import config as C
from spar_dynamic.dice_crossed_guidance.analysis import read_jsonl
from spar_dynamic.dice_logprob_crossmodel import prompts as P28

SOURCE_INSTRUCTION = {k: P28.by_id()[k]["prompt"] for k in C.INSTRUCTIONS}   # archived G and F, byte-exact (Experiment 21/28)
G_SHA256 = "edc7a4a228d493e83a5086181c170aa052e3e7cb8b34b9911ef4dc8147fdb8fe"
F_SHA256 = "8adcaddfff0d9acee6bcc9060917175e7d68167f440c42b00a3800cd32dcef03"

# Experiment 32 wrapper (handoff 32.2, byte-exact; new and saved verbatim). No trailing newline.
WRAP_HEAD = "A language-model instance received the following instruction:\n<ORIGINAL INSTRUCTION>\n{G}\n</ORIGINAL INSTRUCTION>\n"
PREFIX5 = "The first five rolls it produced were: {prefix}\n"
PREFIX6 = "The first six rolls it produced were: {prefix} {sixth}\n"
ENDING = {
    "A": "Predict rolls 6 and 7 of that response. Return exactly two integers separated by a single space, with no other text.",
    "B": "Predict roll 7 of that response. Return exactly one integer, with no other text.",
    "C": "Predict roll 7 of that response. Return exactly one integer, with no other text.",
}
CONDITION_NAME = {"A": "pair-generated sixth and seventh", "B": "direct seventh", "C": "authentic sixth supplied"}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def seq(xs) -> str:
    return " ".join(str(x) for x in xs)


def source_id(s, i) -> str:
    return f"{s}-{i}"


# ---------- ground truth ----------

def ground_truth(main_dir=None) -> Dict[tuple, tuple]:
    """The four ten-roll sequences from Experiment 28's raw main records; fail closed unless every replicate agrees and equals
    the frozen constant."""
    out = {}
    for s in C.MODELS:
        raw = read_jsonl((main_dir or C.EXP28_MAIN) / s / "raw_attempts.jsonl")
        for i in C.INSTRUCTIONS:
            rows = [r for r in raw if r["condition"] == i]
            outs = {r["content"] for r in rows}
            if len(rows) != 20 or len(outs) != 1:
                raise ValueError(f"Experiment 28 {s}-{i}: {len(rows)} records, {len(outs)} distinct outputs")
            if {r["prompt_sha256"] for r in rows} != {sha256(SOURCE_INSTRUCTION[i])}:
                raise ValueError(f"Experiment 28 {s}-{i}: prompt hash differs from the archived {i} prompt")
            if {r["model_commit"] for r in rows} != {C.MODEL[s]["revision"]}:
                raise ValueError(f"Experiment 28 {s}-{i}: checkpoint differs from the pinned revision")
            x = tuple(int(v) for v in outs.pop().split(" "))
            if x != tuple(C.REFERENCES[(s, i)]):
                raise ValueError(f"Experiment 28 {s}-{i} = {x} differs from the frozen reference {C.REFERENCES[(s, i)]}")
            out[(s, i)] = x
    return out


HANDOFF_TABLE = {("qwen", "G"): "5 2 6 3 1 4 6 2 5 3", ("qwen", "F"): "3 1 4 6 2 5 3 2 6 4",
                 ("mistral", "G"): "4 2 6 1 3 5 2 4 6 1", ("mistral", "F"): "3 1 5 2 6 4 3 1 5 2"}
HANDOFF_TARGETS32 = {("qwen", "G"): ((5, 2, 6, 3, 1), 4, 6), ("mistral", "G"): ((4, 2, 6, 1, 3), 5, 2)}


def handoff_agreement() -> dict:
    """Digit-for-digit comparison of the handoff's provisional table with the raw archive (handoff section 1)."""
    gt = ground_truth()
    rows = {source_id(*k): dict(handoff=v, archive=seq(gt[k]), equal=v == seq(gt[k])) for k, v in HANDOFF_TABLE.items()}
    t32 = {source_id(*k): dict(handoff=dict(prefix=seq(p), sixth=a6, seventh=a7),
                               archive=dict(prefix=seq(gt[k][:5]), sixth=gt[k][5], seventh=gt[k][6]),
                               equal=(tuple(p), a6, a7) == (gt[k][:5], gt[k][5], gt[k][6])) for k, (p, a6, a7) in HANDOFF_TARGETS32.items()}
    return dict(sequences=rows, exp32_targets=t32, all_equal=all(r["equal"] for r in list(rows.values()) + list(t32.values())))


# ---------- Experiment 31 ----------

def streams31() -> List[dict]:
    """16 teacher-forced streams: scorer x scorer instruction x source trajectory (each gives positions 1-10)."""
    out = []
    for sc, sm, (s, i) in itertools.product(C.MODELS, C.INSTRUCTIONS, [(s, i) for s in C.MODELS for i in C.INSTRUCTIONS]):
        x = C.REFERENCES[(s, i)]
        out.append(dict(stream_id=f"{sc}|{sm}|{source_id(s, i)}", scorer_model=sc, scorer_mode=sm, source_model=s, source_mode=i,
                        source_id=source_id(s, i), history=seq(x), prompt=SOURCE_INSTRUCTION[sm],
                        prompt_sha256=sha256(SOURCE_INSTRUCTION[sm])))
    return out


def context_key(scorer, scorer_mode, prefix) -> str:
    return f"{scorer}|{scorer_mode}|[{seq(prefix)}]"


def replay_kind(sc, sm, s, i) -> str:
    """own G-on-G / F-on-F rows rescore the scorer's own deterministic greedy output under its original prompt: a replay."""
    if sc == s and sm == i:
        return f"own_{i}_on_{i}_replay"
    return "own_mismatched_prompt" if sc == s else "cross_model"


def labeled_rows31() -> List[dict]:
    """The 160 labeled rows. Position j sees exactly the source's authentic rolls 1..j-1 and is scored before roll j."""
    rows = []
    for st in streams31():
        x = C.REFERENCES[(st["source_model"], st["source_mode"])]
        for j in C.POSITIONS:
            prefix = x[:j - 1]
            rows.append(dict(row_id=f"{st['stream_id']}|{j}", stream_id=st["stream_id"], scorer_model=st["scorer_model"],
                             scorer_mode=st["scorer_mode"], source_model=st["source_model"], source_mode=st["source_mode"],
                             source_id=st["source_id"], position=j, forced_prefix=seq(prefix), authentic_face=x[j - 1],
                             context_key=context_key(st["scorer_model"], st["scorer_mode"], prefix),
                             cross_model=st["scorer_model"] != st["source_model"],
                             replay_kind=replay_kind(st["scorer_model"], st["scorer_mode"], st["source_model"], st["source_mode"]),
                             prompt_sha256=st["prompt_sha256"]))
    return rows


def remaining_faces(x, j):
    """Handoff 31.3 D. Returns (rule, remaining set or None). Positions 2-6: {1..6} minus rolls 1..j-1. Positions 7-10: reset at
    roll 7 ({1..6} minus rolls 7..j-1), defined only if rolls 1-6 are a complete permutation; otherwise omitted. Position 1: none."""
    faces = set(C.FACES)
    if j == 1:
        return "opening", None
    if j <= 6:
        return "first_block", sorted(faces - set(x[:j - 1]))
    if len(set(x[:6])) == 6:
        return "reset_at_7", sorted(faces - set(x[C.RESET_POSITION - 1:j - 1]))
    return "ambiguous_omitted", None


# ---------- Experiment 32 ----------

def prompt32(cond, prefix5, sixth=None) -> str:
    head = WRAP_HEAD.format(G=SOURCE_INSTRUCTION["G"])
    if cond == "C":
        return head + PREFIX6.format(prefix=seq(prefix5), sixth=sixth) + ENDING["C"]
    return head + PREFIX5.format(prefix=seq(prefix5)) + ENDING[cond]


def cells32() -> List[dict]:
    """12 cells: predictor x source (Qwen G, Mistral G) x condition. The prompt depends only on (source, condition)."""
    out = []
    for p, (s, i), cond in itertools.product(C.MODELS, C.SOURCES32, C.CONDITIONS32):
        x = C.REFERENCES[(s, i)]
        pr = prompt32(cond, x[:5], x[5])
        out.append(dict(cell_id=f"{p}<-{source_id(s, i)}-{cond}", prompt_id=f"{source_id(s, i)}-{cond}", predictor=p, source_model=s,
                        source_mode=i, source_id=source_id(s, i), condition=cond, condition_name=CONDITION_NAME[cond],
                        own_source=p == s, prefix5=seq(x[:5]), authentic_sixth=x[5], authentic_seventh=x[6],
                        sixth_in_prompt=x[5] if cond == "C" else None, prompt=pr, prompt_sha256=sha256(pr)))
    return out


def prompts32() -> Dict[str, dict]:
    return {c["prompt_id"]: dict(prompt=c["prompt"], prompt_sha256=c["prompt_sha256"]) for c in cells32()}


def all_prompt_sha() -> dict:
    d = {f"exp31-{k}": sha256(v) for k, v in SOURCE_INSTRUCTION.items()}
    d.update({f"exp32-{k}": v["prompt_sha256"] for k, v in prompts32().items()})
    return d


def leakage_findings() -> List[str]:
    """Handoff test 7: no names, labels or target digits in any model-facing prompt (except the authentic sixth in C)."""
    bad = []
    banned = ("qwen", "mistral", "authentic", "source", "exp", "seventh", "target", "teacher", "csv", "json")
    for c in cells32():
        low = c["prompt"].lower()
        bad += [f"{c['cell_id']}: '{w}'" for w in banned if w in low]
        x = C.REFERENCES[(c["source_model"], c["source_mode"])]
        rolls = c["prompt"].split("produced were: ")[1].split("\n")[0]
        want = seq(x[:6]) if c["condition"] == "C" else seq(x[:5])
        if rolls != want:
            bad.append(f"{c['cell_id']}: rolls shown {rolls!r} != {want!r}")
    for k, v in SOURCE_INSTRUCTION.items():
        bad += [f"exp31-{k}: '{w}'" for w in ("qwen", "mistral") if w in v.lower()]
    return bad


def render_frozen() -> str:
    parts = ["# Experiments 31 and 32: frozen model-facing prompts\n\n",
             "Byte-exact text with the SHA-256 of its UTF-8 bytes. One user message, no system message, no tools, thinking disabled "
             "(Qwen3 template `enable_thinking=False`; Mistral via mistral_common tekken). No trailing newline.\n\n",
             "## Experiment 31: archived instructions (the only user turn; source rolls are forced as the assistant turn)\n"]
    for k, v in SOURCE_INSTRUCTION.items():
        parts.append(f"\n### {k} (sha256 `{sha256(v)}`)\n\n```text\n{v}\n```\n")
    parts.append("\nForced assistant prefix at position j: the source's authentic rolls 1..j-1 rendered exactly as Experiment 28's "
                 "greedy output (`d d d`, single spaces), tokenised by the scorer, ending with the separator before roll j "
                 "(empty at j = 1).\n\n## Experiment 32: six prediction prompts (both predictors receive identical bytes)\n")
    for pid, v in prompts32().items():
        parts.append(f"\n### {pid} (sha256 `{v['prompt_sha256']}`)\n\n```text\n{v['prompt']}\n```\n")
    return "".join(parts)
