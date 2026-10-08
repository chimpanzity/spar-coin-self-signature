"""Phase 2 (v7.1) unit tests, grouped by the arm they protect (Section 14)."""
import json
import subprocess
import sys

import pytest

from spar_dynamic.phase2 import analysis as A
from spar_dynamic.phase2 import config as C
from spar_dynamic.phase2 import lasso as LZ
from spar_dynamic.phase2 import tasks as T
from spar_dynamic.phase2.client import Accountant, BudgetExceeded, Slot, request_params
from spar_dynamic.phase2.parse import parse_answer, parse_generation

J = C.CORE_ORDER
SEQ = "HTTHHTHTHHTTHTHTHHTT"


# ---------------- SHARED ----------------

@pytest.mark.parametrize("text", [
    SEQ, ", ".join(SEQ), " ".join(SEQ),
    "Here:\n" + "\n".join(f"{i}. {'Heads' if c == 'H' else 'Tails'}" for i, c in enumerate(SEQ, 1)) + "\n\nHeads: 10, Tails: 10",
    "\n".join(f"Flip {i}: {'Heads' if c == 'H' else 'Tails'}" for i, c in enumerate(SEQ, 1)) + "\nTotal: 10 heads and 10 tails",
    "H = Heads, T = Tails\n\n" + SEQ,
    "\U0001fa99 " + " ".join(SEQ) + "\n\n**Heads:** 10 · **Tails:** 10",
    " ".join(SEQ[:5]) + " · " + " ".join(SEQ[5:10]) + " · " + " ".join(SEQ[10:15]) + " · " + " ".join(SEQ[15:]),
])
def test_generation_parser_accepts_single_list(text):
    r = parse_generation(text)
    assert r.valid and r.outcomes == SEQ


def test_generation_parser_rejections():
    assert parse_generation(SEQ + "\nor\n" + "H" * 10 + "T" * 10).reason == "conflicting_lists"
    assert parse_generation("H T H T H T").valid is False
    assert parse_generation("I can't flip coins.").valid is False
    assert parse_generation(SEQ, finish_reason="length").reason == "truncated_length"
    r = parse_generation(SEQ + "\n\nAgain: " + SEQ)
    assert r.valid and r.repeated_list
    assert len(parse_generation(SEQ + " " + SEQ).outcomes or "") != 40   # never concatenates into 40


def test_answer_parser():
    assert parse_answer("[0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5]", "array10").strict_valid
    assert parse_answer("```json\n[0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1]\n```", "array10").wrapped_payload
    assert parse_answer("[0.5,1.2,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5]", "array10").valid is False
    assert parse_answer("0.5", "scalar").value == 0.5          # 0.5 is a valid answer
    assert parse_answer("73%", "scalar").valid is False
    assert parse_answer("true", "scalar").valid is False
    assert parse_answer("between 0.3 and 0.4", "scalar").valid is False
    ok = parse_answer('{"C1": 0.2, "C2": 0.3, "C3": 0.5004}', "named3")
    assert ok.valid and abs(sum(ok.value.values()) - 1) < 1e-12
    assert parse_answer('{"C1": 0.2, "C2": 0.3, "C3": 0.6}', "named3").valid is False


def test_seeds_stable_across_processes():
    code = "from spar_dynamic.phase2 import config as C; print(C.derive_seed('x', 1, 'y'))"
    a = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True).stdout
    b = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True).stdout
    assert a == b and a.strip() == str(C.derive_seed("x", 1, "y"))


def test_request_params_omit_unsupported_controls():
    for alias in ("astra", "fable"):
        for role in ("generation", "judge"):
            p = request_params(C.CORE_MODELS[alias], role)
            assert "temperature" not in p and "seed" not in p and "top_p" not in p
            assert p["provider"] == {"order": [C.CORE_MODELS[alias].provider], "allow_fallbacks": False}
    q = request_params(C.CORE_MODELS["qwen"], "generation", seed=7)
    assert q["seed"] == 7 and q["temperature"] == 0.7 and q["top_k"] == 20
    assert request_params(C.CORE_MODELS["qwen"], "judge")["temperature"] == 0.0
    with pytest.raises(AssertionError):
        request_params(C.CORE_MODELS["qwen"], "generation")


def test_generation_slots_quota_and_distinct_qwen_seeds():
    dev = T.generation_slots("development")
    test = T.generation_slots("test")
    assert len(dev) == 360 and len(test) == 144
    seeds = [s.params["seed"] for s in dev + test if s.alias == "qwen"]
    assert len(seeds) == len(set(seeds)) == 168
    assert sum(1 for s in dev if s.meta["smoke"]) == 30


def test_budget_cap_enforced():
    prices = {"m": {"prompt": 1e-5, "completion": 5e-5}}
    acct = Accountant(0.01, prices)
    s = Slot("x", "t", "s", "a", "scalar", [{"role": "user", "content": "hi"}], {"model": "m", "max_tokens": 4000})
    with pytest.raises(BudgetExceeded):
        acct.reserve(s)


def test_planned_total():
    assert sum(C.PLANNED_EXECUTIONS.values()) == 3186


# ---------------- COMPLETION ----------------

def test_completion_conditions_differ_only_in_source_sentence():
    order = C.candidate_orders()[2]
    k = T.render_completion("fable", order, "plain", "HTHTHTTHHT", "astra")
    w = T.render_completion("fable", order, "plain", "HTHTHTTHHT", None)
    assert k.startswith("You are Claude Fable 5.1.") and w.startswith("You are Claude Fable 5.1.")
    kl, wl = k.splitlines(), w.splitlines()
    diff = [(a, b) for a, b in zip(kl, wl) if a != b]
    assert len(kl) == len(wl) and len(diff) == 1
    assert diff[0][0] == "Source information: " + C.SOURCE_KNOWN.format(actual_source_name="GPT-6 Astra")
    assert diff[0][1] == "Source information: " + C.SOURCE_WITHHELD


def test_completion_renderer_rejects_suffix_leak():
    with pytest.raises(AssertionError):
        T.render_completion("astra", C.candidate_orders()[0], "plain", SEQ, None)


def test_completion_allocation_balanced():
    pids = [f"p{i}" for i in range(24)]
    al = T.allocate_completion({("astra", "plain"): pids}, "test")
    from collections import Counter
    assert Counter(a["order_index"] for a in al.values()) == {i: 4 for i in range(6)}
    for oi in range(6):
        firsts = [a["first_condition"] for a in al.values() if a["order_index"] == oi]
        assert firsts.count("known") == firsts.count("withheld") == 2


def _cells(kd, ko, wd, wo, n=3):
    cells = {}
    for g in J:
        for p in C.PROMPT_ORDER:
            cells[(g, p)] = [{"parent_id": f"{g}{p}{i}",
                              **{(j, "known"): (kd if j == g else ko) for j in J},
                              **{(j, "withheld"): (wd if j == g else wo) for j in J}} for i in range(n)]
    return cells


def test_h4_constructed_examples():
    r = A.h4_panel(_cells(.09, .15, .10, .21))["panel"]
    assert r["C_withheld"] == pytest.approx(0.11) and r["C_known"] == pytest.approx(0.06)
    assert r["gain_own"] == pytest.approx(0.01) and r["gain_other"] == pytest.approx(0.06)
    assert r["H4"] == pytest.approx(-0.05)
    r2 = A.h4_panel(_cells(.09, .15, .25, .25))["panel"]
    assert r2["C_withheld"] == pytest.approx(0) and r2["H4"] == pytest.approx(0.06)
    assert r2["H4"] == pytest.approx(r2["C_known"] - r2["C_withheld"])


def test_h4_unchanged_judge_zero_and_skill_by_difficulty():
    skill = {"astra": 1, "fable": 1, "qwen": 0}
    pred = {"astra": .15, "fable": .05, "qwen": 0}
    cells = {(g, p): [{"parent_id": g + p, **{(j, c): 0.25 - skill[j] * pred[g] for j in J for c in A.CONDS}}]
             for g in J for p in C.PROMPT_ORDER}
    r = A.h4_panel(cells)
    assert r["panel"]["H4"] == pytest.approx(0)
    assert r["panel"]["C_known"] == pytest.approx(0.0333, abs=1e-4)
    assert r["pair_means"]["astra-fable"]["C_known"] == pytest.approx(0)


def test_h4_pairwise_mask_ignores_third_judge_failure():
    cells = _cells(.09, .15, .10, .21)
    for lst in cells.values():
        for d in lst:
            d[("qwen", "known")] = None
    r = A.h4_panel(cells)
    assert r["crossovers"]["astra-fable|plain"] is not None
    assert r["crossovers"]["astra-qwen|plain"] is None and r["panel"] is None
    assert A.h4_panel(cells, "common3")["panel"] is None


def test_h4_positive_from_harming_others():
    # own losses unchanged, other-source forecasts get WORSE when source withheld -> negative other gain
    r = A.h4_panel(_cells(.10, .15, .10, .12))["panel"]
    assert r["gain_own"] == pytest.approx(0) and r["gain_other"] < 0 and r["H4"] > 0


# ---------------- ANONYMOUS ----------------

def _items(qfun):
    items = []
    for p in C.PROMPT_ORDER:
        for b in range(4):
            for g in J:
                items.append({"pair_id": f"s{p}{b}{g}", "block_id": f"{p}{b}", "prompt": p, "relation": "SAME",
                              "src": (g, g), "q": {j: qfun(j, "SAME", (g, g)) for j in J}})
            for g, r in (("astra", "fable"), ("astra", "qwen"), ("fable", "qwen")):
                items.append({"pair_id": f"d{p}{b}{g}{r}", "block_id": f"{p}{b}", "prompt": p, "relation": "DIFFERENT",
                              "src": (g, r), "q": {j: qfun(j, "DIFFERENT", (g, r)) for j in J}})
    return items


def test_constant_responses_give_zero_roles():
    for v in (0.0, 0.5, 1.0):
        it = _items(lambda j, rel, s: v)
        assert A.pdr_panel(it)["panel"] == {"P": 0.0, "D": 0.0, "R": 0.0}
        assert A.auroc([v] * 3, [v] * 4) == 0.5


def test_focal_only_sensitivity_positive_P():
    # each judge separates only SAME pairs of its own source from mixed pairs involving it
    def q(j, rel, s):
        if rel == "SAME" and s[0] == j:
            return 0.9
        return 0.5
    r = A.pdr_panel(_items(q))["panel"]
    assert r["P"] > 0 and r["R"] > 0


def test_legacy_identity():
    def q(j, rel, s):
        return 0.8 if (rel == "SAME" and s[0] == j) else (0.3 if (rel == "DIFFERENT" and j in s) else 0.5)
    c3 = A.pdr_common3(_items(q))["panel"]
    assert c3["D_legacy"] == pytest.approx(c3["P"] - c3["D"] / 2)


def test_pair_blocks_structure_and_content_blindness():
    valid = {g: [f"{g}{i}" for i in range(9)] for g in J}
    blocks, pairs = T.build_pair_blocks(valid, "test", "plain")
    assert len(blocks) == 4 and len(pairs) == 24
    from collections import Counter
    for b in blocks:
        ps = [x for x in pairs if x.block_id == b["block_id"]]
        assert Counter(x.relation for x in ps) == {"SAME": 3, "DIFFERENT": 3}
        uses = Counter([x.first for x in ps] + [x.second for x in ps])
        assert all(v == 2 for v in uses.values()) and len(uses) == 6
        assert Counter(x.first for x in ps) == Counter(x.second for x in ps)   # each parent once first, once second
        assert all(x.first != x.second for x in ps)
    rev = sum(b["cycle_reversed"] for b in blocks)
    assert abs(rev - (len(blocks) - rev)) <= 1
    # same ids -> same blocks regardless of content (allocation sees ids only)
    assert T.build_pair_blocks(valid, "test", "plain")[1][0].pair_id == pairs[0].pair_id


def test_pair_prompt_has_no_names():
    txt = T.render_pair("plain", SEQ, SEQ[::-1])
    for m in C.CORE_MODELS.values():
        assert m.display not in txt
    assert "you" not in txt.lower().replace("your", "")


# ---------------- NAMED ----------------

def test_named_always_self_gives_zero_roles():
    items = []
    for p in C.PROMPT_ORDER:
        for g in J:
            for i in range(6):
                items.append({"parent_id": f"{p}{g}{i}", "prompt": p, "source": g,
                              "prob": {j: {x: (1.0 if x == j else 0.0) for x in J} for j in J}})
    r = A.named_panel(items)["panel"]
    assert r == {"P": 0.0, "D": 0.0, "R": 0.0}


# ---------------- LASSO ----------------

def test_lasso_windows_and_features():
    W = LZ.windows(SEQ)
    assert len(W) == 13 and all(len(w[0]) == 14 for w in W)
    for feats, target, t in W:
        assert feats[:7] == [1.0 if c == "H" else 0.0 for c in SEQ[t - 7:t]]
    f = LZ.window_features("HHTTTHT")
    assert f[7] == pytest.approx(3 / 6) and f[8:] == [1.0, 1.0, 0, 0, 0, 0]


# ---------------- FIXTURES ----------------

def test_fixture_truths():
    for slot, truth in T.completion_fixtures("astra"):
        assert len(truth["truth"]) == 10 and all(0 <= x <= 1 for x in truth["truth"])
    pf = T.pair_fixtures("astra")
    vals = sorted(round(t["truth"], 3) for _, t in pf)
    assert vals.count(0.5) == 2 and min(vals) < 0.01 and max(vals) > 0.99
