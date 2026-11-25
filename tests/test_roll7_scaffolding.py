"""Offline tests for Experiment 35."""

from __future__ import annotations

import types

import pytest

torch = pytest.importorskip("torch")

from spar_dynamic.dice_31_32 import gpu as G  # noqa: E402
from spar_dynamic.roll7_scaffolding import analysis as A  # noqa: E402
from spar_dynamic.roll7_scaffolding import design as D  # noqa: E402
from spar_dynamic.roll7_scaffolding import gpu as R  # noqa: E402
from spar_dynamic.roll7_scaffolding.__main__ import preconditions  # noqa: E402
from tests.test_dice_31_32 import TinyEngine  # noqa: E402


def test_prompts_grid_hashes_leakage():
    preconditions()
    cs = D.cells()
    assert sum(c["mode"] == "thinking" for c in cs) == 12 and sum(c["predictor"] == "mistral" for c in cs) == 12
    for c in cs:
        assert c["prompt"].endswith("Return exactly one integer, with no other text.")
    by = {c["cell_id"]: c["prompt_sha256"] for c in cs}
    for s in D.MODELS:
        for c in D.ENDINGS:                                   # identical bytes across predictors and modes
            assert len({by[f"{m}<-{s}-{c}"] for m in ("qwen/standard", "qwen/thinking", "mistral/standard")}) == 1


def test_endings_match_handoff():
    text = (D.EXP.parents[1] / "docs/handoffs/GPT_SPAR_Roll_7_Prompt_Scaffolding_Handoff.md").read_text(encoding="utf-8")
    for e in D.ENDINGS.values():
        assert f"| {e} |" in text


def dec(ids):
    m = {D.THINK_OPEN: "<think>", D.THINK_CLOSE: "</think>", D.THINK_SEP: "\n\n", 198: "\n", 19: "4", 21: "6", 50: "The"}
    return "".join(m[i] for i in ids)


@pytest.mark.parametrize("gen,fin,status,b,valid,tmpl", [
    ([D.THINK_OPEN, 198, 50, D.THINK_CLOSE, D.THINK_SEP, 21], "stop", "answered", 5, True, True),
    ([D.THINK_OPEN, 198, 50, D.THINK_CLOSE, 198, 21], "stop", "answered", 5, False, False),       # non-template whitespace is not stripped
    ([D.THINK_OPEN, 198, D.THINK_CLOSE, D.THINK_SEP, 50, 21], "stop", "answered", 4, False, True),  # prose: no digit extraction
    ([D.THINK_OPEN, 198, D.THINK_CLOSE, D.THINK_SEP, 21, 21], "stop", "answered", 4, False, True),
    ([D.THINK_OPEN, 198, D.THINK_CLOSE, D.THINK_SEP, 21], "length", "truncated after thinking closed", 4, False, True),
    ([D.THINK_OPEN, 198, D.THINK_CLOSE, D.THINK_SEP], "stop", "no final answer after thinking", None, False, True),
    ([D.THINK_OPEN, 198, 21, 19], "length", "truncated inside thinking block", None, False, None),
    ([21], "stop", "no closed thinking block", None, False, None)])
def test_split_thinking(gen, fin, status, b, valid, tmpl):
    r = R.split_thinking(gen, fin, dec)
    assert (r["status"], r["boundary"], r["final_valid"], r["whitespace_is_template"]) == (status, b, valid, tmpl)


class ThinkTiny:
    """Scripted engine for the thinking path: opens, thinks n tokens, closes, newline, face, eos."""

    def __init__(self, n):
        self.key, self.model_id, self.commit, self.eos = "qwen", "x", D.MODEL["qwen"]["revision"], {2}
        self.face_ids = dict(D.MODEL["qwen"]["face_ids"])
        self.script = [D.THINK_OPEN, 198] + [50] * n + [D.THINK_CLOSE, D.THINK_SEP, self.face_ids[6], 2]
        self.tok = types.SimpleNamespace()
        self.tok = type("T", (), {"apply_chat_template": lambda s, m, **k: "u" if k["enable_thinking"] else 1 / 0,
                                  "__call__": lambda s, t, **k: types.SimpleNamespace(input_ids=[1, 1])})()

    def decode(self, ids):
        inv = {v: str(k) for k, v in self.face_ids.items()}
        return "".join(inv.get(i, "") or {D.THINK_OPEN: "<think>", D.THINK_CLOSE: "</think>", D.THINK_SEP: "\n\n", 198: "\n"}.get(i, "x") for i in ids)

    def _fwd(self, ids, past=None):
        k = 0 if past is None else past + 1
        z = torch.zeros(151700)
        z[self.script[k]] = 20
        return types.SimpleNamespace(logits=z.view(1, 1, -1), past_key_values=k)


def test_generate_thinking_and_supplement():
    r = R.generate_thinking(ThinkTiny(5), "p", 64)
    assert r["final_valid"] and r["final_text"] == "6" and r["answer"]["argmax_token"] == "6" and r["boundary"] == 9
    e = ThinkTiny(40)
    cells = [c for c in D.cells() if c["mode"] == "thinking"][:1]
    old = D.THINK_MAX_NEW
    D.THINK_MAX_NEW = 20
    try:
        prim = R.collect_thinking(e, cells)
    finally:
        D.THINK_MAX_NEW = old
    assert len(prim) == 2 and all(p["status"] == "truncated inside thinking block" and p["answer"] is None for p in prim)
    sup = R.collect_supplementary(e, cells, prim)
    assert len(sup) == 1 and sup[0]["extends_primary"] and sup[0]["final_valid"]
    o = A.readout(prim[0])
    assert o["outcome"] == "invalid" and o["p_true7"] is None and o["boundary"] == "none"


def test_standard_tiny_and_readout():
    for e in (TinyEngine("qwen"), TinyEngine("mistral", prose=True)):
        c = next(c for c in D.cells() if c["predictor"] == e.key and c["mode"] == "standard")
        a, b = R.standard_rec(e, c, 1), R.standard_rec(e, c, 2)
        assert a["answer_matches_generation"] and A.same_rep(a, b)
        o = A.readout(a)
        assert abs(sum(o[f"p{f}"] for f in A.F) - 1) < 1e-9
        assert (o["outcome"] == "invalid") == (e.key == "mistral")
    assert A.classify(dict(final_valid=True, final_text="4", true6=4, true7=6)) == "true sixth"


def test_guard():
    with pytest.raises(SystemExit):
        R.guard_out(D.EXP.parent / "34_2026-11-25_dice_unused_faces")
    R.guard_out(D.EXP)


def test_contrast_keys():
    rows = []
    for c in D.cells():
        fl = {f: -2.0 - (c["condition"] == "GAP") * (f == str(c["true6"])) for f in A.F}
        rows.append(A.readout(dict(c, replicate=1, final_text="1", final_valid=True, finish_reason="stop", completion_tokens=1, status="answered",
                                   whitespace_is_template=True, answer=dict(face_logprobs=fl, argmax_token="1", entropy_bits=1.0))))
    cons = A.contrasts(rows)
    assert len(cons) == 30 + 12
    assert all((x["d_p_true7"] > 0) == (x["condition"] == "GAP") for x in cons if x["contrast"] == "variant - B")
    assert len(A.recurrence(cons)) == 10


def test_real_qwen_template():
    try:
        from transformers import AutoTokenizer
        t = AutoTokenizer.from_pretrained(D.MODEL["qwen"]["model_id"], revision=D.MODEL["qwen"]["revision"], local_files_only=True)
    except Exception as e:
        pytest.skip(str(e))
    assert t.convert_tokens_to_ids(["<think>", "</think>"]) == [D.THINK_OPEN, D.THINK_CLOSE]
    assert t("\n\n", add_special_tokens=False).input_ids == [D.THINK_SEP]
    text, _ = R.thinking_ids(types.SimpleNamespace(tok=t), D.prompt("qwen", "B"))
    assert text.endswith("<|im_start|>assistant\n") and "system" not in text
    assert G.canonical_sha(__file__)
