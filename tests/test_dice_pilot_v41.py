"""Synthetic validation tests for DICE_PILOT_v4.1 per spec §16."""

from __future__ import annotations

import json
import pytest

from spar_dynamic.dice_pilot_v41 import config as C
from spar_dynamic.dice_pilot_v41 import prompts, parsers, prefix_detector
from spar_dynamic.dice_pilot_v41.orchestrator import build_manifest
from spar_dynamic.dice_pilot_v41.analysis import (
    phase1_stability, pooled_digit_baseline, single_v4_accuracy,
    matched_prompt_comparison, full_seq_scores, cross_model_template_matrix,
    dissociation_table, response_categories, decision_rule,
)


# ---------------------------------------------------------------- prompts --

def test_phase1_prompt_byte_match_with_v31():
    from spar_dynamic.dice_pilot import prompts as v31
    assert prompts.PHASE1_PROMPT == v31.PHASE1_PROMPT


def test_phase2a_byte_match_with_v31_pos2():
    from spar_dynamic.dice_pilot import prompts as v31
    assert prompts.PHASE2A_PROMPT == v31.phase2_prompt(2)


def test_phase2b_ordinals_four_positions():
    assert set(prompts.PHASE2B_ORDINALS) == {1, 2, 5, 9}
    assert prompts.PHASE2B_ORDINALS[1] == "first"
    assert prompts.PHASE2B_ORDINALS[2] == "second"
    assert prompts.PHASE2B_ORDINALS[5] == "fifth"
    assert prompts.PHASE2B_ORDINALS[9] == "ninth"


def test_phase2b_substitution_and_quoted_phase1():
    for pos, word in prompts.PHASE2B_ORDINALS.items():
        t = prompts.phase2b_prompt(pos)
        assert "{ORDINAL}" not in t
        assert prompts.PHASE1_PROMPT in t
        assert t.count(word) == 2


def test_phase2c_quotes_phase1():
    assert prompts.PHASE1_PROMPT in prompts.PHASE2C_PROMPT
    assert "exactly the response you would give" in prompts.PHASE2C_PROMPT


def test_consistency_check_runs():
    prompts.assert_consistency()


# ---------------------------------------------------------------- prefix detector --

def test_prefix_detector_not_fired_on_between_1_and_6():
    assert not prefix_detector.has_prefix_run("pick an integer between 1 and 6")
    assert not prefix_detector.has_prefix_run("the user wants an integer from 1 to 6")
    assert not prefix_detector.has_prefix_run("values are 1 or 2 or 3 or 4 or 5 or 6")


def test_prefix_detector_fires_on_four_plus_consecutive_digits():
    assert prefix_detector.has_prefix_run("I'll pick 3 5 2 6 1 4 2 5 3 6 and extract the fifth")
    assert prefix_detector.has_prefix_run("the sequence 1 2 3 4")
    assert prefix_detector.has_prefix_run("1, 2, 3, 4, 5")


def test_prefix_detector_requires_at_least_four():
    assert not prefix_detector.has_prefix_run("the digits are 1 2 3 then prose")
    assert prefix_detector.has_prefix_run("the digits are 1 2 3 4 then prose")


def test_prefix_detector_returns_matched_run():
    result = prefix_detector.find_prefix_run("prelude 3 5 2 6 1 4 postlude")
    assert result is not None
    sub, digits = result
    assert digits == [3, 5, 2, 6, 1, 4]
    assert "3 5 2 6 1 4" in sub


def test_prefix_detector_handles_empty_and_none():
    assert prefix_detector.find_prefix_run("") is None
    assert prefix_detector.find_prefix_run(None) is None


# ---------------------------------------------------------------- parsers --

def test_phase1_parser_accepts_valid():
    p = parsers.parse_phase1("3 1 4 1 5 2 6 3 1 4")
    assert p.valid and p.values == [3, 1, 4, 1, 5, 2, 6, 3, 1, 4]


def test_phase1_parser_rejects_wrong_length():
    assert not parsers.parse_phase1("3 1 4 1 5").valid
    assert not parsers.parse_phase1("3 1 4 1 5 2 6 3 1 4 2").valid


def test_phase1_parser_rejects_out_of_range():
    assert not parsers.parse_phase1("3 1 4 1 5 2 7 3 1 4").valid


def test_phase2_parser_valid_single_integer():
    p = parsers.parse_phase2("4")
    assert p.category == "valid" and p.value == 4


def test_phase2_parser_decline():
    p = parsers.parse_phase2("I cannot determine the value without generating the full sequence.")
    assert p.category == "decline"


def test_phase2_parser_prefix_leak():
    p = parsers.parse_phase2("3 5 2 6")
    assert p.category == "prefix_leak"


def test_phase2_parser_invalid():
    assert parsers.parse_phase2("The answer is 4.").category == "invalid"


def test_truncation_detection():
    assert parsers.is_truncated("length")
    assert parsers.is_truncated("LENGTH")
    assert not parsers.is_truncated("stop")
    assert not parsers.is_truncated("")


# ---------------------------------------------------------------- manifest --

def test_manifest_total_count():
    m = build_manifest()
    assert len(m) == C.TOTAL_CALLS_MAX == 210


def test_manifest_per_model_counts():
    m = build_manifest()
    for ml in C.EXECUTION_ORDER:
        es = [e for e in m if e.model_label == ml]
        assert len(es) == C.TOTAL_CALLS_PER_MODEL == 35
        phase_counts = {}
        for e in es: phase_counts[e.phase] = phase_counts.get(e.phase, 0) + 1
        assert phase_counts == {"phase1": 5, "phase2a": 5, "phase2b": 20, "phase2c": 5}


def test_manifest_phase1_first_per_model():
    m = build_manifest()
    for ml in C.EXECUTION_ORDER:
        es = [e for e in m if e.model_label == ml]
        p1 = [e for e in es if e.phase == "phase1"]
        p2 = [e for e in es if e.phase.startswith("phase2")]
        # Every phase1 entry comes before every phase2 entry in this model's block
        assert es[:5] == p1
        assert es[5:] == p2


def test_manifest_phase2_interleaved():
    """Phase 2A/B/C are shuffled together; it's NOT the case that all 2A come
    before all 2B before all 2C."""
    m = build_manifest()
    es = [e for e in m if e.model_label == "astra"]
    p2 = [e for e in es if e.phase.startswith("phase2")]
    seen_phases = set()
    switches = 0
    last = None
    for e in p2:
        if last is not None and e.phase != last: switches += 1
        last = e.phase; seen_phases.add(e.phase)
    assert seen_phases == {"phase2a", "phase2b", "phase2c"}
    # Interleaving should produce multiple phase switches, not just 2.
    assert switches >= 3


# ---------------------------------------------------------------- analysis sanity --

def _synthetic_outcomes():
    """Build a minimal outcomes dict for astra with 5 Phase-1 reps, Phase 2A pos 2,
    Phase 2B at all four positions, Phase 2C 5 reps."""
    outcomes = {}
    seq1 = [4, 1, 6, 3, 2, 5, 2, 6, 6, 1]
    for rep in range(5):
        outcomes[f"phase1|astra|R_min|rep{rep:02d}"] = {
            "trial_id": f"phase1|astra|R_min|rep{rep:02d}", "model": "astra",
            "reasoning_config": "R_min", "phase": "phase1",
            "position": None, "replicate": rep, "status": "ok",
            "parsed_values": seq1, "attempts": 1,
            "first_response_category": "valid", "attempts_meta": [],
            "total_cost_usd": 0.0}
    # Phase 2A: all "4" at pos 2 (one hit coincidence)
    for rep in range(5):
        outcomes[f"phase2a|astra|R_min|pos2|rep{rep:02d}"] = {
            "trial_id": f"phase2a|astra|R_min|pos2|rep{rep:02d}", "model": "astra",
            "reasoning_config": "R_min", "phase": "phase2a",
            "position": 2, "replicate": rep, "status": "ok", "parsed_value": 4,
            "first_response_category": "valid", "attempts_meta": [],
            "total_cost_usd": 0.0}
    # Phase 2B: pos 1 predicts "4" (matches), pos 2 predicts "1" (matches), pos 5 predicts "2" (matches)
    for pos, pred in ((1, 4), (2, 1), (5, 2), (9, 6)):
        for rep in range(5):
            outcomes[f"phase2b|astra|R_min|pos{pos}|rep{rep:02d}"] = {
                "trial_id": f"phase2b|astra|R_min|pos{pos}|rep{rep:02d}", "model": "astra",
                "reasoning_config": "R_min", "phase": "phase2b",
                "position": pos, "replicate": rep, "status": "ok", "parsed_value": pred,
                "first_response_category": "valid", "attempts_meta": [],
                "total_cost_usd": 0.0}
    # Phase 2C: 5 identical reenactments of seq1
    for rep in range(5):
        outcomes[f"phase2c|astra|R_min|full|rep{rep:02d}"] = {
            "trial_id": f"phase2c|astra|R_min|full|rep{rep:02d}", "model": "astra",
            "reasoning_config": "R_min", "phase": "phase2c",
            "position": None, "replicate": rep, "status": "ok",
            "parsed_values": seq1, "first_response_category": "valid",
            "attempts_meta": [], "total_cost_usd": 0.0}
    return outcomes


def test_phase1_stability_computes():
    out = _synthetic_outcomes()
    rows = phase1_stability(out)
    astra = next(r for r in rows if r["model"] == "astra")
    assert astra["n_valid"] == 5
    assert astra["stability"] == "stable"
    assert astra["modal_at_position"] == [4, 1, 6, 3, 2, 5, 2, 6, 6, 1]


def test_pooled_digit_baseline_computes():
    out = _synthetic_outcomes()
    rows = pooled_digit_baseline(out)
    astra = next(r for r in rows if r["model"] == "astra")
    # Pooled digit distribution of [4,1,6,3,2,5,2,6,6,1] * 5 reps:
    # 1:2, 2:2, 3:1, 4:1, 5:1, 6:3. Mode = 6. Pos 1 = 4, so baseline at pos 1 = 0.
    assert astra["pooled_mode_digit"] == 6
    assert astra["baseline_soft_accuracy_by_position"]["1"] == 0.0
    assert astra["baseline_soft_accuracy_by_position"]["9"] == 1.0  # pos 9 is 6


def test_full_seq_scores_perfect_reenactment():
    out = _synthetic_outcomes()
    rows = full_seq_scores(out)
    astra = next(r for r in rows if r["model"] == "astra")
    assert astra["mean_positional_agreement"] == 1.0
    assert astra["exact_match_any_phase1"] == 5
    assert astra["mean_prefix_match_length_vs_modal"] == 10.0


def test_dissociation_computes():
    out = _synthetic_outcomes()
    rows = dissociation_table(out)
    # At pos 5: Phase 2B predicts "2" (hit, soft=1); P2C always has "2" at pos 5
    #   (perfect reenactment), so reenact_at_pos = 1.0. Dissociation = 0.
    pos5 = next(r for r in rows if r["model"] == "astra" and r["position"] == 5)
    assert pos5["single_position_soft_accuracy"] == 1.0
    assert pos5["reenactment_positional_agreement_at_pos"] == 1.0
    assert pos5["dissociation_reenact_minus_single"] == 0.0


def test_cross_model_matrix_shape():
    out = _synthetic_outcomes()
    rows = cross_model_template_matrix(out)
    assert len(rows) == len(C.EXECUTION_ORDER)
    # astra row should have 1.0 self-agreement; other cols None (no data).
    astra = next(r for r in rows if r["reenact_model"] == "astra")
    assert astra["vs_astra"] == 1.0
    for other in ("fable", "sonnet", "oss120", "oss20", "qwen"):
        assert astra[f"vs_{other}"] is None


def test_matched_prompt_comparison_computes():
    out = _synthetic_outcomes()
    rows = matched_prompt_comparison(out)
    astra = next(r for r in rows if r["model"] == "astra")
    # Phase 2A predicts "4" at pos 2; Phase 1 pos 2 is "1" (unanimous). Soft = 0.
    assert astra["phase2a_soft_accuracy"] == 0.0
    # Phase 2B pos 2 predicts "1" five times → soft = 1.0.
    assert astra["phase2b_soft_accuracy"] == 1.0
    assert astra["soft_accuracy_delta_B_minus_A"] == 1.0


def test_response_categories_sum_to_attempted():
    out = _synthetic_outcomes()
    rows = response_categories(out)
    for r in rows:
        assert (r["ok"] + r["decline"] + r["prefix_leak"] + r["invalid"]
                 + r["truncated"] + r["abandoned"]) == r["attempted"]
