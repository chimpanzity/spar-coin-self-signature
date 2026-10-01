"""Section 5-6: pair / triplet / trial construction, deterministic given seeds.

Within each split:
  - sort trajectory_ids per model
  - independently permute per-model lists with PAIR_SEED
  - zip into 10 source triplets (one astra, one fable, one mimo each)
  - from each triplet make 3 unordered pairs (A-F, A-M, F-M)
  - 10 triplets * 3 pairs = 30 pairs / split; 60 overall
  - for each (split, source_pair_type): 5 pairs put the alphabetically-first
    label in position A, 5 put it in B (reproducibly shuffled)
  - freeze A/B order for every judge, target, and wording
  - each pair yields 2 target versions * (3 named + 1 SELF) = 8 trials
  - 30 * 8 = 240 trials / split; 480 overall

Trial IDs encode split, pair, target, wording, judge so they are stable.
"""

import csv, hashlib, os, random
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

from . import config as F


@dataclass(frozen=True)
class SourceTriplet:
    triplet_id: str                 # e.g. "dev_t03"
    split: str                      # "development" | "holdout"
    astra_trajectory_id: str
    fable_trajectory_id: str
    mimo_trajectory_id: str


@dataclass(frozen=True)
class Pair:
    pair_id: str                    # e.g. "dev_t03_af"
    triplet_id: str
    split: str
    source_pair_type: str           # "AF" | "AM" | "FM"
    source_label_A: str             # "astra" | "fable" | "mimo"
    source_label_B: str
    sequence_A_id: str              # trajectory_id in position A
    sequence_B_id: str              # trajectory_id in position B
    sequence_A: str
    sequence_B: str


@dataclass(frozen=True)
class Trial:
    trial_id: str
    pair_id: str
    triplet_id: str
    split: str
    target_item_id: str             # pair_id + ":" + target_label
    target_label: str               # "astra" | "fable" | "mimo"
    distractor_label: str
    wording_condition: str          # "NAMED" | "SELF"
    judge_label: str                # "astra" | "fable" | "mimo"
    judge_role: str                 # target_producer | distractor_producer | uninvolved_observer
    source_pair_type: str
    source_label_A: str
    source_label_B: str
    sequence_A_id: str
    sequence_B_id: str
    sequence_A: str
    sequence_B: str
    correct_answer: str             # "A" or "B" — the position of the target's sequence


def _by_model(rows: List[Dict], split: str, source_method: str) -> Dict[str, List[Dict]]:
    out: Dict[str, List[Dict]] = {"astra": [], "fable": [], "mimo": []}
    for r in rows:
        if r["method"] == source_method and r["split"] == split:
            if r["model"] in out:
                out[r["model"]].append(r)
    for m in out:
        out[m].sort(key=lambda r: r["trajectory_id"])
    return out


def build_triplets(corpus_rows: List[Dict], seed: int = F.PAIR_SEED,
                   source_method: str = F.SOURCE_METHOD) -> List[SourceTriplet]:
    """10 triplets per split. Deterministic under seed."""
    triplets: List[SourceTriplet] = []
    for split, split_tag in (("development", "dev"), ("holdout", "hold")):
        per_model = _by_model(corpus_rows, split, source_method)
        assert all(len(per_model[m]) == 10 for m in per_model), \
            f"split {split} needs 10 trajectories per model, got " \
            f"{ {m: len(per_model[m]) for m in per_model} }"
        a_ids = [r["trajectory_id"] for r in per_model["astra"]]
        f_ids = [r["trajectory_id"] for r in per_model["fable"]]
        m_ids = [r["trajectory_id"] for r in per_model["mimo"]]
        # Independent permutations seeded per-model so cross-model draws don't collide
        random.Random(seed + 1).shuffle(a_ids)
        random.Random(seed + 2).shuffle(f_ids)
        random.Random(seed + 3).shuffle(m_ids)
        for i, (a, fa, mi) in enumerate(zip(a_ids, f_ids, m_ids), start=1):
            triplets.append(SourceTriplet(
                triplet_id=f"{split_tag}_t{i:02d}", split=split,
                astra_trajectory_id=a, fable_trajectory_id=fa, mimo_trajectory_id=mi,
            ))
    return triplets


def _seq_lookup(corpus_rows: List[Dict]) -> Dict[str, str]:
    return {r["trajectory_id"]: r["sequence"] for r in corpus_rows}


def build_pairs(triplets: List[SourceTriplet], corpus_rows: List[Dict],
                seed: int = F.PAIR_SEED) -> List[Pair]:
    """3 pairs per triplet. A/B positions balanced within (split, pair_type)."""
    seq = _seq_lookup(corpus_rows)
    # (split, pair_type) -> list of pending triplets in order
    pair_specs: Dict[tuple, List[tuple]] = {}
    for pt in ("AF", "AM", "FM"):
        for sp in ("development", "holdout"):
            pair_specs[(sp, pt)] = []
    for t in triplets:
        pair_specs[(t.split, "AF")].append((t, t.astra_trajectory_id, t.fable_trajectory_id, "astra", "fable"))
        pair_specs[(t.split, "AM")].append((t, t.astra_trajectory_id, t.mimo_trajectory_id,  "astra", "mimo"))
        pair_specs[(t.split, "FM")].append((t, t.fable_trajectory_id, t.mimo_trajectory_id,  "fable", "mimo"))

    pairs: List[Pair] = []
    for (sp, pt), items in pair_specs.items():
        # 5 of the 10 put the alphabetically-first label (first of pair) in A, the other 5 in B.
        # The alphabetically-first label is the first element of the pair name as constructed
        # above (A < F < M), so items[i][3] is the first-alpha label.
        order_rng = random.Random(seed + 101 + hash((sp, pt)) % 1000)
        indices = list(range(len(items)))
        order_rng.shuffle(indices)
        first_in_A = set(indices[:5])
        for i, (t, first_tid, second_tid, first_lbl, second_lbl) in enumerate(items):
            if i in first_in_A:
                A_id, B_id, A_lbl, B_lbl = first_tid, second_tid, first_lbl, second_lbl
            else:
                A_id, B_id, A_lbl, B_lbl = second_tid, first_tid, second_lbl, first_lbl
            pair_id = f"{t.triplet_id}_{pt.lower()}"
            pairs.append(Pair(
                pair_id=pair_id, triplet_id=t.triplet_id, split=sp,
                source_pair_type=pt,
                source_label_A=A_lbl, source_label_B=B_lbl,
                sequence_A_id=A_id, sequence_B_id=B_id,
                sequence_A=seq[A_id], sequence_B=seq[B_id],
            ))
    return pairs


def build_trials(pairs: List[Pair]) -> List[Trial]:
    """8 trials per pair: 2 targets * (3 named + 1 SELF for target producer).

    Thus 60 pairs * 8 = 480 trials.
    """
    trials: List[Trial] = []
    for p in pairs:
        for target_label in (p.source_label_A, p.source_label_B):
            distractor_label = p.source_label_B if target_label == p.source_label_A else p.source_label_A
            correct_answer = "A" if target_label == p.source_label_A else "B"
            target_item_id = f"{p.pair_id}:{target_label}"
            # 3 NAMED (every judge)
            for judge_lbl in F.JUDGE_LABELS:
                if judge_lbl == target_label:
                    role = "target_producer"
                elif judge_lbl == distractor_label:
                    role = "distractor_producer"
                else:
                    role = "uninvolved_observer"
                trials.append(Trial(
                    trial_id=f"{target_item_id}|NAMED|{judge_lbl}",
                    pair_id=p.pair_id, triplet_id=p.triplet_id, split=p.split,
                    target_item_id=target_item_id,
                    target_label=target_label, distractor_label=distractor_label,
                    wording_condition="NAMED", judge_label=judge_lbl, judge_role=role,
                    source_pair_type=p.source_pair_type,
                    source_label_A=p.source_label_A, source_label_B=p.source_label_B,
                    sequence_A_id=p.sequence_A_id, sequence_B_id=p.sequence_B_id,
                    sequence_A=p.sequence_A, sequence_B=p.sequence_B,
                    correct_answer=correct_answer,
                ))
            # 1 SELF (judge == target)
            trials.append(Trial(
                trial_id=f"{target_item_id}|SELF|{target_label}",
                pair_id=p.pair_id, triplet_id=p.triplet_id, split=p.split,
                target_item_id=target_item_id,
                target_label=target_label, distractor_label=distractor_label,
                wording_condition="SELF", judge_label=target_label, judge_role="target_producer",
                source_pair_type=p.source_pair_type,
                source_label_A=p.source_label_A, source_label_B=p.source_label_B,
                sequence_A_id=p.sequence_A_id, sequence_B_id=p.sequence_B_id,
                sequence_A=p.sequence_A, sequence_B=p.sequence_B,
                correct_answer=correct_answer,
            ))
    return trials


def build_prompt(trial: Trial) -> str:
    """Byte-identical for a given (pair, target, wording) across judges (NAMED), and
    well-defined for SELF (judge == target)."""
    target_name = F.JUDGE_BY_LABEL[trial.target_label].display_name
    distractor_name = F.JUDGE_BY_LABEL[trial.distractor_label].display_name
    if trial.wording_condition == "NAMED":
        suffix = F.NAMED_SUFFIX_TEMPLATE.format(
            TARGET_NAME=target_name, DISTRACTOR_NAME=distractor_name,
            SEQUENCE_A=trial.sequence_A, SEQUENCE_B=trial.sequence_B)
    elif trial.wording_condition == "SELF":
        suffix = F.SELF_SUFFIX_TEMPLATE.format(
            DISTRACTOR_NAME=distractor_name,
            SEQUENCE_A=trial.sequence_A, SEQUENCE_B=trial.sequence_B)
    else:
        raise ValueError(f"unknown wording {trial.wording_condition}")
    return F.SHARED_PROTOCOL_PREFIX + "\n" + suffix


def prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# -- CSV writers --------------------------------------------------------------

def write_triplet_manifest(path: str, triplets: List[SourceTriplet]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(triplets[0]).keys()))
        w.writeheader()
        for t in triplets: w.writerow(asdict(t))


def write_pair_manifest(path: str, pairs: List[Pair]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["pair_id", "triplet_id", "split", "source_pair_type",
                      "source_label_A", "source_label_B",
                      "sequence_A_id", "sequence_B_id"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for p in pairs:
            w.writerow({k: getattr(p, k) for k in fieldnames})


def write_trial_manifest(path: str, trials: List[Trial]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = ["trial_id", "pair_id", "triplet_id", "split",
                  "target_item_id", "target_label", "distractor_label",
                  "wording_condition", "judge_label", "judge_role",
                  "source_pair_type", "source_label_A", "source_label_B",
                  "sequence_A_id", "sequence_B_id", "correct_answer"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for t in trials:
            w.writerow({k: getattr(t, k) for k in fieldnames})


def write_prompts_jsonl(path: str, trials: List[Trial]):
    import json
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for t in trials:
            text = build_prompt(t)
            f.write(json.dumps({
                "trial_id": t.trial_id,
                "prompt_hash": prompt_hash(text),
                "prompt_text": text,
            }) + "\n")
