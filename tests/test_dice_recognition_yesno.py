"""Offline tests for LOULA_DICE_YESNO_LOGPROB v3.0 (Experiment 25). No GPU or network."""

import csv
import json
import math

import pytest

import repo_paths
from spar_dynamic.dice_recognition_v2 import synthetic as S
from spar_dynamic.dice_recognition_yesno import analysis as A, config as C, gpu as G, prompts as P, scoring as SC, stimuli as ST


@pytest.fixture(scope="module")
def items(tmp_path_factory):
    p = tmp_path_factory.mktemp("cal") / "items.csv"
    ST.write_items(p)
    return ST.load_calibration(p)


@pytest.fixture(scope="module")
def pairs():
    return ST.load_pairs()


# ------------------------------------------------------------------------------------------- stimuli --
def test_new_items_valid_deterministic_and_novel(items, tmp_path):
    assert len(items) == 36 and all(sum(i["task"] == t for i in items) == 12 for t in C.TASKS)
    assert all(S.correct_side(i) == "X" for i in items)
    old = {s for r in ST.read_csv(C.SOURCES["exp23_items"]) for s in (r["X"], r["Y"])}
    assert not any(i["X"] in old or i["Y"] in old for i in items)
    p = tmp_path / "items.csv"
    ST.write_items(p)
    ST.write_items(p)                                                 # rewrite is idempotent
    rows = ST.read_csv(p)
    rows[0]["X"] = rows[0]["Y"]
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ST.ITEM_FIELDS)
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(ST.SchemaError):                               # a changed file is never overwritten silently
        ST.write_items(p)


def test_novelty_check_rejects_exp23_items():
    with pytest.raises(ST.SchemaError):
        ST.load_calibration(C.SOURCES["exp23_items"])


# ------------------------------------------------------------------------------------------- prompts --
def test_one_sequence_per_prompt_and_no_labels(items, pairs):
    trials = ST.calibration_trials(items) + ST.screen_trials(pairs)
    for t in trials:
        other = t["Y"] if t["role"] == "X" else t["X"]
        assert t["sequence"] in t["prompt"] and other not in t["prompt"]
        assert "Sample A" not in t["prompt"] and "Sample B" not in t["prompt"]
        assert t["prompt"].endswith("\n" + P.ENDING) and P.sha256(t["prompt"]) == t["prompt_sha256"]


def test_polarities_differ_only_in_question(items, pairs):
    for k, seq in [("MORE_SIXES", items[0]["X"]), ("MORE_REPEATS", items[12]["X"]), ("GEN_RULE", items[24]["X"]),
                   ("AUTH", pairs[0]["qwen_seq"]), ("TYP", pairs[0]["qwen_seq"])]:
        a, b = P.prompt(k, "pos", seq).split("\n"), P.prompt(k, "neg", seq).split("\n")
        assert len(a) == len(b) and sum(x != y for x, y in zip(a, b)) == 1


def test_length_slot_matches_sequence(items):
    it = next(i for i in items if i["task"] == "GEN_RULE" and i["length"] != 10)
    assert f"sequence of {it['length']} numbers" in P.prompt("GEN_RULE", "pos", it["X"])
    assert "in 10 rolls?" in P.prompt("MORE_SIXES", "neg", items[0]["X"])


def test_trial_counts_and_roles(items, pairs):
    cal, scr, pre = ST.calibration_trials(items), ST.screen_trials(pairs), ST.preflight_trials(items)
    assert (len(cal), len(scr), len(pre)) == (144, 160, 5)
    assert len({t["trial_id"] for t in cal + scr + pre}) == 309
    q = {p["pair_id"]: p for p in pairs}
    for t in scr:
        assert t["sequence"] == (q[t["unit_id"]]["qwen_seq"] if t["role"] == "X" else q[t["unit_id"]]["mistral_seq"])
    assert [t["polarity"] for t in pre] == ["pos"] * 5 and pre[-1]["prompt"] == P.GENERIC


# --------------------------------------------------------------------------------------------- scores --
def _z(xp, yp, xn, yn):
    return {("X", "pos"): xp, ("Y", "pos"): yp, ("X", "neg"): xn, ("Y", "neg"): yn}


def test_score_algebra_and_yes_bias_cancels():
    r = SC.unit_score(_z(2.0, 0.5, -1.0, 1.0), 0.1)
    assert (r["c_pos"], r["c_neg"], r["S"]) == (1.5, 2.0, 1.75) and r["both_polarities_X"] and r["outcome"] == "X"
    for bias in (-6.0, 3.0):                                          # a Yes bias per question never moves c_pos, c_neg, S
        rb = SC.unit_score(_z(2.0 + bias, 0.5 + bias, -1.0 - bias, 1.0 - bias), 0.1)
        assert math.isclose(rb["c_pos"], 1.5) and math.isclose(rb["c_neg"], 2.0) and math.isclose(rb["S"], 1.75)
    # Yes to X whatever the question: content-insensitive, polarity-sensitive, S = 0
    r = SC.unit_score(_z(1.0, 0.0, 1.0, 0.0), 0.1)
    assert r["c_pos"] == 1.0 and r["c_neg"] == -1.0 and r["S"] == 0.0 and r["outcome"] == "indeterminate" and r["polarity_sensitive"]
    assert SC.unit_score(_z(0.0, 0.05, 0.0, 0.0), 0.1)["outcome"] == "indeterminate"
    assert SC.unit_score(_z(0.0, 1.0, 1.0, 0.0), 0.1)["both_polarities_Y"]


def _recs(kind, uid, z, **extra):
    return [dict(kind=kind, unit_id=uid, role=r, polarity=p, X="1", Y="2", z=v, mass_YN=0.99,
                 argmax_token="Yes" if v > 0 else "No", **extra) for (r, p), v in z.items()]


def test_unit_records_join_and_errors():
    recs = _recs("MORE_SIXES", "M-1", _z(2.0, -1.0, -2.0, 1.0)) + _recs("GEN_RULE", "G-1", _z(1.0, 1.0, 1.0, 1.0))
    rows = SC.unit_records(recs, 0.1)
    assert [r["unit_id"] for r in rows] == ["G-1", "M-1"]
    m = rows[1]
    assert m["S"] == 3.0 and m["greedy_yes_X_pos"] and not m["greedy_yes_Y_pos"] and m["greedy_yes_Y_neg"]
    with pytest.raises(ValueError):
        SC.unit_records(recs[:-1], 0.1)
    with pytest.raises(ValueError):
        SC.unit_records(recs + recs[:1], 0.1)


def _cal_rows(n_correct, n_both, eps=0.1):
    rows = []
    for t in C.TASKS:
        for i in range(12):
            both = i < min(n_both[t], n_correct[t])
            z = _z(1, 0, 0, 1) if both else _z(3, 0, 0.5, 0) if i < n_correct[t] else _z(0, 1, 1, 0)
            rows.append(dict(kind=t, unit_id=f"{t}-{i}", **SC.unit_score(z, eps)))
    return rows


def test_calibration_gate_pass_and_each_failure():
    ok = SC.calibration_gate(_cal_rows({"GEN_RULE": 10, "MORE_SIXES": 10, "MORE_REPEATS": 9}, {t: 8 for t in C.TASKS}), 0.1)
    assert ok["total_correct"] == 29 and ok["both_polarities_correct"] == 24 and ok["overall"] == "PASS"
    low_task = SC.calibration_gate(_cal_rows({"GEN_RULE": 12, "MORE_SIXES": 12, "MORE_REPEATS": 7},
                                              {"GEN_RULE": 9, "MORE_SIXES": 8, "MORE_REPEATS": 7}), 0.1)
    assert low_task["overall"] == "FAIL" and [k for k, v in low_task["criteria"].items() if not v] == ["MORE_REPEATS >= 8/12"]
    low_both = SC.calibration_gate(_cal_rows({t: 12 for t in C.TASKS}, {t: 7 for t in C.TASKS}), 0.1)
    assert low_both["total_correct"] == 36 and low_both["both_polarities_correct"] == 21 and low_both["overall"] == "FAIL"
    low_total = SC.calibration_gate(_cal_rows({"GEN_RULE": 10, "MORE_SIXES": 9, "MORE_REPEATS": 9}, {t: 8 for t in C.TASKS}), 0.1)
    assert low_total["total_correct"] == 28 and low_total["overall"] == "FAIL"
    with pytest.raises(ValueError):
        SC.calibration_gate(_cal_rows({t: 12 for t in C.TASKS}, {t: 12 for t in C.TASKS})[:-1], 0.1)


def _pre_records(first_tokens=("Yes", "No", "Yes", "No", "Yes"), tokenwise_shift=0.01, repeats=(0.0, 0.0, 0.0)):
    out = []
    ids = [("MORE_SIXES-01", "X"), ("MORE_SIXES-01", "Y"), ("MORE_REPEATS-01", "X"), ("MORE_REPEATS-01", "Y"), ("GENERIC", "X")]
    for i, ((uid, role), ft) in enumerate(zip(ids, first_tokens)):
        z = 1.0 if role == "X" else -1.0
        out.append(dict(trial_id=f"pre|{uid}|{role}", kind="GENERIC" if uid == "GENERIC" else uid.rsplit("-", 1)[0], unit_id=uid,
                        role=role, polarity="pos", z=z, mass_YN=0.99, argmax_token=ft, greedy_first_token=ft, greedy_text=ft,
                        diagnostic=dict(z=z + (tokenwise_shift if role == "X" else 0)),
                        template_checks=dict(ends_with_empty_think=True, has_system_turn=False, n_user_turns=1,
                                             label_appends_single_token={"Yes": True, "No": True}),
                        **({"determinism_repeats": [z + x for x in repeats]} if i == 0 else {})))
    return out


def test_preflight_gate():
    env = dict(revision_match=True, gpu="A100")
    g = SC.preflight_gate(_pre_records(), env)
    assert g["overall"] == "PASS" and math.isclose(g["delta"], 0.01) and g["epsilon"] == 0.05
    g = SC.preflight_gate(_pre_records(tokenwise_shift=0.3), env)
    assert math.isclose(g["epsilon"], 0.6) and g["overall"] == "PASS"
    assert SC.preflight_gate(_pre_records(tokenwise_shift=0.6), env)["overall"] == "FAIL"      # epsilon 1.2
    assert SC.preflight_gate(_pre_records(first_tokens=("Yes", "\n", "Yes", "yes", "No")), env)["overall"] == "FAIL"
    assert SC.preflight_gate(_pre_records(first_tokens=("Yes", "\n", "Yes", "No", "No")), env)["overall"] == "PASS"
    assert SC.preflight_gate(_pre_records(repeats=(0.0, 2e-3, 0.0)), env)["overall"] == "FAIL"
    assert SC.preflight_gate(_pre_records(), dict(env, revision_match=False))["overall"] == "FAIL"


# ------------------------------------------------------------------------------------------ analysis --
def test_auc():
    assert A.auc([2, 3], [0, 1]) == 1.0 and A.auc([0, 1], [2, 3]) == 0.0 and A.auc([1, 1], [1, 1]) == 0.5
    assert A.auc([1, 3], [2]) == 0.5


# ----------------------------------------------------------------------------------- GPU-side helpers --
def test_no_writes_into_frozen_experiments(tmp_path):
    for k in ("dice_logprob", "dice_recognition", "dice_recognition_v2", "dice_recognition_logprob"):
        with pytest.raises(SystemExit):
            G.guard_out(str(repo_paths.T1_EXP[k] / "anything"))
    G.guard_out(str(tmp_path / "out"))
    G.guard_out(str(C.EXP / "calibration"))


def test_resume_and_hash_check(tmp_path, items):
    trials = ST.calibration_trials(items)[:4]
    p = tmp_path / "t.json"
    ST.write_trials(p, trials)
    assert len(G.load_trials(str(p))) == 4
    raw = tmp_path / "scored.jsonl"
    raw.write_text("".join(json.dumps(dict(trial_id=t["trial_id"], prompt_sha256=t["prompt_sha256"])) + "\n" for t in trials[:2]))
    assert G.done_ids(str(raw), trials) == {trials[0]["trial_id"], trials[1]["trial_id"]}
    raw.write_text(json.dumps(dict(trial_id=trials[0]["trial_id"], prompt_sha256="0" * 64)) + "\n")
    with pytest.raises(SystemExit):
        G.done_ids(str(raw), trials)


class _Tok:
    """Qwen3-like toy tokenizer: Yes=9454, No=2753, ' Yes'=7414, ' No'=2308, yes=9693, no=2152."""
    table = {"Yes": [9454], "No": [2753], " Yes": [7414], " No": [2308], "yes": [9693], "no": [2152]}

    def encode(self, s, add_special_tokens=False):
        return self.table[s]

    def decode(self, ids):
        inv = {v[0]: k for k, v in self.table.items() if len(v) == 1}
        return "".join(inv.get(i, "?") for i in ids)


def test_label_ids_and_scores_from_logits():
    import torch
    tok = _Tok()
    lab = G.label_ids(tok)
    assert lab["Yes"]["id"] == 9454 and lab["No"]["id"] == 2753 and lab["No"]["space_id"] == 2308
    logits = torch.full((10000,), -20.0)
    logits[9454], logits[2753], logits[9693] = 1.0, 3.0, 0.0
    s = G.scores_from_logits(logits, lab, tok, top_n=3)
    assert math.isclose(s["z"], -2.0, abs_tol=1e-6) and s["argmax_token"] == "No"
    assert math.isclose(math.exp(s["logp_Yes"]) + math.exp(s["logp_No"]), s["mass_YN"], rel_tol=1e-5)
    assert math.isclose(s["logp_lower"]["yes"], float(torch.log_softmax(logits, -1)[9693]), rel_tol=1e-6)
