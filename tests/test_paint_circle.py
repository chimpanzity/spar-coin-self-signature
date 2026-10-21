import random

from paint_circle import game, shadow


def test_four_action_combinations_are_zero_sum():
    for p in "TS":
        for c in "TS":
            a = game.a_wins(p, c)
            assert a == (p == c)
            # B wins exactly when A loses
            assert (not a) == (p != c)


def test_prompts_match_handoff_and_baseline_has_no_other_agent():
    a = game.system_prompt("A", None)
    b = game.system_prompt("B", None)
    assert a.startswith("Place yellow paint on the shape where you think the blue circle will land.\n\n")
    assert b.startswith("Place the blue circle on the shape that will not receive yellow paint.\n\n")
    for t in (a, b):
        assert "decision-maker" not in t and "language model" not in t
        assert t.endswith("End your response with the chosen action on its own line.")


def test_disclosures_differ_only_by_inserted_paragraph():
    base = game.system_prompt("A", None)
    for d in game.DISCLOSURES[1:]:
        t = game.system_prompt("A", d)
        first, inserted, rest = t.split("\n\n", 2)
        assert first + "\n\n" + rest == base
        assert inserted.startswith(game.EXISTENCE["A"])
    assert game.system_prompt("B", "self").count("another instance of yourself, the same language model") == 1
    assert game.system_prompt("A", "agent").split("\n\n")[1] == game.EXISTENCE["A"]


def test_history_is_truthful_and_identical_for_both_seats():
    paint, circle = "STT", "TTS"
    msg = game.render_history(paint, circle, window=50)
    assert "Yellow paint: S T T" in msg and "Blue circle: T T S" in msg
    assert "Yellow paint placed on TRIANGLE - blue circle landed on STAR (most recent)" in msg
    assert game.render_history("", "", 50) == "No previous rounds yet.\n\nYour action:"


def test_history_window_and_verbal_rows():
    rng = random.Random(0)
    paint = "".join(rng.choice("TS") for _ in range(80))
    circle = "".join(rng.choice("TS") for _ in range(80))
    msg = game.render_history(paint, circle, window=25)
    grid = [l for l in msg.splitlines() if l.startswith("Yellow paint: ")][0]
    assert grid.split(": ")[1].split() == list(paint[-25:])
    assert sum(l.startswith("Yellow paint placed on") for l in msg.splitlines()) == 5


def test_parse_choice_uses_last_token():
    assert game.parse_choice("I think STAR... no.\nTRIANGLE") == "T"
    assert game.parse_choice("**STAR**") == "S"
    assert game.parse_choice("no idea") is None
    assert game.strict_last_line("reasoning\n**TRIANGLE**")
    assert not game.strict_last_line("I choose TRIANGLE because")


def test_shadow_sees_only_window():
    # Long alternation followed by a fresh random-looking tail: the full-history
    # shadow still predicts alternation; a short window does not have to.
    choices = "TS" * 60
    wins = "1" * len(choices)
    f_full = shadow.forecast(choices, wins, None)
    assert f_full.active and f_full.p_triangle > 0.9
    f_w = shadow.forecast(choices, wins, 25)
    assert f_w.active and f_w.p_triangle > 0.9


def test_shadow_null_is_near_half():
    rng = random.Random(3)
    res = []
    for _ in range(20):
        c = "".join(rng.choice("TS") for _ in range(200))
        w = "".join(rng.choice("01") for _ in range(200))
        res.append(shadow.predictability(c, w, 50).p_shadow)
    assert abs(sum(res) / len(res) - 0.5) < 0.02


def test_wins_string():
    assert shadow.wins_string("TS", "TT", matcher=True) == "10"
    assert shadow.wins_string("TT", "TS", matcher=False) == "01"


# ---------------------------------------------------------------- analysis --
from paint_circle import analysis


def test_runs_z_signs():
    assert analysis.runs_z("TS" * 50) > 5          # over-alternation
    assert analysis.runs_z("T" * 50 + "S" * 50) < -5


def test_chi2_and_t_sf():
    assert abs(analysis._chi2_sf(3.841, 1) - 0.05) < 0.002
    assert abs(analysis._chi2_sf(5.991, 2) - 0.05) < 0.002
    assert abs(2 * analysis._t_sf(2.228, 10) - 0.05) < 0.002


def test_brown_rosenthal_detects_opponent_copying():
    rng = random.Random(5)
    opp = "".join(rng.choice("TS") for _ in range(200))
    own = "T" + "".join(opp[t - 1] if rng.random() < 0.9 else rng.choice("TS") for t in range(1, 200))
    wins = shadow.wins_string(own, opp, matcher=True)
    br = analysis.brown_rosenthal(own, opp, wins)
    assert br["br_p_opp"] < 1e-6 and br["br_opp1"] > 1
    assert br["br_p_own"] > 0.01


def test_seat_measures_on_alternator_vs_random():
    rng = random.Random(7)
    opp = "".join(rng.choice("TS") for _ in range(200))
    m = analysis.seat_measures("TS" * 100, opp, matcher=True, window=50)
    assert m["pi"] > 0.8 and m["alt"] == 1.0 and m["runs_z"] > 10
    assert abs(m["bench"] - 0.5) < 0.05             # the random opponent is not predictable


def test_abbreviated_final_line_is_accepted_and_flagged():
    assert game.parse_choice("T") == "T" and game.abbreviated_choice("T")
    assert game.parse_choice("thinking...\n**S**") == "S"
    assert not game.abbreviated_choice("STAR")
    assert game.parse_choice("Tea") is None
