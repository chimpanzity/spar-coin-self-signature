"""Offline tests for SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0 (no GPU, no API).

`ArchiveFake` replays Experiment 28's archived generations and position vectors (so archival and policy regression gates can
pass on CPU) and otherwise uses Experiment 29's hash-based toy policy. `FakeJudge` answers calibration items correctly with a
constant label bias and gives recognition items a known own-source bonus, so the crossed contrast has a known value.
"""

import json
import math

import pytest
from tests.test_dice_bidirectional_completion import FakeEngine

from spar_dynamic.dice_crossed_guidance.analysis import read_jsonl
from spar_dynamic.dice_six_roll_recognition import analysis as A
from spar_dynamic.dice_six_roll_recognition import config as C
from spar_dynamic.dice_six_roll_recognition import gates as Gt
from spar_dynamic.dice_six_roll_recognition import gpu
from spar_dynamic.dice_six_roll_recognition import stimuli as S

HANDOFF_TABLE = {("qwen", "G"): ("5 2 6 3 1 4", "5 2 6 3 4 1", "5 2 6 3 1 1"), ("qwen", "F"): ("3 1 4 6 2 5", "3 1 4 6 5 2", "3 1 4 6 2 2"),
                 ("mistral", "G"): ("4 2 6 1 3 5", "4 2 6 1 5 3", "4 2 6 1 3 3"), ("mistral", "F"): ("3 1 5 2 6 4", "3 1 5 2 4 6", "3 1 5 2 6 6")}


# ---------- fixtures and design ----------

def test_ground_truth_and_fixtures_match_exp28_and_handoff():
    gt = S.ground_truth()
    assert gt == {k: tuple(v) for k, v in C.REFERENCES.items()}
    fx = S.fixtures(gt)
    assert {k: (S.seq(f["authentic"]), S.seq(f["swap"]), S.seq(f["repeat"])) for k, f in fx.items()} == HANDOFF_TABLE
    assert S.seq(fx[("mistral", "G")]["authentic"]) == "4 2 6 1 3 5" and S.seq(fx[("mistral", "G")]["swap"]) == "4 2 6 1 5 3"
    v = Gt.verify_references()
    assert v["ok"], v["detail"]
    assert all(d["p5_match"] for d in v["detail"].values())


def test_transcription_errors_fail_closed(monkeypatch):
    # a Mistral-G sequence mistyped as in a hand-copied table must never become a stimulus
    bad = dict(C.REFERENCES)
    bad[("mistral", "G")] = (4, 2, 6, 1, 5, 3, 2, 4, 6, 1)
    monkeypatch.setattr(C, "REFERENCES", bad)
    with pytest.raises(ValueError):
        S.ground_truth()
    assert not Gt.verify_references()["ok"]
    with pytest.raises(AssertionError):
        S.build_fixture((4, 2, 6, 1, 3, 3, 2, 4, 6, 1))           # first six not six distinct faces
    with pytest.raises(AssertionError):
        S.build_fixture((4, 2, 6, 1, 3, 5, 2, 4, 6))              # nine rolls


def test_presentations_orientation_and_no_leakage():
    pc, cs = S.prompt_cells(), S.conditions()
    assert len(S.items()) == 8 and len(pc) == 32 and len(cs) == 64 and len({c["cell_id"] for c in cs}) == 64
    assert sum(c["frame"] == "self" for c in cs) == 32 and len(cs) * C.N_REPLICATES == 192
    by = {c["prompt_id"]: c for c in pc}
    for c in pc:
        other = by[c["prompt_id"][:-1] + ("2" if c["orientation"] == 1 else "1")]
        assert (c["seq_A"], c["seq_B"]) == (other["seq_B"], other["seq_A"])
        assert c[f"seq_{c['authentic_label']}"] == c["authentic"]
        assert c["prompt"].startswith(S.FRAME_TEXT[c["frame"]]) and c["prompt"].endswith("\n\nAnswer A or B only.")
        assert f"\n\nA: {c['seq_A']}\nB: {c['seq_B']}\n\n" in c["prompt"]
        assert not any(w in c["prompt"].lower() for w in ("qwen", "mistral", "authentic", "swap", "repeat", "foil", "predict"))
    assert S.FRAME_TEXT["self"].startswith("Another instance of your model was asked") and S.FRAME_TEXT["neutral"].startswith("A language model was asked")
    assert len({c["prompt"] for c in cs}) == 32                                 # both judges receive identical bytes
    assert by["self-mistral-G-swap-o1"]["prompt"] == ("Another instance of your model was asked to produce a sequence of simulated rolls of a "
                                                      "six-sided die.\n\nWhich of these two sequences is more likely to be the sequence it "
                                                      "produced?\n\nA: 4 2 6 1 3 5\nB: 4 2 6 1 5 3\n\nAnswer A or B only.")
    assert S.sha256(S.SOURCE_INSTRUCTION["G"]) == "edc7a4a228d493e83a5086181c170aa052e3e7cb8b34b9911ef4dc8147fdb8fe"
    assert S.sha256(S.SOURCE_INSTRUCTION["F"]) == "8adcaddfff0d9acee6bcc9060917175e7d68167f440c42b00a3800cd32dcef03"
    assert len(set(S.all_prompt_sha().values())) == len(S.all_prompt_sha()) == 72


def test_calibration_items_are_objective_and_disjoint_from_study():
    its = S.calibration_items()
    assert its == S.calibration_items() and len(its) == 18                     # deterministic
    study = {s for it in S.items() for s in (it["authentic"], it["foil"])}
    prefixes = {tuple(x[:4]) for x in C.REFERENCES.values()}
    targets = []
    for it in its:
        c, f = [int(v) for v in it["correct"].split()], [int(v) for v in it["foil"].split()]
        assert it["correct"] not in study and it["foil"] not in study and tuple(c[:4]) not in prefixes and c != f
        if it["task"] == "last_digit":
            assert c[:5] == f[:5] and c[5] != f[5] and c[5] != c[4] and f[5] != f[4] and it["question"].endswith(f"digit {c[5]}?")
            targets.append(c[5])
        elif it["task"] == "all_faces":
            assert sorted(c) == [1, 2, 3, 4, 5, 6] and f == c[:5] + [c[4]]
        else:
            assert c[:4] == f[:4] and c[4] > c[5] and f[4] < f[5] and sorted(c) == sorted(f) == [1, 2, 3, 4, 5, 6]
    assert sorted(targets) == [1, 2, 3, 4, 5, 6]
    assert sum(it["gated"] for it in its) == 12 and len(S.calibration_cells()) == 36


def test_frozen_files_match_code_if_frozen():
    if not (C.EXP / "inputs_sha256.json").exists():
        pytest.skip("not frozen yet")
    from spar_dynamic.dice_six_roll_recognition.__main__ import verify_frozen
    verify_frozen()


# ---------- arithmetic ----------

def test_policy_two_step_likelihood_and_logistic():
    fake = ArchiveFake("qwen")
    res = A.policy({"qwen": gpu.policy_rows(fake)})
    d = {(x["source_id"], x["foil_type"]): x for x in res["deltas"]}
    # Qwen-G under Qwen's archived vectors: Delta_swap position 5 = ln p(1) - ln p(4) at roll 5 (Exp 28: .8608 vs .1391)
    assert abs(d[("qwen-G", "swap")]["delta_pos5"] - math.log(0.860814 / 0.139107)) < 1e-4
    assert d[("qwen-G", "repeat")]["delta_pos5"] == 0.0
    x = d[("qwen-G", "swap")]
    assert abs(x["delta"] - (x["delta_pos5"] + x["delta_pos6"])) < 1e-12 and abs(x["p_authentic_of_two"] - A.logistic(x["delta"])) < 1e-15
    assert A.logistic(-800) == 0.0 and A.logistic(800) == 1.0 and A.logistic(-30) > 0        # no overflow at the extremes
    lp = A.log_p6({"1": -1000.0, "2": -1.0, "3": -2.0, "4": -3.0, "5": -4.0, "6": -5.0})
    assert math.isfinite(lp[0]) and abs(sum(math.exp(v) for v in lp) - 1) < 1e-12


def test_crossed_contrast_and_classification():
    pairs = []
    vals = {("qwen", "qwen"): 2.0, ("mistral", "qwen"): 0.5, ("mistral", "mistral"): 1.0, ("qwen", "mistral"): 1.5}
    for frame in C.FRAMES:
        for foil in C.FOILS:
            for i in C.INSTRUCTIONS:
                for (j, s), v in vals.items():
                    pairs.append(dict(frame=frame, foil_type=foil, source_instruction=i, judge=j, source=s, S=v + (0.3 if frame == "self" else 0)))
    rows = A.crossed(pairs)
    d = {(r["frame"], r["foil_type"], r["source_instruction"]): r for r in rows}
    assert d[("self", "swap", "G")]["D"] == pytest.approx(0.5 * ((2.0 - 0.5) + (1.0 - 1.5)))
    assert d[("self_minus_neutral", "swap", "F")]["D"] == pytest.approx(0.0)
    assert Gt.classify(0.2, 0.3, 0.1) == "consistent_target" and Gt.classify(-0.2, -0.3, 0.1) == "consistent_foil"
    assert Gt.classify(0.2, -0.3, 0.1) == Gt.classify(0.05, 0.3, 0.1) == "mixed_or_tied"


# ---------- fakes ----------

class ArchiveFake(FakeEngine):
    """Experiment 29's toy engine, but G/F generations and source-instruction scoring along the reference replay Experiment 28."""

    def __init__(self, key, **kw):
        super().__init__(key, **kw)
        raw = read_jsonl(C.EXP28_MAIN / key / "raw_attempts.jsonl")
        self.arc = {i: next(r for r in raw if r["condition"] == i) for i in C.INSTRUCTIONS}

    def generate(self, prompt, temperature=None, seed=None):
        for i, r in self.arc.items():
            if prompt == S.SOURCE_INSTRUCTION[i]:
                return {k: r[k] for k in ("prompt_tokens", "rendered_prompt_sha256", "completion_tokens", "generated_ids", "content",
                                          "finish_reason", "steps", "digit_steps", "temperature", "seed", "latency_ms")}
        return super().generate(prompt, temperature, seed)

    def score(self, prompt, history, method="incremental"):
        rows = super().score(prompt, history, method)
        for i, r in self.arc.items():
            if prompt != S.SOURCE_INSTRUCTION[i]:
                continue
            ref = list(C.REFERENCES[(self.key, i)])
            faces = [int(c) for c in history.split()]
            for x in rows:
                k = x["position"]
                if faces[:k - 1] == ref[:k - 1]:                         # same context as the archived generation step k
                    x["face_logprobs"] = dict(r["digit_steps"][k - 1]["face_logprobs"])
        return rows


class FakeJudge:
    """Correct on calibration (+3 toward the right label), constant A bias; recognition s = base(item) + bonus on own source."""

    def __init__(self, eng, bias=0.5, content=3.0, bonus=1.0, mass=0.95):
        self.eng, self.bias, self.content, self.bonus, self.mass = eng, bias, content, bonus, mass
        self.labels = {"A": dict(id=32, n_tokens=1, text="A", space_id=362), "B": dict(id=33, n_tokens=1, text="B", space_id=425)}
        self.correct = {c["prompt_sha256"]: c["correct_label"] for c in S.calibration_cells()}
        self.tech = {c["prompt_sha256"]: c["correct_label"] for c in S.tech_cells()}          # arithmetic is easy for every fake
        self.rec = {c["prompt_sha256"]: c for c in S.prompt_cells()}

    def context_check(self, prompt):
        return dict(label_appends_single_token={"A": True, "B": True}, assistant_prefix_tail="fake")

    def _d(self, prompt):
        h = S.sha256(prompt)
        if h in self.rec:
            c = self.rec[h]
            base = (int(S.sha256(c["item_id"] + c["frame"])[:4], 16) / 65535 - 0.5) * 3
            s = base + (self.bonus if c["source"] == self.eng.key else 0.0)
            return self.bias + (s if c["orientation"] == 1 else -s)
        if h in self.tech:
            lab = self.tech[h]
            return self.bias + (0.0 if lab is None else 8.0 if lab == "A" else -8.0)
        lab = self.correct.get(h)
        return self.bias + (0.0 if lab is None else self.content if lab == "A" else -self.content)

    def ask(self, prompt, tokenwise=False):
        d = self._d(prompt)
        pa = 1 / (1 + math.exp(-d))
        la, lb = math.log(self.mass * pa), math.log(self.mass * (1 - pa))
        r = dict(prompt_tokens=40, rendered_prompt_sha256=S.sha256(self.eng.rendered_text(prompt)), logp_A=la, logp_B=lb, logp_space_A=-9.0,
                 logp_space_B=-9.0, argmax_id=32 if d > 0 else 33, argmax_token="A" if d > 0 else "B", argmax_logprob=max(la, lb),
                 entropy_nats=0.5, top=[[32, "A", la], [33, "B", lb]], greedy_ids=[32 if d > 0 else 33], greedy_text="A" if d > 0 else "B",
                 finish_reason="stop", latency_ms=3)
        if tokenwise:
            r.update(logp_A_tokenwise=la + 0.01, logp_B_tokenwise=lb - 0.01)
        return r


def _chain(root, key, **kw):
    eng = ArchiveFake(key)
    return gpu.chain(eng, FakeJudge(eng, **kw), root)


# ---------- end to end ----------

def test_chain_passes_and_analysis_recovers_known_contrast(tmp_path):
    for key in C.MODELS:
        assert _chain(tmp_path, key) == "main"
        for stage, name in (("preflight", "preflight_gates"), ("calibration", "calibration_gate"), ("main", "main_checks")):
            g = json.load(open(tmp_path / stage / key / f"{name}.json"))
            assert g["overall"] == "PASS", {k: v for k, v in g["gates"].items() if v["status"] != "PASS"}
        cal = json.load(open(tmp_path / "calibration" / key / "calibration_gate.json"))
        assert cal["epsilon"] == pytest.approx(0.05) and cal["gates"]["cal_last_digit"]["detail"]["both_orders"] == 6
        raw = read_jsonl(tmp_path / "main" / key / "presentations.jsonl")
        assert len(raw) == 96 and sum("d_tokenwise" in r for r in raw) == 32
        assert [(r["prompt_id"], r["replicate"]) for r in sorted(raw, key=lambda r: r["order_index"])] == [tuple(j) for j in gpu.jobs_for(key, "main")]
        assert len(read_jsonl(tmp_path / "policy_benchmark" / key / "policy_teacher_forced.jsonl")) == 144
    from spar_dynamic.dice_six_roll_recognition.__main__ import analyse
    res = analyse(tmp_path)
    assert all(v["recognition"] == "ANALYSABLE" for v in res["status"].values())
    prim = [r for r in res["crossed"] if r["frame"] in C.FRAMES]
    assert len(prim) == 8 and all(r["D"] == pytest.approx(1.0) for r in prim)        # the fake's own-source bonus
    assert all(r["D"] == pytest.approx(0.0) for r in res["crossed"] if r["frame"] == "self_minus_neutral")
    assert len(res["pairs"]) == 32 and all(p["label_bias"] == pytest.approx(0.5) for p in res["pairs"])
    assert len(res["policy"]["deltas"]) == 2 * 4 * 2 and len(res["presentations"]) == 64
    for f in ("policy_likelihoods", "policy_deltas", "recognition_presentations", "paired_scores", "crossed_contrasts"):
        assert (tmp_path / "analysis" / f"{f}.csv").exists()
    assert len(list((tmp_path / "analysis" / "figures").glob("fig*.png"))) == 6


def test_calibration_failure_stops_that_judge_only(tmp_path):
    assert _chain(tmp_path, "qwen", bias=3.0, content=1.0) == "calibration"     # A bias beats content in the B orientation
    g = json.load(open(tmp_path / "calibration" / "qwen" / "calibration_gate.json"))
    assert g["overall"] == "FAIL" and g["gates"]["cal_last_digit"]["detail"]["both_orders"] == 0
    assert not (tmp_path / "main" / "qwen").exists()
    with pytest.raises(SystemExit):
        gpu.main(ArchiveFake("qwen"), FakeJudge(ArchiveFake("qwen")), tmp_path)
    assert _chain(tmp_path, "mistral") == "main"
    from spar_dynamic.dice_six_roll_recognition.__main__ import analyse
    res = analyse(tmp_path)
    assert res["status"]["qwen"]["recognition"] == "NOT INTERPRETABLE / NOT RUN" and res["status"]["mistral"]["recognition"] == "ANALYSABLE"
    assert res["crossed"] == [] and {p["judge"] for p in res["pairs"]} == {"mistral"}
    assert len(list((tmp_path / "analysis" / "figures").glob("fig*.png"))) == 6


def test_low_label_mass_fails_preflight(tmp_path):
    assert _chain(tmp_path, "mistral", mass=0.2) == "preflight"
    g = json.load(open(tmp_path / "preflight" / "mistral" / "preflight_gates.json"))
    assert {k for k, v in g["gates"].items() if v["status"] == "FAIL"} == {"tech_label_mass"}


def test_archival_mismatch_fails_preflight(tmp_path):
    eng = FakeEngine("qwen")                                                     # toy generations, not Experiment 28's
    eng.score = ArchiveFake("qwen").score
    assert gpu.chain(eng, FakeJudge(eng), tmp_path) == "preflight"
    g = json.load(open(tmp_path / "preflight" / "qwen" / "preflight_gates.json"))
    assert {k for k, v in g["gates"].items() if v["status"] == "FAIL"} >= {"archival_regression"}
    assert g["gates"]["policy_diagonal_regression"]["status"] == "PASS"


def test_main_resume_drift_and_tamper(tmp_path):
    key = "mistral"
    eng = ArchiveFake(key)
    gpu.preflight(eng, FakeJudge(eng), tmp_path)
    Gt.write_preflight_gate(key, tmp_path)
    gpu.calibration(eng, FakeJudge(eng), tmp_path)
    Gt.write_calibration_gate(key, tmp_path)
    with pytest.raises(SystemExit):                                              # calibration is never appended to
        gpu.calibration(eng, FakeJudge(eng), tmp_path)
    j, calls = FakeJudge(eng), {"n": 0}
    orig = j.ask

    def flaky(prompt, tokenwise=False):
        calls["n"] += 1
        if calls["n"] > 40:
            raise KeyboardInterrupt
        return orig(prompt, tokenwise)
    j.ask = flaky
    with pytest.raises(KeyboardInterrupt):
        gpu.main(eng, j, tmp_path)
    assert len(read_jsonl(tmp_path / "main" / key / "presentations.jsonl")) == 40
    gpu.main(eng, FakeJudge(eng), tmp_path)
    chk = Gt.write_main_checks(key, tmp_path)
    assert chk["overall"] == "PASS", {k: v for k, v in chk["gates"].items() if v["status"] != "PASS"}
    p = tmp_path / "main" / key / "presentations.jsonl"
    lines = p.read_text().splitlines()
    r = json.loads(lines[5])
    r["logp_A"] += 0.5
    lines[5] = json.dumps(r)
    p.write_text("\n".join(lines) + "\n")
    chk = Gt.main_checks(key, tmp_path)
    assert chk["gates"]["raw_files_untampered"]["status"] == "FAIL" and chk["gates"]["deterministic_replicates"]["status"] == "FAIL"
    r["prompt_sha256"] = "0" * 64
    lines[5] = json.dumps(r)
    p.write_text("\n".join(lines) + "\n")
    with pytest.raises(SystemExit):
        gpu.main(eng, FakeJudge(eng), tmp_path)


def test_gate_files_and_guards(tmp_path):
    _chain(tmp_path, "qwen", bias=3.0, content=1.0)
    with pytest.raises(SystemExit):
        gpu.check_gate(tmp_path / "calibration" / "qwen" / "calibration_gate.json", "qwen", "calibration")   # FAIL
    with pytest.raises(SystemExit):
        gpu.check_gate(tmp_path / "preflight" / "qwen" / "preflight_gates.json", "qwen", "calibration")      # wrong stage
    with pytest.raises(SystemExit):
        gpu.check_gate(tmp_path / "preflight" / "qwen" / "preflight_gates.json", "mistral", "preflight")     # wrong model
    gpu.check_gate(tmp_path / "preflight" / "qwen" / "preflight_gates.json", "qwen", "preflight")
    with pytest.raises(SystemExit):
        gpu.guard_out(str(C.EXP28 / "main"))
    with pytest.raises(SystemExit):
        gpu.guard_out(str(C.EXP.parent / "29_2026-10-31_bidirectional_dice_completion" / "main"))
    gpu.guard_out(str(C.EXP / "main" / "qwen"))
