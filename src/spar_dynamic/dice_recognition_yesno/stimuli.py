"""Stimuli and frozen trial lists for v3.0.

Calibration items are new: Experiment 23's generator (dice_recognition_v2.synthetic.make_items) under CAL_SEED. They are
written once to calibration/items.csv and then validated against content exactly as v2.1 validated Experiment 23's
items (recomputed counts, X correct), plus a novelty check: no sequence may appear in Experiment 23's items. Recognition
pairs are Experiment 22's archived held-out pairs, read through v2.1's validating loader.

One trial = one prompt = one sequence x one polarity. A unit (item or pair) has four trials: X/Y x pos/neg.
"""

from __future__ import annotations

import csv
import os
import random

from spar_dynamic.dice_recognition_logprob import stimuli as ST24
from spar_dynamic.dice_recognition_v2 import synthetic as S
from spar_dynamic.dice_recognition_yesno import config as C, prompts as P

SchemaError = ST24.SchemaError
read_csv, file_sha256, write_trials = ST24.read_csv, ST24.file_sha256, ST24.write_trials
ITEM_FIELDS = ["item_id", "task", "X", "Y", "length", "X_value", "Y_value", "correct_by_content"]


def generate_items() -> list:
    items = S.make_items(seed=C.CAL_SEED, n=C.N_PER_TASK)
    for i in items:
        i["correct_by_content"] = S.correct_side(i) if i["task"] != "GEN_RULE" else "X"
    return [{k: i[k] for k in ITEM_FIELDS} for i in items]


def write_items(path=C.ITEMS_CSV):
    """Write the new items once; if the file exists it must equal a fresh regeneration."""
    items = generate_items()
    rows = [{k: str(v) for k, v in i.items()} for i in items]
    if os.path.exists(path):
        if read_csv(path) != rows:
            raise SchemaError(f"{path} exists and differs from the seeded regeneration")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ITEM_FIELDS)
        w.writeheader()
        w.writerows(rows)


def load_calibration(path=C.ITEMS_CSV, exp23_path=C.SOURCES["exp23_items"]) -> list:
    items = ST24.load_calibration(path)
    old = {s for r in read_csv(exp23_path) for s in (r["X"], r["Y"])}
    reused = [i["item_id"] for i in items if i["X"] in old or i["Y"] in old]
    if reused:
        raise SchemaError(f"calibration items reuse Experiment 23 sequences: {reused}")
    return items


def load_pairs() -> list:
    return ST24.load_pairs(C.SOURCES["recognition_pairs"], C.SOURCES["heldout"])


def _trial(stage, prefix, unit_id, kind, role, polarity, X, Y):
    seq = X if role == "X" else Y
    p = P.prompt(kind, polarity, seq)
    return dict(trial_id=f"{prefix}|{kind}|{unit_id}|{role}|{polarity}" if prefix == "rec" else f"{prefix}|{unit_id}|{role}|{polarity}",
                stage=stage, unit_id=unit_id, kind=kind, role=role, polarity=polarity, sequence=seq, X=X, Y=Y,
                prompt=p, prompt_sha256=P.sha256(p))


def calibration_trials(items) -> list:
    return [_trial("calibration", "cal", it["item_id"], it["task"], r, pol, it["X"], it["Y"])
            for it in items for r in C.ROLES for pol in C.POLARITIES]


def preflight_trials(items) -> list:
    """5 technical prompts: X and Y of two calibration items in the pos polarity, plus one generic Yes/No prompt."""
    by_id = {i["item_id"]: i for i in items}
    out = [_trial("preflight", "pre", i, by_id[i]["task"], r, "pos", by_id[i]["X"], by_id[i]["Y"])
           for i in C.PREFLIGHT_ITEMS for r in C.ROLES]
    out.append(dict(trial_id="pre|GENERIC", stage="preflight", unit_id="GENERIC", kind="GENERIC", role="X", polarity="pos",
                    sequence="", X="", Y="", prompt=P.GENERIC, prompt_sha256=P.sha256(P.GENERIC)))
    return out


def screen_trials(pairs) -> list:
    return [_trial("screen", "rec", p["pair_id"], fr, r, pol, p["qwen_seq"], p["mistral_seq"])
            for p in pairs for fr in C.FRAMES for r in C.ROLES for pol in C.POLARITIES]


def shuffled(trials, seed=C.ORDER_SEED) -> list:
    t = list(trials)
    random.Random(seed).shuffle(t)
    return t


def input_hashes() -> dict:
    return ST24.input_hashes(dict(C.SOURCES, calibration_items=C.ITEMS_CSV))
