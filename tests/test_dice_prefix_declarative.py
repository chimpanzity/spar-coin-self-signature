"""Offline tests for SPAR_DICE_PREFIX_DECLARATIVE_v1.0 (no GPU, no API)."""

import difflib
import math
import re

import pytest

from spar_dynamic.dice_prefix_declarative import analysis as A
from spar_dynamic.dice_prefix_declarative import config as C
from spar_dynamic.dice_prefix_declarative import prompts as P


def lp(probs):
    return {"bare": {str(f): math.log(p) if p > 0 else -1e9 for f, p in zip(C.FACES, probs)}}


def test_twelve_conditions_and_target_mapping():
    cs = P.conditions()
    assert [c["condition"] for c in cs] == [f"{a}{k}" for k in (0, 3, 6) for a in "HNSO"]
    want = {0: ([1, 2, 3], [5, 2, 6]), 3: ([4, 5, 6], [3, 1, 4]), 6: ([7, 8, 9], [6, 2, 5])}
    for c in cs:
        assert (c["positions"], c["target"]) == want[c["k"]]
        assert f"(positions {c['positions'][0]} through {c['positions'][-1]})" in c["prompt"]


def test_revealed_prefix_is_exact_and_never_leaks_the_target():
    for c in P.conditions():
        k = c["k"]
        if k == 0:
            assert "No part of its response has been revealed." in c["prompt"]
        else:
            assert P.prefix_line(k).endswith(": " + " ".join(map(str, C.G_REF[:k])))
        # the only digit runs in the prompt are the G instruction's, the revealed prefix and position numbers
        shown = re.findall(r"were: ([1-6 ]+)", c["prompt"])
        assert shown == ([] if k == 0 else [" ".join(map(str, C.G_REF[:k]))])
        assert " ".join(map(str, C.G_REF[:k + 3])) not in c["prompt"]


def test_arms_differ_only_by_one_inserted_paragraph():
    for k in C.KS:
        h = P.prompt("H", k)
        for a in "NSO":
            x = P.prompt(a, k)
            assert x == h.replace("Predict the next", P.description(a) + "\n\nPredict the next")
            assert x.startswith(P.HEAD) and x.endswith(P.ask(k))


def test_descriptions_are_matched_and_differ_only_in_source():
    d = {a: P.description(a) for a in "NSO"}
    assert len({len(v.split()) for v in d.values()}) == 1
    for a, b in (("S", "N"), ("S", "O")):
        diff = [t for t in difflib.ndiff(d[a].split(), d[b].split()) if t[0] in "+-"]
        assert {t[2:] for t in diff} <= set((P.SOURCE[a] + " " + P.SOURCE[b]).split())
    for v in d.values():
        assert not re.search(r"\d", v)                                  # no face, position or order leaks
        assert "earlier response" in v and "does not guarantee" in v and "does not determine any order" in v
        assert not re.search(r"\b(tend|tends|usually|always|typically|propensity)\b", v)   # no population claim


def test_references_are_experiment21_bytes():
    r = P.references()
    assert r["G"]["prompt_sha256"] == C.G_PROMPT_SHA256 and r["F"]["prompt_sha256"] == C.F_PROMPT_SHA256
    assert all(P.GEN in c["prompt"] for c in P.conditions())


def test_g_reference_first_six_are_all_faces():
    assert sorted(C.G_REF[:6]) == list(C.FACES)          # the fact the description reports
    assert set(C.FACES) - set(C.G_REF[:3]) == {1, 3, 4}   # k=3: remaining faces


def test_parse_three():
    assert A.parse_three("3 1 4") == [3, 1, 4]
    for bad in ("3 1", "3 1 4 6", "3,1,4", "3  1 4", "7 1 4", "31 4", ""):
        assert A.parse_three(bad) is None


def test_six_face_normalisation_and_mass():
    p, m = A.six(lp([0.4, 0.2, 0.1, 0.1, 0.05, 0.05]))
    assert abs(sum(p) - 1) < 1e-12 and abs(m - 0.9) < 1e-9 and abs(p[0] - 0.4 / 0.9) < 1e-9


def test_js_tv_rank():
    u = [1 / 6] * 6
    d = [1, 0, 0, 0, 0, 0]
    assert A.js_bits(u, u) == 0
    assert abs(A.js_bits(d, [0, 1, 0, 0, 0, 0]) - 1.0) < 1e-12
    assert abs(A.tv(d, u) - 5 / 6) < 1e-12
    assert A.rank_of([0.1, 0.5, 0.4, 0, 0, 0], 3) == 2
    assert A.near_tie([0.45, 0.4, 0.15, 0, 0, 0], 0.09) and not A.near_tie([0.6, 0.3, 0.1, 0, 0, 0], 0.09)


def _fake_data():
    G = {j: [0.05] * 6 for j in range(1, 11)}
    for j in G:
        G[j] = [0.75 if f == C.G_REF[j - 1] else 0.05 for f in C.FACES]
    ref = [dict(instruction=i, history="G", method="incremental", position=j, face_logprobs_exact=lp(G[j]))
           for i in ("G", "F") for j in G]
    tf = []
    for c in P.conditions():
        for w, j in enumerate(c["positions"]):
            good = {"H": 0.3, "N": 0.5, "S": 0.6, "O": 0.4}[c["arm"]]
            p = [good if f == c["target"][w] else (1 - good) / 5 for f in C.FACES]
            tf.append(dict(condition=c["condition"], arm=c["arm"], k=c["k"], replicate=1, original_position=j, face_logprobs_exact=lp(p)))
    raw = [dict(condition=c["condition"], arm=c["arm"], k=c["k"], replicate=1, target=c["target"],
                raw_choice_content=" ".join(map(str, c["target"])) if c["arm"] == "S" else "1 2 3",
                free_digits=[dict(logprob=-0.1, face_logprobs_exact=lp([1 / 6] * 6))] * 3) for c in P.conditions()]
    return dict(ref=ref, tf=tf, raw=raw, numerics=dict(near_tie_floor=0.09))


def test_tidy_pairs_by_position_and_scores_teacher_forcing():
    t = A.tidy(_fake_data())
    assert len(t["rows"]) == 36 and len(t["contrasts"]) == 9 * len(A.CONTRASTS)
    r = next(r for r in t["rows"] if r["condition"] == "S3" and r["position"] == 4)
    assert r["true_face"] == 3 and abs(r["p_true"] - 0.6) < 1e-9 and abs(r["G_p_true"] - 0.75) < 1e-9
    c = next(c for c in t["contrasts"] if c["k"] == 3 and c["position"] == 4 and c["contrast"] == "S-N")
    assert abs(c["d_p_true"] - 0.1) < 1e-9 and not c["within_floor"]
    w = next(w for w in t["window"] if w["condition"] == "H6")
    assert abs(w["sum_logp_true_six"] - 3 * math.log(0.3)) < 1e-9
    f = {x["condition"]: x for x in t["free"]}
    assert f["S3"]["whole_match"] and f["S3"]["k3_rule_set_only"] and not f["H3"]["whole_match"]
    assert f["H3"]["first_wrong_index"] == 1 and f["H3"]["no_repeat_in_first_six"] is False   # 5 2 6 + 1 2 3 repeats 2
    rule = next(x for x in t["rule"] if x["arm"] == "S" and x["position"] == 4)
    assert rule["unused_faces"] == "1 3 4"


def test_guard_out_refuses_frozen_folders():
    from spar_dynamic.dice_prefix_declarative.gpu import guard_out
    with pytest.raises(SystemExit):
        guard_out("/x/track1_self_prediction/21_2026-10-29_dice_logprob/out")
    with pytest.raises(SystemExit):
        guard_out("/x/track1_self_prediction/25_2026-10-30_loula_yesno_logprob_pilot")
    guard_out("/x/track1_self_prediction/26_2026-10-30_dice_prefix_declarative/main")
    guard_out("/root/out/main")


def test_tokenizer_digit_space_boundaries():
    tr = pytest.importorskip("transformers")
    try:
        tok = tr.AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B", local_files_only=True)
    except Exception:
        pytest.skip("no cached Qwen3 tokenizer")
    assert [tok.encode(str(f), add_special_tokens=False) for f in C.FACES] == [[15 + f] for f in C.FACES]
    ids = tok("3 1 4", add_special_tokens=False).input_ids
    assert ids[0::2] == [18, 16, 19] and len(set(ids[1::2])) == 1 and len(ids) == 5
