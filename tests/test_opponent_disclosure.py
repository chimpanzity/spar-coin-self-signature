import json
from collections import Counter

import pytest

from opponent_disclosure import analysis as A
from opponent_disclosure import config as C
from opponent_disclosure.game import FakeTransport, Runner, history_text, parse_choice, player_prompt, request_body

ROWS = [{"round": 1, "matcher": "STAR", "mismatcher": "TRIANGLE", "winner": "Mismatcher"},
        {"round": 2, "matcher": "STAR", "mismatcher": "STAR", "winner": "Matcher"},
        {"round": 3, "matcher": "TRIANGLE", "mismatcher": "STAR", "winner": "Mismatcher"}]


def test_history_format_matches_handoff_example():
    assert history_text(ROWS) == ("Round | Matcher | Mismatcher | Winner\n"
                                  "1     | STAR    | TRIANGLE  | Mismatcher\n"
                                  "2     | STAR    | STAR      | Matcher\n"
                                  "3     | TRIANGLE| STAR      | Mismatcher")
    assert history_text([]) == "None. This is the first round."


def test_prompts_verbatim_and_only_identity_line_differs():
    for role in ("matcher", "mismatcher"):
        i = player_prompt(role, True, ROWS, 4).splitlines()
        u = player_prompt(role, False, ROWS, 4).splitlines()
        d = [k for k, (x, y) in enumerate(zip(i, u)) if x != y]
        assert len(i) == len(u) and len(d) == 1
        assert i[d[0]] == C.INFORMED and u[d[0]] == C.UNINFORMED
        assert i[0] == C.SHARED and i[-1] == "Return your final choice on the last line, using exactly STAR or TRIANGLE."
    m = player_prompt("matcher", False, [], 1)
    assert "You are the MATCHER.\nYour objective is to choose the SAME shape as the Mismatcher." in m
    assert "Astra" not in m and "Round 1 of 20: choose STAR or TRIANGLE." in m
    assert "You are the MISMATCHER.\nYour objective is to choose a DIFFERENT shape from the Matcher." in player_prompt("mismatcher", True, [], 1)


def test_no_future_or_private_leakage():
    with pytest.raises(AssertionError):
        player_prompt("matcher", True, ROWS, 3)
    with pytest.raises(AssertionError):
        player_prompt("matcher", True, [{**ROWS[0], "condition": "11"}], 2)
    p = player_prompt("mismatcher", True, ROWS, 4)
    assert "informed" not in p.lower() and "condition" not in p.lower()


def test_parser():
    assert parse_choice("STAR") == ("STAR", "ok")
    assert parse_choice("  triangle  ") == ("TRIANGLE", "ok")
    assert parse_choice("The opponent is me, so I mirror.\n\nSTAR") == ("STAR", "ok")
    assert parse_choice("I choose STAR")[0] is None
    assert parse_choice("**STAR**")[0] is None          # handoff: only whitespace and case differences
    assert parse_choice("STAR\nreasoning")[0] is None
    assert parse_choice("STAR", "length")[0] is None


def test_design_and_request():
    gs = Runner.games(Runner.__new__(Runner))
    assert len(gs) == 32 and Counter(g["condition"] for g in gs) == {c: 8 for c in C.COND_ORDER}
    assert C.N_PLAYER_CALLS == 1280
    b = request_body("x")
    assert "temperature" not in b and "seed" not in b and b["provider"] == {"order": ["openai"], "allow_fallbacks": False}


def test_factorial_contrasts():
    ct = A.contrasts({"00": 50.0, "10": 60.0, "01": 40.0, "11": 55.0})
    assert ct["matcher_informed"] == pytest.approx(12.5) and ct["mismatcher_informed"] == pytest.approx(-7.5)
    assert ct["interaction"] == pytest.approx(5.0) and ct["10_vs_11"] == pytest.approx(5.0)


def test_fake_end_to_end_and_malformed(tmp_path):
    r = Runner(tmp_path, live=False)
    gs = r.run_all()
    assert all(g["status"] == "complete" for g in gs)
    calls = [json.loads(l) for l in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert len(calls) == 1280
    by = {}
    for c in calls:
        by.setdefault((c["game_id"], c["round"]), []).append(c["public_history"])
    assert all(len(v) == 2 and v[0] == v[1] for v in by.values())
    res = A.analyze(tmp_path)
    assert res["matcher_win_rate"]["contrasts"]["matcher_informed"] is not None and (tmp_path / "report.md").exists()
    r2 = Runner(tmp_path / "m", live=False)
    r2.transport = FakeTransport(malformed_rate=0.1)
    gs2 = r2.run_all()
    assert any(g["status"] == "incomplete" for g in gs2)
    sids = [json.loads(l)["slot_id"] for l in (tmp_path / "m" / "calls.jsonl").read_text().splitlines()]
    assert len(sids) == len(set(sids))
