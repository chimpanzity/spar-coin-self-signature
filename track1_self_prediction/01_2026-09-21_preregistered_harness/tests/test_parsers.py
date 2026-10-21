import pytest

from spar_coin_pilot.parse import (
    parse_judgment,
    parse_judgment_one_word,
    parse_judgment_structured,
    parse_source_string,
)

GOOD = "HT" * 25


# ---------------------------------------------------------------- source strings

def test_source_accepts_exactly_50_ht():
    r = parse_source_string(GOOD)
    assert r.valid and r.value == GOOD and r.reason is None


def test_source_trims_surrounding_whitespace_only():
    assert parse_source_string("\n  " + GOOD + " \r\n").valid
    assert parse_source_string(GOOD).value == GOOD


@pytest.mark.parametrize("bad, reason_prefix", [
    (GOOD[:-1], "wrong_length:49"),
    (GOOD + "H", "wrong_length:51"),
    (GOOD.lower(), "disallowed_characters"),
    ("HT HT" + GOOD[5:], "disallowed_characters"),
    ("Here are your flips: " + GOOD, "disallowed_characters"),
    (GOOD[:25] + "\n" + GOOD[25:], "disallowed_characters"),
    ("H,T," * 25, "disallowed_characters"),
    ("", "empty_completion"),
    ("   ", "empty_completion"),
    (None, "empty_completion"),
])
def test_source_rejects_everything_else(bad, reason_prefix):
    r = parse_source_string(bad)
    assert not r.valid and r.value is None
    assert r.reason.startswith(reason_prefix)


def test_source_configurable_length_and_alphabet():
    assert parse_source_string("AB" * 5, length=10, alphabet="AB").valid
    assert not parse_source_string("HT" * 5, length=10, alphabet="AB").valid


# ---------------------------------------------------------------- one-word judgments

@pytest.mark.parametrize("raw, expected", [
    ("SAME", "SAME"), ("same", "SAME"), (" Different. ", "DIFFERENT"), ("**SAME**", "SAME"),
    ('"DIFFERENT"', "DIFFERENT"), ("SAME!", "SAME"), ("`same`", "SAME"), ("Different\n", "DIFFERENT"),
])
def test_one_word_strict_accepts_single_label(raw, expected):
    r = parse_judgment_one_word(raw)
    assert r.valid and r.value == expected


@pytest.mark.parametrize("raw, reason", [
    ("SAME or DIFFERENT", "both_labels_present"),
    ("I think SAME, not DIFFERENT.", "both_labels_present"),
    ("The answer is SAME", "label_embedded_in_extra_text"),
    ("They look similar", "no_label"),
    ("SAMEDIFFERENT", "no_label"),
    ("", "empty_completion"),
    (None, "empty_completion"),
])
def test_one_word_strict_rejects(raw, reason):
    r = parse_judgment_one_word(raw)
    assert not r.valid and r.reason == reason


def test_one_word_lenient_accepts_short_embedded_label_but_never_both():
    assert parse_judgment_one_word("The answer is SAME", lenient=True).value == "SAME"
    assert parse_judgment_one_word("Not the same.", lenient=True).reason == "negated_label"
    assert parse_judgment_one_word("They aren't different", lenient=True).reason == "negated_label"
    assert not parse_judgment_one_word("SAME or DIFFERENT", lenient=True).valid
    long_reply = "word " * 20 + "SAME"
    assert not parse_judgment_one_word(long_reply, lenient=True).valid


# ---------------------------------------------------------------- structured judgments

def test_structured_accepts_schema_shape():
    assert parse_judgment_structured('{"judgment": "SAME"}').value == "SAME"
    assert parse_judgment_structured('  {"judgment":"different"} ').value == "DIFFERENT"
    assert parse_judgment_structured('```json\n{"judgment": "SAME"}\n```').value == "SAME"


@pytest.mark.parametrize("raw, reason_prefix", [
    ('{"judgment": "MAYBE"}', "judgment_not_in_enum"),
    ('{"judgment": "SAME", "why": "x"}', "unexpected_keys"),
    ('{"verdict": "SAME"}', "unexpected_keys"),
    ('["SAME"]', "json_not_object"),
    ('SAME', "not_json"),
    ('{"judgment": 1}', "judgment_not_string"),
    ("", "empty_completion"),
])
def test_structured_rejects(raw, reason_prefix):
    r = parse_judgment_structured(raw)
    assert not r.valid and r.reason.startswith(reason_prefix)


def test_structured_lenient_falls_back_to_one_word_and_records_it():
    r = parse_judgment_structured("SAME", lenient=True)
    assert r.valid and r.value == "SAME" and r.reason == "lenient_non_json_fallback"
    assert not parse_judgment_structured("SAME or DIFFERENT", lenient=True).valid


def test_parse_judgment_dispatch():
    assert parse_judgment("SAME", "one_word").value == "SAME"
    assert parse_judgment('{"judgment": "SAME"}', "structured").value == "SAME"
    with pytest.raises(ValueError):
        parse_judgment("SAME", "other")
