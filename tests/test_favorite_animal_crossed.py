"""Synthetic validation for FAVORITE_ANIMAL_CROSSED_v1.0."""

from __future__ import annotations

import pytest

from spar_dynamic.favorite_animal_crossed import config as C
from spar_dynamic.favorite_animal_crossed import prompts
from spar_dynamic.favorite_animal_crossed.orchestrator import build_manifest
from spar_dynamic.favorite_animal_crossed.analysis import (
    crossed_prediction_accuracy, crossed_pair_summary,
    crossed_self_vs_other, response_categories,
)


def test_six_cross_pairs():
    assert len(C.CROSS_PAIRS) == 6
    labels = set(C.CROSS_PAIRS)
    assert ("astra", "fable") in labels
    assert ("fable", "astra") in labels
    assert ("fable", "oss120") in labels
    assert ("oss120", "fable") in labels
    for p, t in C.CROSS_PAIRS:
        assert p != t


def test_prior_canonical_favorite_known():
    assert C.PRIOR_CANONICAL_FAVORITE["astra"] == "octopus"
    assert C.PRIOR_CANONICAL_FAVORITE["fable"] == "octopus"
    assert C.PRIOR_CANONICAL_FAVORITE["oss120"] == "elephant"


def test_prompt_consistency():
    prompts.assert_consistency()


def test_crossed_prompt_substitutes_target_name():
    t = prompts.crossed_prompt("GPT-6 Astra", "second")
    assert "GPT-6 Astra" in t
    assert "second" in t
    assert "{POSITION}" not in t and "{TARGET_NAME}" not in t
    assert prompts.EMBEDDED_INSTRUCTION in t


def test_manifest_total():
    m = build_manifest()
    assert len(m) == C.TOTAL_CALLS_MAX == 120


def test_manifest_pair_counts():
    m = build_manifest()
    counts = {}
    for e in m:
        key = (e.predictor_model, e.target_model)
        counts[key] = counts.get(key, 0) + 1
    assert len(counts) == 6
    for key, n in counts.items():
        assert n == C.CALLS_PER_PAIR == 20


def test_manifest_phase2_positions_covered():
    m = build_manifest()
    for pair in C.CROSS_PAIRS:
        block = [e for e in m if (e.predictor_model, e.target_model) == pair]
        pos_counts = {}
        for e in block: pos_counts[e.position] = pos_counts.get(e.position, 0) + 1
        assert pos_counts == {"first": 5, "second": 5, "penultimate": 5, "last": 5}


def _synth_outcomes():
    """Perfect-knowledge crossed outcomes: every predictor correctly predicts
    every other model's favorite letters."""
    outcomes = {}
    for (predictor, target) in C.CROSS_PAIRS:
        target_fav = C.PRIOR_CANONICAL_FAVORITE[target]
        for pos in C.PHASE2_POSITIONS:
            from spar_dynamic.favorite_animal_crossed.parsers import letter_at
            correct = letter_at(target_fav, pos)
            for rep in range(5):
                tid = f"crossed|{predictor}|target{target}|pos{pos}|rep{rep:02d}"
                outcomes[tid] = {
                    "trial_id": tid, "predictor_model": predictor,
                    "target_model": target, "target_name": C.TARGET_NAMED[target],
                    "position": pos, "replicate": rep,
                    "status": "ok", "parsed_letter": correct,
                    "first_response_category": "valid",
                    "attempts_meta": [], "total_cost_usd": 0.0,
                }
    return outcomes


def test_accuracy_perfect():
    out = _synth_outcomes()
    rows = crossed_prediction_accuracy(out)
    for r in rows:
        assert r["soft_accuracy"] == 1.0


def test_pair_summary_perfect():
    out = _synth_outcomes()
    rows = crossed_pair_summary(out)
    for r in rows:
        assert r["overall_accuracy"] == 1.0


def test_self_vs_other_runs():
    out = _synth_outcomes()
    rows = crossed_self_vs_other(out)
    assert len(rows) == 3
    for r in rows:
        assert r["crossed_mean_other"] == 1.0
        # delta = cross - self for e.g. astra: 1.0 - 0.0 = +1.0
        if r["predictor"] == "astra":
            assert r["delta_cross_minus_self"] == 1.0
        if r["predictor"] == "fable":
            assert r["delta_cross_minus_self"] == 0.0


def test_response_categories_sum():
    out = _synth_outcomes()
    rows = response_categories(out)
    for r in rows:
        assert (r["ok"] + r["decline"] + r["prefix_leak"] + r["invalid"]
                 + r["truncated"] + r["abandoned"]) == r["attempted"]
