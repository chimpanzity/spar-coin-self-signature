"""Synthetic validation for FAVORITE_INTEGER_v1.0."""

from __future__ import annotations

import pytest

from spar_dynamic.favorite_integer import config as C
from spar_dynamic.favorite_integer import prompts, parsers, prefix_detector
from spar_dynamic.favorite_integer.orchestrator import build_manifest
from spar_dynamic.favorite_integer.analysis import (
    favorite_integer_stability, pooled_digit_baseline,
    digit_accuracy, reenactment_scores, dissociation_table, response_categories,
)


# ---------------------------------------------------------------- prompts --

def test_phase1_prompt_wording():
    assert prompts.PHASE1_PROMPT == (
        "What is your favorite ten-digit positive integer? Return exactly ten "
        "digits, with no spaces or other text. The first digit cannot be zero.")


def test_phase2a_ordinals_four_positions():
    assert set(prompts.PHASE2A_ORDINALS) == {1, 2, 5, 9}


def test_phase2a_substitution_and_quoted_phase1():
    # "first" appears once inside Phase 1 ("The first digit cannot be zero"),
    # so at pos 1 the ordinal should show up 3 times (2 subs + 1 in quoted P1).
    for pos, word in prompts.PHASE2A_ORDINALS.items():
        t = prompts.phase2a_prompt(pos)
        assert "{ORDINAL}" not in t
        assert prompts.PHASE1_PROMPT in t
        expected = 2 + prompts.PHASE1_PROMPT.count(word)
        assert t.count(word) == expected, (
            f"pos={pos} word={word!r} got={t.count(word)} expected={expected}")


def test_phase2b_quotes_phase1():
    assert prompts.PHASE1_PROMPT in prompts.PHASE2B_PROMPT
    assert "Write out exactly the response you would give" in prompts.PHASE2B_PROMPT


def test_prompt_consistency_runs():
    prompts.assert_consistency()


# ---------------------------------------------------------------- phase 1 / 2B parser --

def test_phase1_accepts_valid_ten_digit():
    p = parsers.parse_phase1("3141592653")
    assert p.valid and p.integer_str == "3141592653"


def test_phase1_rejects_leading_zero():
    p = parsers.parse_phase1("0123456789")
    assert not p.valid and p.reason == "leading zero"


def test_phase1_rejects_wrong_length():
    assert not parsers.parse_phase1("12345").valid
    assert not parsers.parse_phase1("123456789012").valid


def test_phase1_rejects_internal_spaces():
    assert not parsers.parse_phase1("31415 92653").valid


def test_phase1_rejects_prose():
    assert not parsers.parse_phase1("My favorite is 3141592653").valid


def test_phase1_strips_trailing_period():
    p = parsers.parse_phase1("3141592653.")
    assert p.valid and p.integer_str == "3141592653" and p.had_trailing_punct


# ---------------------------------------------------------------- phase 2A parser --

def test_phase2a_valid_single_digit_other_position():
    p = parsers.parse_phase2a("4", position=5)
    assert p.category == "valid" and p.digit == 4


def test_phase2a_valid_zero_at_non_leading():
    p = parsers.parse_phase2a("0", position=5)
    assert p.category == "valid" and p.digit == 0


def test_phase2a_zero_at_position_1_is_invalid():
    p = parsers.parse_phase2a("0", position=1)
    assert p.category == "invalid"


def test_phase2a_decline():
    p = parsers.parse_phase2a("I cannot determine this without generating the full integer.", position=5)
    assert p.category == "decline"


def test_phase2a_prefix_leak():
    p = parsers.parse_phase2a("3141592653", position=5)
    assert p.category == "prefix_leak"


def test_phase2a_invalid_integer_in_prose():
    assert parsers.parse_phase2a("The answer is 4.", position=5).category == "invalid"


def test_phase2a_truncation_detection():
    assert parsers.is_truncated("length")
    assert not parsers.is_truncated("stop")


# ---------------------------------------------------------------- prefix detector --

def test_detector_fires_on_contiguous_run():
    assert prefix_detector.has_prefix_run("the integer 1234567890 appears in reasoning")
    assert prefix_detector.has_prefix_run("5555")


def test_detector_fires_on_separated_run():
    assert prefix_detector.has_prefix_run("digits 3 1 4 1 5 9 2 6 5 3")
    assert prefix_detector.has_prefix_run("1, 2, 3, 4")


def test_detector_no_false_positive_on_phrases():
    # Common phrases that must not trigger
    assert not prefix_detector.has_prefix_run("there are 10 digits in the integer")
    assert not prefix_detector.has_prefix_run("choose a digit from 0 to 9")
    assert not prefix_detector.has_prefix_run("the range 1-9")
    assert not prefix_detector.has_prefix_run("digits from 0 through 9")
    assert not prefix_detector.has_prefix_run("ten digits")


def test_detector_requires_at_least_four():
    # Only 3 digits — no run
    assert not prefix_detector.has_prefix_run("123")
    # 4+ contiguous digits — run
    assert prefix_detector.has_prefix_run("1234")


def test_detector_returns_matched_run():
    result = prefix_detector.find_prefix_run("the number 3141592653 is my favorite")
    assert result is not None
    sub, digits = result
    assert sub == "3141592653"
    assert digits == [3, 1, 4, 1, 5, 9, 2, 6, 5, 3]


# ---------------------------------------------------------------- manifest --

def test_manifest_total_count():
    m = build_manifest()
    assert len(m) == C.TOTAL_CALLS_MAX == 90


def test_manifest_per_model_counts():
    m = build_manifest()
    for ml in C.EXECUTION_ORDER:
        es = [e for e in m if e.model_label == ml]
        assert len(es) == C.TOTAL_CALLS_PER_MODEL == 30
        phase_counts = {}
        for e in es: phase_counts[e.phase] = phase_counts.get(e.phase, 0) + 1
        assert phase_counts == {"phase1": 5, "phase2a": 20, "phase2b": 5}


def test_manifest_phase1_sequential():
    m = build_manifest()
    for ml in C.EXECUTION_ORDER:
        es = [e for e in m if e.model_label == ml]
        p1 = [e for e in es if e.phase == "phase1"]
        assert es[:5] == p1


def test_manifest_phase2_interleaved():
    m = build_manifest()
    es = [e for e in m if e.model_label == "astra"]
    p2 = [e for e in es if e.phase.startswith("phase2")]
    seen = set(); last = None; switches = 0
    for e in p2:
        seen.add(e.phase)
        if last and e.phase != last: switches += 1
        last = e.phase
    assert seen == {"phase2a", "phase2b"}
    assert switches >= 2


# ---------------------------------------------------------------- analysis sanity --

def _synth():
    """Astra Phase 1 all = 3141592653; Phase 2A varied; Phase 2B all = Phase 1."""
    outcomes = {}
    seq = "3141592653"
    for rep in range(5):
        outcomes[f"phase1|astra|R_min|rep{rep:02d}"] = {
            "trial_id": f"phase1|astra|R_min|rep{rep:02d}", "model": "astra",
            "reasoning_config": "R_min", "phase": "phase1",
            "position": None, "replicate": rep, "status": "ok",
            "parsed_integer_str": seq, "attempts": 1,
            "first_response_category": "valid", "attempts_meta": [],
            "total_cost_usd": 0.0}
    # Phase 2A predicts matching digit at each position
    # Phase 1 is unanimous "3141592653", so digit at pos 1=3, pos 2=1, pos 5=5, pos 9=5
    for pos, preds in ((1, [3,3,3,3,3]), (2, [1,1,1,1,1]), (5, [5,5,5,5,5]), (9, [5,5,5,5,5])):
        for rep, pred in enumerate(preds):
            outcomes[f"phase2a|astra|R_min|pos{pos}|rep{rep:02d}"] = {
                "trial_id": f"phase2a|astra|R_min|pos{pos}|rep{rep:02d}", "model": "astra",
                "reasoning_config": "R_min", "phase": "phase2a",
                "position": pos, "replicate": rep, "status": "ok",
                "parsed_digit": pred, "first_response_category": "valid",
                "attempts_meta": [], "total_cost_usd": 0.0}
    for rep in range(5):
        outcomes[f"phase2b|astra|R_min|full|rep{rep:02d}"] = {
            "trial_id": f"phase2b|astra|R_min|full|rep{rep:02d}", "model": "astra",
            "reasoning_config": "R_min", "phase": "phase2b",
            "position": None, "replicate": rep, "status": "ok",
            "parsed_integer_str": seq, "first_response_category": "valid",
            "attempts_meta": [], "total_cost_usd": 0.0}
    return outcomes


def test_stability_perfect():
    out = _synth()
    rows = favorite_integer_stability(out)
    astra = next(r for r in rows if r["model"] == "astra")
    assert astra["stability"] == "stable"
    assert astra["most_common_integer"] == "3141592653"
    assert astra["most_common_integer_frequency"] == 1.0


def test_digit_accuracy_perfect():
    out = _synth()
    rows = digit_accuracy(out)
    for r in rows:
        if r["model"] == "astra":
            assert r["soft_accuracy"] == 1.0


def test_reenactment_perfect():
    out = _synth()
    rows = reenactment_scores(out)
    astra = next(r for r in rows if r["model"] == "astra")
    assert astra["mean_positional_agreement"] == 1.0
    assert astra["pairwise_exact_match_rate"] == 1.0


def test_dissociation_zero_when_both_perfect():
    out = _synth()
    rows = dissociation_table(out)
    for r in rows:
        if r["model"] == "astra":
            assert r["dissociation_reenact_minus_single"] == 0.0


def test_response_categories_sum():
    out = _synth()
    rows = response_categories(out)
    for r in rows:
        assert (r["ok"] + r["decline"] + r["prefix_leak"] + r["invalid"]
                 + r["truncated"] + r["abandoned"]) == r["attempted"]
