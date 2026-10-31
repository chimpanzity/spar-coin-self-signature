"""Offline tests for SPAR_CROSSED_GUIDED_SELFPRED_v1.0 (no GPU, no API)."""

import math
import re

import pytest

from spar_dynamic.dice_crossed_guidance import analysis as A
from spar_dynamic.dice_crossed_guidance import config as C
from spar_dynamic.dice_crossed_guidance import prompts as P
from spar_dynamic.dice_crossed_guidance.gpu import guard_out, seeds

SEQ = [5, 2, 6, 3, 1, 4, 6, 2, 5, 3]
REF = [3, 1, 5, 6, 2, 4, 1, 3, 6, 2]


def items():
    out = []
    for g in C.MODELS:
        out.append(dict(item_id=f"A-{g}", tier="A", generator=g, sequence=SEQ, ref_id=f"R-{g}-01", ref_sequence=REF))
        for i in range(3):
            out.append(dict(item_id=f"B-{g}-{i + 1:02d}", tier="B", generator=g, sequence=SEQ[i:] + SEQ[:i],
                            ref_id=f"R-{g}-{i + 1:02d}", ref_sequence=REF))
    return out


def test_crossed_mapping_is_complete_and_symmetric():
    t = P.build_trials(items())
    assert len(t) == len(items()) * 2 * len(C.CONDITIONS) * 9
    cells = {(x["predictor"], x["generator"]) for x in t}
    assert cells == {(p, g) for p in C.MODELS for g in C.MODELS}
    assert all(x["diagonal"] == (x["predictor"] == x["generator"]) for x in t)
    assert len({x["trial_id"] for x in t}) == len(t)
    # every item is seen by both predictors under identical conditions/arms
    for it in items():
        per = {p: sorted((x["cond"], x["arm"]) for x in t if x["item_id"] == it["item_id"] and x["predictor"] == p) for p in C.MODELS}
        assert per["qwen"] == per["mistral"]


def test_attribution_is_true_in_every_cell():
    for x in P.build_trials(items()):
        head = x["prompt"].split("\n\n")[0]
        if x["framing"] == "R":
            assert ("your own model" in head and " not " not in head) == x["diagonal"]
            assert ("A different model" in head) == (not x["diagonal"])
        if x["framing"] == "T":
            assert C.MODEL[x["generator"]]["name"] in head
            assert C.MODEL[C.MODELS[1 - C.MODELS.index(x["generator"])]]["name"] not in x["prompt"]
        if x["framing"] == "A":
            assert head == "A language model was given the following instruction:"
        assert "your own model" not in x["prompt"] or x["framing"] == "R"


def test_prompts_differ_only_in_header_and_paragraph_and_embed_instruction_verbatim():
    t = [x for x in P.build_trials(items()) if x["item_id"] == "B-qwen-01" and x["predictor"] == "mistral" and x["cond"] == "m3"]
    by = {x["arm"]: x["prompt"].split("\n\n") for x in t}
    for arm, parts in by.items():
        assert parts[1] == P.GEN
        assert parts[-1] == by["AH"][-1] and parts[2] == by["AH"][2]
    assert by["AD"][1:] == by["TD"][1:] == by["RD"][1:]
    assert by["AH"][1:] == by["TH"][1:]


def test_paragraphs_are_length_matched():
    assert len(P.PARAGRAPH["I"].split()) == len(P.paragraph("D", REF).split())


def test_window_indexing_and_targets():
    for x in P.build_trials(items()):
        assert x["target"] == [x["sequence"][j - 1] for j in x["positions"]]
        assert x["positions"] == list(C.CONDITIONS[x["cond"]]["positions"])
        assert f"positions {x['positions'][0]} through {x['positions'][-1]}" in x["prompt"]
        n = {2: "two", 3: "three"}[len(x["positions"])]
        assert f"Return exactly {n} integers" in x["prompt"]


def test_no_leakage_beyond_revealed_prefix():
    for x in P.build_trials(items()):
        r = x["reveal"]
        shown = re.findall(r"were: ([1-6 ]+)", x["prompt"])
        assert shown == ([] if r == 0 else [P.seq_str(x["sequence"][:r])])
        if x["cond"] == "m3":
            assert "The integers at positions 4 through 6 are not revealed to you." in x["prompt"]
        if x["evidence"] == "D":
            assert P.seq_str(REF) in x["prompt"] and "not the response you are predicting" in x["prompt"]
        else:
            assert P.seq_str(REF) not in x["prompt"]


def test_archival_prompts_unchanged():
    refs = P.references()
    assert refs["G"]["prompt_sha256"] == C.G_PROMPT_SHA256 and refs["F"]["prompt_sha256"] == C.F_PROMPT_SHA256
    x = {c["condition"]: c for c in P.archival26()}
    assert len(x) == 12 and x["x26_H3"]["target"] == [3, 1, 4]


def test_scoring_algebra():
    u = [1 / 6] * 6
    d = [1, 0, 0, 0, 0, 0]
    assert A.js_bits(u, u) == 0 and abs(A.js_bits(d, [0, 1, 0, 0, 0, 0]) - 1) < 1e-12
    assert abs(A.kl_bits(u, u)) < 1e-12 and abs(A.entropy_bits(u) - math.log2(6)) < 1e-12
    p = [0.5, 0.3, 0.1, 0.05, 0.03, 0.02]
    ce = -sum(a * math.log2(b) for a, b in zip(u, p))
    assert abs(A.kl_bits(u, p) - (ce - A.entropy_bits(u))) < 1e-12
    lp = {str(f): math.log(x * 0.8) for f, x in zip(C.FACES, p)}
    q, mass = A.six(lp)
    assert abs(mass - 0.8) < 1e-12 and all(abs(a - b) < 1e-12 for a, b in zip(q, p))
    assert abs(sum(A.temper(p, 0.7)) - 1) < 1e-12 and A.temper(p, 0.7)[0] > p[0]


def test_self_advantage_sign_and_interaction():
    vals = {("qwen", "q1"): 0.1, ("mistral", "q1"): 0.3, ("qwen", "m1"): 0.4, ("mistral", "m1"): 0.2}
    s = A.self_advantage(vals)({"qwen": ["q1"], "mistral": ["m1"]})
    assert s == pytest.approx(dict(self_adv_qwen_targets=0.2, self_adv_mistral_targets=0.2, interaction=0.2))


def test_bootstrap_clusters_duplicates_and_is_seeded():
    its = {"B-qwen-01": dict(tier="B", generator="qwen", sequence=SEQ), "B-qwen-02": dict(tier="B", generator="qwen", sequence=SEQ),
           "B-mistral-01": dict(tier="B", generator="mistral", sequence=REF), "A-qwen": dict(tier="A", generator="qwen", sequence=SEQ)}
    cl = A.clusters(its)
    assert cl["qwen"] == [["B-qwen-01", "B-qwen-02"]] and cl["mistral"] == [["B-mistral-01"]]
    vals = {("qwen", "B-qwen-01"): 0.1, ("mistral", "B-qwen-01"): 0.2, ("qwen", "B-qwen-02"): 0.1, ("mistral", "B-qwen-02"): 0.2,
            ("qwen", "B-mistral-01"): 0.3, ("mistral", "B-mistral-01"): 0.1}
    a = A.boot_dict(A.self_advantage(vals), cl)
    assert a == A.boot_dict(A.self_advantage(vals), cl)
    assert a["interaction"]["est"] == pytest.approx(0.15)


def test_seed_table_unique_and_disjoint():
    s = [x for m in C.MODELS for k, n in (("feasibility", 4), ("reference", 16), ("target", 48)) for x in seeds(k, m, n)]
    assert len(set(s)) == len(s)


def test_frozen_folders_guarded(tmp_path):
    with pytest.raises(SystemExit):
        guard_out(str(C.EXP26 / "main"))
    guard_out(str(C.EXP / "main"))


def test_budget_table_within_cap():
    its = [dict(item_id=f"{t}-{g}-{i}", tier=t, generator=g, sequence=SEQ, ref_id="r", ref_sequence=REF)
           for g in C.MODELS for t, n in (("A", 1), ("B", C.N_TARGETS)) for i in range(n)]
    ct = A.call_table(P.build_trials(its), its)
    assert ct["n_trials"] == 5400 and ct["est_cost_usd"] < C.GPU_WARN_USD
    assert set(ct["per_cell"].values()) == {1350}


def test_integrity_flags():
    rows = A.integrity_rows([dict(item_id="x", tier="B", generator="qwen", sequence=SEQ, source="s", seed=1, ref_id="r", ref_sequence=SEQ)])
    assert rows[0]["ref_equals_target"] and rows[0]["ref_shared_prefix_len"] == 10 and not rows[0]["D_is_scored_target"]
