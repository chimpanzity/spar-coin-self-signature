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


# ------------------------------------------------- entropy-gradient pilot (2026-10-22) --
from paint_circle import entropy_gradient


def test_nda_zero_noise_is_exact_pattern_and_half_noise_is_seeded():
    assert scripted.nda_sequence("S", 0.0, 1) == ("SSTT" * 25)
    assert scripted.nda_sequence("T", 0.0, 1) == ("TTSS" * 25)
    a = scripted.nda_sequence("S", 0.5, 2026102250)
    assert a == scripted.nda_sequence("S", 0.5, 2026102250)              # byte-identical on repeat
    assert a != scripted.nda_sequence("S", 0.5, 2026102251)              # different seed, different string
    assert 30 < sum(x != y for x, y in zip(a, "SSTT" * 25)) < 70        # ~half flipped
    name = "NDA_T_e35_2026102235"
    assert "".join(scripted.move(name, t) for t in range(1, 101)) == scripted.nda_sequence("T", 0.35, 2026102235)


def test_oracle_is_prospective_latent_phase():
    # The oracle predicts the latent pattern regardless of what B actually plays.
    latent = scripted.nda_latent("S")
    noisy = scripted.nda_sequence("S", 0.35, 2026102235)
    m = entropy_gradient.gradient_metrics(latent, noisy, latent)["full"]
    assert m["oracle_win_realized"] == m["A_win"] == sum(a == b for a, b in zip(latent, noisy)) / 100
    assert m["pattern_following"] == 1.0 and m["losses_A_deviation"] == 0
    assert m["losses_flip_induced"] == m["losses"]                       # every loss is a script flip


def test_gradient_metrics_on_synthetic_painters():
    import random as _r
    latent = scripted.nda_latent("S")
    circle = scripted.nda_sequence("S", 0.0, 7)
    follow = entropy_gradient.gradient_metrics(circle, circle, latent)
    assert follow["full"]["A_win"] == 1.0 and follow["late"]["PI_A"] > 0.9
    star = entropy_gradient.gradient_metrics("S" * 100, circle, latent)
    assert star["full"]["A_win"] == 0.5 and star["late"]["PI_A"] > 0.9 and star["full"]["A_switch_rate"] == 0.0
    coin = "".join(_r.Random(3).choice("TS") for _ in range(100))
    c = entropy_gradient.gradient_metrics(coin, circle, latent)["full"]
    assert abs(c["pattern_following"] - 0.5) < 0.15 and c["losses_flip_induced"] == 0


def test_shadow_forecast_uses_only_the_past():
    a = scripted.nda_sequence("S", 0.2, 11)
    w = "1" * 100
    f1 = shadow.forecasts_for(a, w, 50)
    b = a[:60] + ("T" if a[60] == "S" else "S") + a[61:]                # change round 61 only
    f2 = shadow.forecasts_for(b, w, 50)
    assert [x.p_triangle for x in f1[:61]] == [x.p_triangle for x in f2[:61]]


def test_script_checksum_mismatch_is_refused(tmp_path):
    import json as _j, pytest
    from paint_circle import run
    plan = dict(cost_cap_usd=1.0, call_cap=5, sessions=[dict(
        session_id="s", model_A="fable", model_B="script", disclosure_A=None, disclosure_B=None,
        script_B="NDA_S_e10_2026102210", script_sha256="0" * 64, window=50, rounds=100)])
    (tmp_path / "plan.json").write_text(_j.dumps(plan))
    with pytest.raises(RuntimeError):
        run.Batch(str(tmp_path), _FakeClient()).run_session(plan["sessions"][0])


def test_next_call_cost_guard(tmp_path):
    import json as _j
    from paint_circle import run
    plan = dict(cost_cap_usd=0.05, max_call_cost_prior_usd=0.02, call_cap=100, sessions=[dict(
        session_id="s", model_A="fable", model_B="script", disclosure_A=None, disclosure_B=None,
        script_B="NDA_S_e00_2026102200", window=50, rounds=10)])
    (tmp_path / "plan.json").write_text(_j.dumps(plan))
    b = run.Batch(str(tmp_path), _FakeClient())
    b.spent = 0.04                                                      # 0.04 + 0.02 > 0.05: must not call
    assert b.run_session(plan["sessions"][0]) in ("budget_stop", "failed")
    assert b.calls == 0


# ------------------------------------------------- experiment 19: noise x label (2026-10-27) --
from paint_circle import noise_label


def _exp19_plan(tmp_path, labels=("none", "self", "other"), rounds=60, cap=5.0, call_cap=400):
    import json as _j, hashlib as _h
    name = "NDA_S_e15_2026102715"
    seq = "".join(scripted.move(name, t) for t in range(1, rounds + 1))
    sessions = [dict(session_id=f"s_{lab}", label=lab, model_A="fable", model_B="script",
                     disclosure_A=None if lab == "none" else lab, disclosure_B=None, script_B=name,
                     script_sha256=_h.sha256(seq.encode()).hexdigest(), window=50, rounds=rounds,
                     prospective_shadow=True) for lab in labels]
    plan = dict(tag="TEST", cost_cap_usd=cap, call_cap=call_cap, sessions=sessions)
    (tmp_path / "plan.json").write_text(_j.dumps(plan))
    return plan


class _AlternatingClient(_FakeClient):
    """Answers alternate TRIANGLE/STAR so the painter's history has some structure."""
    def create(self, **kw):
        self.requests.append(kw)
        return _FakeResp("TRIANGLE" if len(self.requests) % 2 else "STAR")


def test_exp19_dry_run_same_circle_only_label_differs_forecasts_prospective(tmp_path):
    import json as _j
    from paint_circle import run
    plan = _exp19_plan(tmp_path)
    client = _AlternatingClient()
    b = run.Batch(str(tmp_path), client)
    for s in plan["sessions"]:
        assert b.run_session(s) == "complete"
    circles, systems = {}, {}
    for s in plan["sessions"]:
        rows = [_j.loads(l) for l in open(tmp_path / s["session_id"] / "rounds.jsonl")]
        circles[s["label"]] = "".join(r["circle"] for r in rows)
        paint = "".join(r["paint"] for r in rows)
        wins = shadow.wins_string(paint, circles[s["label"]], matcher=True)    # A's own win bits
        for t, r in enumerate(rows):
            f = r["shadow_forecast_A"]
            assert f["window_rounds"] == min(t, 50)                            # last 50 completed rounds only
            off = shadow.forecast(paint[:t], wins[:t], 50)                     # uses rounds < t only
            assert abs(off.p_triangle - f["p_triangle"]) < 1e-12
    assert circles["none"] == circles["self"] == circles["other"]              # identical script under all labels
    reqs = client.requests
    sys_by_label = {}
    for s, k in zip(plan["sessions"], range(0, len(reqs), 60)):
        sys_by_label[s["label"]] = reqs[k]["messages"][0]["content"]
    base = sys_by_label["none"]
    for lab in ("self", "other"):
        parts = sys_by_label[lab].split("\n\n")
        assert "\n\n".join([parts[0]] + parts[2:]) == base                     # only the disclosure paragraph differs
        assert parts[1] == f"{game.EXISTENCE['A']} {game.IDENTITY[lab]}"



def test_exp19_analysis_audits_forecasts(tmp_path):
    import json as _j
    from paint_circle import run
    plan = _exp19_plan(tmp_path, labels=("none", "self"), rounds=100)
    b = run.Batch(str(tmp_path), _AlternatingClient())
    for s in plan["sessions"]:
        b.run_session(s)
    res = noise_label.main(str(tmp_path))
    assert res["sessions_complete"] == 2
    late = [r for r in res["summary"] if r["window"] == "late" and r["label"] == "self"][0]
    assert late["shadow_activation"] > 0.5 and late["PI_A_prospective"] > 0.5   # alternating painter is predictable
    # tamper with one logged forecast: the audit must refuse
    p = tmp_path / "s_self" / "rounds.jsonl"
    rows = [_j.loads(l) for l in open(p)]
    rows[70]["shadow_forecast_A"]["p_triangle"] = 0.123
    p.write_text("\n".join(_j.dumps(r) for r in rows) + "\n")
    import pytest
    with pytest.raises(AssertionError):
        noise_label.main(str(tmp_path))


# ------------------------------------------------- experiment 20: 5 scripts x 5 labels (2026-10-27) --
from paint_circle import noise_label_rep


def test_human_disclosure_matches_handoff():
    assert game.system_prompt("A", "human").split("\n\n")[1] == (
        "Another decision-maker decides where the blue circle lands. The other decision-maker is a human.")
    assert game.system_prompt("A", "salmon").split("\n\n")[1] == (
        "Another decision-maker decides where the blue circle lands. The other decision-maker is a dead salmon.")


def test_exp20_blocks_dry_run_and_paired_contrasts(tmp_path):
    import json as _j, hashlib as _h
    from paint_circle import run
    labels = noise_label_rep.LABELS
    sessions = []
    for blk, (ph, seed) in enumerate([("T", 11), ("S", 12)], start=1):
        name = f"NDA_{ph}_e10_{seed}"
        seq = "".join(scripted.move(name, t) for t in range(1, 101))
        for lab in labels:
            sessions.append(dict(session_id=f"b{blk}_{lab}", block=blk, label=lab, model_A="fable", model_B="script",
                                 disclosure_A=None if lab == "none" else lab, disclosure_B=None, script_B=name,
                                 script_sha256=_h.sha256(seq.encode()).hexdigest(), window=50, rounds=100,
                                 prospective_shadow=True))
    (tmp_path / "plan.json").write_text(_j.dumps(dict(tag="TEST", cost_cap_usd=5.0, call_cap=2000, sessions=sessions)))
    client = _AlternatingClient()
    b = run.Batch(str(tmp_path), client)
    for s in sessions:
        assert b.run_session(s) == "complete"
    # identical circle sequence within each block, across all five labels
    for blk in (1, 2):
        circles = {"".join(_j.loads(l)["circle"] for l in open(tmp_path / f"b{blk}_{lab}" / "rounds.jsonl")) for lab in labels}
        assert len(circles) == 1
    # only the disclosure paragraph differs between label prompts
    systems = {}
    for s, k in zip(sessions, range(0, len(client.requests), 100)):
        systems[s["label"]] = client.requests[k]["messages"][0]["content"]
    base = systems["none"]
    for lab in labels[1:]:
        parts = systems[lab].split("\n\n")
        assert "\n\n".join([parts[0]] + parts[2:]) == base
    res = noise_label_rep.main(str(tmp_path))
    assert res["sessions_complete"] == 10
    c = [x for x in res["paired_contrasts"] if x["window"] == "late" and x["contrast"] == "self - other" and x["metric"] == "A_win"][0]
    assert c["n_blocks"] == 2 and len(c["per_block"]) == 2
