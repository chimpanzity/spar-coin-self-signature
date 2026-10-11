"""Tests for the Blind Twin self-self 00-vs-11 pilot (no network)."""
from collections import Counter

import pytest

from blind_twin_selfself import config as C
from blind_twin_selfself import score as S
from blind_twin_selfself.judge import FakeTransport, Runner, judge_prompt, load_games, schedule


@pytest.fixture(scope="module")
def games():
    return load_games()


def test_games(games):
    assert len(games) == 24 == len({g["gid"] for g in games})
    c = Counter((g["game_type"], g["p1_model"], g["condition"]) for g in games)
    assert len(c) == 12 and set(c.values()) == {2}
    assert all(g["p1_model"] == g["p2_model"] and g["status"] == "complete" for g in games)
    assert len(schedule(games)) == 4320 and schedule(games) == schedule(games)


def test_info_sentence_is_name_free_and_matches_condition(games):
    for g in games:
        for lab in C.CONDITIONS:
            p = judge_prompt("astra", g, 3, lab)
            info = [l for l in p.splitlines() if l.startswith("Player information:")]
            assert len(info) == 1 and info[0] == "Player information: " + C.INFO[g["condition"]]
            for m in C.MODELS.values():
                assert m["name"] not in info[0]
        a = judge_prompt("fable", g, 3, "ANONYMOUS")
        assert all(m["name"] not in a.split("observer.")[1] for m in C.MODELS.values())
    g = next(x for x in games if x["condition"] == "11" and x["p1_model"] == "fable")
    assert "Player 1 is Qwen3.8 27B; Player 2 is Qwen3.8 27B." in judge_prompt("astra", g, 3, "FALSE")


def _acc(self11=0.0, other11=0.0):
    acc = {}
    for gt in C.GAME_TYPES:
        for cond in C.SOURCE_CONDITIONS:
            for j in C.JUDGES:
                for m in C.ORDER:
                    gain = (self11 if j == m else other11) if cond == "11" else 0.0
                    acc[(gt, cond, j, m, "ANONYMOUS")] = 40.0
                    acc[(gt, cond, j, m, "FALSE")] = 40.0
                    acc[(gt, cond, j, m, "TRUE")] = 40.0 + gain
    return acc


def test_delta_signs():
    ix = S.indices(_acc(self11=10))
    assert ix["rps:Delta_self"] == pytest.approx(10) and ix["rps:Delta_other"] == pytest.approx(0)
    assert ix["mp:Delta_selfspec"] == pytest.approx(10) and ix["pooled:Delta_selfspec"] == pytest.approx(10)
    ix = S.indices(_acc(self11=6, other11=6))
    assert ix["rps:Delta_selfspec"] == pytest.approx(0) and ix["rps:Delta_other"] == pytest.approx(6)
    ix = S.indices(_acc(other11=4))
    assert ix["mp:Delta_selfspec"] == pytest.approx(-4)
    assert ix["rps:11:S"] == pytest.approx(-4) and ix["rps:00:S"] == pytest.approx(0)
    a = _acc(); a[("rps", "11", "qwen", "qwen", "TRUE")] = None
    assert S.indices(a)["rps:Delta_selfspec"] is None and S.indices(a)["mp:Delta_selfspec"] is not None


def test_fake_run_and_analysis(tmp_path, games):
    rd = tmp_path / "run"
    Runner(rd, live=False, transport=FakeTransport(malformed_rate=0.02)).run(schedule(games), games)
    Runner(rd, live=False).run(schedule(games), games)
    assert len((rd / "calls.jsonl").read_text().splitlines()) == 4320
    out = S.analyze(rd)
    assert out["indices"]["rps:Delta_selfspec"] is not None
    for f in ("REPORT.md", "accuracy.csv", "indices.csv", "baseline_scores.csv", "checksums.sha256"):
        assert (rd / f).exists()
