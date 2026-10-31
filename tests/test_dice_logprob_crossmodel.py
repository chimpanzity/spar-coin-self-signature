"""Offline tests for SPAR_DICE_LOGPROB_CROSSMODEL_v2.0 (no GPU, no API).

A fake engine with a deterministic toy policy stands in for the GPU engine, so the stage runner, gates and analysis run end to
end on CPU. Tokenizer facts are checked against the real pinned tokenizer files when they are in the local HF cache.
"""

import hashlib
import json
import math
import random

import pytest

from spar_dynamic.dice_logprob import prompts as P21
from spar_dynamic.dice_logprob_crossmodel import analysis as A
from spar_dynamic.dice_logprob_crossmodel import config as C
from spar_dynamic.dice_logprob_crossmodel import gates as Gt
from spar_dynamic.dice_logprob_crossmodel import gpu
from spar_dynamic.dice_logprob_crossmodel import prompts as P
from spar_dynamic.dice_crossed_guidance.analysis import js_bits, read_jsonl, six


# ---------- prompts ----------

def test_fifteen_conditions_and_positions():
    cs = P.conditions()
    assert [c["condition"] for c in cs] == ["G", "F"] + [f"S{k}" for k in range(1, 11)] + ["W1-5", "W3-7", "W6-10"]
    assert {c["condition"]: c["positions"] for c in cs if c["condition_type"] == "W"} == \
        {"W1-5": [1, 2, 3, 4, 5], "W3-7": [3, 4, 5, 6, 7], "W6-10": [6, 7, 8, 9, 10]}
    assert all(c["n_expected"] == len(c["positions"]) for c in cs)
    assert len({c["prompt_sha256"] for c in cs}) == 15


def test_window_template_reproduces_experiment21_byte_for_byte():
    for a, b in P21.WINDOWS:
        assert P.prompt_w(a, b) == P21.prompt_w(a, b)


def test_prompts_identical_to_archived_experiment21_records():
    arch = {r["condition"]: r["prompt_sha256"] for r in read_jsonl(C.EXP21 / "raw_attempts.jsonl")}
    ours = {c["condition"]: c["prompt_sha256"] for c in P.conditions()}
    shared = ["G", "F", "W1-5"] + [f"S{k}" for k in range(1, 11)]
    assert all(ours[k] == arch[k] for k in shared)
    assert ours["G"] == "edc7a4a228d493e83a5086181c170aa052e3e7cb8b34b9911ef4dc8147fdb8fe"
    assert ours["W3-7"] not in arch.values() and ours["W6-10"] not in arch.values()


def test_prompt_text_keeps_framing_and_embedded_instruction():
    for c in P.conditions():
        if c["condition"] == "G":
            assert c["prompt"] == P.GEN
            continue
        assert c["prompt"].count("another instance of your model") == 1
        assert c["prompt"].split("\n\n")[1] == P.GEN
    w = P.by_id()["W6-10"]["prompt"]
    assert "positions 6 through 10, inclusive" in w and "Return exactly 5 integers" in w


def test_frozen_files_match_code_if_frozen():
    if not (C.EXP / "inputs_sha256.json").exists():
        pytest.skip("not frozen yet")
    from spar_dynamic.dice_logprob_crossmodel.__main__ import verify_frozen
    verify_frozen()


# ---------- metrics ----------

def test_js_six_and_normalisation():
    lp = {str(f): math.log(p) for f, p in zip(C.FACES, [0.5, 0.2, 0.1, 0.1, 0.05, 0.03])}
    p, mass = six(lp)
    assert abs(sum(p) - 1) < 1e-12 and abs(mass - 0.98) < 1e-12 and abs(p[0] - 0.5 / 0.98) < 1e-12
    assert js_bits(p, p) == 0.0
    assert abs(js_bits([1, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0]) - 1.0) < 1e-12


def test_best_shift_and_structure():
    g, f = [5, 2, 6, 3, 1, 4, 6, 2, 5, 3], [3, 1, 4, 6, 2, 5, 3, 2, 6, 4]
    bs = A.best_shift(g, f)
    assert bs["shift"] == -3 and bs["matches_at_shift"] == 7 and bs["longest_common_run"] == 7 and bs["run_start_a_b"] == (4, 1)
    s = A.structure(g)
    assert s["first6_is_permutation"] and s["adjacent_repeats"] == 0 and not s["distinct_in_every_6_window"]   # 2 6 3 1 4 6
    assert A.structure([1, 2, 3, 4, 5, 6, 1, 2, 3, 4])["distinct_in_every_6_window"]


# ---------- fake engine ----------

class FakeTok:
    def __init__(self, face_ids, sep):
        self.map = {v: str(k) for k, v in face_ids.items()}
        self.map[sep] = " "

    def __len__(self):
        return 300 if max(self.map) < 300 else 1100

    def decode(self, ids):
        return "".join(self.map.get(i, f"<x{i}>") for i in ids)


class FakeEngine:
    """Toy policy: face log-probs from a hash of (prompt, history text); 2% mass on non-face tokens."""

    def __init__(self, key, prose=(), wobble=0.0):
        self.key, self.prose, self.wobble = key, set(prose), wobble
        spec = C.MODEL[key]
        self.model_id, self.commit = spec["model_id"], spec["revision"]
        self.face_ids = dict(spec["face_ids"])
        self.sep = C.SEPARATOR_ID[key]
        self.eos = {2}
        tok = FakeTok(self.face_ids, self.sep)
        if key == "qwen":
            self.tok = tok
        else:
            tok.n_words, tok.num_special_tokens = 1100, 1000
            self.t = tok
        self.inv = {v: k for k, v in self.face_ids.items()}

    def _lp(self, prompt, prefix, full=False):
        h = hashlib.sha256((prompt + "|" + prefix).encode()).digest()
        w = [1 + h[i] for i in range(6)]
        z = sum(w)
        lp = {str(f): math.log(0.98 * w[i] / z) + (1e-3 * (h[6] % 3) if full else 0.0) for i, f in enumerate(C.FACES)}
        return lp

    def rendered_text(self, prompt):
        return ("<|im_start|>user\n" + prompt + "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n") if self.key == "qwen" \
            else "<s>[INST]" + prompt + "[/INST]"

    def hist_ids(self, text):
        out = []
        for ch in text:
            if ch == " ":
                out.append(self.sep)
            elif ch in "123456":
                out.append(self.face_ids[int(ch)])
            else:
                out.append(500 + ord(ch) % 50)
        return out

    def decode(self, ids):
        return "".join(" " if i == self.sep else str(self.inv[i]) if i in self.inv else "x" for i in ids)

    def _n(self, prompt):
        return next(c["n_expected"] for c in P.conditions() if c["prompt"] == prompt)

    def generate(self, prompt, temperature=None, seed=None):
        n = self._n(prompt)
        cond = next(c["condition"] for c in P.conditions() if c["prompt"] == prompt)
        steps, gen, prefix = [], [], ""
        if cond in self.prose:                            # prose answer: a word token first, then digits, then the cap
            for t in [510, self.sep]:
                steps.append(dict(token="x", token_id=t, logprob=-0.1, face_logprobs=self._lp(prompt, prefix + "x"), top5=[], entropy_bits=1.0))
                gen.append(t)
                prefix += self.decode([t])
        for j in range(n):
            lp = self._lp(prompt, prefix)
            if self.wobble:
                lp = {k: v + random.random() * self.wobble for k, v in lp.items()}
            f = max(C.FACES, key=lambda x: lp[str(x)])
            tid = self.face_ids[f]
            steps.append(dict(token=str(f), token_id=tid, logprob=lp[str(f)], face_logprobs=lp, top5=[], entropy_bits=1.0))
            gen.append(tid)
            prefix += str(f)
            if j < n - 1:
                steps.append(dict(token=" ", token_id=self.sep, logprob=-0.01, face_logprobs=self._lp(prompt, prefix + "_"), top5=[], entropy_bits=0.1))
                gen.append(self.sep)
                prefix += " "
        steps.append(dict(token="", token_id=2, logprob=-0.01, face_logprobs=self._lp(prompt, prefix + "$"), top5=[], entropy_bits=0.1))
        return dict(prompt_tokens=10, rendered_prompt_sha256=P.sha256(self.rendered_text(prompt)), completion_tokens=len(gen),
                    generated_ids=gen, content=self.decode(gen), finish_reason="stop", steps=steps,
                    digit_steps=[s for s in steps if s["token_id"] in self.face_ids.values()], temperature=None, seed=None, latency_ms=5)

    def score(self, prompt, history, method="incremental"):
        rows, k = [], 0
        for i, ch in enumerate(history):
            if ch in "123456":
                k += 1
                rows.append(dict(method=method, position=k, history_face=int(ch),
                                 face_logprobs=self._lp(prompt, history[:i], method == "full_pass"), argmax_token_id=0, argmax_logprob=0.0))
        return rows

    def env_common(self):
        return dict(max_memory_allocated_gb=0.0)

    def env(self):
        e = dict(key=self.key, model_id=self.model_id, model_commit=self.commit, gpu="fake", driver="fake", cuda="fake",
                 torch="fake", transformers="fake", face_ids=self.face_ids, eos_ids=[2], max_memory_allocated_gb=0.0)
        if self.key == "qwen":
            e["chat_template_sha256"] = C.QWEN_CHAT_TEMPLATE_SHA256
        else:
            e.update(tekken_sha256=C.MISTRAL_TEKKEN_SHA256, mistral_common="fake")
        return e


@pytest.fixture
def fake_runs(tmp_path):
    out = {}
    for key in C.MODELS:
        pre, main = tmp_path / "preflight" / key, tmp_path / "main" / key
        pre.mkdir(parents=True)
        main.mkdir(parents=True)
        gpu.preflight(FakeEngine(key), str(pre))
        out[key] = (pre, main)
    return out


def _pass_gate(tmp_path, key, pre):
    res = Gt.preflight_gates(key, pre)
    p = tmp_path / f"gate_{key}.json"
    json.dump(dict(res, overall="PASS"), open(p, "w"))      # the fake cannot pass the archival regression; see its own test
    return res, p


def test_preflight_gates_on_fake_engine(fake_runs, tmp_path):
    for key, (pre, _) in fake_runs.items():
        res = Gt.preflight_gates(key, pre)
        failed = {k for k, v in res["gates"].items() if v["status"] == "FAIL"}
        assert failed == {"archival_regression"}, (key, failed, {k: res["gates"][k] for k in failed})
        assert res["overall"] == "FAIL"
        raw = read_jsonl(pre / "raw_attempts.jsonl")
        assert sorted(r["condition"] for r in raw).count("G") == C.PREFLIGHT_REPEATS and len(raw) == 19
        assert res["gates"]["numerical_floor"]["detail"]["max_abs_dp_incremental_vs_full_pass"] > 0


def test_main_full_run_resume_checks_and_analysis(fake_runs, tmp_path):
    res = {}
    for key, (pre, main) in fake_runs.items():
        _, gate = _pass_gate(tmp_path, key, pre)
        gpu.check_gate(str(gate), key)
        eng = FakeEngine(key)
        # interrupted run: write the first 37 jobs, then resume
        orig = eng.generate
        calls = {"n": 0}

        def flaky(prompt, *a, **k):
            calls["n"] += 1
            if calls["n"] > 37:
                raise KeyboardInterrupt
            return orig(prompt, *a, **k)
        eng.generate = flaky
        with pytest.raises(KeyboardInterrupt):
            gpu.main(eng, str(main), str(gate))
        assert len(read_jsonl(main / "raw_attempts.jsonl")) == 37
        gpu.main(FakeEngine(key), str(main), str(gate))
        raw = read_jsonl(main / "raw_attempts.jsonl")
        assert len(raw) == 15 * C.N_REPLICATES and len({r["trial_id"] for r in raw}) == len(raw)
        order = [(r["condition"], r["replicate"]) for r in sorted(raw, key=lambda r: r["order_index"])]
        jobs = [(k, i) for k in P.by_id() for i in range(1, C.N_REPLICATES + 1)]
        random.Random(C.ORDER_SEED[key]).shuffle(jobs)
        assert order == jobs
        assert sum(r["rescored_subset"] for r in raw) == 15            # deterministic: one distinct output per condition
        chk = Gt.main_checks(key, main, pre)
        assert chk["overall"] == "PASS", {k: v for k, v in chk["gates"].items() if v["status"] == "FAIL"}
        res[key] = A.analyse_model(A.load(key, main))
    for key, r in res.items():
        nat = r["natural"]["rows"]
        assert [x["position"] for x in nat] == list(range(1, 11)) and nat[0]["same_history"]
        # matched prefix: the G row on G's history is the natural G trajectory
        g_on_g = {x["position"]: x for x in r["matched"]["rows"] if x["history"] == "G"}
        assert all(g_on_g[k]["G_top"] == nat[k - 1]["G_face"] for k in range(1, 11))
        w = {x["window"] for x in r["windows"]["rows"]}
        assert w == {"W1-5", "W3-7", "W6-10"} and len(r["windows"]["rows"]) == 15
        assert [(o["pair"], o["position"]) for o in r["windows"]["overlaps"]] == \
            [("W1-5 vs W3-7", 3), ("W1-5 vs W3-7", 4), ("W1-5 vs W3-7", 5), ("W3-7 vs W6-10", 6), ("W3-7 vs W6-10", 7)]
        # window rows are at original serial positions
        assert [x["position"] for x in r["windows"]["rows"] if x["window"] == "W6-10"] == [6, 7, 8, 9, 10]
        assert len(r["singles"]["rows"]) == 10
    table = A.cross_model(res)
    assert all(set(t) == {"metric", "qwen", "mistral"} for t in table)
    from spar_dynamic.dice_logprob_crossmodel.figures import all_figures
    all_figures(res, tmp_path / "figures")
    assert len(list((tmp_path / "figures").glob("fig*.png"))) == 4 and len(list((tmp_path / "figures").glob("fig*.pdf"))) == 4


def test_main_refuses_without_pass_gate_and_on_drift(fake_runs, tmp_path):
    key = "qwen"
    pre, main = fake_runs[key]
    res = Gt.preflight_gates(key, pre)
    bad = tmp_path / "bad.json"
    json.dump(res, open(bad, "w"))                                   # overall FAIL
    with pytest.raises(SystemExit):
        gpu.check_gate(str(bad), key)
    _, gate = _pass_gate(tmp_path, key, pre)
    with pytest.raises(SystemExit):
        gpu.check_gate(str(gate), "mistral")
    # prompt drift in an existing partial file stops the resume
    rec = read_jsonl(pre / "raw_attempts.jsonl")[0]
    rec["prompt_sha256"] = "0" * 64
    (main / "raw_attempts.jsonl").write_text(json.dumps(rec) + "\n")
    with pytest.raises(SystemExit):
        gpu.main(FakeEngine(key), str(main), str(gate))


def test_tamper_detection_on_main_files(fake_runs, tmp_path):
    key = "mistral"
    pre, main = fake_runs[key]
    _, gate = _pass_gate(tmp_path, key, pre)
    gpu.main(FakeEngine(key), str(main), str(gate))
    assert Gt.main_checks(key, main, pre)["gates"]["raw_files_untampered"]["status"] == "PASS"
    lines = (main / "raw_attempts.jsonl").read_text().splitlines()
    r = json.loads(lines[5])
    r["latency_ms"] += 1
    lines[5] = json.dumps(r)
    (main / "raw_attempts.jsonl").write_text("\n".join(lines) + "\n")
    assert Gt.main_checks(key, main, pre)["gates"]["raw_files_untampered"]["status"] == "FAIL"


def test_preflight_refuses_to_append(fake_runs):
    pre, _ = fake_runs["qwen"]
    with pytest.raises(SystemExit):
        gpu.preflight(FakeEngine("qwen"), str(pre))


def test_prose_outputs_fail_format_gate_but_are_never_scored_as_faces(tmp_path):
    pre = tmp_path / "pre"
    pre.mkdir()
    gpu.preflight(FakeEngine("mistral", prose={"S3", "W3-7"}), str(pre))
    res = Gt.preflight_gates("mistral", pre)
    assert res["gates"]["format_all_conditions"]["status"] == "FAIL"
    assert res["gates"]["format_references"]["status"] == "PASS"
    raw = read_jsonl(pre / "raw_attempts.jsonl")
    s3 = next(r for r in raw if r["condition"] == "S3")
    assert not s3["rescore_tokens_equal"] and "own_rescored" not in s3      # prose is not re-encoded as faces
    # analysis maps no free positions for an invalid output, but keeps its first-token distribution (labelled)
    m = A.modal(dict(model="mistral", raw=raw, mp=[]))
    fp = A.free_positions(m)
    assert m["S3"]["valid"] is False and fp["S3"]["rows"] == {} and fp["S3"]["first_token_is_face"] is False
    assert fp["W3-7"]["rows"] == {}


def test_nondeterministic_references_fail(tmp_path):
    pre = tmp_path / "pre"
    pre.mkdir()
    random.seed(1)
    try:
        gpu.preflight(FakeEngine("qwen", wobble=0.5), str(pre))
    except SystemExit:
        return                                                  # references not single -> matched prefix refused
    res = Gt.preflight_gates("qwen", pre)
    assert res["gates"]["determinism"]["status"] == "FAIL"


def test_guard_refuses_frozen_folders():
    with pytest.raises(SystemExit):
        gpu.guard_out(str(C.EXP21))
    with pytest.raises(SystemExit):
        gpu.guard_out(str(C.EXP27_PRE / "qwen"))
    gpu.guard_out(str(C.EXP / "preflight" / "qwen"))


def test_archival_regression_passes_on_archived_records(tmp_path):
    """Feed the archived Experiment 21 Qwen records (converted to this engine's schema) through the regression gate."""
    arc = Gt.archive21()
    raw, mp = [], []
    for k, a in arc["gen"].items():
        if k in P.by_id():
            raw.append(dict(condition=k, prompt_sha256=a["prompt_sha256"], content=a["content"],
                            digit_steps=[dict(face_logprobs=s["bare"]) for s in a["steps"]]))
    for (x, h, method, pos), lp in arc["mp"].items():
        mp.append(dict(kind="mp", instruction=x, history=h, method=method, position=pos, face_logprobs=lp["bare"]))
    g = Gt._regression("qwen", raw, mp)
    assert g["status"] == "PASS", g["detail"]
    raw[0]["content"] = "1 1 1"
    assert Gt._regression("qwen", raw, mp)["status"] == "FAIL"


# ---------- real tokenizers (local HF cache only; skipped otherwise) ----------

def test_real_tokenizers_face_tokens():
    try:
        from huggingface_hub import hf_hub_download
        from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
        from transformers import AutoTokenizer
        q = AutoTokenizer.from_pretrained(C.MODEL["qwen"]["model_id"], revision=C.MODEL["qwen"]["revision"], local_files_only=True)
        tp = hf_hub_download(C.MODEL["mistral"]["model_id"], "tekken.json", revision=C.MODEL["mistral"]["revision"], local_files_only=True)
    except Exception as e:
        pytest.skip(f"tokenizer files not cached: {e}")
    assert hashlib.sha256(open(tp, "rb").read()).hexdigest() == C.MISTRAL_TEKKEN_SHA256
    t = MistralTokenizer.from_file(tp).instruct_tokenizer.tokenizer
    enc = {"qwen": lambda s: q(s, add_special_tokens=False).input_ids, "mistral": lambda s: t.encode(s, bos=False, eos=False)}
    for key, e in enc.items():
        fid = C.MODEL[key]["face_ids"]
        ids = e("5 2 6 3 1 4 6 2 5 3")
        assert ids[0::2] == [fid[f] for f in (5, 2, 6, 3, 1, 4, 6, 2, 5, 3)] and set(ids[1::2]) == {C.SEPARATOR_ID[key]}
        assert all(e(str(f)) == [fid[f]] for f in C.FACES)
        assert all(e(" " + str(f)) == [C.SEPARATOR_ID[key], fid[f]] for f in C.FACES)
