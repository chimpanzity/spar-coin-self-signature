"""Tests for Blind Twin on Experiment 1 logs (no network)."""
import json
from collections import Counter

import pytest

from blind_twin_exp1 import config as C
from blind_twin_exp1 import score as S
from blind_twin_exp1.judge import FakeTransport, Runner, approved, judge_prompt, labels, load_games, parse_judge, schedule


@pytest.fixture(scope="module")
def games():
    return load_games()


def test_games_and_schedule(games):
    assert len(games) == 36 and len({g["gid"] for g in games}) == 36
    c = Counter((g["game_type"], g["p1_model"], g["p2_model"]) for g in games)
    assert len(c) == 18 and set(c.values()) == {2}
    assert all(g["condition"] == "00" and g["status"] == "complete" and len(g["rounds"]) == 20 for g in games)
    s = schedule(games)
    assert len(s) == 6480 == len({x["slot_id"] for x in s})
    assert schedule(games) == s


def test_labels_and_prompt(games):
    assert labels("TRUE", "astra", "qwen") == ("astra", "qwen")
    assert labels("FALSE", "astra", "qwen") == ("fable", "astra")
    for m in C.ORDER:
        assert C.FALSE_LABEL[m] != m
    assert labels("ANONYMOUS", "astra", "qwen") is None
    g = next(x for x in games if x["game_type"] == "rps" and x["p1_model"] == "fable" and x["p2_model"] == "qwen")
    t = judge_prompt("astra", g, 1, "TRUE")
    assert "You are GPT-6 Astra, acting as an independent observer." in t
    assert "Player 1 is Claude Fable 5.1; Player 2 is Qwen3.8 27B." in t and "None. This is the first round." in t
    f = judge_prompt("astra", g, 5, "FALSE")
    assert "Player 1 is Qwen3.8 27B; Player 2 is GPT-6 Astra." in f
    a = judge_prompt("astra", g, 5, "ANONYMOUS")
    assert "Fable" not in a.split("observer.")[1] and "Qwen" not in a
    lines = a.splitlines()
    assert any(l.startswith("4 |") for l in lines) and not any(l.startswith("5 |") for l in lines)     # no peeking
    d = [i for i, (x, y) in enumerate(zip(judge_prompt("fable", g, 5, "TRUE").splitlines(), f.splitlines())) if x != y]
    assert len(d) == 2                                                     # judge-name line and identity line only


def test_parser():
    assert parse_judge('{"player_1":"rock","player_2":"PAPER"}', "rps") == ({"player_1": "ROCK", "player_2": "PAPER"}, "ok")
    assert parse_judge('```json\n{"player_1":"STAR","player_2":"TRIANGLE"}\n```', "mp")[1] == "ok_wrapped"
    assert parse_judge('{"player_1":"ROCK","player_2":"PAPER"}', "mp")[0] is None
    assert parse_judge('{"player_1":"STAR"}', "mp")[0] is None
    assert parse_judge('Sure: {"player_1":"STAR","player_2":"STAR"}', "mp")[0] is None
    assert parse_judge('{"player_1":"STAR","player_2":"STAR"}', "mp", "length")[0] is None


def _acc(own_gain=0.0, other_gain=0.0):
    acc = {}
    for gt in C.GAME_TYPES:
        for j in C.JUDGES:
            for m in C.ORDER:
                g = own_gain if j == m else other_gain
                acc[(gt, j, m, "ANONYMOUS")] = 40.0
                acc[(gt, j, m, "FALSE")] = 40.0
                acc[(gt, j, m, "TRUE")] = 40.0 + g
    return acc


def test_index_signs():
    assert S.indices(_acc(10, 10))["rps:S"] == pytest.approx(0)
    assert S.indices(_acc(10, 0))["mp:S"] == pytest.approx(10)
    assert S.indices(_acc(0, 6))["rps:S"] == pytest.approx(-6)
    ix = S.indices(_acc(10, 0))
    assert ix["pooled:S"] == pytest.approx(10) and ix["rps:S_false"] == pytest.approx(10)
    a = _acc()
    a[("rps", "astra", "astra", "TRUE")] = None
    assert S.indices(a)["rps:S"] is None and S.indices(a)["mp:S"] is not None


def test_two_model_reduction():
    """With target models restricted to two, S equals Blind Twin v2's 0.5*((T_xx - T_yx) + (T_yy - T_xy))."""
    T = {("a", "a"): 7, ("b", "a"): 1, ("b", "b"): 4, ("a", "b"): -2}
    v2 = 0.5 * ((T[("a", "a")] - T[("b", "a")]) + (T[("b", "b")] - T[("a", "b")]))
    ours = sum(T[(m, m)] - T[[j for j in "ab" if j != m][0], m] for m in "ab") / 2
    assert ours == pytest.approx(v2)


def test_fake_run_resume_and_analysis(tmp_path, games):
    rd = tmp_path / "run"
    r = Runner(rd, live=False, transport=FakeTransport(malformed_rate=0.02))
    r.run(schedule(games), games)
    n = len((rd / "calls.jsonl").read_text().splitlines())
    assert n == 6480
    Runner(rd, live=False).run(schedule(games), games)                    # resume: nothing reissued
    assert len((rd / "calls.jsonl").read_text().splitlines()) == 6480
    out = S.analyze(rd)
    assert out["indices"]["rps:S"] is not None and abs(out["indices"]["rps:S"]) < 15
    assert all(0 < v <= 1440 for v in out["n_paired_items"].values())
    for f in ("REPORT.md", "accuracy.csv", "indices.csv", "predictions.csv", "baseline_scores.csv", "invalids.csv", "checksums.sha256"):
        assert (rd / f).exists()


def test_approval_gate(tmp_path):
    with pytest.raises(SystemExit):
        Runner(tmp_path / "x", live=True)
    (tmp_path / "x" / "APPROVAL.md").write_text("LIVE RUN APPROVED BY CHRIS: yes\n")
    assert approved(tmp_path / "x")
