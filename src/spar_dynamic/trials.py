"""Trial construction for the judgment phase.

Per (judge, architecture) block: 24 trials = 6 A + 6 B + 6 C + 6 D.

Rules:
  * strings on a trial always come from the SAME architecture
  * no string paired with itself
  * no unordered (string_id_1, string_id_2) pair repeated within a block
  * String 1 / String 2 placement balanced within block
  * B split evenly across the two non-self models
  * C split evenly across the two non-self models
  * D uses one string from each of the two non-self models
  * every source trajectory used at least once if feasible
  * reproducible via a fixed seed
  * source identities never appear in the model-facing prompt
"""

import random, uuid
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from . import config as C


@dataclass
class Trial:
    trial_id: str
    judge_label: str
    architecture: str
    cell: str                       # A|B|C|D
    correct_answer: str             # SAME|DIFFERENT
    source_model_1: str
    source_model_2: str
    trajectory_id_1: str
    trajectory_id_2: str
    display_string_1: str
    display_string_2: str


def _pair(models_str: List[Tuple[str, str]], rng: random.Random,
          same_ok: bool, first_from: str = None, second_from: str = None,
          used_unordered: set = None) -> Tuple[Tuple[str,str], Tuple[str,str]]:
    """Pick two trajectories from the list of (source_model_label, trajectory_id).
    Ensure:
      - if same_ok=False: source models differ
      - if same_ok=True and no first_from/second_from constraints: source models same
      - no self-pair (same trajectory both sides)
      - unordered pair not already used
      - `first_from` and `second_from` restrict source model of positions when given
    """
    if used_unordered is None:
        used_unordered = set()
    attempts = 0
    while attempts < 500:
        attempts += 1
        cand1 = [t for t in models_str if (first_from is None or t[0] == first_from)]
        cand2 = [t for t in models_str if (second_from is None or t[0] == second_from)]
        if not cand1 or not cand2:
            raise ValueError("no candidates for constraints")
        a = rng.choice(cand1)
        b = rng.choice(cand2)
        if a[1] == b[1]:
            continue  # same trajectory
        if same_ok is False and a[0] == b[0]:
            continue
        if same_ok is True and a[0] != b[0]:
            continue
        # unordered dedup
        uk = tuple(sorted([a[1], b[1]]))
        if uk in used_unordered:
            continue
        used_unordered.add(uk)
        return a, b
    raise RuntimeError("could not find a valid pair matching constraints")


def build_trials_for_judge_arch(
    judge_label: str, architecture: str,
    trajectories: Dict[str, List[Tuple[str, str]]],   # model_label -> [(model_label, traj_id, sequence)]
    rng: random.Random,
) -> List[Trial]:
    """Build 24 trials for one (judge, architecture) block.

    `trajectories[model_label]` is a list of 3-tuples: (label, trajectory_id, sequence).
    """
    n_per = C.TRIALS_PER_CELL_PER_JUDGE_PER_ARCH
    other_models = [m for m in C.MODEL_LABELS if m != judge_label]
    assert len(other_models) == 2, "expected exactly 2 non-self models"

    # flat lists per model (label, traj_id, seq)
    def _flat(model_label):
        return [(model_label, tid, seq) for (label, tid, seq)
                in trajectories[model_label]]

    self_list = _flat(judge_label)
    other0_list = _flat(other_models[0])
    other1_list = _flat(other_models[1])
    all_by_model = {judge_label: self_list,
                    other_models[0]: other0_list,
                    other_models[1]: other1_list}
    # merged (model, traj_id, seq) for pair generator convenience
    combined = self_list + other0_list + other1_list

    used_unordered: set = set()

    def _pick_pair_from_labels(label_a: str, label_b: str) -> Tuple[Tuple, Tuple]:
        # Draws one trajectory from each named model.
        # (label_a, label_b) with label_a == label_b means SAME model (but distinct trajectories).
        # tuples format: (model_label, traj_id, seq)
        lst_a = all_by_model[label_a]
        lst_b = all_by_model[label_b]
        attempts = 0
        while attempts < 500:
            attempts += 1
            a = rng.choice(lst_a)
            b = rng.choice(lst_b)
            if a[1] == b[1]:
                continue
            uk = tuple(sorted([a[1], b[1]]))
            if uk in used_unordered:
                continue
            used_unordered.add(uk)
            return a, b
        raise RuntimeError(f"could not sample from ({label_a}, {label_b})")

    trials: List[Trial] = []

    # Cell A: own + own  -> SAME
    for _ in range(n_per):
        a, b = _pick_pair_from_labels(judge_label, judge_label)
        trials.append(_trial("A", "SAME", judge_label, architecture, a, b, rng))

    # Cell B: own + other -> DIFFERENT (split evenly across the two other models)
    b_per_other = n_per // 2
    b_remainder = n_per - 2 * b_per_other   # 0 for n_per=6
    for other_label in other_models:
        for _ in range(b_per_other):
            a, b = _pick_pair_from_labels(judge_label, other_label)
            trials.append(_trial("B", "DIFFERENT", judge_label, architecture, a, b, rng))
    for _ in range(b_remainder):
        # remaining slots -> alternate
        chosen = rng.choice(other_models)
        a, b = _pick_pair_from_labels(judge_label, chosen)
        trials.append(_trial("B", "DIFFERENT", judge_label, architecture, a, b, rng))

    # Cell C: same-other + same-other -> SAME (split evenly across the two other models)
    c_per_other = n_per // 2
    c_remainder = n_per - 2 * c_per_other
    for other_label in other_models:
        for _ in range(c_per_other):
            a, b = _pick_pair_from_labels(other_label, other_label)
            trials.append(_trial("C", "SAME", judge_label, architecture, a, b, rng))
    for _ in range(c_remainder):
        chosen = rng.choice(other_models)
        a, b = _pick_pair_from_labels(chosen, chosen)
        trials.append(_trial("C", "SAME", judge_label, architecture, a, b, rng))

    # Cell D: other1 + other2 -> DIFFERENT
    for _ in range(n_per):
        a, b = _pick_pair_from_labels(other_models[0], other_models[1])
        trials.append(_trial("D", "DIFFERENT", judge_label, architecture, a, b, rng))

    # Balance String 1 / String 2 placement within block: randomly flip half of trials.
    # Preserve correct_answer (flipping doesn't change SAME/DIFFERENT).
    n_flip = len(trials) // 2
    flip_indices = rng.sample(range(len(trials)), n_flip)
    for i in flip_indices:
        t = trials[i]
        trials[i] = Trial(
            trial_id=t.trial_id, judge_label=t.judge_label,
            architecture=t.architecture, cell=t.cell,
            correct_answer=t.correct_answer,
            source_model_1=t.source_model_2, source_model_2=t.source_model_1,
            trajectory_id_1=t.trajectory_id_2, trajectory_id_2=t.trajectory_id_1,
            display_string_1=t.display_string_2, display_string_2=t.display_string_1,
        )

    # Shuffle order within the block; also avoid long runs of one cell or one correct answer
    rng.shuffle(trials)
    # Simple guardrail against >3 consecutive identical cells or answers.
    trials = _debunch(trials, rng)
    return trials


def _trial(cell: str, correct: str, judge_label: str, architecture: str,
           a: Tuple[str, str, str], b: Tuple[str, str, str],
           rng: random.Random) -> Trial:
    return Trial(
        trial_id=str(uuid.uuid4()),
        judge_label=judge_label, architecture=architecture,
        cell=cell, correct_answer=correct,
        source_model_1=a[0], source_model_2=b[0],
        trajectory_id_1=a[1], trajectory_id_2=b[1],
        display_string_1=a[2], display_string_2=b[2],
    )


def _debunch(trials: List[Trial], rng: random.Random, max_run: int = 3) -> List[Trial]:
    """Very light-touch reshuffling: if the sequence has runs of the same cell/answer
    longer than max_run, swap offending items with earlier compatible ones. Best-effort."""
    def offense(seq):
        n_bad = 0
        for i in range(max_run, len(seq)):
            if all(seq[j].cell == seq[i].cell for j in range(i-max_run, i+1)):
                n_bad += 1
            if all(seq[j].correct_answer == seq[i].correct_answer for j in range(i-max_run, i+1)):
                n_bad += 1
        return n_bad
    best = list(trials); best_off = offense(best)
    for _ in range(200):
        if best_off == 0:
            break
        cand = list(best)
        i, j = rng.sample(range(len(cand)), 2)
        cand[i], cand[j] = cand[j], cand[i]
        o = offense(cand)
        if o < best_off:
            best, best_off = cand, o
    return best


def build_all_trials(source_trajectories, seed: int = C.TRIAL_CONSTRUCTION_SEED) -> List[Trial]:
    """Full trial construction across all judges and architectures.

    source_trajectories: dict[(architecture, model_label)] -> list of (label, traj_id, seq).
    Returns 144 Trial objects (24 per (judge, arch)).
    """
    all_trials: List[Trial] = []
    for judge in C.MODEL_LABELS:
        for arch in C.ARCHITECTURES:
            arch_trajectories = {ml: source_trajectories[(arch, ml)]
                                 for ml in C.MODEL_LABELS}
            # per-block seed = base_seed + hash(judge, arch)
            block_seed = (seed * 1000003
                          + hash((judge, arch)) & 0xffff)
            rng = random.Random(block_seed)
            block = build_trials_for_judge_arch(judge, arch, arch_trajectories, rng)
            all_trials.extend(block)
    return all_trials
