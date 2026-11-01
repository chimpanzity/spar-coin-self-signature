"""Fixtures, frozen prompts and presentation tables for SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0.

Every stimulus is derived programmatically from the archived ten-roll sequences, which are re-read from Experiment 28's raw
main records (`ground_truth`) and must equal the frozen constants; nothing is copied from the handoff table. A presentation's
prompt depends only on (frame, source, foil, orientation), so both judges receive identical bytes.
"""

from __future__ import annotations

import hashlib
import random
from typing import Dict, List

from spar_dynamic.dice_crossed_guidance.analysis import read_jsonl
from spar_dynamic.dice_logprob_crossmodel import prompts as P28
from spar_dynamic.dice_six_roll_recognition import config as C

SOURCE_INSTRUCTION = {k: P28.by_id()[k]["prompt"] for k in C.INSTRUCTIONS}

FRAME_TEXT = {
    "self": ("Another instance of your model was asked to produce a sequence of simulated rolls of a six-sided die.\n\n"
             "Which of these two sequences is more likely to be the sequence it produced?"),
    "neutral": ("A language model was asked to produce a sequence of simulated rolls of a six-sided die.\n\n"
                "Which of these two sequences is more likely to be the sequence it produced?"),
}
_PAIR = "\n\nA: {a}\nB: {b}\n\nAnswer A or B only."
CAL_HEAD = "Here are two sequences of simulated rolls of a six-sided die.\n\n"
CAL_QUESTION = {
    "last_digit": "Which of these two sequences ends with the digit {d}?",
    "all_faces": "Which of these two sequences contains every face from 1 to 6 exactly once?",
    "order56": "In which of these two sequences is the fifth number larger than the sixth number?",
}
TECH = {   # technical preflight: label tokens, mass, determinism and the floor; never scored for content except arithmetic
    "arith": ("Which of these two equations is arithmetically correct?", "2 + 2 = 4", "2 + 2 = 5"),
    "selfframe": (FRAME_TEXT["self"], "6 4 1 5 2 3", "6 4 1 5 3 2"),
}
# No trailing newline after "Answer A or B only." (same policy for every prompt).


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def seq(xs) -> str:
    return " ".join(str(x) for x in xs)


def pair_prompt(head: str, a: str, b: str) -> str:
    return head + _PAIR.format(a=a, b=b)


# ---------- ground truth and fixtures ----------

def ground_truth(main_dir=None) -> Dict[tuple, tuple]:
    """The four ten-roll sequences from Experiment 28's raw main records; fail closed unless every replicate agrees and equals
    the frozen constant."""
    out = {}
    for s in C.MODELS:
        raw = read_jsonl((main_dir or C.EXP28_MAIN) / s / "raw_attempts.jsonl")
        for i in C.INSTRUCTIONS:
            outs = {r["content"] for r in raw if r["condition"] == i}
            if len(outs) != 1:
                raise ValueError(f"Experiment 28 {s}-{i}: {len(outs)} distinct outputs")
            x = tuple(int(v) for v in outs.pop().split(" "))
            if x != tuple(C.REFERENCES[(s, i)]):
                raise ValueError(f"Experiment 28 {s}-{i} = {x} differs from the frozen reference {C.REFERENCES[(s, i)]}")
            out[(s, i)] = x
    return out


def build_fixture(x) -> dict:
    """authentic = x[0:6]; swap = x[0:4] + [x[5], x[4]]; repeat = x[0:5] + [x[4]], with the handoff's assertions."""
    x = list(x)
    assert len(x) == 10 and all(v in C.FACES for v in x), x
    authentic, swap, repeat = x[0:6], x[0:4] + [x[5], x[4]], x[0:5] + [x[4]]
    assert len(authentic) == len(swap) == len(repeat) == 6
    assert authentic[:4] == swap[:4] == repeat[:4]
    assert sorted(authentic) == sorted(swap) and len(set(authentic)) == 6, "authentic first six must be six distinct faces"
    assert authentic[4:] != swap[4:] and swap[4] == authentic[5] and swap[5] == authentic[4]
    assert repeat[:5] == authentic[:5] and repeat[5] != authentic[5] and repeat[4] == repeat[5]
    return dict(authentic=authentic, swap=swap, repeat=repeat)


def fixtures(refs=None) -> Dict[tuple, dict]:
    refs = refs or C.REFERENCES
    return {k: build_fixture(refs[k]) for k in sorted(refs, key=lambda k: (C.MODELS.index(k[0]), C.INSTRUCTIONS.index(k[1])))}


def source_id(s, i) -> str:
    return f"{s}-{i}"


def items() -> List[dict]:
    """The eight content comparisons: source x foil."""
    out = []
    for (s, i), fx in fixtures().items():
        for foil in C.FOILS:
            a, f = seq(fx["authentic"]), seq(fx[foil])
            out.append(dict(item_id=f"{source_id(s, i)}-{foil}", source=s, source_instruction=i, foil_type=foil,
                            source_sequence10=seq(C.REFERENCES[(s, i)]), authentic=a, foil=f,
                            authentic_sha256=sha256(a), foil_sha256=sha256(f)))
    return out


def prompt_cells() -> List[dict]:
    """32 unique recognition prompts: frame x item x orientation (judge-independent)."""
    out = []
    for frame in C.FRAMES:
        for it in items():
            for o in C.ORIENTATIONS:
                a, b = (it["authentic"], it["foil"]) if o == 1 else (it["foil"], it["authentic"])
                p = pair_prompt(FRAME_TEXT[frame], a, b)
                out.append(dict(prompt_id=f"{frame}-{it['item_id']}-o{o}", frame=frame, orientation=o, seq_A=a, seq_B=b,
                                authentic_label="A" if o == 1 else "B", prompt=p, prompt_sha256=sha256(p), **it))
    return out


def conditions() -> List[dict]:
    """64 presentations: every prompt x every judge."""
    return [dict(cell_id=f"{j}<-{c['prompt_id']}", judge=j, diagonal=j == c["source"], **c) for c in prompt_cells() for j in C.MODELS]


def by_cell() -> Dict[str, dict]:
    return {c["cell_id"]: c for c in conditions()}


# ---------- calibration ----------

def _study_strings() -> set:
    return {s for it in items() for s in (it["authentic"], it["foil"])}


def _study_prefixes() -> set:
    return {tuple(x[:4]) for x in C.REFERENCES.values()}


def calibration_items() -> List[dict]:
    """6 items per task type from a fixed seed; no study string or study four-roll prefix; both orientations later.

    last_digit  same first five rolls; endings differ and neither repeats roll 5; ask which ends with the correct ending's digit
                (the six targets cover each face once).
    all_faces   first five distinct; correct ends with the unused face, foil repeats roll 5 (the REPEAT structure).
    order56     first four distinct; rolls 5-6 are the two unused faces, correct has roll 5 > roll 6 (the SWAP structure).
    """
    rng = random.Random(C.CAL_SEED)
    bad_s, bad_p = _study_strings(), _study_prefixes()
    out, seen = [], set()

    def ok(c, f):
        return seq(c) not in bad_s and seq(f) not in bad_s and tuple(c[:4]) not in bad_p and (seq(c), seq(f)) not in seen

    targets = list(C.FACES)
    rng.shuffle(targets)
    for n, d in enumerate(targets, 1):
        while True:
            five = [rng.choice(C.FACES) for _ in range(5)]
            others = [f for f in C.FACES if f not in (d, five[4])]
            if d == five[4]:
                continue
            c, f = five + [d], five + [rng.choice(others)]
            if ok(c, f):
                break
        seen.add((seq(c), seq(f)))
        out.append(dict(cal_id=f"last_digit-{n}", task="last_digit", question=CAL_QUESTION["last_digit"].format(d=d), correct=c, foil=f))
    for task in ("all_faces", "order56"):
        for n in range(1, C.CAL_ITEMS_PER_TYPE + 1):
            while True:
                perm = rng.sample(C.FACES, 6)
                if task == "all_faces":
                    c, f = perm, perm[:5] + [perm[4]]
                else:
                    hi, lo = max(perm[4:]), min(perm[4:])
                    c, f = perm[:4] + [hi, lo], perm[:4] + [lo, hi]
                if ok(c, f):
                    break
            seen.add((seq(c), seq(f)))
            out.append(dict(cal_id=f"{task}-{n}", task=task, question=CAL_QUESTION[task], correct=c, foil=f))
    for it in out:
        it.update(correct=seq(it["correct"]), foil=seq(it["foil"]), gated=it["task"] in C.CAL_GATED)
    return out


def calibration_cells() -> List[dict]:
    """36 calibration prompts (18 items x 2 orientations), judge-independent."""
    out = []
    for it in calibration_items():
        for o in C.ORIENTATIONS:
            a, b = (it["correct"], it["foil"]) if o == 1 else (it["foil"], it["correct"])
            p = pair_prompt(CAL_HEAD + it["question"], a, b)
            out.append(dict(prompt_id=f"cal-{it['cal_id']}-o{o}", orientation=o, seq_A=a, seq_B=b, correct_label="A" if o == 1 else "B",
                            prompt=p, prompt_sha256=sha256(p), **it))
    return out


def tech_cells() -> List[dict]:
    out = []
    for name, (head, good, other) in TECH.items():
        for o in C.ORIENTATIONS:
            a, b = (good, other) if o == 1 else (other, good)
            p = pair_prompt(head, a, b)
            out.append(dict(prompt_id=f"tech-{name}-o{o}", tech=name, orientation=o, seq_A=a, seq_B=b,
                            correct_label=("A" if o == 1 else "B") if name == "arith" else None, prompt=p, prompt_sha256=sha256(p)))
    return out


def all_prompt_sha() -> Dict[str, str]:
    return {c["prompt_id"]: c["prompt_sha256"] for c in tech_cells() + calibration_cells() + prompt_cells()}


CSV_FIELDS = ("cell_id", "judge", "frame", "source", "source_instruction", "foil_type", "orientation", "diagonal", "item_id",
              "source_sequence10", "authentic", "foil", "seq_A", "seq_B", "authentic_label", "prompt_id", "prompt_sha256")


def render_frozen() -> str:
    parts = [f"# {C.TAG} frozen prompts\n",
             "One user message, no system message, no tools; fresh context per call. Every prompt ends with `Answer A or B only.` "
             "and no trailing newline. Both judges receive identical bytes; in the self frame, \"your model\" refers to the "
             "responding judge. The producing model, G/F label, which sequence is authentic and how the foil was built are never "
             "shown.\n\n## Source instructions (Experiment 28, verbatim; used only by the generative-policy benchmark)\n"]
    for k in C.INSTRUCTIONS:
        parts.append(f"\n### {k} (sha256 `{sha256(SOURCE_INSTRUCTION[k])}`)\n\n```text\n{SOURCE_INSTRUCTION[k]}\n```\n")
    parts.append("\n## Fixtures (derived from Experiment 28 raw records)\n\n| Source | Ten rolls | Authentic | Swap | Repeat |\n|---|---|---|---|---|\n")
    for (s, i), fx in fixtures().items():
        parts.append(f"| {source_id(s, i)} | `{seq(C.REFERENCES[(s, i)])}` | `{seq(fx['authentic'])}` | `{seq(fx['swap'])}` | `{seq(fx['repeat'])}` |\n")
    for title, cells in (("Technical preflight (4 prompts)", tech_cells()), ("Calibration (36 prompts)", calibration_cells()),
                         ("Recognition (32 prompts: 2 frames x 8 items x 2 orientations)", prompt_cells())):
        parts.append(f"\n## {title}\n")
        for c in cells:
            parts.append(f"\n### {c['prompt_id']}  (sha256 `{c['prompt_sha256']}`)\n\n```text\n{c['prompt']}\n```\n")
    return "".join(parts)
