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


def test_exploitation_indices():
    rng = random.Random(11)
    opp = "TS" * 100                                   # perfectly predictable opponent
    exploiter = opp                                    # matcher matches every round
    ex = analysis.exploitation(exploiter, opp, matcher=True, window=50)
    assert ex["ei"] == 1.0 and ex["bench"] > 0.9 and ex["eff"] > 1.0
    noisy = "".join(rng.choice("TS") for _ in range(200))
    ex2 = analysis.exploitation(noisy, opp, matcher=True, window=50)
    assert abs(ex2["ei"]) < 0.25 and ex2["eff"] < 0.3
    rand_opp = "".join(rng.choice("TS") for _ in range(200))
    ex3 = analysis.exploitation(noisy, rand_opp, matcher=True, window=50)
    assert ex3["bench"] < analysis.EFFICIENCY_MIN_BENCH and ex3["eff"] != ex3["eff"]   # NaN


# ------------------------------------------------- perspective-taking (2026-10-21) --
HANDOFF_SELF_SIM = """Place yellow paint on the shape where you think the blue circle will land.

Another decision-maker decides where the blue circle lands. The other decision-maker is another instance of yourself, the same language model.

The other decision-maker is instructed: "Place the blue circle on the shape that will not receive yellow paint." Before choosing your shape, consider what you would choose if you were in the other decision-maker's position, following that instruction and using the available history. Use that prediction to choose the shape where you expect the blue circle to land.

Available actions:
TRIANGLE
STAR

You may briefly think through your choice. End your response with the chosen action on its own line."""

HANDOFF_B = """Place the blue circle on the shape that will not receive yellow paint.

Available actions:
TRIANGLE
STAR

You may briefly think through your choice. End your response with the chosen action on its own line."""


def test_guided_prompts_match_handoff_byte_for_byte():
    assert game.system_prompt("A", "self", guidance=True) == HANDOFF_SELF_SIM
    assert game.system_prompt("A", "other", guidance=True) == HANDOFF_SELF_SIM.replace(
        "another instance of yourself, the same language model.", "a different language model.")
    assert game.system_prompt("B", None) == HANDOFF_B


def test_guided_cells_differ_only_by_identity_phrase():
    s, o = game.system_prompt("A", "self", True).split("\n\n"), game.system_prompt("A", "other", True).split("\n\n")
    assert [i for i in range(len(s)) if s[i] != o[i]] == [1]
    assert s[2] == o[2] == game.GUIDANCE_A
    # plain prompts are unchanged by the patch
    assert game.system_prompt("A", "self") == game.system_prompt("A", "self", False)
    assert game.GUIDANCE_A not in game.system_prompt("A", "self")


def test_guidance_only_for_disclosed_seat_a():
    import pytest
    with pytest.raises(AssertionError):
        game.system_prompt("B", "self", guidance=True)
    with pytest.raises(AssertionError):
        game.system_prompt("A", None, guidance=True)


# ------------------------------------------------- scripted-opponent pilot (2026-10-21) --
from paint_circle import scripted, scripted_pilot


def test_scripted_sequences_and_phases():
    assert "".join(scripted.move("ALT_S", t) for t in range(1, 7)) == "STSTST"
    assert "".join(scripted.move("ALT_T", t) for t in range(1, 7)) == "TSTSTS"
    assert "".join(scripted.move("DOUBLE_S", t) for t in range(1, 9)) == "SSTTSSTT"
    assert "".join(scripted.move("DOUBLE_T", t) for t in range(1, 9)) == "TTSSTTSS"


def test_oracle_predicts_every_phase_after_four_moves():
    for name in scripted.SEQUENCES:
        seq = "".join(scripted.move(name, t) for t in range(1, 41))
        for t in range(4, 40):
            assert scripted.oracle_prediction(seq[:t]) == seq[t], (name, t)
        assert scripted.oracle_prediction(seq[:3]) is None


class _FakeMsg:
    def __init__(self, text): self.content, self.tool_calls = text, None
class _FakeChoice:
    def __init__(self, text): self.message, self.finish_reason = _FakeMsg(text), "stop"
class _FakeResp:
    def __init__(self, text):
        self.choices, self.usage, self.provider, self.model, self.id = [_FakeChoice(text)], None, "fake", "fake", "x"
class _FakeClient:
    """Records every request; answers 'think\nTRIANGLE'. Lets tests inspect what A saw."""
    def __init__(self): self.requests = []; self.chat = self; self.completions = self
    def create(self, **kw): self.requests.append(kw); return _FakeResp("thinking...\nTRIANGLE")


def test_scripted_session_dry_run_no_leakage(tmp_path):
    import json as _j
    from paint_circle import run
    plan = dict(cost_cap_usd=5.0, call_cap=120, sessions=[dict(
        session_id="s", model_A="fable", model_B="script", disclosure_A=None, disclosure_B=None,
        script_B="DOUBLE_S", window=50, rounds=100)])
    (tmp_path / "plan.json").write_text(_j.dumps(plan))
    client = _FakeClient()
    b = run.Batch(str(tmp_path), client)
    status = b.run_session(plan["sessions"][0])
    assert status == "complete"
    rows = [_j.loads(l) for l in open(tmp_path / "s" / "rounds.jsonl")]
    assert len(rows) == 100 and len(client.requests) == 100        # one call per round, A only
    circle = "".join(r["circle"] for r in rows)
    assert circle == "".join(scripted.move("DOUBLE_S", t) for t in range(1, 101))
    assert all(r["paint"] == "T" for r in rows) and [r["a_wins"] for r in rows[:4]] == [False, False, True, True]
    for t, req in enumerate(client.requests, start=1):
        user = req["messages"][1]["content"]
        # A sees exactly the completed rounds: never the current or a future circle
        assert req["messages"][0]["content"] == game.system_prompt("A", None)
        grid = [l for l in user.splitlines() if l.startswith("Blue circle: ")]
        seen = grid[0].split(": ")[1].split() if grid else []
        assert seen == list(circle[max(0, t - 1 - 50):t - 1])
    m = scripted_pilot.session_metrics("".join(r["paint"] for r in rows), circle, 50)
    assert m["late"]["A_win"] == 0.52                              # rounds 51-100 of SSTT start at T,T: 26 of 50 are T
    assert m["late"]["PI_A"] > 0.9                                 # a constant painter is fully predictable
    assert m["late"]["shadow_win"] > 0.55 and m["late"]["EI_A"] is not None
    assert m["full"]["oracle_win"] > 0.9


def test_call_cap_stops_session(tmp_path):
    import json as _j
    from paint_circle import run
    plan = dict(cost_cap_usd=5.0, call_cap=10, sessions=[dict(
        session_id="s", model_A="fable", model_B="script", disclosure_A=None, disclosure_B=None,
        script_B="ALT_S", window=50, rounds=100)])
    (tmp_path / "plan.json").write_text(_j.dumps(plan))
    client = _FakeClient()
    b = run.Batch(str(tmp_path), client)
    b.run_session(plan["sessions"][0])
    assert len(client.requests) == 10


def test_learning_onset():
    w = [False, True, False, True] + [True] * 20
    o = scripted_pilot.learning_onset(w)
    assert o == dict(first_run10=4, last_loss=3, sustained_from=4, n_losses=2)
    assert scripted_pilot.learning_onset([True] * 5 + [False])["sustained_from"] is None


def test_iid_scripts_are_fixed_balanced_enough_and_finite():
    import pytest
    a = "".join(scripted.move("IID_20261021", t) for t in range(1, 101))
    assert a == scripted.iid_string(20261021) and set(a) <= {"T", "S"} and len(a) == 100
    assert a != scripted.iid_string(20261022)
    with pytest.raises(ValueError):
        scripted.move("IID_20261021", 101)


def test_strategy_measures_on_simple_painters():
    circle = scripted.iid_string(5)
    follower = "T" + circle[:-1]                       # paints where the circle last landed
    m = scripted_pilot.session_metrics(follower, circle, 50)["late"]
    assert m["A_follows_last_circle"] == 1.0
    m = scripted_pilot.session_metrics("T" * 100, circle, 50)["late"]
    assert m["A_p_triangle"] == 1.0 and m["A_switch_rate"] == 0.0 and m["A_lose_shift"] == 0.0


def test_deterministic_label_differs_from_random_only_in_one_word():
    r = game.system_prompt("A", "program")
    d = game.system_prompt("A", "deterministic")
    assert d == r.replace("a random computer program", "a deterministic computer program")
