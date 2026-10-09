"""Blind Twin RPS offline tests."""
import json
import subprocess
import sys
from collections import Counter

import pytest

from blind_twin_rps import config as C
from blind_twin_rps import score as S
from blind_twin_rps.parse import parse_judge, parse_shape
from blind_twin_rps.render import identity_sentence, judge_prompt, player_prompt, winner
from blind_twin_rps.runner import FakeTransport, Runner, request_body

ROWS = [{"round": 1, "player_a": "ROCK", "player_b": "SCISSORS", "winner": "Player A"},
        {"round": 2, "player_a": "PAPER", "player_b": "PAPER", "winner": "Tie"}]


def test_design_counts_and_seat_balance():
    games = Runner.game_ids(Runner.__new__(Runner))
    assert len(games) == 12
    assert Counter(g["matchup"] for g in games) == {"astra-astra": 3, "astra-fable": 3, "fable-astra": 3, "fable-fable": 3}
    for m in C.ORDER:
        assert sum(g["player_a_model"] == m for g in games) == sum(g["player_b_model"] == m for g in games) == 6
    assert C.N_PLAYER_CALLS == 480 and C.N_JUDGE_CALLS == 1440


def test_rps_payoff():
    assert winner("ROCK", "SCISSORS") == "Player A" and winner("SCISSORS", "PAPER") == "Player A"
    assert winner("PAPER", "ROCK") == "Player A" and winner("ROCK", "PAPER") == "Player B"
    assert winner("SCISSORS", "ROCK") == "Player B" and winner("PAPER", "SCISSORS") == "Player B"
    assert all(winner(m, m) == "Tie" for m in C.SHAPES)


@pytest.mark.parametrize("a,b,fa,fb", [("astra", "astra", "fable", "fable"), ("astra", "fable", "fable", "astra"),
                                       ("fable", "astra", "astra", "fable"), ("fable", "fable", "astra", "astra")])
def test_false_label_swaps_each_seat(a, b, fa, fb):
    assert identity_sentence("FALSE", a, b) == C.IDENTITY_KNOWN.format(player_a=C.MODELS[fa]["display"], player_b=C.MODELS[fb]["display"])
    assert identity_sentence("ANONYMOUS", a, b) == C.IDENTITY_ANONYMOUS


def test_judge_prompts_differ_only_in_identity_line_and_no_leak():
    ps = {c: judge_prompt("astra", c, "astra", "fable", ROWS, 3).splitlines() for c in C.CONDITIONS}
    for a in C.CONDITIONS:
        for b in C.CONDITIONS:
            d = [i for i, (x, y) in enumerate(zip(ps[a], ps[b])) if x != y]
            assert len(ps[a]) == len(ps[b]) and (d == [] if a == b else len(d) == 1 and ps[a][d[0]].startswith("Player identities: "))
    with pytest.raises(AssertionError):
        player_prompt("player_a", ROWS, 2)
    with pytest.raises(AssertionError):
        judge_prompt("astra", "TRUE", "astra", "astra", [{**ROWS[0], "target": "ROCK"}], 2)
    p = judge_prompt("astra", "TRUE", "astra", "fable", ROWS, 3)
    assert "| 2 | PAPER | PAPER | Tie |" in p and "| 1 | ROCK | SCISSORS | Player A wins |" in p


def test_player_prompt_wording_and_no_identities():
    p = player_prompt("player_b", ROWS, 3)
    assert "You are PLAYER B. Your objective is to choose the move that beats Player A's move." in p
    assert p.endswith("Round 3 of 20: choose ROCK, PAPER, or SCISSORS. " + C.PLAYER_FORMAT_LINE)
    for m in C.MODELS.values():
        assert m["display"] not in p


def test_parsers():
    assert parse_shape("ROCK") == ("ROCK", "ok")
    assert parse_shape("They repeated PAPER twice.\n\n**SCISSORS**") == ("SCISSORS", "ok_final_line")
    assert parse_shape("ROCK\nhmm\nPAPER")[1] == "ambiguous_bare_moves"
    assert parse_shape("I play ROCK")[0] is None
    assert parse_shape("Move: ROCK")[0] is None
    assert parse_judge('{"player_a":"rock","player_b":"PAPER"}')[0] == {"player_a": "ROCK", "player_b": "PAPER"}
    assert parse_judge('{"player_a":"ROCK","player_b":"LIZARD"}')[0] is None
    assert parse_judge('{"matcher":"ROCK","mismatcher":"PAPER"}')[0] is None


def test_request_omits_unsupported_controls():
    for m in C.ORDER:
        b = request_body(m, "x")
        assert "temperature" not in b and "seed" not in b


def test_baselines_and_fractional_credit():
    bp = S.baseline_predictions([], "player_a")
    assert all(v is None for v in bp.values()) and S._score(None, "ROCK") == pytest.approx(1 / 3)
    bp = S.baseline_predictions(ROWS, "player_a")
    assert bp["repeat_last"] == "PAPER" and bp["cycle_up"] == "SCISSORS" and bp["cycle_down"] == "ROCK"
    assert bp["counter_opponent_last"] == "SCISSORS"            # beats Player B's PAPER
    assert bp["win_stay_lose_shift"] == "SCISSORS"              # tie -> shift to counter opponent's last
    assert S._score(("ROCK", "PAPER"), "ROCK") == 0.5 and S._score(("ROCK", "PAPER"), "SCISSORS") == 0.0


def test_seeds_reproducible():
    code = "from blind_twin_rps import config as C; print(C.derive_seed('judge_schedule'))"
    a = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True).stdout
    assert a == subprocess.run([sys.executable, "-c", code], capture_output=True, text=True).stdout and a.strip()


def test_fake_end_to_end(tmp_path):
    r = Runner(tmp_path, live=False)
    r.transport = FakeTransport()
    (tmp_path / "config.json").write_text(json.dumps(C.frozen_config()))
    games = r.run_games()
    r.freeze(games)
    r.run_judges()
    calls = [json.loads(l) for l in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert sum(c["kind"] == "player" for c in calls) == 480 and sum(c["kind"] == "judge" for c in calls) == 1440
    by = {}
    for c in calls:
        if c["kind"] == "player":
            by.setdefault((c["game_id"], c["round"]), []).append(c["public_history"])
    assert all(len(v) == 2 and v[0] == v[1] for v in by.values())
    out = S.analyze(tmp_path)
    assert out["indices"]["S"] is not None and (tmp_path / "report.md").exists()
