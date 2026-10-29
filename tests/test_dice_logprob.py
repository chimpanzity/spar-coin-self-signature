"""DICE_LOGPROB_v1.0: offline tests (no API calls)."""

import math

import pytest

from spar_dynamic.dice_logprob import client, extract, prompts

GEN = ("Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, "
       "separated by single spaces, with no other text.")


# ------------------------------------------------------------------ prompts --
def test_prompt_g_and_f_byte_exact():
    assert prompts.prompt_g() == GEN
    assert prompts.prompt_f() == (
        "Give me the output you predict from another instance of your model that is asked to do the following:\n\n"
        + GEN + "\n\nReturn exactly the 10 integers you predict that instance would output, separated by single spaces, "
        "with no other text.")


def test_prompt_s7_and_w38_byte_exact():
    head = "Give me the output you predict from another instance of your model that is asked to do the following:\n\n" + GEN + "\n\n"
    assert prompts.prompt_s(7) == head + ("Return only the integer at position 7 of the 10 integers you predict that instance "
                                          "would output. Return exactly one integer from 1 to 6, with no other text.")
    assert prompts.prompt_w(3, 8) == head + (
        "Return only the integers at positions 3 through 8, inclusive, of the 10 integers you predict that instance would "
        "output. Return exactly 6 integers from 1 to 6, in their original order, separated by single spaces, with no other text.")


def test_fifteen_conditions_and_position_maps():
    cs = prompts.conditions()
    assert len(cs) == 15
    assert sum(c["condition_type"] == "S" for c in cs) == 10 and sum(c["condition_type"] == "W" for c in cs) == 3
    w = {c["condition"]: c for c in cs if c["condition_type"] == "W"}
    assert w["W1-5"]["positions"] == [1, 2, 3, 4, 5] and w["W1-5"]["n_expected"] == 5
    assert w["W3-8"]["positions"] == [3, 4, 5, 6, 7, 8] and w["W3-8"]["n_expected"] == 6
    assert w["W5-10"]["positions"] == [5, 6, 7, 8, 9, 10] and w["W5-10"]["n_expected"] == 6
    assert "exactly 5 integers" in w["W1-5"]["prompt"] and "exactly 6 integers" in w["W5-10"]["prompt"]
    for c in cs:
        if c["condition"] != "G":
            assert GEN in c["prompt"]                      # embedded instruction identical
        assert "reason" not in c["prompt"].lower() and "temperature" not in c["prompt"].lower()
    assert len({c["prompt_sha256"] for c in cs}) == 15


def test_request_has_no_system_message_or_tools():
    b = client.request_body(prompts.prompt_g(), client.CONFIG)
    assert b["messages"] == [{"role": "user", "content": GEN}]
    assert "tools" not in b and "tool_choice" not in b and "response_format" not in b
    assert b["temperature"] == 0 and b["logprobs"] is True and b["top_logprobs"] == 20
    assert b["extra_body"]["provider"] == {"order": ["SiliconFlow"], "allow_fallbacks": False, "require_parameters": True}
    assert b["extra_body"]["reasoning"] == {"enabled": False}


# ------------------------------------------------------------------ parsing --
@pytest.mark.parametrize("text,n,verdict", [
    ("5 3 6 1 2 4 6 3 1 5", 10, "valid"),
    ("4", 1, "valid"),
    ("5 3 6 1 2", 10, "wrong_count"),
    ("5 3 6 1 2 4 6 3 1 5 2", 10, "wrong_count"),
    ("5  3 6 1 2 4 6 3 1 5", 10, "format"),
    ("5 3 6 1 2 4 6 3 1 5\n", 10, "format_whitespace"),
    ("5\n3", 2, "format"),
    ("7", 1, "format"),
    ("0 1", 2, "format"),
    ("4.0", 1, "format"),
    ("The answer is 4", 1, "format"),
    ("<think></think>4", 1, "think_tag"),
    ("<tool_call>x", 1, "tool_use"),
])
def test_parser(text, n, verdict):
    assert extract.parse(text, n)["verdict"] == verdict


def test_parser_rejects_truncation_and_tools():
    assert extract.parse("5 3", 2, finish_reason="length")["verdict"] == "truncated"
    assert extract.parse("5 3", 2, tool_calls=True)["verdict"] == "tool_use"


# ---------------------------------------------------------------- alignment --
def _tok(s, lp, alts=None):
    return dict(token=s, logprob=lp, bytes=list(s.encode()), top_logprobs=alts if alts is not None else [dict(token=s, logprob=lp, bytes=list(s.encode()))])


def _alts(prefix, lps):
    return [dict(token=prefix + str(f), logprob=lp, bytes=list((prefix + str(f)).encode())) for f, lp in zip(range(1, 7), lps) if lp is not None]


def test_alignment_separate_space_tokens():
    lps = [-3.0, -2.0, -0.2, -4.0, -5.0, -6.0]
    toks = [_tok("3", -0.2, _alts("", lps)), _tok(" ", 0.0), _tok("5", -0.1, _alts("", [-7, -6, -5, -4, -0.1, -3]))]
    out = extract.align_faces("3 5", toks)
    assert [o["reported_face"] for o in out] == [3, 5]
    assert all(o["comparable_flag"] for o in out)
    assert out[0]["token_prefix"] == "" and out[0]["logprob_face"][1] == -3.0
    assert abs(sum(out[0]["p6"].values()) - 1) < 1e-12
    assert abs(out[0]["six_face_mass"] - sum(math.exp(x) for x in lps)) < 1e-12


def test_alignment_leading_space_tokens_use_same_shape():
    toks = [_tok("2", -0.5, _alts("", [-1, -0.5, -2, -3, -4, -5])),
            _tok(" 6", -0.3, _alts(" ", [-2, -2, -2, -2, -2, -0.3]))]
    out = extract.align_faces("2 6", toks)
    assert out[1]["token_prefix"] == " " and out[1]["comparable_flag"]
    assert out[1]["logprob_face"][6] == -0.3


def test_missing_face_is_missing_not_zero():
    toks = [_tok("4", -0.1, _alts("", [-3, -2, None, -0.1, -5, -6]))]
    o = extract.align_faces("4", toks)[0]
    assert o["logprob_face"][3] is None and not o["candidate_coverage_complete"]
    assert o["p6"] is None and o["six_face_mass"] is None
    assert "faces missing" in o["reason_if_not_comparable"]


def test_other_shape_face_flags_ambiguity_and_is_not_merged():
    alts = _alts("", [-3, -2, -1, -0.1, -5, -6]) + [dict(token=" 4", logprob=-2.5, bytes=list(b" 4"))]
    o = extract.align_faces("4", [_tok("4", -0.1, alts)])[0]
    assert o["candidate_coverage_complete"] and o["tokenization_ambiguity_flag"] and not o["comparable_flag"]
    assert o["logprob_face"][4] == -0.1 and o["other_shape_face_tokens"] == {" 4": -2.5}


def test_multidigit_token_fails_closed():
    out = extract.align_faces("3 5", [_tok("3 5", -0.1)])
    assert all(not o["comparable_flag"] for o in out)
    assert "not a bare face token" in out[0]["reason_if_not_comparable"]


def test_selected_only_logprobs_fail():
    o = extract.align_faces("4", [_tok("4", -0.1)])[0]          # top_logprobs holds only the chosen token
    assert not o["candidate_coverage_complete"]


def test_token_mismatch_with_content_fails_closed():
    o = extract.align_faces("4", [_tok("5", -0.1, _alts("", [-1] * 6))])[0]
    assert not o["comparable_flag"]


# ---------------------------------------------------------------- metrics --
def test_p6_no_underflow():
    p = extract.p6_from_logp([-1000.0, -1001.0, -1002.0, -2000, -2000, -2000])
    assert abs(sum(p.values()) - 1) < 1e-12 and p[1] > p[2] > p[3]


def test_js_properties():
    p = [0.5, 0.5, 0, 0, 0, 0]
    q = [0, 0, 0, 0, 0.5, 0.5]
    r = [0.1, 0.2, 0.3, 0.2, 0.1, 0.1]
    assert extract.js_bits(p, p) == 0
    assert abs(extract.js_bits(p, q) - 1.0) < 1e-12                    # disjoint support: upper bound 1 bit
    assert abs(extract.js_bits(p, r) - extract.js_bits(r, p)) < 1e-12
    assert 0 < extract.js_bits(p, r) < 1


def test_rank_of_non_selected_face():
    p6 = {1: .05, 2: .1, 3: .5, 4: .2, 5: .1, 6: .05}
    assert extract.rank_of(3, p6) == 1 and extract.rank_of(4, p6) == 2 and extract.rank_of(2, p6) == 3 and extract.rank_of(5, p6) == 3


# ------------------------------------------- generic-model control (amendment v1.1, 2026-10-29) --
G_SHA = "edc7a4a228d493e83a5086181c170aa052e3e7cb8b34b9911ef4dc8147fdb8fe"
F_SHA = "8adcaddfff0d9acee6bcc9060917175e7d68167f440c42b00a3800cd32dcef03"


def test_control_g_f_unchanged_and_hashes_frozen():
    cs = {c["condition"]: c for c in prompts.control_conditions()}
    assert list(cs) == ["G", "F", "N"]
    assert cs["G"]["prompt"] == prompts.prompt_g() and cs["G"]["prompt_sha256"] == G_SHA
    assert cs["F"]["prompt"] == prompts.prompt_f() and cs["F"]["prompt_sha256"] == F_SHA
    assert len(prompts.conditions()) == 15                      # original design untouched


def test_control_n_is_single_phrase_substitution():
    f, n = prompts.prompt_f(), prompts.prompt_n()
    assert f.count("another instance of your model") == 1 and "another instance of your model" not in n
    assert n.count("another language model") == 1
    i = f.index("another instance of your model")
    assert n[:i] == f[:i]
    assert n[i + len("another language model"):] == f[i + len("another instance of your model"):]
    assert "that instance would output" in n and GEN in n         # everything else kept
    assert n == ("Give me the output you predict from another language model that is asked to do the following:\n\n"
                 + GEN + "\n\nReturn exactly the 10 integers you predict that instance would output, separated by single spaces, "
                 "with no other text.")


def test_control_position1_metrics_synthetic():
    from spar_dynamic.dice_logprob import control
    g = {1: .001, 2: .004, 3: .225, 4: .234, 5: .535, 6: .001}
    f = {1: .226, 2: .308, 3: .388, 4: .058, 5: .02, 6: .0}
    assert extract.rank_of(5, g) == 1 and extract.rank_of(5, f) == 5
    assert abs(control._margin(f) - .08) < 1e-9 and control._margin(f) < 0.09   # near-tie under the parent floor
    assert control._js(g, g) == 0 and 0.4 < control._js(g, f) < 0.6
    assert abs(control._js(g, f) - control._js(f, g)) < 1e-12
