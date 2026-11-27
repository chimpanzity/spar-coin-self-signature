"""Offline tests for Experiment 38. GPU code paths run end to end on CPU with Experiment 31/32's tiny scripted engine."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

from spar_dynamic.dice_31_32 import config as C32  # noqa: E402
from spar_dynamic.dice_31_32 import gpu as G  # noqa: E402
from spar_dynamic.dice_31_32 import stimuli as S32  # noqa: E402
from spar_dynamic.slot_skip_ahead import analysis as A  # noqa: E402
from spar_dynamic.slot_skip_ahead import design as D  # noqa: E402
from spar_dynamic.slot_skip_ahead import gpu as R  # noqa: E402
from spar_dynamic.slot_skip_ahead.__main__ import preconditions  # noqa: E402
from tests.test_dice_31_32 import TinyEngine  # noqa: E402


def test_design_counts_anchors_leakage():
    preconditions()
    assert len({s["rolls"] for s in D.sources()}) == 46
    assert [sum(p["k"] == k for p in D.prefixes()) for k in D.KS] == [4, 10, 17, 20, 24, 24, 33, 38]
    assert D.leakage() == []


def test_prompt_text_examples():
    head = S32.WRAP_HEAD.format(G=S32.SOURCE_INSTRUCTION["G"])
    assert D.prompt("SLOT", (5, 2, 6, 3)) == head + ("The first four rolls it produced were: 5 2 6 3\nRoll 5: [blank]. Roll 6: [predict this position]. "
                                                      "Predict roll 6 of that response. Return exactly one integer, with no other text.")
    assert D.prompt("B", (5,)) == head + "The first roll it produced was: 5\nPredict roll 3 of that response. Return exactly one integer, with no other text."
    assert D.prompt("C", (5, 2, 6, 3, 1, 4, 6, 2, 5)).endswith("The first nine rolls it produced were: 5 2 6 3 1 4 6 2 5\nPredict roll 10 of that response. "
                                                               "Return exactly one integer, with no other text.")
    items = D.prompt_items()
    for r in items:
        assert r["target_roll"] == r["k"] + 2 and f"Predict roll {r['target_roll']} " in r["prompt"]
        assert ("[blank]" in r["prompt"]) == (r["condition"] == "SLOT")


def test_rules_and_js():
    assert A.unused((5, 2, 6, 3, 1), 6) == ["4"] and A.unused((5, 2, 6, 3, 1, 4), 7) == list(A.F) and A.unused((5, 2, 6, 3, 1, 4, 6, 2), 9) == ["1", "3", "4", "5"]
    r = A.rule2((5, 2, 6, 3, 1))                       # roll 6 forced to 4, roll 7 opens a new block
    assert all(abs(v - 1 / 6) < 1e-12 for v in r.values())
    r = A.rule2((5, 2, 6, 3))                          # roll 5 in {1, 4}, roll 6 the other one
    assert abs(r["1"] - 0.5) < 1e-12 and abs(r["4"] - 0.5) < 1e-12 and abs(sum(r.values()) - 1) < 1e-12
    p = A.uniform()
    assert A.js(p, p) == 0 and abs(A.js(A.uniform(["1"]), A.uniform(["2"])) - 1) < 1e-12


def test_guard():
    with pytest.raises(SystemExit):
        R.guard_out(D.EXP.parent / "37_2026-11-25_frozen_probe_policy_swap")
    R.guard_out(D.EXP)


def test_exp31_check_indexing_on_the_archive():
    """Feeding Experiment 31's own rows in as a policy must pass bit for bit: checks the k <-> position mapping."""
    for m in D.MODELS:
        ref = {r["stream_id"]: r for r in R.read_jsonl(C32.EXP31 / "raw" / m / "streams.jsonl") if r["method"] == "incremental" and r["replicate"] == 1}
        pol = []
        for g in D.MODELS:
            x = C32.REFERENCES[(g, "G")]
            pos = {p["position"]: p for p in ref[f"{m}|G|{g}-G"]["positions"]}
            for k in D.KS:
                two = {str(f): {"face_logprobs": {s: -9.0 for s in A.F}} for f in D.FACES}
                two[str(x[k])] = pos[k + 2]
                pol.append(dict(prefix=S32.seq(x[:k]), one_step=pos[k + 1], two_step=two))
        chk = R.exp31_check(type("E", (), {"key": m})(), pol)
        assert chk["ok"] and chk["n_bit_identical"] == len(chk["rows"]) == 2 * 16


def tiny_run(root: Path):
    """Collection on tiny engines into root/raw, a fake preflight record, then the full analysis with D.EXP pointed at root."""
    engs = {"qwen": TinyEngine("qwen"), "mistral": TinyEngine("mistral")}
    for m, e in engs.items():
        raw = root / "raw" / m
        raw.mkdir(parents=True)
        pol = [R.policy_rec(e, it) for it in D.policy_items()]
        prm = [R.prompt_rec(e, it, full_pass=(n % 50 == 0)) for n, it in enumerate(D.prompt_items())]
        for r in prm:
            if r["answer_full_pass"] is None:
                r["answer_full_pass"] = r["answer"]
        G.write_jsonl(raw / "policy.jsonl", pol)
        G.write_jsonl(raw / "prompts.jsonl", prm)
        anc = {a["anchor"]: dict(content=next(r for r in prm if r["prompt_sha256"] == a["sha"])["content"]) for a in D.anchors()}
        env = dict(archival_check=dict(ok=True), anchor_check=dict(ok=True, per_anchor=anc), exp31_check=dict(ok=True, rows=[1], n_bit_identical=1),
                   files={p.name: G.canonical_sha(p) for p in sorted(raw.glob("*.jsonl"))})
        json.dump(env, open(raw / "env.json", "w", encoding="utf-8"), indent=1)
    old = D.EXP
    D.EXP = root
    try:
        prm, pol = A.load()
        chk, info = A.checks(prm, pol)
        tmpl = "Qwen standard boundary: rendered prompt ends with the empty think block"     # the tiny engine has no chat template
        assert not chk[tmpl] and all(v for k, v in chk.items() if k != tmpl), [k for k, v in chk.items() if not v]
        A.main()
        rows = list(A.csv.DictReader(open(root / "results" / "prompts_scored.csv", encoding="utf-8")))
        assert len(rows) == 2 * 548
        pri = list(A.csv.DictReader(open(root / "results" / "primary.csv", encoding="utf-8")))
        assert {r["measure"] for r in pri} >= {"Q1 index SLOT - B", "Q2 index SLOT", "Q3 crossed own advantage SLOT", "Q3 crossed own advantage C"}
        assert (root / "figures" / "fig38_slot_by_k.png").exists()
    finally:
        D.EXP = old
    return chk


def test_tiny_end_to_end(tmp_path):
    tiny_run(tmp_path)


def test_targets_sum_to_one(tmp_path):
    e = TinyEngine("qwen")
    rows = [R.policy_rec(e, it) for it in D.policy_items()[:6]]
    assert all(r["one_step_copies_identical"] for r in rows)
    T = A.targets({"qwen": rows})
    for t in T.values():
        assert abs(sum(t["T2"].values()) - 1) < 1e-9 and abs(sum(t["T1"].values()) - 1) < 1e-9
        assert all(abs(sum(b.values()) - 1) < 1e-9 for b in t["B"].values())
    assert math.isfinite(A.js(T[("qwen", (3,))]["T1"], T[("qwen", (3,))]["T2"]))
