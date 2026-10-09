"""Section 7 tests for the three-model RPS opponent-disclosure pilot (no network)."""
import json
from collections import Counter

import pytest

from opponent_disclosure_rps_3models import analysis as A
from opponent_disclosure_rps_3models import config as C
from opponent_disclosure_rps_3models.game import (FakeTransport, Runner, approved, history_text, parse_move,
                                                  payoff_p1, player_prompt, request_body, result, schedule, schedule_hash)

ROWS = [{"round": 1, "p1": "ROCK", "p2": "PAPER", "result": "Player 2"},
        {"round": 2, "p1": "SCISSORS", "p2": "SCISSORS", "result": "Tie"}]


def test_design_counts():
    s = schedule()
    pairs = Counter((g["p1_model"], g["p2_model"]) for g in s)
    assert len(pairs) == 9 and all(v == 32 for v in pairs.values())
    assert sum(1 for a, b in pairs if a == b) == 3
    cells = Counter((g["p1_model"], g["p2_model"], g["condition"]) for g in s)
    assert len(cells) == 36 and set(cells.values()) == {8}
    assert len(s) == C.N_GAMES == 288 and C.N_GAMES * C.N_ROUNDS == 5760 and C.N_CALLS == 11520
    assert len({g["game_id"] for g in s}) == 288
    assert schedule_hash(s) == schedule_hash(schedule())                 # deterministic
    first_wave = s[:36]
    assert len({(g["p1_model"], g["p2_model"], g["condition"]) for g in first_wave}) == 36   # interleaved


def test_only_identity_sentence_differs_and_own_identity_constant():
    for own, opp in [("astra", "astra"), ("fable", "qwen"), ("qwen", "astra")]:
        for seat in ("Player 1", "Player 2"):
            i = player_prompt(seat, own, opp, True, ROWS, 3).splitlines()
            u = player_prompt(seat, own, opp, False, ROWS, 3).splitlines()
            d = [k for k, (x, y) in enumerate(zip(i, u)) if x != y]
            assert len(i) == len(u) and len(d) == 1
            assert i[d[0]] == f"Opponent identity: Your opponent is an independent instance of {C.MODELS[opp]['name']}."
            assert u[d[0]] == "Opponent identity: Your opponent's model identity is not disclosed."
            assert f"Your model identity is {C.MODELS[own]['name']}." in i and f"Your model identity is {C.MODELS[own]['name']}." in u
            assert f"You are {seat}." in i
    p = player_prompt("Player 1", "astra", "astra", True, ROWS, 3)
    for w in ("copy of yourself", "twin", "different from you"):
        assert w not in p


def test_history_public_only_and_no_leak():
    assert history_text([]) == "None. This is the first round."
    assert history_text(ROWS) == "Round | Player 1 | Player 2 | Result\n1 | ROCK | PAPER | Player 2\n2 | SCISSORS | SCISSORS | Tie"
    with pytest.raises(AssertionError):
        player_prompt("Player 1", "astra", "fable", True, ROWS, 2)
    with pytest.raises(AssertionError):
        player_prompt("Player 1", "astra", "fable", True, [{**ROWS[0], "informed": True}], 2)
    u = player_prompt("Player 2", "fable", "qwen", False, ROWS, 3)
    assert "Qwen" not in u and "informed" not in u.lower()


def test_rps_payoffs_sum_to_one():
    for a in C.MOVES:
        for b in C.MOVES:
            r = result(a, b)
            assert payoff_p1(r) + (1 - payoff_p1(r)) == 1
            assert (r == "Tie") == (a == b)
    assert result("ROCK", "SCISSORS") == "Player 1" and result("ROCK", "PAPER") == "Player 2"


def test_parser():
    assert parse_move("ROCK") == ("ROCK", "ok")
    assert parse_move("Thinking...\n\n  paper  ") == ("PAPER", "ok")
    assert parse_move("I pick ROCK")[0] is None
    assert parse_move("**ROCK**")[0] is None
    assert parse_move("ROCK\nexplanation")[0] is None
    assert parse_move("ROCK", "length")[0] is None


def test_request_payload():
    for m in C.ORDER:
        b = request_body(m, "x")
        assert "temperature" not in b and "seed" not in b and "top_p" not in b
        assert b["provider"] == {"order": [C.MODELS[m]["provider"]], "allow_fallbacks": False}
        assert len(b["messages"]) == 1                                    # no persistence across calls
    assert C.MODELS["qwen"] == {"slug": "qwen/qwen3.8-27b", "name": "Qwen3.8 27B", "provider": "alibaba"}


def _V(base=0.5, same_gain=0.0, other_gain=0.0):
    """Synthetic cell means: unilateral disclosure raises the informed player's payoff by gain."""
    V = {}
    for i, j in C.PAIRINGS:
        g = same_gain if i == j else other_gain
        V[(i, j, "00")] = base
        V[(i, j, "10")] = base + g          # P1 informed -> P1 gains
        V[(i, j, "01")] = base - g          # P2 informed -> P2 gains
        V[(i, j, "11")] = base
    return V


def test_primary_contrast_signs():
    assert A.contrasts(_V(same_gain=0.1, other_gain=0.1))["D"] == pytest.approx(0.0)        # common gain
    assert A.contrasts(_V(same_gain=0.1, other_gain=0.0))["D"] == pytest.approx(0.1)        # same-model only
    assert A.contrasts(_V(same_gain=0.0, other_gain=0.1))["D"] == pytest.approx(-0.1)       # other-model only
    assert A.contrasts(_V())["D"] == pytest.approx(0.0)                                     # no payoff change
    ct = A.contrasts(_V(same_gain=0.1))
    assert ct["U1[astra,astra]"] == pytest.approx(0.1) and ct["U2[astra,astra]"] == pytest.approx(0.1)
    assert ct["S[fable]"] == pytest.approx(0.1) and ct["O[fable]"] == pytest.approx(0.0)


def test_missing_cell_makes_panel_not_estimable():
    V = _V(same_gain=0.1)
    V[("qwen", "astra", "01")] = None
    ct = A.contrasts(V)
    assert ct["D"] is None and ct["D[astra]"] is None and ct["D[fable]"] is not None


def test_fake_full_run_resume_rescore_and_incomplete(tmp_path):
    rd = tmp_path / "run"
    r = Runner(rd, live=False)
    games = r.run(schedule())
    assert len(games) == 288 and all(g["status"] == "complete" for g in games)
    calls = [json.loads(l) for l in (rd / "calls.jsonl").read_text().splitlines()]
    assert len(calls) == 11520
    by = {}
    for c in calls:
        by.setdefault((c["game_id"], c["round"]), []).append(c["public_history"])
    assert all(len(v) == 2 and v[0] == v[1] for v in by.values())
    Runner(rd, live=False).run(schedule())                                # resume: no duplicate calls
    assert len((rd / "calls.jsonl").read_text().splitlines()) == 11520
    res = A.analyze(rd)
    assert res["rescore"]["round_result_mismatches"] == 0
    assert res["contrasts"]["D"] == pytest.approx(res["rescore"]["D_rescore"], abs=1e-12)
    rd2 = tmp_path / "bad"
    r2 = Runner(rd2, live=False, transport=FakeTransport(malformed_rate=0.05))
    g2 = r2.run(schedule()[:36])
    inter = [g for g in g2 if g["status"] == "interrupted"]
    assert inter
    V = A.cell_means(g2)                                                   # interrupted games excluded from V
    for g in inter:
        assert all(x["game_id"] != g["game_id"] or x["status"] == "complete" for x in g2 if x["status"] == "complete")


def test_budget_and_approval_gates(tmp_path):
    rd = tmp_path / "gate"
    with pytest.raises(SystemExit):
        Runner(rd, live=True)                                              # no APPROVAL.md -> no network
    (rd / "APPROVAL.md").write_text("LIVE RUN APPROVED BY CHRIS: no\n")
    assert not approved(rd)
    (rd / "APPROVAL.md").write_text("LIVE RUN APPROVED BY CHRIS: yes\n")
    assert approved(rd)
    r = Runner(tmp_path / "cap", live=False)
    r.acct.cap = 0.05                                                      # fake reservation ~$0.24 per call
    g = r.play(schedule()[0])
    assert g["status"] == "interrupted" and r.stop.is_set() and r.acct.spent <= 0.05
