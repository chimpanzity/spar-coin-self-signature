"""Offline tests for the Blind Twin forecast-prediction pilot (no API calls)."""

import copy
import json

import pytest

from blind_twin_forecast_prediction import authors as AU
from blind_twin_forecast_prediction import config as C
from blind_twin_forecast_prediction import data as D
from blind_twin_forecast_prediction import execute as X
from blind_twin_forecast_prediction import prompts as P
from blind_twin_forecast_prediction import sandbox
from blind_twin_forecast_prediction import scoring as S
from blind_twin_selfself import config as BT


@pytest.fixture(scope="module")
def ev():
    return D.evaluation_set()


def _tables(fn):
    """A prediction table per cell from fn(author, target, gid, round) -> (p1, p2)."""
    ev = D.evaluation_set()
    return {(a, j): {k: fn(a, j, *k) for k in ev["inputs"]} for a, j in C.CELLS}


# ---------- evaluation set ----------

def test_acceptance_checks(ev):
    acc = D.acceptance(ev)
    assert acc["ok"], acc
    assert acc["stable_by_pairing"] == {"AA": 11, "FF": 14, "QQ": 17}
    assert {it["gid"] for it in ev["items"]} == set(C.GAMES)
    assert all(it["y_astra"] in ("STAR", "TRIANGLE") and it["y_fable"] in ("STAR", "TRIANGLE") for it in ev["items"])


def test_inputs_are_only_the_completed_history(ev):
    g = D.games()["mp:FF_00_2"]
    for t in (1, 2, 20):
        h = ev["inputs"][("mp:FF_00_2", t)]
        assert len(h) == t - 1 and all(set(r) == set(C.HISTORY_KEYS) for r in h)
        assert h == [{k: r[k] for k in C.HISTORY_KEYS} for r in g["rounds"][: t - 1]]
    assert ev["inputs"][("mp:AA_00_1", 1)] == []
    # changing the current or a future move leaves the current round's input unchanged
    g2 = copy.deepcopy(g)
    for r in g2["rounds"][9:]:
        r["p1"] = "TRIANGLE" if r["p1"] == "STAR" else "STAR"
        r["result"] = "flipped"
    assert all(D.history(g2, t) == D.history(g, t) for t in range(1, 11))
    assert D.history(g2, 11) != D.history(g, 11)


def test_targets_are_judge_forecasts_not_player_moves(ev):
    # the archive's `model` column is the seat's player; labels come from `predicted` of the named judge
    fs = D.read_forecasts(C.ORIGINAL_CSV)
    it = ev["items"][0]
    assert it["y_astra"] == fs[("astra", it["gid"], it["round"], it["seat"])]
    assert any(i["y_astra"] != i["actual_move"] for i in ev["items"])


# ---------- prompts ----------

def test_author_messages():
    ms = P.messages()
    assert P.request_body("astra", "fable")["messages"] == P.request_body("fable", "fable")["messages"]
    a, f = ms["astra"], ms["fable"]
    assert a.replace(BT.MODELS["astra"]["name"], "X") == f.replace(BT.MODELS["fable"]["name"], "X")
    assert a.count(BT.MODELS["astra"]["name"]) == 2 and "Claude" not in a and "GPT" not in f
    for m in ms.values():
        assert "TARGET_NAME" not in m and "OBSERVER_PROMPT" not in m
        assert '{"player_1":"STAR","player_2":"TRIANGLE"}' in m and "Neither player was told its opponent's model identity." in m
        assert "None. This is the first round." in m and BT.IDENTITY_ANONYMOUS in m and BT.RULES["mp"] in m
        assert "Round | Matcher (Player 1) | Mismatcher (Player 2) | Winner" in m
        assert not any(w in m.lower() for w in ("yourself", "your own", "same model", "astra-astra", "retest"))
    b = P.request_body("fable", "astra")
    assert b["provider"] == {"order": ["anthropic"], "allow_fallbacks": False} and b["max_tokens"] == 4000
    assert "temperature" not in b and "tools" not in b and b["reasoning"]["effort"] == "low"


def test_observer_prompt_matches_archived_template(ev):
    from blind_twin_selfself.judge import judge_prompt
    g = D.games()["mp:AA_00_1"]
    real = judge_prompt("fable", g, 3, "ANONYMOUS")
    hist = real.split("Completed-round history:\n")[1].split("\n\nBefore round")[0]
    ill = P.observer_prompt("fable")
    assert ill.replace(P.HISTORY_PLACEHOLDER, hist).replace(P.ROUND_PLACEHOLDER, "3") == real


# ---------- parser ----------

@pytest.mark.parametrize("text,src,why", [
    ("def predict(h):\n    return (0.5, 0.5)", "def predict(h):\n    return (0.5, 0.5)\n", "bare"),
    ("```python\ndef predict(h):\n    return (0.5, 0.5)\n```", "def predict(h):\n    return (0.5, 0.5)\n", "one_fence_stripped"),
    ("```\ndef predict(h):\n    return (0.5, 0.5)\n```\n", "def predict(h):\n    return (0.5, 0.5)\n", "one_fence_stripped"),
    ("Here it is:\n```python\ndef predict(h):\n    return (0.5, 0.5)\n```", None, "fence_not_enclosing"),
    ("```python\na=1\n```\n```python\nb=2\n```", None, "more_than_one_fence"),
    ("   ", None, "empty"),
])
def test_extract_source(text, src, why):
    assert AU.extract_source(text) == (src, why)


# ---------- sandbox and contract ----------

def test_sandbox_contract_and_isolation():
    good = "import math\n\ndef predict(history):\n    n = len(history)\n    return (1 / (1 + math.exp(-n / 10)), 0.5)\n"
    v = X.validate(good)
    assert v["ok"] and v["empty_history_output"] == [0.5, 0.5] and 19 in v["lengths"] and 0 in v["lengths"]
    for bad in ("def predict(h):\n    open('x.txt', 'w')\n    return (0.5, 0.5)\n",
                "def predict(h):\n    return (__import__('socket') and 0.5, 0.5)\n",
                "import os\ndef predict(h):\n    return (0.5, 0.5)\n",
                "def predict(h):\n    return (2.0, 0.5)\n",
                "state = [0]\ndef predict(h):\n    state[0] += 1\n    return (min(state[0] / 1000, 1.0), 0.5)\n",
                "def predict(h)\n    return (0.5, 0.5)\n",
                "def other(h):\n    return (0.5, 0.5)\n"):
        assert not X.validate(bad)["ok"], bad
    r = sandbox.run("def predict(h):\n    while True:\n        pass\n", [[]], timeout_s=5)
    assert not r["ok"] and "timeout" in r["error"]


# ---------- scorer ----------

def test_constant_half_has_brier_quarter(ev):
    t = S.constant_table(ev["inputs"])
    for j in C.TARGETS:
        assert S.brier(t, ev["items"], f"y_{j}") == pytest.approx(0.25)
    assert S.references(ev["inputs"], ev["items"])["constant_0.5"] == {"astra": pytest.approx(0.25), "fable": pytest.approx(0.25)}


def test_identical_predictions_give_zero_interaction_and_zero_swap(ev):
    tables = _tables(lambda a, j, gid, t: (0.3 + 0.01 * (t % 7), 0.6))
    p = S.primary(tables, ev["items"])
    assert p["contrasts"]["balanced_self_advantage"] == pytest.approx(0.0, abs=1e-15)
    assert all(v["balanced_self_advantage"] == pytest.approx(0.0, abs=1e-15) for v in p["per_game"].values())
    assert all(v["swapped_minus_intended"] == pytest.approx(0.0, abs=1e-15) for v in S.target_swap(tables, ev["items"]).values())
    assert all(v["different_modal_calls"] == 0 for v in S.modal_diagnostic(tables, ev["items"]).values())


def test_planted_perfect_diagonal_is_positive(ev):
    lab = {(it["gid"], it["round"], it["seat"]): it for it in ev["items"]}

    def fn(a, j, gid, t):
        if a == j:                                   # same-model author predicts its own judge perfectly
            return tuple(1.0 if lab[(gid, t, s)][f"y_{j}"] == "STAR" else 0.0 for s in C.SEATS)
        return (0.5, 0.5)
    tables = _tables(fn)
    c = S.primary(tables, ev["items"])["contrasts"]
    assert c["fable_target_advantage"] == pytest.approx(0.25) and c["astra_target_advantage"] == pytest.approx(0.25)
    assert c["balanced_self_advantage"] > 0 and c["reciprocal"]
    assert S.target_swap(tables, ev["items"])["astra"]["swapped_minus_intended"] > 0


def test_game_averaging_weights_games_equally():
    items = [dict(gid="g1", round=1, seat="p1", y_astra="STAR"), dict(gid="g1", round=2, seat="p1", y_astra="STAR"),
             dict(gid="g2", round=1, seat="p1", y_astra="TRIANGLE")]
    t = {("g1", 1): (1.0, 0.5), ("g1", 2): (1.0, 0.5), ("g2", 1): (1.0, 0.5)}
    assert S.brier(t, items, "y_astra") == pytest.approx(0.5)          # (0 + 1) / 2 games, not 1/3 per item


def test_repeat_reference(ev):
    t = S.repeat_table(ev["inputs"])
    assert t[("mp:AA_00_1", 1)] == (0.5, 0.5)
    h = ev["inputs"][("mp:AA_00_1", 2)][-1]
    assert t[("mp:AA_00_1", 2)] == tuple(0.75 if h[s] == "STAR" else 0.25 for s in ("p1", "p2"))


# ---------- runner ----------

def test_dry_pipeline_and_approval_gate(tmp_path, monkeypatch):
    prices = {m["slug"]: {"prompt": 1e-5, "completion": 5e-5} for m in C.MODELS.values()}
    AU.run_cells(tmp_path, AU.FakeAuthor(), prices, "planhash")
    calls = (tmp_path / "responses" / "calls.jsonl").read_text().splitlines()
    assert len(calls) == 4
    AU.run_cells(tmp_path, AU.FakeAuthor(), prices, "planhash")       # resume: nothing regenerated
    assert (tmp_path / "responses" / "calls.jsonl").read_text().splitlines() == calls
    man = AU.freeze_programs(tmp_path)
    assert all(v["status"] == "frozen" for v in man.values()) and man["fable_for_fable.py"]["parse"] == "one_fence_stripped"
    (tmp_path / "programs" / "astra_for_astra.py").write_text("def predict(h):\n    return (0.1, 0.1)\n")
    with pytest.raises(SystemExit):
        AU.freeze_programs(tmp_path)                                  # a frozen program is never overwritten
    assert not AU.approved(tmp_path, "planhash")
    (tmp_path / "APPROVAL.md").write_text("LIVE RUN APPROVED BY CHRIS: yes\nplan otherhash\n")
    assert not AU.approved(tmp_path, "planhash")                      # an approval for another plan does not carry over
    (tmp_path / "APPROVAL.md").write_text("LIVE RUN APPROVED BY CHRIS: yes\nplan planhash\n")
    assert AU.approved(tmp_path, "planhash")
    # budget: reservation of the worst case refuses a call that would cross the cap
    monkeypatch.setattr(C, "CAP_USD", 0.01)
    rd2 = tmp_path / "capped"
    done = AU.run_cells(rd2, AU.FakeAuthor(), prices, "planhash")
    assert done == {}
