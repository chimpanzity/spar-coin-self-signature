"""Blind Twin offline tests (handoff step 2)."""
import json
import subprocess
import sys
from collections import Counter

import pytest

from blind_twin import config as C
from blind_twin import score as S
from blind_twin.parse import parse_judge, parse_shape
from blind_twin.render import history_table, identity_sentence, judge_prompt, player_prompt, winner
from blind_twin.runner import FakeTransport, Runner

ROWS = [{"round": 1, "matcher": "STAR", "mismatcher": "TRIANGLE", "winner": "Mismatcher"},
        {"round": 2, "matcher": "STAR", "mismatcher": "STAR", "winner": "Matcher"}]


def test_four_matchups_three_games_each_role_balanced():
    r = Runner.__new__(Runner)
    games = Runner.game_ids(r)
    assert len(games) == 12
    assert Counter(g["matchup"] for g in games) == {"astra-astra": 3, "astra-fable": 3, "fable-astra": 3, "fable-fable": 3}
    for m in C.ORDER:
        assert sum(g["matcher_model"] == m for g in games) == sum(g["mismatcher_model"] == m for g in games) == 6
    assert C.N_PLAYER_CALLS == 480 and C.N_JUDGE_CALLS == 1440


@pytest.mark.parametrize("mm,ms,fm,fs", [("astra", "astra", "fable", "fable"), ("astra", "fable", "fable", "astra"),
                                         ("fable", "astra", "astra", "fable"), ("fable", "fable", "astra", "astra")])
def test_false_label_swaps_each_seat(mm, ms, fm, fs):
    assert identity_sentence("FALSE", mm, ms) == C.IDENTITY_KNOWN.format(matcher=C.MODELS[fm]["display"], mismatcher=C.MODELS[fs]["display"])
    assert identity_sentence("TRUE", mm, ms) == C.IDENTITY_KNOWN.format(matcher=C.MODELS[mm]["display"], mismatcher=C.MODELS[ms]["display"])
    assert identity_sentence("ANONYMOUS", mm, ms) == C.IDENTITY_ANONYMOUS


def test_judge_prompts_differ_only_in_identity_line():
    ps = {c: judge_prompt("fable", c, "astra", "fable", ROWS, 3).splitlines() for c in C.CONDITIONS}
    for a in C.CONDITIONS:
        for b in C.CONDITIONS:
            diff = [i for i, (x, y) in enumerate(zip(ps[a], ps[b])) if x != y]
            assert len(ps[a]) == len(ps[b]) and (diff == [] if a == b else len(diff) == 1)
            if diff:
                assert ps[a][diff[0]].startswith("Player identities: ")
    assert ps["TRUE"][1].startswith("You are Claude Fable 5.1, acting as an independent observer.")


def test_no_future_leakage_and_public_rows_only():
    with pytest.raises(AssertionError):
        player_prompt("matcher", ROWS, 2)            # history longer than t-1
    with pytest.raises(AssertionError):
        judge_prompt("astra", "TRUE", "astra", "astra", [{**ROWS[0], "target": "STAR"}], 2)
    p = judge_prompt("astra", "TRUE", "astra", "fable", ROWS[:1], 2)
    assert "| 1 | STAR | TRIANGLE | Mismatcher |" in p and "| 2 |" not in p
    assert C.EMPTY_HISTORY in player_prompt("mismatcher", [], 1)


def test_players_not_told_identities_and_prompts_verbatim():
    p = player_prompt("matcher", ROWS, 3)
    for m in C.MODELS.values():
        assert m["display"] not in p
    assert p.startswith(C.SHARED_GAME_EXPLANATION + "\nYou are the MATCHER.")
    assert p.endswith("Round 3 of 20: choose STAR or TRIANGLE. " + C.PLAYER_FORMAT_LINE)
    assert "You are the MISMATCHER. Your objective is to choose a DIFFERENT shape" in player_prompt("mismatcher", ROWS, 3)


def test_payoff():
    assert winner("STAR", "STAR") == "Matcher" and winner("TRIANGLE", "TRIANGLE") == "Matcher"
    assert winner("STAR", "TRIANGLE") == "Mismatcher" and winner("TRIANGLE", "STAR") == "Mismatcher"


def test_v2_prompt_wording():
    assert C.VERSION == "v2"
    p = player_prompt("matcher", [], 1)
    assert p.endswith("You may briefly think through your choice. End your response with the chosen shape "
                      "(STAR or TRIANGLE) alone on the final line.")
    assert "Return ONLY" not in p


def test_parsers():
    assert parse_shape("STAR") == ("STAR", "ok")
    assert parse_shape("**Triangle**")[0] == "TRIANGLE"
    assert parse_shape("STAR.")[0] == "STAR"
    assert parse_shape("I choose STAR")[0] is None                       # final line is not a bare shape
    assert parse_shape("STAR or TRIANGLE")[0] is None
    assert parse_shape("STAR", "length")[0] is None
    # v2 final-line rule
    assert parse_shape("Mismatcher alternated — pattern suggests STAR next.\n\nSTAR") == ("STAR", "ok_final_line")
    assert parse_shape("Thinking.\n**TRIANGLE**")[0] == "TRIANGLE"
    assert parse_shape("STAR\nActually no.\nTRIANGLE")[1] == "ambiguous_bare_shapes"
    assert parse_shape("STAR\nreasoning\nSTAR")[0] == "STAR"
    assert parse_shape("I pick TRIANGLE.\nChoice: TRIANGLE")[0] is None   # labelled final line is not bare
    assert parse_shape("Reasoning only, no answer")[1] == "final_line_not_a_shape"
    assert parse_judge('{"matcher":"STAR","mismatcher":"TRIANGLE"}')[0] == {"matcher": "STAR", "mismatcher": "TRIANGLE"}
    assert parse_judge('```json\n{"matcher":"star","mismatcher":"TRIANGLE"}\n```')[1] == "ok_wrapped"
    assert parse_judge('{"matcher":"STAR"}')[0] is None
    assert parse_judge('Prediction: {"matcher":"STAR","mismatcher":"STAR"}')[0] is None
    assert parse_judge('{"matcher":"CIRCLE","mismatcher":"STAR"}')[0] is None


def test_seeds_reproducible_across_processes():
    code = "from blind_twin import config as C; print(C.derive_seed('judge_schedule'))"
    a = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True).stdout
    b = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True).stdout
    assert a == b and a.strip()


def test_request_omits_unsupported_controls():
    from blind_twin.runner import request_body
    for m in C.ORDER:
        b = request_body(m, "x")
        assert "temperature" not in b and "seed" not in b and "top_p" not in b
        assert b["provider"] == {"order": [C.MODELS[m]["provider"]], "allow_fallbacks": False}


def _fake_run(tmp_path, malformed=0.0):
    r = Runner(tmp_path, live=False)
    r.transport = FakeTransport(malformed_rate=malformed)
    (tmp_path / "config.json").write_text(json.dumps(C.frozen_config()))
    games = r.run_games()
    r.freeze(games)
    r.run_judges()
    return r, games


def test_fake_end_to_end_and_simultaneous_commits(tmp_path):
    r, games = _fake_run(tmp_path)
    assert all(g["status"] == "complete" and g["n_valid_rounds"] == 20 for g in games)
    calls = [json.loads(l) for l in (tmp_path / "calls.jsonl").read_text().splitlines()]
    players = [c for c in calls if c["kind"] == "player"]
    judges = [c for c in calls if c["kind"] == "judge"]
    assert len(players) == 480 and len(judges) == 1440
    by = {}
    for c in players:
        by.setdefault((c["game_id"], c["round"]), []).append(c["public_history"])
    assert all(len(v) == 2 and v[0] == v[1] for v in by.values())          # both seats saw identical history
    for c in judges:                                                       # same log/target across label arms
        g = next(x for x in games if x["game_id"] == c["game_id"])
        assert c["public_history"] == g["rounds"][: c["round"] - 1]
        assert c["private"]["target_matcher"] == g["rounds"][c["round"] - 1]["matcher"]
    out = S.analyze(tmp_path)
    assert (tmp_path / "report.md").exists() and out["indices"]["S"] is not None


def test_malformed_choice_ends_game_without_resample(tmp_path):
    r, games = _fake_run(tmp_path, malformed=0.08)
    inc = [g for g in games if g["status"] == "incomplete"]
    assert inc and all("invalid round" in g["note"] for g in inc)
    calls = [json.loads(l) for l in (tmp_path / "calls.jsonl").read_text().splitlines()]
    sids = [c["slot_id"] for c in calls if c["kind"] == "player"]
    assert len(sids) == len(set(sids))                                      # never re-asked
    for g in inc:
        n = g["n_valid_rounds"]
        assert not any(c["kind"] == "player" and c["game_id"] == g["game_id"] and c["round"] > n + 1 for c in calls)


def test_primary_formulas_constructed():
    # constructed paired items: judge j correct whenever told TRUE about its own model; otherwise 50/50 pattern
    items, meta = {}, {}
    games = []
    for mm, ms in C.MATCHUPS:
        for k in range(3):
            gid = f"G{mm}{ms}{k}"
            games.append({"game_id": gid, "matchup": f"{mm}-{ms}"})
            for t in range(1, 5):
                for seat, model, opp in (("matcher", mm, ms), ("mismatcher", ms, mm)):
                    for j in C.JUDGES:
                        key = (j, gid, t, seat)
                        base = t % 2
                        items[key] = {"TRUE": 1 if model == j else base, "FALSE": base, "ANONYMOUS": base}
                        meta[key] = {"seat_model": model, "opponent_model": opp}
    acc = S.acc_table(items, meta)
    ix = S.indices(acc)
    assert acc[("astra", "astra", "ANONYMOUS")] == pytest.approx(50.0)
    assert acc[("astra", "astra", "TRUE")] == pytest.approx(100.0)
    assert ix["T[astra,astra]"] == pytest.approx(50.0) and ix["T[fable,astra]"] == pytest.approx(0.0)
    assert ix["S"] == pytest.approx(50.0) and ix["S_false"] == pytest.approx(50.0)


def test_baselines_use_prior_history_only():
    assert S.baseline_predictions([], "matcher")["frequency"] is None          # round 1 -> half credit
    bp = S.baseline_predictions(ROWS, "matcher")
    assert bp["repeat_last"] == "STAR" and bp["alternate_last"] == "TRIANGLE"
    assert bp["win_stay_lose_shift"] == "STAR"                                  # matcher won round 2 -> stay
    assert S._score(None, "STAR") == 0.5
