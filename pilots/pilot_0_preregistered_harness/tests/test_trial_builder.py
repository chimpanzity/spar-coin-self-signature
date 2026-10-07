import random
from collections import Counter
from pathlib import Path

import pytest

from spar_coin_pilot.build_trials import (
    MAX_CELL_RUN,
    balance_report,
    build_all_sessions,
    build_judge_session,
    longest_run,
    render_prompt,
    unordered_sample_pair,
)
from spar_coin_pilot.records import TrialRecord

LABELS = ["astra", "fable", "qwen"]
PROMPT_TEMPLATE = (Path(__file__).resolve().parent.parent / "prompts" / "judge_same_different.txt").read_text(encoding="utf-8")


def make_pool(n=10, seed=1):
    rng = random.Random(seed)
    return {l: [(f"src_{l}_{i:03d}", "".join(rng.choice("HT") for _ in range(50))) for i in range(1, n + 1)] for l in LABELS}


def build(seed=20260921, n_per_cell=6, pool_n=10):
    pool = make_pool(pool_n, seed)
    return build_all_sessions("run", LABELS, pool, n_per_cell, seed, "HT", "HT")


def by_judge(trials: list[TrialRecord], judge: str) -> list[TrialRecord]:
    return sorted([t for t in trials if t.judge_model_label == judge], key=lambda t: t.trial_position)


@pytest.fixture(scope="module")
def built():
    return build()


def test_every_judge_gets_six_trials_per_cell(built):
    trials, _ = built
    for judge in LABELS:
        counts = Counter(t.analytical_cell for t in by_judge(trials, judge))
        assert counts == {"A": 6, "B": 6, "C": 6, "D": 6}


def test_twelve_same_twelve_different(built):
    trials, _ = built
    for judge in LABELS:
        counts = Counter(t.correct_answer for t in by_judge(trials, judge))
        assert counts == {"SAME": 12, "DIFFERENT": 12}


def test_cell_definitions_match_sources(built):
    trials, _ = built
    for judge in LABELS:
        for t in by_judge(trials, judge):
            models = {t.source_1_model_label, t.source_2_model_label}
            if t.analytical_cell == "A":
                assert models == {judge} and t.correct_answer == "SAME"
            elif t.analytical_cell == "B":
                assert judge in models and len(models) == 2 and t.correct_answer == "DIFFERENT"
            elif t.analytical_cell == "C":
                assert judge not in models and len(models) == 1 and t.correct_answer == "SAME"
            else:
                assert judge not in models and len(models) == 2 and t.correct_answer == "DIFFERENT"


def test_cells_B_and_C_balanced_across_other_models(built):
    trials, _ = built
    for judge in LABELS:
        others = [l for l in LABELS if l != judge]
        sub = Counter(t.subcell for t in by_judge(trials, judge))
        for o in others:
            assert sub[f"B:{o}"] == 3
            assert sub[f"C:{o}"] == 3


def test_no_string_paired_with_itself_and_no_repeated_pair(built):
    trials, _ = built
    for judge in LABELS:
        ts = by_judge(trials, judge)
        assert all(t.source_1_sample_id != t.source_2_sample_id for t in ts)
        keys = [unordered_sample_pair(t) for t in ts]
        assert len(keys) == len(set(keys))


def test_string_reuse_is_as_balanced_as_the_pool_permits(built):
    trials, _ = built
    for judge in LABELS:
        ts = by_judge(trials, judge)
        use = Counter()
        for t in ts:
            use[t.source_1_sample_id] += 1
            use[t.source_2_sample_id] += 1
        for label in LABELS:
            counts = sorted(v for k, v in use.items() if k.startswith(f"src_{label}_"))
            slots = 18 if label == judge else 15   # 3n and 2.5n slots over a pool of 10
            assert sum(counts) == slots
            assert len(counts) == 10, "every string in the pool is used at least once"
            assert max(counts) - min(counts) <= 1


def test_display_order_balanced(built):
    trials, _ = built
    for judge in LABELS:
        ts = by_judge(trials, judge)
        b = [t for t in ts if t.analytical_cell == "B"]
        assert sum(t.source_1_model_label == judge for t in b) == 3
        for o in [l for l in LABELS if l != judge]:
            bo = [t for t in b if t.subcell == f"B:{o}"]
            assert abs(sum(t.source_1_model_label == judge for t in bo) - sum(t.source_2_model_label == judge for t in bo)) <= 1
        d = [t for t in ts if t.analytical_cell == "D"]
        first_other = [l for l in LABELS if l != judge][0]
        assert sum(t.source_1_model_label == first_other for t in d) == 3
        for label in LABELS:
            s1 = sum(t.source_1_model_label == label for t in ts)
            s2 = sum(t.source_2_model_label == label for t in ts)
            assert abs(s1 - s2) <= 1
        assert Counter(t.display_order for t in ts) == {"orig": 12, "flipped": 12}


def test_positions_are_a_permutation_and_cell_runs_are_short(built):
    trials, _ = built
    for judge in LABELS:
        ts = by_judge(trials, judge)
        assert [t.trial_position for t in ts] == list(range(1, 25))
        assert len({t.trial_id for t in ts}) == 24
        assert longest_run([t.analytical_cell for t in ts]) <= MAX_CELL_RUN


def test_sequence_is_reproducible_from_seed(built):
    trials, infos = built
    again, infos2 = build()
    assert [t.model_dump() for t in trials] == [t.model_dump() for t in again]
    assert infos == infos2
    for judge in LABELS:
        assert all(t.construction_seed == f"20260921:{judge}" for t in by_judge(trials, judge))
    other, _ = build(seed=7)
    assert [t.model_dump() for t in trials] != [t.model_dump() for t in other]


def test_judge_session_depends_only_on_seed_judge_and_pool_sizes():
    """A judge's session is the same whether built alone or as part of build_all_sessions, and
    does not depend on the string contents of the pool (only on its size)."""
    pool_a, pool_b = make_pool(seed=1), make_pool(seed=2)
    all_a, _ = build_all_sessions("run", LABELS, pool_a, 6, 123, "HT", "HT")
    all_b, _ = build_all_sessions("run", LABELS, pool_b, 6, 123, "HT", "HT")
    key = lambda t: (t.trial_id, t.analytical_cell, t.source_1_sample_id, t.source_2_sample_id, t.display_order)
    assert [key(t) for t in all_a] == [key(t) for t in all_b]
    specs, _ = build_judge_session("fable", ("astra", "qwen"), {l: 10 for l in LABELS}, 6, 123)
    fable_from_all = by_judge(all_a, "fable")
    for spec, rec in zip(specs, fable_from_all):
        (l1, i1), (l2, i2) = spec.displayed()
        assert rec.source_1_sample_id == f"src_{l1}_{i1 + 1:03d}" and rec.source_2_sample_id == f"src_{l2}_{i2 + 1:03d}"
        assert rec.analytical_cell == spec.cell


def test_no_source_identity_or_metadata_in_displayed_stimulus(built):
    trials, _ = built
    forbidden = ["astra", "fable", "qwen", "openai", "anthropic", "src_", "gpt", "claude", "provider", "sample", "2026"]
    for t in trials:
        prompt = render_prompt(PROMPT_TEMPLATE, t.string_1_display, t.string_2_display)
        low = prompt.lower()
        assert not any(tok in low for tok in forbidden), prompt
        assert set(t.string_1_display) <= {"H", "T"} and len(t.string_1_display) == 50
        assert set(t.string_2_display) <= {"H", "T"} and len(t.string_2_display) == 50


def test_balance_report_checks_pass_for_many_seeds():
    for seed in range(1, 41):
        trials, _ = build(seed=seed)
        report = balance_report(trials, LABELS, 6)
        for judge, r in report.items():
            failed = [c for c in r["checks"] if not c["pass"]]
            assert not failed, (seed, judge, failed)


def test_eight_per_cell_variant_also_balances():
    trials, _ = build(seed=5, n_per_cell=8)
    report = balance_report(trials, LABELS, 8)
    for judge, r in report.items():
        assert r["trials_per_cell"] == {"A": 8, "B": 8, "C": 8, "D": 8}
        assert not [c for c in r["checks"] if not c["pass"]], r["checks"]


def test_ab_display_relabels_without_changing_canonical_pool():
    pool = make_pool()
    trials, _ = build_all_sessions("run", LABELS, pool, 6, 1, "AB", "HT")
    for t in trials:
        assert set(t.string_1_display) <= {"A", "B"}
    canon = {sid: s for l in LABELS for sid, s in pool[l]}
    t = trials[0]
    assert t.string_1_display == canon[t.source_1_sample_id].replace("H", "A").replace("T", "B")
