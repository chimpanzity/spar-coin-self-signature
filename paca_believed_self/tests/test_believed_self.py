"""Offline tests for the PACA believed-self generator pilot (no network)."""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "task"))

import believed_self as B                          # noqa: E402
import run_believed_self_pilot as R                # noqa: E402
from api_client import parse_choice                # noqa: E402
from prompts import SYS_MINIMALIST                 # noqa: E402

PRICES = {m["slug"]: {"prompt": 1e-5, "completion": 5e-5} for m in B.MODELS.values()}


def _run(tmp_path, s, policy="mixed", fail_rate=0.0, budget=None):
    return R.run_session(s, str(tmp_path), R.FakeClient(s.model, fail_rate=fail_rate, policy=policy), PRICES,
                         budget or R.Budget(1e9, 0.0), live=False, log=lambda x: None)


def _trials(tmp_path, s):
    return R._jsonl(os.path.join(str(tmp_path), s.model, s.session_id, "trials.jsonl"))


def _sess(model="fable", gen="random", belief="self"):
    return next(x for x in B.sessions() if (x.model, x.generator, x.belief) == (model, gen, belief))


def test_design():
    ss = B.sessions()
    assert len(ss) == 12 and len({s.session_id for s in ss}) == 12
    assert [s.model for s in ss[::4]] == ["fable", "astra", "qwen"]                 # execution order
    for m in B.MODEL_ORDER:
        codes = sorted(s.code for s in ss if s.model == m)
        assert codes == ["P-O", "P-S", "R-O", "R-S"]
        for g in B.GENERATORS:                                                      # paired opponent seeds
            assert len({s.seed for s in ss if s.model == m and s.generator == g}) == 1
    assert len({s.seed for s in ss}) == 6
    assert B.MODELS["qwen"]["slug"] == "qwen/qwen3.8-27b" and B.MODELS["fable"]["provider"] == "anthropic"


def test_prompts_differ_only_in_belief_sentence_and_hide_generator():
    a, b = R.system_prompt("self").split("\n"), R.system_prompt("other").split("\n")
    assert a[0] == B.BELIEF_SENTENCE["self"] and b[0] == B.BELIEF_SENTENCE["other"]
    assert a[1:] == b[1:] and "\n".join(a[2:]) == SYS_MINIMALIST                     # baseline PACA prompt, byte-identical
    for p in (R.system_prompt("self"), R.system_prompt("other")):
        for w in R.FORBIDDEN_IN_PROMPTS:
            assert w not in p.lower(), w


def test_no_peeking_and_order_of_operations(tmp_path, monkeypatch):
    calls = []
    real = R.choose_opponent_move

    def spy(gen, past_choices, past_cr, rng):
        calls.append(("opp", len(past_choices)))
        return real(gen, past_choices, past_cr, rng)
    monkeypatch.setattr(R, "choose_opponent_move", spy)
    s = _sess("astra", "proteus", "self")
    fc = R.FakeClient("astra")
    orig = fc.chat.completions.create
    fc.chat.completions.create = lambda **kw: (calls.append(("model", None)), orig(**kw))[1]
    R.run_session(s, str(tmp_path), fc, PRICES, R.Budget(1e9, 0.0), False, log=lambda x: None)
    seq = [c for c in calls]
    for t in range(1, B.N_TRIALS + 1):                      # opponent commits from t-1 trials before the trial-t model call
        i = seq.index(("opp", t - 1))
        assert seq[i + 1] == ("model", None)
    rows = _trials(tmp_path, s)
    assert len(rows) == 200 and all(len(r["prior_forecasts"]) == r["trial"] - 1 for r in rows)


def test_model_sees_only_last_25_and_history_matches(tmp_path):
    s = _sess("fable", "proteus", "other")
    _run(tmp_path, s)
    rows = _trials(tmp_path, s)
    r = rows[150]
    grid = [l for l in r["user_prompt"].splitlines() if l.startswith("Blue circle landed on:")][0]
    assert grid.split(":", 1)[1].split() == list(r["prior_circles"][-25:])
    assert "Previous rounds" in r["user_prompt"] and r["user_prompt"].count("You chose") == 5
    for w in R.FORBIDDEN_IN_PROMPTS:
        assert w not in r["user_prompt"].lower()


def test_self_vs_other_identical_history_fields_when_behaviour_identical(tmp_path):
    for gen in B.GENERATORS:                                # model policy depends only on the user prompt -> identical games
        a, b = _sess("qwen", gen, "self"), _sess("qwen", gen, "other")
        _run(tmp_path, a, policy="copy_last"); _run(tmp_path, b, policy="copy_last")
        ra, rb = _trials(tmp_path, a), _trials(tmp_path, b)
        assert [x["user_prompt"] for x in ra] == [x["user_prompt"] for x in rb]
        assert [x["circle"] for x in ra] == [x["circle"] for x in rb]
        assert ra[0]["system_prompt_sha256"] != rb[0]["system_prompt_sha256"]


def test_random_coin_sequence_independent_of_model_and_failures(tmp_path):
    s = _sess("astra", "random", "self")
    _run(tmp_path / "a", s, policy="mixed")
    _run(tmp_path / "b", s, policy="copy_last", fail_rate=0.3)     # retries consume no opponent draws
    ca = [r["circle"] for r in _trials(tmp_path / "a", s)]
    cb = [r["circle"] for r in _trials(tmp_path / "b", s)]
    assert len(ca) == 200 and 70 < ca.count("T") < 130
    assert len(cb) >= 3 and cb == ca[:len(cb)]                       # b may stop early (3 failures in a row) by design
    att = R._jsonl(os.path.join(str(tmp_path / "b"), "astra", s.session_id, "attempts.jsonl"))
    assert any(not x["accepted"] for x in att)


def test_no_coin_substitution_session_stops(tmp_path):
    s = _sess("qwen", "proteus", "self")
    st = _run(tmp_path, s, fail_rate=1.0)
    assert st["status"] == "stopped_no_valid_choice" and st["completed_trials"] == 0
    att = R._jsonl(os.path.join(str(tmp_path), "qwen", s.session_id, "attempts.jsonl"))
    assert len(att) == B.MAX_TRIAL_ATTEMPTS and not any(a["accepted"] for a in att)
    assert _trials(tmp_path, s) == []


def test_resume_reproduces_uninterrupted_run(tmp_path):
    s = _sess("fable", "proteus", "self")
    _run(tmp_path / "full", s, policy="copy_last")
    b = R.Budget(1e9, 0.0)
    b.cap = 80 * 0.001 + (0.002 + B.MAX_TOKENS * 5e-5)
    st = _run(tmp_path / "part", s, policy="copy_last", budget=b)
    assert st["status"] == "stopped_budget" and 0 < st["completed_trials"] < 200
    st2 = _run(tmp_path / "part", s, policy="copy_last")              # resume: replays and verifies opponent RNG
    assert st2["status"] == "complete"
    keys = ("trial", "forecast", "circle", "correct", "opp_ranval", "n_channels_active", "user_prompt")
    full = [{k: r[k] for k in keys} for r in _trials(tmp_path / "full", s)]
    part = [{k: r[k] for k in keys} for r in _trials(tmp_path / "part", s)]
    assert full == part


def test_parser_expected_responses():
    assert parse_choice("TRIANGLE") == "T"
    assert parse_choice("Looking at the recent landings, star seems likely.\n\n**STAR**") == "S"
    assert parse_choice("The circle has landed on STAR often, but I'll go with\nTRIANGLE") == "T"
    assert parse_choice("") is None and parse_choice("I can't tell.") is None
    assert R.final_line_exact("blah\n**STAR**", "S") and not R.final_line_exact("STAR it is", "S")
