"""Source ingestion with schema validation (handoff 2 and 5.1) and the frozen trial lists.

Archived Experiment 22 and 23 files are read only. Truth comes from content (recomputed counts) or from recorded
source labels, never from a model's explanation. Any mismatch raises SchemaError, which stops the pilot.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random

from spar_dynamic.dice_recognition_logprob import config as C, prompts as P
from spar_dynamic.dice_recognition_v2 import synthetic as S

ORIENTATIONS = ("XA", "XB")                          # XA: candidate X shown as Sample A; XB: X shown as B


class SchemaError(RuntimeError):
    pass


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def file_sha256(path) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def input_hashes(sources=None) -> dict:
    sources = sources or C.SOURCES
    return {k: dict(path=str(p.relative_to(C.EXP.parents[1])).replace("\\", "/"), sha256=file_sha256(p))
            for k, p in sources.items()}


def _seq(s):
    faces = [int(x) for x in s.split(" ")]
    if not faces or any(f not in range(1, 7) for f in faces) or " ".join(map(str, faces)) != s:
        raise SchemaError(f"malformed sequence {s!r}")
    return faces


def load_calibration(path=None) -> list:
    """36 Experiment 23 items. X is the correct candidate by construction; the counts are recomputed here."""
    rows = read_csv(path or C.SOURCES["calibration_items"])
    need = {"item_id", "task", "X", "Y", "length", "X_value", "Y_value", "correct_by_content"}
    if not rows or not need <= set(rows[0]):
        raise SchemaError(f"calibration items: expected columns {sorted(need)}, got {sorted(rows[0]) if rows else []}")
    ids = [r["item_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise SchemaError("duplicate item_id")
    for t in C.TASKS:
        n = sum(r["task"] == t for r in rows)
        if n != C.N_PER_TASK:
            raise SchemaError(f"{t}: {n} items, expected {C.N_PER_TASK}")
    if len(rows) != C.N_PER_TASK * len(C.TASKS):
        raise SchemaError(f"{len(rows)} items, expected {C.N_PER_TASK * len(C.TASKS)}")
    out = []
    for r in rows:
        x, y = _seq(r["X"]), _seq(r["Y"])
        if len(x) != len(y) or len(x) != int(r["length"]) or r["X"] == r["Y"]:
            raise SchemaError(f"{r['item_id']}: lengths or identical sequences")
        count = S.n_sixes if r["task"] == "MORE_SIXES" else S.n_repeats
        if (count(x), count(y)) != (int(r["X_value"]), int(r["Y_value"])):
            raise SchemaError(f"{r['item_id']}: archived counts do not match content")
        if r["correct_by_content"] != "X" or not count(x) > count(y):
            raise SchemaError(f"{r['item_id']}: X is not the content-correct candidate")
        out.append(dict(item_id=r["item_id"], task=r["task"], X=r["X"], Y=r["Y"], length=len(x),
                        X_value=count(x), Y_value=count(y)))
    return out


def load_pairs(path=None, heldout_path=None) -> list:
    """20 archived held-out Qwen-Mistral pairs (Experiment 22). X = the Qwen sequence."""
    rows = read_csv(path or C.SOURCES["recognition_pairs"])
    need = {"pair_id", "qwen_id", "qwen_seq", "mistral_id", "mistral_seq"}
    if not rows or not need <= set(rows[0]):
        raise SchemaError(f"pairs: expected columns {sorted(need)}")
    if len({r["pair_id"] for r in rows}) != C.N_PAIRS or len(rows) != C.N_PAIRS:
        raise SchemaError(f"expected {C.N_PAIRS} distinct pair ids")
    held = {h["stimulus_id"]: h for h in read_csv(heldout_path or C.EXP22 / "corpus" / "heldout.csv")}
    for r in rows:
        for src in ("qwen", "mistral"):
            seq = _seq(r[f"{src}_seq"])
            h = held.get(r[f"{src}_id"])
            if len(seq) != 10 or h is None or h["source"] != src or h["split"] != "heldout" or h["sequence"] != r[f"{src}_seq"]:
                raise SchemaError(f"{r['pair_id']}: {src} stimulus not a matching held-out record")
        if r["qwen_seq"] == r["mistral_seq"]:
            raise SchemaError(f"{r['pair_id']}: identical sequences")
    return [{k: r[k] for k in need} for r in rows]


def _trial(stage, trial_id, unit_id, kind, orientation, X, Y, prompt, **extra):
    a, b = (X, Y) if orientation == "XA" else (Y, X)
    return dict(trial_id=trial_id, stage=stage, unit_id=unit_id, kind=kind, orientation=orientation, A=a, B=b,
                prompt=prompt, prompt_sha256=P.sha256(prompt), **extra)


def calibration_trials(items) -> list:
    out = []
    for it in items:
        for o in ORIENTATIONS:
            a, b = (it["X"], it["Y"]) if o == "XA" else (it["Y"], it["X"])
            out.append(_trial("calibration", f"cal|{it['item_id']}|{o}", it["item_id"], it["task"], o, it["X"], it["Y"],
                              P.calibration(it["task"], a, b)))
    return out


def preflight_trials(items) -> list:
    """5 technical prompts: two calibration items in both orientations plus one generic A/B example."""
    by_id = {i["item_id"]: i for i in items}
    out = [dict(t, stage="preflight", trial_id=t["trial_id"].replace("cal|", "pre|"))
           for t in calibration_trials([by_id[i] for i in C.PREFLIGHT_ITEMS])]
    out.append(dict(trial_id="pre|GENERIC", stage="preflight", unit_id="GENERIC", kind="GENERIC", orientation="XA",
                    A="2 + 2 = 4", B="2 + 2 = 5", prompt=P.GENERIC, prompt_sha256=P.sha256(P.GENERIC)))
    return out


def screen_trials(pairs, named_arm=C.NAMED_ARM) -> list:
    out = []
    for p in pairs:
        X, Y = p["qwen_seq"], p["mistral_seq"]
        for o in ORIENTATIONS:
            a, b = (X, Y) if o == "XA" else (Y, X)
            for fr in C.FRAMES:
                out.append(_trial("screen", f"rec|{fr}|{p['pair_id']}|{o}", p["pair_id"], fr, o, X, Y, P.frame(fr, a, b)))
            if named_arm == "RUN":
                for no in C.NAME_ORDERS:
                    out.append(_trial("screen", f"rec|NAMED_QWEN|{p['pair_id']}|{o}|{no}", p["pair_id"], "NAMED_QWEN", o,
                                      X, Y, P.named(a, b, no), name_order=no))
    return out


def shuffled(trials, seed=C.ORDER_SEED) -> list:
    t = list(trials)
    random.Random(seed).shuffle(t)
    return t


def write_trials(path, trials):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(trials, f, indent=1)
