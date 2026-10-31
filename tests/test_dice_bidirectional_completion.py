"""Offline tests for SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1 (no GPU, no API).

A fake engine with a deterministic toy policy stands in for the GPU engine, so the stage runner, gates and analysis run end to
end on CPU.
"""

import hashlib
import json
import math
import random
import re

import pytest

from spar_dynamic.dice_bidirectional_completion import analysis as A
from spar_dynamic.dice_bidirectional_completion import config as C
from spar_dynamic.dice_bidirectional_completion import gates as Gt
from spar_dynamic.dice_bidirectional_completion import gpu
from spar_dynamic.dice_bidirectional_completion import prompts as P
from spar_dynamic.dice_crossed_guidance.analysis import read_jsonl, six
from spar_dynamic.dice_logprob_crossmodel import prompts as P28


# ---------- design ----------

def test_references_equal_experiment28_raw_records():
    v = Gt.verify_references()
    assert v["ok"], v["detail"]
    assert {k: P.seq(r) for k, r in C.REFERENCES.items()} == {
        ("qwen", "G"): "5 2 6 3 1 4 6 2 5 3", ("qwen", "F"): "3 1 4 6 2 5 3 2 6 4",
        ("mistral", "G"): "4 2 6 1 3 5 2 4 6 1", ("mistral", "F"): "3 1 5 2 6 4 3 1 5 2"}


def test_counts():
    cs, pc = P.conditions(), P.prompt_cells()
    assert len(cs) == 152 and sum(c["task_type"] == "primary" for c in cs) == 144 and sum(c["task_type"] == "middle" for c in cs) == 8
    assert len(pc) == 76 and len({c["cell_id"] for c in cs}) == 152
    assert sum(c["n_missing"] for c in cs) == 752 and sum(c["n_missing"] for c in cs if c["task_type"] == "primary") == 720
    assert len(cs) * C.N_REPLICATES == 456
    assert sum(len(P.preflight_cells(m)) for m in C.MODELS) == 56
    for m in C.MODELS:
        assert sum(c["n_missing"] for c in cs if c["predictor"] == m and c["task_type"] == "primary") == 360


def test_paired_prompts_identical_and_documented_duplicates():
    by = {}
    for c in P.conditions():
        by.setdefault(c["prompt_id"], set()).add(c["prompt"])
    assert all(len(v) == 1 for v in by.values()) and len(by) == 76
    # Qwen F and Mistral F share rolls 1-2, so forward k=1, 2 under F render identical bytes (documented in the protocol)
    dup = {}
    for c in P.prompt_cells():
        dup.setdefault(c["prompt_sha256"], []).append(c["prompt_id"])
    assert sorted(v for v in dup.values() if len(v) > 1) == [["qwen-F-fwd1", "mistral-F-fwd1"], ["qwen-F-fwd2", "mistral-F-fwd2"]]
    assert len(dup) == 74


def test_indices_all_k_and_boundaries():
    for k in C.KS:
        rev, miss = P.split("forward", k)
        assert rev == list(range(1, k + 1)) and miss == list(range(k + 1, 11))
        rev, miss = P.split("backward", k)
        assert rev == list(range(11 - k, 11)) and miss == list(range(1, 11 - k))
    assert P.split("middle", None) == ([3, 4, 5, 6, 7, 8], [1, 2, 9, 10])
    d = {c["prompt_id"]: c for c in P.prompt_cells()}
    assert d["qwen-G-fwd3"]["target"] == "3 1 4 6 2 5 3" and d["qwen-G-fwd9"]["target"] == "3"
    assert d["qwen-G-bwd1"]["target"] == "5 2 6 3 1 4 6 2 5" and d["qwen-G-bwd3"]["target"] == "5 2 6 3 1 4 6"
    assert d["qwen-G-bwd9"]["revealed_values"] == [2, 6, 3, 1, 4, 6, 2, 5, 3] and d["qwen-G-bwd9"]["target"] == "5"
    assert d["qwen-G-mid"]["revealed_values"] == [6, 3, 1, 4, 6, 2] and d["qwen-G-mid"]["target"] == "5 2 5 3"
    assert "positions 1 through 1, were: 5" in d["qwen-G-fwd1"]["prompt"]
    assert "Return exactly 1 integers" in d["qwen-G-fwd9"]["prompt"]          # frozen template wording for k = 9


def test_wrapper_bytes_source_instruction_and_no_leakage():
    for c in P.prompt_cells():
        p = c["prompt"]
        inner = p.split("<ORIGINAL INSTRUCTION>\n")[1].split("\n</ORIGINAL INSTRUCTION>")[0]
        assert inner == P28.by_id()[c["source_instruction"]]["prompt"]
        assert not any(w in p.lower() for w in ("qwen", "mistral", "alibaba"))
        revealed = p.split("<REVEALED>\n")[1].split("\n</REVEALED>")[0]
        assert re.findall(r"[1-6](?: [1-6])*$", revealed)[0] == P.seq(c["revealed_values"])
        assert p.endswith("with no other text.") and not p.endswith("\n")
        assert p.startswith("A language-model instance received the following instruction:\n\n<ORIGINAL INSTRUCTION>\n")
    f = P.SOURCE_INSTRUCTION["F"]
    assert "another instance of your model" in f and f == P28.by_id()["F"]["prompt"]
    assert P.sha256(P.SOURCE_INSTRUCTION["G"]) == "edc7a4a228d493e83a5086181c170aa052e3e7cb8b34b9911ef4dc8147fdb8fe"
    assert P.sha256(f) == "8adcaddfff0d9acee6bcc9060917175e7d68167f440c42b00a3800cd32dcef03"


def test_frozen_files_match_code_if_frozen():
    if not (C.EXP / "inputs_sha256.json").exists():
        pytest.skip("not frozen yet")
    from spar_dynamic.dice_bidirectional_completion.__main__ import verify_frozen
    verify_frozen()


# ---------- metrics ----------

def test_contrast_arithmetic_and_loss():
    L = {("qwen", "qwen"): 1.0, ("qwen", "mistral"): 1.5, ("mistral", "qwen"): 2.0, ("mistral", "mistral"): 1.2}
    c = A.contrast(L)
    assert c["self_advantage"] == round((1.5 + 2.0 - 1.0 - 1.2) / 2, 4) == 0.65
    assert c["qwen_self_minus_other"] == -0.5 and c["mistral_self_minus_other"] == -0.8
    lp = {str(f): math.log(v) for f, v in zip(C.FACES, [0.4, 0.2, 0.1, 0.1, 0.05, 0.05])}
    p, mass = six(lp)
    assert abs(sum(p) - 1) < 1e-12 and abs(mass - 0.9) < 1e-12 and abs(-math.log(p[0]) - -math.log(0.4 / 0.9)) < 1e-12


# ---------- fake engine ----------

class FakeTok:
    def __init__(self, face_ids, sep, n):
        self.map = {v: str(k) for k, v in face_ids.items()}
        self.map[sep] = " "
        self.n = n

    def __len__(self):
        return self.n

    def decode(self, ids):
        return "".join(self.map.get(i, f"<x{i}>") for i in ids)


class FakeEngine:
    """Toy policy: face log-probs from a hash of (prompt, answer prefix); a prose answer for prompts in `prose`."""

    def __init__(self, key, prose=(), low_mass=False):
        spec = C.MODEL[key]
        self.key, self.model_id, self.commit = key, spec["model_id"], spec["revision"]
        self.face_ids, self.sep, self.eos = dict(spec["face_ids"]), C.SEPARATOR_ID[key], {2}
        self.inv = {v: k for k, v in self.face_ids.items()}
        self.prose, self.low_mass = set(prose), low_mass
        if key == "qwen":
            self.tok = FakeTok(self.face_ids, self.sep, 300)
        else:
            self.t = FakeTok(self.face_ids, self.sep, 1100)
            self.t.n_words, self.t.num_special_tokens = 1100, 1000

    def _lp(self, prompt, prefix, full=False):
        h = hashlib.sha256((prompt + "|" + prefix).encode()).digest()
        w = [1 + h[i] for i in range(6)]
        mass = 0.005 if self.low_mass else 0.98
        return {str(f): math.log(mass * w[i] / sum(w)) + (1e-3 * (h[6] % 3) if full else 0.0) for i, f in enumerate(C.FACES)}

    def rendered_text(self, prompt):
        return ("<|im_start|>user\n" + prompt + "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n") if self.key == "qwen" \
            else "<s>[INST]" + prompt + "[/INST]"

    def hist_ids(self, text):
        return [self.sep if ch == " " else self.face_ids[int(ch)] if ch in "123456" else 500 + ord(ch) % 50 for ch in text]

    def decode(self, ids):
        return "".join(" " if i == self.sep else str(self.inv[i]) if i in self.inv else "x" for i in ids)

    def _n(self, prompt):
        n = re.findall(r"Return exactly (\d+|four) integers", prompt)[-1]        # the wrapper's request, not the quoted instruction
        return 4 if n == "four" else int(n)

    def generate(self, prompt, temperature=None, seed=None):
        n = self._n(prompt)
        steps, gen, prefix = [], [], ""
        if P.sha256(prompt) in self.prose:
            for t in (510, self.sep):
                steps.append(dict(token="x", token_id=t, logprob=-0.1, face_logprobs=self._lp(prompt, prefix + "x"), top5=[], entropy_bits=1.0))
                gen.append(t)
                prefix += self.decode([t])
        for j in range(n):
            lp = self._lp(prompt, prefix)
            f = max(C.FACES, key=lambda x: lp[str(x)])
            steps.append(dict(token=str(f), token_id=self.face_ids[f], logprob=lp[str(f)], face_logprobs=lp, top5=[], entropy_bits=1.0))
            gen.append(self.face_ids[f])
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
        from spar_dynamic.dice_logprob_crossmodel import config as C28
        e = dict(key=self.key, model_id=self.model_id, model_commit=self.commit, gpu="fake", driver="fake", cuda="fake",
                 torch="fake", transformers="fake", face_ids=self.face_ids, eos_ids=[2], max_memory_allocated_gb=0.0)
        e.update(dict(chat_template_sha256=C28.QWEN_CHAT_TEMPLATE_SHA256) if self.key == "qwen" else
                 dict(tekken_sha256=C28.MISTRAL_TEKKEN_SHA256, mistral_common="fake"))
        return e


def _pass_gate(tmp_path, key, pre):
    res = Gt.preflight_gates(key, pre)
    p = tmp_path / f"gate_{key}.json"
    json.dump(dict(res, overall="PASS"), open(p, "w"))       # the fake cannot pass the archival regression (see its own test)
    return res, p


@pytest.fixture
def pre_runs(tmp_path):
    out = {}
    for key in C.MODELS:
        pre = tmp_path / "preflight" / key
        pre.mkdir(parents=True)
        gpu.run(FakeEngine(key), str(pre), "preflight")
        out[key] = pre
    return out


def test_preflight_on_fake_engine(pre_runs):
    for key, pre in pre_runs.items():
        res = Gt.preflight_gates(key, pre)
        failed = {k for k, v in res["gates"].items() if v["status"] == "FAIL"}
        assert failed == {"archival_regression"}, {k: res["gates"][k]["detail"] for k in failed}
        raw = read_jsonl(pre / "raw_attempts.jsonl")
        assert sum(r["kind"] == "cell" for r in raw) == 28 and sum(r["kind"] == "archival" for r in raw) == 4
        tf = read_jsonl(pre / "teacher_forced.jsonl")
        assert sum(x["method"] == "incremental" for x in tf) == sum(c["n_missing"] for c in P.preflight_cells(key))


def test_teacher_forcing_backward_order_and_prefixes(pre_runs):
    tf = [x for x in read_jsonl(pre_runs["qwen"] / "teacher_forced.jsonl") if x["method"] == "incremental"]
    bwd = sorted((x for x in tf if x["cell_id"] == "qwen<-qwen-G-bwd5"), key=lambda x: x["output_step"])
    assert [x["original_position"] for x in bwd] == [1, 2, 3, 4, 5]
    assert [x["true_face"] for x in bwd] == [5, 2, 6, 3, 1]
    assert [x["forced_prefix"] for x in bwd] == ["", "5", "5 2", "5 2 6", "5 2 6 3"]
    assert bwd[2]["forced_prefix_ids"] == [20, 220, 17, 220]               # faces and separators, Qwen ids
    mid = sorted((x for x in tf if x["cell_id"] == "qwen<-mistral-F-mid"), key=lambda x: x["output_step"])
    assert [x["original_position"] for x in mid] == [1, 2, 9, 10] and [x["true_face"] for x in mid] == [3, 1, 5, 2]
    assert mid[2]["forced_prefix"] == "3 1"                                  # positions 3-8 are never forced into the answer
    fwd = sorted((x for x in tf if x["cell_id"] == "qwen<-mistral-G-fwd5"), key=lambda x: x["output_step"])
    assert [x["original_position"] for x in fwd] == [6, 7, 8, 9, 10] and fwd[0]["forced_prefix"] == ""


def test_main_full_run_resume_checks_analysis_and_figures(pre_runs, tmp_path):
    datas = {}
    for key, pre in pre_runs.items():
        _, gate = _pass_gate(tmp_path, key, pre)
        gpu.check_gate(str(gate), key)
        main = tmp_path / "main" / key
        main.mkdir(parents=True)
        eng = FakeEngine(key)
        orig, calls = eng.generate, {"n": 0}

        def flaky(prompt, *a, **k):
            calls["n"] += 1
            if calls["n"] > 50:
                raise KeyboardInterrupt
            return orig(prompt, *a, **k)
        eng.generate = flaky
        with pytest.raises(KeyboardInterrupt):
            gpu.run(eng, str(main), "main", str(gate))
        assert len(read_jsonl(main / "raw_attempts.jsonl")) == 50
        gpu.run(FakeEngine(key), str(main), "main", str(gate))
        raw = read_jsonl(main / "raw_attempts.jsonl")
        assert sum(r["kind"] == "cell" for r in raw) == 228 and len({r["trial_id"] for r in raw}) == len(raw) == 232
        order = [(r["job"], r["replicate"]) for r in sorted(raw, key=lambda r: r["order_index"])]
        assert order == [tuple(j) for j in gpu.jobs_for(key, "main")]
        chk = Gt.main_checks(key, main)
        assert {k for k, v in chk["gates"].items() if v["status"] == "FAIL"} == {"archival_regression"}
        assert chk["gates"]["target_mapping"]["detail"]["incremental_rows"] == 376
        datas[key] = A.load(key, main)
    res = A.analyse(datas)
    assert len(res["positions"]) == 752 and len(res["cells"]) == 152
    assert all(c["free_all_valid"] for c in res["cells"])                    # the fake answers in the requested format
    assert len(res["crossed_mean"]) == 2 * 2 * 9 and len(res["crossed_avg_mean"]) == 4
    assert {(m["part"], m["source_instruction"]) for m in res["middle"]["contrasts"]} == \
        {(p, i) for p in ("early_1_2", "late_9_10", "all_four") for i in "GF"}
    # identical-prompt pairs give identical free outputs, different targets
    cl = {c["cell_id"]: c for c in res["cells"]}
    assert cl["qwen<-qwen-F-fwd1"]["free_output"] == cl["qwen<-mistral-F-fwd1"]["free_output"]
    assert cl["qwen<-qwen-F-fwd1"]["target"] != cl["qwen<-mistral-F-fwd1"]["target"]
    # source reference JS only labelled as a reference for forward cells
    assert all((x["source_ref_js"] is None) == (x["direction"] != "forward") for x in res["positions"])
    # cell mean loss is the equal-weighted mean of its positions
    c = cl["mistral<-qwen-G-bwd4"]
    xs = [x["cond_loss"] for x in res["positions"] if x["cell_id"] == "mistral<-qwen-G-bwd4"]
    assert len(xs) == 6 and abs(c["mean_loss"] - sum(xs) / 6) < 1e-12
    from spar_dynamic.dice_bidirectional_completion.figures import all_figures
    all_figures(res, tmp_path / "figures")
    assert len(list((tmp_path / "figures").glob("fig*.png"))) == 7


def test_resume_refuses_drift_and_preflight_refuses_append(pre_runs, tmp_path):
    pre = pre_runs["mistral"]
    with pytest.raises(SystemExit):
        gpu.run(FakeEngine("mistral"), str(pre), "preflight")
    _, gate = _pass_gate(tmp_path, "mistral", pre)
    main = tmp_path / "m2"
    main.mkdir()
    rec = next(r for r in read_jsonl(pre / "raw_attempts.jsonl") if r["kind"] == "cell")
    rec["prompt_sha256"] = "0" * 64
    (main / "raw_attempts.jsonl").write_text(json.dumps(rec) + "\n")
    with pytest.raises(SystemExit):
        gpu.run(FakeEngine("mistral"), str(main), "main", str(gate))
    bad = tmp_path / "bad.json"
    json.dump(Gt.preflight_gates("mistral", pre), open(bad, "w"))
    with pytest.raises(SystemExit):
        gpu.check_gate(str(bad), "mistral")


def test_tamper_detection(pre_runs, tmp_path):
    key = "qwen"
    _, gate = _pass_gate(tmp_path, key, pre_runs[key])
    main = tmp_path / "m3"
    main.mkdir()
    gpu.run(FakeEngine(key), str(main), "main", str(gate))
    assert Gt.main_checks(key, main)["gates"]["raw_files_untampered"]["status"] == "PASS"
    lines = (main / "teacher_forced.jsonl").read_text().splitlines()
    r = json.loads(lines[3])
    r["true_face"] = 7 - r["true_face"]
    lines[3] = json.dumps(r)
    (main / "teacher_forced.jsonl").write_text("\n".join(lines) + "\n")
    chk = Gt.main_checks(key, main)
    assert chk["gates"]["raw_files_untampered"]["status"] == "FAIL" and chk["gates"]["target_mapping"]["status"] == "FAIL"


def test_prose_is_invalid_never_scored_and_low_mass_stops(tmp_path):
    pc = {c["prompt_id"]: c for c in P.prompt_cells()}
    prose = {pc["qwen-G-bwd5"]["prompt_sha256"], pc["mistral-F-mid"]["prompt_sha256"]}
    pre = tmp_path / "p"
    pre.mkdir()
    gpu.run(FakeEngine("mistral", prose=prose), str(pre), "preflight")
    res = Gt.preflight_gates("mistral", pre)
    fm = res["info"]["format_reported_not_gated"]
    assert fm["mistral<-qwen-G-bwd5"]["valid"] == 0 and fm["mistral<-mistral-F-mid"]["valid"] == 0
    assert res["gates"]["scorer_matches_generation"]["status"] == "PASS"
    raw = read_jsonl(pre / "raw_attempts.jsonl")
    r = next(x for x in raw if x["job"] == "mistral<-qwen-G-bwd5")
    assert not r["rescore_tokens_equal"] and "own_rescored" not in r
    free = A.free_by_cell(dict(raw=raw))
    assert free["mistral<-qwen-G-bwd5"]["n_valid"] == 0 and free["mistral<-qwen-G-bwd5"]["first_token_is_face"] is False
    low = tmp_path / "low"
    low.mkdir()
    gpu.run(FakeEngine("qwen", low_mass=True), str(low), "preflight")
    assert Gt.preflight_gates("qwen", low)["gates"]["teacher_forced_mass_review"]["status"] == "FAIL"


def test_archival_regression_passes_on_exp28_records():
    raw = []
    for k in C.INSTRUCTIONS:
        a = Gt.archive28("mistral")[k]
        raw.append(dict(kind="archival", job=k, content=a["content"], digit_steps=[dict(face_logprobs=s) for s in a["steps"]]))
    assert Gt._regression("mistral", raw)["status"] == "PASS"
    raw[0]["content"] = "1 2 3"
    assert Gt._regression("mistral", raw)["status"] == "FAIL"


def test_guard_refuses_frozen_folders():
    with pytest.raises(SystemExit):
        gpu.guard_out(str(C.EXP28 / "main" / "qwen"))
    gpu.guard_out(str(C.EXP / "preflight" / "qwen"))
