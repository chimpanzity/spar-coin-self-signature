"""Offline tests for the first-level Blind Coder pilot (track 2, folder 22). No API calls."""

import copy
import math

import pytest

from blind_coder_player_choices import authors as AU
from blind_coder_player_choices import config as C
from blind_coder_player_choices import data as D
from blind_coder_player_choices import execute as X
from blind_coder_player_choices import prompts as P
from blind_coder_player_choices import scoring as S
from opponent_disclosure_mp_3models import game as G


@pytest.fixture(scope="module")
def games():
    return D.load_games()


@pytest.fixture(scope="module")
def items(games):
    return D.items(games)


def programs_all_valid():
    return [dict(id=f"b{b:02d}_{a}_for_{j}.py", block=b, author=a, target=j, valid=True, status="valid")
            for b in range(1, C.N_BLOCKS + 1) for a, j in C.CELLS]


def preds_from(fn, items, programs):
    return {p["id"]: {S.key(it): fn(p, it) for it in items} for p in programs}


# ---------- answer key ----------

def test_acceptance(games, items):
    acc = D.acceptance(games, items)
    assert acc["ok"], acc
    assert {"AQ_00_2_MU1", "QA_00_1_MU1", "QF_00_1_MU1"} <= set(acc["contributing_games"])
    assert not any(it["target"] == "qwen" for it in items)
    assert all(it["y"] in ("STAR", "TRIANGLE") for it in items)


def test_inputs_only_preceding_rounds(games, items):
    g = next(x for x in games if x["game_id"] == "AQ_00_1")
    it = next(i for i in items if i["game_id"] == "AQ_00_1" and i["round"] == 8 and i["seat"] == "p1")
    assert it["history"] == [{k: r[k] for k in C.HISTORY_KEYS} for r in g["rounds"][:7]] and it["y"] == g["rounds"][7]["p1"]
    g2 = copy.deepcopy(g)
    for r in g2["rounds"][7:]:                        # change round t = 8 and later
        r["p1"], r["p2"], r["result"] = "TRIANGLE", "TRIANGLE", "Matcher"
    assert all(D.history(g2, t) == D.history(g, t) for t in range(1, 9))
    assert all(set(it["history"][0]) == set(C.HISTORY_KEYS) for it in items if it["history"])
    assert all(it["history"] == [] for it in items if it["round"] == 1)


# ---------- prompts ----------

def test_player_templates_reproduce_original_prompts(games):
    g = games[0]
    for seat in C.SEATS:
        for target in C.TARGETS:
            for t in (1, 2, 20):
                h = D.history(g, t)
                real = G.player_prompt(P.SEAT_NAME[seat], target, "qwen", False, h, t)
                assert P.player_template(seat, target).replace(P.HISTORY_SLOT, G.history_text(h)).replace(P.ROUND_SLOT, str(t)) == real


def test_author_messages_identical_across_authors_and_clean():
    for j in C.TARGETS:
        assert P.request_body("astra", j)["messages"] == P.request_body("fable", j)["messages"]
        b = P.request_body("fable", j)
        assert not {"temperature", "top_p", "seed", "tools"} & set(b) and b["max_tokens"] == 4000
        assert b["provider"]["allow_fallbacks"] is False and b["reasoning"]["effort"] == "low"
    a, f = P.messages()["astra"], P.messages()["fable"]
    assert a.replace("GPT-6 Astra", "X") == f.replace("Claude Fable 5.1", "X")
    for m in (a, f):
        assert "TARGET_NAME" not in m and "PLAYER_1_TEMPLATE" not in m and "PLAYER_2_TEMPLATE" not in m
        assert m.count("Return your final choice on the last nonempty line, using exactly STAR or TRIANGLE.") == 2
        assert "Your opponent's model identity is not disclosed." in m and "You are Player 2, the MISMATCHER." in m
        assert not any(w in m.lower() for w in ("71/109", "65.1", "observer", "yourself", "your own", "switch", "experiment", "forecast"))


# ---------- contract ----------

def test_contract_accepts_valid_and_rejects_bad():
    good = "import math\n\ndef predict(history, seat):\n    if not history:\n        return 0.5 if seat == 'p1' else 0.4\n" \
           "    return 0.5 + 0.3 * math.tanh(len(history) / 19 - 0.5)\n"
    v = X.validate(good)
    assert v["ok"] and v["round1_p1"] == 0.5 and v["round1_p2"] == 0.4
    calls = X.synthetic_calls()
    assert {s for _, s in calls} == {"p1", "p2"} and any(len(h) == 19 for h, _ in calls) and any(h == [] for h, _ in calls)
    for bad in ("def predict(history, seat):\n    return True\n",
                "def predict(history, seat):\n    return float('inf')\n",
                "def predict(history, seat):\n    return -0.1\n",
                "def predict(history, seat):\n    return (0.5, 0.5)\n",
                "def predict(history):\n    return 0.5\n",
                "n = [0]\ndef predict(history, seat):\n    n[0] += 1\n    return 0.5 if n[0] < 50 else 0.6\n",
                "import random\ndef predict(history, seat):\n    return random.random()\n",
                "def predict(history, seat):\n    return open('C:/Windows/win.ini').read() and 0.5\n"):
        assert not X.validate(bad)["ok"], bad


# ---------- scorer ----------

def test_constant_half_and_perfect(items):
    for j in C.TARGETS:
        assert S.stratified_loss(S.constant(items), items, j) == pytest.approx(0.25)
        perfect = {S.key(it): float(S.yv(it)) for it in items}
        assert S.stratified_loss(perfect, items, j) == 0.0


def test_stratified_equals_item_mean_on_balanced_archive(items):
    _, base = S.baselines(items)
    for p in base.values():
        for j in C.TARGETS:
            assert S.stratified_loss(p, items, j) == pytest.approx(S.item_loss(p, items, j), abs=1e-12)


def test_identical_predictions_zero_balanced_and_zero_swap(items):
    progs = programs_all_valid()
    preds = preds_from(lambda p, it: 0.3 + 0.4 * (it["round"] % 3 == 0), items, progs)
    pr = S.primary(progs, preds, items)
    assert pr["contrasts"]["balanced_self_advantage"] == pytest.approx(0.0, abs=1e-15)
    # an author giving identical predictions for both names has exactly zero swap effect, even if the authors differ
    preds = preds_from(lambda p, it: 0.6 if p["author"] == "astra" else 0.2 + 0.1 * (it["round"] % 2), items, progs)
    sw = S.target_swap(progs, preds, items)
    assert all(r["swapped_minus_intended"] == 0.0 for a in C.AUTHORS for r in sw[a]["per_block"])


def test_planted_diagonal_positive_and_targeting(items):
    progs = programs_all_valid()
    preds = preds_from(lambda p, it: float(S.yv(it)) if p["author"] == p["target"] == it["target"] else 0.5, items, progs)
    pr = S.primary(progs, preds, items)
    assert pr["contrasts"]["fable_own_author_advantage"] == pytest.approx(0.25)
    assert pr["contrasts"]["astra_own_author_advantage"] == pytest.approx(0.25) and pr["contrasts"]["reciprocal"]
    assert all(r["swapped_minus_intended"] > 0 for r in S.target_swap(progs, preds, items)["astra"]["per_block"])


def test_incomplete_blocks_and_failures(items):
    progs = programs_all_valid()
    progs[5]["valid"], progs[5]["status"] = False, "contract failure"
    preds = preds_from(lambda p, it: 0.5, items, [p for p in progs if p["valid"]])
    assert len(S.complete_blocks(progs)) == 9
    res = S.score_all(progs, preds, items)
    assert res["validity"]["valid"] == 39 and res["primary"]["planned_comparison_complete"]
    assert res["cell_descriptives"][f"{progs[5]['author']}->{progs[5]['target']}"]["n_valid"] == 9
    for p in progs[:12]:
        p["valid"] = p is progs[0] or p["valid"] and False
    assert not S.primary(progs, preds_from(lambda p, it: 0.5, items, progs), items)["planned_comparison_complete"]


def test_opening_handling_and_switch_conversion_hand_worked():
    its = [dict(game_id="g", round=1, seat="p1", target="astra", opponent="qwen", replicate=1, y="STAR", prev_own=None, prev_won=None, history=[]),
           dict(game_id="g", round=2, seat="p1", target="astra", opponent="qwen", replicate=1, y="STAR", prev_own="STAR", prev_won=True, history=[]),
           dict(game_id="g", round=3, seat="p1", target="astra", opponent="qwen", replicate=1, y="STAR", prev_own="STAR", prev_won=False, history=[]),
           dict(game_id="g", round=4, seat="p1", target="astra", opponent="qwen", replicate=1, y="TRIANGLE", prev_own="STAR", prev_won=True, history=[])]
    rep, swi = S.history_rule(its, False), S.history_rule(its, True)
    assert rep[("g", 1, "p1")] == swi[("g", 1, "p1")] == 0.5
    assert rep[("g", 2, "p1")] == 0.75 and swi[("g", 2, "p1")] == 0.25
    assert S.p_switch(0.8, "STAR") == pytest.approx(0.2) and S.p_switch(0.8, "TRIANGLE") == 0.8
    prof = S.switch_profile({("g", 1, "p1"): 0.5, ("g", 2, "p1"): 0.9, ("g", 3, "p1"): 0.2, ("g", 4, "p1"): 0.3}, its, "astra")
    assert prof["win"] == pytest.approx((0.1 + 0.7) / 2) and prof["loss"] == pytest.approx(0.8)          # round 1 excluded
    obs = S.observed_switch(its)["astra"]
    assert obs["win"] == 0.5 and obs["loss"] == 0.0 and obs["n_win"] == 2


def test_observed_switch_matches_handoff(items):
    obs = S.observed_switch(items)
    for (j, k), (sw, n) in C.EXPECTED_SWITCH.items():
        assert obs[j][f"n_{k}"] == n and obs[j][k] == pytest.approx(sw / n)


def test_learned_reference_uses_other_wave_only(items):
    ref = S.learned_reference(items)
    it = next(i for i in items if i["target"] == "astra" and i["replicate"] == 1 and i["round"] == 5)
    train = [i for i in items if i["target"] == "astra" and i["replicate"] == 2 and i["round"] > 1 and i["prev_won"] is it["prev_won"]]
    ps = (sum(i["y"] != i["prev_own"] for i in train) + 1) / (len(train) + 2)
    assert ref[S.key(it)] == pytest.approx(1 - ps if it["prev_own"] == "STAR" else ps)
    assert all(ref[S.key(i)] == 0.5 for i in items if i["round"] == 1)


# ---------- runner ----------

def test_schedule_and_dry_pipeline(tmp_path, monkeypatch):
    sch = AU.schedule()
    assert sch == AU.schedule() and len(sch) == 40 and len({s["slot_id"] for s in sch}) == 40
    assert [s["order"] for s in sch] == list(range(1, 41))
    assert all(sorted((s["author"], s["target"]) for s in sch if s["block"] == b) == sorted(C.CELLS) for b in range(1, 11))
    assert any([(s["author"], s["target"]) for s in sch if s["block"] == b] != list(C.CELLS) for b in range(1, 11))   # shuffled within blocks
    prices = {m["slug"]: {"prompt": 1e-5, "completion": 5e-5} for m in C.MODELS.values()}
    fake = AU.FakeAuthor()
    AU.run_schedule(tmp_path, fake, prices, "planhash", log=lambda m: None)
    n = fake.n
    AU.run_schedule(tmp_path, fake, prices, "planhash", log=lambda m: None)
    assert n == 40 and fake.n == 40                                     # resume reissues nothing
    man = AU.freeze_programs(tmp_path)
    assert sum(v["status"] == "frozen" for v in man.values()) == 40
    name = next(iter(man))
    (tmp_path / "programs" / name).write_text("def predict(history, seat):\n    return 0.1\n")
    with pytest.raises(SystemExit):
        AU.freeze_programs(tmp_path)
    assert not AU.approved(tmp_path, "planhash")
    (tmp_path / "APPROVAL.md").write_text("LIVE RUN APPROVED BY CHRIS: yes\nplan 588d03bb7bc7\n")       # folder 21's plan
    assert not AU.approved(tmp_path, "planhash")
    monkeypatch.setattr(C, "CAP_USD", 0.05)
    assert AU.run_schedule(tmp_path / "capped", AU.FakeAuthor(), prices, "planhash", log=lambda m: None) == {}
