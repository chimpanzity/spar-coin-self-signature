"""Balanced four-cell trial construction, one independent session per judge.

For judge J and the two other models O1, O2 (n = trials_per_cell, default 6):

    Cell A: J-J          correct = SAME       n trials
    Cell B: J-O1, J-O2   correct = DIFFERENT  n trials, n/2 per other model
    Cell C: O1-O1, O2-O2 correct = SAME       n trials, n/2 per other model
    Cell D: O1-O2        correct = DIFFERENT  n trials

Construction is deterministic given the run seed and the judge label. Sample strings are
referred to by their index in the per-model pool of valid strings (in generation order), so
the pairing structure of a dry run with placeholder strings is identical to the real run.

Reuse balance: the slots each model must fill are drawn from concatenated random permutations
of that model's pool, so every string's use count is either floor(slots/pool) or ceil.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from itertools import groupby
from typing import Any, Sequence

from .records import TrialRecord, sha256_text
from .representation import render

CELLS = ("A", "B", "C", "D")
CELL_ANSWER = {"A": "SAME", "B": "DIFFERENT", "C": "SAME", "D": "DIFFERENT"}
MAX_CELL_RUN = 2       # hard constraint on consecutive trials from one cell
MAX_ANSWER_RUN = 3     # soft preference on consecutive identical correct answers


@dataclass
class TrialSpec:
    cell: str
    subcell: str
    correct: str
    src1: tuple[str, int]  # (model label, pool index) in canonical order
    src2: tuple[str, int]
    flipped: bool = False  # display order: True -> src2 is shown as String 1

    @property
    def unordered_key(self) -> frozenset:
        return frozenset([self.src1, self.src2]) if self.src1 != self.src2 else frozenset([self.src1, ("__self__", -1)])

    def displayed(self) -> tuple[tuple[str, int], tuple[str, int]]:
        return (self.src2, self.src1) if self.flipped else (self.src1, self.src2)


class TrialBuildError(RuntimeError):
    pass


# ---------------------------------------------------------------- construction helpers

def _balanced_slots(rng: random.Random, pool_size: int, n_slots: int) -> list[int]:
    slots: list[int] = []
    while len(slots) < n_slots:
        perm = list(range(pool_size))
        rng.shuffle(perm)
        slots.extend(perm)
    return slots[:n_slots]


def _consecutive_pairs(slots: Sequence[int]) -> list[tuple[int, int]]:
    return [(slots[i], slots[i + 1]) for i in range(0, len(slots) - 1, 2)]


def _same_pairs_ok(pairs: list[tuple[int, int]]) -> bool:
    seen: set[frozenset] = set()
    for a, b in pairs:
        if a == b:
            return False
        key = frozenset((a, b))
        if key in seen:
            return False
        seen.add(key)
    return True


def _split_counts(n: int) -> tuple[int, int]:
    """Split n trials across the two other models as evenly as possible."""
    return n - n // 2, n // 2


def _try_build(judge: str, others: tuple[str, str], pool_sizes: dict[str, int], n: int,
               rng: random.Random) -> list[TrialSpec] | None:
    o1, o2 = others
    b_counts = dict(zip(others, _split_counts(n)))            # B trials per other
    c_pairs = dict(zip(others, _split_counts(n)[::-1]))       # C pairs per other (complementary split)
    if c_pairs[o1] + c_pairs[o2] != n or b_counts[o1] + b_counts[o2] != n:
        raise TrialBuildError("internal split error")

    # --- judge's own strings: A pairs (2n slots) then B slots (n)
    j_slots = _balanced_slots(rng, pool_sizes[judge], 3 * n)
    a_pairs = _consecutive_pairs(j_slots[: 2 * n])
    if not _same_pairs_ok(a_pairs):
        return None
    b_j = j_slots[2 * n:]

    # --- other models: C pairs, B slots, D slots
    trials: list[TrialSpec] = [
        TrialSpec("A", "A", "SAME", (judge, a), (judge, b)) for a, b in a_pairs
    ]
    b_o: dict[str, list[int]] = {}
    d_o: dict[str, list[int]] = {}
    for o in others:
        n_c_slots = 2 * c_pairs[o]
        o_slots = _balanced_slots(rng, pool_sizes[o], n_c_slots + b_counts[o] + n)
        c_pairs_o = _consecutive_pairs(o_slots[:n_c_slots])
        if not _same_pairs_ok(c_pairs_o):
            return None
        trials.extend(TrialSpec("C", f"C:{o}", "SAME", (o, a), (o, b)) for a, b in c_pairs_o)
        b_o[o] = o_slots[n_c_slots: n_c_slots + b_counts[o]]
        d_o[o] = o_slots[n_c_slots + b_counts[o]:]

    # --- B: judge vs other
    cursor = 0
    b_specs: list[TrialSpec] = []
    for o in others:
        for o_idx in b_o[o]:
            b_specs.append(TrialSpec("B", f"B:{o}", "DIFFERENT", (judge, b_j[cursor]), (o, o_idx)))
            cursor += 1
    trials.extend(b_specs)

    # --- D: other1 vs other2
    d2 = list(d_o[o2])
    rng.shuffle(d2)
    trials.extend(TrialSpec("D", "D", "DIFFERENT", (o1, a), (o2, b)) for a, b in zip(d_o[o1], d2))

    # --- global uniqueness of unordered string pairs
    keys = [t.unordered_key for t in trials]
    if len(set(keys)) != len(keys):
        return None
    return trials


def _assign_display_order(trials: list[TrialSpec], rng: random.Random) -> None:
    """Balance String 1 / String 2 placement within every sub-cell (and hence globally)."""
    groups: dict[str, list[TrialSpec]] = {}
    for t in trials:
        groups.setdefault(t.subcell, []).append(t)
    # For odd group sizes alternate which group gets the extra flip so the cell total stays even.
    extra_toggle = True
    for subcell in sorted(groups):
        group = groups[subcell]
        n_flip = len(group) // 2
        if len(group) % 2 == 1:
            n_flip += 1 if extra_toggle else 0
            extra_toggle = not extra_toggle
        flips = [True] * n_flip + [False] * (len(group) - n_flip)
        rng.shuffle(flips)
        for t, f in zip(group, flips):
            t.flipped = f


def longest_run(seq: Sequence[Any]) -> int:
    return max((len(list(g)) for _, g in groupby(seq)), default=0)


def _order_trials(trials: list[TrialSpec], rng: random.Random, max_tries: int = 5000) -> tuple[list[TrialSpec], dict]:
    """Randomize presentation order: no more than MAX_CELL_RUN consecutive trials of one cell
    (hard, when achievable) and preferably no more than MAX_ANSWER_RUN consecutive identical
    correct answers (soft)."""
    best: list[TrialSpec] | None = None
    best_score = (10**9, 10**9)
    hard_only: list[TrialSpec] | None = None
    for _ in range(max_tries):
        order = trials[:]
        rng.shuffle(order)
        cell_run = longest_run([t.cell for t in order])
        ans_run = longest_run([t.correct for t in order])
        if cell_run <= MAX_CELL_RUN and ans_run <= MAX_ANSWER_RUN:
            return order, {"cell_run_ok": True, "answer_run_ok": True, "max_cell_run": cell_run, "max_answer_run": ans_run}
        if cell_run <= MAX_CELL_RUN and hard_only is None:
            hard_only = order
        if (cell_run, ans_run) < best_score:
            best_score, best = (cell_run, ans_run), order
    if hard_only is not None:
        return hard_only, {"cell_run_ok": True, "answer_run_ok": False,
                           "max_cell_run": longest_run([t.cell for t in hard_only]),
                           "max_answer_run": longest_run([t.correct for t in hard_only])}
    assert best is not None
    return best, {"cell_run_ok": False, "answer_run_ok": False,
                  "max_cell_run": best_score[0], "max_answer_run": best_score[1]}


# ---------------------------------------------------------------- public API

def session_seed(run_seed: int, judge: str) -> str:
    return f"{run_seed}:{judge}"


def build_judge_session(
    judge: str,
    others: tuple[str, str],
    pool_sizes: dict[str, int],
    trials_per_cell: int,
    run_seed: int,
    max_attempts: int = 5000,
) -> tuple[list[TrialSpec], dict[str, Any]]:
    """Build one judge's balanced, ordered trial list. Deterministic for (run_seed, judge)."""
    seed = session_seed(run_seed, judge)
    n = trials_per_cell
    for label in (judge, *others):
        if pool_sizes[label] < 2:
            raise TrialBuildError(f"pool for {label} has fewer than 2 strings")
    for attempt in range(max_attempts):
        rng = random.Random(f"{seed}:attempt{attempt}")
        trials = _try_build(judge, others, pool_sizes, n, rng)
        if trials is None:
            continue
        _assign_display_order(trials, rng)
        ordered, order_info = _order_trials(trials, rng)
        info = {"construction_seed": seed, "attempts": attempt + 1, **order_info}
        return ordered, info
    raise TrialBuildError(f"could not build a valid session for judge {judge} in {max_attempts} attempts")


def stimulus_hash(string_1_display: str, string_2_display: str) -> str:
    """Hash of the displayed stimulus proper (the two strings, in display order).

    The instruction wording is hashed separately per judgment call (prompt_hash), because the
    response mode (structured vs one-word) can only be fixed after the preflight.
    """
    return sha256_text(string_1_display + "\n" + string_2_display)


def specs_to_records(
    run_id: str,
    judge: str,
    specs: list[TrialSpec],
    pool: dict[str, list[tuple[str, str]]],  # label -> [(sample_id, canonical_string), ...]
    display_alphabet: str,
    canonical_alphabet: str,
    construction_seed: str,
) -> list[TrialRecord]:
    """Turn ordered specs into TrialRecords with rendered strings and stimulus hashes."""
    records: list[TrialRecord] = []
    for pos, t in enumerate(specs, start=1):
        (l1, i1), (l2, i2) = t.displayed()
        sid1, s1 = pool[l1][i1]
        sid2, s2 = pool[l2][i2]
        d1 = render(s1, display_alphabet, canonical_alphabet)
        d2 = render(s2, display_alphabet, canonical_alphabet)
        records.append(TrialRecord(
            run_id=run_id,
            trial_id=f"t_{judge}_{pos:02d}",
            judge_model_label=judge,
            analytical_cell=t.cell,  # type: ignore[arg-type]
            subcell=t.subcell,
            correct_answer=t.correct,  # type: ignore[arg-type]
            source_1_model_label=l1,
            source_2_model_label=l2,
            source_1_sample_id=sid1,
            source_2_sample_id=sid2,
            display_order="flipped" if t.flipped else "orig",
            trial_position=pos,
            construction_seed=construction_seed,
            stimulus_hash=stimulus_hash(d1, d2),
            string_1_display=d1,
            string_2_display=d2,
        ))
    return records


def render_prompt(template: str, string_1: str, string_2: str) -> str:
    return template.replace("{string_1}", string_1).replace("{string_2}", string_2)


def build_all_sessions(
    run_id: str,
    labels: list[str],
    pool: dict[str, list[tuple[str, str]]],
    trials_per_cell: int,
    run_seed: int,
    display_alphabet: str,
    canonical_alphabet: str,
) -> tuple[list[TrialRecord], dict[str, dict[str, Any]]]:
    """Build every judge's session. `others` are the remaining labels in config order."""
    all_records: list[TrialRecord] = []
    infos: dict[str, dict[str, Any]] = {}
    pool_sizes = {label: len(pool[label]) for label in labels}
    for judge in labels:
        others = tuple(l for l in labels if l != judge)
        if len(others) != 2:
            raise TrialBuildError("exactly three models are required")
        specs, info = build_judge_session(judge, others, pool_sizes, trials_per_cell, run_seed)  # type: ignore[arg-type]
        recs = specs_to_records(run_id, judge, specs, pool, display_alphabet,
                                canonical_alphabet, info["construction_seed"])
        all_records.extend(recs)
        infos[judge] = info
    return all_records, infos


# ---------------------------------------------------------------- balance report and checks

def unordered_sample_pair(t: TrialRecord) -> frozenset:
    return frozenset([t.source_1_sample_id, t.source_2_sample_id])


def session_report(trials: list[TrialRecord], judge: str, labels: list[str], trials_per_cell: int) -> dict[str, Any]:
    """Balance report for one judge's session (also the basis of validation checks)."""
    ts = sorted([t for t in trials if t.judge_model_label == judge], key=lambda t: t.trial_position)
    others = [l for l in labels if l != judge]
    cell_counts = Counter(t.analytical_cell for t in ts)
    subcell_counts = Counter(t.subcell for t in ts)
    answer_counts = Counter(t.correct_answer for t in ts)
    pair_freq = Counter("-".join(sorted([t.source_1_model_label, t.source_2_model_label])) for t in ts)
    left_right: dict[str, dict[str, int]] = {l: {"string_1": 0, "string_2": 0} for l in labels}
    for t in ts:
        left_right[t.source_1_model_label]["string_1"] += 1
        left_right[t.source_2_model_label]["string_2"] += 1
    # position balance within DIFFERENT sub-cells: how often the canonical-first model is String 1
    subcell_left: dict[str, dict[str, int]] = {}
    for t in ts:
        if t.analytical_cell == "B":
            key = t.subcell
            d = subcell_left.setdefault(key, {"judge_as_string_1": 0, "judge_as_string_2": 0})
            d["judge_as_string_1" if t.source_1_model_label == judge else "judge_as_string_2"] += 1
        elif t.analytical_cell == "D":
            d = subcell_left.setdefault("D", {f"{others[0]}_as_string_1": 0, f"{others[0]}_as_string_2": 0})
            d[f"{others[0]}_as_string_1" if t.source_1_model_label == others[0] else f"{others[0]}_as_string_2"] += 1
    use_by_model: dict[str, dict[str, int]] = {}
    for t in ts:
        for label, sid in ((t.source_1_model_label, t.source_1_sample_id),
                           (t.source_2_model_label, t.source_2_sample_id)):
            d = use_by_model.setdefault(label, {})
            d[sid] = d.get(sid, 0) + 1
    self_pairs = sum(1 for t in ts if t.source_1_sample_id == t.source_2_sample_id)
    keys = [unordered_sample_pair(t) for t in ts]
    duplicate_pairs = len(keys) - len(set(keys))
    positions = [t.trial_position for t in ts]
    dup_positions = len(positions) != len(set(positions))
    trial_ids = [t.trial_id for t in ts]
    report = {
        "judge": judge,
        "n_trials": len(ts),
        "trials_per_cell": dict(sorted(cell_counts.items())),
        "trials_per_subcell": dict(sorted(subcell_counts.items())),
        "answers": dict(sorted(answer_counts.items())),
        "same_response_expected": answer_counts.get("SAME", 0),
        "source_pair_frequencies": dict(sorted(pair_freq.items())),
        "left_right_by_model": left_right,
        "position_balance_in_different_subcells": subcell_left,
        "use_counts_by_model": {m: dict(sorted(v.items())) for m, v in sorted(use_by_model.items())},
        "use_count_range_by_model": {m: [min(v.values()), max(v.values())] for m, v in use_by_model.items()},
        "self_pairs": self_pairs,
        "duplicate_unordered_pairs": duplicate_pairs,
        "longest_run_by_cell": {c: _longest_run_of_value([t.analytical_cell for t in ts], c) for c in CELLS},
        "longest_run_any_cell": longest_run([t.analytical_cell for t in ts]),
        "longest_run_by_answer": {a: _longest_run_of_value([t.correct_answer for t in ts], a) for a in ("SAME", "DIFFERENT")},
        "longest_run_any_answer": longest_run([t.correct_answer for t in ts]),
        "duplicate_positions": dup_positions,
        "duplicate_trial_ids": len(trial_ids) != len(set(trial_ids)),
        "construction_seed": ts[0].construction_seed if ts else None,
    }
    report["checks"] = session_checks(report, judge, others, trials_per_cell)
    return report


def _longest_run_of_value(seq: Sequence[Any], value: Any) -> int:
    best = 0
    for k, g in groupby(seq):
        if k == value:
            best = max(best, len(list(g)))
    return best


def session_checks(report: dict[str, Any], judge: str, others: list[str], n: int) -> list[dict[str, Any]]:
    """PASS/FAIL checks on a session report (used by build-trials and validate)."""
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    tpc = report["trials_per_cell"]
    add("six_trials_per_cell", all(tpc.get(c, 0) == n for c in CELLS), f"{tpc} (expected {n} each)")
    add("same_different_balance",
        report["answers"].get("SAME", 0) == 2 * n and report["answers"].get("DIFFERENT", 0) == 2 * n,
        f"{report['answers']} (expected {2 * n} each)")
    sc = report["trials_per_subcell"]
    b_split = sorted(sc.get(f"B:{o}", 0) for o in others)
    c_split = sorted(sc.get(f"C:{o}", 0) for o in others)
    expected_split = sorted(_split_counts(n))
    add("cell_B_balanced_across_others", b_split == expected_split, f"B per other: {b_split} (expected {expected_split})")
    add("cell_C_balanced_across_others", c_split == expected_split, f"C per other: {c_split} (expected {expected_split})")
    add("no_self_pairs", report["self_pairs"] == 0, f"{report['self_pairs']} self pairs")
    add("no_duplicate_unordered_pairs", report["duplicate_unordered_pairs"] == 0, f"{report['duplicate_unordered_pairs']} duplicates")
    ranges = report["use_count_range_by_model"]
    add("string_reuse_balanced", all(hi - lo <= 1 for lo, hi in ranges.values()), f"use-count [min,max] per model: {ranges}")
    lr_ok = True
    details = []
    for key, d in report["position_balance_in_different_subcells"].items():
        vals = list(d.values())
        if abs(vals[0] - vals[1]) > 1:
            lr_ok = False
        details.append(f"{key}: {d}")
    for model, d in report["left_right_by_model"].items():
        if abs(d["string_1"] - d["string_2"]) > 1:
            lr_ok = False
        details.append(f"{model} S1/S2: {d['string_1']}/{d['string_2']}")
    add("display_order_balanced", lr_ok, "; ".join(details) or "n/a")
    add("max_cell_run_le_2", report["longest_run_any_cell"] <= MAX_CELL_RUN, f"longest run of one cell: {report['longest_run_any_cell']}")
    add("unique_positions_and_ids", not report["duplicate_positions"] and not report["duplicate_trial_ids"],
        "positions and trial ids unique")
    return checks


def balance_report(trials: list[TrialRecord], labels: list[str], trials_per_cell: int) -> dict[str, Any]:
    return {judge: session_report(trials, judge, labels, trials_per_cell) for judge in labels}


def balance_report_markdown(report: dict[str, Any], infos: dict[str, dict[str, Any]] | None = None) -> str:
    lines = ["# Trial balance report", ""]
    for judge, r in report.items():
        lines.append(f"## Judge: {judge}")
        lines.append("")
        lines.append(f"- trials: {r['n_trials']}; per cell: {r['trials_per_cell']}; per sub-cell: {r['trials_per_subcell']}")
        lines.append(f"- correct answers: {r['answers']}")
        lines.append(f"- source-pair frequencies: {r['source_pair_frequencies']}")
        lines.append(f"- String 1 / String 2 by model: {r['left_right_by_model']}")
        lines.append(f"- position balance in DIFFERENT sub-cells: {r['position_balance_in_different_subcells']}")
        lines.append(f"- use count [min, max] per model: {r['use_count_range_by_model']}")
        lines.append(f"- self pairs: {r['self_pairs']}; duplicate unordered pairs: {r['duplicate_unordered_pairs']}")
        lines.append(f"- longest run by cell: {r['longest_run_by_cell']} (any cell: {r['longest_run_any_cell']})")
        lines.append(f"- longest run by answer: {r['longest_run_by_answer']} (any answer: {r['longest_run_any_answer']})")
        lines.append(f"- construction seed: {r['construction_seed']}"
                     + (f"; build attempts: {infos[judge]['attempts']}" if infos and judge in infos else ""))
        lines.append("")
        lines.append("| check | result | detail |")
        lines.append("|---|---|---|")
        for c in r["checks"]:
            lines.append(f"| {c['check']} | {'PASS' if c['pass'] else 'FAIL'} | {c['detail']} |")
        lines.append("")
        lines.append("Use counts per string:")
        lines.append("")
        for model, counts in r["use_counts_by_model"].items():
            lines.append(f"- {model}: " + ", ".join(f"{sid.split('_')[-1]}x{c}" for sid, c in counts.items()))
        lines.append("")
    return "\n".join(lines)


def trial_manifest_markdown(trials: list[TrialRecord], labels: list[str]) -> str:
    lines = ["# Trial manifest (researcher-facing; judges never see this)", ""]
    for judge in labels:
        ts = sorted([t for t in trials if t.judge_model_label == judge], key=lambda t: t.trial_position)
        lines.append(f"## Judge: {judge} ({len(ts)} trials)")
        lines.append("")
        lines.append("| pos | trial_id | cell | sub-cell | correct | String 1 (source, sample) | String 2 (source, sample) | display |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for t in ts:
            lines.append(
                f"| {t.trial_position} | {t.trial_id} | {t.analytical_cell} | {t.subcell} | {t.correct_answer} "
                f"| {t.source_1_model_label} {t.source_1_sample_id} | {t.source_2_model_label} {t.source_2_sample_id} "
                f"| {t.display_order} |"
            )
        lines.append("")
        lines.append("Displayed strings:")
        lines.append("")
        for t in ts:
            lines.append(f"- {t.trial_id}: S1=`{t.string_1_display}` S2=`{t.string_2_display}` (stimulus sha256 {t.stimulus_hash[:12]})")
        lines.append("")
    return "\n".join(lines)
