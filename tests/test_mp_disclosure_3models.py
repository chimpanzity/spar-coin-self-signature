"""Tests for the three-model matching-pennies opponent-disclosure pilot (no network). P1 = Matcher, P2 = Mismatcher."""
import json
from collections import Counter

import pytest

from opponent_disclosure_mp_3models import analysis as A
from opponent_disclosure_mp_3models import config as C
from opponent_disclosure_mp_3models.game import (FakeTransport, Runner, approved, history_text, parse_move,
                                                 payoff_p1, player_prompt, request_body, result, schedule, schedule_hash)

ROWS = [{"round": 1, "p1": "STAR", "p2": "TRIANGLE", "result": "Mismatcher"},
        {"round": 2, "p1": "TRIANGLE", "p2": "TRIANGLE", "result": "Matcher"}]

PROMPT_P1_ASTRA_VS_FABLE_INFORMED_R3 = """This is a 20-round simultaneous-choice matching-pennies game between Player 1 (the Matcher) and Player 2 (the Mismatcher). On each round, both players independently choose STAR or TRIANGLE without seeing the other's current choice. The Matcher wins if the two choices are the same. The Mismatcher wins if they differ. After each completed round, both choices and the winner are revealed. Your objective is to win as many rounds as possible.

You are Player 1, the MATCHER.
Your model identity is GPT-6 Astra.

Opponent identity: Your opponent is an independent instance of Claude Fable 5.1.

Completed-round history:
Round | Matcher (Player 1) | Mismatcher (Player 2) | Winner
1 | STAR | TRIANGLE | Mismatcher
2 | TRIANGLE | TRIANGLE | Matcher

Round 3 of 20: choose STAR or TRIANGLE.

Return your final choice on the last nonempty line, using exactly STAR or TRIANGLE."""


def test_exact_prompt_text():
    assert player_prompt("Player 1", "astra", "fable", True, ROWS, 3) == PROMPT_P1_ASTRA_VS_FABLE_INFORMED_R3
    p2 = player_prompt("Player 2", "qwen", "qwen", False, [], 1)
    assert "You are Player 2, the MISMATCHER.\nYour model identity is Qwen3.8 27B." in p2
    assert "Opponent identity: Your opponent's model identity is not disclosed." in p2
    assert "Completed-round history:\nNone. This is the first round.\n\nRound 1 of 20" in p2


def test_design_counts():
    s = schedule()
    pairs = Counter((g["p1_model"], g["p2_model"]) for g in s)
    assert len(pairs) == 9 and all(v == 4 * C.REPLICATES for v in pairs.values())
    assert sum(1 for a, b in pairs if a == b) == 3
    cells = Counter((g["p1_model"], g["p2_model"], g["condition"]) for g in s)
    assert len(cells) == 36 and set(cells.values()) == {2}
    assert len(s) == C.N_GAMES == 72 and C.N_GAMES * C.N_ROUNDS == 1440 and C.N_CALLS == 2880
    assert len({g["game_id"] for g in s}) == 72
    assert schedule_hash(s) == schedule_hash(schedule())
    assert len({(g["p1_model"], g["p2_model"], g["condition"]) for g in s[:36]}) == 36          # interleaved waves
    for g in s:                                                                                  # truthful assignment
        assert (g["p1_informed"], g["p2_informed"]) == C.CONDITIONS[g["condition"]]


def test_only_identity_sentence_differs_and_roles_fixed():
    for own, opp in C.PAIRINGS:
        for seat, role in (("Player 1", "MATCHER"), ("Player 2", "MISMATCHER")):
            i = player_prompt(seat, own, opp, True, ROWS, 3).splitlines()
            u = player_prompt(seat, own, opp, False, ROWS, 3).splitlines()
            d = [k for k, (x, y) in enumerate(zip(i, u)) if x != y]
            assert len(i) == len(u) and len(d) == 1
            assert i[d[0]] == f"Opponent identity: Your opponent is an independent instance of {C.MODELS[opp]['name']}."
            assert u[d[0]] == "Opponent identity: Your opponent's model identity is not disclosed."
            assert f"You are {seat}, the {role}." in i and f"Your model identity is {C.MODELS[own]['name']}." in u
    a = player_prompt("Player 1", "fable", "fable", True, ROWS, 3).splitlines()
    b = player_prompt("Player 2", "fable", "fable", True, ROWS, 3).splitlines()
    assert [k for k, (x, y) in enumerate(zip(a, b)) if x != y] == [2]                           # only the seat/role line
    for w in ("twin", "another you", "same as you", "copy of yourself"):
        assert w not in " ".join(a).lower()


def test_history_public_only_and_no_leak():
    assert history_text([]) == "None. This is the first round."
    assert history_text(ROWS) == ("Round | Matcher (Player 1) | Mismatcher (Player 2) | Winner\n"
                                  "1 | STAR | TRIANGLE | Mismatcher\n2 | TRIANGLE | TRIANGLE | Matcher")
    with pytest.raises(AssertionError):
        player_prompt("Player 1", "astra", "fable", True, ROWS, 2)                               # future/current row
    with pytest.raises(AssertionError):
        player_prompt("Player 1", "astra", "fable", True, [{**ROWS[0], "informed": True}], 2)
    u = player_prompt("Player 2", "fable", "qwen", False, ROWS, 3)
    assert "Qwen" not in u and "informed" not in u.lower()


def test_mp_payoffs_no_ties_sum_to_one():
    for a in C.MOVES:
        for b in C.MOVES:
            r = result(a, b)
            assert r in ("Matcher", "Mismatcher") and (r == "Matcher") == (a == b)
            assert payoff_p1(r) in (0.0, 1.0)


def test_parser():
    assert parse_move("STAR") == ("STAR", "ok")
    assert parse_move("Looking at the history, they alternate.\n\n  triangle  ") == ("TRIANGLE", "ok")
    assert parse_move("I choose STAR")[0] is None
    assert parse_move("**STAR**")[0] is None
    assert parse_move("STAR\nbecause...")[0] is None
    assert parse_move("ROCK")[0] is None
    assert parse_move("STAR", "length")[0] is None
    assert parse_move("")[0] is None


def test_request_payload():
    for m in C.ORDER:
        b = request_body(m, "x")
        assert "temperature" not in b and "seed" not in b and "top_p" not in b
        assert b["provider"] == {"order": [C.MODELS[m]["provider"]], "allow_fallbacks": False}
        assert len(b["messages"]) == 1
    from opponent_disclosure_rps_3models import config as R
    assert C.MODELS == R.MODELS and C.REASONING == R.REASONING and C.MAX_TOKENS == R.MAX_TOKENS   # same panel as RPS


def _V(base=0.5, same_gain=0.0, other_gain=0.0):
    V = {}
    for i, j in C.PAIRINGS:
        g = same_gain if i == j else other_gain
        V[(i, j, "00")], V[(i, j, "10")], V[(i, j, "01")], V[(i, j, "11")] = base, base + g, base - g, base
    return V


def test_primary_contrast_signs_and_role_weights():
    assert A.contrasts(_V(same_gain=0.1, other_gain=0.1))["D"] == pytest.approx(0.0)
    assert A.contrasts(_V(same_gain=0.1))["D"] == pytest.approx(0.1)
    assert A.contrasts(_V(other_gain=0.1))["D"] == pytest.approx(-0.1)
    # Matcher-only benefit (U1 > 0, U2 = 0) on the diagonal: S counts each role with weight 1/2
    V = _V()
    for m in C.ORDER:
        V[(m, m, "10")] = 0.7
    ct = A.contrasts(V)
    assert ct["U1[astra,astra]"] == pytest.approx(0.2) and ct["U2[astra,astra]"] == pytest.approx(0.0)
    assert ct["S[astra]"] == pytest.approx(0.1) and ct["D"] == pytest.approx(0.1)
    # Mismatcher-only benefit against other models: O[i] = (U1 ij + U2 ji + U1 ik + U2 ki)/4
    V = _V()
    for i, j in C.PAIRINGS:
        if i != j:
            V[(i, j, "01")] = 0.3                                          # P2 informed -> Mismatcher +0.2
    ct = A.contrasts(V)
    assert ct["O[fable]"] == pytest.approx(0.1) and ct["D"] == pytest.approx(-0.1)


def test_missing_cell_makes_panel_not_estimable():
    V = _V(same_gain=0.1)
    V[("qwen", "astra", "01")] = None
    ct = A.contrasts(V)
    assert ct["D"] is None and ct["D[astra]"] is None and ct["D[fable]"] is not None


def test_baselines_role_aware():
    g = {"rounds": [{"round": 1, "p1": "STAR", "p2": "TRIANGLE", "result": "Mismatcher"},
                    {"round": 2, "p1": "TRIANGLE", "p2": "STAR", "result": "Mismatcher"}]}
    m = A.baseline_scores(g, "p1")       # Matcher copies opponent's last (TRIANGLE) in round 2 -> predicted
    assert m["best_response_opponent_last"] == pytest.approx(100 * (0.5 + 1) / 2)
    mm = A.baseline_scores(g, "p2")      # Mismatcher best response to STAR... opp last was STAR -> TRIANGLE; chose STAR
    assert mm["best_response_opponent_last"] == pytest.approx(100 * (0.5 + 0) / 2)
    assert m["win_stay_lose_shift"] == pytest.approx(75.0)                    # Matcher lost r1, shifted -> predicted
    assert mm["win_stay_lose_shift"] == pytest.approx(0.0 + 25.0)             # Mismatcher won r1 but shifted


def test_fake_full_run_resume_rescore_and_incomplete(tmp_path):
    rd = tmp_path / "run"
    games = Runner(rd, live=False).run(schedule())
    assert len(games) == 72 and all(g["status"] == "complete" for g in games)
    calls = [json.loads(l) for l in (rd / "calls.jsonl").read_text().splitlines()]
    assert len(calls) == 2880
    by = {}
    for c in calls:
        by.setdefault((c["game_id"], c["round"]), []).append(c)
        assert ("an independent instance of " + C.MODELS[c["private"]["true_opponent"]]["name"] in c["request"]["messages"][0]["content"]) == c["private"]["informed"]
    assert all(len(v) == 2 and v[0]["public_history"] == v[1]["public_history"] and len(v[0]["public_history"]) == v[0]["round"] - 1
               for v in by.values())
    Runner(rd, live=False).run(schedule())                                # resume: no duplicate calls
    assert len((rd / "calls.jsonl").read_text().splitlines()) == 2880
    res = A.analyze(rd)
    assert res["rescore"]["round_result_mismatches"] == 0
    assert res["contrasts"]["D"] == pytest.approx(res["rescore"]["D_rescore"], abs=1e-12)
    for f in ("games.csv", "rounds.csv", "invalids.csv", "cell_means.csv", "primary_contrasts.csv", "behavioral_metrics.csv",
              "baseline_predictions.csv", "bootstrap_intervals.csv", "conditional_choice.csv", "REPORT.md", "checksums.sha256"):
        assert (rd / f).exists()
    rd2 = tmp_path / "bad"
    g2 = Runner(rd2, live=False, transport=FakeTransport(malformed_rate=0.05)).run(schedule()[:36])
    inter = [g for g in g2 if g["status"] == "interrupted"]
    assert inter and all(g["n_valid_rounds"] < 20 and "invalid response" in g["note"] for g in inter)
    V = A.cell_means(g2)
    assert all(v is None or 0 <= v <= 1 for v in V.values())


def test_interrupted_run_resumes_without_reissuing(tmp_path):
    rd = tmp_path / "res"

    class StopAfter(FakeTransport):                                        # simulate an interruption mid-run
        def send(self, body):
            out = super().send(body)
            if self.n >= 1000:
                r.stop.set()
            return out
    r = Runner(rd, live=False, transport=StopAfter())
    first = r.run(schedule())
    assert any(g["status"] == "interrupted" for g in first)
    n1 = len((rd / "calls.jsonl").read_text().splitlines())
    assert 0 < n1 < 2880 and r.stop.is_set()
    games = Runner(rd, live=False).run(schedule())
    calls = [json.loads(l) for l in (rd / "calls.jsonl").read_text().splitlines()]
    assert all(g["status"] == "complete" for g in games) and len({c["slot_id"] for c in calls}) == 2880 == len(calls)


def test_budget_and_approval_gates(tmp_path):
    rd = tmp_path / "gate"
    with pytest.raises(SystemExit):
        Runner(rd, live=True)
    (rd / "APPROVAL.md").write_text("LIVE RUN APPROVED BY CHRIS: no\n")
    assert not approved(rd)
    (rd / "APPROVAL.md").write_text("LIVE RUN APPROVED BY CHRIS: yes\n")
    assert approved(rd)
    r = Runner(tmp_path / "cap", live=False)
    r.acct.cap = 0.05
    g = r.play(schedule()[0])
    assert g["status"] == "interrupted" and r.stop.is_set() and r.acct.spent <= 0.05


def test_live_prices_from_plan_snapshot():
    import pathlib
    from opponent_disclosure_mp_3models.game import snapshot_prices
    run = sorted(pathlib.Path(C.RESULTS).glob("*p2-20261010/endpoint_and_price_snapshots.json"))[0]
    pr = snapshot_prices(json.loads(run.read_text()))
    assert set(pr) == {m["slug"] for m in C.MODELS.values()}
    assert pr["openai/gpt-6-astra"] == {"prompt": 1e-05, "completion": 5e-05}          # pinned "openai", not flex/fast
    assert pr["qwen/qwen3.8-27b"]["completion"] == 2.55e-06
