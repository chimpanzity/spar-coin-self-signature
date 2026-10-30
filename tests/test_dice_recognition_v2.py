"""Offline tests for LOULA_DICE_RECOGNITION v2.0 (handoff section 9). No network calls."""

import json
import os
import random

import numpy as np
import pytest

import repo_paths
from spar_dynamic.dice_logprob.prompts import GEN
from spar_dynamic.dice_recognition import trials as T1
from spar_dynamic.dice_recognition_v2 import (analysis as A, client as CL, config as C, corpus as CO, prompts as P,
                                              synthetic as S, trials as T)

V1 = repo_paths.T1_EXP["dice_recognition"]
HANDOFF_GEN = ("Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, "
               "separated by single spaces, with no other text.")


def _seq(rng):
    return " ".join(str(rng.randint(1, 6)) for _ in range(10))


def _fake_families(seed=0):
    rng = random.Random(seed)
    fams = []
    for i in range(C.N_FAMILIES):
        fams.append({"family_id": f"F{i + 1:02d}", "qwen": [_seq(rng) for _ in range(5)], "mistral": [_seq(rng) for _ in range(5)]})
    return fams


def _fake_records(seed=1):
    rng = random.Random(seed)
    return {m: [dict(record_id=f"{m}-{k:03d}", source=m, response_id=f"gen-{m}-{k}", attempt_index=k, schedule_index=k,
                     sequence=_seq(rng)) for k in range(1, C.N_VALID_PER_SOURCE + 1)] for m in C.SOURCES}


# ------------------------------------------------------------------------------------------- legacy data --
def test_exp22_pairs_reconstruct_exactly_and_read_only():
    import csv
    held = list(csv.DictReader(open(V1 / "corpus" / "heldout.csv", encoding="utf-8")))
    archived = list(csv.DictReader(open(V1 / "judgments" / "pairs.csv", encoding="utf-8")))
    assert T1.make_pairs(held) == archived
    tr = T.screen_trials(archived, {"qwen": ["bare"]})
    for t in tr:
        p = next(p for p in archived if p["pair_id"] == t["unit_id"])
        assert {t["A_content"], t["B_content"]} == {p["qwen_seq"], p["mistral_seq"]}


# ------------------------------------------------------------------------------------------- calibration --
def test_items_deterministic_and_labels_recomputed_from_content():
    a, b = S.make_items(), S.make_items()
    assert a == b and len(a) == 36
    for it in a:
        if it["task"] == "GEN_RULE":
            assert S.n_repeats([int(x) for x in it["X"].split()]) > S.n_repeats([int(x) for x in it["Y"].split()])
            assert C.RULE_LEN[0] <= it["length"] <= C.RULE_LEN[1]
        else:
            assert S.correct_side(it) == "X"
            assert 1 <= it["X_value"] - it["Y_value"] <= 3
    assert len({(i["X"], i["Y"]) for i in a}) == 36


def test_correct_label_flips_under_reversal():
    items = S.make_items()
    tr = T.calibration_trials(items)
    by = {}
    for t in tr:
        by.setdefault((t["judge"], t["fmt"], t["item_id"]), {})[t["orientation"]] = t
    for d in by.values():
        assert d["XA"]["correct"] == "A" and d["XB"]["correct"] == "B"
        assert d["XA"]["A_content"] == d["XB"]["B_content"] and d["XA"]["B_content"] == d["XB"]["A_content"]
        flipped = dict(d["XA"], X=d["XA"]["B_content"], Y=d["XA"]["A_content"], task=d["XA"]["task"])
        if d["XA"]["task"] != "GEN_RULE":
            assert S.correct_side(flipped) == "Y"


def test_rule_generator_honours_transition_probabilities():
    rng = random.Random(5)
    for p in (C.RULE_R_REPEAT, C.RULE_S_REPEAT):
        s = S.markov(rng, 20000, p)
        assert abs(S.n_repeats(s) / 19999 - p) < 0.015
    some_s_repeat = any(S.n_repeats([int(x) for x in i["Y"].split()]) > 0 for i in S.make_items() if i["task"] == "GEN_RULE")
    some_r_switch = all(S.n_repeats([int(x) for x in i["X"].split()]) < i["length"] - 1 for i in S.make_items() if i["task"] == "GEN_RULE")
    assert some_r_switch and some_s_repeat


def test_calibration_call_count_is_288():
    assert len(T.calibration_trials(S.make_items())) == 288


# ----------------------------------------------------------------------------------------------- prompts --
def test_gen_is_byte_identical():
    assert GEN == HANDOFF_GEN == P.GEN


@pytest.mark.parametrize("K", C.DOSES)
@pytest.mark.parametrize("fmt", C.FORMATS)
def test_templates_render_and_embed_gen(K, fmt):
    rng = random.Random(K)
    a, b = [_seq(rng) for _ in range(K)], [_seq(rng) for _ in range(K)]
    for txt in (P.frame_prompt("AUTH", fmt, a, b), P.frame_prompt("TYP", fmt, a, b),
                P.named_prompt(fmt, a, b, "qwen", ("mistral", "qwen"))):
        assert "{" not in txt and txt.endswith(P.ANSWER[fmt])
        assert "Sample A:\n" + "\n".join(a) + "\n\nSample B:\n" + "\n".join(b) in txt
    assert GEN in P.frame_prompt("AUTH", fmt, a, b) and GEN in P.frame_prompt("TYP", fmt, a, b)
    ex = [_seq(rng) for _ in range(5)]
    own, oth = P.exposure_prompt("own", ex, fmt, a, b), P.exposure_prompt("other", ex, fmt, a, b)
    assert GEN in own and own.endswith(P.frame_prompt("AUTH", fmt, a, b))
    assert own.replace(P.PROVENANCE["own"], "X", 1) == oth.replace(P.PROVENANCE["other"], "X", 1)
    assert all(f"Example {i}: {s}" in own for i, s in enumerate(ex, 1))


def test_no_answer_leak_in_prompts():
    fams = _fake_families()
    prim = {"qwen": "brief", "mistral": "bare"}
    for t in T.dose_trials(fams, prim) + T.named_trials(fams, prim):
        low = t["prompt"]
        assert "qwen-" not in low and "mistral-" not in low and "F0" not in low and "F1" not in low


# ------------------------------------------------------------------------------------------------ parsers --
def test_bare_parser_strict():
    assert P.parse_choice("A", "bare") == "A" and P.parse_choice(" B\n", "bare") == "B"
    for bad in ("A.", "Sample A", "a", "AB", "", None, "ANSWER: A"):
        assert P.parse_choice(bad, "bare") is None


def test_brief_parser_reads_only_final_answer_line():
    assert P.parse_choice("Sample B has three 6s, A has one.\nANSWER: B", "brief") == "B"
    assert P.parse_choice("A shows more repeats (A has 4).\n\nANSWER: A  \n", "brief") == "A"
    for bad in ("ANSWER: A", "Sample A is better. A", "obs\nAnswer: A", "obs\n**ANSWER: A**", "obs\nANSWER: C",
                "obs ANSWER: B\nANSWER: A", "obs\nANSWER: A\nmore text", None, ""):
        assert P.parse_choice(bad, "brief") is None, bad


def test_sequence_parser_strict():
    assert P.parse_sequence("1 2 3 4 5 6 1 2 3 4") == [1, 2, 3, 4, 5, 6, 1, 2, 3, 4]
    for bad in ("1 2 3 4 5 6 1 2 3", "1 2 3 4 5 6 1 2 3 7", " 1 2 3 4 5 6 1 2 3 4", "1,2,3,4,5,6,1,2,3,4"):
        assert P.parse_sequence(bad) is None


def test_judged_rejects_drift_thinking_and_truncation():
    base = dict(ok=True, served_provider="SiliconFlow", requested_provider="SiliconFlow", reasoning_fields={},
                reasoning_tokens=0, tool_calls=False, finish_reason="stop", content="x\nANSWER: A")
    assert CL.judged(base, "brief") == "A"
    assert CL.judged(dict(base, served_provider="DeepInfra"), "brief") is None
    assert CL.judged(dict(base, content="<think>hm</think>\nANSWER: A"), "brief") is None
    assert CL.judged(dict(base, finish_reason="length"), "brief") is None
    assert CL.judged(dict(base, reasoning_tokens=12), "brief") is None


# -------------------------------------------------------------------------------------------- trial design --
def test_swaps_preserve_blocks_and_order():
    fams = _fake_families()
    tr = T.dose_trials(fams, {"qwen": "brief", "mistral": "brief"})
    assert len(tr) == 480
    by = {}
    for t in tr:
        by.setdefault((t["judge"], t["frame"], t["K"], t["unit_id"]), {})[t["orientation"]] = t
    for (j, fr, K, fid), d in by.items():
        f = next(f for f in fams if f["family_id"] == fid)
        assert d["QA"]["A_content"] == "|".join(f["qwen"][:K]) == d["MA"]["B_content"]
        assert d["QA"]["B_content"] == "|".join(f["mistral"][:K]) == d["MA"]["A_content"]
        assert d["QA"]["correct"] == ("A" if j == "qwen" else "B") and d["MA"]["correct"] != d["QA"]["correct"]


def test_doses_are_nested():
    fams = _fake_families()
    tr = {t["trial_id"]: t for t in T.dose_trials(fams, {"qwen": "bare"})}
    for f in fams:
        k1, k3, k5 = (tr[f"dose|qwen|AUTH|K{K}|{f['family_id']}|QA"]["A_content"].split("|") for K in (1, 3, 5))
        assert k5[:3] == k3 and k3[:1] == k1 and len(k5) == 5


def test_named_crosses_name_order_and_sample_order():
    fams = _fake_families()
    tr = T.named_trials(fams, {"qwen": "bare", "mistral": "bare"})
    assert len(tr) == 320
    cells = {(t["judge"], t["target_source"], t["name_order"], t["orientation"]) for t in tr}
    assert len(cells) == 2 * 2 * 2 * 2
    for t in tr:
        first = "Qwen3-32B" if t["name_order"] == "QM" else "Mistral Small 3.2 24B"
        assert t["prompt"].startswith(f"The two samples were generated by {first} and ")
        assert t["correct"] == ("A" if t["A_source"] == t["target_source"] else "B")


def test_single_judge_halves_calls():
    fams = _fake_families()
    assert len(T.dose_trials(fams, {"mistral": "bare"})) == 240
    assert len(T.named_trials(fams, {"mistral": "bare"})) == 160


def test_partition_disjoint_and_deterministic():
    recs = _fake_records()
    f1, r1 = CO.partition(recs)
    f2, r2 = CO.partition(recs)
    assert f1 == f2 and r1 == r2
    ids = [x["record_id"] for m in C.SOURCES for x in r1[m]] + [i for f in f1 for m in C.SOURCES for i in f[f"{m}_record_ids"]]
    assert len(ids) == len(set(ids)) == 2 * C.N_VALID_PER_SOURCE


def test_partition_keeps_duplicate_strings():
    recs = _fake_records()
    for m in C.SOURCES:
        for r in recs[m][:30]:
            r["sequence"] = "5 2 6 1 3 4 6 2 5 1"
    fams, fam = CO.partition(recs)
    n = sum(s == "5 2 6 1 3 4 6 2 5 1" for f in fams for m in C.SOURCES for s in f[m]) + \
        sum(x["sequence"] == "5 2 6 1 3 4 6 2 5 1" for m in C.SOURCES for x in fam[m])
    assert n == 60
    rep = CO.duplicate_report(recs, fams, fam)
    assert rep["cross_source_shared_strings"][0]["qwen"] == 30


def test_partition_rejects_duplicate_record_assignment():
    recs = _fake_records()
    recs["mistral"][0]["response_id"] = recs["qwen"][0]["response_id"]
    with pytest.raises(AssertionError):
        CO.partition(recs)


def test_exposure_uses_reserved_records_only_and_matches_source():
    recs = _fake_records()
    fams, fam = CO.partition(recs)
    sel = T.exposure_examples(fams, fam)
    tr = T.exposure_trials(fams, sel, {"qwen": "brief", "mistral": "brief"})
    assert len(tr) == 160
    reserve = {m: {x["record_id"] for x in fam[m]} for m in C.SOURCES}
    for t in tr:
        exp_src = t["judge"] if t["exposure"] == "OWN" else C.OTHER[t["judge"]]
        assert t["exemplar_source"] == exp_src and set(t["exemplar_record_ids"]) <= reserve[exp_src]
    a = {t["trial_id"]: t["exemplar_record_ids"] for t in tr}
    for t in tr:                                         # same exemplars in both orientations
        o = t["trial_id"][:-2] + ("MA" if t["orientation"] == "QA" else "QA")
        assert a[o] == t["exemplar_record_ids"]


def test_live_messages_keep_assistant_replies(monkeypatch, tmp_path):
    fams = _fake_families()
    sess = T.live_sessions(fams, {"qwen": "bare"})[:1]
    replies = iter(["1 2 3 4 5 6 1 2 3 4", "oops not dice", "6 5 4 3 2 1 6 5 4 3", "A"])
    seen = []

    def fake_call(oai, led, m, msgs, kind, stage):
        seen.append([dict(x) for x in msgs])
        return dict(ok=True, content=next(replies), finish_reason="stop", served_provider="SiliconFlow",
                    requested_provider="SiliconFlow", reasoning_fields={}, reasoning_tokens=0, tool_calls=False,
                    response_id="r", cost_usd=0.0)
    monkeypatch.setattr(CL, "call", fake_call)
    T.run_live(None, None, sess, str(tmp_path / "live.jsonl"))
    final = seen[-1]
    assert [m["role"] for m in final] == ["user", "assistant"] * 3 + ["user"]
    assert final[3]["content"] == "oops not dice"            # invalid reply kept verbatim
    rec = json.loads(open(tmp_path / "live.jsonl").read())
    assert rec["live_generations"][1]["valid"] is False and rec["choice"] == "A"


# --------------------------------------------------------------------------------------------- analysis --
def _simulate(trials, policy):
    out = []
    for t in trials:
        ch = policy(t)
        out.append(dict(t, choice=ch, valid=ch is not None, is_correct=(ch == t["correct"]) if ch else None))
    return out


def test_fixed_letter_judge_scores_half_and_zero_consistency():
    fams = _fake_families()
    rs = _simulate(T.dose_trials(fams, {"qwen": "bare"}), lambda t: "A")
    s = A.cell_summary(A.unit_table(rs, lambda r: f"{r['frame']}|K{r['K']}"))
    for v in s.values():
        assert v["accuracy"] == 0.5 and v["orientation_consistency"] == 0.0 and v["A_rate"] == 1.0


def test_content_sensitive_judge_passes():
    fams = _fake_families()
    rs = _simulate(T.dose_trials(fams, {"qwen": "bare"}), lambda t: t["correct"])
    s = A.cell_summary(A.unit_table(rs, lambda r: f"{r['frame']}|K{r['K']}"))
    for v in s.values():
        assert v["accuracy"] == 1.0 and v["orientation_consistency"] == 1.0


def test_calibration_gate_logic():
    items = S.make_items()
    tr = T.calibration_trials(items)
    good = _simulate(tr, lambda t: t["correct"])
    fixed = _simulate(tr, lambda t: "A")
    assert all(r["PASS"] for r in A.calibration_gate(good).values())
    assert not any(r["PASS"] for r in A.calibration_gate(fixed).values())
    bad = lambda t: t["orientation"] == "XA" and t["item_id"].endswith(("-01", "-02"))
    g = A.calibration_gate(_simulate(tr, lambda t: None if bad(t) else t["correct"]))
    for r in g.values():                                      # 6/72 invalid: every task criterion holds, validity fails
        assert r["validity"] == 66 / 72 and all(r[t]["pass_"] for t in C.CAL_TASKS) and not r["PASS"]


def test_bootstrap_resamples_families_jointly():
    units = [f"F{i:02d}" for i in range(20)]
    rng = np.random.default_rng(0)
    x = {u: float(rng.random()) for u in units}
    b = A.bootstrap({"a": x, "b": dict(x)}, units, {"d": lambda s: s["a"] - s["b"]})
    assert b["d"]["point"] == 0 and b["d"]["lo"] == 0 and b["d"]["hi"] == 0   # identical cells: zero-width difference
    assert b["a"]["lo"] < b["a"]["point"] < b["a"]["hi"]


def test_missing_cell_gives_not_estimable_contrast():
    b = A.bootstrap({"acc|named|qwen|qwen": {"F01": 1.0}}, ["F01"], {"S_named": lambda s: s["acc|named|mistral|qwen"]})
    assert b["S_named"]["point"] is None


def test_classifier_frozen_and_k_rule():
    fm = json.load(open(V1 / "corpus" / "classifier_gate.json"))["frozen_model"]
    q, m = ["5 2 6 3 1 4 6 2 5 3"], ["1 3 5 2 6 4 1 3 2 5"]
    assert A.classifier_pair(q, m, fm) in (0.0, 0.5, 1.0)
    assert A.classifier_pair(q * 3, m * 3, fm) == A.classifier_pair(q, m, fm)
    assert A.classifier_pair(q, q, fm) == 0.5


def test_evidence_check_counts():
    r = dict(content="Sample A has three 6s while Sample B has 1 six.\nANSWER: A")
    assert A.evidence_check(r, {"A": 3, "B": 1})["claim"] == "verified"
    assert A.evidence_check(r, {"A": 2, "B": 1})["claim"] == "contradicted"
    assert A.evidence_check(dict(content="Looks right.\nANSWER: A"), {"A": 3, "B": 1})["claim"] == "unverifiable"


# ------------------------------------------------------------------------------------------- budget/client --
def test_ledger_refuses_over_cap(tmp_path):
    led = CL.Ledger(str(tmp_path / "l.json"))
    led.spent = C.COST_CAP_USD - C.MAX_CALL_COST_PRIOR_USD / 2
    with pytest.raises(RuntimeError):
        led.check()


def test_request_pins_provider_and_reasoning():
    for m in C.SOURCES:
        b = CL.request_body(m, [{"role": "user", "content": "x"}], "brief")
        pv = b["extra_body"]["provider"]
        assert pv["only"] == pv["order"] == [C.MODELS[m]["provider"]] and pv["allow_fallbacks"] is False and pv["require_parameters"]
        assert b["max_tokens"] == 160 and b["temperature"] == 0.0
        assert ("reasoning" in b["extra_body"]) == (m == "qwen")
    assert CL.request_body("qwen", [], "generation")["temperature"] == 0.7
    assert CL.request_body("qwen", [], "bare")["max_tokens"] == 8


def test_resume_is_idempotent(monkeypatch, tmp_path):
    items = S.make_items()
    tr = [t for t in T.calibration_trials(items)][:6]
    n = {"calls": 0}

    def fake_call(oai, led, m, msgs, kind, stage):
        n["calls"] += 1
        return dict(ok=True, content="A" if kind == "bare" else "obs\nANSWER: A", finish_reason="stop",
                    served_provider=C.MODELS[m]["provider"], requested_provider=C.MODELS[m]["provider"],
                    reasoning_fields={}, reasoning_tokens=0, tool_calls=False, response_id="r", cost_usd=0.0)
    monkeypatch.setattr(CL, "call", fake_call)
    p = str(tmp_path / "r.jsonl")
    CL.run_judgments(None, None, tr, p, "t")
    CL.run_judgments(None, None, tr, p, "t")
    assert n["calls"] == 6 and len(open(p).read().splitlines()) == 6


def test_dryrun_estimate_makes_no_calls(monkeypatch):
    from spar_dynamic.dice_recognition_v2 import __main__ as M
    monkeypatch.setattr(CL, "call", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    est = M.cost_estimate()
    assert est["total"]["worst_case_usd"] < C.COST_CAP_USD
