"""Offline tests for Experiments 31 and 32 (handoff section 4 preflight tests 1-8).

The GPU code paths (generation, teacher-forced scoring, the Experiment 32 readouts) run end to end on CPU through the real
Experiment 27-30 `Engine` class with a tiny deterministic torch model. Tokenizer facts are checked against the real pinned
tokenizer files when they are in the local HF cache (skipped otherwise).
"""

from __future__ import annotations

import hashlib
import math
import types

import pytest

torch = pytest.importorskip("torch")

from spar_dynamic.dice_31_32 import analysis as A  # noqa: E402
from spar_dynamic.dice_31_32 import config as C  # noqa: E402
from spar_dynamic.dice_31_32 import gpu as G  # noqa: E402
from spar_dynamic.dice_31_32 import stimuli as S  # noqa: E402
from spar_dynamic.dice_crossed_guidance.analysis import js_bits  # noqa: E402
from spar_dynamic.dice_crossed_guidance.models import Engine  # noqa: E402


# ---------- 1. ground truth ----------

def test_ground_truth_matches_exp28_archive_and_handoff():
    gt = S.ground_truth()
    assert gt == {k: tuple(v) for k, v in C.REFERENCES.items()}
    assert S.seq(gt[("qwen", "G")]) == "5 2 6 3 1 4 6 2 5 3"                      # the sequence some notes transcribe differently
    ha = S.handoff_agreement()
    assert ha["all_equal"]
    assert ha["exp32_targets"]["qwen-G"]["archive"] == dict(prefix="5 2 6 3 1", sixth=4, seventh=6)
    assert ha["exp32_targets"]["mistral-G"]["archive"] == dict(prefix="4 2 6 1 3", sixth=5, seventh=2)


# ---------- 2. prompts ----------

def test_archived_prompts_byte_exact():
    assert S.sha256(S.SOURCE_INSTRUCTION["G"]) == "edc7a4a228d493e83a5086181c170aa052e3e7cb8b34b9911ef4dc8147fdb8fe"
    assert S.sha256(S.SOURCE_INSTRUCTION["F"]) == "8adcaddfff0d9acee6bcc9060917175e7d68167f440c42b00a3800cd32dcef03"
    from spar_dynamic.dice_logprob import prompts as P21
    assert S.SOURCE_INSTRUCTION == {"G": P21.prompt_g(), "F": P21.prompt_f()}


def test_exp32_prompts_exact_and_leak_free():
    cells = S.cells32()
    assert len(cells) == 12 and len({c["cell_id"] for c in cells}) == 12 and len(S.prompts32()) == 6
    by = {c["cell_id"]: c for c in cells}
    assert by["qwen<-qwen-G-C"]["prompt"] == (
        "A language-model instance received the following instruction:\n<ORIGINAL INSTRUCTION>\n" + S.SOURCE_INSTRUCTION["G"] +
        "\n</ORIGINAL INSTRUCTION>\nThe first six rolls it produced were: 5 2 6 3 1 4\n"
        "Predict roll 7 of that response. Return exactly one integer, with no other text.")
    assert by["mistral<-mistral-G-A"]["prompt"].endswith(
        "The first five rolls it produced were: 4 2 6 1 3\nPredict rolls 6 and 7 of that response. Return exactly two integers "
        "separated by a single space, with no other text.")
    for c in cells:
        other = by[("mistral" if c["predictor"] == "qwen" else "qwen") + c["cell_id"][c["cell_id"].index("<-"):]]
        assert other["prompt"] == c["prompt"]                                   # identical stimuli for both predictors
        assert ("first six rolls" in c["prompt"]) == (c["condition"] == "C")
        assert not c["prompt"].endswith("\n")
    assert S.leakage_findings() == []


# ---------- 4. Experiment 31 indexing ----------

def test_exp31_design_indexing():
    rows = S.labeled_rows31()
    assert len(rows) == 160 and sum(r["cross_model"] for r in rows) == 80 and len({r["row_id"] for r in rows}) == 160
    for r in rows:
        x = C.REFERENCES[(r["source_model"], r["source_mode"])]
        assert r["forced_prefix"] == S.seq(x[:r["position"] - 1]) and r["authentic_face"] == x[r["position"] - 1]
        assert (r["forced_prefix"] == "") == (r["position"] == 1)
    assert sum(r["replay_kind"].endswith("replay") for r in rows) == 40
    ctx = {}
    for r in rows:
        ctx.setdefault(r["context_key"], []).append(r)
    # F sources share "3 1" under the same scorer/instruction: positions 1-3 contexts are shared across Qwen F and Mistral F
    shared = [k for k, v in ctx.items() if {x["source_id"] for x in v} >= {"qwen-F", "mistral-F"}]
    assert {k.split("|")[2] for k in shared} == {"[]", "[3]", "[3 1]"}
    assert len(ctx) == 140


def test_remaining_face_heuristic():
    x = C.REFERENCES[("qwen", "G")]                                              # 5 2 6 3 1 4 6 2 5 3
    assert S.remaining_faces(x, 1) == ("opening", None)
    assert S.remaining_faces(x, 2) == ("first_block", [1, 2, 3, 4, 6])
    assert S.remaining_faces(x, 6) == ("first_block", [4])                       # one left: uninformative by construction
    assert S.remaining_faces(x, 7) == ("reset_at_7", [1, 2, 3, 4, 5, 6])
    assert S.remaining_faces(x, 9) == ("reset_at_7", [1, 3, 4, 5])
    assert S.remaining_faces((1, 1, 2, 3, 4, 5, 6, 1, 2, 3), 8) == ("ambiguous_omitted", None)


# ---------- 3. scoring helpers ----------

def test_dist_and_js():
    lp = {str(f): math.log(v) for f, v in zip(C.FACES, [0.4, 0.2, 0.1, 0.1, 0.05, 0.05])}
    d = A.dist(lp)
    assert abs(sum(d["p"]) - 1) < 1e-12 and abs(d["mass"] - 0.9) < 1e-12 and d["top"] == 1 and A.rank_of(d["p"], 3) == 3
    assert js_bits(d["p"], d["p"]) == 0 and abs(js_bits([1, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0]) - 1) < 1e-12


# ---------- tiny torch engine (real Engine code paths on CPU) ----------

class TinyModel:
    """Deterministic logits from the full token prefix; a policy that answers digits for prediction prompts (two faces when the
    prompt asks for two, prose first when `prose`)."""

    V = 1100

    def __init__(self, eng, prose=False):
        self.e, self.prose = eng, prose

    def _logits(self, ids):
        h = hashlib.sha256(",".join(map(str, ids)).encode()).digest()
        g = torch.Generator().manual_seed(int.from_bytes(h[:8], "little"))
        z = torch.randn(self.V, generator=g) * 2
        e, last = self.e, ids[-1]
        faces, sep, eos = list(e.face_ids.values()), C.SEPARATOR_ID[e.key], next(iter(e.eos))
        p_end = ids.index(999) if 999 in ids else len(ids) - 1
        gen = ids[p_end + 1:]
        nf = sum(t in faces for t in gen)
        want = 2 if e.last_prompt_wants_two else 1
        if self.prose and not gen:
            z[700] += 30
        elif last in (999, sep, 700):
            for f in faces:
                z[f] += 20
        elif last in faces:
            z[sep if nf < want else eos] += 30
        return z

    def __call__(self, input_ids, past_key_values=None, use_cache=True):
        ids = (past_key_values or []) + input_ids[0].tolist()
        start = len(past_key_values or [])
        lg = torch.stack([self._logits(ids[:k + 1]) for k in range(start, len(ids))])
        return types.SimpleNamespace(logits=lg.unsqueeze(0), past_key_values=ids)


class TinyEngine(Engine):
    device = "cpu"

    def __init__(self, key, prose=False):
        self.key, self.model_id, self.commit = key, C.MODEL[key]["model_id"], C.MODEL[key]["revision"]
        self.face_ids = dict(C.MODEL[key]["face_ids"])
        self.eos = {2}
        self.inv = {v: k for k, v in self.face_ids.items()}
        self.last_prompt_wants_two = False
        self.model = TinyModel(self, prose)

    def prompt_ids(self, prompt):
        self.last_prompt_wants_two = "rolls 6 and 7" in prompt
        return [100 + ord(c) % 500 for c in prompt[-120:]] + [999]

    def hist_ids(self, text):
        return [C.SEPARATOR_ID[self.key] if ch == " " else self.face_ids[int(ch)] for ch in text]

    def decode(self, ids):
        return "".join(" " if i == C.SEPARATOR_ID[self.key] else str(self.inv[i]) if i in self.inv else "x" for i in ids)

    def rendered_text(self, prompt):
        return "<u>" + prompt + "</u><a>"

    def env_common(self):
        return dict(max_memory_allocated_gb=0.0)


def _data31(engs):
    return {e.key: dict(streams=G.exp31(e), archival=[]) for e in engs}


def test_exp31_end_to_end_tiny_engine():
    engs = [TinyEngine("qwen"), TinyEngine("mistral")]
    data = _data31(engs)
    streams = [s for d in data.values() for s in d["streams"]]
    assert len(streams) == 48
    rows = A.rows31(data)
    assert len(rows) == 160 and all(r["rep2_identical"] for r in rows) and max(r["floor_max_dp"] for r in rows) < 1e-6
    for s in streams:
        for p in s["positions"]:                                                  # position j sees exactly j-1 forced faces
            assert p["n_forced"] == 2 * (p["position"] - 1)
            assert p["forced_ids"] == s["history_ids"][:p["n_forced"]]
            assert s["history_ids"][p["n_forced"]] == C.MODEL[s["scorer_model"]]["face_ids"][p["authentic_face"]]
    cc = A.context_check(rows)
    assert cc["unique_contexts"] == 140 and not cc["mismatched_contexts"]
    # the archival-equivalence index finds the 80 within-model rows (Exp 28) + 24 cross rows with matching instruction (Exp 30)
    assert sum(bool(r["archival_equivalents"]) for r in rows) == 104
    cr = A.crossed31(rows)
    assert len(cr) == 8 and sum(c["own_cell_is_replay"] for c in cr) == 4
    rc = A.reciprocal31(cr)
    assert len(rc) == 4
    js = A.js31(rows)
    assert len(js["between"]) == 80 and len(js["within"]) == 80
    assert all(0 <= x["js_bits"] <= 1 for x in js["between"])
    h = A.heuristic31(rows)
    assert len(h) == 16 and all(x["n_uninformative_one_left"] == 1 for x in h)     # position 6 only


def test_exp32_end_to_end_tiny_engine():
    q, m = TinyEngine("qwen"), TinyEngine("mistral", prose=True)
    data = {"qwen": G.exp32(q), "mistral": G.exp32(m)}
    cells = A.cells32(data)
    assert len(cells) == 12 and all(c["replicates_identical"] for c in cells) and all(c["first_boundary_matches_generation"] for c in cells)
    qa = next(c for c in cells if c["cell_id"] == "qwen<-qwen-G-A")
    assert qa["free_strict_valid"] and qa["free_roll7_defined"] and qa["constrained_equals_free"]
    rec = next(r for r in data["qwen"] if r["prompt_id"] == "qwen-G-A" and r["replicate"] == 1)
    assert rec["free_roll7"]["forced_ids"] == rec["free"]["generated_ids"][:2]           # roll 7 after the predicted sixth
    assert rec["free_roll7"]["generated_sixth"] == qa["generated_sixth"] == int(rec["free"]["content"][0])
    ma = next(c for c in cells if c["cell_id"] == "mistral<-qwen-G-A")
    assert not ma["free_strict_valid"] and not ma["free_roll7_defined"] and ma["p_true7"] is None
    assert ma["constrained_p_true7"] is not None                                    # labelled constrained readout still available
    qb = next(c for c in cells if c["cell_id"] == "qwen<-qwen-G-B")
    assert qb["free_strict_valid"] and qb["p_true7"] is not None
    con = A.contrasts32(cells)
    assert len(con) == 4
    for c in con:
        if c["p_true7_A"] is not None:
            assert abs(c["A_minus_B"] - round(c["p_true7_A"] - c["p_true7_B"], 4)) < 2e-4


# ---------- real tokenizers (local cache only) ----------

def test_real_tokenizers_history_and_boundary():
    try:
        from huggingface_hub import hf_hub_download
        from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
        from transformers import AutoTokenizer
        qt = AutoTokenizer.from_pretrained(C.MODEL["qwen"]["model_id"], revision=C.MODEL["qwen"]["revision"], local_files_only=True)
        tp = hf_hub_download(C.MODEL["mistral"]["model_id"], "tekken.json", revision=C.MODEL["mistral"]["revision"], local_files_only=True)
    except Exception as e:
        pytest.skip(f"tokenizer files not cached: {e}")
    mt = MistralTokenizer.from_file(tp).instruct_tokenizer.tokenizer
    enc = {"qwen": lambda s: qt(s, add_special_tokens=False).input_ids, "mistral": lambda s: mt.encode(s, bos=False, eos=False)}
    for key, e in enc.items():
        fid, sep = C.MODEL[key]["face_ids"], C.SEPARATOR_ID[key]
        for x in C.REFERENCES.values():
            ids = e(S.seq(x))
            assert ids[0::2] == [fid[f] for f in x] and set(ids[1::2]) == {sep}     # face, space, face ... no merged tokens
        assert all(e(str(f)) == [fid[f]] for f in C.FACES)
        assert all(e(" " + str(f)) == [sep, fid[f]] for f in C.FACES)               # no " d" variant: post-space digits are bare
        assert all(e(f"{a} {b}") == [fid[a], sep, fid[b]] for a in C.FACES for b in C.FACES)   # condition A answer format
    r = qt.apply_chat_template([{"role": "user", "content": S.SOURCE_INSTRUCTION["G"]}], tokenize=False, add_generation_prompt=True,
                               enable_thinking=False)
    assert r.endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n")               # first face follows the empty think block
