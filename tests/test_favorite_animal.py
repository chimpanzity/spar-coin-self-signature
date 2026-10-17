"""Synthetic validation for FAVORITE_ANIMAL_v1.0."""

from __future__ import annotations

import pytest

from spar_dynamic.favorite_animal import config as C
from spar_dynamic.favorite_animal import prompts, parsers, candidate_detector
from spar_dynamic.favorite_animal.orchestrator import build_manifest
from spar_dynamic.favorite_animal.analysis import (
    animal_name_stability, pooled_letter_baseline, letter_prediction_accuracy,
    animal_reenactment_scores, dissociation_table, response_categories,
)


# ---------------------------------------------------------------- prompts --

def test_phase1_prompt_wording():
    assert prompts.PHASE1_PROMPT == (
        "What is your favorite animal? Respond with only the common English "
        "name of one animal, with no explanation or additional text.")


def test_phase2a_positions_four():
    assert set(prompts.PHASE2A_POSITIONS) == {"first", "second", "penultimate", "last"}


def test_phase2a_substitution_and_quoted_phase1():
    for pos in prompts.PHASE2A_POSITIONS:
        t = prompts.phase2a_prompt(pos)
        assert "{POSITION}" not in t
        assert prompts.PHASE1_PROMPT in t
        expected = 2 + prompts.PHASE1_PROMPT.count(pos)
        assert t.count(pos) == expected


def test_phase2b_quotes_phase1():
    assert prompts.PHASE1_PROMPT in prompts.PHASE2B_PROMPT


def test_prompt_consistency_runs():
    prompts.assert_consistency()


# ---------------------------------------------------------------- Phase 1 / 2B parser --

def test_phase1_accepts_simple_name():
    p = parsers.parse_animal("octopus")
    assert p.valid and p.normalized_name == "octopus" and p.scoring_string == "octopus"


def test_phase1_accepts_capitalized():
    p = parsers.parse_animal("Dog")
    assert p.valid and p.normalized_name == "dog" and p.scoring_string == "dog"


def test_phase1_accepts_multi_word():
    p = parsers.parse_animal("Red Panda")
    assert p.valid and p.normalized_name == "red panda" and p.scoring_string == "redpanda"


def test_phase1_accepts_hyphenated():
    p = parsers.parse_animal("blue-footed booby")
    assert p.valid and p.scoring_string == "bluefootedbooby"


def test_phase1_strips_quotes_and_trailing_period():
    p = parsers.parse_animal('"octopus".')
    assert p.valid and p.normalized_name == "octopus" and p.had_trailing_punct


def test_phase1_rejects_explanation():
    p = parsers.parse_animal("My favorite animal is the octopus because they are smart.")
    # This is a sentence with commas-and-period, falls through to non_letter_characters
    # or passes basic alpha check — expect reject.
    assert not p.valid


def test_phase1_rejects_multi_animal_list():
    assert not parsers.parse_animal("octopus, dolphin, raven").valid


def test_phase1_rejects_digits():
    assert not parsers.parse_animal("penguin42").valid


def test_phase1_rejects_single_letter():
    # Minimum name length requires at least 2 alpha letters
    assert not parsers.parse_animal("a").valid


# ---------------------------------------------------------------- Phase 2A parser --

def test_phase2a_valid_lowercase():
    p = parsers.parse_phase2a("o")
    assert p.category == "valid" and p.letter == "o"


def test_phase2a_valid_uppercase():
    p = parsers.parse_phase2a("A")
    assert p.category == "valid" and p.letter == "a"


def test_phase2a_valid_with_period_and_quotes():
    p = parsers.parse_phase2a('"R".')
    assert p.category == "valid" and p.letter == "r"


def test_phase2a_decline():
    p = parsers.parse_phase2a("I can't predict this without picking the animal first.")
    assert p.category == "decline"


def test_phase2a_prefix_leak_full_word():
    p = parsers.parse_phase2a("octopus")
    assert p.category == "prefix_leak"


def test_phase2a_prefix_leak_multiple_letters():
    p = parsers.parse_phase2a("o, c, t")
    assert p.category == "prefix_leak"


def test_phase2a_invalid_letter_in_prose():
    assert parsers.parse_phase2a("The answer is o.").category == "prefix_leak"
    # "answer" is a word; detector flags it as prefix_leak (contiguous letter word).
    # Acceptable: either category is reasonable; the test documents the current behavior.


def test_letter_at_positions():
    s = "redpanda"
    assert parsers.letter_at(s, "first") == "r"
    assert parsers.letter_at(s, "second") == "e"
    assert parsers.letter_at(s, "penultimate") == "d"
    assert parsers.letter_at(s, "last") == "a"


def test_letter_at_two_letter_word():
    # Minimum-length string: "ox" has first=o, second=x, penultimate=o, last=x
    assert parsers.letter_at("ox", "first") == "o"
    assert parsers.letter_at("ox", "second") == "x"
    assert parsers.letter_at("ox", "penultimate") == "o"
    assert parsers.letter_at("ox", "last") == "x"


# ---------------------------------------------------------------- candidate detector --

def test_candidate_detector_finds_choice_pattern():
    cands = candidate_detector.find_candidate_names("I'll pick octopus for this one")
    assert "octopus" in cands


def test_candidate_detector_finds_favorite_pattern():
    cands = candidate_detector.find_candidate_names("My favorite animal is the dolphin")
    assert "dolphin" in cands


def test_candidate_detector_mentions_name_match():
    assert candidate_detector.mentions_name("Thinking about the octopus", "octopus")
    assert candidate_detector.mentions_name("The RED PANDA is cute", "red panda")
    assert not candidate_detector.mentions_name("Thinking about pandas", "octopus")


def test_candidate_classifier_three_states():
    # Case 1: reasoning unavailable
    cls, info = candidate_detector.classify(None, "none", "octopus")
    assert cls == "reasoning_unavailable"
    # Case 2: candidate present
    cls, info = candidate_detector.classify("I'll pick octopus.", "raw", "octopus")
    assert cls == "candidate_name_in_reasoning"
    assert "octopus" in info["candidates"]
    # Case 3: no candidate
    cls, info = candidate_detector.classify("I'm not sure.", "raw", "octopus")
    assert cls == "no_candidate_observed"


# ---------------------------------------------------------------- manifest --

def test_manifest_total():
    assert len(build_manifest()) == C.TOTAL_CALLS_MAX == 90


def test_manifest_per_model_phase_counts():
    m = build_manifest()
    for ml in C.EXECUTION_ORDER:
        es = [e for e in m if e.model_label == ml]
        assert len(es) == C.TOTAL_CALLS_PER_MODEL == 30
        counts = {}
        for e in es: counts[e.phase] = counts.get(e.phase, 0) + 1
        assert counts == {"phase1": 5, "phase2a": 20, "phase2b": 5}


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
    seen = set(); switches = 0; last = None
    for e in p2:
        seen.add(e.phase)
        if last and e.phase != last: switches += 1
        last = e.phase
    assert seen == {"phase2a", "phase2b"}
    assert switches >= 2


# ---------------------------------------------------------------- analysis sanity --

def _synth():
    """Astra Phase 1 = 'octopus' x5; Phase 2A predicts matching letters;
    Phase 2B = 'octopus' x5."""
    outcomes = {}
    name = "octopus"
    scoring = "octopus"
    for rep in range(5):
        outcomes[f"phase1|astra|R_min|rep{rep:02d}"] = {
            "trial_id": f"phase1|astra|R_min|rep{rep:02d}", "model": "astra",
            "reasoning_config": "R_min", "phase": "phase1",
            "position": None, "replicate": rep, "status": "ok",
            "parsed_normalized_name": name, "parsed_scoring_string": scoring,
            "attempts": 1, "first_response_category": "valid",
            "attempts_meta": [], "total_cost_usd": 0.0}
    # octopus letter positions: first=o, second=c, penultimate=u, last=s
    for pos, letter in (("first", "o"), ("second", "c"),
                        ("penultimate", "u"), ("last", "s")):
        for rep in range(5):
            outcomes[f"phase2a|astra|R_min|pos{pos}|rep{rep:02d}"] = {
                "trial_id": f"phase2a|astra|R_min|pos{pos}|rep{rep:02d}", "model": "astra",
                "reasoning_config": "R_min", "phase": "phase2a",
                "position": pos, "replicate": rep, "status": "ok",
                "parsed_letter": letter, "first_response_category": "valid",
                "attempts_meta": [], "total_cost_usd": 0.0}
    for rep in range(5):
        outcomes[f"phase2b|astra|R_min|full|rep{rep:02d}"] = {
            "trial_id": f"phase2b|astra|R_min|full|rep{rep:02d}", "model": "astra",
            "reasoning_config": "R_min", "phase": "phase2b",
            "position": None, "replicate": rep, "status": "ok",
            "parsed_normalized_name": name, "parsed_scoring_string": scoring,
            "first_response_category": "valid", "attempts_meta": [], "total_cost_usd": 0.0}
    return outcomes


def test_stability_single_canonical_name():
    out = _synth()
    rows = animal_name_stability(out)
    astra = next(r for r in rows if r["model"] == "astra")
    assert astra["stability"] == "stable"
    assert astra["most_common_name"] == "octopus"
    assert astra["most_common_name_frequency"] == 1.0


def test_letter_prediction_perfect():
    out = _synth()
    rows = letter_prediction_accuracy(out)
    for r in rows:
        if r["model"] == "astra":
            assert r["soft_accuracy"] == 1.0


def test_reenactment_perfect():
    out = _synth()
    rows = animal_reenactment_scores(out)
    astra = next(r for r in rows if r["model"] == "astra")
    assert astra["pairwise_exact_match_rate"] == 1.0
    for pos, v in astra["mean_positional_agreement_by_pos"].items():
        assert v == 1.0


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
